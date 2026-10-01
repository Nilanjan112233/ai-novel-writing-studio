"""Phase 1B readiness, arc, timeline, and bounded-memory migration."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable
from uuid import NAMESPACE_URL, uuid5

from pymongo import ASCENDING, DESCENDING


ARC_STATUS_MAP = {
    "planned": "draft",
    "planning": "draft",
    "draft": "draft",
    "discussion": "discussed",
    "discussed": "discussed",
    "approved": "approved",
    "drafting": "active",
    "active": "active",
    "complete": "completed",
    "completed": "completed",
    "archived": "archived",
}


def _stable_id(kind: str, value: Any) -> str:
    return str(uuid5(NAMESPACE_URL, f"novelforge:{kind}:{value}"))


async def _normalize_arcs(db) -> int:
    updated = 0
    async for arc in db.story_arcs.find({}):
        current_status = str(
            arc.get("approval_status")
            or arc.get("completion_status")
            or arc.get("status")
            or "draft"
        ).lower()
        chapter_range = arc.get("chapter_range")
        if not isinstance(chapter_range, list) or len(chapter_range) != 2:
            estimated = int(arc.get("estimated_chapters") or 0)
            chapter_range = [None, estimated or None]
        patch = {
            "arc_id": arc.get("arc_id") or _stable_id("arc", arc["_id"]),
            "approval_status": ARC_STATUS_MAP.get(current_status, "draft"),
            "chapter_range": chapter_range,
            "readiness_status": arc.get("readiness_status") or "NOT_READY",
            "drafting_eligible": bool(arc.get("drafting_eligible", False)),
            "updated_at": arc.get("updated_at") or datetime.utcnow(),
        }
        await db.story_arcs.update_one({"_id": arc["_id"]}, {"$set": patch})
        updated += 1
    return updated


async def _migrate_timeline(db) -> int:
    migrated = 0
    async for legacy in db.story_timelines.find({}):
        project_id = legacy.get("project_id")
        if not project_id:
            continue
        arc_title = str(legacy.get("arc") or legacy.get("arc_title") or "").strip()
        arc = None
        if arc_title:
            arc = await db.story_arcs.find_one(
                {"project_id": project_id, "title": arc_title}
            )
        entry_id = _stable_id("timeline", legacy["_id"])
        consequences = legacy.get("consequences") or legacy.get("summary") or ""
        summary = (
            "; ".join(str(item) for item in consequences)
            if isinstance(consequences, list)
            else str(consequences or "")
        )
        result = await db.timeline_entries.update_one(
            {"project_id": project_id, "entry_id": entry_id},
            {
                "$setOnInsert": {
                    "project_id": project_id,
                    "entry_id": entry_id,
                    "arc_id": (arc or {}).get("arc_id"),
                    "title": str(
                        legacy.get("event")
                        or legacy.get("event_title")
                        or "Legacy timeline event"
                    ),
                    "summary": summary,
                    "importance": str(legacy.get("importance") or "major"),
                    "status": "planned",
                    "certainty": "known",
                    "dependencies": legacy.get("dependencies") or [],
                    "chapter_range": legacy.get("chapter_range") or [],
                    "order": int(legacy.get("chronology") or 0),
                    "legacy_source_id": str(legacy["_id"]),
                    "created_at": legacy.get("created_at") or datetime.utcnow(),
                    "updated_at": legacy.get("updated_at") or datetime.utcnow(),
                }
            },
            upsert=True,
        )
        migrated += int(result.upserted_id is not None)
    return migrated


async def _create_indexes(db) -> None:
    specs: Iterable[tuple[str, list[tuple[str, int]], Dict[str, Any]]] = [
        (
            "story_readiness",
            [("project_id", ASCENDING), ("item_id", ASCENDING)],
            {"name": "readiness_project_item", "unique": True},
        ),
        (
            "story_readiness",
            [
                ("project_id", ASCENDING),
                ("arc_id", ASCENDING),
                ("blocking", ASCENDING),
                ("priority", ASCENDING),
                ("status", ASCENDING),
            ],
            {"name": "readiness_project_arc_gate"},
        ),
        (
            "story_arcs",
            [("project_id", ASCENDING), ("arc_id", ASCENDING)],
            {"name": "story_arcs_project_arc", "unique": True},
        ),
        (
            "story_arcs",
            [
                ("project_id", ASCENDING),
                ("approval_status", ASCENDING),
                ("order", ASCENDING),
            ],
            {"name": "story_arcs_project_lifecycle_order"},
        ),
        (
            "timeline_entries",
            [("project_id", ASCENDING), ("entry_id", ASCENDING)],
            {"name": "timeline_entries_project_entry", "unique": True},
        ),
        (
            "timeline_entries",
            [
                ("project_id", ASCENDING),
                ("arc_id", ASCENDING),
                ("certainty", ASCENDING),
                ("order", ASCENDING),
            ],
            {"name": "timeline_entries_project_arc_certainty_order"},
        ),
        (
            "character_progressions",
            [
                ("project_id", ASCENDING),
                ("arc_id", ASCENDING),
                ("character", ASCENDING),
            ],
            {"name": "character_progressions_arc_character", "unique": True},
        ),
        (
            "knowledge_entries",
            [("project_id", ASCENDING), ("entry_id", ASCENDING)],
            {"name": "knowledge_entries_project_entry", "unique": True},
        ),
        (
            "knowledge_entries",
            [
                ("project_id", ASCENDING),
                ("knowledge_type", ASCENDING),
                ("arc_id", ASCENDING),
            ],
            {"name": "knowledge_entries_project_type_arc"},
        ),
        (
            "foreshadow_registry_v2",
            [("project_id", ASCENDING), ("entry_id", ASCENDING)],
            {"name": "foreshadow_v2_project_entry", "unique": True},
        ),
        (
            "foreshadow_registry_v2",
            [
                ("project_id", ASCENDING),
                ("status", ASCENDING),
                ("payoff_arc_id", ASCENDING),
            ],
            {"name": "foreshadow_v2_project_status_payoff"},
        ),
        (
            "artifact_registry",
            [("project_id", ASCENDING), ("artifact_id", ASCENDING)],
            {"name": "artifact_registry_project_artifact", "unique": True},
        ),
        (
            "artifact_registry",
            [("project_id", ASCENDING), ("owner", ASCENDING), ("status", ASCENDING)],
            {"name": "artifact_registry_project_owner_status"},
        ),
        (
            "agent_memories",
            [
                ("project_id", ASCENDING),
                ("agent_name", ASCENDING),
                ("memory_type", ASCENDING),
                ("source_type", ASCENDING),
                ("source_id", ASCENDING),
                ("source_version", ASCENDING),
            ],
            {"name": "agent_memories_source_version", "unique": True},
        ),
        (
            "agent_memories",
            [
                ("project_id", ASCENDING),
                ("agent_name", ASCENDING),
                ("memory_type", ASCENDING),
                ("active", ASCENDING),
                ("updated_at", DESCENDING),
            ],
            {"name": "agent_memories_agent_tier_active"},
        ),
    ]
    for collection, keys, options in specs:
        await db[collection].create_index(keys, **options)


async def migrate_phase_1b(db) -> Dict[str, Any]:
    arcs_normalized = await _normalize_arcs(db)
    timeline_entries_migrated = await _migrate_timeline(db)
    await _create_indexes(db)
    await db.app_settings.update_one(
        {"_id": "global_settings"},
        {
            "$set": {
                "migrations.phase_1b_completed_at": datetime.utcnow(),
                "migrations.phase_1b_version": 1,
            }
        },
        upsert=True,
    )
    return {
        "arcs_normalized": arcs_normalized,
        "timeline_entries_migrated": timeline_entries_migrated,
        "indexes_installed": True,
    }
