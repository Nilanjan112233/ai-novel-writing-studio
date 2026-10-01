"""Post-RC5 compatibility and lifecycle hardening migration."""
from __future__ import annotations

from datetime import datetime

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING


async def _normalize_project_ids(db, collection_name: str) -> int:
    changed = 0
    cursor = db[collection_name].find({"project_id": {"$type": "string"}})
    async for row in cursor:
        raw = row.get("project_id")
        if not raw or not ObjectId.is_valid(raw):
            continue
        result = await db[collection_name].update_one(
            {"_id": row["_id"], "project_id": raw},
            {"$set": {"project_id": ObjectId(raw)}},
        )
        changed += result.modified_count
    return changed


async def _backfill_paragraph_children(db, collection_name: str) -> int:
    changed = 0
    cursor = db[collection_name].find({"project_id": {"$exists": False}})
    async for row in cursor:
        paragraph_id = row.get("paragraph_id")
        if not paragraph_id:
            continue
        owner = await db.scene_paragraphs.find_one(
            {"paragraph_id": paragraph_id}, {"project_id": 1}
        )
        if not owner or not owner.get("project_id"):
            continue
        project_id = owner["project_id"]
        if isinstance(project_id, str) and ObjectId.is_valid(project_id):
            project_id = ObjectId(project_id)
        result = await db[collection_name].update_one(
            {"_id": row["_id"], "project_id": {"$exists": False}},
            {"$set": {"project_id": project_id}},
        )
        changed += result.modified_count
    return changed


async def migrate_post_rc5_hardening(db):
    normalized = {}
    for name in (
        "scene_paragraphs",
        "paragraph_content",
        "paragraph_versions",
        "paragraph_comments",
        "paragraph_suggestions",
        "orchestration_plans",
        "orchestration_tasks",
    ):
        normalized[name] = await _normalize_project_ids(db, name)

    backfilled = {}
    for name in ("paragraph_versions", "paragraph_suggestions"):
        backfilled[name] = await _backfill_paragraph_children(db, name)

    specs = (
        ("scene_paragraphs", [("project_id", ASCENDING), ("scene_id", ASCENDING), ("order", ASCENDING)], {"name": "paragraphs_project_scene_order"}),
        ("paragraph_content", [("project_id", ASCENDING), ("paragraph_id", ASCENDING)], {"name": "paragraph_content_project"}),
        ("paragraph_versions", [("project_id", ASCENDING), ("paragraph_id", ASCENDING), ("version_number", DESCENDING)], {"name": "paragraph_versions_project"}),
        ("paragraph_comments", [("project_id", ASCENDING), ("paragraph_id", ASCENDING), ("created_at", DESCENDING)], {"name": "paragraph_comments_project"}),
        ("paragraph_suggestions", [("project_id", ASCENDING), ("paragraph_id", ASCENDING), ("created_at", DESCENDING)], {"name": "paragraph_suggestions_project"}),
        ("narrative_analysis_jobs", [("project_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)], {"name": "narrative_jobs_status"}),
        ("story_bible_sections", [("project_id", ASCENDING), ("section", ASCENDING)], {"unique": True, "name": "story_bible_section_identity"}),
        ("publication_exports", [("project_id", ASCENDING), ("created_at", DESCENDING)], {"name": "publication_exports_project"}),
    )
    for collection, keys, options in specs:
        await db[collection].create_index(keys, **options)

    segmented_bibles = 0
    cursor = db.story_bibles.find({
        "sections": {"$type": "object"},
        "storage_mode": {"$ne": "segmented"},
    })
    async for bible in cursor:
        sections = bible.get("sections") or {}
        version = int(bible.get("version") or 1)
        now = datetime.utcnow()
        for section_name, value in sections.items():
            await db.story_bible_sections.update_one(
                {"project_id": bible["project_id"], "section": section_name},
                {
                    "$set": {"value": value, "version": version, "updated_at": now},
                    "$setOnInsert": {"created_at": now},
                },
                upsert=True,
            )
        await db.story_bibles.update_one(
            {"_id": bible["_id"]},
            {
                "$set": {
                    "storage_mode": "segmented",
                    "section_names": list(sections),
                    "updated_at": now,
                },
                "$unset": {"sections": ""},
            },
        )
        segmented_bibles += 1

    await db.app_settings.update_one(
        {"_id": "global_settings"},
        {
            "$set": {
                "migrations.post_rc5_hardening_completed_at": datetime.utcnow(),
                "migrations.post_rc5_hardening_version": 1,
            }
        },
        upsert=True,
    )
    return {
        "normalized": normalized,
        "backfilled": backfilled,
        "segmented_bibles": segmented_bibles,
        "version": 1,
    }
