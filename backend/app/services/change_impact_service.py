"""Deterministic, project-scoped change impact previews."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Iterable
from uuid import uuid4

from bson import ObjectId


SUPPORTED_CHANGE_TYPES = {
    "character_removal",
    "character_addition",
    "timeline_change",
    "arc_change",
    "ending_change",
    "mystery_change",
    "artifact_change",
    "relationship_change",
    "canon_change",
    "major_event_change",
}

COLLECTION_GROUPS = {
    "chapters": ("chapter_plans", "chapter_drafts", "chapter_intelligence"),
    "scenes": ("scene_plans", "scene_drafts"),
    "characters": ("character_bibles", "character_journeys", "character_progressions"),
    "plot_threads": ("plot_threads", "mystery_registry", "foreshadow_registry_v2"),
    "timeline": ("timeline_entries",),
    "arcs": ("story_arcs", "arc_dependencies"),
    "canon_entries": ("canon_registry",),
    "knowledge_entries": ("knowledge_entries", "knowledge_evolutions"),
    "foreshadow_records": ("foreshadow_registry_v2", "foreshadow_chains"),
    "artifacts": ("artifact_registry", "artifact_evolutions"),
    "manuscripts": ("manuscripts", "manuscript_versions"),
    "editorial_reports": (
        "editorial_reports",
        "editorial_scores",
        "revision_branches",
        "revision_versions",
        "manuscript_reports",
    ),
}

ID_FIELDS = (
    "intelligence_id",
    "chapter_plan_id",
    "scene_id",
    "draft_id",
    "entry_id",
    "artifact_id",
    "relationship_id",
    "mystery_id",
    "canon_id",
    "manuscript_id",
    "report_id",
    "arc_id",
)


def _serialize(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {
            ("id" if key == "_id" else key): _serialize(item)
            for key, item in value.items()
        }
    return value


def _contains(value: Any, needles: set[str]) -> bool:
    if isinstance(value, dict):
        return any(_contains(item, needles) for item in value.values())
    if isinstance(value, list):
        return any(_contains(item, needles) for item in value)
    normalized = str(value or "").strip().lower()
    if not normalized:
        return False
    return any(
        needle == normalized
        or (len(needle) >= 4 and needle in normalized)
        for needle in needles
    )


def _identity(document: Dict[str, Any]) -> str:
    for field in ID_FIELDS:
        if document.get(field):
            return str(document[field])
    return str(document.get("_id") or "")


def _title(document: Dict[str, Any], fallback: str) -> str:
    return str(
        document.get("title")
        or document.get("name")
        or document.get("question")
        or document.get("subject")
        or document.get("summary")
        or fallback
    )


class ChangeImpactService:
    async def analyze(
        self,
        db,
        project_id: str,
        *,
        change_type: str,
        target: Dict[str, Any],
        proposed_change: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        if change_type not in SUPPORTED_CHANGE_TYPES:
            raise ValueError("Unsupported change type")
        if not ObjectId.is_valid(project_id):
            raise ValueError("Invalid project ID")
        pid = ObjectId(project_id)
        if not await db.projects.find_one({"_id": pid}):
            raise ValueError("Project not found")
        target_values = {
            str(value).strip().lower()
            for value in target.values()
            if str(value or "").strip()
        }
        if not target_values and change_type != "character_addition":
            raise ValueError("Impact analysis requires a target identity")

        affected: Dict[str, list[Dict[str, Any]]] = {
            group: [] for group in COLLECTION_GROUPS
        }
        seen: Dict[str, set[tuple[str, str]]] = {
            group: set() for group in COLLECTION_GROUPS
        }
        all_collections = {
            collection
            for collections in COLLECTION_GROUPS.values()
            for collection in collections
        }
        matched_chapter_plans: set[str] = set()
        matched_chapter_drafts: set[str] = set()

        for collection in all_collections:
            documents = await db[collection].find(
                {"project_id": pid}
            ).to_list(length=10000)
            for document in documents:
                matched = (
                    change_type == "character_addition"
                    and collection in {"story_arcs", "chapter_plans", "scene_plans"}
                ) or _contains(document, target_values)
                if not matched:
                    continue
                identity = _identity(document)
                if collection in {
                    "chapter_plans",
                    "chapter_drafts",
                    "chapter_intelligence",
                }:
                    chapter_plan_id = str(document.get("chapter_plan_id") or "")
                    if chapter_plan_id:
                        matched_chapter_plans.add(chapter_plan_id)
                    chapter_draft_id = str(document.get("chapter_draft_id") or "")
                    if chapter_draft_id:
                        matched_chapter_drafts.add(chapter_draft_id)
                for group, collections in COLLECTION_GROUPS.items():
                    if collection not in collections:
                        continue
                    marker = (collection, identity)
                    if marker in seen[group]:
                        continue
                    seen[group].add(marker)
                    affected[group].append(
                        {
                            "collection": collection,
                            "id": identity,
                            "title": _title(document, identity),
                            "reason": (
                                "Contains the requested target or a direct linked reference"
                            ),
                        }
                    )

        if matched_chapter_plans:
            chapter_drafts = await db.chapter_drafts.find(
                {
                    "project_id": pid,
                    "chapter_plan_id": {"$in": list(matched_chapter_plans)},
                }
            ).to_list(length=10000)
            matched_chapter_drafts.update(
                str(item.get("draft_id")) for item in chapter_drafts
            )
            for item in chapter_drafts:
                marker = ("chapter_drafts", str(item.get("draft_id")))
                if marker not in seen["chapters"]:
                    seen["chapters"].add(marker)
                    affected["chapters"].append(
                        {
                            "collection": "chapter_drafts",
                            "id": str(item.get("draft_id")),
                            "title": f"Chapter draft v{item.get('version_number', 1)}",
                            "reason": "Draft derives from an affected chapter plan",
                        }
                    )

        if matched_chapter_drafts:
            manuscript_versions = await db.manuscript_versions.find(
                {
                    "project_id": pid,
                    "source_chapters.chapter_draft_id": {
                        "$in": list(matched_chapter_drafts)
                    },
                }
            ).to_list(length=10000)
            for item in manuscript_versions:
                marker = ("manuscript_versions", str(item.get("version_id")))
                if marker in seen["manuscripts"]:
                    continue
                seen["manuscripts"].add(marker)
                affected["manuscripts"].append(
                    {
                        "collection": "manuscript_versions",
                        "id": str(item.get("version_id")),
                        "title": f"Manuscript version {item.get('version_number')}",
                        "reason": "Manuscript contains an affected chapter draft",
                    }
                )

        counts = {group: len(items) for group, items in affected.items()}
        total = sum(counts.values())
        risk = "low"
        if (
            counts["canon_entries"]
            or counts["manuscripts"]
            or (change_type in {"canon_change", "timeline_change", "major_event_change"} and total >= 5)
            or total >= 15
        ):
            risk = "high"
        elif total >= 5:
            risk = "medium"
        now = datetime.utcnow()
        record = {
            "project_id": pid,
            "impact_id": str(uuid4()),
            "change_type": change_type,
            "target": target,
            "proposed_change": proposed_change or {},
            "affected": affected,
            "counts": counts,
            "total_affected": total,
            "risk": risk,
            "estimated_narrative_risk": risk,
            "requires_confirmation": risk == "high",
            "impact_summary": {
                "affected_chapters": counts.get("chapters", 0),
                "affected_scenes": counts.get("scenes", 0),
                "affected_characters": counts.get("characters", 0),
                "affected_plot_threads": counts.get("plot_threads", 0),
                "canon_impact": counts.get("canon_entries", 0),
                "timeline_impact": counts.get("timeline", 0),
            },
            "status": "preview",
            "created_at": now,
            "updated_at": now,
        }
        inserted = await db.change_impacts.insert_one(record)
        record["_id"] = inserted.inserted_id
        return _serialize(record)

    async def set_status(
        self,
        db,
        project_id: str,
        impact_id: str,
        status: str,
    ) -> Dict[str, Any]:
        normalized = status.lower()
        if normalized not in {"approved", "rejected"}:
            raise ValueError("Impact status must be approved or rejected")
        pid = ObjectId(project_id)
        record = await db.change_impacts.find_one(
            {"project_id": pid, "impact_id": impact_id}
        )
        if not record:
            raise ValueError("Change impact preview not found")
        if record.get("status") != "preview":
            raise ValueError("Change impact preview already has a decision")
        now = datetime.utcnow()
        await db.change_impacts.update_one(
            {"_id": record["_id"]},
            {
                "$set": {
                    "status": normalized,
                    "decided_at": now,
                    "updated_at": now,
                }
            },
        )
        record["status"] = normalized
        record["decided_at"] = now
        record["updated_at"] = now
        return _serialize(record)

    async def latest(
        self, db, project_id: str, *, limit: int = 20
    ) -> list[Dict[str, Any]]:
        records = await db.change_impacts.find(
            {"project_id": ObjectId(project_id)}
        ).sort("created_at", -1).to_list(length=limit)
        return [_serialize(item) for item in records]


change_impact_service = ChangeImpactService()
