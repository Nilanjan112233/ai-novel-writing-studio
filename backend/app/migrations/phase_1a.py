"""Phase 1A production orchestration data migration."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Iterable, Tuple

from pymongo import ASCENDING, DESCENDING
from app.services.secret_encryption_service import migrate_provider_secrets


async def _deduplicate_singleton(db, collection_name: str, key: str) -> int:
    collection = db[collection_name]
    groups = collection.aggregate(
        [
            {"$match": {key: {"$exists": True}}},
            {
                "$group": {
                    "_id": f"${key}",
                    "ids": {"$push": "$_id"},
                    "count": {"$sum": 1},
                }
            },
            {"$match": {"count": {"$gt": 1}}},
        ]
    )
    deleted = 0
    async for group in groups:
        documents = await collection.find(
            {"_id": {"$in": group["ids"]}},
            {"updated_at": 1, "created_at": 1},
        ).to_list(length=None)
        documents.sort(
            key=lambda item: (
                item.get("updated_at") or item.get("created_at") or datetime.min,
                str(item["_id"]),
            ),
            reverse=True,
        )
        stale_ids = [item["_id"] for item in documents[1:]]
        if stale_ids:
            result = await collection.delete_many({"_id": {"$in": stale_ids}})
            deleted += result.deleted_count
    return deleted


async def _normalize_memory_versions(db) -> Dict[str, int]:
    collection = db.memory_embeddings
    cursor = collection.find(
        {},
        {
            "_id": 1,
            "project_id": 1,
            "source_type": 1,
            "source_id": 1,
            "updated_at": 1,
            "created_at": 1,
        },
    )
    grouped: Dict[Tuple[Any, str, str], list[Dict[str, Any]]] = defaultdict(list)
    async for document in cursor:
        source_id = str(document.get("source_id") or document["_id"])
        grouped[
            (
                document.get("project_id"),
                str(document.get("source_type") or "unknown"),
                source_id,
            )
        ].append(document)

    normalized = 0
    deleted = 0
    for (_, _, source_id), documents in grouped.items():
        documents.sort(
            key=lambda item: (
                item.get("updated_at") or item.get("created_at") or datetime.min,
                str(item["_id"]),
            ),
            reverse=True,
        )
        retained = documents[:2]
        for offset, document in enumerate(reversed(retained), start=1):
            is_latest = document["_id"] == retained[0]["_id"]
            await collection.update_one(
                {"_id": document["_id"]},
                {
                    "$set": {
                        "source_id": source_id,
                        "source_version": offset,
                        "active": is_latest,
                    }
                },
            )
            normalized += 1
        stale_ids = [document["_id"] for document in documents[2:]]
        if stale_ids:
            result = await collection.delete_many({"_id": {"$in": stale_ids}})
            deleted += result.deleted_count
    return {"normalized": normalized, "deleted": deleted}


async def _create_indexes(db) -> None:
    index_specs: Iterable[tuple[str, list[tuple[str, int]], Dict[str, Any]]] = [
        ("projects", [("updated_at", DESCENDING)], {"name": "projects_updated_at"}),
        (
            "projects",
            [("status", ASCENDING), ("updated_at", DESCENDING)],
            {"name": "projects_status_updated_at"},
        ),
        (
            "runs",
            [("project_id", ASCENDING), ("started_at", DESCENDING)],
            {"name": "runs_project_started_at"},
        ),
        (
            "runs",
            [("project_id", ASCENDING), ("status", ASCENDING)],
            {"name": "runs_project_status"},
        ),
        (
            "cycles",
            [("project_id", ASCENDING), ("cycle_number", ASCENDING)],
            {"name": "cycles_project_cycle", "unique": True},
        ),
        (
            "agent_outputs",
            [("project_id", ASCENDING), ("created_at", ASCENDING)],
            {"name": "agent_outputs_project_created_at"},
        ),
        (
            "agent_outputs",
            [("run_id", ASCENDING), ("created_at", ASCENDING)],
            {"name": "agent_outputs_run_created_at"},
        ),
        (
            "questions",
            [
                ("project_id", ASCENDING),
                ("answered", ASCENDING),
                ("created_at", ASCENDING),
            ],
            {"name": "questions_project_answered_created_at"},
        ),
        (
            "timeline_messages",
            [("project_id", ASCENDING), ("created_at", ASCENDING)],
            {"name": "timeline_messages_project_created_at"},
        ),
        (
            "discussion_messages",
            [
                ("project_id", ASCENDING),
                ("cycle_number", DESCENDING),
                ("created_at", DESCENDING),
            ],
            {"name": "discussion_messages_project_cycle_created_at"},
        ),
        (
            "story_bibles",
            [("project_id", ASCENDING)],
            {"name": "story_bibles_project", "unique": True},
        ),
        (
            "memory_embeddings",
            [
                ("project_id", ASCENDING),
                ("source_type", ASCENDING),
                ("source_id", ASCENDING),
                ("source_version", ASCENDING),
            ],
            {"name": "memory_source_version", "unique": True},
        ),
        (
            "memory_embeddings",
            [
                ("project_id", ASCENDING),
                ("active", ASCENDING),
                ("source_type", ASCENDING),
            ],
            {"name": "memory_project_active_source"},
        ),
        (
            "project_events",
            [("project_id", ASCENDING), ("_id", ASCENDING)],
            {"name": "project_events_project_id"},
        ),
        (
            "execution_traces",
            [("project_id", ASCENDING), ("created_at", DESCENDING)],
            {"name": "execution_traces_project_created_at"},
        ),
        (
            "execution_traces",
            [("run_id", ASCENDING)],
            {"name": "execution_traces_run"},
        ),
        (
            "orchestration_plans",
            [("project_id", ASCENDING), ("created_at", DESCENDING)],
            {"name": "orchestration_plans_project_created_at"},
        ),
        (
            "orchestration_plans",
            [("run_id", ASCENDING)],
            {"name": "orchestration_plans_run", "unique": True, "sparse": True},
        ),
        (
            "orchestration_tasks",
            [("plan_id", ASCENDING), ("agent_name", ASCENDING)],
            {"name": "orchestration_tasks_plan_agent", "unique": True},
        ),
        (
            "orchestration_tasks",
            [("plan_id", ASCENDING), ("status", ASCENDING)],
            {"name": "orchestration_tasks_plan_status"},
        ),
    ]
    for collection_name, keys, options in index_specs:
        await db[collection_name].create_index(keys, **options)


async def migrate_phase_1a(db) -> Dict[str, Any]:
    """Normalize Phase 1A identities and install required indexes."""
    story_bibles_deleted = await _deduplicate_singleton(
        db, "story_bibles", "project_id"
    )
    provider_secrets_migrated = await migrate_provider_secrets(db)
    settings_document = await db.app_settings.find_one(
        {"_id": "global_settings"},
        {"migrations.phase_1a_memory_versions": 1},
    )
    memory_migrated = bool(
        ((settings_document or {}).get("migrations") or {}).get(
            "phase_1a_memory_versions"
        )
    )
    if memory_migrated:
        memory = {"normalized": 0, "deleted": 0, "skipped": True}
    else:
        memory = await _normalize_memory_versions(db)
        await db.app_settings.update_one(
            {"_id": "global_settings"},
            {
                "$set": {
                    "migrations.phase_1a_memory_versions": 1,
                    "migrations.phase_1a_completed_at": datetime.utcnow(),
                }
            },
            upsert=True,
        )
    await _create_indexes(db)
    return {
        "story_bibles_deleted": story_bibles_deleted,
        "provider_secrets_migrated": provider_secrets_migrated,
        "memory": memory,
        "indexes_installed": True,
    }
