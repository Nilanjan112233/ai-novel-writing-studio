"""Project-owned Phase 1B planning ledgers and readiness APIs."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable
from uuid import uuid4

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query

from app.core.database import Database
from app.services.agent_memory_service import agent_memory_service
from app.services.project_intelligence_coordinator import project_intelligence_coordinator
from app.services.readiness_service import readiness_service


router = APIRouter(prefix="/api/projects/{project_id}", tags=["planning-v2"])

ARC_STATUSES = {"draft", "discussed", "approved", "active", "completed", "archived"}
TIMELINE_STATUSES = {"planned", "approved", "drafted", "completed"}
TIMELINE_CERTAINTY = {"known", "probable", "unknown"}
KNOWLEDGE_TYPES = {"WORLD_TRUTH", "READER_KNOWLEDGE", "CHARACTER_KNOWLEDGE"}
FORESHADOW_STATUSES = {"seeded", "developing", "paid_off", "abandoned"}


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


def _chapter_range(value: Any) -> list:
    values = _list(value)
    if values and len(values) != 2:
        raise HTTPException(
            status_code=400, detail="chapter_range must contain start and end"
        )
    return values


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


async def _validate_arc_ids(db, pid: ObjectId, arc_ids: Iterable[str]) -> None:
    normalized = {str(arc_id) for arc_id in arc_ids if arc_id}
    if not normalized:
        return
    found = {
        item["arc_id"]
        for item in await db.story_arcs.find(
            {"project_id": pid, "arc_id": {"$in": list(normalized)}},
            {"arc_id": 1},
        ).to_list(length=1000)
    }
    missing = sorted(normalized - found)
    if missing:
        raise HTTPException(
            status_code=400, detail=f"Unknown linked arc IDs: {', '.join(missing)}"
        )


async def _validate_entry_ids(
    db, pid: ObjectId, collection: str, key: str, values: Iterable[str]
) -> None:
    normalized = {str(value) for value in values if value}
    if not normalized:
        return
    found = {
        item[key]
        for item in await db[collection].find(
            {"project_id": pid, key: {"$in": list(normalized)}}, {key: 1}
        ).to_list(length=1000)
    }
    missing = sorted(normalized - found)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown linked {collection} IDs: {', '.join(missing)}",
        )


async def _after_change(
    db,
    *,
    project_id: str,
    event_type: str,
    payload: Dict[str, Any],
    arc_id: str | None = None,
) -> None:
    if arc_id:
        try:
            await readiness_service.evaluate(db, project_id, arc_id=arc_id)
        except ValueError:
            pass
    await project_intelligence_coordinator.after_change(
        db, project_id, event_type, payload, touch_project=True,
    )


@router.get("/readiness")
async def get_readiness(project_id: str, arc_id: str | None = None):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    query: Dict[str, Any] = {"project_id": pid}
    if arc_id:
        await _arc(db, pid, arc_id)
        query["arc_id"] = arc_id
    docs = await db.story_readiness.find(query).sort(
        [("priority", 1), ("category", 1), ("title", 1)]
    ).to_list(length=1000)
    return [_serialize(doc) for doc in docs]


@router.get("/readiness/report")
async def get_readiness_report(project_id: str, arc_id: str | None = None):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await readiness_service.evaluate(db, project_id, arc_id=arc_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/readiness")
async def create_readiness(project_id: str, payload: dict):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    arc_id = str(payload.get("arc_id") or "") or None
    if arc_id:
        await _arc(db, pid, arc_id)
    try:
        item = readiness_service.normalize_item(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    now = datetime.utcnow()
    doc = {
        "project_id": pid,
        "item_id": str(payload.get("item_id") or uuid4()),
        "arc_id": arc_id,
        **{
            key: item[key]
            for key in [
                "category",
                "title",
                "description",
                "priority",
                "status",
                "evidence",
                "blocking",
            ]
        },
        "source": str(payload.get("source") or "user"),
        "created_at": now,
        "updated_at": now,
    }
    try:
        result = await db.story_readiness.insert_one(doc)
    except Exception as exc:
        raise HTTPException(status_code=409, detail="Readiness item already exists") from exc
    doc["_id"] = result.inserted_id
    await _after_change(
        db,
        project_id=project_id,
        event_type="readiness_changed",
        payload={"item_id": doc["item_id"], "action": "created", "arc_id": arc_id},
        arc_id=arc_id,
    )
    return _serialize(doc)


@router.put("/readiness/{item_id}")
async def update_readiness(project_id: str, item_id: str, payload: dict):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    existing = await db.story_readiness.find_one(
        {"project_id": pid, "item_id": item_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Readiness item not found")
    merged = {**existing, **payload}
    try:
        item = readiness_service.normalize_item(merged)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    arc_id = str(payload.get("arc_id", existing.get("arc_id")) or "") or None
    if arc_id:
        await _arc(db, pid, arc_id)
    patch = {
        key: item[key]
        for key in [
            "category",
            "title",
            "description",
            "priority",
            "status",
            "evidence",
            "blocking",
        ]
    }
    patch.update({"arc_id": arc_id, "updated_at": datetime.utcnow()})
    await db.story_readiness.update_one({"_id": existing["_id"]}, {"$set": patch})
    await _after_change(
        db,
        project_id=project_id,
        event_type="readiness_changed",
        payload={"item_id": item_id, "action": "updated", "arc_id": arc_id},
        arc_id=arc_id,
    )
    return _serialize(await db.story_readiness.find_one({"_id": existing["_id"]}))


@router.delete("/readiness/{item_id}")
async def delete_readiness(project_id: str, item_id: str):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    existing = await db.story_readiness.find_one(
        {"project_id": pid, "item_id": item_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Readiness item not found")
    await db.story_readiness.delete_one({"_id": existing["_id"]})
    await _after_change(
        db,
        project_id=project_id,
        event_type="readiness_changed",
        payload={"item_id": item_id, "action": "deleted"},
        arc_id=existing.get("arc_id"),
    )
    return {"deleted": True}


@router.post("/arcs")
async def create_arc(project_id: str, payload: dict):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    status = str(payload.get("approval_status") or "draft").lower()
    if status not in ARC_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported arc lifecycle status")
    development_status = str(payload.get("development_status") or "idea").lower()
    if development_status not in {
        "idea",
        "discussion",
        "outline",
        "development",
        "approved",
        "active",
        "draftable",
        "completed",
        "archived",
    }:
        raise HTTPException(status_code=400, detail="Unsupported arc development status")
    focus_role = str(payload.get("focus_role") or "future").lower()
    if focus_role not in {"current", "next", "future"}:
        raise HTTPException(status_code=400, detail="Unsupported arc focus role")
    now = datetime.utcnow()
    doc = {
        "project_id": pid,
        "arc_id": str(payload.get("arc_id") or uuid4()),
        "title": str(payload.get("title") or "Untitled Arc").strip(),
        "purpose": str(payload.get("purpose") or "").strip(),
        "goal": str(payload.get("goal") or "").strip(),
        "conflict": str(payload.get("conflict") or "").strip(),
        "stakes": str(payload.get("stakes") or "").strip(),
        "approval_status": status,
        "development_status": development_status,
        "focus_role": focus_role,
        "chapter_range": _chapter_range(payload.get("chapter_range") or []),
        "readiness_status": "NOT_READY",
        "drafting_eligible": False,
        "arc_maturity_score": 0,
        "maturity_threshold": 85,
        "maturity_details": {},
        "resolution_direction": str(payload.get("resolution_direction") or ""),
        "order": int(payload.get("order") or 1),
        "major_events": _list(payload.get("major_events")),
        "payoffs": _list(payload.get("payoffs")),
        "mysteries": _list(payload.get("mysteries")),
        "character_growth": _list(payload.get("character_growth")),
        "dependencies": _list(payload.get("dependencies")),
        "created_at": now,
        "updated_at": now,
    }
    await _validate_arc_ids(db, pid, doc["dependencies"])
    try:
        result = await db.story_arcs.insert_one(doc)
    except Exception as exc:
        raise HTTPException(status_code=409, detail="Arc already exists") from exc
    doc["_id"] = result.inserted_id
    report = await readiness_service.evaluate(
        db, project_id, arc_id=doc["arc_id"]
    )
    await _after_change(
        db,
        project_id=project_id,
        event_type="arc_changed",
        payload={"arc_id": doc["arc_id"], "action": "created"},
        arc_id=doc["arc_id"],
    )
    return {**_serialize(doc), "readiness_report": report}


@router.get("/arcs/{arc_id}")
async def get_arc(project_id: str, arc_id: str):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    return _serialize(await _arc(db, pid, arc_id))


@router.put("/arcs/{arc_id}")
async def update_arc(project_id: str, arc_id: str, payload: dict):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    existing = await _arc(db, pid, arc_id)
    allowed = {
        "title",
        "purpose",
        "goal",
        "conflict",
        "stakes",
        "approval_status",
        "chapter_range",
        "order",
        "major_events",
        "payoffs",
        "mysteries",
        "character_growth",
        "dependencies",
        "development_status",
        "focus_role",
        "resolution_direction",
    }
    patch = {key: value for key, value in payload.items() if key in allowed}
    if "approval_status" in patch:
        patch["approval_status"] = str(patch["approval_status"]).lower()
        if patch["approval_status"] not in ARC_STATUSES:
            raise HTTPException(status_code=400, detail="Unsupported arc lifecycle status")
    if "development_status" in patch:
        patch["development_status"] = str(patch["development_status"]).lower()
        if patch["development_status"] not in {
            "idea",
            "discussion",
            "outline",
            "development",
            "approved",
            "active",
            "draftable",
            "completed",
            "archived",
        }:
            raise HTTPException(status_code=400, detail="Unsupported arc development status")
    if "focus_role" in patch:
        patch["focus_role"] = str(patch["focus_role"]).lower()
        if patch["focus_role"] not in {"current", "next", "future"}:
            raise HTTPException(status_code=400, detail="Unsupported arc focus role")
    if "chapter_range" in patch:
        patch["chapter_range"] = _chapter_range(patch["chapter_range"])
    for field in [
        "major_events",
        "payoffs",
        "mysteries",
        "character_growth",
        "dependencies",
    ]:
        if field in patch:
            patch[field] = _list(patch[field])
    await _validate_arc_ids(db, pid, patch.get("dependencies") or [])
    patch["updated_at"] = datetime.utcnow()
    await db.story_arcs.update_one({"_id": existing["_id"]}, {"$set": patch})
    report = await readiness_service.evaluate(db, project_id, arc_id=arc_id)
    await _after_change(
        db,
        project_id=project_id,
        event_type="arc_changed",
        payload={"arc_id": arc_id, "action": "updated", "changed_fields": sorted(patch)},
        arc_id=arc_id,
    )
    return {
        **_serialize(await db.story_arcs.find_one({"_id": existing["_id"]})),
        "readiness_report": report,
    }


@router.get("/arcs/{arc_id}/drafting-eligibility")
async def get_drafting_eligibility(project_id: str, arc_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await readiness_service.evaluate(db, project_id, arc_id=arc_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/timeline-v2")
async def get_timeline_v2(project_id: str, arc_id: str | None = None):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    query: Dict[str, Any] = {"project_id": pid}
    if arc_id:
        await _arc(db, pid, arc_id)
        query["arc_id"] = arc_id
    docs = await db.timeline_entries.find(query).sort(
        [("order", 1), ("created_at", 1)]
    ).to_list(length=2000)
    return [_serialize(doc) for doc in docs]


def _timeline_doc(payload: dict, *, partial: bool = False) -> Dict[str, Any]:
    patch: Dict[str, Any] = {}
    fields = [
        "arc_id",
        "title",
        "summary",
        "importance",
        "status",
        "certainty",
        "dependencies",
        "chapter_range",
        "order",
    ]
    for field in fields:
        if not partial or field in payload:
            patch[field] = payload.get(field)
    if "status" in patch:
        patch["status"] = str(patch["status"] or "planned").lower()
        if patch["status"] not in TIMELINE_STATUSES:
            raise HTTPException(status_code=400, detail="Unsupported timeline status")
    if "certainty" in patch:
        patch["certainty"] = str(patch["certainty"] or "unknown").lower()
        if patch["certainty"] not in TIMELINE_CERTAINTY:
            raise HTTPException(status_code=400, detail="Unsupported timeline certainty")
    if "dependencies" in patch:
        patch["dependencies"] = _list(patch["dependencies"])
    if "chapter_range" in patch:
        patch["chapter_range"] = _chapter_range(patch["chapter_range"] or [])
    if "order" in patch:
        patch["order"] = int(patch["order"] or 0)
    if "title" in patch:
        patch["title"] = str(patch["title"] or "Unknown future event").strip()
    if "summary" in patch:
        patch["summary"] = str(patch["summary"] or "").strip()
    if "importance" in patch:
        patch["importance"] = str(patch["importance"] or "major").strip()
    return patch


@router.post("/timeline-v2")
async def create_timeline_v2(project_id: str, payload: dict):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    patch = _timeline_doc(payload)
    arc_id = str(patch.get("arc_id") or "") or None
    if arc_id:
        await _arc(db, pid, arc_id)
    await _validate_entry_ids(
        db, pid, "timeline_entries", "entry_id", patch.get("dependencies") or []
    )
    now = datetime.utcnow()
    doc = {
        "project_id": pid,
        "entry_id": str(payload.get("entry_id") or uuid4()),
        **patch,
        "arc_id": arc_id,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.timeline_entries.insert_one(doc)
    doc["_id"] = result.inserted_id
    await _after_change(
        db,
        project_id=project_id,
        event_type="timeline_v2_changed",
        payload={"entry_id": doc["entry_id"], "action": "created", "arc_id": arc_id},
        arc_id=arc_id,
    )
    return _serialize(doc)


@router.put("/timeline-v2/{entry_id}")
async def update_timeline_v2(project_id: str, entry_id: str, payload: dict):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    existing = await db.timeline_entries.find_one(
        {"project_id": pid, "entry_id": entry_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Timeline entry not found")
    patch = _timeline_doc(payload, partial=True)
    arc_id = str(patch.get("arc_id", existing.get("arc_id")) or "") or None
    if arc_id:
        await _arc(db, pid, arc_id)
    await _validate_entry_ids(
        db, pid, "timeline_entries", "entry_id", patch.get("dependencies") or []
    )
    patch.update({"arc_id": arc_id, "updated_at": datetime.utcnow()})
    await db.timeline_entries.update_one({"_id": existing["_id"]}, {"$set": patch})
    await _after_change(
        db,
        project_id=project_id,
        event_type="timeline_v2_changed",
        payload={"entry_id": entry_id, "action": "updated", "arc_id": arc_id},
        arc_id=arc_id,
    )
    return _serialize(await db.timeline_entries.find_one({"_id": existing["_id"]}))


@router.get("/character-progressions")
async def get_character_progressions(
    project_id: str, arc_id: str | None = None, character: str | None = None
):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    query: Dict[str, Any] = {"project_id": pid}
    if arc_id:
        query["arc_id"] = arc_id
    if character:
        query["character"] = character
    docs = await db.character_progressions.find(query).sort(
        [("arc_id", 1), ("character", 1)]
    ).to_list(length=1000)
    return [_serialize(doc) for doc in docs]


@router.post("/character-progressions")
async def upsert_character_progression(project_id: str, payload: dict):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    arc_id = str(payload.get("arc_id") or "")
    character = str(payload.get("character") or "").strip()
    if not arc_id or not character:
        raise HTTPException(status_code=400, detail="arc_id and character are required")
    await _arc(db, pid, arc_id)
    now = datetime.utcnow()
    fields = {
        "current_state": str(payload.get("current_state") or ""),
        "desired_state": str(payload.get("desired_state") or ""),
        "arc_start_state": str(
            payload.get("arc_start_state") or payload.get("current_state") or ""
        ),
        "arc_midpoint_state": str(payload.get("arc_midpoint_state") or ""),
        "arc_end_state": str(
            payload.get("arc_end_state") or payload.get("desired_state") or ""
        ),
        "emotional_growth": str(payload.get("emotional_growth") or ""),
        "maturity_growth": str(payload.get("maturity_growth") or ""),
        "power_growth": _list(payload.get("power_growth")),
        "relationship_growth": _list(payload.get("relationship_growth")),
        "belief_changes": _list(payload.get("belief_changes")),
        "goal_changes": _list(payload.get("goal_changes")),
        "skills": _list(payload.get("skills")),
        "powers": _list(payload.get("powers")),
        "beliefs": _list(payload.get("beliefs")),
        "relationships": _list(payload.get("relationships")),
        "maturity": payload.get("maturity"),
        "trauma": _list(payload.get("trauma")),
        "goals": _list(payload.get("goals")),
        "updated_at": now,
    }
    await db.character_progressions.update_one(
        {"project_id": pid, "arc_id": arc_id, "character": character},
        {
            "$set": {
                "project_id": pid,
                "arc_id": arc_id,
                "character": character,
                **fields,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    doc = await db.character_progressions.find_one(
        {"project_id": pid, "arc_id": arc_id, "character": character}
    )
    await _after_change(
        db,
        project_id=project_id,
        event_type="character_progression_changed",
        payload={"arc_id": arc_id, "character": character},
        arc_id=arc_id,
    )
    return _serialize(doc)


@router.get("/knowledge")
async def get_knowledge(
    project_id: str,
    knowledge_type: str | None = Query(default=None),
    arc_id: str | None = None,
):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    query: Dict[str, Any] = {"project_id": pid}
    if knowledge_type:
        normalized = knowledge_type.upper()
        if normalized not in KNOWLEDGE_TYPES:
            raise HTTPException(status_code=400, detail="Unsupported knowledge type")
        query["knowledge_type"] = normalized
    if arc_id:
        query["arc_id"] = arc_id
    docs = await db.knowledge_entries.find(query).sort(
        [("knowledge_type", 1), ("created_at", 1)]
    ).to_list(length=2000)
    return [_serialize(doc) for doc in docs]


def _knowledge_doc(payload: dict, *, partial: bool = False) -> Dict[str, Any]:
    fields = [
        "knowledge_type",
        "arc_id",
        "title",
        "content",
        "known_by",
        "not_known_by",
        "learned_how",
        "is_false",
        "confidence",
        "source",
        "source_id",
        "reveal_target",
        "world_truth_entry_id",
    ]
    patch = {
        field: payload.get(field)
        for field in fields
        if not partial or field in payload
    }
    if "knowledge_type" in patch:
        patch["knowledge_type"] = str(
            patch["knowledge_type"] or "WORLD_TRUTH"
        ).upper()
        if patch["knowledge_type"] not in KNOWLEDGE_TYPES:
            raise HTTPException(status_code=400, detail="Unsupported knowledge type")
    for field in ["known_by", "not_known_by"]:
        if field in patch:
            patch[field] = [str(item) for item in _list(patch[field]) if str(item)]
    if set(patch.get("known_by") or []) & set(patch.get("not_known_by") or []):
        raise HTTPException(
            status_code=400,
            detail="The same subject cannot know and not know one entry",
        )
    if "confidence" in patch:
        patch["confidence"] = max(0.0, min(float(patch["confidence"] or 0), 1.0))
    if "is_false" in patch:
        patch["is_false"] = bool(patch["is_false"])
    return patch


@router.post("/knowledge")
async def create_knowledge(project_id: str, payload: dict):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    patch = _knowledge_doc(payload)
    arc_id = str(patch.get("arc_id") or "") or None
    if arc_id:
        await _arc(db, pid, arc_id)
    truth_id = str(patch.get("world_truth_entry_id") or "") or None
    if truth_id:
        await _validate_entry_ids(
            db, pid, "knowledge_entries", "entry_id", [truth_id]
        )
    now = datetime.utcnow()
    doc = {
        "project_id": pid,
        "entry_id": str(payload.get("entry_id") or uuid4()),
        **patch,
        "arc_id": arc_id,
        "world_truth_entry_id": truth_id,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.knowledge_entries.insert_one(doc)
    doc["_id"] = result.inserted_id
    await _after_change(
        db,
        project_id=project_id,
        event_type="knowledge_changed",
        payload={"entry_id": doc["entry_id"], "action": "created", "arc_id": arc_id},
        arc_id=arc_id,
    )
    return _serialize(doc)


@router.put("/knowledge/{entry_id}")
async def update_knowledge(project_id: str, entry_id: str, payload: dict):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    existing = await db.knowledge_entries.find_one(
        {"project_id": pid, "entry_id": entry_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    patch = _knowledge_doc({**existing, **payload})
    arc_id = str(patch.get("arc_id") or "") or None
    if arc_id:
        await _arc(db, pid, arc_id)
    truth_id = str(patch.get("world_truth_entry_id") or "") or None
    if truth_id and truth_id != entry_id:
        await _validate_entry_ids(
            db, pid, "knowledge_entries", "entry_id", [truth_id]
        )
    patch.update(
        {
            "arc_id": arc_id,
            "world_truth_entry_id": truth_id,
            "updated_at": datetime.utcnow(),
        }
    )
    await db.knowledge_entries.update_one({"_id": existing["_id"]}, {"$set": patch})
    await _after_change(
        db,
        project_id=project_id,
        event_type="knowledge_changed",
        payload={"entry_id": entry_id, "action": "updated", "arc_id": arc_id},
        arc_id=arc_id,
    )
    return _serialize(await db.knowledge_entries.find_one({"_id": existing["_id"]}))


@router.get("/foreshadowing-v2")
async def get_foreshadowing_v2(project_id: str):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    docs = await db.foreshadow_registry_v2.find({"project_id": pid}).sort(
        "created_at", 1
    ).to_list(length=1000)
    return [_serialize(doc) for doc in docs]


@router.post("/foreshadowing-v2")
async def upsert_foreshadowing_v2(project_id: str, payload: dict):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    entry_id = str(payload.get("entry_id") or uuid4())
    status = str(payload.get("status") or "seeded").lower()
    if status not in FORESHADOW_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported foreshadow status")
    arc_ids = [
        value
        for value in [payload.get("arc_planted"), payload.get("payoff_arc_id")]
        if value
    ]
    await _validate_arc_ids(db, pid, arc_ids)
    now = datetime.utcnow()
    doc = {
        "project_id": pid,
        "entry_id": entry_id,
        "seed": str(payload.get("seed") or "").strip(),
        "chapter_planted": payload.get("chapter_planted"),
        "arc_planted": payload.get("arc_planted"),
        "payoff_target": str(payload.get("payoff_target") or "").strip(),
        "payoff_arc_id": payload.get("payoff_arc_id"),
        "payoff_chapter": payload.get("payoff_chapter"),
        "status": status,
        "timeline_entry_ids": _list(payload.get("timeline_entry_ids")),
        "updated_at": now,
    }
    await _validate_entry_ids(
        db, pid, "timeline_entries", "entry_id", doc["timeline_entry_ids"]
    )
    await db.foreshadow_registry_v2.update_one(
        {"project_id": pid, "entry_id": entry_id},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    await _after_change(
        db,
        project_id=project_id,
        event_type="foreshadow_changed",
        payload={"entry_id": entry_id, "status": status},
        arc_id=payload.get("arc_planted") or payload.get("payoff_arc_id"),
    )
    return _serialize(
        await db.foreshadow_registry_v2.find_one(
            {"project_id": pid, "entry_id": entry_id}
        )
    )


@router.get("/artifacts")
async def get_artifacts(project_id: str):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    docs = await db.artifact_registry.find({"project_id": pid}).sort(
        "created_at", 1
    ).to_list(length=1000)
    return [_serialize(doc) for doc in docs]


@router.post("/artifacts")
async def upsert_artifact(project_id: str, payload: dict):
    db = Database.get_db()
    pid, _ = await _project(db, project_id)
    artifact_id = str(payload.get("artifact_id") or uuid4())
    arc_ids = [str(item) for item in _list(payload.get("arc_ids")) if item]
    timeline_ids = [
        str(item) for item in _list(payload.get("timeline_entry_ids")) if item
    ]
    knowledge_ids = [
        str(item) for item in _list(payload.get("knowledge_entry_ids")) if item
    ]
    await _validate_arc_ids(db, pid, arc_ids)
    await _validate_entry_ids(
        db, pid, "timeline_entries", "entry_id", timeline_ids
    )
    await _validate_entry_ids(
        db, pid, "knowledge_entries", "entry_id", knowledge_ids
    )
    now = datetime.utcnow()
    doc = {
        "project_id": pid,
        "artifact_id": artifact_id,
        "item": str(payload.get("item") or "Untitled artifact").strip(),
        "owner": str(payload.get("owner") or "").strip(),
        "power": str(payload.get("power") or "").strip(),
        "hidden_power": str(payload.get("hidden_power") or "").strip(),
        "cost": str(payload.get("cost") or "").strip(),
        "limitations": _list(payload.get("limitations")),
        "history": str(payload.get("history") or "").strip(),
        "future_relevance": str(payload.get("future_relevance") or "").strip(),
        "status": str(payload.get("status") or "planned").strip().lower(),
        "arc_ids": arc_ids,
        "character_ids": _list(payload.get("character_ids")),
        "timeline_entry_ids": timeline_ids,
        "knowledge_entry_ids": knowledge_ids,
        "updated_at": now,
    }
    await db.artifact_registry.update_one(
        {"project_id": pid, "artifact_id": artifact_id},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    await _after_change(
        db,
        project_id=project_id,
        event_type="artifact_changed",
        payload={"artifact_id": artifact_id, "arc_ids": arc_ids},
        arc_id=arc_ids[0] if arc_ids else None,
    )
    return _serialize(
        await db.artifact_registry.find_one(
            {"project_id": pid, "artifact_id": artifact_id}
        )
    )


@router.get("/agent-memories")
async def get_agent_memories(project_id: str, agent_name: str):
    db = Database.get_db()
    await _project(db, project_id)
    return await agent_memory_service.get_context(
        db, project_id=project_id, agent_name=agent_name
    )


@router.post("/agent-memories/{agent_name}/compact")
async def compact_agent_memories(project_id: str, agent_name: str):
    db = Database.get_db()
    await _project(db, project_id)
    deleted = await agent_memory_service.compact(
        db, project_id=project_id, agent_name=agent_name
    )
    return {"agent_name": agent_name, "compacted_memories": deleted}
