"""Central eligibility and identity policy for Native memory retrieval.

This module does not create story authority.  It decides whether an indexed,
derived observation is safe to place in a consumer context and records why.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable


BAD_AUTHORITY_STATUSES = {
    "candidate", "suggested", "rejected", "reconsidered", "stale",
    "superseded", "archived", "inactive", "abandoned",
}
APPROVED_AUTHORITY_STATUSES = {"approved", "confirmed", "active", "resolved", "locked"}

SAFE_WRITING_EXCLUDED_SOURCES = {
    "timeline",       # raw orchestration/chat history
    "output",         # agent suggestion/output
    "ai_insight",     # unapproved recommendation
    "readiness",      # diagnostic suggestion
    "continuity",     # supplied separately as a labelled diagnostic
}

SOURCE_ID_FIELDS: Dict[str, tuple[str, ...]] = {
    "character": ("character_id", "candidate_id"),
    "relationship": ("relationship_id", "candidate_id"),
    "world": ("world_id",),
    "plot_thread": ("thread_id", "candidate_id"),
    "theme": ("theme_id",),
    "foreshadow": ("foreshadow_id", "entry_id"),
    "continuity": ("report_id",),
    "scene": ("scene_id",),
    "story_timeline": ("event_id", "entry_id"),
    "question": ("question_id", "candidate_id"),
    "canon": ("canon_id", "source_id"),
    "decision": ("decision_id", "question_id"),
    "story_vision": ("vision_id",),
    "story_arc": ("arc_id", "candidate_id"),
    "readiness": ("readiness_id",),
    "timeline_v2": ("entry_id", "candidate_id"),
    "character_progression": ("progression_id", "character_id"),
    "knowledge": ("entry_id", "candidate_id"),
    "foreshadow_v2": ("entry_id",),
    "artifact": ("artifact_id", "candidate_id"),
    "power_system": ("power_system_id",),
    "character_journey": ("journey_id", "character_id"),
    "mystery": ("mystery_id", "candidate_id"),
    "faction": ("faction_id",),
    "arc_checklist": ("item_id", "checklist_id"),
    "arc_dependency": ("dependency_id",),
    "chapter_plan": ("chapter_plan_id",),
    "scene_plan_v2": ("scene_id",),
    "power_progression": ("progression_id",),
    "foreshadow_chain": ("evolution_id", "entry_id"),
    "artifact_evolution": ("evolution_id", "artifact_id"),
    "knowledge_evolution": ("evolution_id", "entry_id"),
    "chapter_intelligence": ("intelligence_id",),
    "atomic_memory": ("memory_id",),
}

OWNER_VERSION_FIELDS = (
    "version_number", "source_version", "owner_source_version", "version",
)


def normalized_values(value: Any) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    return [str(item).strip().lower() for item in values if str(item).strip()]


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def canonical_source_id(
    source_type: str,
    document: Dict[str, Any],
    *,
    fallback: str = "",
) -> str:
    metadata = document.get("metadata") or {}
    for value in (
        metadata.get("logical_source_id"),
        *(document.get(field) for field in SOURCE_ID_FIELDS.get(source_type, ())),
        document.get("source_id"),
        fallback,
        document.get("_id"),
    ):
        if value is not None and str(value).strip():
            return str(value)
    return "unknown"


def owner_source_version(document: Dict[str, Any]) -> int:
    metadata = document.get("metadata") or {}
    for value in (
        metadata.get("owner_source_version"),
        *(document.get(field) for field in OWNER_VERSION_FIELDS),
    ):
        if value not in (None, ""):
            try:
                return max(1, int(value))
            except (TypeError, ValueError):
                continue
    return 1


def logical_identity(source_type: str, logical_source_id: str, version: int) -> str:
    return f"{source_type}:{logical_source_id}:v{max(1, int(version or 1))}"


def metadata_for_source(source_type: str, document: Dict[str, Any]) -> Dict[str, Any]:
    logical_id = canonical_source_id(source_type, document)
    version = owner_source_version(document)
    provenance = document.get("provenance") or {
        "source_type": source_type,
        "source_id": logical_id,
        "physical_source_id": str(document.get("_id") or ""),
    }
    chapter = (
        document.get("chapter_number")
        or document.get("source_chapter")
        or document.get("observed_at_chapter")
    )
    return {
        "source_type": source_type,
        "logical_source_id": logical_id,
        "logical_identity": logical_identity(source_type, logical_id, version),
        "physical_source_id": str(document.get("_id") or ""),
        "owner_source_version": version,
        "authority_status": document.get("authority_status"),
        "candidate_status": document.get("candidate_status"),
        "approval_status": document.get("approval_status"),
        "status": document.get("status"),
        "active": document.get("active"),
        "branch_id": document.get("branch_id"),
        "chapter_number": chapter,
        "valid_from_chapter": document.get("valid_from_chapter") or chapter,
        "valid_to_chapter": document.get("valid_to_chapter"),
        "scene_number": document.get("scene_number") or document.get("scene_order"),
        "valid_from_scene": document.get("valid_from_scene"),
        "valid_to_scene": document.get("valid_to_scene"),
        "known_by": list(document.get("known_by") or []),
        "not_known_by": list(document.get("not_known_by") or []),
        "provenance": provenance,
        "evidence_pointer": {
            "source_type": source_type,
            "logical_source_id": logical_id,
            "owner_source_version": version,
            "physical_source_id": str(document.get("_id") or ""),
        },
        "authority_level": authority_level(source_type, document),
    }


def authority_level(source_type: str, document: Dict[str, Any]) -> str:
    status_values = set(
        normalized_values(document.get("authority_status"))
        + normalized_values(document.get("approval_status"))
        + normalized_values(document.get("status"))
    )
    if source_type == "canon":
        return "canon"
    if source_type == "decision":
        return "author_decision"
    if status_values & APPROVED_AUTHORITY_STATUSES:
        return "confirmed_planning"
    if source_type in {
        "character", "world", "plot_thread", "theme", "story_arc",
        "timeline_v2", "knowledge", "artifact", "mystery", "faction",
    } and not status_values & BAD_AUTHORITY_STATUSES:
        return "structured_owner"
    if source_type == "project":
        return "project"
    return "derived"


AUTHORITY_PRIORITY = {
    "canon": 600,
    "author_decision": 550,
    "confirmed_planning": 500,
    "structured_owner": 400,
    "project": 350,
    "derived": 100,
}


@dataclass(frozen=True, slots=True)
class RetrievalEligibilityContext:
    safe_for_writing: bool = False
    consumer: str = "conversation"
    project_id: str | None = None
    branch_id: str | None = None
    as_of_chapter: int | None = None
    as_of_scene: int | None = None
    pov_character: str | None = None


@dataclass(frozen=True, slots=True)
class EligibilityDecision:
    eligible: bool
    validity: str
    authority_level: str
    authority_priority: int
    reasons: tuple[str, ...]

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RetrievalEligibilityPolicy:
    def evaluate(
        self,
        document: Dict[str, Any],
        context: RetrievalEligibilityContext,
    ) -> EligibilityDecision:
        metadata = document.get("metadata") or {}
        source_type = str(document.get("source_type") or metadata.get("source_type") or "memory")
        level = str(metadata.get("authority_level") or authority_level(source_type, document))
        priority = AUTHORITY_PRIORITY.get(level, 0)
        reasons: list[str] = []

        if document.get("active") is False or metadata.get("active") is False:
            reasons.append("inactive_source_version")

        if context.project_id and str(document.get("project_id") or "") not in {"", context.project_id}:
            reasons.append("project_mismatch")

        record_branch = metadata.get("branch_id") or document.get("branch_id")
        if context.branch_id and record_branch and str(record_branch) != str(context.branch_id):
            reasons.append("branch_mismatch")

        statuses: set[str] = set()
        for key in ("authority_status", "candidate_status", "approval_status", "status"):
            statuses.update(normalized_values(document.get(key)))
            statuses.update(normalized_values(metadata.get(key)))
        bad = statuses & BAD_AUTHORITY_STATUSES
        if context.safe_for_writing and bad:
            reasons.append("unsafe_status:" + ",".join(sorted(bad)))
        if context.safe_for_writing and source_type in SAFE_WRITING_EXCLUDED_SOURCES:
            reasons.append("unsafe_source_type:" + source_type)

        chapter = metadata.get("chapter_number") or metadata.get("valid_from_chapter")
        valid_from = metadata.get("valid_from_chapter") or chapter
        valid_to = metadata.get("valid_to_chapter")
        if context.as_of_chapter is not None:
            valid_from_number = _optional_int(valid_from)
            valid_to_number = _optional_int(valid_to)
            if valid_from_number is not None and valid_from_number > int(context.as_of_chapter):
                reasons.append("future_chapter")
            if valid_to_number is not None and valid_to_number < int(context.as_of_chapter):
                reasons.append("superseded_before_chapter")

        valid_from_scene = metadata.get("valid_from_scene") or metadata.get("scene_number")
        valid_to_scene = metadata.get("valid_to_scene")
        if context.as_of_scene is not None:
            valid_from_scene_number = _optional_int(valid_from_scene)
            valid_to_scene_number = _optional_int(valid_to_scene)
            if valid_from_scene_number is not None and valid_from_scene_number > int(context.as_of_scene):
                reasons.append("future_scene")
            if valid_to_scene_number is not None and valid_to_scene_number < int(context.as_of_scene):
                reasons.append("superseded_before_scene")

        if context.safe_for_writing and context.pov_character and source_type in {"knowledge", "atomic_memory"}:
            pov = context.pov_character.strip().lower()
            known_by = set(normalized_values(metadata.get("known_by")))
            not_known_by = set(normalized_values(metadata.get("not_known_by")))
            if pov in not_known_by:
                reasons.append("explicitly_not_known_by_pov")
            elif known_by and pov not in known_by:
                reasons.append("not_known_by_pov")

        if context.safe_for_writing and source_type == "atomic_memory":
            conflict_status = str(metadata.get("conflict_status") or document.get("conflict_status") or "")
            if conflict_status in {"conflicts_with_authority", "unresolved_conflict"}:
                reasons.append("conflicting_derived_observation")

        return EligibilityDecision(
            eligible=not reasons,
            validity="valid" if not reasons else "excluded",
            authority_level=level,
            authority_priority=priority,
            reasons=tuple(reasons or ["eligible_for_consumer"]),
        )


retrieval_eligibility_policy = RetrievalEligibilityPolicy()
