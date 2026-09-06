"""Indexes for the rebuildable Phase C lexical candidate projection."""
from datetime import datetime
from typing import Any, Dict

from pymongo import ASCENDING


async def migrate_memory_phase_c(db) -> Dict[str, Any]:
    await db.memory_embeddings.create_index(
        [("project_id", ASCENDING), ("active", ASCENDING), ("phase_c_ranker_version", ASCENDING), ("search_terms", ASCENDING)],
        name="memory_phase_c_lexical_terms",
    )
    await db.memory_phase_c_checkpoints.create_index(
        [("project_id", ASCENDING)], name="memory_phase_c_checkpoint", unique=True,
    )
    await db.app_settings.update_one(
        {"_id": "global_settings"},
        {"$set": {"migrations.memory_phase_c_completed_at": datetime.utcnow(), "migrations.memory_phase_c_version": 1}},
        upsert=True,
    )
    return {"version": 1, "bounded_lexical_candidates": True}
