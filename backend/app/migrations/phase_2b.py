"""Phase 2B controlled drafting migration and indexes."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable
from uuid import NAMESPACE_URL, uuid5

from pymongo import ASCENDING, DESCENDING


def _stable_id(kind: str, value: Any) -> str:
    return str(uuid5(NAMESPACE_URL, f"novelforge:{kind}:{value}"))


async def _normalize_scene_drafts(db) -> int:
    changed = 0
    async for draft in db.scene_drafts.find({}):
        patch: Dict[str, Any] = {}
        if not draft.get("draft_id"):
            patch["draft_id"] = _stable_id("scene-draft", draft["_id"])
        if not draft.get("scene_id"):
            patch.update(
                {
                    "legacy": True,
                    "active": False,
                    "status": "archived",
                    "version_number": int(draft.get("version_number") or 1),
                }
            )
        else:
            patch.setdefault("version_number", int(draft.get("version_number") or 1))
            patch.setdefault("active", bool(draft.get("active", False)))
            patch.setdefault("status", str(draft.get("status") or "archived").lower())
        patch["generated_text"] = str(
            draft.get("generated_text")
            or draft.get("draft_text")
            or ""
        )
        patch["generation_metadata"] = draft.get("generation_metadata") or {}
        patch["continuity_claims"] = draft.get("continuity_claims") or {}
        patch["generated_by"] = str(draft.get("generated_by") or "legacy")
        patch["parent_version_id"] = draft.get("parent_version_id")
        patch["created_at"] = draft.get("created_at") or datetime.utcnow()
        patch["updated_at"] = draft.get("updated_at") or datetime.utcnow()
        if any(draft.get(key) != value for key, value in patch.items()):
            await db.scene_drafts.update_one({"_id": draft["_id"]}, {"$set": patch})
            changed += 1
    return changed


async def _normalize_continuity(db) -> int:
    changed = 0
    async for report in db.continuity_reports.find({}):
        patch = {
            "report_id": report.get("report_id")
            or _stable_id("continuity-report", report["_id"]),
            "subject_type": report.get("subject_type") or "legacy",
            "subject_id": str(report.get("subject_id") or ""),
            "version_number": int(report.get("version_number") or 0),
            "validation_stage": report.get("validation_stage") or "legacy",
            "result": str(report.get("result") or "WARNING").upper(),
            "missing_knowledge": report.get("missing_knowledge") or [],
            "contradictions": report.get("contradictions") or [],
            "artifact_violations": report.get("artifact_violations") or [],
            "timeline_violations": report.get("timeline_violations") or [],
            "character_violations": report.get("character_violations") or [],
            "power_violations": report.get("power_violations") or [],
            "dependency_violations": report.get("dependency_violations") or [],
            "foreshadow_violations": report.get("foreshadow_violations") or [],
            "chapter_membership_violations": report.get(
                "chapter_membership_violations"
            ) or [],
            "scene_ordering_violations": report.get(
                "scene_ordering_violations"
            ) or [],
            "warnings": report.get("warnings") or [],
            "evidence": report.get("evidence") or [],
            "created_at": report.get("created_at") or datetime.utcnow(),
        }
        if any(report.get(key) != value for key, value in patch.items()):
            await db.continuity_reports.update_one(
                {"_id": report["_id"]}, {"$set": patch}
            )
            changed += 1
    return changed


async def _create_indexes(db) -> None:
    specs: Iterable[tuple[str, list[tuple[str, int]], Dict[str, Any]]] = [
        (
            "scene_drafts",
            [("project_id", ASCENDING), ("draft_id", ASCENDING)],
            {"name": "scene_drafts_project_draft", "unique": True},
        ),
        (
            "scene_drafts",
            [
                ("project_id", ASCENDING),
                ("scene_id", ASCENDING),
                ("version_number", ASCENDING),
            ],
            {
                "name": "scene_drafts_scene_version",
                "unique": True,
                "partialFilterExpression": {"scene_id": {"$type": "string"}},
            },
        ),
        (
            "scene_drafts",
            [
                ("project_id", ASCENDING),
                ("arc_id", ASCENDING),
                ("chapter_plan_id", ASCENDING),
                ("scene_id", ASCENDING),
                ("status", ASCENDING),
                ("active", ASCENDING),
            ],
            {"name": "scene_drafts_review_queue"},
        ),
        (
            "scene_drafts",
            [
                ("project_id", ASCENDING),
                ("scene_id", ASCENDING),
                ("parent_version_id", ASCENDING),
                ("version_number", DESCENDING),
            ],
            {"name": "scene_drafts_lineage"},
        ),
        (
            "chapter_drafts",
            [("project_id", ASCENDING), ("draft_id", ASCENDING)],
            {"name": "chapter_drafts_project_draft", "unique": True},
        ),
        (
            "chapter_drafts",
            [
                ("project_id", ASCENDING),
                ("chapter_plan_id", ASCENDING),
                ("version_number", ASCENDING),
            ],
            {
                "name": "chapter_drafts_chapter_version",
                "unique": True,
                # Discovery drafts intentionally have no chapter_plan_id;
                # preserve structured lineage uniqueness without collapsing
                # all write-first drafts into one null-key record.
                "partialFilterExpression": {"chapter_plan_id": {"$type": "string"}},
            },
        ),
        (
            "chapter_drafts",
            [
                ("project_id", ASCENDING),
                ("arc_id", ASCENDING),
                ("chapter_plan_id", ASCENDING),
                ("status", ASCENDING),
                ("active", ASCENDING),
            ],
            {"name": "chapter_drafts_review_queue"},
        ),
        (
            "chapter_drafts",
            [
                ("project_id", ASCENDING),
                ("chapter_plan_id", ASCENDING),
                ("parent_version_id", ASCENDING),
                ("version_number", DESCENDING),
            ],
            {"name": "chapter_drafts_lineage"},
        ),
        (
            "continuity_reports",
            [("project_id", ASCENDING), ("report_id", ASCENDING)],
            {"name": "continuity_reports_project_report", "unique": True},
        ),
        (
            "continuity_reports",
            [
                ("project_id", ASCENDING),
                ("subject_type", ASCENDING),
                ("subject_id", ASCENDING),
                ("version_number", DESCENDING),
                ("validation_stage", ASCENDING),
                ("result", ASCENDING),
            ],
            {"name": "continuity_reports_subject_result"},
        ),
    ]
    for collection, keys, options in specs:
        await db[collection].create_index(keys, **options)


async def migrate_phase_2b(db) -> Dict[str, Any]:
    scene_drafts_normalized = await _normalize_scene_drafts(db)
    continuity_reports_normalized = await _normalize_continuity(db)
    await _create_indexes(db)
    await db.app_settings.update_one(
        {"_id": "global_settings"},
        {
            "$set": {
                "migrations.phase_2b_completed_at": datetime.utcnow(),
                "migrations.phase_2b_version": 1,
            }
        },
        upsert=True,
    )
    return {
        "scene_drafts_normalized": scene_drafts_normalized,
        "continuity_reports_normalized": continuity_reports_normalized,
        "indexes_installed": True,
    }
