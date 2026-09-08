"""Role-bounded Develop Story packets and durable same-cycle delta handoffs.

This service derives context only. It never promotes, edits, or replaces story
authority. Full Story Bible projections and specialist outputs remain stored;
specialists receive bounded role views plus evidence references.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List

from bson import ObjectId

from app.services.provider_gateway import estimate_tokens
from app.services.memory_phase_b_service import compact_chapter_memory_context, compact_retrieval_hit


UNSAFE_STATUSES = {"candidate", "pending", "rejected", "superseded", "archived", "inactive"}
WORKFLOW_MEMORY_TERMS = (
    "failed", "failure", "retry", "rejected", "accepted", "unresolved",
    "conflict", "contradiction", "blocked", "fallback", "must preserve",
)


@dataclass(frozen=True)
class RoleManifest:
    sections: tuple[str, ...]
    chapter_memory: bool = False
    native_limit: int = 6
    budget_tokens: int = 20_000
    upstream_roles: tuple[str, ...] = ()


ROLE_MANIFESTS: Dict[str, RoleManifest] = {
    "NarrativeDirectorAgent": RoleManifest(("story_vision", "arcs", "plot_threads", "mysteries", "themes", "readiness"), budget_tokens=24_000),
    "StoryArchitectAgent": RoleManifest(("story_vision", "arcs", "plot_threads", "timeline", "characters", "world"), budget_tokens=24_000),
    "RelationshipAgent": RoleManifest(("characters", "relationships", "character_journeys", "character_progressions", "knowledge", "timeline"), chapter_memory=True, budget_tokens=20_000),
    "CharacterJourneyAgent": RoleManifest(("characters", "character_journeys", "character_progressions", "relationships", "knowledge", "arcs", "plot_threads", "timeline"), chapter_memory=True, budget_tokens=22_000, upstream_roles=("RelationshipAgent",)),
    "MysteryAgent": RoleManifest(("mysteries", "foreshadowing", "foreshadow_chains", "knowledge", "timeline", "plot_threads", "artifacts"), chapter_memory=True, budget_tokens=22_000, upstream_roles=("RelationshipAgent", "CharacterJourneyAgent")),
    "ArcArchitectAgent": RoleManifest(("arcs", "arc_development", "plot_threads", "mysteries", "character_journeys", "character_progressions", "relationships", "timeline", "drafting", "readiness"), chapter_memory=True, budget_tokens=30_000, upstream_roles=("RelationshipAgent", "CharacterJourneyAgent", "MysteryAgent", "ThemeAgent", "KnowledgeAgent")),
    "PacingAgent": RoleManifest(("arcs", "arc_development", "plot_threads", "mysteries", "timeline", "drafting", "character_progressions", "readiness"), chapter_memory=True, budget_tokens=30_000, upstream_roles=("CharacterJourneyAgent", "MysteryAgent", "ArcArchitectAgent")),
    "WorldAgent": RoleManifest(("world", "factions", "artifacts", "power_system", "timeline"), budget_tokens=20_000),
    "PowerSystemAgent": RoleManifest(("power_system", "power_progressions", "artifacts", "characters", "world"), budget_tokens=20_000),
    "FactionAgent": RoleManifest(("factions", "relationships", "world", "characters", "timeline"), budget_tokens=20_000),
    "ThemeAgent": RoleManifest(("themes", "story_vision", "arcs", "plot_threads", "characters"), budget_tokens=18_000),
    "QuestionAgent": RoleManifest(("questions", "active_questions", "story_vision", "readiness", "arcs"), budget_tokens=18_000),
    "ReadinessAgent": RoleManifest(("readiness", "questions", "arcs", "plot_threads", "mysteries", "drafting"), budget_tokens=20_000),
    "KnowledgeAgent": RoleManifest(("knowledge", "knowledge_evolutions", "characters", "mysteries", "timeline"), chapter_memory=True, budget_tokens=22_000),
    "StoryDevelopmentAgent": RoleManifest(("arc_development", "arcs", "drafting", "plot_threads", "mysteries", "characters", "relationships", "timeline"), chapter_memory=True, budget_tokens=30_000),
    "ScenePlannerAgent": RoleManifest(("drafting", "arcs", "characters", "relationships", "knowledge", "timeline"), chapter_memory=True, budget_tokens=24_000),
}
DEFAULT_MANIFEST = RoleManifest(("story_vision", "arcs", "plot_threads", "characters", "timeline"), budget_tokens=24_000)


SECTION_FIELDS: Dict[str, tuple[str, ...]] = {
    "story_vision": ("premise", "genre", "tone", "themes", "audience", "narrative_goals", "scope"),
    "characters": ("character_id", "name", "role", "description", "goals", "motivations", "fears", "beliefs", "arc", "current_state", "knowledge", "status", "authority_status", "approval_status", "source_chapter", "provenance"),
    "relationships": ("relationship_id", "character_a", "character_b", "type", "relationship", "state", "history", "tension", "trust", "source_chapter", "status", "authority_status", "approval_status", "provenance"),
    "character_journeys": ("character_id", "character_name", "starting_state", "current_state", "goal", "fear", "wound", "belief", "change", "milestones", "status", "approval_status", "provenance"),
    "character_progressions": ("character_id", "character_name", "chapter_number", "from_state", "to_state", "change", "knowledge_changes", "status", "approval_status", "provenance"),
    "knowledge": ("entry_id", "character_id", "character_name", "subject", "fact", "knowledge", "learned_chapter", "as_of_chapter", "status", "authority_status", "approval_status", "provenance"),
    "mysteries": ("mystery_id", "question", "setup", "truth", "clues", "red_herrings", "reveal_target", "status", "authority_status", "approval_status", "source_chapter", "provenance"),
    "foreshadowing": ("foreshadow_id", "seed", "reinforcements", "payoff", "planned_chapter", "status", "approval_status", "provenance"),
    "foreshadow_chains": ("chain_id", "title", "seed", "reinforcements", "payoff", "status", "approval_status", "provenance"),
    "timeline": ("entry_id", "title", "summary", "chapter_number", "scene_number", "order", "certainty", "importance", "status", "authority_status", "approval_status", "provenance"),
    "arcs": ("arc_id", "title", "name", "description", "goal", "conflict", "stakes", "turning_points", "chapter_range", "status", "approval_status", "provenance"),
    "arc_development": ("arc_id", "focus", "goals", "constraints", "open_items", "dependencies", "status", "approval_status"),
    "plot_threads": ("thread_id", "title", "description", "promise", "progression", "target_chapter", "status", "authority_status", "approval_status", "source_chapter", "provenance"),
    "drafting": ("chapter_number", "chapter_plan_id", "scene_id", "title", "purpose", "conflict", "outcome", "character_focus", "knowledge_changes", "timeline_impacts", "order", "status", "approval_status", "provenance"),
    "world": ("name", "summary", "locations", "rules", "cultures", "history", "constraints", "status", "approval_status", "provenance"),
    "factions": ("faction_id", "name", "goal", "methods", "members", "relationships", "status", "approval_status", "provenance"),
    "artifacts": ("artifact_id", "name", "description", "owner", "history", "rules", "status", "approval_status", "provenance"),
    "power_system": ("name", "rules", "limits", "costs", "levels", "status", "approval_status", "provenance"),
    "power_progressions": ("character_id", "ability", "from_state", "to_state", "chapter_number", "status", "approval_status", "provenance"),
    "themes": ("theme", "description", "motifs", "progression", "status", "approval_status", "provenance"),
    "questions": ("question_id", "question", "answer", "blocking", "status", "decision_status", "provenance"),
    "active_questions": ("question_id", "question", "blocking", "status", "provenance"),
    "readiness": ("ready", "score", "blocking_gaps", "warnings", "requirements", "status"),
}


def _tokens(value: Any) -> int:
    return estimate_tokens(json.dumps(value, default=str, ensure_ascii=False))


def _normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", json.dumps(value, default=str, ensure_ascii=False, sort_keys=True)).strip().lower()


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_normalize(value).encode("utf-8")).hexdigest()


def _is_unsafe(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    status = str(item.get("status") or "").strip().lower()
    authority = str(item.get("authority_status") or "").strip().lower()
    candidate = str(item.get("candidate_status") or "").strip().lower()
    approval = str(item.get("approval_status") or "").strip().lower()
    decision = str(item.get("decision_status") or "").strip().lower()
    if authority in {"candidate", "rejected", "stale", "superseded", "archived", "inactive"}:
        return True
    if candidate in {"candidate", "pending", "rejected", "stale", "superseded"}:
        return True
    if approval in {"candidate", "pending", "rejected", "stale", "superseded"}:
        return True
    if decision in {"candidate", "pending", "rejected", "stale", "superseded"}:
        return True
    if status in {"candidate", "rejected", "superseded", "archived", "inactive", "stale"}:
        return True
    values = {status, authority, candidate, approval, decision}
    return bool(values & UNSAFE_STATUSES) and not bool(values & {"confirmed", "approved", "active"})


def _compact_scalar(value: Any) -> Any:
    if isinstance(value, str):
        return value[:1600]
    if isinstance(value, list):
        return [_compact_scalar(item) for item in value[:20]]
    if isinstance(value, dict):
        return {
            str(key): _compact_scalar(item)
            for key, item in list(value.items())[:30]
            if str(key) not in {"_id", "project_id", "embedding", "created_at", "updated_at", "content_hash"}
        }
    return value


def _section_rows(section: str, value: Any) -> Any:
    fields = SECTION_FIELDS.get(section, ())

    def compact_item(item: Any) -> Any:
        if not isinstance(item, dict):
            return _compact_scalar(item)
        if _is_unsafe(item):
            return None
        selected = {key: item[key] for key in fields if key in item and item[key] not in (None, "", [], {})}
        if not selected:
            selected = {
                key: value
                for key, value in item.items()
                if key not in {"_id", "project_id", "embedding", "created_at", "updated_at", "content_hash"}
                and value not in (None, "", [], {})
            }
        return _compact_scalar(selected)

    if isinstance(value, list):
        return [row for item in value[:200] if (row := compact_item(item)) is not None]
    if isinstance(value, dict):
        # Drafting and similar wrapper sections retain their named child lists.
        if any(isinstance(child, list) for child in value.values()):
            projected: Dict[str, Any] = {}
            for key, child in value.items():
                if isinstance(child, list):
                    rows = [row for item in child[:200] if (row := compact_item(item)) is not None]
                    if rows:
                        projected[key] = rows
                elif key in fields and child not in (None, "", [], {}):
                    projected[key] = _compact_scalar(child)
            return projected
        return compact_item(value) or {}
    return _compact_scalar(value)


def _authority_item(item: Any) -> Any:
    if not isinstance(item, dict):
        return _compact_scalar(item)
    keys = (
        "canon_id", "decision_id", "planning_id", "type", "values", "source", "subject", "field", "value",
        "fact", "decision", "content", "summary", "title", "status",
        "authority_status", "approval_status", "source_type", "source_id",
        "source_chapter", "as_of_chapter", "supersedes", "provenance",
    )
    return _compact_scalar({key: item[key] for key in keys if key in item and item[key] not in (None, "", [], {})})


def _safe_authority(items: Iterable[Any]) -> List[Any]:
    return [_authority_item(item) for item in items if not _is_unsafe(item)]


def _workflow_memory(agent_memory: Dict[str, Any]) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    for bucket in ("recent", "important", "compressed"):
        for item in agent_memory.get(bucket) or []:
            text = str(item.get("content") if isinstance(item, dict) else item)
            if any(term in text.lower() for term in WORKFLOW_MEMORY_TERMS):
                selected.append({
                    "memory_type": bucket,
                    "content": text[:800],
                    "cycle_number": item.get("cycle_number") if isinstance(item, dict) else None,
                    "evidence_ref": str(item.get("_id") or item.get("memory_id") or "") if isinstance(item, dict) else "",
                })
    return selected[-8:]


def _dedupe_sections(sections: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    seen: Dict[str, str] = {}
    seen_text: Dict[str, str] = {}
    removed_tokens = 0
    removed: List[Dict[str, Any]] = []

    def long_texts(value: Any) -> List[str]:
        if isinstance(value, str):
            normalized = re.sub(r"\s+", " ", value).strip().lower()
            return [normalized] if len(normalized) >= 32 else []
        if isinstance(value, list):
            return [text for item in value for text in long_texts(item)]
        if isinstance(value, dict):
            return [text for item in value.values() for text in long_texts(item)]
        return []

    def visit(value: Any, source: str) -> Any:
        nonlocal removed_tokens
        if isinstance(value, list):
            kept = []
            for item in value:
                fp = _fingerprint(item)
                item_texts = long_texts(item)
                duplicate_text = next((text for text in item_texts if text in seen_text), "")
                if fp in seen or duplicate_text:
                    token_count = _tokens(item)
                    removed_tokens += token_count
                    removed.append({
                        "source": source,
                        "duplicate_of": seen.get(fp) or seen_text.get(duplicate_text),
                        "estimated_tokens": token_count,
                    })
                    continue
                seen[fp] = source
                for text in item_texts:
                    seen_text[text] = source
                kept.append(item)
            return kept
        if isinstance(value, dict):
            return {key: visit(child, f"{source}.{key}") for key, child in value.items()}
        return value

    deduped = {key: visit(value, key) for key, value in sections.items()}
    return deduped, {"removed_tokens": removed_tokens, "removed_items": removed[:100]}


class DevelopStoryContextService:
    def supports_agent(self, agent_name: str) -> bool:
        return agent_name in ROLE_MANIFESTS

    def manifest(self, agent_name: str) -> RoleManifest:
        return ROLE_MANIFESTS.get(agent_name, DEFAULT_MANIFEST)

    def build_packet(
        self,
        *,
        agent_name: str,
        project: Dict[str, Any],
        state: Dict[str, Any],
        retrieved_memory: List[Dict[str, Any]],
        agent_memory: Dict[str, Any],
    ) -> Dict[str, Any]:
        manifest = self.manifest(agent_name)
        story_bible = state.get("story_bible") or {}
        project_identity = {
            key: project.get(key)
            for key in ("title", "premise", "genre", "tone", "themes", "target_length", "audience", "narrative_goals")
            if project.get(key) not in (None, "", [], {})
        }
        authority = {
            "project_identity": _compact_scalar(project_identity),
            "canon": _safe_authority((state.get("canon_facts") or [])[-60:]),
            "approved_decisions": _safe_authority((state.get("decision_registry") or [])[-60:]),
            "confirmed_planning": _safe_authority((state.get("confirmed_story_studio_planning") or [])[-120:]),
            "rejected_prohibitions": [
                _authority_item(item)
                for item in (state.get("rejected_decisions") or [])[-30:]
            ],
        }
        role_projection = {
            section: _section_rows(section, story_bible.get(section))
            for section in manifest.sections
            if story_bible.get(section) not in (None, "", [], {})
        }
        handoffs = [
            _compact_scalar(item)
            for item in state.get("cycle_handoffs") or []
            if item.get("specialist") in manifest.upstream_roles
            and item.get("accepted_state") != "rejected"
        ][-8:]
        chapter_memory: Any = {}
        if manifest.chapter_memory:
            chapter_memory = _compact_scalar(compact_chapter_memory_context(state.get("chapter_memory") or {}))
            if isinstance(chapter_memory, dict):
                chapter_memory = {
                    key: value[-12:] if isinstance(value, list) else value
                    for key, value in chapter_memory.items()
                }
        sections = {
            "instruction": _compact_scalar((state.get("new_messages") or [])[-5:]),
            "authority": authority,
            "role_specific_structured_context": role_projection,
            "native_retrieval": [compact_retrieval_hit(item) for item in retrieved_memory[:manifest.native_limit]],
            "chapter_episode_memory": chapter_memory,
            "previous_agent_handoffs": handoffs,
            "agent_workflow_memory": _workflow_memory(agent_memory),
            "workflow_metadata": {
                "cycle_number": int(state.get("cycle_number") or 1),
                "agent": agent_name,
                "arc_scope": _compact_scalar(state.get("arc_focus") or {}),
                "authority_rule": "Only approved prose, active canon, approved decisions, and confirmed planning are authoritative. Every other supplied item is derived evidence.",
                "evidence_rule": "Native retrieval, chapter intelligence, and handoffs may contain derived or conflicting evidence. Use them to locate questions and support recommendations, never to replace the authority snapshot. All specialist proposals remain pending author review.",
            },
        }
        sections, duplicate_report = _dedupe_sections(sections)
        source_tokens = {key: _tokens(value) for key, value in sections.items()}
        authority_expected = {
            "canon": len({_fingerprint(item) for item in _safe_authority((state.get("canon_facts") or [])[-60:])}),
            "approved_decisions": len({_fingerprint(item) for item in _safe_authority((state.get("decision_registry") or [])[-60:])}),
            "confirmed_planning": len({_fingerprint(item) for item in _safe_authority((state.get("confirmed_story_studio_planning") or [])[-120:])}),
        }
        authority_actual = {
            key: len(sections["authority"].get(key) or [])
            for key in authority_expected
        }
        authority_complete = authority_expected == authority_actual
        total = _tokens(sections)
        fallback_reason = ""
        if not authority_complete:
            fallback_reason = "compact_authority_coverage_mismatch"
        elif total > manifest.budget_tokens:
            # Trim optional evidence in a deterministic order. Authority and
            # the role projection are never removed to satisfy a budget.
            for key in ("agent_workflow_memory", "native_retrieval", "chapter_episode_memory", "previous_agent_handoffs"):
                value = sections[key]
                while total > manifest.budget_tokens and isinstance(value, list) and value:
                    value.pop()
                    total = _tokens(sections)
                if total <= manifest.budget_tokens:
                    break
            if total > manifest.budget_tokens:
                fallback_reason = "mandatory_role_context_exceeds_budget"
        attribution = {
            "mode": "role_specific",
            "manifest_sections": list(manifest.sections),
            "packet_budget_tokens": manifest.budget_tokens,
            "tokens_by_source": {key: _tokens(value) for key, value in sections.items()},
            "pre_budget_tokens_by_source": source_tokens,
            "duplicate_tokens_removed": duplicate_report["removed_tokens"],
            "duplicates_removed": duplicate_report["removed_items"],
            "authority_expected": authority_expected,
            "authority_actual": authority_actual,
            "authority_complete": authority_complete,
            "final_context_tokens": _tokens(sections),
            "fallback_reason": fallback_reason,
        }
        return {"context": sections, "attribution": attribution, "fallback_required": bool(fallback_reason)}

    @staticmethod
    def build_handoff(
        *,
        agent_name: str,
        cycle_number: int,
        payload: Dict[str, Any],
        counts: Dict[str, int],
        contradiction_reports: List[Dict[str, Any]],
        proposal_id: str,
        run_id: str,
    ) -> Dict[str, Any]:
        recommendations = [str(payload.get("recommendation") or "").strip()]
        recommendations = [item for item in recommendations if item]
        claims = [str(payload.get("summary") or "").strip()]
        claims = [item for item in claims if item]
        affected: List[str] = []
        for key, value in payload.items():
            if not isinstance(value, list):
                continue
            for item in value[:20]:
                if isinstance(item, dict):
                    for field in ("name", "title", "character_name", "character_a", "character_b", "mystery_id", "arc_id"):
                        if item.get(field):
                            affected.append(str(item[field]))
        constraints = [
            text for text in [str(item) for item in payload.get("concerns") or []]
            if any(term in text.lower() for term in ("must", "preserve", "canon", "decision", "confirmed", "chronolog", "knowledge"))
        ]
        return {
            "specialist": agent_name,
            "cycle_number": cycle_number,
            "claims": claims[:5],
            "recommendations": recommendations[:5],
            "affected_entities": list(dict.fromkeys(affected))[:30],
            "constraints_preserved": constraints[:10],
            "new_conflicts": [str(item.get("message") or item.get("summary") or item)[:800] for item in contradiction_reports[:10]],
            "open_questions": [str(item)[:800] for item in payload.get("questions") or payload.get("open_questions") or []][:10],
            "accepted_state": "pending",
            "evidence_refs": [
                *(f"artifact:{key}" for key, value in counts.items() if int(value or 0) > 0),
                *( [f"proposal:{proposal_id}"] if proposal_id else [] ),
                *( [f"run:{run_id}"] if run_id else [] ),
            ],
        }

    async def persist_handoff(self, db, project_id: str, run_id: str, handoff: Dict[str, Any]) -> Dict[str, Any]:
        query = {
            "project_id": ObjectId(project_id),
            "run_id": ObjectId(run_id) if ObjectId.is_valid(run_id) else run_id,
            "cycle_number": int(handoff["cycle_number"]),
            "specialist": handoff["specialist"],
        }
        document = {**query, **handoff, "updated_at": datetime.utcnow()}
        await db.develop_story_handoffs.update_one(
            query,
            {"$set": document, "$setOnInsert": {"created_at": datetime.utcnow()}},
            upsert=True,
        )
        return document

    async def load_handoffs(self, db, project_id: str, run_id: str, cycle_number: int) -> List[Dict[str, Any]]:
        if not run_id:
            return []
        query = {
            "project_id": ObjectId(project_id),
            "run_id": ObjectId(run_id) if ObjectId.is_valid(run_id) else run_id,
            "cycle_number": int(cycle_number),
        }
        rows = await db.develop_story_handoffs.find(query).sort("created_at", 1).to_list(length=100)
        return [
            {key: value for key, value in row.items() if key not in {"_id", "project_id", "run_id", "created_at", "updated_at"}}
            for row in rows
        ]


develop_story_context_service = DevelopStoryContextService()
