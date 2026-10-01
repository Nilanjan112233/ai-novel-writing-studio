from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId
from app.core.database import Database
from app.services.workspace_context_service import workspace_context_service
from app.models.project import Project, Run, AgentOutput
from app.schemas.project import (
    DeleteProjectResponse,
    MessageCreateRequest,
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectPurgeRequest,
    RunResponse,
    TimelineMessageResponse,
)
from app.utils.serialize import serialize_timeline_message
from app.services.canon_service import record_user_message_decision
from app.services.project_event_service import emit_project_event
from app.services.story_bible_service import rebuild_story_bible
from app.services.shared_narrative_context_service import shared_narrative_context_service
from app.services.project_lifecycle_service import project_lifecycle_service
from datetime import datetime
from typing import List
from app.core.version import APP_VERSION, SCHEMA_VERSION

router = APIRouter(prefix="/api/projects", tags=["projects"])


def normalize_project(doc: dict) -> dict:
    """Ensure all ProjectResponse fields exist for legacy documents."""
    doc = dict(doc)
    doc["id"] = str(doc["_id"])
    doc["project_name"] = str(doc.get("project_name") or doc.get("title") or "Untitled project").strip() or "Untitled project"
    # ``title`` is retained as the legacy project-name field for older API
    # consumers. Reader-facing surfaces use ``story_title`` instead.
    doc["title"] = doc["project_name"]
    doc["story_title"] = str(doc.get("story_title") or "").strip() or None
    # Old private-beta records may predate explicit timestamps. ObjectId keeps
    # their creation time, allowing the library to remain readable without a
    # write-on-read migration or fabricated ordering.
    legacy_created_at = doc["_id"].generation_time.replace(tzinfo=None)
    doc.setdefault("created_at", legacy_created_at)
    doc.setdefault("updated_at", doc["created_at"])
    doc.setdefault("premise", "")
    doc.setdefault("idea_dump", "")
    doc.setdefault("genre", "")
    doc.setdefault("tone", "")
    doc.setdefault("themes", [])
    doc.setdefault("inspirations", [])
    doc.setdefault("character_notes", None)
    doc.setdefault("world_notes", None)
    doc.setdefault("plot_notes", None)
    doc.setdefault("notes", None)
    doc.setdefault("target_length", None)
    doc.setdefault("audience", None)
    doc.setdefault("narrative_goals", [])
    doc.setdefault("status", "draft")
    doc.setdefault("planning_reconsideration", None)
    if isinstance(doc.get("planning_reconsideration"), dict):
        doc["planning_reconsideration"] = {
            key: str(value) if isinstance(value, ObjectId) else value
            for key, value in doc["planning_reconsideration"].items()
        }
    if doc.get("duplicated_from_project_id"):
        doc["duplicated_from_project_id"] = str(doc["duplicated_from_project_id"])
    if doc.get("restored_from_project_id"):
        doc["restored_from_project_id"] = str(doc["restored_from_project_id"])
    return doc


@router.post("", response_model=ProjectResponse)
async def create_project(project: ProjectCreate):
    """Create a new project."""
    db = Database.get_db()
    
    project_dict = project.model_dump()
    project_dict["project_name"] = (project_dict.get("project_name") or project_dict.get("title") or "Untitled project").strip()
    project_dict["title"] = project_dict["project_name"]
    project_dict["story_title"] = (project_dict.get("story_title") or "").strip() or None
    project_dict["created_at"] = datetime.utcnow()
    project_dict["updated_at"] = datetime.utcnow()
    project_dict["status"] = "draft"
    project_dict["app_version"] = APP_VERSION
    project_dict["created_with_app_version"] = APP_VERSION
    project_dict["schema_version"] = SCHEMA_VERSION
    
    result = await db.projects.insert_one(project_dict)
    project_dict["_id"] = result.inserted_id
    project_dict["id"] = str(result.inserted_id)
    # Story Bible aggregation is intentionally lazy. Returning the created
    # project must not wait on dozens of project-knowledge queries; the existing
    # GET /story-bible path rebuilds it on first intelligence load.
    await emit_project_event(db, str(result.inserted_id), "project_created")
    
    return ProjectResponse(**normalize_project(project_dict))


@router.get("", response_model=List[ProjectResponse])
async def get_projects(
    include_archived: bool = Query(default=False),
    include_trashed: bool = Query(default=False),
):
    """Get all projects."""
    db = Database.get_db()
    excluded = []
    if not include_archived:
        excluded.append("archived")
    if not include_trashed:
        excluded.append("trashed")
    query = {"status": {"$nin": excluded}} if excluded else {}
    projects = await db.projects.find(query).sort("updated_at", -1).to_list(length=1000)
    return [ProjectResponse(**normalize_project(p)) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get a specific project."""
    db = Database.get_db()
    
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    
    project = await db.projects.find_one({
        "_id": ObjectId(project_id),
        "status": {"$ne": "trashed"},
    })
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return ProjectResponse(**normalize_project(project))


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, project: ProjectUpdate):
    """Update a project."""
    db = Database.get_db()
    
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    
    existing = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Project not found")
    submitted = {k: v for k, v in project.model_dump().items() if v is not None}
    if "project_name" in submitted:
        submitted["project_name"] = str(submitted["project_name"] or "Untitled project").strip() or "Untitled project"
        submitted["title"] = submitted["project_name"]
    elif "title" in submitted:
        submitted["project_name"] = str(submitted["title"] or "Untitled project").strip() or "Untitled project"
        submitted["title"] = submitted["project_name"]
    if "story_title" in submitted:
        submitted["story_title"] = str(submitted["story_title"] or "").strip() or None
    update_data = {
        key: value
        for key, value in submitted.items()
        if existing.get(key) != value
    }
    if not update_data:
        return ProjectResponse(**normalize_project(existing))
    changed_fields = sorted(update_data)
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.projects.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": update_data}
    )
    
    updated_project = await db.projects.find_one({"_id": ObjectId(project_id)})
    await rebuild_story_bible(db, project_id)
    await emit_project_event(
        db,
        project_id,
        "project_updated",
        payload={"changed_fields": changed_fields},
    )
    return ProjectResponse(**normalize_project(updated_project))


@router.delete("/{project_id}", response_model=DeleteProjectResponse)
async def delete_project(project_id: str):
    """Legacy permanent delete endpoint retained for API compatibility.

    The commercial UI uses ``POST /trash`` and requires a second explicit
    confirmation before it calls the guarded purge endpoint.
    """
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    pid = ObjectId(project_id)
    if not await db.projects.find_one({"_id": pid}, {"_id": 1}):
        raise HTTPException(status_code=404, detail="Project not found")
    counts = await project_lifecycle_service.purge(db, pid)
    return {"message": "Project deleted", "recoverable": False, "deleted_counts": counts}


@router.post("/{project_id}/trash", response_model=DeleteProjectResponse)
async def trash_project(project_id: str):
    """Move a project to recoverable Trash; all story data is preserved."""
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    result = await project_lifecycle_service.trash(db, ObjectId(project_id))
    if result["matched"] == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project moved to Trash", "recoverable": True}


@router.delete("/{project_id}/purge", response_model=DeleteProjectResponse)
async def purge_project(project_id: str, payload: ProjectPurgeRequest):
    """Permanently erase a trashed project after an explicit title check."""
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    pid = ObjectId(project_id)
    project = await db.projects.find_one({"_id": pid})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.get("status") != "trashed":
        raise HTTPException(status_code=409, detail="Move the project to Trash before permanent deletion")
    if payload.confirmation_title.strip() != str(project.get("title", "")).strip():
        raise HTTPException(status_code=400, detail="Project title confirmation does not match")
    counts = await project_lifecycle_service.purge(db, pid)
    return {"message": "Project permanently deleted", "recoverable": False, "deleted_counts": counts}


@router.post("/{project_id}/restore", response_model=ProjectResponse)
async def restore_project(project_id: str):
    """Restore a project from Trash."""
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    pid = ObjectId(project_id)
    result = await project_lifecycle_service.restore(db, pid)
    if result["matched"] == 0:
        raise HTTPException(status_code=404, detail="Trashed project not found")
    project = await db.projects.find_one({"_id": pid})
    return ProjectResponse(**normalize_project(project))


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(project_id: str):
    """Archive a project without deleting story memory."""
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    result = await project_lifecycle_service.archive(db, ObjectId(project_id))
    if result["matched"] == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    project = await db.projects.find_one({"_id": ObjectId(project_id)})
    return ProjectResponse(**normalize_project(project))


@router.post("/{project_id}/unarchive", response_model=ProjectResponse)
async def unarchive_project(project_id: str):
    """Return an archived project to the active list."""
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    pid = ObjectId(project_id)
    result = await project_lifecycle_service.unarchive(db, pid)
    if result["matched"] == 0:
        raise HTTPException(status_code=404, detail="Archived project not found")
    project = await db.projects.find_one({"_id": pid})
    return ProjectResponse(**normalize_project(project))


@router.post("/{project_id}/duplicate", response_model=ProjectResponse)
async def duplicate_project(
    project_id: str,
    mode: str = Query(default="shell", pattern="^(shell|story)$"),
):
    """Duplicate either project setup only or the governed story content."""
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    source = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not source:
        raise HTTPException(status_code=404, detail="Project not found")
    duplicate = await project_lifecycle_service.duplicate(db, source, mode=mode)
    await emit_project_event(
        db,
        str(duplicate["_id"]),
        "project_duplicated",
        payload={"mode": mode, "source_project_id": project_id},
    )
    return ProjectResponse(**normalize_project(duplicate))


@router.get("/{project_id}/timeline", response_model=List[TimelineMessageResponse])
async def get_timeline(project_id: str):
    """Get project timeline."""
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    
    messages = (
        await db.timeline_messages.find({"project_id": ObjectId(project_id)})
        .sort("created_at", 1)
        .to_list(length=1000)
    )
    return [TimelineMessageResponse(**serialize_timeline_message(m)) for m in messages]


@router.post("/{project_id}/messages", response_model=TimelineMessageResponse)
async def add_message(project_id: str, payload: MessageCreateRequest):
    """Add a user message to the timeline."""
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")
        
    # Get current max cycle number
    project = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # Find latest cycle
    latest_cycle = await db.cycles.find_one(
        {"project_id": ObjectId(project_id)},
        sort=[("cycle_number", -1)]
    )
    cycle_number = (latest_cycle["cycle_number"] + 1) if latest_cycle and latest_cycle.get("status") == "completed" else 1
    
    message = {
        "project_id": ObjectId(project_id),
        "cycle_number": cycle_number,
        "role": "user",
        "agent_name": None,
        "message_type": "idea",
        "content": content,
        "created_at": datetime.utcnow()
    }
    
    result = await db.timeline_messages.insert_one(message)
    message_id = result.inserted_id
    await db.discussion_messages.insert_one({
        "project_id": ObjectId(project_id),
        "author": "User",
        "role": "user",
        "cycle": cycle_number,
        "cycle_number": cycle_number,
        "reasoning": "User intervention",
        "references": [],
        "content": content,
        "timestamp": datetime.utcnow(),
        "created_at": datetime.utcnow(),
        "provider": "user",
        "model": "human",
        "tokens": 0,
        "cost": 0,
        "latency": 0,
        "execution_trace_id": "",
        "source_type": "human",
        "mock_used": False,
    })
    await record_user_message_decision(
        db,
        project_id=project_id,
        content=content,
        cycle_number=cycle_number,
        message_id=message_id,
    )
    await shared_narrative_context_service.ingest(
        db,
        project_id,
        content=content,
        source_type="user_message",
        source_id=str(message_id),
        source_excerpt=content,
    )
    await db.projects.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {"updated_at": datetime.utcnow()}}
    )
    bible = await rebuild_story_bible(db, project_id, cycle_number=cycle_number)
    await emit_project_event(
        db, project_id, "user_message",
        cycle_number=cycle_number,
        payload={"message_id": str(message_id), "story_bible_version": bible.get("version")},
    )
    
    return TimelineMessageResponse(**serialize_timeline_message({**message, "_id": result.inserted_id}))


@router.get("/{project_id}/workspace-context")
async def get_project_workspace_context(project_id: str):
    """Retrieve unified context statistics and metrics for the workspace."""
    db = Database.get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    try:
        context = await workspace_context_service.get_workspace_context(db, project_id)
        return context
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
