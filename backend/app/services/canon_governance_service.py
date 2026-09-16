"""Deterministic typed canon authority and conflict detection."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Dict, Iterable
from uuid import uuid4

from bson import ObjectId

from app.services.narrative_studio import narrative_studio_service
from app.services.orchestration_engine import orchestration_engine
from app.services.orchestration_service_v2 import orchestration_service_v2
from app.services.project_intelligence_coordinator import project_intelligence_coordinator


CANON_TYPES = {
    "character",
    "power",
    "artifact",
    "timeline",
    "knowledge",
    "faction",
    "world",
    "mystery",
    "relationship",
}
SOURCE_COLLECTIONS = {
    "character_bibles",
    "character_progressions",
    "power_progressions",
    "artifact_registry",
    "artifact_evolutions",
    "timeline_entries",
    "knowledge_entries",
    "knowledge_evolutions",
    "factions",
    "world_bibles",
    "mystery_registry",
    "relationship_graphs",
    "story_arcs",
    "chapter_plans",
    "scene_plans",
    "scene_drafts",
    "chapter_drafts",
    "canon_proposals",
}


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


def _normalized(value: Any) -> str:
    return json.dumps(_serialize(value), sort_keys=True, separators=(",", ":"))


def _unique(values: Iterable[Any]) -> list[Any]:
    result = []
    seen = set()
    for value in values:
        marker = _normalized(value)
        if marker not in seen:
            result.append(value)
            seen.add(marker)
    return result


class CanonGovernanceService:
    async def _project(self, db, project_id: str) -> tuple[ObjectId, Dict[str, Any]]:
        if not ObjectId.is_valid(project_id):
            raise ValueError("Invalid project ID")
        pid = ObjectId(project_id)
        project = await db.projects.find_one({"_id": pid})
        if not project:
            raise ValueError("Project not found")
        return pid, project

    async def _after_change(
        self,
        db,
        project_id: str,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        await project_intelligence_coordinator.after_change(
            db, project_id, event_type, payload,
        )

    async def promote(
        self,
        db,
        project_id: str,
        *,
        canon_type: str,
        source_collection: str,
        source_id: str,
        subject: str,
        field: str,
        value: Any,
        source_version: int = 1,
        authority_level: str = "approved",
        evidence: list[Any] | None = None,
    ) -> Dict[str, Any]:
        pid, _ = await self._project(db, project_id)
        canon_type = canon_type.strip().lower()
        if canon_type not in CANON_TYPES:
            raise ValueError("Unsupported canon type")
        if source_collection not in SOURCE_COLLECTIONS:
            raise ValueError("Unsupported canon source collection")
        source = await db[source_collection].find_one(
            {
                "project_id": pid,
                "$or": [
                    {"_id": ObjectId(source_id)}
                    if ObjectId.is_valid(source_id)
                    else {"_id": None},
                    {"entry_id": source_id},
                    {"artifact_id": source_id},
                    {"progression_id": source_id},
                    {"evolution_id": source_id},
                    {"arc_id": source_id},
                    {"chapter_plan_id": source_id},
                    {"scene_id": source_id},
                    {"draft_id": source_id},
                    {"relationship_id": source_id},
                    {"proposal_id": source_id},
                ],
            }
        )
        if not source:
            raise ValueError("Project-owned canon source not found")
        subject = subject.strip()
        field = field.strip()
        if not subject or not field:
            raise ValueError("Canon subject and field are required")
        now = datetime.utcnow()
        source_version = max(1, int(source_version or source.get("version_number") or 1))
        fingerprint = hashlib.sha256(
            f"{project_id}|{source_collection}|{source_id}|{source_version}|"
            f"{canon_type}|{subject}|{field}|{_normalized(value)}".encode("utf-8")
        ).hexdigest()
        existing = await db.canon_registry.find_one(
            {"project_id": pid, "promotion_fingerprint": fingerprint}
        )
        if existing:
            return _serialize(existing)
        doc = {
            "project_id": pid,
            "canon_id": str(uuid4()),
            "canon_type": canon_type,
            "source_collection": source_collection,
            "source_id": source_id,
            "source_version": source_version,
            "authority_level": authority_level.strip().lower() or "approved",
            "active": True,
            "subject": subject,
            "field": field,
            "value": value,
            "evidence": _unique(evidence or [f"{source_collection}:{source_id}"]),
            "status": "LOCKED",
            "fact": f"{subject}.{field}: {_normalized(value)}",
            "promotion_fingerprint": fingerprint,
            "created_at": now,
            "updated_at": now,
        }
        inserted = await db.canon_registry.insert_one(doc)
        doc["_id"] = inserted.inserted_id
        await self.validate(db, project_id)
        await self._after_change(
            db,
            project_id,
            "canon_promoted",
            {"canon_id": doc["canon_id"], "canon_type": canon_type},
        )
        return _serialize(doc)

    async def _typed_conflicts(
        self, db, pid: ObjectId
    ) -> list[Dict[str, Any]]:
        records = await db.canon_registry.find(
            {
                "project_id": pid,
                "active": True,
                "canon_type": {"$in": sorted(CANON_TYPES)},
            }
        ).to_list(length=10000)
        grouped: Dict[tuple[str, str, str], list[Dict[str, Any]]] = {}
        for record in records:
            key = (
                str(record.get("canon_type")),
                str(record.get("subject")),
                str(record.get("field")),
            )
            grouped.setdefault(key, []).append(record)
        conflicts = []
        for key, items in grouped.items():
            values = {_normalized(item.get("value")) for item in items}
            if len(values) > 1:
                conflicts.append(
                    {
                        "conflict_type": f"{key[0]}_authority_conflict",
                        "domain": key[0],
                        "subject": key[1],
                        "field": key[2],
                        "severity": "high",
                        "message": (
                            f"Active canon has {len(values)} values for "
                            f"{key[1]}.{key[2]}"
                        ),
                        "canon_ids": [item.get("canon_id") for item in items],
                        "evidence": [_serialize(item.get("value")) for item in items],
                        "original_source": {
                            "collection": items[0].get("source_collection"),
                            "source_id": items[0].get("source_id"),
                            "canon_id": items[0].get("canon_id"),
                            "value": _serialize(items[0].get("value")),
                        },
                        "conflicting_sources": [
                            {
                                "collection": item.get("source_collection"),
                                "source_id": item.get("source_id"),
                                "canon_id": item.get("canon_id"),
                                "value": _serialize(item.get("value")),
                            }
                            for item in items[1:]
                        ],
                        "affected_locations": _unique([
                            *[value for item in items for value in item.get("affected_locations") or []],
                            *[f"{item.get('source_collection')}:{item.get('source_id')}" for item in items],
                        ]),
                        "impact": "Conflicting active facts can invalidate continuity, character, timeline, and downstream Story Bible analysis.",
                    }
                )
        return conflicts

    async def _ledger_conflicts(
        self, db, pid: ObjectId
    ) -> list[Dict[str, Any]]:
        conflicts: list[Dict[str, Any]] = []
        knowledge = await db.knowledge_entries.find(
            {"project_id": pid}
        ).to_list(length=5000)
        for item in knowledge:
            known = set(item.get("known_by_character") or item.get("known_by") or [])
            unknown = set(item.get("not_known_by") or item.get("unknown_to") or [])
            overlap = sorted(known & unknown)
            if overlap:
                conflicts.append(
                    {
                        "conflict_type": "knowledge_audience_conflict",
                        "domain": "knowledge",
                        "subject": str(item.get("entry_id") or item.get("_id")),
                        "field": "known_by",
                        "severity": "high",
                        "message": "The same character is marked as knowing and not knowing this fact",
                        "canon_ids": [],
                        "evidence": overlap,
                    }
                )

        timeline = await db.timeline_entries.find(
            {"project_id": pid, "certainty": {"$ne": "unknown"}}
        ).to_list(length=5000)
        by_order: Dict[Any, list[Dict[str, Any]]] = {}
        timeline_ids = {
            str(item.get("entry_id") or item.get("_id")) for item in timeline
        }
        for item in timeline:
            order = item.get("order")
            if order is not None:
                by_order.setdefault(order, []).append(item)
            missing = [
                str(dep)
                for dep in item.get("dependencies") or []
                if str(dep) not in timeline_ids
            ]
            if missing:
                conflicts.append(
                    {
                        "conflict_type": "timeline_dependency_conflict",
                        "domain": "timeline",
                        "subject": str(item.get("entry_id") or item.get("_id")),
                        "field": "dependencies",
                        "severity": "high",
                        "message": "Timeline entry depends on missing project entries",
                        "canon_ids": [],
                        "evidence": missing,
                    }
                )
        for order, items in by_order.items():
            if len(items) > 1:
                conflicts.append(
                    {
                        "conflict_type": "timeline_order_conflict",
                        "domain": "timeline",
                        "subject": str(order),
                        "field": "order",
                        "severity": "warning",
                        "message": "Multiple known timeline entries use the same order",
                        "canon_ids": [],
                        "evidence": [
                            str(item.get("entry_id") or item.get("_id"))
                            for item in items
                        ],
                    }
                )

        powers = await db.power_progressions.find(
            {"project_id": pid}
        ).to_list(length=5000)
        power_groups: Dict[tuple[str, str], list[Dict[str, Any]]] = {}
        for item in powers:
            power_groups.setdefault(
                (str(item.get("character")), str(item.get("arc_id"))), []
            ).append(item)
        for key, items in power_groups.items():
            endings = {
                _normalized(item.get("ending_power")) for item in items
            }
            if len(endings) > 1:
                conflicts.append(
                    {
                        "conflict_type": "power_progression_conflict",
                        "domain": "power",
                        "subject": key[0],
                        "field": f"ending_power:{key[1]}",
                        "severity": "high",
                        "message": "Character has contradictory ending power in one arc",
                        "canon_ids": [],
                        "evidence": [_serialize(item.get("ending_power")) for item in items],
                    }
                )
        return conflicts

    async def validate(self, db, project_id: str) -> Dict[str, Any]:
        pid, _ = await self._project(db, project_id)
        candidates = [
            *await self._typed_conflicts(db, pid),
            *await self._ledger_conflicts(db, pid),
        ]
        now = datetime.utcnow()
        seen = set()
        persisted = []
        for candidate in candidates:
            candidate.setdefault("original_source", {})
            candidate.setdefault("conflicting_sources", [])
            candidate.setdefault("affected_locations", [])
            candidate.setdefault("impact", "This conflict lowers Canon Health and Overall Story Health until resolved.")
            fingerprint = hashlib.sha256(
                _normalized(
                    {
                        key: candidate.get(key)
                        for key in ("conflict_type", "subject", "field", "evidence")
                    }
                ).encode("utf-8")
            ).hexdigest()
            seen.add(fingerprint)
            doc = {
                "project_id": pid,
                "conflict_id": str(uuid4()),
                **candidate,
                "fingerprint": fingerprint,
                "status": "open",
                "detected_at": now,
                "last_seen_at": now,
            }
            await db.canon_conflicts.update_one(
                {"project_id": pid, "fingerprint": fingerprint},
                {
                    "$set": {
                        **candidate,
                        "status": "open",
                        "last_seen_at": now,
                    },
                    "$setOnInsert": {
                        "conflict_id": doc["conflict_id"],
                        "project_id": pid,
                        "fingerprint": fingerprint,
                        "detected_at": now,
                    },
                },
                upsert=True,
            )
            persisted.append(
                await db.canon_conflicts.find_one(
                    {"project_id": pid, "fingerprint": fingerprint}
                )
            )
        stale_query: Dict[str, Any] = {"project_id": pid, "status": "open"}
        if seen:
            stale_query["fingerprint"] = {"$nin": list(seen)}
        await db.canon_conflicts.update_many(
            stale_query,
            {"$set": {"status": "resolved", "resolved_at": now}},
        )
        result = (
            "FAIL"
            if any(item.get("severity") == "high" for item in candidates)
            else ("WARNING" if candidates else "PASS")
        )
        await self._after_change(
            db,
            project_id,
            "canon_validated",
            {"result": result, "conflict_count": len(candidates)},
        )
        return {
            "result": result,
            "conflicts": _serialize(persisted),
            "validated_at": now.isoformat(),
        }

    async def review(self, db, project_id: str) -> Dict[str, Any]:
        pid, project = await self._project(db, project_id)
        assignments = {
            item.agent_name: item
            for item in await orchestration_engine.get_assignments(db)
        }
        assignment = assignments.get("CanonAgent")
        if assignment and not assignment.enabled:
            raise ValueError("CanonAgent is disabled")
        validation = await self.validate(db, project_id)
        records = await db.canon_registry.find(
            {"project_id": pid, "active": True}
        ).sort("updated_at", -1).to_list(length=2000)
        from app.api.workflow import build_persistent_state

        latest_cycle = await db.cycles.find_one(
            {"project_id": pid}, sort=[("cycle_number", -1)]
        )
        state = await build_persistent_state(
            db,
            project,
            project_id,
            str(latest_cycle["_id"]) if latest_cycle else None,
        )
        state["canon_governance_context"] = {
            "active_canon": _serialize(records),
            "validation": validation,
        }
        settings = await orchestration_engine.get_settings(db)
        plan = await orchestration_service_v2.create_explicit_plan(
            db,
            project_id=project_id,
            agent_name="CanonAgent",
            changed_entity="canon_registry:active",
            affected_domain="canon_validation",
            reason="Explicit canon review requires CanonAgent",
        )
        try:
            result = await narrative_studio_service.run(
                db,
                project_id=project_id,
                state=state,
                agent_names=["CanonAgent"],
                plan_id=str(plan["_id"]),
                max_agent_calls=1,
                max_cycle_cost_usd=float(settings.max_cycle_cost_usd),
            )
            outputs = [
                item
                for item in state.get("cycle_outputs") or []
                if item.get("agent_name") == "CanonAgent"
            ]
            if not outputs:
                raise ValueError("CanonAgent did not return structured output")
            await orchestration_service_v2.finalize_explicit_plan(
                db,
                plan_id=plan["_id"],
                agent_name="CanonAgent",
                status="completed",
                actual_cost_usd=float(result.get("actual_cost_usd") or 0),
            )
        except Exception as exc:
            await orchestration_service_v2.finalize_explicit_plan(
                db,
                plan_id=plan["_id"],
                agent_name="CanonAgent",
                status="failed",
                error=str(exc),
            )
            raise
        raw = outputs[-1]["structured_output"].get("canon_review") or {}
        now = datetime.utcnow()
        report = {
            "project_id": pid,
            "report_id": str(uuid4()),
            "manuscript_id": None,
            "version_id": None,
            "report_type": "canon_review",
            "result": str(raw.get("result") or validation["result"]).upper(),
            "findings": list(raw.get("findings") or []),
            "recommendations": list(raw.get("recommendations") or []),
            "evidence": list(raw.get("evidence") or []),
            "generated_by": "CanonAgent",
            "orchestration_plan_id": str(plan["_id"]),
            "created_at": now,
        }
        inserted = await db.manuscript_reports.insert_one(report)
        report["_id"] = inserted.inserted_id
        await self._after_change(
            db,
            project_id,
            "canon_reviewed",
            {"report_id": report["report_id"]},
        )
        return _serialize(report)

    async def set_conflict_status(
        self, db, project_id: str, conflict_id: str, status: str
    ) -> Dict[str, Any]:
        pid, _ = await self._project(db, project_id)
        status = status.lower()
        if status not in {"open", "acknowledged", "resolved"}:
            raise ValueError("Unsupported conflict status")
        conflict = await db.canon_conflicts.find_one(
            {"project_id": pid, "conflict_id": conflict_id}
        )
        if not conflict:
            raise ValueError("Canon conflict not found")
        now = datetime.utcnow()
        patch: Dict[str, Any] = {"status": status, "updated_at": now}
        if status == "resolved":
            patch["resolved_at"] = now
        await db.canon_conflicts.update_one(
            {"_id": conflict["_id"]}, {"$set": patch}
        )
        return _serialize(
            await db.canon_conflicts.find_one({"_id": conflict["_id"]})
        )

    async def set_record_active(
        self,
        db,
        project_id: str,
        canon_id: str,
        active: bool,
    ) -> Dict[str, Any]:
        pid, _ = await self._project(db, project_id)
        legacy_id = canon_id.removeprefix("legacy:")
        record = await db.canon_registry.find_one({
            "project_id": pid,
            "$or": [
                {"canon_id": canon_id},
                {"_id": ObjectId(legacy_id)} if ObjectId.is_valid(legacy_id) else {"_id": None},
            ],
        })
        if not record:
            raise ValueError("Canon record not found")
        now = datetime.utcnow()
        await db.canon_registry.update_one(
            {"_id": record["_id"]},
            {"$set": {"active": bool(active), "updated_at": now}},
        )
        await self.validate(db, project_id)
        await self._after_change(
            db,
            project_id,
            "canon_record_changed",
            {"canon_id": canon_id, "active": bool(active)},
        )
        return _serialize(
            await db.canon_registry.find_one({"_id": record["_id"]})
        )

    async def dashboard(self, db, project_id: str) -> Dict[str, Any]:
        pid, _ = await self._project(db, project_id)
        return {
            "registry": _serialize(
                await db.canon_registry.find({"project_id": pid}).sort(
                    "updated_at", -1
                ).to_list(length=10000)
            ),
            "conflicts": _serialize(
                await db.canon_conflicts.find({"project_id": pid}).sort(
                    "last_seen_at", -1
                ).to_list(length=5000)
            ),
            "reports": _serialize(
                await db.manuscript_reports.find(
                    {"project_id": pid, "report_type": "canon_review"}
                ).sort("created_at", -1).to_list(length=1000)
            ),
        }

    async def explorer(
        self,
        db,
        project_id: str,
        *,
        search: str = "",
        canon_type: str = "",
        active: bool | None = None,
        limit: int = 1000,
    ) -> Dict[str, Any]:
        """Authoritative, searchable view over typed and legacy official canon."""
        pid, _ = await self._project(db, project_id)
        query: Dict[str, Any] = {"project_id": pid}
        if canon_type:
            query["canon_type"] = canon_type.strip().lower()
        if active is not None:
            query["active"] = active
        if search.strip():
            pattern = re.escape(search.strip())
            query["$or"] = [
                {"subject": {"$regex": pattern, "$options": "i"}},
                {"field": {"$regex": pattern, "$options": "i"}},
                {"fact": {"$regex": pattern, "$options": "i"}},
            ]
        records = await db.canon_registry.find(query).sort("updated_at", -1).to_list(length=max(1, min(limit, 10000)))
        conflicts = await db.canon_conflicts.find({"project_id": pid}).sort("last_seen_at", -1).to_list(length=5000)
        proposals = await db.canon_proposals.find({"project_id": pid}).sort("created_at", -1).to_list(length=5000)
        grouped: Dict[str, list[Dict[str, Any]]] = {}
        for record in records:
            record.setdefault("canon_id", f"legacy:{record['_id']}")
            record.setdefault("canon_type", "legacy")
            record.setdefault("active", str(record.get("status") or "LOCKED").upper() == "LOCKED")
            record.setdefault("authority_level", "author_approved" if record.get("source") in {"user_message", "question_answer"} else "legacy")
            grouped.setdefault(str(record.get("canon_type") or "legacy"), []).append(record)
        return _serialize({
            "records": records,
            "groups": grouped,
            "conflicts": conflicts,
            "proposals": proposals,
            "filters": {"search": search, "canon_type": canon_type, "active": active},
            "total": len(records),
            "authority": "canon_registry",
        })

    async def record_detail(self, db, project_id: str, canon_id: str) -> Dict[str, Any]:
        pid, _ = await self._project(db, project_id)
        legacy_id = canon_id.removeprefix("legacy:")
        record = await db.canon_registry.find_one({
            "project_id": pid,
            "$or": [{"canon_id": canon_id}, {"_id": ObjectId(legacy_id) if ObjectId.is_valid(legacy_id) else None}],
        })
        if not record:
            raise ValueError("Canon record not found")
        source_id = str(record.get("source_id") or "")
        proposals = await db.canon_proposals.find({
            "project_id": pid,
            "$or": [{"approved_canon_id": record.get("canon_id")}, {"source_id": source_id}],
        }).sort("created_at", 1).to_list(length=1000)
        conflicts = await db.canon_conflicts.find({
            "project_id": pid, "canon_ids": record.get("canon_id"),
        }).sort("last_seen_at", -1).to_list(length=1000)
        nodes = await db.narrative_nodes.find({
            "project_id": pid,
            "$or": [{"label": record.get("subject")}, {"source_id": source_id}],
        }).to_list(length=100)
        node_ids = [item.get("node_id") for item in nodes if item.get("node_id")]
        edges = await db.narrative_edges.find({
            "project_id": pid, "$or": [{"from_node_id": {"$in": node_ids}}, {"to_node_id": {"$in": node_ids}}],
        }).to_list(length=500) if node_ids else []
        versions = await db.canon_registry.find({
            "project_id": pid,
            "canon_type": record.get("canon_type"),
            "subject": record.get("subject"),
            "field": record.get("field"),
        }).sort([("source_version", 1), ("created_at", 1)]).to_list(length=1000)
        return _serialize({
            "record": record,
            "source": {"collection": record.get("source_collection") or record.get("source"), "source_id": source_id},
            "confidence": record.get("confidence", 1.0 if record.get("authority_level") == "approved" else .9),
            "evidence": record.get("evidence") or [record.get("fact")],
            "approval_history": proposals,
            "conflicts": conflicts,
            "relationships": edges,
            "versions": versions,
            "originating_chapter": record.get("originating_chapter") or record.get("chapter_number"),
        })

    async def compare(self, db, project_id: str, left_id: str, right_id: str) -> Dict[str, Any]:
        left = await self.record_detail(db, project_id, left_id)
        right = await self.record_detail(db, project_id, right_id)
        left_record, right_record = left["record"], right["record"]
        return {
            "left": left_record,
            "right": right_record,
            "changes": {
                key: {"from": left_record.get(key), "to": right_record.get(key)}
                for key in ("value", "fact", "authority_level", "active", "source_version", "evidence")
                if left_record.get(key) != right_record.get(key)
            },
        }

    async def propose_edit(self, db, project_id: str, canon_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        detail = await self.record_detail(db, project_id, canon_id)
        record = detail["record"]
        proposed_value = payload.get("value")
        if proposed_value is None:
            raise ValueError("Proposed canon value is required")
        from app.services.change_impact_service import change_impact_service
        from app.services.narrative_interaction_service import narrative_interaction_service
        impact = await change_impact_service.analyze(
            db, project_id, change_type="canon_change",
            target={"canon_id": record.get("canon_id"), "subject": record.get("subject"), "field": record.get("field")},
            proposed_change={"from": record.get("value"), "to": proposed_value},
        )
        proposal = await narrative_interaction_service.create_canon_proposal(db, project_id, {
            "canon_type": record.get("canon_type") if record.get("canon_type") in CANON_TYPES else "world",
            "subject": record.get("subject") or "Canon",
            "field": record.get("field") or "fact",
            "value": proposed_value,
            "confidence": float(payload.get("confidence") or .99),
            "evidence": list(payload.get("evidence") or [f"Governed edit of {record.get('canon_id') or canon_id}"]),
        }, source_type="canon_explorer_edit", source_id=str(record.get("canon_id") or record.get("id") or canon_id))
        return {"proposal": proposal, "impact_preview": impact, "applied": False, "requires_author_approval": True}


canon_governance_service = CanonGovernanceService()
