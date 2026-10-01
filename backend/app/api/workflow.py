from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from bson import ObjectId
from app.core.database import Database
from app.schemas.project import RunResponse, AgentOutputResponse, AnswerSubmit
from app.services.workflow_persistence import (
    build_initial_state,
    finalize_run,
)
from app.utils.serialize import serialize_run, serialize_agent_output, serialize_cycle
from app.services.orchestration_service_v2 import orchestration_service_v2
from app.services.canon_service import get_canon_context, record_answer_decision
from app.services.project_event_service import emit_project_event
from app.services.story_bible_service import get_story_bible, rebuild_story_bible
from app.services.shared_narrative_context_service import shared_narrative_context_service
from app.services.development_state_service import development_state_service
from app.services.planning_authority_service import planning_authority_service
from app.services.narrative_analysis_engine import narrative_analysis_engine
from app.services.narrative_completeness_service import narrative_completeness_service
from app.services.story_knowledge_projection_service import story_knowledge_projection_service
from datetime import datetime
from typing import Any, Dict, List
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects/{project_id}", tags=["workflow"])

MAX_AUTOMATIC_CYCLES_PER_ADVANCE = 3


async def next_cycle_number(db, project_id: str) -> int:
    latest_cycle = await db.cycles.find_one(
        {"project_id": ObjectId(project_id)},
        sort=[("cycle_number", -1)],
    )
    return (latest_cycle.get("cycle_number", 0) + 1) if latest_cycle else 1


async def get_unprocessed_user_message_ids(db, project_id: str) -> List[ObjectId]:
    cycles = await db.cycles.find({"project_id": ObjectId(project_id)}).to_list(length=1000)
    processed = {
        message_id
        for cycle in cycles
        for message_id in cycle.get("trigger_message_ids", [])
    }
    messages = await db.timeline_messages.find(
        {"project_id": ObjectId(project_id), "role": "user"}
    ).sort("created_at", 1).to_list(length=1000)
    return [message["_id"] for message in messages if message["_id"] not in processed]


async def build_persistent_state(
    db,
    project: Dict[str, Any] | None,
    project_id: str,
    cycle_id: str | None = None,
) -> Dict[str, Any]:
    state = build_initial_state(project or {}, project_id)
    cycle = None
    if cycle_id:
        cycle = await db.cycles.find_one({
            "_id": ObjectId(cycle_id),
            "project_id": ObjectId(project_id),
        })
        if cycle:
            state["cycle_number"] = cycle.get("cycle_number", 1)

    messages = (
        await db.timeline_messages.find({"project_id": ObjectId(project_id)})
        .sort("created_at", 1)
        .to_list(length=1000)
    )
    state["timeline_messages"] = [
        {
            "id": str(m["_id"]),
            "cycle_number": m.get("cycle_number", 1),
            "role": m.get("role", "user"),
            "content": m.get("content", ""),
            "agent_name": m.get("agent_name"),
            "message_type": m.get("message_type", "summary"),
        }
        for m in messages
    ]

    trigger_ids = set(cycle.get("trigger_message_ids", [])) if cycle else set()
    state["new_messages"] = [
        message for message in state["timeline_messages"]
        if ObjectId(message["id"]) in trigger_ids
    ]

    outline = await db.outlines.find_one({"project_id": ObjectId(project_id)})
    if outline:
        state["previous_outline"] = {
            "premise": outline.get("premise", ""),
            "themes": outline.get("themes") or [],
            "acts": outline.get("acts") or [],
            "chapters": outline.get("chapters") or [],
        }
        state["outline"] = state["previous_outline"]

    characters = await db.characters.find({"project_id": ObjectId(project_id)}).to_list(length=100)
    if characters:
        state["previous_characters"] = characters
        state["characters"] = characters

    world_bible = await db.world_bibles.find_one({"project_id": ObjectId(project_id)})
    if world_bible:
        state["previous_world_bible"] = world_bible
        state["world_bible"] = world_bible

    unresolved = await db.questions.find(
        {"project_id": ObjectId(project_id), "answered": False}
    ).sort("created_at", 1).to_list(length=100)
    state["unresolved_questions"] = unresolved

    answered = await db.questions.find(
        {"project_id": ObjectId(project_id), "answered": True}
    ).sort("created_at", 1).to_list(length=100)
    state["questions"] = [
        {"text": q.get("text", ""), "choices": q.get("choices") or []}
        for q in answered + unresolved
    ]
    state["answers"] = [q.get("answer") or "" for q in answered]
    canon_context = await get_canon_context(db, project_id)
    state["canon_facts"] = canon_context["locked_facts"]
    state["decision_registry"] = canon_context["decisions"]
    state["rejected_decisions"] = canon_context["rejected_decisions"]

    outputs = await db.agent_outputs.find({"project_id": ObjectId(project_id)}).sort("created_at", 1).to_list(length=200)
    state["outputs"] = [
        {
            "agent_name": output.get("agent_name", ""),
            "content": output.get("content", ""),
            "metadata": output.get("metadata") or {},
        }
        for output in outputs
    ]

    state["story_bible"] = (await get_story_bible(db, project_id)).get("sections", {})
    state["confirmed_story_studio_planning"] = await story_knowledge_projection_service.confirmed_planning_context(db, project_id)
    queued_tasks = await db.cycle_tasks.find(
        {"project_id": ObjectId(project_id), "status": "queued"}
    ).sort("created_at", 1).to_list(length=100)
    state["queued_tasks"] = [
        {
            "id": str(task["_id"]),
            "task_type": task.get("task_type"),
            "agent_name": task.get("agent_name"),
            "instruction": task.get("instruction"),
            "parent_proposal_id": str(task.get("parent_proposal_id") or ""),
        }
        for task in queued_tasks
    ]
    state["new_messages"].extend(
        {
            "id": task["id"],
            "cycle_number": state.get("cycle_number", 1),
            "role": "system",
            "content": task.get("instruction") or task.get("task_type") or "",
            "agent_name": task.get("agent_name"),
            "message_type": "queued_task",
        }
        for task in state["queued_tasks"]
    )

    return state


async def run_workflow_async(project_id: str, run_id: str, cycle_id: str | None = None):
    """Run bounded automatic planning cycles until stable or author-blocked."""
    db = Database.get_db()

    try:
        active_cycle_id = cycle_id
        last_state: Dict[str, Any] = {}
        all_agents_run: List[str] = []
        completed_cycles = 0
        automatic_stop_reason = "Planning reached a stable point"

        for pass_index in range(MAX_AUTOMATIC_CYCLES_PER_ADVANCE):
            project = await db.projects.find_one({"_id": ObjectId(project_id)})
            if not project:
                logger.error("Project %s not found for workflow", project_id)
                return
            if not active_cycle_id:
                cycle_number = await next_cycle_number(db, project_id)
                cycle_doc = {
                    "project_id": ObjectId(project_id),
                    "cycle_number": cycle_number,
                    "trigger_message_ids": await get_unprocessed_user_message_ids(db, project_id),
                    "agents_run": [],
                    "started_at": datetime.utcnow(),
                    "finished_at": None,
                    "status": "running",
                    "automatic_continuation": pass_index > 0,
                    "parent_run_id": ObjectId(run_id),
                }
                inserted_cycle = await db.cycles.insert_one(cycle_doc)
                active_cycle_id = str(inserted_cycle.inserted_id)
                await emit_project_event(
                    db,
                    project_id,
                    "cycle_started",
                    cycle_number=cycle_number,
                    payload={"run_id": run_id, "automatic_continuation": pass_index > 0},
                )

            last_state = await build_persistent_state(
                db, project, project_id, active_cycle_id
            )
            last_state["automatic_development"] = True
            last_state["primary_run_plan"] = pass_index == 0
            studio_result = await orchestration_service_v2.execute_plan(
                db,
                project_id=project_id,
                run_id=run_id,
                cycle_id=active_cycle_id,
                state=last_state,
            )
            agents_run = studio_result.get("agents_run", [])
            all_agents_run.extend(agents_run)
            completed_cycles += 1

            await db.cycles.update_one(
                {
                    "_id": ObjectId(active_cycle_id),
                    "project_id": ObjectId(project_id),
                },
                {
                    "$set": {
                        "status": "completed",
                        "finished_at": datetime.utcnow(),
                        "agents_run": agents_run,
                        "automatic_continuation": pass_index > 0,
                    }
                },
            )
            queued_task_ids = [
                ObjectId(task["id"])
                for task in last_state.get("queued_tasks", [])
                if ObjectId.is_valid(task.get("id", ""))
            ]
            if queued_task_ids:
                await db.cycle_tasks.update_many(
                    {"_id": {"$in": queued_task_ids}},
                    {"$set": {
                        "status": "completed",
                        "completed_cycle_number": last_state.get("cycle_number", 1),
                        "completed_at": datetime.utcnow(),
                    }},
                )
            bible = await rebuild_story_bible(
                db,
                project_id,
                cycle_number=last_state.get("cycle_number", 1),
            )
            await emit_project_event(
                db,
                project_id,
                "story_bible_updated",
                cycle_number=last_state.get("cycle_number", 1),
                payload={
                    "version": bible.get("version"),
                    "plan_id": studio_result.get("plan_id"),
                    "artifacts": studio_result.get("artifacts", {}),
                    "automatic_cycle": pass_index + 1,
                },
            )
            await emit_project_event(
                db,
                project_id,
                "cycle_completed",
                cycle_number=last_state.get("cycle_number", 1),
                payload={
                    "run_id": run_id,
                    "agents_run": agents_run,
                    "automatic_cycle": pass_index + 1,
                },
            )

            blocking_query = {
                "project_id": ObjectId(project_id),
                "answered": False,
                "$or": [{"blocking": True}, {"blocking": {"$exists": False}}],
            }
            if run_id:
                run_record = await db.runs.find_one({"_id": ObjectId(run_id), "project_id": ObjectId(project_id)}, {"metadata": 1, "started_at": 1}) or {}
                if (run_record.get("metadata") or {}).get("story_studio_job_id") and run_record.get("started_at"):
                    blocking_query["created_at"] = {"$gte": run_record["started_at"]}
            blocking_questions = await db.questions.count_documents(blocking_query)
            if blocking_questions:
                automatic_stop_reason = "Waiting for an author decision"
                break
            if not agents_run:
                automatic_stop_reason = studio_result.get("stop_reason") or automatic_stop_reason
                break
            if pass_index + 1 >= MAX_AUTOMATIC_CYCLES_PER_ADVANCE:
                automatic_stop_reason = "Automatic cycle limit reached"
                break

            active_cycle_id = None
            await db.runs.update_one(
                {"_id": ObjectId(run_id), "project_id": ObjectId(project_id)},
                {"$set": {
                    "current_agent": "",
                    "metadata.author_phase": "Preparing the next planning pass",
                    "metadata.automatic_cycles_completed": completed_cycles,
                }},
            )

        await finalize_run(
            db,
            project_id=project_id,
            run_id=run_id,
            result=last_state,
        )
        await db.runs.update_one(
            {"_id": ObjectId(run_id), "project_id": ObjectId(project_id)},
            {"$set": {
                "metadata.automatic_development": True,
                "metadata.automatic_cycles_completed": completed_cycles,
                "metadata.automatic_stop_reason": automatic_stop_reason,
                "metadata.agents_run": all_agents_run,
                "metadata.author_phase": (
                    "Waiting for your decision"
                    if automatic_stop_reason == "Waiting for an author decision"
                    else "Story development finished"
                ),
            }},
        )
        resolved_count = 0
        invalidations = await db.planning_invalidations.find({
            "project_id": ObjectId(project_id), "status": "pending",
        }).to_list(length=500)
        agents_completed = set(all_agents_run)
        for invalidation in invalidations:
            required = set(invalidation.get("required_agents") or [])
            if required and not required.issubset(agents_completed):
                continue
            result = await db.planning_invalidations.update_one(
                {"_id": invalidation["_id"], "status": "pending"},
                {"$set": {"status": "resolved", "resolved_at": datetime.utcnow(), "resolved_by_run_id": ObjectId(run_id)}},
            )
            resolved_count += result.modified_count
        remaining_invalidations = await db.planning_invalidations.count_documents(
            {"project_id": ObjectId(project_id), "status": "pending"}
        )
        await db.projects.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {
                "planning_reconsideration.status": "pending" if remaining_invalidations else "resolved",
                "planning_reconsideration.remaining": remaining_invalidations,
                "planning_reconsideration.updated_at": datetime.utcnow(),
            }},
        )
        if resolved_count:
            await narrative_analysis_engine.analyze(db, project_id, force=True)
            await rebuild_story_bible(
                db,
                project_id,
                cycle_number=int(last_state.get("cycle_number") or 0),
            )
        await narrative_completeness_service.calculate(db, project_id)
        logger.info("Workflow run %s finished for project %s", run_id, project_id)

    except Exception as exc:
        logger.exception("Workflow run %s failed", run_id)
        error_code = str(getattr(exc, "code", "") or type(exc).__name__).upper()
        error_message = str(exc) or "The story team could not complete this development pass."
        await db.runs.update_one(
            {
                "_id": ObjectId(run_id),
                "project_id": ObjectId(project_id),
            },
            {
                "$set": {
                    "status": "failed",
                    "current_agent": "",
                    "finished_at": datetime.utcnow(),
                    "error_code": error_code,
                    "error": error_message,
                    "metadata.author_phase": "Development needs attention",
                    "metadata.recovery_action": "retry_development",
                }
            },
        )
        if active_cycle_id:
            await db.cycles.update_one(
                {
                    "_id": ObjectId(active_cycle_id),
                    "project_id": ObjectId(project_id),
                },
                {"$set": {"status": "failed", "finished_at": datetime.utcnow()}},
            )
        await emit_project_event(
            db,
            project_id,
            "workflow_failed",
            cycle_number=int(last_state.get("cycle_number") or 0),
            payload={"run_id": run_id, "error_code": error_code, "message": error_message},
        )
    finally:
        await development_state_service.release(db, project_id, run_id)


@router.post("/run", response_model=RunResponse)
async def run_workflow(project_id: str, background_tasks: BackgroundTasks):
    """Start a new workflow run for a project."""
    db = Database.get_db()

    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")

    project = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    lease_token = await development_state_service.acquire(db, project_id)
    if not lease_token:
        raise HTTPException(
            status_code=409,
            detail="Story development is already running for this project. Open Project Activity to follow its progress.",
        )

    cycle_number = await next_cycle_number(db, project_id)
    cycle_dict = {
        "project_id": ObjectId(project_id),
        "cycle_number": cycle_number,
        "trigger_message_ids": await get_unprocessed_user_message_ids(db, project_id),
        "agents_run": [],
        "started_at": datetime.utcnow(),
        "finished_at": None,
        "status": "running",
    }
    cycle_result = await db.cycles.insert_one(cycle_dict)
    cycle_id = str(cycle_result.inserted_id)

    run_dict = {
        "project_id": ObjectId(project_id),
        "status": "running",
        "current_agent": "OrchestratorAgent",
        "started_at": datetime.utcnow(),
        "finished_at": None,
        "metadata": {
            "cycle_id": cycle_id,
            "cycle_number": cycle_number,
            "automatic_development": True,
            "max_automatic_cycles": MAX_AUTOMATIC_CYCLES_PER_ADVANCE,
        },
    }

    try:
        result = await db.runs.insert_one(run_dict)
        run_id = str(result.inserted_id)
        await development_state_service.attach_run(db, project_id, lease_token, run_id)
    except Exception:
        await development_state_service.release(db, project_id)
        raise
    await emit_project_event(
        db, project_id, "cycle_started",
        cycle_number=cycle_number,
        payload={"run_id": run_id},
    )

    background_tasks.add_task(run_workflow_async, project_id, run_id, cycle_id)

    return RunResponse(**serialize_run({**run_dict, "_id": result.inserted_id}))


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(project_id: str, run_id: str):
    """Get a specific run."""
    db = Database.get_db()

    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    if not ObjectId.is_valid(run_id):
        raise HTTPException(status_code=400, detail="Invalid run ID")

    run = await db.runs.find_one({
        "_id": ObjectId(run_id),
        "project_id": ObjectId(project_id),
    })
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return RunResponse(**serialize_run(run))


@router.get("/runs", response_model=List[RunResponse])
async def get_runs(project_id: str):
    """Get all runs for a project, newest first."""
    db = Database.get_db()

    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")

    runs = (
        await db.runs.find({"project_id": ObjectId(project_id)})
        .sort("started_at", -1)
        .to_list(length=100)
    )
    return [RunResponse(**serialize_run(r)) for r in runs]


@router.post("/answers")
async def submit_answer(
    project_id: str,
    answer: AnswerSubmit,
):
    """Resolve a question and persist the answer into decisions and canon."""
    db = Database.get_db()

    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")

    if not ObjectId.is_valid(answer.question_id):
        raise HTTPException(status_code=400, detail="Invalid question ID")

    question = await db.questions.find_one({
        "_id": ObjectId(answer.question_id),
        "project_id": ObjectId(project_id),
    })
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    invalidation = await planning_authority_service.supersede_for_decision(
        db,
        project_id=project_id,
        question_id=answer.question_id,
        question_text=str(question.get("text") or ""),
        # Development may continue past a non-blocking question by using its
        # documented default. If the author's first answer differs, that
        # default is the authority that generated planning must be compared
        # against; treating the prior value as empty would leave stale work
        # active and silently contradictory.
        previous_answer=str(
            question.get("answer")
            if question.get("answered")
            else question.get("default_recommendation") or ""
        ),
        new_answer=answer.answer,
    )

    await db.questions.update_one(
        {
            "_id": ObjectId(answer.question_id),
            "project_id": ObjectId(project_id),
        },
        {"$set": {"answered": True, "answer": answer.answer}},
    )
    await db.answers.insert_one({
        "project_id": ObjectId(project_id),
        "question_id": ObjectId(answer.question_id),
        "answer": answer.answer,
        "created_at": datetime.utcnow(),
    })
    await record_answer_decision(
        db,
        project_id=project_id,
        question=question,
        answer=answer.answer,
    )
    await shared_narrative_context_service.ingest(
        db,
        project_id,
        content=answer.answer,
        source_type="question_answer",
        source_id=answer.question_id,
        source_excerpt=f"{question.get('text', '')} Answer: {answer.answer}",
        structured={
            "subject": str(question.get("subject") or question.get("topic") or "Author answer"),
            "field": str(question.get("field") or "resolved_question"),
            "value": answer.answer,
            "confidence": 0.98,
        },
    )
    await emit_project_event(
        db, project_id, "question_resolved",
        cycle_number=int(question.get("cycle_number") or 1),
        payload={
            "question_id": answer.question_id,
            "affected_planning_records": invalidation.get("affected_count", 0),
        },
    )
    await narrative_analysis_engine.analyze(db, project_id, force=True)
    await rebuild_story_bible(db, project_id)
    await db.projects.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {"updated_at": datetime.utcnow()}},
    )

    unanswered = await db.questions.count_documents(
        {
            "project_id": ObjectId(project_id),
            "answered": False,
            "$or": [{"blocking": True}, {"blocking": {"$exists": False}}],
        }
    )
    return {
        "message": "Answer submitted",
        "remaining_questions": unanswered,
        "canon_updated": True,
    }


@router.post("/cycle", response_model=RunResponse)
async def run_cycle(project_id: str, background_tasks: BackgroundTasks):
    """Start a new discussion cycle."""
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")

    project = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    lease_token = await development_state_service.acquire(db, project_id)
    if not lease_token:
        raise HTTPException(
            status_code=409,
            detail="Story development is already running for this project. Open Project Activity to follow its progress.",
        )

    next_cycle = await next_cycle_number(db, project_id)
    trigger_message_ids = await get_unprocessed_user_message_ids(db, project_id)

    cycle_dict = {
        "project_id": ObjectId(project_id),
        "cycle_number": next_cycle,
        "trigger_message_ids": trigger_message_ids,
        "agents_run": [],
        "started_at": datetime.utcnow(),
        "finished_at": None,
        "status": "running"
    }
    cycle_result = await db.cycles.insert_one(cycle_dict)
    cycle_id = str(cycle_result.inserted_id)

    # Create a Run to track progress (UI expects Run)
    run_dict = {
        "project_id": ObjectId(project_id),
        "status": "running",
        "current_agent": "OrchestratorAgent",
        "started_at": datetime.utcnow(),
        "finished_at": None,
        "metadata": {"cycle_id": cycle_id, "cycle_number": next_cycle}
    }
    try:
        run_result = await db.runs.insert_one(run_dict)
        run_id = str(run_result.inserted_id)
        await development_state_service.attach_run(db, project_id, lease_token, run_id)
    except Exception:
        await development_state_service.release(db, project_id)
        raise
    await emit_project_event(
        db, project_id, "cycle_started",
        cycle_number=next_cycle,
        payload={"run_id": run_id},
    )

    background_tasks.add_task(run_cycle_async, project_id, run_id, cycle_id)

    return RunResponse(**serialize_run({**run_dict, "_id": run_result.inserted_id}))


async def run_cycle_async(project_id: str, run_id: str, cycle_id: str):
    """Background task to run a discussion cycle."""
    db = Database.get_db()
    try:
        project = await db.projects.find_one({"_id": ObjectId(project_id)})
        result = await build_persistent_state(db, project, project_id, cycle_id)
        studio_result = await orchestration_service_v2.execute_plan(
            db,
            project_id=project_id,
            run_id=run_id,
            cycle_id=cycle_id,
            state=result,
        )
        agents_run = studio_result.get("agents_run", [])
        
        # Update cycle
        await db.cycles.update_one(
            {
                "_id": ObjectId(cycle_id),
                "project_id": ObjectId(project_id),
            },
            {
                "$set": {
                    "status": "completed",
                    "finished_at": datetime.utcnow(),
                    "agents_run": agents_run
                }
            }
        )
        await db.projects.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {"updated_at": datetime.utcnow()}},
        )
        queued_task_ids = [
            ObjectId(task["id"])
            for task in result.get("queued_tasks", [])
            if ObjectId.is_valid(task.get("id", ""))
        ]
        if queued_task_ids:
            await db.cycle_tasks.update_many(
                {"_id": {"$in": queued_task_ids}},
                {
                    "$set": {
                        "status": "completed",
                        "completed_cycle_number": result.get("cycle_number", 1),
                        "completed_at": datetime.utcnow(),
                    }
                },
            )
        await finalize_run(db, project_id=project_id, run_id=run_id, result=result)
        bible = await rebuild_story_bible(
            db,
            project_id,
            cycle_number=result.get("cycle_number", 1),
        )
        await emit_project_event(
            db,
            project_id,
            "story_bible_updated",
            cycle_number=result.get("cycle_number", 1),
            payload={
                "version": bible.get("version"),
                "plan_id": studio_result.get("plan_id"),
                "artifacts": studio_result.get("artifacts", {}),
            },
        )
        await emit_project_event(
            db, project_id, "cycle_completed",
            cycle_number=result.get("cycle_number", 1),
            payload={"run_id": run_id, "agents_run": agents_run},
        )
        
    except Exception as exc:
        logger.exception("Cycle run %s failed", run_id)
        await db.runs.update_one(
            {"_id": ObjectId(run_id), "project_id": ObjectId(project_id)},
            {"$set": {
                "status": "failed",
                "current_agent": "",
                "finished_at": datetime.utcnow(),
                "error_code": str(getattr(exc, "code", "") or type(exc).__name__).upper(),
                "error": str(exc),
                "metadata.author_phase": "Development needs attention",
                "metadata.recovery_action": "retry_development",
            }},
        )
        await db.cycles.update_one(
            {"_id": ObjectId(cycle_id), "project_id": ObjectId(project_id)},
            {"$set": {"status": "failed", "finished_at": datetime.utcnow()}},
        )
        await emit_project_event(
            db, project_id, "workflow_failed", cycle_number=0,
            payload={"run_id": run_id, "message": str(exc)},
        )
    finally:
        await development_state_service.release(db, project_id, run_id)


@router.get("/cycles", response_model=List[dict])
async def get_cycles(project_id: str):
    """Get all cycles for a project."""
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    cycles = await db.cycles.find({"project_id": ObjectId(project_id)}).sort("cycle_number", 1).to_list(length=100)
    return [serialize_cycle(c) for c in cycles]


@router.get("/outputs", response_model=List[AgentOutputResponse])
async def get_agent_outputs(project_id: str, run_id: str = None):
    """Get agent outputs for a project or specific run."""
    db = Database.get_db()

    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")

    query: dict = {"project_id": ObjectId(project_id)}
    if run_id:
        if not ObjectId.is_valid(run_id):
            raise HTTPException(status_code=400, detail="Invalid run ID")
        run = await db.runs.find_one({
            "_id": ObjectId(run_id),
            "project_id": ObjectId(project_id),
        })
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        query["run_id"] = ObjectId(run_id)
    else:
        runs = await db.runs.find({"project_id": ObjectId(project_id)}).to_list(length=100)
        run_ids = [r["_id"] for r in runs]
        if not run_ids:
            return []
        query["run_id"] = {"$in": run_ids}

    outputs = await db.agent_outputs.find(query).sort("created_at", 1).to_list(length=200)
    return [AgentOutputResponse(**serialize_agent_output(o)) for o in outputs]


@router.get("/stream")
async def stream_project_events(project_id: str, request: Request):
    """Stream project mutation events for Story Bible synchronization."""
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")

    async def event_generator():
        db = Database.get_db()
        last_id = request.headers.get("last-event-id")
        last_seen = ObjectId(last_id) if last_id and ObjectId.is_valid(last_id) else None
        if last_seen is None:
            latest = await db.project_events.find_one(
                {"project_id": ObjectId(project_id)},
                sort=[("_id", -1)],
            )
            last_seen = latest.get("_id") if latest else None
        yield f"event: connected\ndata: {json.dumps({'project_id': project_id})}\n\n"
        heartbeat = 0
        while not await request.is_disconnected():
            query: Dict[str, Any] = {"project_id": ObjectId(project_id)}
            if last_seen:
                query["_id"] = {"$gt": last_seen}
            events = await db.project_events.find(query).sort("_id", 1).to_list(length=100)
            for event in events:
                last_seen = event["_id"]
                payload = {
                    "id": str(event["_id"]),
                    "event_type": event.get("event_type"),
                    "cycle_number": event.get("cycle_number", 0),
                    "payload": event.get("payload") or {},
                    "created_at": event.get("created_at", datetime.utcnow()).isoformat(),
                }
                yield f"id: {payload['id']}\nevent: project_update\ndata: {json.dumps(payload)}\n\n"
            heartbeat += 1
            if heartbeat % 15 == 0:
                yield "event: heartbeat\ndata: {}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
