"""Single-flight workspace bootstrap projection for RC6."""
from __future__ import annotations

import hashlib
from time import perf_counter
from datetime import datetime
from typing import Any

from bson import ObjectId

from app.services.narrative_completeness_service import narrative_completeness_service
from app.services.story_bible_service import get_story_bible
from app.services.story_health_service import story_health_service
from app.services.workspace_companion_service import workspace_companion_service
from app.services.narrative_analysis_engine import narrative_analysis_engine


def _serialize(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {("id" if key == "_id" else key): _serialize(item) for key, item in value.items()}
    return value


class WorkspaceBootstrapService:
    async def invalidate(self, db, project_id: str) -> None:
        if ObjectId.is_valid(project_id):
            await db.workspace_bootstrap_cache.delete_one(
                {"project_id": ObjectId(project_id)}
            )

    async def get(self, db, project_id: str) -> dict[str, Any]:
        started = perf_counter()
        timings: dict[str, int] = {}
        if not ObjectId.is_valid(project_id):
            raise ValueError("Invalid project ID")
        pid = ObjectId(project_id)
        project = await db.projects.find_one({"_id": pid, "status": {"$ne": "trashed"}})
        if not project:
            raise ValueError("Project not found")
        latest_event = await db.project_events.find_one(
            {"project_id": pid},
            {"_id": 1, "created_at": 1},
            sort=[("created_at", -1)],
        )
        source_token = hashlib.sha256(
            (
                f"{project.get('updated_at') or project.get('created_at')}|"
                f"{(latest_event or {}).get('_id') or ''}|"
                f"{(latest_event or {}).get('created_at') or ''}"
            ).encode("utf-8")
        ).hexdigest()
        cached = await db.workspace_bootstrap_cache.find_one(
            {"project_id": pid, "source_token": source_token}
        )
        if cached and isinstance(cached.get("payload"), dict):
            return {
                **cached["payload"],
                "cache": {
                    "hit": True,
                    "source_token": source_token,
                    "cached_at": _serialize(cached.get("cached_at")),
                    "total_ms": round((perf_counter() - started) * 1000),
                },
            }
        stage = perf_counter()
        current_chapter_count = await db.chapter_intelligence.count_documents({"project_id": pid, "active": True})
        analysis_snapshot = await db.narrative_analysis_snapshots.find_one({"project_id": pid, "snapshot_type": "current"})
        snapshot_count = int(((analysis_snapshot or {}).get("source_manifest") or {}).get("chapter", {}).get("count") or 0)
        if current_chapter_count != snapshot_count:
            await narrative_analysis_engine.analyze(db, project_id, force=True)
        story_bible = await get_story_bible(db, project_id)
        timings["story_bible_ms"] = round((perf_counter() - stage) * 1000)
        stage = perf_counter()
        health = await db.story_health_snapshots.find_one(
            {"project_id": pid, "snapshot_type": "current"}
        )
        if not health or int(((health or {}).get("metrics") or {}).get("total_chapters") or 0) != current_chapter_count:
            health = await story_health_service.calculate(db, project_id)
        timings["story_health_ms"] = round((perf_counter() - stage) * 1000)
        stage = perf_counter()
        completeness = await db.narrative_completeness_snapshots.find_one(
            {"project_id": pid, "snapshot_type": "current"}
        )
        if not completeness:
            completeness = await narrative_completeness_service.calculate(db, project_id)
        timings["completeness_ms"] = round((perf_counter() - stage) * 1000)
        stage = perf_counter()
        companion = await workspace_companion_service.refresh(db, project_id)
        timings["companion_ms"] = round((perf_counter() - stage) * 1000)
        payload = _serialize({
            "project_id": project_id,
            "project": project,
            "story_bible": story_bible,
            "story_health": health,
            "completeness": completeness,
            "companion": companion,
            "version": "rc6-v1",
            "generated_at": datetime.utcnow(),
            "readiness": {
                "core": "ready",
                "story_bible": "ready",
                "story_health": "ready",
                "completeness": "ready",
                "companion": "ready",
            },
            "performance": {**timings, "total_ms": round((perf_counter() - started) * 1000)},
        })
        await db.workspace_bootstrap_cache.update_one(
            {"project_id": pid},
            {
                "$set": {
                    "source_token": source_token,
                    "payload": payload,
                    "cached_at": datetime.utcnow(),
                },
                "$setOnInsert": {"project_id": pid},
            },
            upsert=True,
        )
        return {
            **payload,
            "cache": {
                "hit": False,
                "source_token": source_token,
                "cached_at": payload["generated_at"],
                "total_ms": payload["performance"]["total_ms"],
            },
        }


workspace_bootstrap_service = WorkspaceBootstrapService()
