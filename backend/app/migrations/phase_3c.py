"""Phase 3C story intelligence and production-readiness migration."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable

from pymongo import ASCENDING, DESCENDING


async def _create_indexes(db) -> None:
    specs: Iterable[tuple[str, list[tuple[str, int]], Dict[str, Any]]] = [
        (
            "chapter_intelligence",
            [("project_id", ASCENDING), ("intelligence_id", ASCENDING)],
            {"name": "chapter_intelligence_project_id", "unique": True},
        ),
        (
            "chapter_intelligence",
            [
                ("project_id", ASCENDING),
                ("chapter_plan_id", ASCENDING),
                ("chapter_draft_version", DESCENDING),
            ],
            {"name": "chapter_intelligence_chapter_version"},
        ),
        (
            "chapter_intelligence",
            [
                ("project_id", ASCENDING),
                ("active", ASCENDING),
                ("chapter_number", ASCENDING),
            ],
            {"name": "chapter_intelligence_memory_order"},
        ),
        (
            "story_audit_reports",
            [
                ("project_id", ASCENDING),
                ("created_at", DESCENDING),
                ("result", ASCENDING),
            ],
            {"name": "story_audits_project_created"},
        ),
        (
            "change_impacts",
            [
                ("project_id", ASCENDING),
                ("status", ASCENDING),
                ("created_at", DESCENDING),
            ],
            {"name": "change_impacts_project_status"},
        ),
        (
            "change_impacts",
            [("project_id", ASCENDING), ("impact_id", ASCENDING)],
            {"name": "change_impacts_project_id", "unique": True},
        ),
        (
            "story_health_snapshots",
            [("project_id", ASCENDING), ("calculated_at", DESCENDING)],
            {"name": "story_health_project_calculated"},
        ),
    ]
    for collection, keys, options in specs:
        await db[collection].create_index(keys, **options)


async def migrate_phase_3c(db) -> Dict[str, Any]:
    await _create_indexes(db)
    await db.app_settings.update_one(
        {"_id": "global_settings"},
        {
            "$set": {
                "migrations.phase_3c_completed_at": datetime.utcnow(),
                "migrations.phase_3c_version": 1,
            }
        },
        upsert=True,
    )
    return {"indexes_installed": True}
