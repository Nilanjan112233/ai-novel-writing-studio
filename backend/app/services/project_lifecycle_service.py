"""Project lifecycle operations backed by one authoritative ownership registry.

The registry deliberately separates recoverable lifecycle changes from permanent
purging.  New project-scoped collections must be added here so deletion,
duplication, and integrity audits cannot silently drift apart.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, Iterable, List

from bson import ObjectId


PROJECT_OWNED_COLLECTIONS = (
    "runs",
    "agent_outputs",
    "questions",
    "answers",
    "beginner_setup_steps",
    "outlines",
    "characters",
    "world_bibles",
    "timeline_messages",
    "cycles",
    "character_bibles",
    "plot_threads",
    "story_timelines",
    "theme_registry",
    "foreshadow_registry",
    "scene_registry",
    "relationship_graphs",
    "continuity_reports",
    "scene_drafts",
    "chapter_drafts",
    "editorial_reports",
    "editorial_scores",
    "revision_branches",
    "revision_versions",
    "manuscripts",
    "manuscript_versions",
    "manuscript_reports",
    "canon_conflicts",
    "memory_embeddings",
    "memory_index_checkpoints",
    "memory_index_events",
    "memory_index_staging",
    "atomic_memories",
    "memory_phase_b_checkpoints",
    "memory_phase_c_checkpoints",
    "context_packets",
    "develop_story_handoffs",
    "compressed_memories",
    "orchestration_runs",
    "orchestration_plans",
    "orchestration_tasks",
    "cognition_events",
    "cycle_costs",
    "observability_events",
    "discussion_messages",
    "story_visions",
    "story_vision_versions",
    "story_arcs",
    "power_systems",
    "character_journeys",
    "mystery_registry",
    "ai_insights",
    "factions",
    "canon_registry",
    "decision_registry",
    "story_bibles",
    "story_bible_sections",
    "project_events",
    "audit_logs",
    "contradiction_reports",
    "discussion_threads",
    "cycle_tasks",
    "production_audits",
    "e2e_test_results",
    "story_readiness",
    "timeline_entries",
    "character_progressions",
    "knowledge_entries",
    "foreshadow_registry_v2",
    "artifact_registry",
    "agent_memories",
    "arc_checklists",
    "arc_dependencies",
    "chapter_plans",
    "scene_plans",
    "scene_plans_v2",
    "scene_paragraphs",
    "paragraph_content",
    "paragraph_versions",
    "paragraph_comments",
    "paragraph_suggestions",
    "power_progressions",
    "foreshadow_chains",
    "artifact_evolutions",
    "knowledge_evolutions",
    "chapter_intelligence",
    "story_audit_reports",
    "story_health_snapshots",
    "change_impacts",
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
    "proposed_canon",
    "shared_narrative_context",
    "narrative_completeness_snapshots",
    "narrative_completeness_history",
    "workspace_companion_messages",
    "workspace_companion_state",
    "workspace_bootstrap_cache",
    "publication_exports",
    "project_timeline_events",
    "planning_invalidations",
)

# Story-domain documents that can be copied without duplicating operational
# execution state, provider traces, notifications, or cached analysis output.
DUPLICABLE_STORY_COLLECTIONS = (
    "story_visions",
    "story_vision_versions",
    "story_arcs",
    "power_systems",
    "character_bibles",
    "character_journeys",
    "world_bibles",
    "mystery_registry",
    "factions",
    "relationship_graphs",
    "plot_threads",
    "theme_registry",
    "story_timelines",
    "scene_registry",
    "chapter_plans",
    "scene_plans",
    "scene_paragraphs",
    "paragraph_content",
    "paragraph_versions",
    "paragraph_comments",
    "canon_registry",
    "decision_registry",
    "shared_narrative_context",
    "beginner_setup_steps",
    "manuscripts",
    "manuscript_versions",
)


def project_ownership_query(project_id: ObjectId) -> Dict[str, Any]:
    """Match current ObjectId ownership and the legacy paragraph string form."""
    return {"project_id": {"$in": [project_id, str(project_id)]}}


async def _copy_documents(
    db,
    source_id: ObjectId,
    target_id: ObjectId,
    collections: Iterable[str],
) -> Dict[str, int]:
    copied: Dict[str, int] = {}
    for collection_name in collections:
        rows = await db[collection_name].find(
            project_ownership_query(source_id)
        ).to_list(length=None)
        documents: List[Dict[str, Any]] = []
        for row in rows:
            clone = deepcopy(row)
            clone.pop("_id", None)
            clone["project_id"] = target_id
            clone["duplicated_from_project_id"] = source_id
            documents.append(clone)
        if documents:
            result = await db[collection_name].insert_many(documents)
            copied[collection_name] = len(result.inserted_ids)
    return copied


class ProjectLifecycleService:
    async def trash(self, db, project_id: ObjectId) -> Dict[str, Any]:
        now = datetime.utcnow()
        result = await db.projects.update_one(
            {"_id": project_id, "status": {"$ne": "trashed"}},
            {
                "$set": {
                    "status": "trashed",
                    "trashed_at": now,
                    "updated_at": now,
                }
            },
        )
        return {"matched": result.matched_count, "changed": result.modified_count}

    async def restore(self, db, project_id: ObjectId) -> Dict[str, Any]:
        now = datetime.utcnow()
        result = await db.projects.update_one(
            {"_id": project_id, "status": "trashed"},
            {
                "$set": {"status": "draft", "updated_at": now},
                "$unset": {"trashed_at": ""},
            },
        )
        return {"matched": result.matched_count, "changed": result.modified_count}

    async def archive(self, db, project_id: ObjectId) -> Dict[str, Any]:
        now = datetime.utcnow()
        result = await db.projects.update_one(
            {"_id": project_id, "status": {"$ne": "trashed"}},
            {"$set": {"status": "archived", "archived_at": now, "updated_at": now}},
        )
        return {"matched": result.matched_count, "changed": result.modified_count}

    async def unarchive(self, db, project_id: ObjectId) -> Dict[str, Any]:
        now = datetime.utcnow()
        result = await db.projects.update_one(
            {"_id": project_id, "status": "archived"},
            {
                "$set": {"status": "draft", "updated_at": now},
                "$unset": {"archived_at": ""},
            },
        )
        return {"matched": result.matched_count, "changed": result.modified_count}

    async def purge(self, db, project_id: ObjectId) -> Dict[str, int]:
        deleted: Dict[str, int] = {}
        runs = await db.runs.find(project_ownership_query(project_id)).to_list(length=None)
        run_ids = [row["_id"] for row in runs if row.get("_id")]
        if run_ids:
            result = await db.agent_outputs.delete_many({"run_id": {"$in": run_ids}})
            deleted["agent_outputs_by_run"] = result.deleted_count
        for collection_name in PROJECT_OWNED_COLLECTIONS:
            result = await db[collection_name].delete_many(
                project_ownership_query(project_id)
            )
            if result.deleted_count:
                deleted[collection_name] = result.deleted_count
        result = await db.projects.delete_one({"_id": project_id})
        deleted["projects"] = result.deleted_count
        return deleted

    async def duplicate(
        self,
        db,
        source: Dict[str, Any],
        *,
        mode: str = "shell",
    ) -> Dict[str, Any]:
        now = datetime.utcnow()
        duplicate = deepcopy(source)
        source_id = duplicate.pop("_id")
        duplicate.pop("archived_at", None)
        duplicate.pop("trashed_at", None)
        source_name = source.get("project_name") or source.get("title") or "Untitled Project"
        duplicate["project_name"] = f"{source_name} Copy"
        duplicate["title"] = duplicate["project_name"]
        duplicate["status"] = "draft"
        duplicate["created_at"] = now
        duplicate["updated_at"] = now
        duplicate["duplicated_from_project_id"] = source_id
        result = await db.projects.insert_one(duplicate)
        duplicate["_id"] = result.inserted_id
        duplicate["copied_collections"] = {}
        if mode == "story":
            duplicate["copied_collections"] = await _copy_documents(
                db, source_id, result.inserted_id, DUPLICABLE_STORY_COLLECTIONS
            )
        return duplicate


project_lifecycle_service = ProjectLifecycleService()
