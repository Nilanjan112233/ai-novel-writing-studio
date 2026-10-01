from fastapi import APIRouter, HTTPException
from bson import ObjectId
from app.core.database import Database
from app.schemas.project import OutlineResponse, CharacterResponse, WorldBibleResponse, QuestionResponse
from app.utils.serialize import serialize_outline, serialize_question
from app.services.memory_provider import memory_provider_service
from app.services.memory_incremental_index_service import memory_incremental_index_service
from app.services.canon_service import get_canon_context, upsert_canon_fact
from app.services.project_event_service import emit_project_event
from app.services.story_bible_service import get_story_bible as load_story_bible, rebuild_story_bible
from app.services.database_audit_service import audit_project_database
from app.services.story_knowledge_projection_service import story_knowledge_projection_service
from typing import List
from datetime import datetime

router = APIRouter(prefix="/api/projects/{project_id}", tags=["data"])


def serialize_doc(doc: dict) -> dict:
    data = {}
    for key, value in doc.items():
        if key == "_id":
            data["id"] = str(value)
        elif isinstance(value, ObjectId):
            data[key] = str(value)
        elif isinstance(value, datetime):
            data[key] = value.isoformat()
        elif isinstance(value, list):
            data[key] = [serialize_doc(v) if isinstance(v, dict) else str(v) if isinstance(v, ObjectId) else v for v in value]
        elif isinstance(value, dict):
            data[key] = serialize_doc(value)
        else:
            data[key] = value
    return data


@router.get("/outline", response_model=OutlineResponse)
async def get_outline(project_id: str):
    """Get the outline for a project."""
    db = Database.get_db()
    
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    
    outline = await db.outlines.find_one({"project_id": ObjectId(project_id)})
    
    if not outline:
        raise HTTPException(status_code=404, detail="Outline not created")
    
    return OutlineResponse(**serialize_outline(outline, project_id))


@router.get("/characters", response_model=List[CharacterResponse])
async def get_characters(project_id: str):
    """Get characters for a project."""
    db = Database.get_db()
    
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    
    characters = await db.characters.find({"project_id": ObjectId(project_id)}).to_list(length=100)
    return [CharacterResponse(**c) for c in characters] if characters else []


@router.get("/world", response_model=WorldBibleResponse)
async def get_world_bible(project_id: str):
    """Get world bible for a project."""
    db = Database.get_db()
    
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    
    world = await db.world_bibles.find_one({"project_id": ObjectId(project_id)})
    
    if not world:
        raise HTTPException(status_code=404, detail="World artifact not created")
    
    return WorldBibleResponse(**world)


@router.get("/questions", response_model=List[QuestionResponse])
async def get_questions(project_id: str):
    """Get questions for a project."""
    db = Database.get_db()
    
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    
    questions = (
        await db.questions.find({"project_id": ObjectId(project_id)})
        .sort("created_at", 1)
        .to_list(length=100)
    )
    return [QuestionResponse(**serialize_question(q)) for q in questions] if questions else []


@router.get("/character-bibles")
async def get_character_bibles(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    await story_knowledge_projection_service.normalize_planning_character_names(db, project_id)
    docs = await db.character_bibles.find({"project_id": ObjectId(project_id)}).sort("name", 1).to_list(length=100)
    return [serialize_doc(doc) for doc in docs]


@router.get("/story-knowledge/candidates")
async def get_story_knowledge_candidates(project_id: str):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    return await story_knowledge_projection_service.list_candidates(Database.get_db(), project_id)


@router.post("/story-knowledge/candidates/{candidate_id}/decision")
async def decide_story_knowledge_candidate(project_id: str, candidate_id: str, payload: dict):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    try:
        return await story_knowledge_projection_service.decide(
            Database.get_db(), project_id, candidate_id, str(payload.get("decision") or "")
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/story-knowledge/reproject")
async def reproject_story_knowledge(project_id: str):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    db = Database.get_db()
    for collection in ("character_bibles", "relationship_graphs", "mystery_registry", "plot_threads", "timeline_entries", "artifact_registry", "knowledge_entries"):
        await db[collection].delete_many({"project_id": ObjectId(project_id), "authority_status": "candidate", "source_type": "approved_discovery_prose"})
    world = await db.world_bibles.find_one({"project_id": ObjectId(project_id)})
    if world and world.get("suggested_world_facts"):
        remaining = [item for item in world.get("suggested_world_facts") if item.get("source_type") != "approved_discovery_prose"]
        await db.world_bibles.update_one({"_id": world["_id"]}, {"$set": {"suggested_world_facts": remaining}})
    extractions = await db.discovery_extractions.find({"project_id": ObjectId(project_id)}).to_list(length=500)
    results = []
    for extraction in extractions:
        try:
            results.append(await story_knowledge_projection_service.project_candidates(
                db, project_id, extraction.get("candidates") or [], source_type="approved_discovery_prose",
                source_id=str(extraction.get("source_draft_id") or extraction.get("extraction_id") or ""),
                source_chapter=int(extraction.get("chapter_number") or 0) or None,
            ))
        except Exception as exc:
            results.append({"status": "failed", "source_chapter": extraction.get("chapter_number"), "error": str(exc)})
    return {"extractions": len(extractions), "results": results}


@router.get("/world-bible")
async def get_narrative_world_bible(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    doc = await db.world_bibles.find_one({"project_id": ObjectId(project_id)})
    return serialize_doc(doc) if doc else {}


@router.get("/plot-threads")
async def get_plot_threads(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    docs = await db.plot_threads.find({"project_id": ObjectId(project_id)}).sort("updated_at", -1).to_list(length=100)
    return [serialize_doc(doc) for doc in docs]


@router.get("/themes")
async def get_theme_registry(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    doc = await db.theme_registry.find_one({"project_id": ObjectId(project_id)})
    return serialize_doc(doc) if doc else {}


@router.get("/foreshadowing")
async def get_foreshadowing(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    docs = await db.foreshadow_registry.find({"project_id": ObjectId(project_id)}).sort("updated_at", -1).to_list(length=100)
    return [serialize_doc(doc) for doc in docs]


@router.get("/scenes")
async def get_scenes(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    docs = await db.scene_registry.find({"project_id": ObjectId(project_id)}).sort("created_at", 1).to_list(length=100)
    return [serialize_doc(doc) for doc in docs]


@router.get("/story-timeline")
async def get_story_timeline(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    docs = await db.timeline_entries.find({"project_id": ObjectId(project_id)}).sort(
        [("order", 1), ("created_at", 1)]
    ).to_list(length=2000)
    return [serialize_doc(doc) for doc in docs]


@router.get("/discussion")
async def get_discussion_messages(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    docs = await db.discussion_messages.find({"project_id": ObjectId(project_id)}).sort("created_at", 1).to_list(length=1000)
    return [serialize_doc(doc) for doc in docs]


@router.get("/story-vision")
async def get_story_vision(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    doc = await db.story_visions.find_one({"project_id": ObjectId(project_id)})
    return serialize_doc(doc) if doc else {}


@router.put("/story-vision")
async def update_story_vision(project_id: str, payload: dict):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    pid = ObjectId(project_id)
    project = await db.projects.find_one({"_id": pid})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    allowed = {
        "premise", "genre", "themes", "target_length", "inspirations",
        "audience", "narrative_goals",
    }
    update = {key: value for key, value in payload.items() if key in allowed}
    if not update:
        raise HTTPException(status_code=400, detail="No Story Vision fields supplied")
    current = await db.story_visions.find_one({"project_id": pid})
    baseline = current or project
    update = {
        key: value
        for key, value in update.items()
        if baseline.get(key) != value
    }
    if not update:
        return serialize_doc(current or project)
    changed_fields = sorted(update)
    now = datetime.utcnow()
    if current:
        await db.story_vision_versions.insert_one({
            **{key: value for key, value in current.items() if key != "_id"},
            "story_vision_id": current["_id"],
            "versioned_at": now,
        })
    latest_cycle = await db.cycles.find_one({"project_id": pid}, sort=[("cycle_number", -1)])
    doc = {
        "project_id": pid,
        **update,
        "cycle_generated": int((latest_cycle or {}).get("cycle_number", 0)),
        "source_type": "user",
        "provider": "user",
        "model": "manual-edit",
        "updated_at": now,
    }
    await db.story_visions.update_one(
        {"project_id": pid},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    await db.projects.update_one(
        {"_id": pid},
        {"$set": {**update, "updated_at": now}},
    )
    bible = await rebuild_story_bible(db, project_id)
    await emit_project_event(
        db,
        project_id,
        "story_vision_updated",
        cycle_number=bible.get("cycle_number", 0),
        payload={
            "story_bible_version": bible.get("version"),
            "changed_fields": changed_fields,
        },
    )
    return bible["sections"]["story_vision"]


@router.get("/arcs")
async def get_story_arcs(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    docs = await db.story_arcs.find({"project_id": ObjectId(project_id)}).sort("order", 1).to_list(length=100)
    return [serialize_doc(doc) for doc in docs]


@router.get("/power-system")
async def get_power_system(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    doc = await db.power_systems.find_one({"project_id": ObjectId(project_id)})
    return serialize_doc(doc) if doc else {}


@router.get("/character-journeys")
async def get_character_journeys(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    docs = await db.character_journeys.find({"project_id": ObjectId(project_id)}).sort("character_name", 1).to_list(length=100)
    return [serialize_doc(doc) for doc in docs]


@router.get("/mysteries")
async def get_mysteries(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    docs = await db.mystery_registry.find({"project_id": ObjectId(project_id)}).sort("updated_at", -1).to_list(length=100)
    return [serialize_doc(doc) for doc in docs]


@router.get("/ai-insights")
async def get_ai_insights(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    doc = await db.ai_insights.find_one({"project_id": ObjectId(project_id)})
    return serialize_doc(doc) if doc else {}


@router.get("/factions")
async def get_factions(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    docs = await db.factions.find({"project_id": ObjectId(project_id)}).sort("name", 1).to_list(length=100)
    return [serialize_doc(doc) for doc in docs]


@router.get("/canon")
async def get_canon(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    return await get_canon_context(db, project_id)


@router.get("/story-bible")
async def get_story_bible(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    return await load_story_bible(db, project_id)


@router.get("/audit")
async def audit_project(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    if not await db.projects.find_one({"_id": ObjectId(project_id)}):
        raise HTTPException(status_code=404, detail="Project not found")
    return await audit_project_database(db, project_id)


@router.post("/test-results")
async def store_project_test_result(project_id: str, payload: dict):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    if not await db.projects.find_one({"_id": ObjectId(project_id)}):
        raise HTTPException(status_code=404, detail="Project not found")
    doc = {
        "project_id": ObjectId(project_id),
        "suite": str(payload.get("suite") or "production_e2e"),
        "status": str(payload.get("status") or "unknown"),
        "model": payload.get("model"),
        "provider": payload.get("provider"),
        "checks": payload.get("checks") or {},
        "notes": payload.get("notes") or [],
        "created_at": datetime.utcnow(),
    }
    result = await db.e2e_test_results.insert_one(doc)
    return {"id": str(result.inserted_id), "stored": True}


@router.post("/discussion/{message_id}/decision")
async def record_discussion_decision(project_id: str, message_id: str, payload: dict):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id) or not ObjectId.is_valid(message_id):
        raise HTTPException(status_code=400, detail="Invalid ID")
    action = str(payload.get("action", "")).lower().strip()
    if action not in {"approve", "reject", "modify", "discuss", "expand"}:
        raise HTTPException(status_code=400, detail="Unsupported action")
    message = await db.discussion_messages.find_one({"_id": ObjectId(message_id), "project_id": ObjectId(project_id)})
    if not message:
        raise HTTPException(status_code=404, detail="Discussion message not found")
    note = str(payload.get("note") or "").strip()
    now = datetime.utcnow()
    cycle_number = int(message.get("cycle_number") or message.get("cycle") or 1)
    if action == "approve" and message.get("contradiction_status") == "open":
        raise HTTPException(status_code=409, detail="Resolve canon contradictions before approval")
    if action in {"reject", "modify"} and not note:
        raise HTTPException(status_code=400, detail=f"{action.title()} requires a reason or revision")

    status_by_action = {
        "approve": "approved",
        "reject": "rejected",
        "modify": "revision_proposed",
        "discuss": "discussion_open",
        "expand": "expansion_queued",
    }
    decision = {
        "project_id": ObjectId(project_id),
        "message_id": ObjectId(message_id),
        "action": action,
        "status": status_by_action[action],
        "decision": note or message.get("summary") or message.get("content", "")[:2000],
        "answer": note,
        "source": "discussion_action",
        "source_id": message_id,
        "cycle_number": cycle_number,
        "updated_at": now,
        "created_at": now,
    }
    decision_result = await db.decision_registry.insert_one(decision)
    related: dict = {}
    if action == "approve":
        await upsert_canon_fact(
            db,
            project_id=project_id,
            fact=decision["decision"],
            source="discussion_action",
            source_id=message_id,
            cycle_number=cycle_number,
        )
    elif action == "modify":
        revision = {
            **{key: value for key, value in message.items() if key != "_id"},
            "parent_proposal_id": ObjectId(message_id),
            "summary": note,
            "content": note,
            "decision_status": "pending",
            "revision_number": int(message.get("revision_number") or 0) + 1,
            "revision_history": [
                *message.get("revision_history", []),
                {"summary": message.get("summary") or message.get("content", ""), "changed_at": now},
            ],
            "created_at": now,
            "updated_at": now,
        }
        revision_result = await db.discussion_messages.insert_one(revision)
        related["revision_proposal_id"] = str(revision_result.inserted_id)
    elif action == "discuss":
        thread_result = await db.discussion_threads.insert_one({
            "project_id": ObjectId(project_id),
            "proposal_id": ObjectId(message_id),
            "status": "open",
            "cycle_number": cycle_number,
            "messages": [{
                "author": "User",
                "role": "user",
                "content": note or f"Discuss proposal from {message.get('author', 'agent')}.",
                "created_at": now,
            }],
            "created_at": now,
            "updated_at": now,
        })
        related["discussion_thread_id"] = str(thread_result.inserted_id)
        task_result = await db.cycle_tasks.insert_one({
            "project_id": ObjectId(project_id),
            "parent_proposal_id": ObjectId(message_id),
            "task_type": "discussion_followup",
            "agent_name": message.get("author"),
            "instruction": note or f"Discuss the proposal further: {message.get('summary') or message.get('content', '')}",
            "status": "queued",
            "cycle_number": cycle_number + 1,
            "created_at": now,
        })
        related["cycle_task_id"] = str(task_result.inserted_id)
    elif action == "expand":
        task_result = await db.cycle_tasks.insert_one({
            "project_id": ObjectId(project_id),
            "parent_proposal_id": ObjectId(message_id),
            "task_type": "proposal_expansion",
            "agent_name": message.get("author"),
            "instruction": note or f"Expand proposal: {message.get('summary') or message.get('content', '')}",
            "status": "queued",
            "cycle_number": cycle_number + 1,
            "created_at": now,
        })
        related["cycle_task_id"] = str(task_result.inserted_id)

    await db.discussion_messages.update_one(
        {"_id": ObjectId(message_id)},
        {"$set": {
            "decision_action": action,
            "decision_status": status_by_action[action],
            "decision_note": note,
            "updated_at": now,
        }},
    )
    await db.audit_logs.insert_one({
        "project_id": ObjectId(project_id),
        "event_type": "discussion_decision",
        "action": action,
        "proposal_id": ObjectId(message_id),
        "decision_id": decision_result.inserted_id,
        "cycle_number": cycle_number,
        "details": related,
        "created_at": now,
    })
    bible = await rebuild_story_bible(db, project_id, cycle_number=cycle_number)
    await emit_project_event(
        db, project_id, "discussion_decision",
        cycle_number=cycle_number,
        payload={"action": action, "proposal_id": message_id, **related, "story_bible_version": bible.get("version")},
    )
    return {
        "message": "Decision recorded",
        "action": action,
        "status": status_by_action[action],
        "decision_id": str(decision_result.inserted_id),
        **related,
    }


@router.get("/legacy-scene-drafts")
async def get_scene_drafts(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    docs = await db.scene_drafts.find({"project_id": ObjectId(project_id)}).sort("created_at", 1).to_list(length=100)
    return [serialize_doc(doc) for doc in docs]


@router.post("/draft-scenes")
async def draft_scenes(project_id: str, payload: dict | None = None):
    from app.services.narrative_studio import narrative_studio_service
    from app.api.workflow import build_persistent_state
    from app.services.arc_development_service import arc_development_service

    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    project = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    arc_id = str((payload or {}).get("arc_id") or "")
    if not arc_id:
        raise HTTPException(
            status_code=400,
            detail="arc_id is required for readiness-gated scene planning",
        )
    try:
        development = await arc_development_service.evaluate(
            db, project_id, arc_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not development["draftable"]:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Arc is not mature enough for scene planning",
                "development": development,
            },
        )
    latest_cycle = await db.cycles.find_one({"project_id": ObjectId(project_id)}, sort=[("cycle_number", -1)])
    state = await build_persistent_state(db, project, project_id, str(latest_cycle["_id"]) if latest_cycle else None)
    state["target_arc_id"] = arc_id
    result = await narrative_studio_service.run(
        db,
        project_id=project_id,
        state=state,
        agent_names=["ScenePlannerAgent"],
    )
    await rebuild_story_bible(
        db,
        project_id,
        cycle_number=int(state.get("cycle_number") or 1),
    )
    return {
        "message": "Scene planning completed",
        "arc_id": arc_id,
        "development": development,
        "artifacts": result.get("artifacts", {}),
    }


@router.get("/relationships")
async def get_relationships(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    docs = await db.relationship_graphs.find({"project_id": ObjectId(project_id)}).sort("updated_at", -1).to_list(length=100)
    return [serialize_doc(doc) for doc in docs]


@router.get("/continuity")
async def get_continuity_reports(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    docs = await db.continuity_reports.find({"project_id": ObjectId(project_id)}).sort("created_at", -1).to_list(length=100)
    return [serialize_doc(doc) for doc in docs]


@router.get("/memory/search")
async def search_memory(project_id: str, q: str, top_k: int = 10):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    result = await memory_provider_service.recall(
        db, project_id, q, top_k=top_k, refresh_index=False, consumer="developer_memory_search"
    )
    return result["primary"]["hits"]


@router.get("/memory/index/status")
async def memory_index_status(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    return serialize_doc(await memory_incremental_index_service.get_status(db, project_id))


@router.post("/memory/index/process")
async def process_memory_index(project_id: str, limit: int = 32):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    return serialize_doc(await memory_incremental_index_service.process_pending(db, project_id, limit=min(max(limit, 1), 500)))


@router.post("/memory/index/rebuild")
async def rebuild_memory_index(project_id: str, dry_run: bool = False, resume: bool = True):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    return serialize_doc(await memory_incremental_index_service.rebuild(db, project_id, dry_run=dry_run, resume=resume))


@router.post("/memory/index/verify")
async def verify_memory_index(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    return serialize_doc(await memory_incremental_index_service.verify(db, project_id))


@router.get("/orchestration/latest")
async def get_latest_orchestration(project_id: str):
    from app.services.orchestration_service_v2 import orchestration_service_v2

    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    doc = await db.orchestration_plans.find_one(
        {"project_id": ObjectId(project_id)},
        sort=[("created_at", -1)],
    )
    return await orchestration_service_v2.get_plan(db, doc) if doc else {}


@router.get("/orchestration/history")
async def get_orchestration_history(project_id: str):
    from app.services.orchestration_service_v2 import orchestration_service_v2

    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    docs = await db.orchestration_plans.find(
        {"project_id": ObjectId(project_id)}
    ).sort("created_at", -1).to_list(length=50)
    return [
        await orchestration_service_v2.get_plan(db, doc)
        for doc in docs
    ]


@router.get("/context/latest")
async def get_latest_context_packet(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    doc = await db.context_packets.find_one({"project_id": ObjectId(project_id)}, sort=[("created_at", -1)])
    return serialize_doc(doc) if doc else {}


@router.get("/observability/latest")
async def get_latest_observability(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    docs = await db.observability_events.find({"project_id": ObjectId(project_id)}).sort("created_at", -1).to_list(length=25)
    return [serialize_doc(doc) for doc in docs]


@router.get("/cognition")
async def get_cognition_events(project_id: str):
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    docs = await db.cognition_events.find({"project_id": ObjectId(project_id)}).sort("created_at", 1).to_list(length=200)
    return [serialize_doc(doc) for doc in docs]
