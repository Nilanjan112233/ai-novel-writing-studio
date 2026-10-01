"""Additive metadata/indexes for Story Studio and Discovery Writing."""
from datetime import datetime
from typing import Any, Dict

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import OperationFailure


async def migrate_evolution(db) -> Dict[str, Any]:
    # The mature RC9 index predates write-first drafts and treats every
    # chapter_plan_id=null as the same chapter. Replace it with the same
    # uniqueness rule for structured drafts only; discovery drafts use their
    # own draft/version lineage.
    try:
        await db.chapter_drafts.drop_index("chapter_drafts_chapter_version")
    except OperationFailure:
        pass
    await db.chapter_drafts.create_index(
        [("project_id", ASCENDING), ("chapter_plan_id", ASCENDING), ("version_number", ASCENDING)],
        name="chapter_drafts_chapter_version",
        unique=True,
        partialFilterExpression={"chapter_plan_id": {"$type": "string"}},
    )
    await db.story_studio_jobs.create_index(
        [("project_id", ASCENDING), ("created_at", DESCENDING)],
        name="story_studio_job_history",
    )
    await db.story_studio_jobs.create_index(
        [("project_id", ASCENDING), ("request_id", ASCENDING)],
        name="story_studio_request_identity",
        unique=True,
        sparse=True,
    )
    await db.chapter_drafts.create_index(
        [("project_id", ASCENDING), ("workflow_mode", ASCENDING), ("created_at", DESCENDING)],
        name="chapter_draft_workflow_mode",
    )
    await db.discovery_extractions.create_index(
        [("project_id", ASCENDING), ("source_draft_id", ASCENDING)],
        name="discovery_extraction_source",
        unique=True,
    )
    await db.app_settings.update_one(
        {"_id": "global_settings"},
        {"$set": {"migrations.evolution_completed_at": datetime.utcnow(), "migrations.evolution_version": 2}},
        upsert=True,
    )
    return {"version": 2, "story_studio_jobs": True, "discovery_extractions": True}
