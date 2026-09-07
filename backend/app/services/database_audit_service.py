"""Project-scoped production data integrity audit."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from bson import ObjectId
from app.services.project_lifecycle_service import (
    PROJECT_OWNED_COLLECTIONS,
    project_ownership_query,
)


COLLECTIONS = [
    "story_bibles",
    "canon_registry",
    "decision_registry",
    "discussion_messages",
    "story_visions",
    "story_vision_versions",
    "story_arcs",
    "power_systems",
    "character_bibles",
    "character_journeys",
    "world_bibles",
    "mystery_registry",
    "ai_insights",
    "factions",
    "relationship_graphs",
    "plot_threads",
    "theme_registry",
    "story_timelines",
    "questions",
    "scene_registry",
    "scene_drafts",
    "chapter_drafts",
    "continuity_reports",
    "editorial_reports",
    "editorial_scores",
    "revision_branches",
    "revision_versions",
    "manuscripts",
    "manuscript_versions",
    "manuscript_reports",
    "canon_conflicts",
    "chapter_intelligence",
    "story_audit_reports",
    "change_impacts",
    "story_health_snapshots",
    "narrative_nodes",
    "narrative_edges",
    "narrative_findings",
    "narrative_analysis_snapshots",
    "narrative_analysis_history",
    "narrative_analysis_jobs",
    "narrative_conversations",
    "character_conversation_memories",
    "narrative_assistant_messages",
    "canon_proposals",
    "shared_narrative_context",
    "narrative_completeness_snapshots",
    "narrative_completeness_history",
    "workspace_companion_messages",
    "workspace_companion_state",
    "arc_checklists",
    "arc_dependencies",
    "chapter_plans",
    "scene_plans",
    "power_progressions",
    "foreshadow_chains",
    "artifact_evolutions",
    "knowledge_evolutions",
    "runs",
    "cycles",
    "agent_outputs",
    "orchestration_runs",
    "contradiction_reports",
]
COLLECTIONS = list(dict.fromkeys([*PROJECT_OWNED_COLLECTIONS, *COLLECTIONS]))

UNIQUE_KEYS = {
    "story_visions": ["project_id"],
    "power_systems": ["project_id"],
    "world_bibles": ["project_id"],
    "ai_insights": ["project_id"],
    "theme_registry": ["project_id"],
    "character_bibles": ["project_id", "name"],
    "character_journeys": ["project_id", "character_name"],
    "factions": ["project_id", "name"],
    "relationship_graphs": ["project_id", "character_a", "character_b"],
    "plot_threads": ["project_id", "title"],
    "mystery_registry": ["project_id", "question"],
    "story_arcs": ["project_id", "title"],
    "story_timelines": ["project_id", "event"],
    "questions": ["project_id", "text"],
    "scene_drafts": ["project_id", "draft_id"],
    "chapter_drafts": ["project_id", "draft_id"],
    "continuity_reports": ["project_id", "report_id"],
    "editorial_reports": ["project_id", "report_id"],
    "editorial_scores": ["project_id", "score_id"],
    "revision_branches": ["project_id", "branch_id"],
    "revision_versions": ["project_id", "branch_id", "version_number"],
    "manuscripts": ["project_id", "manuscript_id"],
    "manuscript_versions": ["project_id", "manuscript_id", "version_number"],
    "manuscript_reports": ["project_id", "report_id"],
    "canon_conflicts": ["project_id", "conflict_id"],
    "narrative_analysis_history": ["project_id", "analysis_id"],
    "workspace_companion_messages": ["project_id", "message_id"],
    "workspace_companion_state": ["project_id"],
    "chapter_intelligence": ["project_id", "intelligence_id"],
    "story_audit_reports": ["project_id", "report_id"],
    "change_impacts": ["project_id", "impact_id"],
    "narrative_nodes": ["project_id", "node_id"],
    "narrative_edges": ["project_id", "edge_id"],
    "narrative_findings": ["project_id", "finding_id"],
    "narrative_conversations": ["project_id", "turn_id"],
    "character_conversation_memories": ["project_id", "memory_id"],
    "narrative_assistant_messages": ["project_id", "message_id"],
    "canon_proposals": ["project_id", "proposal_id"],
    "shared_narrative_context": ["project_id", "context_id"],
    "workspace_companion_messages": ["project_id", "message_id"],
}


async def audit_project_database(db, project_id: str) -> Dict[str, Any]:
    pid = ObjectId(project_id)
    project = await db.projects.find_one({"_id": pid})
    findings: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}
    latest_cycle = await db.cycles.find_one({"project_id": pid}, sort=[("cycle_number", -1)])
    latest_cycle_number = int((latest_cycle or {}).get("cycle_number", 0))

    for collection_name in COLLECTIONS:
        collection = db[collection_name]
        ownership = project_ownership_query(pid)
        counts[collection_name] = await collection.count_documents(ownership)
        mock_count = await collection.count_documents({
            **ownership,
            "$or": [
                {"provider": "mock"},
                {"mock_used": True},
                {"source_type": {"$in": ["mock", "test_mock", "fallback_mock"]}},
                {"metadata.provider": "mock"},
                {"metadata.mock_used": True},
            ],
        })
        if mock_count:
            findings.append({
                "severity": "error",
                "type": "mock_data",
                "collection": collection_name,
                "count": mock_count,
            })

        keys = UNIQUE_KEYS.get(collection_name)
        if keys:
            group_id = {key: f"${key}" for key in keys}
            duplicates = await collection.aggregate([
                {"$match": {"project_id": pid}},
                {"$group": {"_id": group_id, "count": {"$sum": 1}}},
                {"$match": {"count": {"$gt": 1}}},
            ]).to_list(length=100)
            if duplicates:
                findings.append({
                    "severity": "error",
                    "type": "duplicate_artifacts",
                    "collection": collection_name,
                    "count": len(duplicates),
                })

    cycle_checks = [
        ("discussion_messages", "cycle_number"),
        ("story_visions", "cycle_generated"),
        ("story_arcs", "cycle_generated"),
        ("power_systems", "cycle_generated"),
        ("character_bibles", "cycle_generated"),
        ("world_bibles", "cycle_generated"),
        ("mystery_registry", "cycle_generated"),
        ("ai_insights", "cycle_generated"),
        ("factions", "cycle_generated"),
        ("relationship_graphs", "cycle_generated"),
        ("theme_registry", "cycle_generated"),
        ("story_timelines", "cycle_generated"),
    ]
    if latest_cycle_number:
        for collection_name, field in cycle_checks:
            invalid = await db[collection_name].count_documents({
                "project_id": pid,
                "$or": [{field: {"$exists": False}}, {field: {"$lte": 0}}],
            })
            if invalid:
                findings.append({
                    "severity": "error",
                    "type": "invalid_cycle_metadata",
                    "collection": collection_name,
                    "field": field,
                    "count": invalid,
                })

    broken_question_decisions = 0
    decisions = await db.decision_registry.find(
        {"project_id": pid, "question_id": {"$exists": True, "$ne": None}}
    ).to_list(length=1000)
    for decision in decisions:
        if not await db.questions.find_one({"_id": decision["question_id"], "project_id": pid}):
            broken_question_decisions += 1
    if broken_question_decisions:
        findings.append({
            "severity": "error",
            "type": "broken_question_reference",
            "collection": "decision_registry",
            "count": broken_question_decisions,
        })

    story_bible = await db.story_bibles.find_one({"project_id": pid})
    if project and not story_bible:
        findings.append({
            "severity": "error",
            "type": "missing_story_bible",
            "collection": "story_bibles",
            "count": 1,
        })

    report = {
        "project_id": project_id,
        "project_exists": bool(project),
        "latest_cycle_number": latest_cycle_number,
        "collection_counts": counts,
        "findings": findings,
        "status": "pass" if not findings else "fail",
        "audited_at": datetime.utcnow(),
    }
    await db.production_audits.insert_one({**report, "project_id": pid})
    report["audited_at"] = report["audited_at"].isoformat()
    return report
