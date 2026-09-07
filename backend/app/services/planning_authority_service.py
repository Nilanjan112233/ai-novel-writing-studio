"""Reconcile generated planning when an authoritative author decision changes."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from bson import ObjectId


PLANNING_OWNERS = {
    "character_bibles": ["CharacterJourneyAgent"],
    "character_journeys": ["CharacterJourneyAgent"],
    "relationship_graphs": ["RelationshipAgent"],
    "world_bibles": ["WorldAgent"],
    "power_systems": ["PowerSystemAgent"],
    "factions": ["FactionAgent"],
    "theme_registry": ["ThemeAgent"],
    "mystery_registry": ["MysteryAgent"],
    "plot_threads": ["StoryArchitectAgent", "ArcArchitectAgent"],
    "timeline_entries": ["ArcArchitectAgent"],
    "story_timelines": ["ArcArchitectAgent"],
    "story_arcs": ["ArcArchitectAgent"],
    "arc_checklists": ["StoryDevelopmentAgent"],
    "arc_dependencies": ["StoryDevelopmentAgent"],
    "chapter_plans": ["StoryDevelopmentAgent"],
    "scene_plans": ["ScenePlannerAgent", "StoryDevelopmentAgent"],
    "character_progressions": ["CharacterJourneyAgent"],
    "power_progressions": ["PowerSystemAgent"],
    "knowledge_entries": ["KnowledgeAgent"],
    "knowledge_evolutions": ["KnowledgeAgent"],
    "foreshadow_registry_v2": ["MysteryAgent"],
    "foreshadow_chains": ["MysteryAgent"],
    "artifact_registry": ["WorldAgent", "PowerSystemAgent"],
    "artifact_evolutions": ["WorldAgent", "PowerSystemAgent"],
    "story_readiness": ["ReadinessAgent"],
}


def _contains_authority(value: Any, pattern: re.Pattern[str]) -> bool:
    if isinstance(value, str):
        return bool(pattern.search(value))
    if isinstance(value, list):
        return any(_contains_authority(item, pattern) for item in value)
    if isinstance(value, dict):
        return any(
            _contains_authority(item, pattern)
            for key, item in value.items()
            if key not in {"_id", "project_id", "created_at", "updated_at", "generation_metadata"}
        )
    return False


def _authority_patterns(answer: str) -> list[re.Pattern[str]]:
    """Match both a complete answer and its meaningful clauses.

    Agents commonly paraphrase or split a recommended answer across fields, so
    exact full-answer matching alone misses planning that clearly inherited the
    old authority. Short fragments are excluded to avoid broad accidental
    invalidation.
    """
    exact = answer.strip()
    patterns = [re.compile(rf"(?<![\w]){re.escape(exact)}(?![\w])", re.IGNORECASE)]
    unique: list[str] = [exact]
    for candidate in re.split(r"(?:[.!?]\s+|;\s+|\s+[—–-]\s+)", answer):
        cleaned = candidate.strip(" \t\r\n.;:!?\"'")
        if len(cleaned) >= 28 and cleaned.casefold() not in {item.casefold() for item in unique}:
            unique.append(cleaned)
            patterns.append(re.compile(re.escape(cleaned), re.IGNORECASE))
    return patterns


def _label(document: dict[str, Any]) -> str:
    for field in ("name", "character_name", "title", "question", "event", "summary"):
        if document.get(field):
            return str(document[field])[:160]
    return str(document.get("_id"))


class PlanningAuthorityService:
    async def supersede_for_decision(
        self,
        db,
        *,
        project_id: str,
        question_id: str,
        question_text: str,
        previous_answer: str,
        new_answer: str,
    ) -> dict[str, Any]:
        old = previous_answer.strip()
        new = new_answer.strip()
        if not old or old.casefold() == new.casefold():
            return {"affected_count": 0, "affected_records": [], "required_agents": []}
        pid = ObjectId(project_id)
        now = datetime.utcnow()
        patterns = _authority_patterns(old)
        affected: list[dict[str, str]] = []
        required_agents: set[str] = set()

        for collection_name, owners in PLANNING_OWNERS.items():
            documents = await db[collection_name].find({
                "project_id": pid,
                "authority_status": {"$ne": "stale"},
            }).to_list(length=20000)
            for document in documents:
                if not any(_contains_authority(document, pattern) for pattern in patterns):
                    continue
                await db[collection_name].update_one(
                    {"_id": document["_id"]},
                    {"$set": {
                        "authority_status": "stale",
                        "stale_reason": f"Author changed '{question_text}' from '{old}' to '{new}'.",
                        "stale_at": now,
                        "superseded_by_decision_id": ObjectId(question_id),
                        "updated_at": now,
                    }},
                )
                await db.memory_embeddings.update_many(
                    {"project_id": pid, "source_id": str(document["_id"])},
                    {"$set": {"active": False, "stale_reason": "Superseded by an author decision", "updated_at": now}},
                )
                affected.append({
                    "collection": collection_name,
                    "record_id": str(document["_id"]),
                    "label": _label(document),
                })
                required_agents.update(owners)

        # Old summaries must remain auditable, but they must not be retrieved as
        # current story authority after the author has changed the decision.
        for pattern in patterns:
            await db.memory_embeddings.update_many(
                {"project_id": pid, "active": {"$ne": False}, "content": pattern},
                {"$set": {"active": False, "stale_reason": "Superseded by an author decision", "updated_at": now}},
            )
        # Decision supersession is an immediate P0 safety boundary. Do not let
        # a READY in-process index snapshot retain rows just marked stale while
        # the durable incremental event is being enqueued.
        from app.services.memory_index_cache import memory_index_cache
        memory_index_cache.invalidate(project_id)
        invalidation = {
            "project_id": pid,
            "decision_id": ObjectId(question_id),
            "question": question_text,
            "previous_answer": old,
            "new_answer": new,
            "affected_count": len(affected),
            "affected_records": affected,
            "required_agents": sorted(required_agents),
            "status": "pending" if affected else "resolved",
            "message": (
                f"{len(affected)} generated planning record{'s' if len(affected) != 1 else ''} {'need' if len(affected) != 1 else 'needs'} reconsideration after you changed this decision."
                if affected else "No generated planning conflicted with this decision change."
            ),
            "created_at": now,
            "updated_at": now,
        }
        result = await db.planning_invalidations.insert_one(invalidation)
        if affected:
            await db.projects.update_one(
                {"_id": pid},
                {"$set": {
                    "planning_reconsideration": {
                        "status": "pending",
                        "decision_id": ObjectId(question_id),
                        "message": invalidation["message"],
                        "affected_count": len(affected),
                        "invalidation_id": result.inserted_id,
                        "updated_at": now,
                    },
                    "updated_at": now,
                }},
            )
        return {
            "invalidation_id": str(result.inserted_id),
            "affected_count": len(affected),
            "affected_records": affected,
            "required_agents": sorted(required_agents),
        }


planning_authority_service = PlanningAuthorityService()
