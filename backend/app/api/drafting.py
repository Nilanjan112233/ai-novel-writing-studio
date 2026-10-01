"""Project-owned controlled drafting and review APIs."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query

from app.core.database import Database
from app.services.draft_validation_service import draft_validation_service
from app.services.drafting_service import DRAFT_STATUSES, drafting_service
from app.services.discovery_writing_service import discovery_writing_service
from app.services.writing_experience_service import writing_experience_service


router = APIRouter(prefix="/api/projects/{project_id}", tags=["drafting"])


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


async def _project(db, project_id: str) -> ObjectId:
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    pid = ObjectId(project_id)
    if not await db.projects.find_one({"_id": pid}):
        raise HTTPException(status_code=404, detail="Project not found")
    return pid


def _conflict(exc: ValueError) -> HTTPException:
    detail = exc.args[0] if exc.args else str(exc)
    return HTTPException(status_code=409, detail=_serialize(detail))


@router.get("/writing-dashboard")
async def get_writing_dashboard(project_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return _serialize(await writing_experience_service.dashboard(db, project_id))
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/writing-state")
async def get_writing_state(project_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await writing_experience_service.state(db, project_id)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/writing-state/chapters/{chapter_number}/context")
async def get_writing_chapter_context(project_id: str, chapter_number: int):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await writing_experience_service.chapter_context(db, project_id, chapter_number)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/scene-plans/{scene_id}/generate-draft")
async def generate_scene_draft(project_id: str, scene_id: str, payload: dict | None = None):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        request = payload or {}
        return await drafting_service.generate_scene(
            db,
            project_id,
            scene_id,
            change_reason=str(request.get("change_reason") or ""),
            operation=str(request.get("operation") or "generate"),
            request_id=str(request.get("request_id") or "") or None,
            allow_exploratory=bool(request.get("allow_exploratory", False)),
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/scene-drafts/{draft_id}/regenerate")
async def regenerate_scene_draft(project_id: str, draft_id: str, payload: dict):
    db = Database.get_db()
    pid = await _project(db, project_id)
    reason = str(payload.get("change_reason") or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="change_reason is required")
    draft = await db.scene_drafts.find_one(
        {"project_id": pid, "draft_id": draft_id}
    )
    if not draft:
        raise HTTPException(status_code=404, detail="Scene draft not found")
    try:
        return await drafting_service.generate_scene(
            db,
            project_id,
            draft["scene_id"],
            parent_version_id=draft_id,
            change_reason=reason,
            operation=str(payload.get("operation") or "rewrite"),
            request_id=str(payload.get("request_id") or "") or None,
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/scene-drafts/{draft_id}/writers-room")
async def create_writers_room(
    project_id: str,
    draft_id: str,
    payload: dict | None = None,
):
    db = Database.get_db()
    await _project(db, project_id)
    request = payload or {}
    try:
        return await drafting_service.create_writers_room_options(
            db,
            project_id,
            draft_id,
            directions=list(request.get("directions") or []),
            instruction=str(request.get("instruction") or ""),
            request_id=str(request.get("request_id") or "") or None,
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/chapter-plans/{chapter_plan_id}/generate-draft")
async def generate_chapter_draft(
    project_id: str, chapter_plan_id: str, payload: dict | None = None
):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await drafting_service.generate_chapter(
            db,
            project_id,
            chapter_plan_id,
            change_reason=str((payload or {}).get("change_reason") or ""),
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/discovery-writing")
async def generate_discovery_writing(project_id: str, payload: dict):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await discovery_writing_service.generate(db, project_id, payload or {})
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/discovery-writing/extractions")
async def get_discovery_extractions(project_id: str, limit: int = Query(default=100, ge=1, le=500)):
    db = Database.get_db()
    pid = await _project(db, project_id)
    docs = await db.discovery_extractions.find({"project_id": pid}).sort("created_at", -1).to_list(length=limit)
    return [_serialize(item) for item in docs]


@router.post("/discovery-writing/extractions/{draft_id}/reextract")
async def reextract_discovery_knowledge(project_id: str, draft_id: str):
    """Re-run enrichment for one approved chapter without touching prose authority."""
    db = Database.get_db()
    pid = await _project(db, project_id)
    draft = await db.chapter_drafts.find_one({"project_id": pid, "draft_id": draft_id, "status": "approved"})
    if not draft:
        raise HTTPException(status_code=404, detail="Approved chapter draft not found")
    source_chapter = draft.get("chapter_number")
    legacy_source = {"$or": [{"source_id": draft_id}, {"source_id": None}, {"source_id": {"$exists": False}}]}
    for collection in ("character_bibles", "relationship_graphs", "mystery_registry", "plot_threads", "story_arcs", "questions", "timeline_entries", "artifact_registry", "knowledge_entries"):
        await db[collection].delete_many({"project_id": pid, "authority_status": "candidate", "source_type": "approved_discovery_prose", "source_chapter": source_chapter, **legacy_source})
    world = await db.world_bibles.find_one({"project_id": pid})
    if world and world.get("suggested_world_facts"):
        remaining = [item for item in world.get("suggested_world_facts") if not (isinstance(item, dict) and item.get("source_type") == "approved_discovery_prose" and item.get("source_chapter") == source_chapter and (item.get("source_id") in {draft_id, None} or "source_id" not in item))]
        await db.world_bibles.update_one({"_id": world["_id"]}, {"$set": {"suggested_world_facts": remaining, "updated_at": datetime.utcnow()}})
    await db.discovery_extractions.delete_many({"project_id": pid, "source_draft_id": draft_id})
    return await discovery_writing_service.extract_approved(db, project_id, draft)


@router.post("/chapter-drafts/{draft_id}/regenerate")
async def regenerate_chapter_draft(project_id: str, draft_id: str, payload: dict):
    db = Database.get_db()
    pid = await _project(db, project_id)
    reason = str(payload.get("change_reason") or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="change_reason is required")
    draft = await db.chapter_drafts.find_one(
        {"project_id": pid, "draft_id": draft_id}
    )
    if not draft:
        raise HTTPException(status_code=404, detail="Chapter draft not found")
    try:
        return await drafting_service.generate_chapter(
            db,
            project_id,
            draft["chapter_plan_id"],
            parent_version_id=draft_id,
            change_reason=reason,
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.put("/chapter-drafts/{draft_id}/content")
async def edit_chapter_content(project_id: str, draft_id: str, payload: dict):
    """Save a normal author edit as a protected, reviewable chapter version."""
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await drafting_service.edit_chapter_content(
            db,
            project_id,
            draft_id,
            str(payload.get("edited_text") or ""),
            reason=str(payload.get("reason") or "Author edited chapter prose"),
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


async def _history(
    db,
    pid: ObjectId,
    collection: str,
    *,
    identity: str | None = None,
    identity_value: str | None = None,
    status: str | None = None,
):
    query: Dict[str, Any] = {"project_id": pid}
    if identity and identity_value:
        query[identity] = identity_value
    if status:
        normalized = status.lower()
        if normalized not in DRAFT_STATUSES:
            raise HTTPException(status_code=400, detail="Unsupported draft status")
        query["status"] = normalized
    docs = await db[collection].find(query).sort(
        [("created_at", -1), ("version_number", -1)]
    ).to_list(length=5000)
    if collection == "scene_drafts":
        for doc in docs:
            if not doc.get("version_label"):
                number = max(1, int(doc.get("version_number") or 1))
                label = ""
                while number:
                    number, remainder = divmod(number - 1, 26)
                    label = chr(65 + remainder) + label
                doc["version_label"] = f"Version {label}"
            doc.setdefault("favorite", False)
    return [_serialize(doc) for doc in docs]


@router.get("/scene-drafts")
async def get_scene_draft_history(
    project_id: str,
    scene_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    db = Database.get_db()
    pid = await _project(db, project_id)
    return await _history(
        db,
        pid,
        "scene_drafts",
        identity="scene_id",
        identity_value=scene_id,
        status=status,
    )


@router.get("/chapter-drafts")
async def get_chapter_draft_history(
    project_id: str,
    chapter_plan_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    db = Database.get_db()
    pid = await _project(db, project_id)
    return await _history(
        db,
        pid,
        "chapter_drafts",
        identity="chapter_plan_id",
        identity_value=chapter_plan_id,
        status=status,
    )


@router.get("/writing-activity")
async def get_writing_activity(project_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    return await writing_experience_service.activity(db, project_id)


@router.get("/writing-state/chapters/{chapter_number}/compare")
async def compare_chapter_versions(project_id: str, chapter_number: int):
    db = Database.get_db()
    await _project(db, project_id)
    return await writing_experience_service.compare_chapter_versions(db, project_id, chapter_number)


@router.put("/scene-drafts/{draft_id}/status")
async def update_scene_draft_status(project_id: str, draft_id: str, payload: dict):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await drafting_service.transition(
            db,
            project_id,
            "scene",
            draft_id,
            str(payload.get("status") or ""),
            reason=str(payload.get("reason") or ""),
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.put("/chapter-drafts/{draft_id}/status")
async def update_chapter_draft_status(project_id: str, draft_id: str, payload: dict):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await drafting_service.transition(
            db,
            project_id,
            "chapter",
            draft_id,
            str(payload.get("status") or ""),
            reason=str(payload.get("reason") or ""),
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/scene-drafts/{draft_id}/rollback")
async def rollback_scene_draft(project_id: str, draft_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await drafting_service.rollback(
            db, project_id, "scene", draft_id
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.put("/scene-drafts/{draft_id}/favorite")
async def favorite_scene_draft(project_id: str, draft_id: str, payload: dict):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await drafting_service.set_scene_favorite(
            db,
            project_id,
            draft_id,
            bool(payload.get("favorite", True)),
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/scene-drafts/compare")
async def compare_scene_drafts(
    project_id: str,
    left_draft_id: str = Query(...),
    right_draft_id: str = Query(...),
):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await drafting_service.compare_scene_versions(
            db,
            project_id,
            left_draft_id,
            right_draft_id,
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/scene-drafts/merge")
async def merge_scene_drafts(project_id: str, payload: dict):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await drafting_service.merge_scene_versions(
            db,
            project_id,
            str(payload.get("left_draft_id") or ""),
            str(payload.get("right_draft_id") or ""),
            str(payload.get("merged_text") or ""),
            reason=str(payload.get("reason") or ""),
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/chapter-drafts/{draft_id}/rollback")
async def rollback_chapter_draft(project_id: str, draft_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await drafting_service.rollback(
            db, project_id, "chapter", draft_id
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/scene-drafts/{draft_id}/validate")
async def validate_scene_draft(project_id: str, draft_id: str):
    db = Database.get_db()
    pid = await _project(db, project_id)
    draft = await db.scene_drafts.find_one(
        {"project_id": pid, "draft_id": draft_id}
    )
    if not draft:
        raise HTTPException(status_code=404, detail="Scene draft not found")
    return _serialize(
        await draft_validation_service.validate_scene_draft(
            db, project_id, draft
        )
    )


@router.post("/chapter-drafts/{draft_id}/validate")
async def validate_chapter_draft(project_id: str, draft_id: str):
    db = Database.get_db()
    pid = await _project(db, project_id)
    draft = await db.chapter_drafts.find_one(
        {"project_id": pid, "draft_id": draft_id}
    )
    if not draft:
        raise HTTPException(status_code=404, detail="Chapter draft not found")
    return _serialize(
        await draft_validation_service.validate_chapter_draft(
            db, project_id, draft
        )
    )


@router.get("/continuity-reports")
async def get_draft_continuity_reports(
    project_id: str,
    subject_type: str | None = Query(default=None),
    subject_id: str | None = Query(default=None),
):
    db = Database.get_db()
    pid = await _project(db, project_id)
    query: Dict[str, Any] = {"project_id": pid}
    if subject_type:
        query["subject_type"] = subject_type
    if subject_id:
        query["subject_id"] = subject_id
    docs = await db.continuity_reports.find(query).sort(
        "created_at", -1
    ).to_list(length=5000)
    return [_serialize(doc) for doc in docs]


@router.get("/draft-review-queue")
async def get_draft_review_queue(project_id: str):
    db = Database.get_db()
    pid = await _project(db, project_id)
    scene_drafts = await db.scene_drafts.find(
        {"project_id": pid, "active": True}
    ).sort("created_at", -1).to_list(length=2000)
    chapter_drafts = await db.chapter_drafts.find(
        {"project_id": pid, "active": True}
    ).sort("created_at", -1).to_list(length=2000)
    reports = await db.continuity_reports.find(
        {
            "project_id": pid,
            "subject_type": {"$in": ["scene_draft", "chapter_draft"]},
        }
    ).sort("created_at", -1).to_list(length=5000)
    histories = {
        "scene_versions": await db.scene_drafts.count_documents(
            {"project_id": pid}
        ),
        "chapter_versions": await db.chapter_drafts.count_documents(
            {"project_id": pid}
        ),
    }
    return _serialize(
        {
            "project_id": pid,
            "scene_drafts": scene_drafts,
            "chapter_drafts": chapter_drafts,
            "review_queue": [
                *[item for item in scene_drafts if item.get("status") in {"draft", "review"}],
                *[item for item in chapter_drafts if item.get("status") in {"draft", "review"}],
            ],
            "continuity_warnings": [
                item for item in reports if item.get("result") in {"WARNING", "FAIL"}
            ],
            "continuity_reports": reports,
            "generation_history": histories,
            "generated_at": datetime.utcnow(),
        }
    )


@router.get("/scenes/{scene_id}/paragraphs")
async def get_scene_paragraphs(project_id: str, scene_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await drafting_service.get_scene_paragraphs(db, project_id, scene_id)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/scenes/{scene_id}/paragraphs/{paragraph_id}/content")
async def get_paragraph_content(project_id: str, scene_id: str, paragraph_id: str):
    """Return the authoritative prose content for the Tiptap editor.

    Checks ``paragraph_content`` first; synthesises from the skeleton's
    ``prose`` field as a fallback so the editor is never empty on first open.
    """
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await drafting_service.get_paragraph_content(db, project_id, scene_id, paragraph_id)
    except ValueError as exc:
        raise _conflict(exc) from exc




@router.post("/scenes/{scene_id}/paragraphs/generate")
async def generate_scene_paragraphs(project_id: str, scene_id: str, payload: dict | None = None):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        res = await drafting_service.generate_scene(
            db,
            project_id,
            scene_id,
            change_reason=str((payload or {}).get("change_reason") or ""),
        )
        paragraphs = await drafting_service.get_scene_paragraphs(db, project_id, scene_id)
        return {"status": "success", "draft": res["draft"], "paragraphs": paragraphs}
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.put("/scenes/{scene_id}/paragraphs/{paragraph_id}")
async def update_paragraph(project_id: str, scene_id: str, paragraph_id: str, payload: dict):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        updates = payload.get("updates") or {}
        change_reason = str(payload.get("change_reason") or "")
        create_version = bool(payload.get("create_version", False))
        created_by = str(payload.get("created_by", "human"))
        generation_metadata = payload.get("generation_metadata")
        return await drafting_service.update_paragraph(
            db, project_id, scene_id, paragraph_id, updates, change_reason,
            create_version=create_version, created_by=created_by, generation_metadata=generation_metadata
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/scenes/{scene_id}/paragraphs/{paragraph_id}/ai-edit")
async def ai_edit_paragraph(project_id: str, scene_id: str, paragraph_id: str, payload: dict):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        mode = str(payload.get("mode") or "expand")
        prompt = str(payload.get("prompt") or "")
        return await drafting_service.ai_edit_paragraph(
            db, project_id, scene_id, paragraph_id, mode, prompt
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/scenes/{scene_id}/paragraphs/{paragraph_id}/comments")
async def add_paragraph_comment(project_id: str, scene_id: str, paragraph_id: str, payload: dict):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        author = str(payload.get("author") or "User")
        content = str(payload.get("content") or "")
        if not content:
            raise HTTPException(status_code=400, detail="Comment content is required")
        return await drafting_service.add_paragraph_comment(
            db, project_id, paragraph_id, author, content
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/scenes/{scene_id}/paragraphs/{paragraph_id}/comments/{comment_id}/reply")
async def reply_paragraph_comment(project_id: str, scene_id: str, paragraph_id: str, comment_id: str, payload: dict):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        author = str(payload.get("author") or "User")
        content = str(payload.get("content") or "")
        if not content:
            raise HTTPException(status_code=400, detail="Reply content is required")
        return await drafting_service.reply_paragraph_comment(
            db, project_id, paragraph_id, comment_id, author, content
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.put("/scenes/{scene_id}/paragraphs/{paragraph_id}/comments/{comment_id}/resolve")
async def resolve_paragraph_comment(project_id: str, scene_id: str, paragraph_id: str, comment_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await drafting_service.resolve_paragraph_comment(
            db, project_id, paragraph_id, comment_id
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/scenes/{scene_id}/paragraphs/{paragraph_id}/comments")
async def get_paragraph_comments(project_id: str, scene_id: str, paragraph_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await drafting_service.get_paragraph_comments(
            db, project_id, paragraph_id
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/scenes/{scene_id}/paragraphs/reorder")
async def reorder_paragraphs(project_id: str, scene_id: str, payload: dict):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        reorder_payload = payload.get("reorder_payload") or []
        if not isinstance(reorder_payload, list):
            raise HTTPException(status_code=400, detail="reorder_payload must be a list")
        return await drafting_service.reorder_paragraphs(db, project_id, scene_id, reorder_payload)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/scenes/{scene_id}/paragraphs/{paragraph_id}/lock")
async def lock_paragraph(project_id: str, scene_id: str, paragraph_id: str, payload: dict):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        is_locked = bool(payload.get("is_locked"))
        return await drafting_service.lock_paragraph(db, project_id, scene_id, paragraph_id, is_locked)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.delete("/scenes/{scene_id}/paragraphs/{paragraph_id}")
async def delete_paragraph(project_id: str, scene_id: str, paragraph_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await drafting_service.delete_paragraph(db, project_id, scene_id, paragraph_id)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/scenes/{scene_id}/paragraphs/{paragraph_id}/duplicate")
async def duplicate_paragraph(project_id: str, scene_id: str, paragraph_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await drafting_service.duplicate_paragraph(db, project_id, scene_id, paragraph_id)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/scenes/{scene_id}/paragraphs/{paragraph_id}/approve")
async def approve_paragraph(project_id: str, scene_id: str, paragraph_id: str, payload: dict):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        approval_state = str(payload.get("approval_state") or "pending")
        return await drafting_service.approve_paragraph(db, project_id, scene_id, paragraph_id, approval_state)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/scenes/{scene_id}/paragraphs/{paragraph_id}/regenerate")
async def regenerate_paragraph(project_id: str, scene_id: str, paragraph_id: str, payload: dict):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        change_reason = str(payload.get("change_reason") or "")
        return await drafting_service.regenerate_paragraph(db, project_id, scene_id, paragraph_id, change_reason)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/scenes/{scene_id}/paragraphs/{paragraph_id}/history")
async def get_paragraph_history(project_id: str, scene_id: str, paragraph_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await drafting_service.get_paragraph_history(db, project_id, scene_id, paragraph_id)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/scenes/{scene_id}/paragraphs/{paragraph_id}/restore/{version_id}")
async def restore_paragraph_version(project_id: str, scene_id: str, paragraph_id: str, version_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await drafting_service.restore_paragraph_version(db, project_id, scene_id, paragraph_id, version_id)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/scenes/{scene_id}/paragraphs/{paragraph_id}/suggestions")
async def get_paragraph_suggestions(project_id: str, scene_id: str, paragraph_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await drafting_service.get_paragraph_suggestions(
            db, paragraph_id, project_id=project_id
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/scenes/{scene_id}/paragraphs/{paragraph_id}/suggestions/{suggestion_id}/accept")
async def accept_paragraph_suggestion(project_id: str, scene_id: str, paragraph_id: str, suggestion_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await drafting_service.accept_paragraph_suggestion(db, project_id, scene_id, paragraph_id, suggestion_id)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/scenes/{scene_id}/paragraphs/{paragraph_id}/suggestions/{suggestion_id}/reject")
async def reject_paragraph_suggestion(project_id: str, scene_id: str, paragraph_id: str, suggestion_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await drafting_service.reject_paragraph_suggestion(db, project_id, scene_id, paragraph_id, suggestion_id)
    except ValueError as exc:
        raise _conflict(exc) from exc
