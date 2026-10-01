"""Project-owned story intelligence, audits, health, and impact previews."""
from __future__ import annotations

from datetime import datetime
import asyncio
from typing import Any, Dict

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.core.database import Database
from app.services.change_impact_service import (
    SUPPORTED_CHANGE_TYPES,
    change_impact_service,
)
from app.services.chapter_intelligence_service import chapter_intelligence_service
from app.services.story_auditor_service import story_auditor_service
from app.services.story_health_service import story_health_service
from app.services.narrative_analysis_engine import narrative_analysis_engine
from app.services.project_event_service import emit_project_event


router = APIRouter(prefix="/api/projects/{project_id}", tags=["story-intelligence"])
_RECOVERY_TASKS: set[asyncio.Task] = set()


async def _background_analysis(db, project_id: str, job_id: str, force: bool, changed_sources: list[str]) -> None:
    try:
        await db.narrative_analysis_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"status": "running", "started_at": datetime.utcnow()}},
        )
        await emit_project_event(
            db, project_id, "narrative_analysis_started", payload={"job_id": job_id}
        )
        result = await narrative_analysis_engine.analyze(
            db, project_id, force=force, changed_sources=changed_sources
        )
        await db.narrative_analysis_jobs.update_one(
            {"job_id": job_id},
            {"$set": {
                "status": "complete",
                "analysis_id": result["snapshot"]["analysis_id"],
                "completed_at": datetime.utcnow(),
            }},
        )
        await emit_project_event(
            db,
            project_id,
            "narrative_analysis_completed",
            payload={"job_id": job_id, "analysis_id": result["snapshot"]["analysis_id"]},
        )
    except Exception as exc:
        await db.narrative_analysis_jobs.update_one(
            {"job_id": job_id},
            {"$set": {
                "status": "failed",
                "error": str(exc),
                "completed_at": datetime.utcnow(),
            }},
        )
        await emit_project_event(
            db,
            project_id,
            "narrative_analysis_failed",
            payload={"job_id": job_id, "message": "Narrative analysis could not finish."},
        )


async def recover_narrative_analysis_jobs(db) -> int:
    """Resume queued/interrupted analysis jobs after an API process restart."""
    await db.narrative_analysis_jobs.update_many(
        {"status": "running"},
        {
            "$set": {"status": "queued", "recovered_at": datetime.utcnow()},
            "$inc": {"recovery_count": 1},
        },
    )
    queued = await db.narrative_analysis_jobs.find(
        {"status": "queued"}
    ).sort("created_at", 1).to_list(length=100)
    for job in queued:
        task = asyncio.create_task(
            _background_analysis(
                db,
                str(job["project_id"]),
                str(job["job_id"]),
                bool(job.get("force")),
                [str(value) for value in job.get("changed_sources") or []],
            )
        )
        _RECOVERY_TASKS.add(task)
        task.add_done_callback(_RECOVERY_TASKS.discard)
    return len(queued)


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


@router.get("/chapter-intelligence")
async def get_chapter_intelligence(
    project_id: str,
    active: bool | None = Query(default=True),
):
    db = Database.get_db()
    pid = await _project(db, project_id)
    query: Dict[str, Any] = {"project_id": pid}
    if active is not None:
        query["active"] = active
    docs = await db.chapter_intelligence.find(query).sort(
        [("chapter_number", 1), ("chapter_draft_version", -1)]
    ).to_list(length=10000)
    return _serialize(docs)


@router.post("/chapter-intelligence/backfill")
async def backfill_chapter_intelligence(project_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await chapter_intelligence_service.backfill(db, project_id)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/chapter-intelligence/memory")
async def get_chapter_intelligence_memory(
    project_id: str,
    recent_limit: int = Query(default=12, ge=1, le=50),
    obligation_limit: int = Query(default=12, ge=1, le=50),
):
    db = Database.get_db()
    await _project(db, project_id)
    return await chapter_intelligence_service.memory_packet(
        db,
        project_id,
        recent_limit=recent_limit,
        obligation_limit=obligation_limit,
    )


@router.post("/story-audit")
async def run_story_audit(project_id: str, payload: dict | None = None):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await story_auditor_service.run(
            db,
            project_id,
            include_agent=bool((payload or {}).get("include_agent", True)),
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/story-audits")
async def get_story_audits(
    project_id: str,
    limit: int = Query(default=20, ge=1, le=200),
):
    db = Database.get_db()
    pid = await _project(db, project_id)
    docs = await db.story_audit_reports.find(
        {"project_id": pid}
    ).sort("created_at", -1).to_list(length=limit)
    return _serialize(docs)


@router.get("/story-health")
async def get_story_health(project_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await story_health_service.calculate(db, project_id)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/narrative-intelligence")
async def get_narrative_intelligence(project_id: str):
    db = Database.get_db()
    await _project(db, project_id)
    pid = ObjectId(project_id)
    current_chapters = await db.chapter_intelligence.count_documents({"project_id": pid, "active": True})
    snapshot = await db.narrative_analysis_snapshots.find_one({"project_id": pid, "snapshot_type": "current"})
    indexed_chapters = int(((snapshot or {}).get("source_manifest") or {}).get("chapter", {}).get("count") or 0)
    if current_chapters != indexed_chapters:
        await narrative_analysis_engine.analyze(db, project_id, force=True)
    return await narrative_analysis_engine.platform(db, project_id)


@router.post("/narrative-analysis")
async def run_narrative_analysis(project_id: str, background_tasks: BackgroundTasks, payload: dict | None = None):
    db = Database.get_db()
    pid = await _project(db, project_id)
    body = payload or {}
    force = bool(body.get("force", False))
    changed_sources = [str(value) for value in body.get("changed_sources") or []]
    if not body.get("background"):
        return await narrative_analysis_engine.analyze(db, project_id, force=force, changed_sources=changed_sources)
    existing = await db.narrative_analysis_jobs.find_one(
        {"project_id": pid, "status": {"$in": ["queued", "running"]}},
        sort=[("created_at", -1)],
    )
    if existing:
        return _serialize({**existing, "coalesced": True})
    from uuid import uuid4
    job = {
        "project_id": pid,
        "job_id": str(uuid4()),
        "status": "queued",
        "force": force,
        "changed_sources": changed_sources,
        "created_at": datetime.utcnow(),
    }
    await db.narrative_analysis_jobs.insert_one(job)
    background_tasks.add_task(_background_analysis, db, project_id, job["job_id"], force, changed_sources)
    return _serialize(job)


@router.get("/narrative-analysis/jobs/{job_id}")
async def get_narrative_analysis_job(project_id: str, job_id: str):
    db = Database.get_db()
    pid = await _project(db, project_id)
    job = await db.narrative_analysis_jobs.find_one({"project_id": pid, "job_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Analysis job not found")
    return _serialize(job)


@router.get("/narrative-intelligence/{domain}")
async def get_narrative_domain(project_id: str, domain: str):
    if domain not in {"character", "canon", "timeline", "plot", "pacing", "continuity", "balance"}:
        raise HTTPException(status_code=400, detail="Unsupported intelligence domain")
    db = Database.get_db()
    await _project(db, project_id)
    platform = await narrative_analysis_engine.platform(db, project_id)
    return {"domain": domain, "score": platform["snapshot"]["scores"][domain], "findings": platform["domains"][domain], "analysis_id": platform["snapshot"]["analysis_id"]}


@router.put("/narrative-findings/{finding_id}/status")
async def update_narrative_finding_status(project_id: str, finding_id: str, payload: dict):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await narrative_analysis_engine.set_finding_status(db, project_id, finding_id, str(payload.get("status") or ""))
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/change-impact")
async def preview_change_impact(project_id: str, payload: dict):
    db = Database.get_db()
    await _project(db, project_id)
    change_type = str(payload.get("change_type") or "")
    if change_type not in SUPPORTED_CHANGE_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported change type")
    try:
        return await change_impact_service.analyze(
            db,
            project_id,
            change_type=change_type,
            target=dict(payload.get("target") or {}),
            proposed_change=dict(payload.get("proposed_change") or {}),
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/change-impacts")
async def get_change_impacts(
    project_id: str,
    limit: int = Query(default=20, ge=1, le=200),
):
    db = Database.get_db()
    await _project(db, project_id)
    return await change_impact_service.latest(db, project_id, limit=limit)


@router.put("/change-impacts/{impact_id}/status")
async def update_change_impact_status(
    project_id: str,
    impact_id: str,
    payload: dict,
):
    db = Database.get_db()
    await _project(db, project_id)
    try:
        return await change_impact_service.set_status(
            db,
            project_id,
            impact_id,
            str(payload.get("status") or ""),
        )
    except ValueError as exc:
        raise _conflict(exc) from exc
