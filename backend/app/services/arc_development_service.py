"""Deterministic arc maturity, focus, dependency, and draftable evaluation."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable
from uuid import uuid4

from bson import ObjectId

from app.services.readiness_service import readiness_service


DEVELOPMENT_STATUSES = (
    "idea",
    "discussion",
    "outline",
    "development",
    "approved",
    "active",
    "draftable",
    "completed",
    "archived",
)
FOCUS_ROLES = {"current", "next", "future"}
CHECKLIST_PRIORITIES = {"required", "recommended", "optional"}
CHECKLIST_STATUSES = {
    "missing",
    "discussed",
    "proposed",
    "approved",
    "completed",
    "waived",
}
SATISFIED_CHECKLIST_STATUSES = {"approved", "completed", "waived"}

DEFAULT_DIMENSION_WEIGHTS: Dict[str, int] = {
    "goal_clarity": 10,
    "conflict_clarity": 10,
    "stakes_clarity": 10,
    "character_growth": 10,
    "progression_coverage": 10,
    "knowledge_coverage": 8,
    "foreshadow_coverage": 8,
    "artifact_coverage": 8,
    "timeline_coverage": 10,
    "mystery_coverage": 8,
    "resolution_planning": 8,
}

DEFAULT_CHECKLIST_TEMPLATE = (
    ("Arc Foundation", "Main Goal Defined", "goal_clarity", "required"),
    ("Arc Foundation", "Conflict Defined", "conflict_clarity", "required"),
    ("Arc Foundation", "Primary Stakes Defined", "stakes_clarity", "required"),
    ("Character", "Character Growth Defined", "character_growth", "required"),
    ("Structure", "Beginning Defined", "timeline_coverage", "required"),
    ("Structure", "Major Turning Point Defined", "timeline_coverage", "required"),
    ("Structure", "Climax Defined", "timeline_coverage", "required"),
    ("Structure", "Resolution Direction Defined", "resolution_planning", "required"),
    ("Continuity", "Knowledge Structure Present", "knowledge_coverage", "recommended"),
    ("Continuity", "Foreshadow Seeds Present", "foreshadow_coverage", "recommended"),
    ("Continuity", "Artifact Relevance Present", "artifact_coverage", "optional"),
    ("Progression", "Power Growth Present", "progression_coverage", "optional"),
)


def _satisfied(item: Dict[str, Any]) -> bool:
    return str(item.get("status") or "").lower() in SATISFIED_CHECKLIST_STATUSES


def _nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return value is not None


class ArcDevelopmentService:
    maturity_threshold = 85

    def normalize_checklist(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        priority = str(payload.get("priority") or "recommended").lower()
        status = str(payload.get("status") or "missing").lower()
        if priority not in CHECKLIST_PRIORITIES:
            raise ValueError("Unsupported checklist priority")
        if status not in CHECKLIST_STATUSES:
            raise ValueError("Unsupported checklist status")
        weight = max(0, min(int(payload.get("weight") or 1), 100))
        return {
            "category": str(payload.get("category") or "Arc Development").strip(),
            "title": str(payload.get("title") or "Untitled checklist item").strip(),
            "description": str(payload.get("description") or "").strip(),
            "priority": priority,
            "status": status,
            "dimension": str(payload.get("dimension") or "resolution_planning").strip(),
            "weight": weight,
            "evidence": list(payload.get("evidence") or []),
            "blocking": bool(payload.get("blocking", priority == "required")),
        }

    async def seed_default_checklist(
        self, db, project_id: str, arc_id: str, *, source: str = "system"
    ) -> int:
        pid = ObjectId(project_id)
        if await db.arc_checklists.count_documents(
            {"project_id": pid, "arc_id": arc_id}
        ):
            return 0
        now = datetime.utcnow()
        documents = []
        for category, title, dimension, priority in DEFAULT_CHECKLIST_TEMPLATE:
            documents.append(
                {
                    "project_id": pid,
                    "arc_id": arc_id,
                    "item_id": str(uuid4()),
                    "category": category,
                    "title": title,
                    "description": "",
                    "priority": priority,
                    "status": "missing",
                    "dimension": dimension,
                    "weight": 1,
                    "evidence": [],
                    "blocking": priority == "required",
                    "source": source,
                    "created_at": now,
                    "updated_at": now,
                }
            )
        if documents:
            await db.arc_checklists.insert_many(documents)
        return len(documents)

    async def _dependency_status(
        self, db, pid: ObjectId, dependency: Dict[str, Any]
    ) -> tuple[bool, str]:
        dependency_type = str(dependency.get("dependency_type") or "")
        target_id = str(dependency.get("target_id") or "")
        required_state = str(dependency.get("required_state") or "").lower()
        if dependency_type in {"requires_arc", "follows_arc"}:
            target = await db.story_arcs.find_one(
                {"project_id": pid, "arc_id": target_id}
            )
            if not target:
                return False, "Required arc does not exist"
            status = str(target.get("development_status") or "idea").lower()
            acceptable = (
                {required_state}
                if required_state
                else {"draftable", "completed", "archived"}
            )
            return status in acceptable, f"Arc status is {status}"
        if dependency_type == "depends_on_reveal":
            query = {
                "project_id": pid,
                "event_type": "reveal",
                "$or": [{"evolution_id": target_id}, {"knowledge_entry_id": target_id}],
            }
            found = await db.knowledge_evolutions.find_one(query)
            return bool(found), "Reveal event found" if found else "Reveal event missing"
        if dependency_type == "depends_on_artifact":
            found = await db.artifact_registry.find_one(
                {"project_id": pid, "artifact_id": target_id}
            )
            if not found:
                return False, "Artifact does not exist"
            status = str(found.get("status") or "").lower()
            return (not required_state or status == required_state), f"Artifact status is {status}"
        if dependency_type == "depends_on_character_growth":
            identity = [{"character": target_id}]
            if ObjectId.is_valid(target_id):
                identity.append({"_id": ObjectId(target_id)})
            found = await db.character_progressions.find_one(
                {"project_id": pid, "$or": identity}
            )
            complete = bool(
                found
                and (
                    _nonempty(found.get("arc_end_state"))
                    or _nonempty(found.get("desired_state"))
                )
            )
            return complete, "Character end state found" if complete else "Character growth incomplete"
        if dependency_type == "depends_on_knowledge_state":
            found = await db.knowledge_entries.find_one(
                {"project_id": pid, "entry_id": target_id}
            )
            if not found:
                return False, "Knowledge entry does not exist"
            state = str(found.get("knowledge_type") or "").lower()
            return (not required_state or state == required_state), f"Knowledge state is {state}"
        return False, "Unsupported dependency type"

    async def validate_dependencies(
        self, db, project_id: str, arc_id: str, *, persist: bool = True
    ) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        dependencies = await db.arc_dependencies.find(
            {"project_id": pid, "arc_id": arc_id}
        ).sort("created_at", 1).to_list(length=1000)
        results = []
        now = datetime.utcnow()
        for dependency in dependencies:
            satisfied, reason = await self._dependency_status(db, pid, dependency)
            status = "satisfied" if satisfied else "blocked"
            if persist:
                await db.arc_dependencies.update_one(
                    {"_id": dependency["_id"]},
                    {
                        "$set": {
                            "status": status,
                            "validation_reason": reason,
                            "validated_at": now,
                            "updated_at": now,
                        }
                    },
                )
            results.append(
                {
                    "dependency_id": dependency.get("dependency_id"),
                    "dependency_type": dependency.get("dependency_type"),
                    "blocking": bool(dependency.get("blocking", True)),
                    "status": status,
                    "reason": reason,
                }
            )
        blockers = [
            item
            for item in results
            if item["blocking"] and item["status"] != "satisfied"
        ]
        return {"items": results, "blockers": blockers, "satisfied": not blockers}

    async def _dimension_evidence(
        self, db, pid: ObjectId, arc: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        arc_id = arc["arc_id"]
        progression = await db.character_progressions.find(
            {"project_id": pid, "arc_id": arc_id}
        ).to_list(length=500)
        powers = await db.power_progressions.find(
            {"project_id": pid, "arc_id": arc_id}
        ).to_list(length=500)
        knowledge = await db.knowledge_entries.count_documents(
            {"project_id": pid, "arc_id": arc_id}
        )
        knowledge_evolution = await db.knowledge_evolutions.count_documents(
            {"project_id": pid, "arc_id": arc_id}
        )
        foreshadow = await db.foreshadow_registry_v2.count_documents(
            {
                "project_id": pid,
                "$or": [{"arc_planted": arc_id}, {"payoff_arc_id": arc_id}],
            }
        )
        foreshadow_nodes = await db.foreshadow_chains.count_documents(
            {"project_id": pid, "arc_id": arc_id}
        )
        artifacts = await db.artifact_registry.count_documents(
            {"project_id": pid, "arc_ids": arc_id}
        )
        artifact_nodes = await db.artifact_evolutions.count_documents(
            {"project_id": pid, "arc_id": arc_id}
        )
        timeline = await db.timeline_entries.find(
            {"project_id": pid, "arc_id": arc_id}
        ).to_list(length=500)
        known_timeline = [item for item in timeline if item.get("certainty") != "unknown"]
        mysteries = len(list(arc.get("mysteries") or []))
        if not mysteries:
            mysteries = await db.mystery_registry.count_documents(
                {
                    "project_id": pid,
                    "$or": [
                        {"arc_id": arc_id},
                        {"reveal_target": arc.get("title")},
                    ],
                }
            )
        character_complete = _nonempty(arc.get("character_growth")) or any(
            _nonempty(item.get("arc_start_state") or item.get("current_state"))
            and _nonempty(item.get("arc_midpoint_state"))
            and _nonempty(item.get("arc_end_state") or item.get("desired_state"))
            for item in progression
        )
        progression_complete = character_complete and any(
            _nonempty(item.get("starting_power"))
            and _nonempty(item.get("ending_power"))
            and (
                _nonempty(item.get("new_abilities"))
                or _nonempty(item.get("mastered_abilities"))
            )
            for item in powers
        )
        resolution = (
            arc.get("resolution_direction")
            or arc.get("payoffs")
            or arc.get("purpose")
        )
        return {
            "goal_clarity": {"complete": _nonempty(arc.get("goal")), "evidence": ["arc.goal"]},
            "conflict_clarity": {"complete": _nonempty(arc.get("conflict")), "evidence": ["arc.conflict"]},
            "stakes_clarity": {"complete": _nonempty(arc.get("stakes")), "evidence": ["arc.stakes"]},
            "character_growth": {
                "complete": character_complete,
                "evidence": [
                    *( ["arc.character_growth"] if _nonempty(arc.get("character_growth")) else [] ),
                    f"{len(progression)} character progression records",
                ],
            },
            "progression_coverage": {
                "complete": progression_complete,
                "evidence": [f"{len(powers)} power progression records"],
            },
            "knowledge_coverage": {
                "complete": knowledge > 0 and knowledge_evolution > 0,
                "evidence": [f"{knowledge} knowledge entries", f"{knowledge_evolution} evolution events"],
            },
            "foreshadow_coverage": {
                "complete": foreshadow > 0 and foreshadow_nodes >= 2,
                "evidence": [f"{foreshadow} registry records", f"{foreshadow_nodes} chain nodes"],
            },
            "artifact_coverage": {
                "complete": artifacts > 0 and artifact_nodes > 0,
                "evidence": [f"{artifacts} artifacts", f"{artifact_nodes} evolution events"],
            },
            "timeline_coverage": {
                "complete": len(known_timeline) >= 3,
                "evidence": [f"{len(known_timeline)} known/probable timeline anchors"],
            },
            "mystery_coverage": {
                "complete": mysteries > 0,
                "evidence": [f"{mysteries} mystery references"],
            },
            "resolution_planning": {
                "complete": _nonempty(resolution),
                "evidence": ["resolution direction or payoff"],
            },
        }

    async def evaluate(
        self, db, project_id: str, arc_id: str, *, persist: bool = True
    ) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        arc = await db.story_arcs.find_one(
            {"project_id": pid, "arc_id": arc_id}
        )
        if not arc:
            raise ValueError("Arc not found")
        await self.seed_default_checklist(db, project_id, arc_id)
        checklist = await db.arc_checklists.find(
            {"project_id": pid, "arc_id": arc_id}
        ).sort([("priority", 1), ("category", 1), ("title", 1)]).to_list(length=1000)
        if persist:
            # Arc checklist and readiness are two projections of the same
            # author gate. Keep exact matching requirements synchronized so an
            # author does not have to approve the same fact on a second page.
            approved_titles = [
                str(item.get("title"))
                for item in checklist
                if _satisfied(item) and item.get("title")
            ]
            if approved_titles:
                await db.story_readiness.update_many(
                    {
                        "project_id": pid,
                        "arc_id": arc_id,
                        "title": {"$in": approved_titles},
                    },
                    {
                        "$set": {"status": "approved", "updated_at": datetime.utcnow()},
                        "$addToSet": {"evidence": "Approved in Arc Review"},
                    },
                )
        evidence = await self._dimension_evidence(db, pid, arc)
        dimension_weights = dict(DEFAULT_DIMENSION_WEIGHTS)
        configured_weights: Dict[str, int] = {}
        for item in checklist:
            dimension = str(item.get("dimension") or "")
            if dimension and int(item.get("weight") or 0) > 0:
                configured_weights[dimension] = configured_weights.get(dimension, 0) + int(
                    item.get("weight") or 0
                )
        for dimension, value in configured_weights.items():
            if dimension in dimension_weights:
                dimension_weights[dimension] = max(1, value)
        total_weight = sum(dimension_weights.values()) or 1
        dimensions = {}
        weighted_score = 0.0
        for dimension, weight in dimension_weights.items():
            dimension_items = [
                item for item in checklist if item.get("dimension") == dimension
            ]
            checklist_ratio = (
                sum(1 for item in dimension_items if _satisfied(item))
                / len(dimension_items)
                if dimension_items
                else 0
            )
            data_complete = bool(evidence.get(dimension, {}).get("complete"))
            if dimension_items:
                score = 100 if data_complete and checklist_ratio == 1 else (
                    70 if data_complete else round(checklist_ratio * 50)
                )
            else:
                score = 100 if data_complete else 0
            weighted_score += score * weight
            dimensions[dimension] = {
                "score": int(score),
                "weight": weight,
                "data_complete": data_complete,
                "checklist_satisfied": sum(
                    1 for item in dimension_items if _satisfied(item)
                ),
                "checklist_total": len(dimension_items),
                "evidence": evidence.get(dimension, {}).get("evidence", []),
            }
        score = int(round(weighted_score / total_weight))
        required_open = [
            item
            for item in checklist
            if item.get("priority") == "required"
            and item.get("blocking", True)
            and not _satisfied(item)
        ]
        required_dimensions = {
            str(item.get("dimension") or "")
            for item in checklist
            if item.get("priority") == "required"
            and item.get("dimension")
            and str(item.get("dimension")) in evidence
        }
        incomplete_required_dimensions = sorted(
            dimension
            for dimension in required_dimensions
            if not evidence.get(dimension, {}).get("complete")
        )
        dependency_report = await self.validate_dependencies(
            db, project_id, arc_id, persist=persist
        )
        readiness = await readiness_service.evaluate(
            db, project_id, arc_id=arc_id, persist=persist
        )
        threshold = int(arc.get("maturity_threshold") or self.maturity_threshold)
        authority_status = str(arc.get("approval_status") or "").lower()
        development_status = str(arc.get("development_status") or "idea").lower()
        gate_passed = (
            not required_open
            and not incomplete_required_dimensions
            and dependency_report["satisfied"]
            and readiness["status"] == "READY"
            and authority_status in {"approved", "active", "completed"}
            and development_status in {"approved", "active", "draftable", "completed"}
        )
        next_status = development_status
        if gate_passed and development_status in {"approved", "active", "draftable"}:
            next_status = "draftable"
        elif development_status == "draftable" and not gate_passed:
            next_status = "active"
        now = datetime.utcnow()
        report = {
            "project_id": project_id,
            "arc_id": arc_id,
            "development_status": next_status,
            "focus_role": arc.get("focus_role") or "future",
            "maturity_score": score,
            "maturity_threshold": threshold,
            "dimensions": dimensions,
            "checklist": {
                "total": len(checklist),
                "satisfied": sum(1 for item in checklist if _satisfied(item)),
                "required_open": [
                    {
                        "item_id": item.get("item_id"),
                        "title": item.get("title"),
                        "status": item.get("status"),
                    }
                    for item in required_open
                ],
            },
            "dependencies": dependency_report,
            "readiness_status": readiness["status"],
            "draftable": gate_passed,
            "blockers": [
                *[f"Checklist: {item.get('title')}" for item in required_open],
                *[
                    f"Dependency: {item.get('reason')}"
                    for item in dependency_report["blockers"]
                ],
                *(
                    []
                    if readiness["status"] == "READY"
                    else [f"Readiness is {readiness['status']}"]
                ),
                *[f"Required planning evidence is incomplete: {dimension.replace('_', ' ')}" for dimension in incomplete_required_dimensions],
            ],
            "evaluated_at": now.isoformat(),
        }
        if persist:
            await db.story_arcs.update_one(
                {"_id": arc["_id"]},
                {
                    "$set": {
                        "development_status": next_status,
                        "arc_maturity_score": score,
                        "maturity_threshold": threshold,
                        "maturity_details": dimensions,
                        "drafting_eligible": gate_passed,
                        "maturity_evaluated_at": now,
                        "updated_at": now,
                    }
                },
            )
        return report

    async def evaluate_all(
        self, db, project_id: str, *, persist: bool = True
    ) -> list[Dict[str, Any]]:
        pid = ObjectId(project_id)
        arcs = await db.story_arcs.find(
            {"project_id": pid}, {"arc_id": 1}
        ).sort("order", 1).to_list(length=1000)
        return [
            await self.evaluate(db, project_id, arc["arc_id"], persist=persist)
            for arc in arcs
            if arc.get("arc_id")
        ]

    async def activate(self, db, project_id: str, arc_id: str) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        arc = await db.story_arcs.find_one({"project_id": pid, "arc_id": arc_id})
        if not arc:
            raise ValueError("Arc not found")
        dependency_report = await self.validate_dependencies(
            db, project_id, arc_id
        )
        if not dependency_report["satisfied"]:
            raise ValueError("Arc dependencies are not satisfied")
        now = datetime.utcnow()
        await db.story_arcs.update_many(
            {
                "project_id": pid,
                "arc_id": {"$ne": arc_id},
                "focus_role": "current",
                "development_status": {"$nin": ["completed", "archived"]},
            },
            {"$set": {"focus_role": "future", "updated_at": now}},
        )
        await db.story_arcs.update_one(
            {"_id": arc["_id"]},
            {
                "$set": {
                    "focus_role": "current",
                    "development_status": "active",
                    "approval_status": "active",
                    "updated_at": now,
                }
            },
        )
        ordered = await db.story_arcs.find(
            {
                "project_id": pid,
                "arc_id": {"$ne": arc_id},
                "development_status": {"$nin": ["completed", "archived"]},
            }
        ).sort("order", 1).to_list(length=1000)
        next_assigned = False
        for candidate in ordered:
            role = "next" if not next_assigned and int(candidate.get("order") or 0) > int(arc.get("order") or 0) else "future"
            if role == "next":
                next_assigned = True
            await db.story_arcs.update_one(
                {"_id": candidate["_id"]},
                {"$set": {"focus_role": role, "updated_at": now}},
            )
        return await self.evaluate(db, project_id, arc_id)


arc_development_service = ArcDevelopmentService()
