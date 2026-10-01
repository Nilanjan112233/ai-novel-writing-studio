"""Local/private-beta operational safety APIs."""
from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.core.database import Database
from app.schemas.rc9 import BackupCreateRequest, BackupRestoreRequest, BetaFeedbackRequest
from app.services.project_backup_service import BackupError, project_backup_service
from app.services.operational_readiness_service import operational_readiness_service
from app.services.support_bundle_service import support_bundle_service


router = APIRouter(prefix="/api", tags=["operations"])


def _project_id(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(status_code=400, detail="This project address is invalid.")
    return ObjectId(value)


def _backup_failure(exc: Exception) -> HTTPException:
    detail = str(exc).strip() or "The backup operation could not be completed. Your existing project is unchanged."
    return HTTPException(status_code=409, detail=detail)


@router.get("/operations/readiness")
async def operational_readiness():
    return await operational_readiness_service.snapshot(Database.get_db())


@router.get("/operations/privacy")
async def privacy_summary():
    from app.services.project_backup_service import backup_root
    from app.services.support_bundle_service import support_root

    return {
        "deployment": "local_private_beta",
        "local_data": [
            "projects, plans, drafts, versions, canon, Story Bible, analysis, and approvals in local MongoDB",
            "encrypted AI provider credentials in local application settings",
            "backups and publication exports in local folders",
        ],
        "provider_data": [
            "only the story context needed for an AI operation",
            "the selected provider and model receive that context when the author starts the operation",
        ],
        "never_in_support_bundle": [
            "story prose or prompts",
            "provider responses",
            "API keys, access tokens, or database connection strings",
        ],
        "author_controls": [
            "AI is not required to open existing work",
            "provider credentials can be replaced from Settings",
            "project backup is separate from publication export",
            "feedback diagnostics are opt-in",
        ],
        "hosted_saas_supported": False,
        "locations": {
            "project_storage": "The local MongoDB database configured for this NovelForge installation.",
            "backup_folder": str(backup_root()),
            "support_folder": str(support_root()),
        },
    }


@router.post("/operations/support-bundles")
async def create_support_bundle():
    try:
        return await support_bundle_service.create(Database.get_db())
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="NovelForge could not create the diagnostic bundle. No story content or credentials were shared.",
        ) from exc


@router.get("/operations/support-bundles/{support_id}/download")
async def download_support_bundle(support_id: str):
    try:
        path = await support_bundle_service.file_path(Database.get_db(), support_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path, media_type="application/zip", filename=path.name)


@router.post("/operations/feedback")
async def submit_beta_feedback(payload: BetaFeedbackRequest):
    db = Database.get_db()
    support = await support_bundle_service.create(db) if payload.include_diagnostics else None
    feedback_id = str(ObjectId())
    document = {
        "feedback_id": feedback_id,
        "category": payload.category.strip().lower() or "general",
        "message": payload.message.strip(),
        "include_diagnostics": payload.include_diagnostics,
        "include_story_content": False,
        "story_content_requested": payload.include_story_content,
        "support_id": support.get("support_id") if support else None,
        "status": "new",
        "created_at": datetime.utcnow(),
    }
    await db.beta_feedback.insert_one(document)
    return {
        "feedback_id": feedback_id,
        "status": "saved_locally",
        "explanation": "Your beta feedback was saved in this local NovelForge installation.",
        "diagnostics_attached": bool(support),
        "story_content_attached": False,
        "support_id": support.get("support_id") if support else None,
    }


@router.post("/projects/{project_id}/backups")
async def create_project_backup(project_id: str, payload: BackupCreateRequest):
    db = Database.get_db()
    pid = _project_id(project_id)
    try:
        return await project_backup_service.create(db, pid, reason=payload.reason.strip() or "manual")
    except BackupError as exc:
        raise _backup_failure(exc) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="NovelForge could not create the backup. Your project is unchanged. Check storage availability and try again.",
        ) from exc


@router.post("/operations/backups")
async def create_all_project_backups(payload: BackupCreateRequest):
    """Create bounded, independent archives for every non-trashed project.

    One project failing never invalidates archives that already completed, and
    the response names the affected project in author language.
    """
    db = Database.get_db()
    projects = await db.projects.find(
        {"status": {"$ne": "trashed"}}, {"_id": 1, "title": 1}
    ).sort("updated_at", -1).to_list(length=10000)
    results = []
    failures = []
    for project in projects:
        try:
            results.append(await project_backup_service.create(
                db,
                project["_id"],
                reason=payload.reason.strip() or "all-project author backup",
            ))
        except Exception as exc:
            failures.append({
                "project_id": str(project["_id"]),
                "project_title": str(project.get("title") or "Untitled project"),
                "explanation": str(exc).strip() or "Backup could not be created.",
            })
    return {
        "attempted": len(projects),
        "succeeded": len(results),
        "failed": len(failures),
        "backups": results,
        "failures": failures,
        "complete": not failures,
        "explanation": (
            "All project backups completed."
            if not failures
            else "Some projects could not be backed up. Completed archives remain available; review the named failures."
        ),
    }


@router.get("/projects/{project_id}/backups")
async def list_project_backups(project_id: str):
    db = Database.get_db()
    pid = _project_id(project_id)
    if not await db.projects.find_one({"_id": pid}, {"_id": 1}):
        raise HTTPException(status_code=404, detail="Project not found.")
    return {"project_id": project_id, "backups": await project_backup_service.list(db, pid)}


@router.post("/backups/{backup_id}/validate")
async def validate_project_backup(backup_id: str):
    try:
        return await project_backup_service.validate(Database.get_db(), backup_id)
    except BackupError as exc:
        raise _backup_failure(exc) from exc


@router.post("/backups/import")
async def import_project_backup(request: Request):
    try:
        return await project_backup_service.import_archive(
            Database.get_db(),
            request.stream(),
            original_filename=request.headers.get("X-NovelForge-Filename", "imported-backup"),
        )
    except BackupError as exc:
        raise _backup_failure(exc) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="NovelForge could not import this backup. No project data was changed.",
        ) from exc


@router.post("/backups/{backup_id}/restore")
async def restore_project_backup(backup_id: str, payload: BackupRestoreRequest):
    try:
        return await project_backup_service.restore_as_copy(
            Database.get_db(), backup_id, title=payload.title, request_id=payload.request_id
        )
    except BackupError as exc:
        raise _backup_failure(exc) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="NovelForge could not restore this backup. The original project is unchanged and the incomplete copy was removed.",
        ) from exc


@router.get("/backups/{backup_id}/download")
async def download_project_backup(backup_id: str):
    try:
        path = await project_backup_service.file_path(Database.get_db(), backup_id)
    except BackupError as exc:
        raise _backup_failure(exc) from exc
    return FileResponse(
        path,
        media_type="application/zip",
        filename=path.name,
        headers={"X-NovelForge-Backup": backup_id, "X-NovelForge-Generated-At": datetime.utcnow().isoformat() + "Z"},
    )
