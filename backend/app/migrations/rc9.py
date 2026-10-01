"""RC9 additive operational metadata and indexes.

This migration does not alter narrative records. It only introduces bounded
operational collections used for backup, recovery, feedback, and support.
"""
from datetime import datetime
from typing import Any, Dict

from pymongo import ASCENDING, DESCENDING

from app.core.version import APP_VERSION, SCHEMA_VERSION


async def migrate_rc9(db) -> Dict[str, Any]:
    await db.project_backups.create_index(
        [("project_id", ASCENDING), ("created_at", DESCENDING)],
        name="project_backup_history",
    )
    await db.project_backups.create_index(
        [("backup_id", ASCENDING)], name="project_backup_identity", unique=True
    )
    await db.restore_operations.create_index(
        [("backup_id", ASCENDING), ("created_at", DESCENDING)],
        name="restore_operation_history",
    )
    await db.restore_operations.create_index(
        [("request_id", ASCENDING)],
        name="restore_request_identity",
        unique=True,
        sparse=True,
    )
    await db.beta_feedback.create_index(
        [("created_at", DESCENDING)], name="beta_feedback_created_at"
    )
    await db.beta_feedback.create_index(
        [("feedback_id", ASCENDING)], name="beta_feedback_identity", unique=True
    )
    await db.support_bundles.create_index(
        [("support_id", ASCENDING)], name="support_bundle_identity", unique=True
    )
    await db.migration_runs.create_index(
        [("run_id", ASCENDING), ("migration", ASCENDING)],
        name="migration_run_step",
        unique=True,
    )
    legacy_projects = await db.projects.update_many(
        {"schema_version": {"$exists": False}},
        {"$set": {
            "schema_version": SCHEMA_VERSION,
            "created_with_app_version": "legacy_pre_rc9",
            "last_migrated_at": datetime.utcnow(),
            "last_migrated_with_app_version": APP_VERSION,
        }},
    )
    await db.app_settings.update_one(
        {"_id": "global_settings"},
        {
            "$set": {
                "migrations.rc9_completed_at": datetime.utcnow(),
                "migrations.rc9_version": 1,
                "application.version": APP_VERSION,
                "application.schema_version": SCHEMA_VERSION,
            }
        },
        upsert=True,
    )
    return {
        "version": 1,
        "schema_version": SCHEMA_VERSION,
        "legacy_projects_normalized": legacy_projects.modified_count,
    }
