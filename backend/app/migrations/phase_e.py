"""Indexes for derived Develop Story delta handoffs and packet telemetry."""
from datetime import datetime
from typing import Any, Dict

from pymongo import ASCENDING


async def migrate_phase_e(db) -> Dict[str, Any]:
    await db.develop_story_handoffs.create_index(
        [
            ("project_id", ASCENDING),
            ("run_id", ASCENDING),
            ("cycle_number", ASCENDING),
            ("specialist", ASCENDING),
        ],
        name="develop_story_handoff_identity",
        unique=True,
    )
    await db.develop_story_handoffs.create_index(
        [("project_id", ASCENDING), ("cycle_number", ASCENDING), ("created_at", ASCENDING)],
        name="develop_story_handoff_cycle",
    )
    await db.app_settings.update_one(
        {"_id": "global_settings"},
        {"$set": {
            "migrations.phase_e_completed_at": datetime.utcnow(),
            "migrations.phase_e_version": 1,
        }},
        upsert=True,
    )
    return {"version": 1, "role_specific_develop_story_context": True}
