"""Persist workflow state and agent outputs to MongoDB."""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from bson import ObjectId
from app.services.canon_service import question_is_solved

AGENT_ORDER = [
    "intake",
    "brainstorm",
    "critic",
    "story_architect",
    "question",
    "revision",
]

AGENT_DISPLAY_NAMES = {
    "intake": "Intake Agent",
    "brainstorm": "Brainstorm Agent",
    "critic": "Critic Agent",
    "story_architect": "Story Architect Agent",
    "question": "Question Agent",
    "revision": "Revision Agent",
}

NODE_TO_SLUG = {
    "intake": "intake",
    "brainstorm": "brainstorm",
    "critic": "critic",
    "architect": "story_architect",
    "question_agent": "question",
    "revision": "revision",
}


def build_initial_state(project: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": project_id,
        "title": project.get("title", ""),
        "premise": project.get("premise", ""),
        "idea_dump": project.get("idea_dump", "") or project.get("premise", ""),
        "genre": project.get("genre", ""),
        "tone": project.get("tone", ""),
        "themes": project.get("themes") or [],
        "inspirations": project.get("inspirations") or [],
        "character_notes": project.get("character_notes") or "",
        "world_notes": project.get("world_notes") or "",
        "plot_notes": project.get("plot_notes") or "",
        "notes": project.get("notes") or "",
        "timeline_messages": [],
        "new_messages": [],
        "previous_outline": None,
        "previous_characters": None,
        "previous_world_bible": None,
        "cycle_number": 1,
        "outputs": [],
        "ideas": [],
        "critiques": [],
        "questions": [],
        "unresolved_questions": [],
        "answers": [],
        "outline": {},
        "characters": [],
        "world_bible": {},
        "current_agent": "",
        "logs": [],
    }


def extract_agent_content(agent_slug: str, state: Dict[str, Any]) -> str:
    """Build human-readable JSON content for an agent output."""
    if agent_slug == "intake":
        payload = {
            "genre": state.get("genre"),
            "themes": state.get("themes"),
            "hooks": state.get("hooks"),
            "assumptions": state.get("assumptions"),
            "premise_candidates": state.get("premise_candidates"),
            "character_concepts": state.get("character_concepts"),
            "setting_ideas": state.get("setting_ideas"),
            "plot_seeds": state.get("plot_seeds"),
        }
    elif agent_slug == "brainstorm":
        payload = {
            "ideas": state.get("ideas"),
            "conflicts": state.get("conflicts"),
            "twists": state.get("twists"),
            "scene_ideas": state.get("scene_ideas"),
            "symbolism": state.get("symbolism"),
            "alternative_directions": state.get("alternative_directions"),
        }
    elif agent_slug == "critic":
        payload = {
            "critiques": state.get("critiques"),
            "weaknesses": state.get("weaknesses"),
            "suggestions": state.get("suggestions"),
            "missing_elements": state.get("missing_elements"),
        }
    elif agent_slug == "story_architect":
        payload = state.get("outline") or {}
    elif agent_slug == "question":
        payload = {"questions": state.get("questions") or []}
    elif agent_slug == "revision":
        payload = state.get("outline") or {}
    else:
        payload = {"status": "completed"}

    return json.dumps(payload, indent=2, default=str)


async def save_agent_output(
    db,
    *,
    project_id: str,
    run_id: str,
    agent_slug: str,
    state: Dict[str, Any],
) -> None:
    cycle_number = state.get("cycle_number")
    content = extract_agent_content(agent_slug, state)
    display_name = AGENT_DISPLAY_NAMES.get(agent_slug, agent_slug)
    metadata = {}
    if cycle_number:
        metadata["cycle_number"] = cycle_number
    trace = await db.execution_traces.find_one(
        {"agent_name": display_name.replace(" ", "")},
        sort=[("created_at", -1)],
    )
    if trace:
        metadata.update({
            "provider": trace.get("provider"),
            "model": trace.get("model"),
            "tokens": trace.get("total_tokens", 0),
            "cost": trace.get("cost_usd", 0),
            "latency": trace.get("latency_ms", 0),
            "duration_ms": trace.get("latency_ms", 0),
            "execution_trace_id": str(trace.get("_id", "")),
            "source_type": "real_ai" if trace.get("provider") != "mock" else "test_mock",
            "fallback_used": trace.get("fallback_used", False),
        })

    await db.agent_outputs.insert_one({
        "project_id": ObjectId(project_id),
        "run_id": ObjectId(run_id),
        "agent_name": display_name,
        "agent_slug": agent_slug,
        "content": content,
        "metadata": metadata,
        "created_at": datetime.utcnow(),
    })
    if cycle_number:
        await db.timeline_messages.insert_one({
            "project_id": ObjectId(project_id),
            "cycle_number": cycle_number,
            "role": "agent",
            "agent_name": display_name,
            "message_type": "summary",
            "content": content,
            "created_at": datetime.utcnow(),
        })


async def save_outline(db, project_id: str, outline: Dict[str, Any]) -> None:
    if not outline:
        return
    now = datetime.utcnow()
    await db.outlines.update_one(
        {"project_id": ObjectId(project_id)},
        {
            "$set": {
                "project_id": ObjectId(project_id),
                "premise": outline.get("premise", ""),
                "themes": outline.get("themes") or [],
                "acts": outline.get("acts") or [],
                "chapters": outline.get("chapters") or [],
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    await db.projects.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {"updated_at": now}},
    )


async def save_questions(
    db,
    project_id: str,
    questions: List[Dict[str, Any]],
    *,
    cycle_number: int | None = None,
    agent_name: str = "QuestionAgent",
) -> None:
    if not questions:
        return
    for q in questions:
        text = q.get("text", "").strip()
        if not text:
            continue
        if await question_is_solved(db, project_id=project_id, text=text, choices=q.get("choices") or []):
            continue
        exists = await db.questions.find_one({"project_id": ObjectId(project_id), "text": text})
        if exists:
            continue
        await db.questions.insert_one({
            "project_id": ObjectId(project_id),
            "text": text,
            "choices": q.get("choices") or [],
            "default_recommendation": q.get("default_recommendation"),
            "story_area": q.get("story_area"),
            "cycle_number": int(q.get("cycle_number") or cycle_number or 1),
            "agent_name": q.get("agent_name") or agent_name,
            # QuestionAgent is explicitly asked for optional, high-value
            # questions. Those should be visible to the author without
            # freezing automatic project development. Older questions that do
            # not carry this field retain their historical blocking behavior.
            "blocking": bool(q.get("blocking", False)),
            "answered": False,
            "created_at": datetime.utcnow(),
        })


def make_progress_handler(db, project_id: str, run_id: str):
    """Create async callback for workflow node progress."""

    async def on_progress(phase: str, node_name: str, state: Dict[str, Any]) -> None:
        slug = NODE_TO_SLUG.get(node_name, node_name)
        run_oid = ObjectId(run_id)

        if phase == "start":
            await db.runs.update_one(
                {"_id": run_oid},
                {"$set": {"current_agent": slug, "status": "running"}},
            )
            return

        if phase == "complete":
            await save_agent_output(
                db,
                project_id=project_id,
                run_id=run_id,
                agent_slug=slug,
                state=state,
            )
            if slug == "story_architect" and state.get("outline"):
                await save_outline(db, project_id, state["outline"])
            if slug == "question" and state.get("questions"):
                await save_questions(db, project_id, state["questions"])

    return on_progress


async def finalize_run(
    db,
    *,
    project_id: str,
    run_id: str,
    result: Dict[str, Any],
) -> str:
    """Set final run status. Returns terminal status string."""
    run = await db.runs.find_one({"_id": ObjectId(run_id), "project_id": ObjectId(project_id)}, {"metadata": 1, "started_at": 1}) or {}
    question_query = {
        "project_id": ObjectId(project_id),
        "answered": False,
        "$or": [
            {"blocking": True},
            {"blocking": {"$exists": False}},
        ],
    }
    # Story Studio must not be held by an old unresolved question from a
    # previous conversation. Questions created by this durable run remain
    # fully governed and blocking; ordinary workflow runs retain historical
    # project-wide behavior for backward compatibility.
    if (run.get("metadata") or {}).get("story_studio_job_id") and run.get("started_at"):
        question_query["created_at"] = {"$gte": run["started_at"]}
    unanswered = await db.questions.count_documents(question_query)
    if unanswered:
        status = "waiting_for_user"
        current_agent = "QuestionAgent"
    else:
        status = "completed"
        current_agent = "completed"

    await db.runs.update_one(
        {
            "_id": ObjectId(run_id),
            "project_id": ObjectId(project_id),
        },
        {
            "$set": {
                "status": status,
                "current_agent": current_agent,
                "finished_at": datetime.utcnow(),
            }
        },
    )
    await db.projects.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {"updated_at": datetime.utcnow()}},
    )
    return status
