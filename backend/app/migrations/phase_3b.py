"""Phase 3B manuscript and canon governance migration."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable
from uuid import NAMESPACE_URL, uuid5

from pymongo import ASCENDING, DESCENDING


CANON_SOURCES = {
    "character_bibles": ("character", "name"),
    "power_progressions": ("power", "character"),
    "artifact_registry": ("artifact", "name"),
    "timeline_entries": ("timeline", "title"),
    "knowledge_entries": ("knowledge", "title"),
    "factions": ("faction", "name"),
    "world_bibles": ("world", "name"),
    "mystery_registry": ("mystery", "question"),
    "relationship_graphs": ("relationship", "relationship_id"),
}


def _stable_id(kind: str, value: Any) -> str:
    return str(uuid5(NAMESPACE_URL, f"novelforge:{kind}:{value}"))


def _source_id(document: Dict[str, Any]) -> str:
    return str(
        document.get("source_id")
        or document.get("entry_id")
        or document.get("artifact_id")
        or document.get("progression_id")
        or document.get("relationship_id")
        or document.get("_id")
        or ""
    )


def _public_value(document: Dict[str, Any]) -> Dict[str, Any]:
    omitted = {
        "_id",
        "project_id",
        "created_at",
        "updated_at",
        "cycle_generated",
        "source_version",
    }
    return {key: value for key, value in document.items() if key not in omitted}


async def _normalize_canon(db) -> int:
    changed = 0
    async for record in db.canon_registry.find({}):
        source_collection = str(
            record.get("source_collection")
            or record.get("source")
            or "legacy_canon"
        )
        source_id = str(record.get("source_id") or record.get("_id"))
        fact = str(record.get("fact") or "")
        patch = {
            "canon_id": record.get("canon_id")
            or _stable_id("canon", f"{source_collection}:{source_id}"),
            "canon_type": str(record.get("canon_type") or "world"),
            "source_collection": source_collection,
            "source_id": source_id,
            "source_version": int(record.get("source_version") or 1),
            "authority_level": str(
                record.get("authority_level") or "locked"
            ).lower(),
            "active": bool(record.get("active", True)),
            "subject": str(record.get("subject") or "legacy"),
            "field": str(record.get("field") or "fact"),
            "value": record.get("value", fact),
            "evidence": record.get("evidence")
            or ([fact] if fact else []),
            "created_at": record.get("created_at") or datetime.utcnow(),
            "updated_at": record.get("updated_at")
            or record.get("created_at")
            or datetime.utcnow(),
        }
        if any(record.get(key) != value for key, value in patch.items()):
            await db.canon_registry.update_one(
                {"_id": record["_id"]}, {"$set": patch}
            )
            changed += 1
    return changed


async def _build_canon(db) -> int:
    created = 0
    for collection, (canon_type, subject_field) in CANON_SOURCES.items():
        async for source in db[collection].find({"project_id": {"$exists": True}}):
            source_id = _source_id(source)
            if not source_id:
                continue
            subject = str(
                source.get(subject_field)
                or source.get("title")
                or source.get("name")
                or source_id
            )
            canon_id = _stable_id(
                "canon-source", f"{collection}:{source_id}"
            )
            now = datetime.utcnow()
            result = await db.canon_registry.update_one(
                {"project_id": source["project_id"], "canon_id": canon_id},
                {
                    "$setOnInsert": {
                        "project_id": source["project_id"],
                        "canon_id": canon_id,
                        "canon_type": canon_type,
                        "source_collection": collection,
                        "source_id": source_id,
                        "source_version": int(source.get("version_number") or 1),
                        "authority_level": "approved_source",
                        "active": source.get("status") not in {
                            "rejected",
                            "archived",
                            "abandoned",
                        },
                        "subject": subject,
                        "field": "record",
                        "value": _public_value(source),
                        "evidence": [f"{collection}:{source_id}"],
                        "status": "LOCKED",
                        "created_at": now,
                        "updated_at": now,
                    }
                },
                upsert=True,
            )
            created += int(result.upserted_id is not None)
    return created


async def _normalize_manuscripts(db) -> int:
    changed = 0
    async for manuscript in db.manuscripts.find({}):
        patch = {
            "manuscript_id": manuscript.get("manuscript_id")
            or _stable_id("manuscript", manuscript["_id"]),
            "status": str(manuscript.get("status") or "draft").lower(),
            "active": bool(manuscript.get("active", True)),
            "version": int(manuscript.get("version") or 0),
            "created_at": manuscript.get("created_at") or datetime.utcnow(),
            "updated_at": manuscript.get("updated_at")
            or manuscript.get("created_at")
            or datetime.utcnow(),
        }
        if any(manuscript.get(key) != value for key, value in patch.items()):
            await db.manuscripts.update_one(
                {"_id": manuscript["_id"]}, {"$set": patch}
            )
            changed += 1
    return changed


async def _create_indexes(db) -> None:
    specs: Iterable[tuple[str, list[tuple[str, int]], Dict[str, Any]]] = [
        (
            "manuscripts",
            [
                ("project_id", ASCENDING),
                ("version", DESCENDING),
                ("manuscript_id", ASCENDING),
            ],
            {"name": "manuscripts_project_version"},
        ),
        (
            "manuscript_versions",
            [
                ("project_id", ASCENDING),
                ("manuscript_id", ASCENDING),
                ("version_number", ASCENDING),
            ],
            {
                "name": "manuscript_versions_manuscript_version",
                "unique": True,
            },
        ),
        (
            "manuscript_reports",
            [
                ("project_id", ASCENDING),
                ("manuscript_id", ASCENDING),
                ("version_id", ASCENDING),
                ("report_type", ASCENDING),
                ("created_at", DESCENDING),
            ],
            {"name": "manuscript_reports_subject"},
        ),
        (
            "canon_registry",
            [
                ("project_id", ASCENDING),
                ("canon_type", ASCENDING),
                ("subject", ASCENDING),
                ("field", ASCENDING),
            ],
            {"name": "canon_registry_project_type"},
        ),
        (
            "canon_registry",
            [
                ("project_id", ASCENDING),
                ("active", ASCENDING),
                ("authority_level", ASCENDING),
                ("updated_at", DESCENDING),
            ],
            {"name": "canon_registry_active"},
        ),
        (
            "canon_conflicts",
            [
                ("project_id", ASCENDING),
                ("status", ASCENDING),
                ("severity", ASCENDING),
                ("detected_at", DESCENDING),
            ],
            {"name": "canon_conflicts_project_status"},
        ),
    ]
    for collection, keys, options in specs:
        await db[collection].create_index(keys, **options)


async def migrate_phase_3b(db) -> Dict[str, Any]:
    settings = await db.app_settings.find_one(
        {"_id": "global_settings"},
        {"migrations.phase_3b_version": 1},
    )
    completed_version = int(
        (((settings or {}).get("migrations") or {}).get("phase_3b_version"))
        or 0
    )
    if completed_version >= 1:
        await _create_indexes(db)
        return {
            "canon_records_normalized": 0,
            "canon_records_created": 0,
            "manuscripts_normalized": 0,
            "indexes_installed": True,
        }
    canon_normalized = await _normalize_canon(db)
    canon_created = await _build_canon(db)
    manuscripts_normalized = await _normalize_manuscripts(db)
    await _create_indexes(db)
    await db.app_settings.update_one(
        {"_id": "global_settings"},
        {
            "$set": {
                "migrations.phase_3b_completed_at": datetime.utcnow(),
                "migrations.phase_3b_version": 1,
            }
        },
        upsert=True,
    )
    return {
        "canon_records_normalized": canon_normalized,
        "canon_records_created": canon_created,
        "manuscripts_normalized": manuscripts_normalized,
        "indexes_installed": True,
    }
