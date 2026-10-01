"""Project-owned Phase 2A arc development and planning APIs."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable
from uuid import uuid4

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.core.database import Database
from app.services.arc_development_service import (
    CHECKLIST_STATUSES,
    DEVELOPMENT_STATUSES,
    FOCUS_ROLES,
    arc_development_service,
)
from app.services.project_intelligence_coordinator import project_intelligence_coordinator


router = APIRouter(prefix="/api/projects/{project_id}", tags=["arc-development"])

DEPENDENCY_TYPES = {
    "requires_arc",
    "follows_arc",
    "depends_on_reveal",
    "depends_on_artifact",
    "depends_on_character_growth",
    "depends_on_knowledge_state",
}
PLAN_STATUSES = {"planned", "approved", "drafted", "completed"}
FORESHADOW_NODE_TYPES = {"seed", "development", "reinforcement", "payoff"}
ARTIFACT_EVENT_TYPES = {
    "discovery",
    "ownership",
    "usage",
    "awakening",
    "hidden_ability",
    "destruction",
    "transfer",
    "relevance",
}
KNOWLEDGE_EVENT_TYPES = {
    "discovery",
    "misunderstanding",
    "confirmation",
    "reveal",
    "twist",
}
FORBIDDEN_PROSE_FIELDS = {
    "prose",
    "chapter_text",
    "scene_text",
    "draft_text",
    "dialogue",
    "manuscript",
}


def _serialize(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {
            ("id" if key == "_id" else key): _serialize(item)
            for key, item in value.items()
        }
    return value


def _list(value: Any) -> list:
    if value is None:
        return []
    if not isinstance(value, list):
        raise HTTPException(status_code=400, detail="Expected a list")
    return value


def _reject_prose(payload: Dict[str, Any]) -> None:
    forbidden = sorted(FORBIDDEN_PROSE_FIELDS.intersection(payload))
    if forbidden:
        raise HTTPException(
            status_code=400,
            detail=f"Phase 2A does not accept prose fields: {', '.join(forbidden)}",
        )


async def _project(db, project_id: str) -> tuple[ObjectId, Dict[str, Any]]:
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    pid = ObjectId(project_id)
    project = await db.projects.find_one({"_id": pid})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return pid, project


async def _arc(db, pid: ObjectId, arc_id: str) -> Dict[str, Any]:
    arc = await db.story_arcs.find_one({"project_id": pid, "arc_id": arc_id})
    if not arc:
        raise HTTPException(status_code=404, detail="Arc not found")
    return arc


async def _owned(
    db, pid: ObjectId, collection: str, key: str, value: str
) -> Dict[str, Any]:
    item = await db[collection].find_one({"project_id": pid, key: value})
    if not item:
        raise HTTPException(status_code=400, detail=f"Unknown {collection} link")
    return item


async def _validate_links(
    db,
    pid: ObjectId,
    collection: str,
    key: str,
    values: Iterable[str],
) -> None:
    normalized = {str(value) for value in values if value}
    if not normalized:
        return
    found = {
        item[key]
        for item in await db[collection].find(
            {"project_id": pid, key: {"$in": list(normalized)}}, {key: 1}
        ).to_list(length=2000)
    }
    missing = sorted(normalized - found)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown {collection} links: {', '.join(missing)}",
        )


async def _after_change(
    db,
    *,
    project_id: str,
    arc_id: str,
    event_type: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    report = await arc_development_service.evaluate(db, project_id, arc_id)
    await project_intelligence_coordinator.after_change(
        db,
        project_id,
        event_type,
        {**payload, "arc_id": arc_id, "maturity_score": report["maturity_score"]},
        touch_project=True,
    )
    return report


@router.get("/arcs/{arc_id}/development")
async def get_arc_development(project_id: str, arc_id: str):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    await _arc(db, pid, arc_id)
    return await arc_development_service.evaluate(db, project_id, arc_id)


@router.get("/arc-development")
async def get_all_arc_development(project_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    return await arc_development_service.evaluate_all(db, project_id)


@router.post("/arcs/{arc_id}/activate")
async def activate_arc(project_id: str, arc_id: str):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    await _arc(db, pid, arc_id)
    try:
        report = await arc_development_service.activate(db, project_id, arc_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await _after_change(
        db,
        project_id=project_id,
        arc_id=arc_id,
        event_type="arc_focus_changed",
        payload={"action": "activated"},
    )
    return report


@router.put("/arcs/{arc_id}/development-status")
async def update_development_status(project_id: str, arc_id: str, payload: dict):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    arc = await _arc(db, pid, arc_id)
    status = str(payload.get("development_status") or "").lower()
    if status not in DEVELOPMENT_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported development status")
    current = str(arc.get("development_status") or "idea").lower()
    current_index = DEVELOPMENT_STATUSES.index(current)
    next_index = DEVELOPMENT_STATUSES.index(status)
    if status != "archived" and abs(next_index - current_index) > 1:
        raise HTTPException(status_code=409, detail="Invalid lifecycle transition")
    if status == "active":
        return await activate_arc(project_id, arc_id)
    if status == "draftable":
        report = await arc_development_service.evaluate(db, project_id, arc_id)
        if not report["draftable"]:
            raise HTTPException(status_code=409, detail={"blockers": report["blockers"]})
    await db.story_arcs.update_one(
        {"_id": arc["_id"]},
        {"$set": {"development_status": status, "updated_at": datetime.utcnow()}},
    )
    report = await _after_change(
        db,
        project_id=project_id,
        arc_id=arc_id,
        event_type="arc_development_changed",
        payload={"action": "status", "development_status": status},
    )
    return report


@router.get("/arc-checklists")
async def get_arc_checklists(project_id: str, arc_id: str):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    await _arc(db, pid, arc_id)
    await arc_development_service.seed_default_checklist(db, project_id, arc_id)
    docs = await db.arc_checklists.find(
        {"project_id": pid, "arc_id": arc_id}
    ).sort([("priority", 1), ("category", 1), ("title", 1)]).to_list(length=1000)
    return [_serialize(doc) for doc in docs]


@router.post("/arc-checklists/seed")
async def seed_arc_checklists(project_id: str, payload: dict):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    arc_id = str(payload.get("arc_id") or "")
    await _arc(db, pid, arc_id)
    seeded = await arc_development_service.seed_default_checklist(
        db, project_id, arc_id, source="user"
    )
    report = await _after_change(
        db,
        project_id=project_id,
        arc_id=arc_id,
        event_type="arc_checklist_changed",
        payload={"action": "seeded", "count": seeded},
    )
    return {"seeded": seeded, "development": report}


@router.post("/arc-checklists")
async def create_arc_checklist(project_id: str, payload: dict):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    arc_id = str(payload.get("arc_id") or "")
    await _arc(db, pid, arc_id)
    try:
        normalized = arc_development_service.normalize_checklist(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    now = datetime.utcnow()
    doc = {
        "project_id": pid,
        "arc_id": arc_id,
        "item_id": str(payload.get("item_id") or uuid4()),
        **normalized,
        "source": str(payload.get("source") or "user"),
        "created_at": now,
        "updated_at": now,
    }
    result = await db.arc_checklists.insert_one(doc)
    doc["_id"] = result.inserted_id
    report = await _after_change(
        db,
        project_id=project_id,
        arc_id=arc_id,
        event_type="arc_checklist_changed",
        payload={"action": "created", "item_id": doc["item_id"]},
    )
    return {**_serialize(doc), "development": report}


@router.put("/arc-checklists/{item_id}")
async def update_arc_checklist(project_id: str, item_id: str, payload: dict):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    existing = await db.arc_checklists.find_one(
        {"project_id": pid, "item_id": item_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    try:
        normalized = arc_development_service.normalize_checklist(
            {**existing, **payload}
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.arc_checklists.update_one(
        {"_id": existing["_id"]},
        {"$set": {**normalized, "updated_at": datetime.utcnow()}},
    )
    report = await _after_change(
        db,
        project_id=project_id,
        arc_id=existing["arc_id"],
        event_type="arc_checklist_changed",
        payload={"action": "updated", "item_id": item_id},
    )
    return {
        **_serialize(await db.arc_checklists.find_one({"_id": existing["_id"]})),
        "development": report,
    }


@router.delete("/arc-checklists/{item_id}")
async def delete_arc_checklist(project_id: str, item_id: str):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    existing = await db.arc_checklists.find_one(
        {"project_id": pid, "item_id": item_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    await db.arc_checklists.delete_one({"_id": existing["_id"]})
    report = await _after_change(
        db,
        project_id=project_id,
        arc_id=existing["arc_id"],
        event_type="arc_checklist_changed",
        payload={"action": "deleted", "item_id": item_id},
    )
    return {"deleted": True, "development": report}


@router.get("/arc-dependencies")
async def get_arc_dependencies(project_id: str, arc_id: str):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    await _arc(db, pid, arc_id)
    await arc_development_service.validate_dependencies(db, project_id, arc_id)
    docs = await db.arc_dependencies.find(
        {"project_id": pid, "arc_id": arc_id}
    ).sort("created_at", 1).to_list(length=1000)
    return [_serialize(doc) for doc in docs]


@router.post("/arc-dependencies")
async def create_arc_dependency(project_id: str, payload: dict):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    arc_id = str(payload.get("arc_id") or "")
    dependency_type = str(payload.get("dependency_type") or "")
    target_id = str(payload.get("target_id") or "")
    await _arc(db, pid, arc_id)
    if dependency_type not in DEPENDENCY_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported dependency type")
    if not target_id:
        raise HTTPException(status_code=400, detail="target_id is required")
    if dependency_type in {"requires_arc", "follows_arc"}:
        await _arc(db, pid, target_id)
        if target_id == arc_id:
            raise HTTPException(status_code=400, detail="Arc cannot depend on itself")
    now = datetime.utcnow()
    doc = {
        "project_id": pid,
        "dependency_id": str(payload.get("dependency_id") or uuid4()),
        "arc_id": arc_id,
        "dependency_type": dependency_type,
        "target_id": target_id,
        "required_state": str(payload.get("required_state") or ""),
        "blocking": bool(payload.get("blocking", True)),
        "status": "pending",
        "evidence": _list(payload.get("evidence")),
        "created_at": now,
        "updated_at": now,
    }
    result = await db.arc_dependencies.insert_one(doc)
    doc["_id"] = result.inserted_id
    report = await _after_change(
        db,
        project_id=project_id,
        arc_id=arc_id,
        event_type="arc_dependency_changed",
        payload={"action": "created", "dependency_id": doc["dependency_id"]},
    )
    return {**_serialize(doc), "development": report}


@router.put("/arc-dependencies/{dependency_id}")
async def update_arc_dependency(project_id: str, dependency_id: str, payload: dict):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    existing = await db.arc_dependencies.find_one(
        {"project_id": pid, "dependency_id": dependency_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Dependency not found")
    patch = {
        key: payload[key]
        for key in ["required_state", "blocking", "evidence"]
        if key in payload
    }
    if "evidence" in patch:
        patch["evidence"] = _list(patch["evidence"])
    patch["updated_at"] = datetime.utcnow()
    await db.arc_dependencies.update_one({"_id": existing["_id"]}, {"$set": patch})
    report = await _after_change(
        db,
        project_id=project_id,
        arc_id=existing["arc_id"],
        event_type="arc_dependency_changed",
        payload={"action": "updated", "dependency_id": dependency_id},
    )
    return {
        **_serialize(await db.arc_dependencies.find_one({"_id": existing["_id"]})),
        "development": report,
    }


def _plan_status(value: Any) -> str:
    status = str(value or "planned").lower()
    if status not in PLAN_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported planning status")
    return status


@router.get("/chapter-plans")
async def get_chapter_plans(project_id: str, arc_id: str | None = None):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    query: Dict[str, Any] = {"project_id": pid}
    if arc_id:
        await _arc(db, pid, arc_id)
        query["arc_id"] = arc_id
    docs = await db.chapter_plans.find(query).sort("chapter_number", 1).to_list(
        length=2000
    )
    return [_serialize(doc) for doc in docs]


@router.post("/chapter-plans")
async def create_chapter_plan(project_id: str, payload: dict):
    _reject_prose(payload)
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    arc_id = str(payload.get("arc_id") or "")
    await _arc(db, pid, arc_id)
    number = int(payload.get("chapter_number") or 0)
    if number <= 0:
        raise HTTPException(status_code=400, detail="chapter_number must be positive")
    knowledge = _list(payload.get("knowledge_changes"))
    artifacts = _list(payload.get("artifact_ids"))
    foreshadow = _list(payload.get("foreshadow_ids"))
    timeline = _list(payload.get("timeline_entry_ids"))
    await _validate_links(db, pid, "knowledge_entries", "entry_id", knowledge)
    await _validate_links(db, pid, "artifact_registry", "artifact_id", artifacts)
    await _validate_links(db, pid, "foreshadow_registry_v2", "entry_id", foreshadow)
    await _validate_links(db, pid, "timeline_entries", "entry_id", timeline)
    now = datetime.utcnow()
    doc = {
        "project_id": pid,
        "chapter_plan_id": str(payload.get("chapter_plan_id") or uuid4()),
        "arc_id": arc_id,
        "chapter_number": number,
        "title": str(payload.get("title") or f"Chapter {number}"),
        "purpose": str(payload.get("purpose") or ""),
        "conflict": str(payload.get("conflict") or ""),
        "character_focus": _list(payload.get("character_focus")),
        "knowledge_changes": knowledge,
        "artifact_ids": artifacts,
        "foreshadow_ids": foreshadow,
        "timeline_entry_ids": timeline,
        "status": _plan_status(payload.get("status")),
        "created_at": now,
        "updated_at": now,
    }
    try:
        result = await db.chapter_plans.insert_one(doc)
    except Exception as exc:
        raise HTTPException(status_code=409, detail="Chapter plan already exists") from exc
    doc["_id"] = result.inserted_id
    report = await _after_change(
        db,
        project_id=project_id,
        arc_id=arc_id,
        event_type="chapter_plan_changed",
        payload={"action": "created", "chapter_plan_id": doc["chapter_plan_id"]},
    )
    return {**_serialize(doc), "development": report}


@router.put("/chapter-plans/{chapter_plan_id}")
async def update_chapter_plan(project_id: str, chapter_plan_id: str, payload: dict):
    _reject_prose(payload)
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    existing = await db.chapter_plans.find_one(
        {"project_id": pid, "chapter_plan_id": chapter_plan_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Chapter plan not found")
    allowed = {
        "title",
        "purpose",
        "conflict",
        "character_focus",
        "knowledge_changes",
        "artifact_ids",
        "foreshadow_ids",
        "timeline_entry_ids",
        "status",
    }
    patch = {key: payload[key] for key in allowed if key in payload}
    for field in [
        "character_focus",
        "knowledge_changes",
        "artifact_ids",
        "foreshadow_ids",
        "timeline_entry_ids",
    ]:
        if field in patch:
            patch[field] = _list(patch[field])
    if "status" in patch:
        patch["status"] = _plan_status(patch["status"])
    await _validate_links(
        db, pid, "knowledge_entries", "entry_id", patch.get("knowledge_changes") or []
    )
    await _validate_links(
        db, pid, "artifact_registry", "artifact_id", patch.get("artifact_ids") or []
    )
    patch["updated_at"] = datetime.utcnow()
    await db.chapter_plans.update_one({"_id": existing["_id"]}, {"$set": patch})
    report = await _after_change(
        db,
        project_id=project_id,
        arc_id=existing["arc_id"],
        event_type="chapter_plan_changed",
        payload={"action": "updated", "chapter_plan_id": chapter_plan_id},
    )
    return {
        **_serialize(await db.chapter_plans.find_one({"_id": existing["_id"]})),
        "development": report,
    }


@router.get("/scene-plans-v2")
async def get_scene_plans_v2(
    project_id: str, arc_id: str | None = None, chapter_plan_id: str | None = None
):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    query: Dict[str, Any] = {"project_id": pid}
    if arc_id:
        await _arc(db, pid, arc_id)
        query["arc_id"] = arc_id
    if chapter_plan_id:
        await _owned(db, pid, "chapter_plans", "chapter_plan_id", chapter_plan_id)
        query["chapter_plan_id"] = chapter_plan_id
    docs = await db.scene_plans.find(query).to_list(length=5000)
    chapter_ids = list({doc.get("chapter_plan_id") for doc in docs if doc.get("chapter_plan_id")})
    chapter_rows = await db.chapter_plans.find(
        {"project_id": pid, "chapter_plan_id": {"$in": chapter_ids}},
        {"chapter_plan_id": 1, "chapter_number": 1},
    ).to_list(length=5000)
    chapter_numbers = {
        str(item.get("chapter_plan_id")): int(item.get("chapter_number") or 0)
        for item in chapter_rows
    }
    docs.sort(
        key=lambda doc: (
            chapter_numbers.get(str(doc.get("chapter_plan_id")), 10**9),
            int(doc.get("order") or 0),
            str(doc.get("title") or "").casefold(),
        )
    )
    return [_serialize(doc) for doc in docs]


@router.post("/scene-plans-v2")
async def create_scene_plan_v2(project_id: str, payload: dict):
    _reject_prose(payload)
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    arc_id = str(payload.get("arc_id") or "")
    chapter_plan_id = str(payload.get("chapter_plan_id") or "")
    await _arc(db, pid, arc_id)
    chapter = await _owned(
        db, pid, "chapter_plans", "chapter_plan_id", chapter_plan_id
    )
    if chapter["arc_id"] != arc_id:
        raise HTTPException(status_code=400, detail="Scene and chapter arc mismatch")
    now = datetime.utcnow()
    doc = {
        "project_id": pid,
        "scene_id": str(payload.get("scene_id") or uuid4()),
        "arc_id": arc_id,
        "chapter_plan_id": chapter_plan_id,
        "title": str(payload.get("title") or "Untitled scene plan"),
        "purpose": str(payload.get("purpose") or ""),
        "conflict": str(payload.get("conflict") or ""),
        "outcome": str(payload.get("outcome") or ""),
        "character_focus": _list(payload.get("character_focus")),
        "character_change": str(payload.get("character_change") or ""),
        "knowledge_changes": _list(payload.get("knowledge_changes")),
        "foreshadow_links": _list(payload.get("foreshadow_links")),
        "artifact_interactions": _list(payload.get("artifact_interactions")),
        "timeline_impacts": _list(payload.get("timeline_impacts")),
        "status": _plan_status(payload.get("status")),
        "order": int(payload.get("order") or 0),
        "created_at": now,
        "updated_at": now,
    }
    await _validate_links(
        db, pid, "knowledge_entries", "entry_id", doc["knowledge_changes"]
    )
    await _validate_links(
        db, pid, "foreshadow_registry_v2", "entry_id", doc["foreshadow_links"]
    )
    await _validate_links(
        db, pid, "artifact_registry", "artifact_id", doc["artifact_interactions"]
    )
    await _validate_links(
        db, pid, "timeline_entries", "entry_id", doc["timeline_impacts"]
    )
    result = await db.scene_plans.insert_one(doc)
    doc["_id"] = result.inserted_id
    report = await _after_change(
        db,
        project_id=project_id,
        arc_id=arc_id,
        event_type="scene_plan_changed",
        payload={"action": "created", "scene_id": doc["scene_id"]},
    )
    return {**_serialize(doc), "development": report}


@router.put("/scene-plans-v2/{scene_id}")
async def update_scene_plan_v2(project_id: str, scene_id: str, payload: dict):
    _reject_prose(payload)
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    existing = await db.scene_plans.find_one(
        {"project_id": pid, "scene_id": scene_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Scene plan not found")
    allowed = {
        "title",
        "purpose",
        "conflict",
        "outcome",
        "character_focus",
        "character_change",
        "knowledge_changes",
        "foreshadow_links",
        "artifact_interactions",
        "timeline_impacts",
        "status",
        "order",
    }
    patch = {key: payload[key] for key in allowed if key in payload}
    for field in [
        "character_focus",
        "knowledge_changes",
        "foreshadow_links",
        "artifact_interactions",
        "timeline_impacts",
    ]:
        if field in patch:
            patch[field] = _list(patch[field])
    if "status" in patch:
        patch["status"] = _plan_status(patch["status"])
    patch["updated_at"] = datetime.utcnow()
    await db.scene_plans.update_one({"_id": existing["_id"]}, {"$set": patch})
    report = await _after_change(
        db,
        project_id=project_id,
        arc_id=existing["arc_id"],
        event_type="scene_plan_changed",
        payload={"action": "updated", "scene_id": scene_id},
    )
    return {
        **_serialize(await db.scene_plans.find_one({"_id": existing["_id"]})),
        "development": report,
    }


@router.get("/power-progressions")
async def get_power_progressions(project_id: str, arc_id: str | None = None):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    query: Dict[str, Any] = {"project_id": pid}
    if arc_id:
        await _arc(db, pid, arc_id)
        query["arc_id"] = arc_id
    docs = await db.power_progressions.find(query).sort(
        [("arc_id", 1), ("character", 1)]
    ).to_list(length=1000)
    return [_serialize(doc) for doc in docs]


@router.post("/power-progressions")
async def upsert_power_progression(project_id: str, payload: dict):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    arc_id = str(payload.get("arc_id") or "")
    character = str(payload.get("character") or "").strip()
    await _arc(db, pid, arc_id)
    new_abilities = _list(payload.get("new_abilities"))
    mastered = _list(payload.get("mastered_abilities"))
    start = str(payload.get("starting_power") or "")
    end = str(payload.get("ending_power") or "")
    if end and end != start and not (new_abilities or mastered):
        raise HTTPException(
            status_code=400,
            detail="Power increase requires new or mastered ability evidence",
        )
    now = datetime.utcnow()
    doc = {
        "project_id": pid,
        "arc_id": arc_id,
        "character": character,
        "starting_power": start,
        "ending_power": end,
        "new_abilities": new_abilities,
        "mastered_abilities": mastered,
        "limitations": _list(payload.get("limitations")),
        "costs": _list(payload.get("costs")),
        "future_evolution": str(payload.get("future_evolution") or ""),
        "updated_at": now,
    }
    await db.power_progressions.update_one(
        {"project_id": pid, "arc_id": arc_id, "character": character},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    report = await _after_change(
        db,
        project_id=project_id,
        arc_id=arc_id,
        event_type="power_progression_changed",
        payload={"action": "upserted", "character": character},
    )
    return {
        **_serialize(
            await db.power_progressions.find_one(
                {"project_id": pid, "arc_id": arc_id, "character": character}
            )
        ),
        "development": report,
    }


async def _create_evolution(
    *,
    project_id: str,
    payload: dict,
    collection: str,
    id_key: str,
    parent_collection: str,
    parent_key: str,
    parent_payload_key: str,
    event_types: set[str],
    event_name: str,
):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    arc_id = str(payload.get("arc_id") or "")
    await _arc(db, pid, arc_id)
    parent_id = str(payload.get(parent_payload_key) or "")
    await _owned(db, pid, parent_collection, parent_key, parent_id)
    event_type = str(payload.get("event_type") or "").lower()
    if event_type not in event_types:
        raise HTTPException(status_code=400, detail="Unsupported evolution event")
    chapter_plan_id = str(payload.get("chapter_plan_id") or "") or None
    if chapter_plan_id:
        chapter = await _owned(
            db, pid, "chapter_plans", "chapter_plan_id", chapter_plan_id
        )
        if chapter["arc_id"] != arc_id:
            raise HTTPException(status_code=400, detail="Evolution chapter arc mismatch")
    now = datetime.utcnow()
    doc = {
        "project_id": pid,
        id_key: str(payload.get(id_key) or uuid4()),
        parent_payload_key: parent_id,
        "arc_id": arc_id,
        "chapter_plan_id": chapter_plan_id,
        "event_type": event_type,
        "summary": str(payload.get("summary") or ""),
        "from_state": str(payload.get("from_state") or ""),
        "to_state": str(payload.get("to_state") or ""),
        "order": int(payload.get("order") or 0),
        "evidence": _list(payload.get("evidence")),
        "created_at": now,
        "updated_at": now,
    }
    result = await db[collection].insert_one(doc)
    doc["_id"] = result.inserted_id
    report = await _after_change(
        db,
        project_id=project_id,
        arc_id=arc_id,
        event_type=event_name,
        payload={"action": "created", id_key: doc[id_key]},
    )
    return {**_serialize(doc), "development": report}


@router.get("/foreshadow-chains")
async def get_foreshadow_chains(project_id: str, arc_id: str | None = None):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    query: Dict[str, Any] = {"project_id": pid}
    if arc_id:
        query["arc_id"] = arc_id
    docs = await db.foreshadow_chains.find(query).sort("order", 1).to_list(
        length=2000
    )
    return [_serialize(doc) for doc in docs]


@router.post("/foreshadow-chains")
async def create_foreshadow_chain_node(project_id: str, payload: dict):
    return await _create_evolution(
        project_id=project_id,
        payload=payload,
        collection="foreshadow_chains",
        id_key="chain_node_id",
        parent_collection="foreshadow_registry_v2",
        parent_key="entry_id",
        parent_payload_key="foreshadow_id",
        event_types=FORESHADOW_NODE_TYPES,
        event_name="foreshadow_chain_changed",
    )


@router.get("/artifact-evolutions")
async def get_artifact_evolutions(project_id: str, arc_id: str | None = None):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    query: Dict[str, Any] = {"project_id": pid}
    if arc_id:
        query["arc_id"] = arc_id
    docs = await db.artifact_evolutions.find(query).sort("order", 1).to_list(
        length=2000
    )
    return [_serialize(doc) for doc in docs]


@router.post("/artifact-evolutions")
async def create_artifact_evolution(project_id: str, payload: dict):
    return await _create_evolution(
        project_id=project_id,
        payload=payload,
        collection="artifact_evolutions",
        id_key="evolution_id",
        parent_collection="artifact_registry",
        parent_key="artifact_id",
        parent_payload_key="artifact_id",
        event_types=ARTIFACT_EVENT_TYPES,
        event_name="artifact_evolution_changed",
    )


@router.get("/knowledge-evolutions")
async def get_knowledge_evolutions(project_id: str, arc_id: str | None = None):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    query: Dict[str, Any] = {"project_id": pid}
    if arc_id:
        query["arc_id"] = arc_id
    docs = await db.knowledge_evolutions.find(query).sort("order", 1).to_list(
        length=2000
    )
    return [_serialize(doc) for doc in docs]


@router.post("/knowledge-evolutions")
async def create_knowledge_evolution(project_id: str, payload: dict):
    return await _create_evolution(
        project_id=project_id,
        payload=payload,
        collection="knowledge_evolutions",
        id_key="evolution_id",
        parent_collection="knowledge_entries",
        parent_key="entry_id",
        parent_payload_key="knowledge_entry_id",
        event_types=KNOWLEDGE_EVENT_TYPES,
        event_name="knowledge_evolution_changed",
    )


@router.get("/story-room")
async def get_story_room(project_id: str):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    arcs = await db.story_arcs.find(
        {"project_id": pid}, {"arc_id": 1, "title": 1, "focus_role": 1}
    ).sort("order", 1).to_list(length=1000)
    current = next((arc for arc in arcs if arc.get("focus_role") == "current"), None)
    current_arc_id = (current or {}).get("arc_id")
    checklist_query: Dict[str, Any] = {
        "project_id": pid,
        "status": {"$nin": list(CHECKLIST_STATUSES.intersection({"approved", "completed", "waived"}))},
    }
    if current_arc_id:
        checklist_query["arc_id"] = current_arc_id
    open_items = await db.arc_checklists.find(checklist_query).sort(
        [("priority", 1), ("updated_at", -1)]
    ).to_list(length=200)
    blocked = await db.arc_dependencies.find(
        {
            "project_id": pid,
            **({"arc_id": current_arc_id} if current_arc_id else {}),
            "blocking": True,
            "status": {"$ne": "satisfied"},
        }
    ).sort("updated_at", -1).to_list(length=200)
    discussions = await db.discussion_messages.find(
        {"project_id": pid, "decision_status": {"$in": [None, "pending"]}}
    ).sort("created_at", -1).to_list(length=100)
    proposals = [
        item
        for item in discussions
        if item.get("role") == "agent" or item.get("structured_output")
    ]
    suggestions = [
        {
            "type": "checklist",
            "title": item.get("title"),
            "priority": item.get("priority"),
            "arc_id": item.get("arc_id"),
        }
        for item in open_items
    ]
    scene_drafts = await db.scene_drafts.find(
        {"project_id": pid, "active": True}
    ).sort("created_at", -1).to_list(length=500)
    chapter_drafts = await db.chapter_drafts.find(
        {"project_id": pid, "active": True}
    ).sort("created_at", -1).to_list(length=500)
    continuity_warnings = await db.continuity_reports.find(
        {
            "project_id": pid,
            "subject_type": {"$in": ["scene_draft", "chapter_draft"]},
            "result": {"$in": ["WARNING", "FAIL"]},
        }
    ).sort("created_at", -1).to_list(length=500)
    draft_history_count = (
        await db.scene_drafts.count_documents({"project_id": pid})
        + await db.chapter_drafts.count_documents({"project_id": pid})
    )
    editorial_reports = await db.editorial_reports.find(
        {"project_id": pid}
    ).sort("created_at", -1).to_list(length=1000)
    reviewed_keys = {
        (
            str(item.get("subject_type")),
            str(item.get("subject_id")),
            str(item.get("report_type")),
        )
        for item in editorial_reports
    }
    editorial_queue = []
    for subject_type, drafts in (
        ("scene", scene_drafts),
        ("chapter", chapter_drafts),
    ):
        for draft in drafts:
            if draft.get("status") != "approved":
                continue
            missing = [
                report_type
                for report_type in ("editorial", "dialogue")
                if (subject_type, str(draft.get("draft_id")), report_type)
                not in reviewed_keys
            ]
            if missing:
                editorial_queue.append(
                    {
                        "subject_type": subject_type,
                        "subject_id": draft.get("draft_id"),
                        "arc_id": draft.get("arc_id"),
                        "chapter_plan_id": draft.get("chapter_plan_id"),
                        "scene_id": draft.get("scene_id"),
                        "missing_reviews": missing,
                    }
                )
    revision_queue = await db.revision_branches.find(
        {
            "project_id": pid,
            "status": {"$in": ["draft", "review"]},
        }
    ).sort("updated_at", -1).to_list(length=500)
    editorial_blockers = [
        item
        for item in editorial_reports
        if item.get("blockers") or int(item.get("score") or 0) < 60
    ]
    manuscripts = await db.manuscripts.find(
        {"project_id": pid, "active": True}
    ).sort("updated_at", -1).to_list(length=100)
    manuscript_reports = await db.manuscript_reports.find(
        {"project_id": pid}
    ).sort("created_at", -1).to_list(length=1000)
    reviewed_manuscript_versions = {
        str(item.get("version_id"))
        for item in manuscript_reports
        if item.get("report_type") == "manuscript_review"
    }
    manuscript_queue = [
        item
        for item in manuscripts
        if item.get("status") in {"draft", "review", "validated"}
        or str(item.get("current_version_id")) not in reviewed_manuscript_versions
    ]
    canon_conflicts = await db.canon_conflicts.find(
        {"project_id": pid, "status": {"$in": ["open", "acknowledged"]}}
    ).sort("last_seen_at", -1).to_list(length=500)
    latest_canon_review = await db.manuscript_reports.find_one(
        {"project_id": pid, "report_type": "canon_review"},
        sort=[("created_at", -1)],
    )
    canon_queue = [
        {
            "type": "canon_review",
            "title": "Review active canon authority",
            "last_reviewed_at": (latest_canon_review or {}).get("created_at"),
            "open_conflicts": len(canon_conflicts),
        }
    ] if canon_conflicts or not latest_canon_review else []
    return _serialize(
        {
            "project_id": pid,
            "current_arc": current,
            "active_discussions": discussions,
            "open_planning_items": open_items,
            "blocked_items": blocked,
            "suggestions": suggestions,
            "agent_proposals": proposals,
            "draft_queue": [
                *[item for item in scene_drafts if item.get("status") == "draft"],
                *[item for item in chapter_drafts if item.get("status") == "draft"],
            ],
            "review_queue": [
                *[item for item in scene_drafts if item.get("status") == "review"],
                *[item for item in chapter_drafts if item.get("status") == "review"],
            ],
            "continuity_warnings": continuity_warnings,
            "editorial_queue": editorial_queue,
            "revision_queue": revision_queue,
            "editorial_blockers": editorial_blockers,
            "manuscript_queue": manuscript_queue,
            "canon_queue": canon_queue,
            "conflict_queue": canon_conflicts,
            "draft_approval_status": {
                "scene": {
                    status: sum(1 for item in scene_drafts if item.get("status") == status)
                    for status in ["draft", "review", "approved", "rejected", "archived"]
                },
                "chapter": {
                    status: sum(1 for item in chapter_drafts if item.get("status") == status)
                    for status in ["draft", "review", "approved", "rejected", "archived"]
                },
            },
            "generation_history": {"total_versions": draft_history_count},
            "generated_at": datetime.utcnow(),
        }
    )
