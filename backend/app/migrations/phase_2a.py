"""Phase 2A arc development, planning, and evolution migration."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable
from uuid import NAMESPACE_URL, uuid5

from pymongo import ASCENDING, DESCENDING

from app.services.arc_development_service import arc_development_service


DEVELOPMENT_STATUS_MAP = {
    "draft": "idea",
    "discussed": "discussion",
    "approved": "approved",
    "active": "active",
    "completed": "completed",
    "archived": "archived",
}


def _stable_id(kind: str, value: Any) -> str:
    return str(uuid5(NAMESPACE_URL, f"novelforge:{kind}:{value}"))


async def _normalize_arcs(db) -> int:
    changed = 0
    current_projects = set()
    async for arc in db.story_arcs.find({}):
        status = str(arc.get("development_status") or "").lower()
        if not status:
            status = DEVELOPMENT_STATUS_MAP.get(
                str(arc.get("approval_status") or "draft").lower(), "idea"
            )
        focus_role = str(arc.get("focus_role") or "").lower()
        if focus_role not in {"current", "next", "future"}:
            focus_role = "current" if status == "active" else "future"
        if focus_role == "current":
            project_key = str(arc.get("project_id"))
            if project_key in current_projects:
                focus_role = "future"
            else:
                current_projects.add(project_key)
        patch = {
            "development_status": status,
            "focus_role": focus_role,
            "arc_maturity_score": int(arc.get("arc_maturity_score") or 0),
            "maturity_threshold": int(
                arc.get("maturity_threshold")
                or arc_development_service.maturity_threshold
            ),
            "maturity_details": arc.get("maturity_details") or {},
            "resolution_direction": str(arc.get("resolution_direction") or ""),
            "updated_at": arc.get("updated_at") or datetime.utcnow(),
        }
        if any(arc.get(key) != value for key, value in patch.items()):
            await db.story_arcs.update_one({"_id": arc["_id"]}, {"$set": patch})
            changed += 1
    return changed


async def _normalize_progressions(db) -> int:
    changed = 0
    async for item in db.character_progressions.find({}):
        patch = {
            "arc_start_state": item.get("arc_start_state")
            or item.get("current_state")
            or "",
            "arc_midpoint_state": item.get("arc_midpoint_state") or "",
            "arc_end_state": item.get("arc_end_state")
            or item.get("desired_state")
            or "",
            "emotional_growth": item.get("emotional_growth") or "",
            "maturity_growth": item.get("maturity_growth")
            or item.get("maturity")
            or "",
            "power_growth": item.get("power_growth") or [],
            "relationship_growth": item.get("relationship_growth")
            or item.get("relationships")
            or [],
            "belief_changes": item.get("belief_changes") or [],
            "goal_changes": item.get("goal_changes") or [],
        }
        if any(item.get(key) != value for key, value in patch.items()):
            await db.character_progressions.update_one(
                {"_id": item["_id"]}, {"$set": patch}
            )
            changed += 1
    return changed


async def _migrate_scenes(db) -> int:
    migrated = 0
    async for legacy in db.scene_registry.find({}):
        project_id = legacy.get("project_id")
        if not project_id:
            continue
        arc = None
        arc_id = legacy.get("arc_id")
        if arc_id:
            arc = await db.story_arcs.find_one(
                {"project_id": project_id, "arc_id": str(arc_id)}
            )
        if not arc and legacy.get("arc"):
            arc = await db.story_arcs.find_one(
                {"project_id": project_id, "title": legacy.get("arc")}
            )
        if not arc:
            continue
        scene_id = _stable_id("scene-plan", legacy["_id"])
        result = await db.scene_plans.update_one(
            {"project_id": project_id, "scene_id": scene_id},
            {
                "$setOnInsert": {
                    "project_id": project_id,
                    "scene_id": scene_id,
                    "arc_id": arc["arc_id"],
                    "chapter_plan_id": None,
                    "title": str(legacy.get("title") or "Legacy scene plan"),
                    "purpose": str(legacy.get("purpose") or ""),
                    "conflict": str(legacy.get("conflict") or ""),
                    "outcome": str(
                        legacy.get("outcome")
                        or legacy.get("summary")
                        or ""
                    ),
                    "character_change": legacy.get("character_change")
                    or legacy.get("emotional_shift")
                    or "",
                    "knowledge_changes": legacy.get("knowledge_changes") or [],
                    "foreshadow_links": legacy.get("foreshadowing") or [],
                    "artifact_interactions": legacy.get("artifact_interactions")
                    or [],
                    "timeline_impacts": legacy.get("timeline_impacts") or [],
                    "character_focus": legacy.get("characters_present") or [],
                    "status": str(legacy.get("status") or "planned").lower(),
                    "order": int(legacy.get("order") or 0),
                    "legacy_source_id": str(legacy["_id"]),
                    "created_at": legacy.get("created_at") or datetime.utcnow(),
                    "updated_at": legacy.get("updated_at") or datetime.utcnow(),
                }
            },
            upsert=True,
        )
        migrated += int(result.upserted_id is not None)
    return migrated


async def _seed_checklists(db) -> int:
    seeded = 0
    async for arc in db.story_arcs.find(
        {"development_status": {"$ne": "archived"}},
        {"project_id": 1, "arc_id": 1},
    ):
        if not arc.get("project_id") or not arc.get("arc_id"):
            continue
        seeded += await arc_development_service.seed_default_checklist(
            db,
            str(arc["project_id"]),
            str(arc["arc_id"]),
            source="migration",
        )
    return seeded


async def _create_indexes(db) -> None:
    specs: Iterable[tuple[str, list[tuple[str, int]], Dict[str, Any]]] = [
        (
            "arc_checklists",
            [("project_id", ASCENDING), ("item_id", ASCENDING)],
            {"name": "arc_checklists_project_item", "unique": True},
        ),
        (
            "arc_checklists",
            [
                ("project_id", ASCENDING),
                ("arc_id", ASCENDING),
                ("priority", ASCENDING),
                ("status", ASCENDING),
                ("dimension", ASCENDING),
            ],
            {"name": "arc_checklists_arc_gate"},
        ),
        (
            "arc_dependencies",
            [("project_id", ASCENDING), ("dependency_id", ASCENDING)],
            {"name": "arc_dependencies_project_id", "unique": True},
        ),
        (
            "arc_dependencies",
            [
                ("project_id", ASCENDING),
                ("arc_id", ASCENDING),
                ("dependency_type", ASCENDING),
                ("status", ASCENDING),
                ("blocking", ASCENDING),
            ],
            {"name": "arc_dependencies_arc_status"},
        ),
        (
            "chapter_plans",
            [("project_id", ASCENDING), ("chapter_plan_id", ASCENDING)],
            {"name": "chapter_plans_project_id", "unique": True},
        ),
        (
            "chapter_plans",
            [
                ("project_id", ASCENDING),
                ("arc_id", ASCENDING),
                ("chapter_number", ASCENDING),
            ],
            {"name": "chapter_plans_arc_number", "unique": True},
        ),
        (
            "chapter_plans",
            [
                ("project_id", ASCENDING),
                ("arc_id", ASCENDING),
                ("status", ASCENDING),
                ("chapter_number", ASCENDING),
            ],
            {"name": "chapter_plans_arc_status"},
        ),
        (
            "scene_plans",
            [("project_id", ASCENDING), ("scene_id", ASCENDING)],
            {"name": "scene_plans_project_id", "unique": True},
        ),
        (
            "scene_plans",
            [
                ("project_id", ASCENDING),
                ("chapter_plan_id", ASCENDING),
                ("order", ASCENDING),
                ("status", ASCENDING),
            ],
            {"name": "scene_plans_chapter_order"},
        ),
        (
            "power_progressions",
            [
                ("project_id", ASCENDING),
                ("arc_id", ASCENDING),
                ("character", ASCENDING),
            ],
            {"name": "power_progressions_arc_character", "unique": True},
        ),
        (
            "foreshadow_chains",
            [("project_id", ASCENDING), ("chain_node_id", ASCENDING)],
            {"name": "foreshadow_chains_project_node", "unique": True},
        ),
        (
            "foreshadow_chains",
            [
                ("project_id", ASCENDING),
                ("foreshadow_id", ASCENDING),
                ("arc_id", ASCENDING),
                ("order", ASCENDING),
            ],
            {"name": "foreshadow_chains_parent_order"},
        ),
        (
            "artifact_evolutions",
            [("project_id", ASCENDING), ("evolution_id", ASCENDING)],
            {"name": "artifact_evolutions_project_id", "unique": True},
        ),
        (
            "artifact_evolutions",
            [
                ("project_id", ASCENDING),
                ("artifact_id", ASCENDING),
                ("arc_id", ASCENDING),
                ("order", ASCENDING),
            ],
            {"name": "artifact_evolutions_parent_order"},
        ),
        (
            "knowledge_evolutions",
            [("project_id", ASCENDING), ("evolution_id", ASCENDING)],
            {"name": "knowledge_evolutions_project_id", "unique": True},
        ),
        (
            "knowledge_evolutions",
            [
                ("project_id", ASCENDING),
                ("knowledge_entry_id", ASCENDING),
                ("arc_id", ASCENDING),
                ("order", ASCENDING),
            ],
            {"name": "knowledge_evolutions_parent_order"},
        ),
        (
            "story_arcs",
            [
                ("project_id", ASCENDING),
                ("focus_role", ASCENDING),
                ("development_status", ASCENDING),
                ("order", ASCENDING),
            ],
            {"name": "story_arcs_focus_status_order"},
        ),
    ]
    for collection, keys, options in specs:
        await db[collection].create_index(keys, **options)


async def migrate_phase_2a(db) -> Dict[str, Any]:
    arcs_normalized = await _normalize_arcs(db)
    progressions_normalized = await _normalize_progressions(db)
    scene_plans_migrated = await _migrate_scenes(db)
    checklist_items_seeded = await _seed_checklists(db)
    await _create_indexes(db)
    await db.app_settings.update_one(
        {"_id": "global_settings"},
        {
            "$set": {
                "migrations.phase_2a_completed_at": datetime.utcnow(),
                "migrations.phase_2a_version": 1,
            }
        },
        upsert=True,
    )
    return {
        "arcs_normalized": arcs_normalized,
        "progressions_normalized": progressions_normalized,
        "scene_plans_migrated": scene_plans_migrated,
        "checklist_items_seeded": checklist_items_seeded,
        "indexes_installed": True,
    }
