"""Project-owned editorial review and revision governance APIs."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query

from app.core.database import Database
from app.services.editorial_service import editorial_service


router = APIRouter(prefix="/api/projects/{project_id}", tags=["editorial"])


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


@router.post("/editorial/review/scene/{draft_id}")
async def request_scene_review(project_id: str, draft_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await editorial_service.request_review(
            db,
            project_id,
            subject_type="scene",
            subject_id=draft_id,
            report_type="editorial",
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/editorial/review/chapter/{draft_id}")
async def request_chapter_review(project_id: str, draft_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await editorial_service.request_review(
            db,
            project_id,
            subject_type="chapter",
            subject_id=draft_id,
            report_type="editorial",
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/editorial/review/arc/{arc_id}")
async def request_arc_review(project_id: str, arc_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await editorial_service.request_review(
            db,
            project_id,
            subject_type="arc",
            subject_id=arc_id,
            report_type="editorial",
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/editorial/dialogue/{draft_type}/{draft_id}")
async def request_dialogue_review(
    project_id: str, draft_type: str, draft_id: str
):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await editorial_service.request_review(
            db,
            project_id,
            subject_type=draft_type,
            subject_id=draft_id,
            report_type="dialogue",
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/editorial/reports")
async def get_editorial_reports(
    project_id: str,
    subject_type: str | None = Query(default=None),
    subject_id: str | None = Query(default=None),
    report_type: str | None = Query(default=None),
):
    db = Database.get_db()
    pid = await _project(db, project_id)
    query: Dict[str, Any] = {"project_id": pid}
    if subject_type:
        query["subject_type"] = subject_type
    if subject_id:
        query["subject_id"] = subject_id
    if report_type:
        query["report_type"] = report_type
    docs = await db.editorial_reports.find(query).sort(
        "created_at", -1
    ).to_list(length=5000)
    return _serialize(docs)


@router.get("/editorial/scores")
async def get_editorial_scores(
    project_id: str,
    subject_type: str | None = Query(default=None),
    subject_id: str | None = Query(default=None),
    score_type: str | None = Query(default=None),
):
    db = Database.get_db()
    pid = await _project(db, project_id)
    query: Dict[str, Any] = {"project_id": pid}
    if subject_type:
        query["subject_type"] = subject_type
    if subject_id:
        query["subject_id"] = subject_id
    if score_type:
        query["score_type"] = score_type
    docs = await db.editorial_scores.find(query).sort(
        "calculated_at", -1
    ).to_list(length=5000)
    return _serialize(docs)


@router.get("/editorial/dashboard")
async def get_editorial_dashboard(project_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await editorial_service.dashboard(db, project_id)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/revision-branches")
async def create_revision_branch(project_id: str, payload: dict):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await editorial_service.create_branch(
            db,
            project_id,
            source_draft_type=str(payload.get("source_draft_type") or ""),
            source_draft_id=str(payload.get("source_draft_id") or ""),
            title=str(payload.get("title") or ""),
            parent_branch_id=payload.get("parent_branch_id"),
            revision_pass=str(payload.get("revision_pass") or "development"),
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/chapter-drafts/{draft_id}/selection-revision")
async def create_selection_revision(project_id: str, draft_id: str, payload: dict):
    """Create a protected revision proposal for a selected passage."""
    db = Database.get_db()
    await _project(db, project_id)
    selected_text = str(payload.get("selected_text") or "").strip()
    instruction = str(payload.get("instruction") or "").strip()
    if not selected_text or not instruction:
        raise HTTPException(status_code=400, detail="selected_text and instruction are required")
    try:
        await editorial_service.request_review(db, project_id, subject_type="chapter", subject_id=draft_id, report_type="editorial")
        branch = await editorial_service.create_branch(
            db,
            project_id,
            source_draft_type="chapter",
            source_draft_id=draft_id,
            title=f"Focused edit: {instruction[:60]}",
            revision_pass="line",
        )
        revision = await editorial_service.generate_revision(
            db,
            project_id,
            branch["branch_id"],
            change_reason=(
                f"Only revise the selected passage below. Keep all other chapter events, facts, POV, chronology, and outcome unchanged.\n"
                f"Selected passage:\n{selected_text}\nAuthor instruction: {instruction}"
            ),
            revision_pass="line",
        )
        return {"branch": branch, "revision": revision, "selected_text": selected_text}
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/revision-branches")
async def get_revision_branches(
    project_id: str,
    source_draft_id: str | None = Query(default=None),
):
    db = Database.get_db()
    pid = await _project(db, project_id)
    query: Dict[str, Any] = {"project_id": pid}
    if source_draft_id:
        query["source_draft_id"] = source_draft_id
    docs = await db.revision_branches.find(query).sort(
        "updated_at", -1
    ).to_list(length=5000)
    return _serialize(docs)


@router.post("/revision-branches/{branch_id}/generate")
async def generate_revision(project_id: str, branch_id: str, payload: dict):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await editorial_service.generate_revision(
            db,
            project_id,
            branch_id,
            change_reason=str(payload.get("change_reason") or ""),
            report_ids=list(payload.get("report_ids") or []),
            revision_pass=str(payload.get("revision_pass") or "") or None,
            request_id=str(payload.get("request_id") or "") or None,
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.put("/revision-branches/{branch_id}/status")
async def update_revision_branch_status(
    project_id: str, branch_id: str, payload: dict
):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await editorial_service.transition_branch(
            db,
            project_id,
            branch_id,
            str(payload.get("status") or ""),
            reason=str(payload.get("reason") or ""),
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/revision-branches/{branch_id}/apply")
async def apply_revision(project_id: str, branch_id: str, payload: dict | None = None):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await editorial_service.apply_revision(
            db,
            project_id,
            branch_id,
            revision_id=str((payload or {}).get("revision_id") or "") or None,
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/revision-branches/{branch_id}/lineage")
async def get_revision_lineage(project_id: str, branch_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await editorial_service.lineage(db, project_id, branch_id)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/revision-branches/{branch_id}/compare")
async def compare_revision(
    project_id: str,
    branch_id: str,
    revision_id: str | None = Query(default=None),
):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await editorial_service.compare(
            db,
            project_id,
            branch_id,
            revision_id=revision_id,
        )
    except ValueError as exc:
        raise _conflict(exc) from exc
