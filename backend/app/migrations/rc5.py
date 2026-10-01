"""RC5 presentation-projection indexes."""
from datetime import datetime

from pymongo import ASCENDING, DESCENDING


async def migrate_rc5(db):
    specs = [
        (
            "narrative_analysis_history",
            [("project_id", ASCENDING), ("analysis_id", ASCENDING)],
            {"unique": True, "name": "analysis_history_identity"},
        ),
        (
            "narrative_analysis_history",
            [("project_id", ASCENDING), ("calculated_at", DESCENDING)],
            {"name": "analysis_history_timeline"},
        ),
        (
            "workspace_companion_messages",
            [("project_id", ASCENDING), ("recommendation_key", ASCENDING)],
            {
                "unique": True,
                "partialFilterExpression": {"recommendation_key": {"$type": "string"}},
                "name": "companion_recommendation_identity",
            },
        ),
        (
            "workspace_companion_messages",
            [("project_id", ASCENDING), ("state", ASCENDING), ("priority", DESCENDING)],
            {"name": "companion_recommendation_lifecycle"},
        ),
        (
            "workspace_companion_state",
            [("project_id", ASCENDING)],
            {"unique": True, "name": "companion_project_state"},
        ),
    ]
    for collection, keys, options in specs:
        await db[collection].create_index(keys, **options)
    await db.app_settings.update_one(
        {"_id": "global_settings"},
        {
            "$set": {
                "migrations.rc5_completed_at": datetime.utcnow(),
                "migrations.rc5_version": 1,
            }
        },
        upsert=True,
    )
    return {"indexes_installed": True, "version": 1}

