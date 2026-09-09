"""Deterministic project health metrics for long-running novel work."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from bson import ObjectId

from app.services.narrative_analysis_engine import narrative_analysis_engine


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


class StoryHealthService:
    async def calculate(self, db, project_id: str) -> Dict[str, Any]:
        if not ObjectId.is_valid(project_id):
            raise ValueError("Invalid project ID")
        pid = ObjectId(project_id)
        if not await db.projects.find_one({"_id": pid}):
            raise ValueError("Project not found")
        platform = await narrative_analysis_engine.analyze(db, project_id)
        chapters = await db.chapter_intelligence.find(
            {"project_id": pid, "active": True}
        ).sort("chapter_number", 1).to_list(length=10000)
        mysteries = await db.mystery_registry.find(
            {"project_id": pid}
        ).to_list(length=5000)
        artifacts = await db.artifact_registry.find(
            {"project_id": pid}
        ).to_list(length=5000)
        foreshadow = await db.foreshadow_registry_v2.find(
            {"project_id": pid}
        ).to_list(length=5000)
        conflicts = await db.canon_conflicts.find(
            {
                "project_id": pid,
                "status": {"$in": ["open", "acknowledged"]},
            }
        ).to_list(length=5000)
        continuity = await db.continuity_reports.find(
            {
                "project_id": pid,
                "result": {"$in": ["WARNING", "FAIL"]},
            }
        ).to_list(length=5000)
        audit = await db.story_audit_reports.find_one(
            {"project_id": pid}, sort=[("created_at", -1)]
        )
        audit_findings = list((audit or {}).get("findings") or [])
        characters = await db.character_bibles.find(
            {"project_id": pid}
        ).to_list(length=5000)
        recent_characters = {
            str(value).lower()
            for chapter in chapters[-10:]
            for value in chapter.get("characters_present", [])
        }
        abandoned_characters = [
            item
            for item in characters
            if str(item.get("current_status") or "").lower()
            not in {"dead", "departed", "archived"}
            and str(item.get("name") or "").lower() not in recent_characters
        ]
        recent_artifacts = {
            str(item.get("artifact_id") if isinstance(item, dict) else item)
            for chapter in chapters[-10:]
            for item in chapter.get("artifact_usage", [])
        }
        abandoned_artifacts = [
            item
            for item in artifacts
            if str(item.get("status") or "active").lower()
            not in {"resolved", "destroyed", "archived"}
            and str(item.get("artifact_id") or item.get("_id"))
            not in recent_artifacts
        ]
        unresolved_promises = {
            str(value)
            for chapter in chapters
            for value in chapter.get("future_obligations", [])
            if value
        }
        resolved_text = " ".join(
            str(value).lower()
            for chapter in chapters
            for key in (
                "important_events",
                "mysteries_resolved",
                "foreshadowing_resolved",
            )
            for value in chapter.get(key, [])
        )
        unresolved_promises = {
            value
            for value in unresolved_promises
            if value.lower() not in resolved_text
        }
        arcs = await db.story_arcs.find(
            {"project_id": pid}
        ).to_list(length=1000)
        progressions = await db.character_progressions.find(
            {"project_id": pid}
        ).to_list(length=5000)
        completed_arcs = sum(
            1
            for item in arcs
            if str(item.get("development_status") or "").lower()
            in {"completed", "archived"}
        )
        latest_manuscript = await db.manuscripts.find_one(
            {"project_id": pid, "active": True}, sort=[("updated_at", -1)]
        )
        manuscript_readiness = (
            "APPROVED"
            if (latest_manuscript or {}).get("status") == "approved"
            else "VALIDATED"
            if (latest_manuscript or {}).get("status") == "validated"
            else "IN_REVIEW"
            if (latest_manuscript or {}).get("status") == "review"
            else "NOT_READY"
        )
        editorial_blockers = await db.editorial_reports.count_documents(
            {
                "project_id": pid,
                "$or": [
                    {"blockers.0": {"$exists": True}},
                    {"score": {"$lt": 60}},
                ],
            }
        )
        pacing_warnings = [
            item
            for item in audit_findings
            if item.get("category")
            in {
                "pacing_dead_zone",
                "repetitive_chapter_structure",
                "over_uniform_chapter_length",
            }
        ]
        continuity_warnings = len(continuity) + sum(
            1
            for item in audit_findings
            if item.get("category") == "narrative_contradiction"
        )
        metrics = {
            "total_chapters": len(chapters),
            "total_words": sum(int(item.get("word_count") or 0) for item in chapters),
            "open_mysteries": sum(
                1
                for item in mysteries
                if str(item.get("status") or "open").lower()
                not in {"resolved", "closed", "paid_off"}
            ),
            "resolved_mysteries": sum(
                1
                for item in mysteries
                if str(item.get("status") or "").lower()
                in {"resolved", "closed", "paid_off"}
            ),
            "unresolved_promises": len(unresolved_promises),
            "active_artifacts": sum(
                1
                for item in artifacts
                if str(item.get("status") or "active").lower()
                not in {"resolved", "destroyed", "archived"}
            ),
            "abandoned_artifacts": len(abandoned_artifacts),
            "active_foreshadowing": sum(
                1
                for item in foreshadow
                if str(item.get("status") or "seeded").lower()
                not in {"resolved", "paid_off"}
            ),
            "resolved_foreshadowing": sum(
                1
                for item in foreshadow
                if str(item.get("status") or "").lower()
                in {"resolved", "paid_off"}
            ),
            "canon_conflicts": len(conflicts),
            "continuity_warnings": continuity_warnings,
            "pacing_warnings": len(pacing_warnings),
            "abandoned_characters": len(abandoned_characters),
            "character_arc_completion": round(
                (
                    100
                    * sum(
                        1
                        for item in progressions
                        if item.get("arc_end_state")
                        or str(item.get("status") or "").lower()
                        in {"completed", "resolved"}
                        or (
                            item.get("desired_state")
                            and item.get("current_state")
                            == item.get("desired_state")
                        )
                    )
                    / max(1, len(progressions))
                ),
                1,
            ),
            "arc_completion": round(100 * completed_arcs / max(1, len(arcs)), 1),
            "manuscript_readiness": manuscript_readiness,
            "editorial_blockers": editorial_blockers,
        }
        # Compatibility metrics remain available, but the authoritative score is
        # produced by the shared Narrative Analysis Engine.
        score = int(platform["snapshot"]["scores"]["overall"])
        source_documents = int((platform["snapshot"].get("stats") or {}).get("source_documents") or 0)
        evaluation_status = "not_enough_story" if source_documents <= 1 and not chapters else "evaluated"
        now = datetime.utcnow()
        snapshot = {
            "project_id": pid,
            "metrics": metrics,
            "story_health_score": score,
            "evaluation_status": evaluation_status,
            "status": (
                "healthy"
                if score >= 80
                else "watch"
                if score >= 60
                else "at_risk"
            ),
            "latest_audit_report_id": (audit or {}).get("report_id"),
            "dimension_scores": platform["snapshot"]["scores"],
            "findings": platform["findings"],
            "analysis": platform["snapshot"]["stats"],
            "calculated_at": now,
        }
        await db.story_health_snapshots.update_one(
            {"project_id": pid, "snapshot_type": "current"},
            {
                "$set": {**snapshot, "snapshot_type": "current"},
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        return _serialize(snapshot)


story_health_service = StoryHealthService()
