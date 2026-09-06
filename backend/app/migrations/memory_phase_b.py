"""Indexes for rebuildable Phase B atomic and episode projections."""
from datetime import datetime
from typing import Any, Dict

from pymongo import ASCENDING


async def migrate_memory_phase_b(db) -> Dict[str, Any]:
    await db.atomic_memories.create_index(
        [("project_id", ASCENDING), ("memory_id", ASCENDING)],
        name="atomic_memory_identity", unique=True,
    )
    await db.atomic_memories.create_index(
        [("project_id", ASCENDING), ("owner_key", ASCENDING), ("active", ASCENDING)],
        name="atomic_memory_owner",
    )
    await db.atomic_memories.create_index(
        [("project_id", ASCENDING), ("subject", ASCENDING), ("predicate", ASCENDING), ("valid_from_chapter", ASCENDING)],
        name="atomic_memory_story_scope",
    )
    await db.memory_phase_b_checkpoints.create_index(
        [("project_id", ASCENDING)], name="memory_phase_b_checkpoint", unique=True,
    )
    await db.app_settings.update_one(
        {"_id": "global_settings"},
        {"$set": {"migrations.memory_phase_b_completed_at": datetime.utcnow(), "migrations.memory_phase_b_version": 1}},
        upsert=True,
    )
    return {"version": 1, "atomic_episode_memory": True}
