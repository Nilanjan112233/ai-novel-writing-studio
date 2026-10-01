"""Phase 3A editorial intelligence collections and indexes."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable
from uuid import NAMESPACE_URL, uuid5

from pymongo import ASCENDING, DESCENDING


def _stable_id(kind: str, value: Any) -> str:
    return str(uuid5(NAMESPACE_URL, f"novelforge:{kind}:{value}"))


async def _normalize_reports(db) -> int:
    changed = 0
    async for report in db.editorial_reports.find({}):
        patch = {
            "report_id": report.get("report_id")
            or _stable_id("editorial-report", report["_id"]),
            "subject_type": str(report.get("subject_type") or "legacy"),
            "subject_id": str(report.get("subject_id") or report.get("draft_id") or ""),
            "report_type": str(report.get("report_type") or "editorial"),
            "score": max(0, min(100, int(report.get("score") or 0))),
            "dimension_scores": report.get("dimension_scores") or {},
            "findings": report.get("findings") or [],
            "recommendations": report.get("recommendations") or [],
            "blockers": report.get("blockers") or [],
            "evidence": report.get("evidence") or [],
            "created_at": report.get("created_at") or datetime.utcnow(),
        }
        if any(report.get(key) != value for key, value in patch.items()):
            await db.editorial_reports.update_one(
                {"_id": report["_id"]}, {"$set": patch}
            )
            changed += 1
    return changed


async def _normalize_branches(db) -> int:
    changed = 0
    async for branch in db.revision_branches.find({}):
        patch = {
            "branch_id": branch.get("branch_id")
            or _stable_id("revision-branch", branch["_id"]),
            "status": str(branch.get("status") or "archived").lower(),
            "parent_branch_id": branch.get("parent_branch_id"),
            "created_at": branch.get("created_at") or datetime.utcnow(),
            "updated_at": branch.get("updated_at")
            or branch.get("created_at")
            or datetime.utcnow(),
        }
        if any(branch.get(key) != value for key, value in patch.items()):
            await db.revision_branches.update_one(
                {"_id": branch["_id"]}, {"$set": patch}
            )
            changed += 1
    return changed


async def _normalize_versions(db) -> int:
    changed = 0
    async for version in db.revision_versions.find({}):
        patch = {
            "revision_id": version.get("revision_id")
            or _stable_id("revision-version", version["_id"]),
            "version_number": int(version.get("version_number") or 1),
            "parent_revision_id": version.get("parent_revision_id"),
            "generated_text": str(version.get("generated_text") or ""),
            "created_by": str(version.get("created_by") or "legacy"),
            "generation_metadata": version.get("generation_metadata") or {},
            "created_at": version.get("created_at") or datetime.utcnow(),
        }
        if any(version.get(key) != value for key, value in patch.items()):
            await db.revision_versions.update_one(
                {"_id": version["_id"]}, {"$set": patch}
            )
            changed += 1
    return changed


async def _normalize_scores(db) -> int:
    changed = 0
    async for score in db.editorial_scores.find({}):
        patch = {
            "score_id": score.get("score_id")
            or _stable_id("editorial-score", score["_id"]),
            "subject_type": str(score.get("subject_type") or "legacy"),
            "subject_id": str(score.get("subject_id") or ""),
            "score_type": str(score.get("score_type") or "editorial"),
            "score": max(0, min(100, int(score.get("score") or 0))),
            "dimensions": score.get("dimensions") or {},
            "evidence": score.get("evidence") or [],
            "calculated_at": score.get("calculated_at") or datetime.utcnow(),
        }
        if any(score.get(key) != value for key, value in patch.items()):
            await db.editorial_scores.update_one(
                {"_id": score["_id"]}, {"$set": patch}
            )
            changed += 1
    return changed


async def _create_indexes(db) -> None:
    specs: Iterable[tuple[str, list[tuple[str, int]], Dict[str, Any]]] = [
        (
            "editorial_reports",
            [
                ("project_id", ASCENDING),
                ("subject_type", ASCENDING),
                ("subject_id", ASCENDING),
                ("created_at", DESCENDING),
            ],
            {"name": "editorial_reports_project_subject"},
        ),
        (
            "editorial_reports",
            [
                ("project_id", ASCENDING),
                ("report_type", ASCENDING),
                ("score", ASCENDING),
                ("created_at", DESCENDING),
            ],
            {"name": "editorial_reports_type_score"},
        ),
        (
            "revision_branches",
            [("project_id", ASCENDING), ("branch_id", ASCENDING)],
            {"name": "revision_branches_project_branch", "unique": True},
        ),
        (
            "revision_branches",
            [
                ("project_id", ASCENDING),
                ("source_draft_id", ASCENDING),
                ("status", ASCENDING),
                ("created_at", DESCENDING),
            ],
            {"name": "revision_branches_source"},
        ),
        (
            "revision_versions",
            [
                ("project_id", ASCENDING),
                ("branch_id", ASCENDING),
                ("version_number", ASCENDING),
            ],
            {"name": "revision_versions_branch_version", "unique": True},
        ),
        (
            "editorial_scores",
            [
                ("project_id", ASCENDING),
                ("subject_type", ASCENDING),
                ("subject_id", ASCENDING),
                ("calculated_at", DESCENDING),
            ],
            {"name": "editorial_scores_subject"},
        ),
        (
            "editorial_scores",
            [
                ("project_id", ASCENDING),
                ("score_type", ASCENDING),
                ("calculated_at", DESCENDING),
            ],
            {"name": "editorial_scores_project_type"},
        ),
    ]
    for collection, keys, options in specs:
        await db[collection].create_index(keys, **options)


async def migrate_phase_3a(db) -> Dict[str, Any]:
    reports_normalized = await _normalize_reports(db)
    branches_normalized = await _normalize_branches(db)
    versions_normalized = await _normalize_versions(db)
    scores_normalized = await _normalize_scores(db)
    await _create_indexes(db)
    await db.app_settings.update_one(
        {"_id": "global_settings"},
        {
            "$set": {
                "migrations.phase_3a_completed_at": datetime.utcnow(),
                "migrations.phase_3a_version": 1,
            }
        },
        upsert=True,
    )
    return {
        "editorial_reports_normalized": reports_normalized,
        "revision_branches_normalized": branches_normalized,
        "revision_versions_normalized": versions_normalized,
        "editorial_scores_normalized": scores_normalized,
        "indexes_installed": True,
    }
