"""Indexes for resumable, project-scoped Native memory maintenance."""
from datetime import datetime
from typing import Any, Dict

from pymongo import ASCENDING, DESCENDING


OWNER_COLLECTIONS = (
    "timeline_messages", "agent_outputs", "character_bibles", "relationship_graphs",
    "world_bibles", "plot_threads", "theme_registry", "foreshadow_registry",
    "continuity_reports", "scene_registry", "story_timelines", "questions",
    "canon_registry", "decision_registry", "story_visions", "story_arcs",
    "story_readiness", "timeline_entries", "character_progressions", "knowledge_entries",
    "foreshadow_registry_v2", "artifact_registry", "power_systems", "character_journeys",
    "mystery_registry", "ai_insights", "factions", "arc_checklists", "arc_dependencies",
    "chapter_plans", "scene_plans", "power_progressions", "foreshadow_chains",
    "artifact_evolutions", "knowledge_evolutions", "chapter_intelligence",
)


async def migrate_memory_phase_a(db) -> Dict[str, Any]:
    await db.memory_index_checkpoints.create_index(
        [("project_id", ASCENDING)], name="memory_index_checkpoint_project", unique=True,
    )
    await db.memory_index_events.create_index(
        [("event_key", ASCENDING)], name="memory_index_event_identity", unique=True,
    )
    await db.memory_index_events.create_index(
        [("project_id", ASCENDING), ("status", ASCENDING), ("sequence", ASCENDING)],
        name="memory_index_pending_by_project",
    )
    await db.memory_index_staging.create_index(
        [
            ("project_id", ASCENDING), ("rebuild_id", ASCENDING),
            ("source_type", ASCENDING), ("logical_source_id", ASCENDING),
            ("source_version", ASCENDING),
        ],
        name="memory_index_staging_identity",
        unique=True,
    )
    await db.memory_index_staging.create_index(
        [("project_id", ASCENDING), ("rebuild_id", ASCENDING), ("physical_source_id", ASCENDING)],
        name="memory_index_staging_resume",
    )
    for collection_name in OWNER_COLLECTIONS:
        await db[collection_name].create_index(
            [("project_id", ASCENDING), ("updated_at", ASCENDING)],
            name=f"{collection_name}_memory_changes",
        )
    await db.app_settings.update_one(
        {"_id": "global_settings"},
        {"$set": {
            "migrations.memory_phase_a_completed_at": datetime.utcnow(),
            "migrations.memory_phase_a_version": 1,
        }},
        upsert=True,
    )
    return {"version": 1, "checkpointed_incremental_memory": True}
