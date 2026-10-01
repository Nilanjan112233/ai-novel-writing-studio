"""RC8 additive integrity indexes and bounded Writer's Room repair."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from pymongo import ASCENDING


async def _deduplicate_scene_request_ids(db) -> int:
    repaired = 0
    groups = db.scene_drafts.aggregate(
        [
            {"$match": {"request_id": {"$type": "string", "$ne": ""}}},
            {
                "$group": {
                    "_id": {
                        "project_id": "$project_id",
                        "scene_id": "$scene_id",
                        "request_id": "$request_id",
                    },
                    "documents": {"$push": {"id": "$_id", "created_at": "$created_at"}},
                    "count": {"$sum": 1},
                }
            },
            {"$match": {"count": {"$gt": 1}}},
        ]
    )
    async for group in groups:
        documents = sorted(
            group.get("documents") or [],
            key=lambda item: (item.get("created_at") or datetime.min, str(item.get("id"))),
        )
        for duplicate in documents[1:]:
            await db.scene_drafts.update_one(
                {"_id": duplicate["id"]},
                {
                    "$unset": {"request_id": ""},
                    "$set": {
                        "legacy_duplicate_request": True,
                        "updated_at": datetime.utcnow(),
                    },
                },
            )
            repaired += 1
    return repaired


async def _repair_writers_room_activation(db) -> int:
    """Restore an approved parent only where legacy exploratory intent is explicit.

    This deliberately avoids guessing about ordinary rewrites. A record is repairable
    only when the active child says Writer's Room in its change reason and its direct
    parent is approved.
    """
    repaired = 0
    query = {
        "active": True,
        "change_reason": {"$regex": "^Writer's Room direction:", "$options": "i"},
        "parent_version_id": {"$type": "string", "$ne": ""},
    }
    async for option in db.scene_drafts.find(query):
        parent = await db.scene_drafts.find_one(
            {
                "project_id": option.get("project_id"),
                "scene_id": option.get("scene_id"),
                "draft_id": option.get("parent_version_id"),
                "status": "approved",
            }
        )
        if not parent:
            continue
        now = datetime.utcnow()
        await db.scene_drafts.update_one(
            {"_id": option["_id"]},
            {
                "$set": {
                    "active": False,
                    "writer_room_source_id": parent.get("draft_id"),
                    "legacy_writer_room_repaired_at": now,
                    "updated_at": now,
                }
            },
        )
        await db.scene_drafts.update_one(
            {"_id": parent["_id"]}, {"$set": {"active": True, "updated_at": now}}
        )
        repaired += 1
    return repaired


async def migrate_rc8(db) -> Dict[str, Any]:
    await db.scene_drafts.update_many(
        {"request_id": ""}, {"$unset": {"request_id": ""}}
    )
    deduplicated_requests = await _deduplicate_scene_request_ids(db)
    repaired_writer_rooms = await _repair_writers_room_activation(db)
    await db.scene_drafts.create_index(
        [
            ("project_id", ASCENDING),
            ("scene_id", ASCENDING),
            ("request_id", ASCENDING),
        ],
        name="scene_drafts_request_identity",
        unique=True,
        partialFilterExpression={"request_id": {"$type": "string"}},
    )
    await db.narrative_assistant_messages.create_index(
        [("project_id", ASCENDING), ("request_id", ASCENDING)],
        name="assistant_message_request_identity",
        unique=True,
        partialFilterExpression={"request_id": {"$type": "string"}},
    )
    normalized_character_fields = 0
    for field in ("goals", "fears", "motivations", "personality"):
        result = await db.character_bibles.update_many(
            {field: {"$type": "string"}},
            [{"$set": {field: [f"${field}"]}}],
        )
        normalized_character_fields += result.modified_count
    await db.app_settings.update_one(
        {"_id": "global_settings"},
        {
            "$set": {
                "migrations.rc8_completed_at": datetime.utcnow(),
                "migrations.rc8_version": 2,
            }
        },
        upsert=True,
    )
    return {
        "deduplicated_scene_requests": deduplicated_requests,
        "repaired_writer_room_activations": repaired_writer_rooms,
        "normalized_character_fields": normalized_character_fields,
    }
