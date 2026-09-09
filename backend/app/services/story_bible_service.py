"""Persisted Story Bible aggregation.

Pages consume this document instead of reading agent outputs or individual
artifact collections directly.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from bson import ObjectId
from pymongo import UpdateOne

from app.services.canon_service import get_canon_context
from app.services.readiness_service import readiness_service
from app.services.arc_development_service import arc_development_service
from app.services.narrative_analysis_engine import narrative_analysis_engine


def serialize_value(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {
            ("id" if key == "_id" else key): serialize_value(item)
            for key, item in value.items()
        }
    return value


async def _list(db, collection: str, pid: ObjectId, *, sort=None, limit: int = 500):
    cursor = db[collection].find({"project_id": pid, "authority_status": {"$nin": ["stale", "candidate", "suggested", "rejected"]}})
    if sort:
        cursor = cursor.sort(*sort)
    return await cursor.to_list(length=limit)


async def rebuild_story_bible(
    db,
    project_id: str,
    *,
    cycle_number: int | None = None,
) -> Dict[str, Any]:
    pid = ObjectId(project_id)
    project = await db.projects.find_one({"_id": pid})
    if not project:
        raise ValueError("Project not found")
    narrative_platform = await narrative_analysis_engine.platform(db, project_id)

    latest_cycle = await db.cycles.find_one(
        {"project_id": pid},
        sort=[("cycle_number", -1)],
    )
    resolved_cycle = int(
        cycle_number
        if cycle_number is not None
        else (latest_cycle or {}).get("cycle_number", 0)
    )
    canon = await get_canon_context(db, project_id)
    questions = await _list(db, "questions", pid, sort=("created_at", 1))
    decisions = await _list(db, "decision_registry", pid, sort=("created_at", 1))
    discussion_decisions = [
        item for item in decisions if item.get("source") == "discussion_action"
    ]
    latest_orchestration = await db.orchestration_plans.find_one(
        {"project_id": pid},
        sort=[("created_at", -1)],
    )
    if latest_orchestration:
        latest_tasks = await db.orchestration_tasks.find(
            {"plan_id": latest_orchestration["_id"]}
        ).sort([("order", 1), ("agent_name", 1)]).to_list(length=100)
        latest_orchestration["tasks"] = latest_tasks

    readiness_reports = await readiness_service.evaluate_all_arcs(db, project_id)
    development_reports = await arc_development_service.evaluate_all(
        db, project_id, persist=False
    )
    latest_story_health = await db.story_health_snapshots.find_one(
        {"project_id": pid}, sort=[("calculated_at", -1)]
    )
    latest_story_audit = await db.story_audit_reports.find_one(
        {"project_id": pid}, sort=[("created_at", -1)]
    )
    latest_completeness = await db.narrative_completeness_snapshots.find_one(
        {"project_id": pid, "snapshot_type": "current"}
    )

    story_vision = await db.story_visions.find_one({"project_id": pid}) or {
        "project_id": pid,
        "premise": project.get("premise") or project.get("idea_dump", ""),
        "genre": project.get("genre", ""),
        "themes": project.get("themes") or [],
        "target_length": project.get("target_length"),
        "inspirations": project.get("inspirations") or [],
        "audience": project.get("audience"),
        "narrative_goals": project.get("narrative_goals") or [],
        "cycle_generated": 0,
        "source_type": "project",
    }
    ordered_chapter_plans = await _list(
        db, "chapter_plans", pid, sort=("chapter_number", 1), limit=5000
    )
    chapter_number_by_id = {
        str(item.get("chapter_plan_id")): int(item.get("chapter_number") or 0)
        for item in ordered_chapter_plans
    }
    ordered_scene_plans = await _list(db, "scene_plans", pid, limit=20000)
    ordered_scene_plans.sort(
        key=lambda item: (
            chapter_number_by_id.get(str(item.get("chapter_plan_id")), 10**9),
            int(item.get("order") or 0),
            str(item.get("title") or "").casefold(),
        )
    )
    sections = {
        "story_vision": story_vision,
        "characters": await _list(db, "character_bibles", pid, sort=("name", 1)),
        "character_journeys": await _list(db, "character_journeys", pid, sort=("character_name", 1)),
        "world": await db.world_bibles.find_one({"project_id": pid, "authority_status": {"$ne": "stale"}}) or {},
        "power_system": await db.power_systems.find_one({"project_id": pid, "authority_status": {"$ne": "stale"}}) or {},
        "factions": await _list(db, "factions", pid, sort=("name", 1)),
        "relationships": await _list(db, "relationship_graphs", pid, sort=("updated_at", -1)),
        "plot_threads": await _list(db, "plot_threads", pid, sort=("updated_at", -1)),
        "themes": await db.theme_registry.find_one({"project_id": pid, "authority_status": {"$ne": "stale"}}) or {},
        "foreshadowing": await _list(db, "foreshadow_registry_v2", pid, sort=("updated_at", -1)),
        "legacy_foreshadowing": await _list(db, "foreshadow_registry", pid, sort=("updated_at", -1)),
        "mysteries": await _list(db, "mystery_registry", pid, sort=("updated_at", -1)),
        "timeline": await _list(db, "timeline_entries", pid, sort=("order", 1)),
        "legacy_timeline": await _list(db, "story_timelines", pid, sort=("chronology", 1)),
        "arcs": await _list(db, "story_arcs", pid, sort=("order", 1)),
        "arc_development": {
            "reports": development_reports,
            "checklists": await _list(
                db, "arc_checklists", pid, sort=("updated_at", -1), limit=5000
            ),
            "dependencies": await _list(
                db, "arc_dependencies", pid, sort=("updated_at", -1), limit=5000
            ),
        },
        "readiness": {
            "items": await _list(db, "story_readiness", pid, sort=("updated_at", -1)),
            "reports": readiness_reports,
        },
        "character_progressions": await _list(
            db, "character_progressions", pid, sort=("updated_at", -1)
        ),
        "power_progressions": await _list(
            db, "power_progressions", pid, sort=("updated_at", -1)
        ),
        "knowledge": await _list(db, "knowledge_entries", pid, sort=("created_at", 1)),
        "knowledge_evolutions": await _list(
            db, "knowledge_evolutions", pid, sort=("order", 1), limit=5000
        ),
        "artifacts": await _list(db, "artifact_registry", pid, sort=("created_at", 1)),
        "artifact_evolutions": await _list(
            db, "artifact_evolutions", pid, sort=("order", 1), limit=5000
        ),
        "foreshadow_chains": await _list(
            db, "foreshadow_chains", pid, sort=("order", 1), limit=5000
        ),
        "questions": questions,
        "active_questions": [item for item in questions if not item.get("answered")],
        "resolved_questions": [item for item in questions if item.get("answered")],
        "ai_insights": await db.ai_insights.find_one({"project_id": pid, "authority_status": {"$ne": "stale"}}) or {},
        "drafting": {
            "chapter_plans": ordered_chapter_plans,
            "scene_plans": ordered_scene_plans,
            "legacy_scene_plans": await _list(
                db, "scene_registry", pid, sort=("created_at", 1)
            ),
            "scene_drafts": await _list(db, "scene_drafts", pid, sort=("created_at", 1)),
            "chapter_drafts": await _list(
                db, "chapter_drafts", pid, sort=("created_at", 1), limit=5000
            ),
            "review_queue": [
                item
                for item in [
                    *await _list(
                        db, "scene_drafts", pid, sort=("created_at", -1), limit=5000
                    ),
                    *await _list(
                        db, "chapter_drafts", pid, sort=("created_at", -1), limit=5000
                    ),
                ]
                if item.get("active")
                and item.get("status") in {"draft", "review"}
            ],
        },
        "editorial": {
            "reports": await _list(
                db, "editorial_reports", pid, sort=("created_at", -1), limit=5000
            ),
            "scores": await _list(
                db, "editorial_scores", pid, sort=("calculated_at", -1), limit=5000
            ),
            "revision_branches": await _list(
                db, "revision_branches", pid, sort=("updated_at", -1), limit=5000
            ),
            "revision_versions": await _list(
                db, "revision_versions", pid, sort=("created_at", -1), limit=5000
            ),
        },
        "manuscript": {
            "manuscripts": await _list(
                db, "manuscripts", pid, sort=("updated_at", -1), limit=100
            ),
            "versions": await _list(
                db, "manuscript_versions", pid, sort=("created_at", -1), limit=5000
            ),
            "reports": await _list(
                db, "manuscript_reports", pid, sort=("created_at", -1), limit=5000
            ),
        },
        "canon_governance": {
            "registry": await _list(
                db, "canon_registry", pid, sort=("updated_at", -1), limit=10000
            ),
            "conflicts": await _list(
                db, "canon_conflicts", pid, sort=("last_seen_at", -1), limit=5000
            ),
        },
        "chapter_intelligence": await _list(
            db,
            "chapter_intelligence",
            pid,
            sort=("chapter_number", 1),
            limit=10000,
        ),
        "story_intelligence": {
            "analysis": narrative_platform["snapshot"],
            "findings": narrative_platform["findings"],
            "health": latest_story_health or {},
            "latest_audit": latest_story_audit or {},
            "audits": await _list(
                db,
                "story_audit_reports",
                pid,
                sort=("created_at", -1),
                limit=100,
            ),
            "change_impacts": await _list(
                db,
                "change_impacts",
                pid,
                sort=("created_at", -1),
                limit=100,
            ),
            "narrative_critique": [
                item for item in await _list(
                    db, "narrative_findings", pid, sort=("last_seen_at", -1), limit=20000
                ) if item.get("finding_type") == "critique" and item.get("status") in {"open", "acknowledged"}
            ],
            "narrative_completeness": latest_completeness or {},
        },
        "shared_narrative_context": await _list(
            db, "shared_narrative_context", pid, sort=("updated_at", -1), limit=5000
        ),
        "interactive_intelligence": {
            "character_conversations": await _list(
                db,
                "narrative_conversations",
                pid,
                sort=("created_at", -1),
                limit=500,
            ),
            "character_memories": await _list(
                db,
                "character_conversation_memories",
                pid,
                sort=("created_at", -1),
                limit=1000,
            ),
            "assistant_history": await _list(
                db,
                "narrative_assistant_messages",
                pid,
                sort=("created_at", -1),
                limit=200,
            ),
            "canon_proposals": await _list(
                db,
                "canon_proposals",
                pid,
                sort=("created_at", -1),
                limit=1000,
            ),
            "source_policy": "narrative_analysis_grounded_and_canon_governed",
        },
        "approved_story_content": {
            "chapter_drafts": [
                item for item in await _list(
                    db, "chapter_drafts", pid, sort=("created_at", 1), limit=10000
                )
                if item.get("active") and item.get("status") in {"approved", "validated"}
            ],
            "scene_drafts": [
                item for item in await _list(
                    db, "scene_drafts", pid, sort=("created_at", 1), limit=20000
                )
                if item.get("active") and item.get("status") in {"approved", "validated"}
            ],
            "source_policy": "approved_active_content_only",
        },
        "discussion": await _list(db, "discussion_messages", pid, sort=("created_at", 1), limit=1000),
        "canon_registry": await _list(db, "canon_registry", pid, sort=("updated_at", -1)),
        "decision_registry": decisions,
        "discussion_decisions": discussion_decisions,
        "canon": canon,
        "contradictions": await _list(db, "contradiction_reports", pid, sort=("created_at", -1)),
        "continuity_reports": await _list(db, "continuity_reports", pid, sort=("created_at", -1)),
        "workflow": {
            "cycles": await _list(db, "cycles", pid, sort=("cycle_number", 1)),
            "runs": await _list(db, "runs", pid, sort=("started_at", -1)),
            "latest_orchestration": latest_orchestration or {},
            "agents": [
                {
                    "id": str(item.get("_id", "")),
                    "run_id": str(item.get("run_id", "")),
                    "agent_name": item.get("agent_name", ""),
                    "summary": item.get("summary") or item.get("content", "")[:500],
                    "metadata": item.get("metadata") or {},
                    "created_at": item.get("created_at"),
                }
                for item in await _list(db, "agent_outputs", pid, sort=("created_at", 1), limit=1000)
            ],
        },
    }
    now = datetime.utcnow()
    previous = await db.story_bibles.find_one({"project_id": pid}) or {}
    version = int(previous.get("version", 0)) + 1
    section_updates = [
        UpdateOne(
            {"project_id": pid, "section": section_name},
            {
                "$set": {
                    "value": section_value,
                    "version": version,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        for section_name, section_value in sections.items()
    ]
    if section_updates:
        await db.story_bible_sections.bulk_write(section_updates, ordered=False)
    await db.story_bible_sections.delete_many({
        "project_id": pid,
        "section": {"$nin": list(sections)},
    })
    doc = {
        "project_id": pid,
        "cycle_number": resolved_cycle,
        "version": version,
        "section_names": list(sections),
        "storage_mode": "segmented",
        "updated_at": now,
    }
    await db.story_bibles.update_one(
        {"project_id": pid},
        {
            "$set": doc,
            "$unset": {"sections": ""},
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    return serialize_value({**doc, "sections": sections})


async def get_story_bible(db, project_id: str) -> Dict[str, Any]:
    pid = ObjectId(project_id)
    doc = await db.story_bibles.find_one({"project_id": pid})
    if not doc:
        return await rebuild_story_bible(db, project_id)
    if doc.get("storage_mode") == "segmented":
        rows = await db.story_bible_sections.find({"project_id": pid}).to_list(length=500)
        sections = {str(row.get("section")): row.get("value") for row in rows}
        return serialize_value({**doc, "sections": sections})
    return serialize_value(doc)
