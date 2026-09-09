"""Project completeness and milestone gates derived from existing story truth."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Iterable
from uuid import uuid4

from bson import ObjectId

from app.services.narrative_analysis_engine import narrative_analysis_engine
from app.services.story_bible_service import get_story_bible


DIMENSIONS = ("story", "character", "world", "power", "relationship", "mystery", "timeline", "canon")


def _serialize(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {("id" if key == "_id" else key): _serialize(item) for key, item in value.items()}
    return value


def _has(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return value not in (None, False, 0)


def _criterion(
    criterion_id: str,
    label: str,
    met: bool,
    *,
    evidence: Iterable[Any] = (),
    target: str,
    required: bool = True,
    improvement: str = "",
) -> Dict[str, Any]:
    return {
        "criterion_id": criterion_id,
        "label": label,
        "met": bool(met),
        "required": required,
        "evidence": list(evidence),
        "target": target,
        "suggested_improvement": improvement or ("No action required." if met else f"Complete {label.lower()}."),
    }


def _dimension(name: str, criteria: list[Dict[str, Any]]) -> Dict[str, Any]:
    required = [item for item in criteria if item["required"]]
    recommended = [item for item in criteria if not item["required"]]
    required_score = sum(1 for item in required if item["met"]) / max(1, len(required))
    recommended_score = sum(1 for item in recommended if item["met"]) / max(1, len(recommended)) if recommended else 1
    score = round(100 * (required_score * .9 + recommended_score * .1))
    blockers = [item for item in required if not item["met"]]
    return {
        "dimension": name,
        "score": score,
        "status": "complete" if not blockers and score >= 90 else "in_progress" if score else "not_started",
        "criteria": criteria,
        "blockers": blockers,
        "remaining": [item for item in criteria if not item["met"]],
    }


class NarrativeCompletenessService:
    async def _project(self, db, project_id: str) -> tuple[ObjectId, Dict[str, Any]]:
        if not ObjectId.is_valid(project_id):
            raise ValueError("Invalid project ID")
        pid = ObjectId(project_id)
        project = await db.projects.find_one({"_id": pid})
        if not project:
            raise ValueError("Project not found")
        return pid, project

    async def calculate(self, db, project_id: str, *, persist: bool = True) -> Dict[str, Any]:
        pid, project = await self._project(db, project_id)
        bible = await get_story_bible(db, project_id)
        sections = bible.get("sections") or {}
        platform = await narrative_analysis_engine.platform(db, project_id)
        findings = platform.get("findings") or []
        scores = (platform.get("snapshot") or {}).get("scores") or {}

        vision = sections.get("story_vision") or {}
        characters = sections.get("characters") or []
        world = sections.get("world") or {}
        power = sections.get("power_system") or {}
        relationships = sections.get("relationships") or []
        mysteries = sections.get("mysteries") or []
        timeline = sections.get("timeline") or []
        arcs = sections.get("arcs") or []
        drafting = sections.get("drafting") or {}
        editorial = sections.get("editorial") or {}
        manuscript = sections.get("manuscript") or {}
        canon_section = sections.get("canon_governance") or {}
        proposals = (sections.get("interactive_intelligence") or {}).get("canon_proposals") or []
        progressions = sections.get("character_progressions") or []
        active_characters = [item for item in characters if str(item.get("current_status") or "active").lower() not in {"dead", "departed", "archived"}]
        major_characters = [item for item in active_characters if str(item.get("role") or "").lower() in {"protagonist", "antagonist", "main", "lead"}] or active_characters[:3]
        open_mysteries = [item for item in mysteries if str(item.get("status") or "open").lower() not in {"resolved", "closed", "paid_off", "abandoned"}]
        mysteries_not_applicable = (sections.get("ai_insights") or {}).get("mysteries_not_applicable") is True
        mystery_scope_defined = bool(mysteries) or mysteries_not_applicable
        open_conflicts = [item for item in canon_section.get("conflicts") or [] if str(item.get("status") or "open") in {"open", "acknowledged"}]
        critical = [item for item in findings if str(item.get("severity")) in {"critical", "high"}]
        timeline_critical = [item for item in critical if item.get("domain") == "timeline"]
        canon_critical = [item for item in critical if item.get("domain") == "canon"]

        dimensions = {
            "story": _dimension("story", [
                _criterion("story.premise", "A clear premise", _has(vision.get("premise") or project.get("premise") or project.get("idea_dump")), target="vision", evidence=[vision.get("premise") or project.get("idea_dump")], improvement="Define the protagonist, disruption, objective, and stakes in one clear premise."),
                _criterion("story.genre", "Genre", _has(vision.get("genre") or project.get("genre")), target="vision", evidence=[vision.get("genre") or project.get("genre")]),
                _criterion("story.themes", "At least one theme", _has(vision.get("themes") or project.get("themes")), target="vision", evidence=vision.get("themes") or project.get("themes") or []),
                _criterion("story.goal", "A primary narrative goal", _has(vision.get("narrative_goals")) or any(_has(item.get("goal")) for item in arcs), target="arcs", evidence=vision.get("narrative_goals") or [item.get("goal") for item in arcs]),
                _criterion("story.conflict", "A central conflict", any(_has(item.get("conflict")) for item in arcs), target="arcs", evidence=[item.get("conflict") for item in arcs if item.get("conflict")]),
                _criterion("story.arc", "At least one developed story arc", any(str(item.get("development_status") or "idea") not in {"idea", "discussion"} for item in arcs), target="arc-development", evidence=[item.get("title") for item in arcs]),
            ]),
            "character": _dimension("character", [
                _criterion("character.primary", "A primary character", bool(major_characters), target="characters", evidence=[item.get("name") for item in major_characters]),
                _criterion("character.motivation", "Motivations for major characters", bool(major_characters) and all(_has(item.get("motivations") or item.get("goals")) for item in major_characters), target="characters", evidence=[{"name": item.get("name"), "motivations": item.get("motivations") or item.get("goals")} for item in major_characters]),
                _criterion("character.backstory", "Backstory or formative history", bool(major_characters) and all(_has(item.get("backstory") or item.get("history") or item.get("trauma")) for item in major_characters), target="characters", required=False, evidence=[item.get("name") for item in major_characters]),
                _criterion("character.progression", "Arc progression for major characters", bool(major_characters) and all(any(str(row.get("character") or "").lower() == str(item.get("name") or "").lower() for row in progressions) for item in major_characters), target="arc-development", evidence=[row.get("character") for row in progressions]),
                _criterion("character.health", "No high-severity character inconsistencies", not any(item.get("domain") == "character" for item in critical), target="story-health", evidence=[item.get("finding_id") for item in critical if item.get("domain") == "character"]),
            ]),
            "world": _dimension("world", [
                _criterion("world.foundation", "A defined world foundation", bool(world), target="world", evidence=[list(world)[:12]] if world else []),
                _criterion("world.locations", "Named locations", _has(world.get("locations")) or any(item.get("canon_type") == "world" for item in canon_section.get("registry") or []), target="world", evidence=world.get("locations") or []),
                _criterion("world.rules", "World rules or constraints", _has(world.get("world_rules") or world.get("rules") or world.get("politics") or world.get("history")), target="world", evidence=world.get("world_rules") or []),
                _criterion("world.organizations", "Organizations or factions", _has(sections.get("factions")), target="factions", required=False, evidence=[item.get("name") for item in sections.get("factions") or []]),
                _criterion("world.consistency", "No high-severity world/canon conflicts", not canon_critical, target="canon", evidence=[item.get("finding_id") for item in canon_critical]),
            ]),
            "power": _dimension("power", [
                _criterion("power.applicability", "Power system defined or explicitly not applicable", bool(power) and (_has(power.get("ranks") or power.get("levels") or power.get("rules") or power.get("limitations")) or power.get("not_applicable") is True), target="power", evidence=[power.get("not_applicable")]),
                _criterion("power.rules", "Power rules and capabilities", power.get("not_applicable") is True or _has(power.get("ranks") or power.get("levels") or power.get("skills") or power.get("classes")), target="power", evidence=power.get("ranks") or power.get("levels") or []),
                _criterion("power.costs", "Costs or limitations", power.get("not_applicable") is True or _has(power.get("limitations") or power.get("costs")), target="power", evidence=power.get("limitations") or power.get("costs") or []),
                _criterion("power.progression", "Progression path", power.get("not_applicable") is True or _has(power.get("progression_curve") or power.get("evolution_paths") or sections.get("power_progressions")), target="power", required=False, evidence=power.get("evolution_paths") or []),
            ]),
            "relationship": _dimension("relationship", [
                _criterion("relationship.primary", "At least one meaningful relationship", bool(relationships), target="relationships", evidence=[f"{item.get('character_a')} / {item.get('character_b')}" for item in relationships]),
                _criterion("relationship.definition", "Relationship type and current state", bool(relationships) and all(_has(item.get("relationship") or item.get("type") or item.get("status")) for item in relationships), target="relationships", evidence=[item.get("relationship") or item.get("type") for item in relationships]),
                _criterion("relationship.evolution", "Planned relationship evolution", any(_has(item.get("history") or item.get("future_payoff")) for item in relationships), target="relationships", required=False, evidence=[item.get("future_payoff") for item in relationships if item.get("future_payoff")]),
            ]),
            "mystery": _dimension("mystery", [
                _criterion("mystery.registry", "Mysteries intentionally defined or explicitly absent", mystery_scope_defined, target="mysteries", evidence=[item.get("question") for item in mysteries]),
                _criterion("mystery.truth", "A truth or intended answer for each mystery", mystery_scope_defined and (mysteries_not_applicable or all(_has(item.get("truth")) for item in open_mysteries)), target="mysteries", evidence=[item.get("question") for item in open_mysteries if not item.get("truth")]),
                _criterion("mystery.payoff", "A reveal target for every open mystery", mystery_scope_defined and (mysteries_not_applicable or all(_has(item.get("reveal_target")) for item in open_mysteries)), target="mysteries", evidence=[item.get("question") for item in open_mysteries if not item.get("reveal_target")]),
                _criterion("mystery.resolution", "All publication-scope mysteries resolved or intentionally deferred", mystery_scope_defined and (mysteries_not_applicable or not open_mysteries), target="mysteries", required=False, evidence=[item.get("question") for item in open_mysteries]),
            ]),
            "timeline": _dimension("timeline", [
                _criterion("timeline.entries", "Chronological anchor events", bool(timeline), target="timeline", evidence=[item.get("title") or item.get("event") for item in timeline[:20]]),
                _criterion("timeline.known", "Major events have known or probable chronology", bool(timeline) and all(str(item.get("certainty") or "known") != "unknown" for item in timeline if str(item.get("importance") or "major") == "major"), target="timeline", evidence=[item.get("title") for item in timeline if str(item.get("certainty")) == "unknown"]),
                _criterion("timeline.consistency", "No high-severity timeline findings", not timeline_critical, target="timeline", evidence=[item.get("finding_id") for item in timeline_critical]),
                _criterion("timeline.health", "Timeline Health at or above 85", int(scores.get("timeline", 0)) >= 85, target="story-health", evidence=[scores.get("timeline")]),
            ]),
            "canon": _dimension("canon", [
                _criterion("canon.registry", "Official canon facts", bool(canon_section.get("registry")), target="canon", evidence=[item.get("canon_id") for item in (canon_section.get("registry") or [])[:20]]),
                _criterion("canon.conflicts", "No high-severity open canon conflicts", not any(str(item.get("severity")) in {"high", "critical"} for item in open_conflicts), target="canon", evidence=[item.get("conflict_id") for item in open_conflicts]),
                _criterion("canon.proposals", "Canon proposal queue reviewed", not any(str(item.get("status")) == "pending" for item in proposals), target="canon", evidence=[item.get("proposal_id") for item in proposals if item.get("status") == "pending"]),
                _criterion("canon.health", "Canon Health at or above 85", int(scores.get("canon", 0)) >= 85, target="story-health", evidence=[scores.get("canon")]),
            ]),
        }
        dimensions["mystery"]["readiness_state"] = (
            "not_applicable" if mysteries_not_applicable
            else "absent" if not mysteries
            else "resolved" if not open_mysteries
            else "open"
        )

        def gate(gate_id: str, label: str, criterion_refs: list[tuple[str, str]], extra: list[Dict[str, Any]] | None = None) -> Dict[str, Any]:
            criteria = []
            for dimension_name, criterion_id in criterion_refs:
                criteria.extend(item for item in dimensions[dimension_name]["criteria"] if item["criterion_id"] == criterion_id)
            criteria.extend(extra or [])
            blockers = [item for item in criteria if item["required"] and not item["met"]]
            return {"gate_id": gate_id, "label": label, "achieved": not blockers, "criteria": criteria, "blockers": blockers}

        concept = gate("concept_complete", "Concept Complete", [
            ("story", "story.premise"), ("story", "story.genre"), ("story", "story.themes"),
            ("story", "story.goal"), ("story", "story.conflict"), ("character", "character.primary"),
            ("character", "character.motivation"),
        ])
        world_ready = gate("world_ready", "World Ready", [
            ("world", "world.foundation"), ("world", "world.locations"), ("world", "world.rules"),
            ("world", "world.consistency"), ("power", "power.applicability"), ("power", "power.costs"),
        ], [_criterion("gate.concept", "Concept Complete", concept["achieved"], target="dashboard", evidence=[concept["achieved"]])])
        readiness_reports = (sections.get("readiness") or {}).get("reports") or []
        draft_ready = gate("draft_ready", "Draft Ready", [
            ("story", "story.arc"), ("character", "character.progression"), ("relationship", "relationship.primary"),
            ("timeline", "timeline.entries"), ("timeline", "timeline.consistency"), ("mystery", "mystery.payoff"),
        ], [
            _criterion("gate.concept", "Concept Complete", concept["achieved"], target="dashboard"),
            _criterion("gate.world", "World Ready", world_ready["achieved"], target="dashboard"),
            _criterion("gate.arc_readiness", "An approved draftable arc", any(item.get("drafting_eligible") for item in readiness_reports), target="readiness", evidence=[item.get("arc_id") for item in readiness_reports if item.get("drafting_eligible")]),
            _criterion("gate.chapter_plan", "At least one chapter plan", bool(drafting.get("chapter_plans")), target="drafting"),
            _criterion("gate.scene_plan", "At least one scene plan", bool(drafting.get("scene_plans")), target="drafting"),
        ])
        chapter_plans = drafting.get("chapter_plans") or []
        chapter_drafts = drafting.get("chapter_drafts") or []
        drafted_chapter_ids = {str(item.get("chapter_plan_id") or item.get("chapter_number")) for item in chapter_drafts}
        revision_ready = gate("revision_ready", "Revision Ready", [], [
            _criterion("gate.draft", "Draft Ready", draft_ready["achieved"], target="dashboard"),
            _criterion("gate.scope_drafted", "All planned chapters have drafts", bool(chapter_plans) and all(str(item.get("chapter_plan_id") or item.get("chapter_number")) in drafted_chapter_ids for item in chapter_plans), target="drafting", evidence=[len(chapter_plans), len(chapter_drafts)]),
            _criterion("gate.editorial", "Editorial review exists", bool(editorial.get("reports")), target="editorial", evidence=[item.get("report_id") for item in editorial.get("reports") or []]),
            _criterion("gate.no_critical_structure", "No critical/high structural or continuity findings", not any(item.get("domain") in {"continuity", "balance", "pacing"} for item in critical), target="story-health", evidence=[item.get("finding_id") for item in critical]),
        ])
        approved_manuscripts = [item for item in manuscript.get("manuscripts") or [] if str(item.get("status")) == "approved"]
        publication_ready = gate("publication_ready", "Publication Ready", [], [
            _criterion("gate.revision", "Revision Ready", revision_ready["achieved"], target="dashboard"),
            _criterion("gate.manuscript", "Approved manuscript", bool(approved_manuscripts), target="manuscript", evidence=[item.get("manuscript_id") for item in approved_manuscripts]),
            _criterion("gate.health", "No critical/high unresolved Story Health findings", not critical, target="story-health", evidence=[item.get("finding_id") for item in critical]),
            _criterion("gate.canon", "Canon completeness at or above 85", dimensions["canon"]["score"] >= 85, target="canon", evidence=[dimensions["canon"]["score"]]),
            _criterion("gate.timeline", "Timeline completeness at or above 85", dimensions["timeline"]["score"] >= 85, target="timeline", evidence=[dimensions["timeline"]["score"]]),
            _criterion("gate.mystery", "Mysteries resolved or intentionally deferred", mystery_scope_defined and (mysteries_not_applicable or not open_mysteries), target="mysteries", evidence=[item.get("question") for item in open_mysteries]),
            _criterion("gate.dimensions", "Every completeness dimension at or above 80", all(item["score"] >= 80 for item in dimensions.values()), target="readiness", evidence={key: value["score"] for key, value in dimensions.items()}),
        ])
        milestones = [concept, world_ready, draft_ready, revision_ready, publication_ready]
        highest = "Getting Started"
        for item in milestones:
            if item["achieved"]:
                highest = item["label"]
            else:
                break
        remaining = [
            {**criterion, "dimension": name}
            for name, dimension in dimensions.items()
            for criterion in dimension["remaining"]
        ]
        next_actions = []
        seen_targets = set()
        for milestone in milestones:
            if milestone["achieved"]:
                continue
            for blocker in milestone["blockers"]:
                target = blocker["target"]
                if target in seen_targets:
                    continue
                seen_targets.add(target)
                next_actions.append({
                    "action_id": blocker["criterion_id"],
                    "label": blocker["label"],
                    "reason": blocker["suggested_improvement"],
                    "target": target,
                    "milestone": milestone["label"],
                })
            if next_actions:
                break
        now = datetime.utcnow()
        snapshot = {
            "project_id": pid,
            "snapshot_id": str(uuid4()),
            "snapshot_type": "current",
            "analysis_id": (platform.get("snapshot") or {}).get("analysis_id"),
            "story_bible_version": bible.get("version"),
            "overall_completion": round(sum(item["score"] for item in dimensions.values()) / len(DIMENSIONS)),
            "dimensions": dimensions,
            "milestones": milestones,
            "current_milestone": highest,
            "remaining_work": remaining,
            "next_actions": next_actions[:5],
            "calculated_at": now,
        }
        fingerprint = hashlib.sha256(json.dumps(_serialize({
            "dimensions": {key: value["score"] for key, value in dimensions.items()},
            "milestones": {item["gate_id"]: item["achieved"] for item in milestones},
            "remaining": [item["criterion_id"] for item in remaining],
        }), sort_keys=True).encode("utf-8")).hexdigest()
        snapshot["fingerprint"] = fingerprint
        if persist:
            previous = await db.narrative_completeness_snapshots.find_one({"project_id": pid, "snapshot_type": "current"})
            await db.narrative_completeness_snapshots.update_one(
                {"project_id": pid, "snapshot_type": "current"}, {"$set": snapshot}, upsert=True,
            )
            if not previous or previous.get("fingerprint") != fingerprint:
                await db.narrative_completeness_history.insert_one({**snapshot, "snapshot_type": "history"})
        return _serialize(snapshot)


narrative_completeness_service = NarrativeCompletenessService()
