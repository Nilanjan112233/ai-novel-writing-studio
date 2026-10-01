"""Comprehensive product-experience persistence indexes."""
from datetime import datetime

from pymongo import ASCENDING, DESCENDING


async def migrate_product_completion(db):
    specs = [
        (
            "shared_narrative_context",
            [("project_id", ASCENDING), ("context_id", ASCENDING)],
            {"unique": True, "name": "shared_context_identity"},
        ),
        (
            "shared_narrative_context",
            [("project_id", ASCENDING), ("dedupe_fingerprint", ASCENDING), ("active", ASCENDING)],
            {"name": "shared_context_dedupe"},
        ),
        (
            "shared_narrative_context",
            [("project_id", ASCENDING), ("domain", ASCENDING), ("updated_at", DESCENDING)],
            {"name": "shared_context_domain"},
        ),
        (
            "narrative_completeness_snapshots",
            [("project_id", ASCENDING), ("snapshot_type", ASCENDING)],
            {"unique": True, "name": "narrative_completeness_current"},
        ),
        (
            "narrative_completeness_history",
            [("project_id", ASCENDING), ("calculated_at", DESCENDING)],
            {"name": "narrative_completeness_history"},
        ),
        (
            "workspace_companion_messages",
            [("project_id", ASCENDING), ("message_id", ASCENDING)],
            {"unique": True, "name": "workspace_companion_identity"},
        ),
        (
            "workspace_companion_messages",
            [("project_id", ASCENDING), ("dismissed", ASCENDING), ("created_at", DESCENDING)],
            {"name": "workspace_companion_feed"},
        ),
    ]
    for collection, keys, options in specs:
        await db[collection].create_index(keys, **options)
    await db.app_settings.update_one(
        {"_id": "global_settings"},
        {
            "$set": {
                "migrations.product_completion_completed_at": datetime.utcnow(),
                "migrations.product_completion_version": 1,
            }
        },
        upsert=True,
    )
    return {"indexes_installed": True, "version": 1}
