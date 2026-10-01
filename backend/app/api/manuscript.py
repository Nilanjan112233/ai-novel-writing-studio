"""Project-owned manuscript assembly and canon governance APIs."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.core.database import Database
from app.services.canon_governance_service import canon_governance_service
from app.services.manuscript_service import manuscript_service
from app.services.publication_service import publication_service
from app.services.project_event_service import emit_project_event


router = APIRouter(prefix="/api/projects/{project_id}", tags=["manuscript"])


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


@router.post("/manuscripts")
async def create_manuscript(project_id: str, payload: dict | None = None):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await manuscript_service.create(
            db, project_id, title=str((payload or {}).get("title") or "")
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/manuscripts")
async def list_manuscripts(project_id: str):
    db = Database.get_db()
    pid = await _project(db, project_id)
    return _serialize(
        await db.manuscripts.find({"project_id": pid}).sort(
            "updated_at", -1
        ).to_list(length=100)
    )


@router.post("/manuscripts/{manuscript_id}/assemble")
async def assemble_manuscript(
    project_id: str, manuscript_id: str, payload: dict | None = None
):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await manuscript_service.assemble(
            db,
            project_id,
            manuscript_id,
            chapter_draft_ids=list(
                (payload or {}).get("chapter_draft_ids") or []
            )
            or None,
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/manuscripts/{manuscript_id}/validate")
async def validate_manuscript(
    project_id: str, manuscript_id: str, payload: dict | None = None
):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await manuscript_service.validate(
            db,
            project_id,
            manuscript_id,
            version_id=(payload or {}).get("version_id"),
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/manuscripts/{manuscript_id}/review")
async def review_manuscript(project_id: str, manuscript_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await manuscript_service.review(db, project_id, manuscript_id)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.put("/manuscripts/{manuscript_id}/status")
async def update_manuscript_status(
    project_id: str, manuscript_id: str, payload: dict
):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await manuscript_service.transition(
            db,
            project_id,
            manuscript_id,
            str(payload.get("status") or ""),
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/manuscripts/{manuscript_id}/approve")
async def approve_manuscript(project_id: str, manuscript_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await manuscript_service.transition(
            db, project_id, manuscript_id, "approved"
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/manuscripts/{manuscript_id}/archive")
async def archive_manuscript(project_id: str, manuscript_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await manuscript_service.transition(
            db, project_id, manuscript_id, "archived"
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/manuscripts/{manuscript_id}/versions")
async def manuscript_versions(project_id: str, manuscript_id: str):
    db = Database.get_db()
    pid = await _project(db, project_id)
    if not await db.manuscripts.find_one(
        {"project_id": pid, "manuscript_id": manuscript_id}
    ):
        raise HTTPException(status_code=404, detail="Manuscript not found")
    return _serialize(
        await db.manuscript_versions.find(
            {"project_id": pid, "manuscript_id": manuscript_id}
        ).sort("version_number", -1).to_list(length=5000)
    )


@router.post("/manuscripts/{manuscript_id}/rollback/{version_id}")
async def rollback_manuscript(
    project_id: str, manuscript_id: str, version_id: str
):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await manuscript_service.rollback(
            db, project_id, manuscript_id, version_id
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/manuscript-reports")
async def manuscript_reports(
    project_id: str,
    manuscript_id: str | None = Query(default=None),
    report_type: str | None = Query(default=None),
):
    db = Database.get_db()
    pid = await _project(db, project_id)
    query: Dict[str, Any] = {"project_id": pid}
    if manuscript_id:
        query["manuscript_id"] = manuscript_id
    if report_type:
        query["report_type"] = report_type
    return _serialize(
        await db.manuscript_reports.find(query).sort(
            "created_at", -1
        ).to_list(length=5000)
    )


@router.get("/manuscript-dashboard")
async def manuscript_dashboard(project_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    return await manuscript_service.dashboard(db, project_id)


@router.get("/manuscripts/{manuscript_id}/publication-preflight")
async def publication_preflight(project_id: str, manuscript_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await publication_service.preflight(db, project_id, manuscript_id)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/manuscripts/{manuscript_id}/publication-exports")
async def create_publication_export(project_id: str, manuscript_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        manifest = await publication_service.export(db, project_id, manuscript_id)
        await emit_project_event(
            db,
            project_id,
            "publication_export_completed",
            payload={
                "export_id": manifest["export_id"],
                "manuscript_id": manuscript_id,
                "version_id": manifest["version_id"],
            },
        )
        return manifest
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/publication-exports")
async def publication_exports(project_id: str):
    db = Database.get_db()
    pid = await _project(db, project_id)
    rows = await db.publication_exports.find(
        {"project_id": pid}
    ).sort("created_at", -1).to_list(length=100)
    return _serialize([
        {
            "export_id": row.get("export_id"),
            "manuscript_id": row.get("manuscript_id"),
            "version_id": row.get("version_id"),
            "status": row.get("status"),
            "manifest": row.get("manifest") or {},
            "created_at": row.get("created_at"),
        }
        for row in rows
    ])


@router.get("/publication-exports/{export_id}/{kind}")
async def download_publication_export(project_id: str, export_id: str, kind: str):
    db = Database.get_db()
    await _project(db, project_id)
    if kind not in {"markdown", "text", "html", "docx", "epub", "pdf", "package"}:
        raise HTTPException(status_code=400, detail="Unsupported publication artifact")
    try:
        path = await publication_service.artifact(db, project_id, export_id, kind)
    except ValueError as exc:
        raise _conflict(exc) from exc
    return FileResponse(path, filename=path.name)


@router.get("/canon/registry")
async def canon_registry(
    project_id: str,
    canon_type: str | None = Query(default=None),
    active: bool | None = Query(default=None),
):
    db = Database.get_db()
    pid = await _project(db, project_id)
    query: Dict[str, Any] = {"project_id": pid}
    if canon_type:
        query["canon_type"] = canon_type
    if active is not None:
        query["active"] = active
    return _serialize(
        await db.canon_registry.find(query).sort(
            "updated_at", -1
        ).to_list(length=10000)
    )


@router.post("/canon/promote")
async def promote_canon(project_id: str, payload: dict):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await canon_governance_service.promote(
            db,
            project_id,
            canon_type=str(payload.get("canon_type") or ""),
            source_collection=str(payload.get("source_collection") or ""),
            source_id=str(payload.get("source_id") or ""),
            subject=str(payload.get("subject") or ""),
            field=str(payload.get("field") or ""),
            value=payload.get("value"),
            source_version=int(payload.get("source_version") or 1),
            authority_level=str(payload.get("authority_level") or "approved"),
            evidence=list(payload.get("evidence") or []),
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.put("/canon/registry/{canon_id}/active")
async def update_canon_record_active(
    project_id: str, canon_id: str, payload: dict
):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await canon_governance_service.set_record_active(
            db,
            project_id,
            canon_id,
            bool(payload.get("active")),
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/canon/validate")
async def validate_canon(project_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await canon_governance_service.validate(db, project_id)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/canon/review")
async def review_canon(project_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await canon_governance_service.review(db, project_id)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/canon/conflicts")
async def canon_conflicts(
    project_id: str, status: str | None = Query(default=None)
):
    db = Database.get_db()
    pid = await _project(db, project_id)
    query: Dict[str, Any] = {"project_id": pid}
    if status:
        query["status"] = status
    return _serialize(
        await db.canon_conflicts.find(query).sort(
            "last_seen_at", -1
        ).to_list(length=5000)
    )


@router.put("/canon/conflicts/{conflict_id}/status")
async def update_canon_conflict(
    project_id: str, conflict_id: str, payload: dict
):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await canon_governance_service.set_conflict_status(
            db,
            project_id,
            conflict_id,
            str(payload.get("status") or ""),
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/canon/reports")
async def canon_reports(project_id: str):
    db = Database.get_db()
    pid = await _project(db, project_id)
    return _serialize(
        await db.manuscript_reports.find(
            {"project_id": pid, "report_type": "canon_review"}
        ).sort("created_at", -1).to_list(length=1000)
    )


@router.get("/canon/promotion-history")
async def canon_promotion_history(project_id: str):
    db = Database.get_db()
    pid = await _project(db, project_id)
    return _serialize(
        await db.canon_registry.find(
            {"project_id": pid, "promotion_fingerprint": {"$exists": True}}
        ).sort("created_at", -1).to_list(length=5000)
    )


@router.get("/canon/dashboard")
async def canon_dashboard(project_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    return await canon_governance_service.dashboard(db, project_id)
