"""Phase 7 Interactive Narrative Studio persistence indexes."""
from datetime import datetime

from pymongo import ASCENDING, DESCENDING


async def migrate_phase_7(db):
    specs = [
        (
            "narrative_conversations",
            [("project_id", ASCENDING), ("turn_id", ASCENDING)],
            {"unique": True, "name": "narrative_conversation_turn_identity"},
        ),
        (
            "narrative_conversations",
            [("project_id", ASCENDING), ("character_name", ASCENDING), ("created_at", DESCENDING)],
            {"name": "narrative_conversation_character_history"},
        ),
        (
            "character_conversation_memories",
            [("project_id", ASCENDING), ("character_name", ASCENDING), ("created_at", DESCENDING)],
            {"name": "character_conversation_memory"},
        ),
        (
            "narrative_assistant_messages",
            [("project_id", ASCENDING), ("created_at", DESCENDING)],
            {"name": "narrative_assistant_history"},
        ),
        (
            "canon_proposals",
            [("project_id", ASCENDING), ("proposal_id", ASCENDING)],
            {"unique": True, "name": "canon_proposal_identity"},
        ),
        (
            "canon_proposals",
            [("project_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)],
            {"name": "canon_proposal_queue"},
        ),
    ]
    for collection, keys, options in specs:
        await db[collection].create_index(keys, **options)
    await db.app_settings.update_one(
        {"_id": "global_settings"},
        {
            "$set": {
                "migrations.phase_7_completed_at": datetime.utcnow(),
                "migrations.phase_7_version": 1,
            }
        },
        upsert=True,
    )
    return {"indexes_installed": True, "version": 1}
