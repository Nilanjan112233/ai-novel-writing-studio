"""Controlled versioned drafting built on authoritative planning artifacts."""
from __future__ import annotations

import asyncio
import logging
from difflib import SequenceMatcher
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.services.draft_validation_service import draft_validation_service
from app.services.narrative_studio import narrative_studio_service
from app.services.orchestration_engine import orchestration_engine
from app.services.orchestration_service_v2 import orchestration_service_v2
from app.services.project_intelligence_coordinator import project_intelligence_coordinator
from app.services.chapter_intelligence_service import chapter_intelligence_service
from app.services.discovery_writing_service import discovery_writing_service
from app.services.execution_trace_service import execution_trace_service
from app.services.memory_provider import memory_provider_service
from app.models.scene_paragraph import ParagraphSkeleton, ParagraphVersion, ParagraphSuggestion

logger = logging.getLogger(__name__)


DRAFT_STATUSES = {"draft", "review", "approved", "rejected", "archived"}
SCENE_OPERATIONS = {
    "generate",
    "rewrite",
    "expand",
    "condense",
    "dialogue",
    "pacing",
    "emotion",
    "tension",
    "description",
    "action",
    "humor",
    "mystery",
    "horror",
    "romance",
    "world_detail",
    "internal_thoughts",
    "transitions",
}
TRANSITIONS = {
    "draft": {"review", "rejected", "archived"},
    "review": {"approved", "rejected", "archived"},
    "approved": {"archived"},
    "rejected": {"archived"},
    "archived": set(),
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


def _claims(payload: Any) -> Dict[str, list]:
    source = payload if isinstance(payload, dict) else {}
    return {
        key: list(source.get(key) or [])
        for key in (
            "knowledge_entry_ids",
            "artifact_ids",
            "timeline_entry_ids",
            "foreshadow_ids",
            "characters",
            "power_changes",
            "dependency_ids",
        )
    }


def _version_label(version_number: int) -> str:
    """Return an author-friendly A, B, ... AA label without changing numeric lineage."""
    value = max(1, int(version_number))
    label = ""
    while value:
        value, remainder = divmod(value - 1, 26)
        label = chr(65 + remainder) + label
    return f"Version {label}"


class DraftingService:
    """Own scene/chapter draft state transitions.

    Request locks are deliberately scoped to this service process. The RC8 database
    request identity index remains the cross-process safety net; the lock prevents a
    second provider call for the normal single-process desktop deployment.
    """

    def __init__(self) -> None:
        self._request_locks: dict[tuple[str, str, str], asyncio.Lock] = {}
        self._request_locks_guard = asyncio.Lock()

    @staticmethod
    def _reconcile_scene_references(
        generated: Dict[str, Any],
        scene: Dict[str, Any],
        context: Dict[str, Any],
    ) -> tuple[Dict[str, list], Dict[str, Any]]:
        raw = _claims(generated.get("continuity_claims"))
        planned = {
            "knowledge_entry_ids": list(dict.fromkeys(scene.get("knowledge_changes") or [])),
            "artifact_ids": list(dict.fromkeys(scene.get("artifact_interactions") or [])),
            "timeline_entry_ids": list(dict.fromkeys(scene.get("timeline_impacts") or [])),
            "foreshadow_ids": list(dict.fromkeys(scene.get("foreshadow_links") or [])),
            "characters": list(dict.fromkeys(scene.get("character_focus") or [])),
        }
        allowed_power = list(
            dict.fromkeys(
                str(value)
                for item in context.get("power_progression") or []
                for field in ("new_abilities", "mastered_abilities")
                for value in item.get(field) or []
                if str(value).strip()
            )
        )
        power_by_name = {value.casefold(): value for value in allowed_power}
        reconciled_power = [
            power_by_name[str(value).casefold()]
            for value in raw.get("power_changes") or []
            if str(value).casefold() in power_by_name
        ]
        dependencies = context.get("dependencies") or []
        dependency_by_identity: dict[str, str] = {}
        for item in dependencies:
            dependency_id = str(item.get("dependency_id") or "")
            if not dependency_id:
                continue
            for value in (
                dependency_id,
                item.get("title"),
                item.get("description"),
                item.get("dependency_type"),
            ):
                if str(value or "").strip():
                    dependency_by_identity[str(value).strip().casefold()] = dependency_id
        reconciled_dependencies = list(
            dict.fromkeys(
                dependency_by_identity[str(value).strip().casefold()]
                for value in raw.get("dependency_ids") or []
                if str(value).strip().casefold() in dependency_by_identity
            )
        )
        claims = {
            **planned,
            "power_changes": reconciled_power,
            "dependency_ids": reconciled_dependencies,
        }
        collections = {
            "knowledge_entry_ids": (context.get("knowledge") or [], "entry_id", ("title", "content")),
            "artifact_ids": (context.get("artifacts") or [], "artifact_id", ("item", "name")),
            "timeline_entry_ids": (context.get("timeline") or [], "entry_id", ("title", "summary")),
            "foreshadow_ids": (context.get("foreshadowing") or [], "entry_id", ("seed", "payoff_target")),
        }
        labels: Dict[str, list[str]] = {}
        for claim_key, (rows, id_key, label_keys) in collections.items():
            by_id = {str(item.get(id_key)): item for item in rows}
            labels[claim_key] = []
            for value in claims[claim_key]:
                item = by_id.get(str(value)) or {}
                label = next(
                    (str(item.get(key)) for key in label_keys if str(item.get(key) or "").strip()),
                    "Planned story reference",
                )
                labels[claim_key].append(label)
        return claims, {
            "strategy": "server_authoritative_scene_plan",
            "story_labels": labels,
            "discarded_unresolved_provider_references": {
                key: [str(value) for value in raw.get(key) or [] if str(value) not in {str(item) for item in claims.get(key) or []}]
                for key in raw
            },
        }

    async def _scene_handoff_context(
        self,
        db,
        pid: ObjectId,
        scene: Dict[str, Any],
        chapter: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        """Return bounded adjacent-scene evidence from existing approved drafts."""
        if not chapter:
            return {
                "chapter_scene_plans": [],
                "previous_approved_scene": None,
                "next_scene_plan": None,
            }
        chapter_scenes = await db.scene_plans.find(
            {
                "project_id": pid,
                "chapter_plan_id": chapter.get("chapter_plan_id"),
            }
        ).sort("order", 1).to_list(length=500)
        current_order = int(scene.get("order") or 0)
        previous_plan = next(
            (
                item
                for item in reversed(chapter_scenes)
                if int(item.get("order") or 0) < current_order
            ),
            None,
        )
        next_plan = next(
            (
                item
                for item in chapter_scenes
                if int(item.get("order") or 0) > current_order
            ),
            None,
        )

        if not previous_plan:
            previous_chapter = await db.chapter_plans.find_one(
                {
                    "project_id": pid,
                    "arc_id": scene.get("arc_id"),
                    "chapter_number": {"$lt": int(chapter.get("chapter_number") or 0)},
                },
                sort=[("chapter_number", -1)],
            )
            if previous_chapter:
                previous_plan = await db.scene_plans.find_one(
                    {
                        "project_id": pid,
                        "chapter_plan_id": previous_chapter.get("chapter_plan_id"),
                    },
                    sort=[("order", -1)],
                )
        if not next_plan:
            next_chapter = await db.chapter_plans.find_one(
                {
                    "project_id": pid,
                    "arc_id": scene.get("arc_id"),
                    "chapter_number": {"$gt": int(chapter.get("chapter_number") or 0)},
                },
                sort=[("chapter_number", 1)],
            )
            if next_chapter:
                next_plan = await db.scene_plans.find_one(
                    {
                        "project_id": pid,
                        "chapter_plan_id": next_chapter.get("chapter_plan_id"),
                    },
                    sort=[("order", 1)],
                )

        previous_draft = None
        if previous_plan:
            previous_draft = await db.scene_drafts.find_one(
                {
                    "project_id": pid,
                    "scene_id": previous_plan.get("scene_id"),
                    "status": "approved",
                },
                sort=[("version_number", -1), ("created_at", -1)],
            )
        previous_text = str((previous_draft or {}).get("generated_text") or "")
        return {
            "chapter_scene_plans": [
                {
                    key: item.get(key)
                    for key in (
                        "scene_id",
                        "title",
                        "purpose",
                        "conflict",
                        "outcome",
                        "character_change",
                        "order",
                    )
                }
                for item in chapter_scenes
            ],
            "previous_approved_scene": {
                "scene_id": previous_plan.get("scene_id"),
                "title": previous_plan.get("title"),
                "planned_outcome": previous_plan.get("outcome"),
                "ending_excerpt": previous_text[-2400:],
                "continuity_claims": (previous_draft or {}).get("continuity_claims") or {},
            } if previous_plan and previous_draft else None,
            "next_scene_plan": {
                key: next_plan.get(key)
                for key in (
                    "scene_id",
                    "title",
                    "purpose",
                    "conflict",
                    "outcome",
                    "character_change",
                    "order",
                )
            } if next_plan else None,
        }

    async def _execute(
        self,
        db,
        *,
        project_id: str,
        agent_name: str,
        state_patch: Dict[str, Any],
        changed_entity: str,
        affected_domain: str,
        selection_reason: str,
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        assignments = {
            item.agent_name: item
            for item in await orchestration_engine.get_assignments(db)
        }
        assignment = assignments.get(agent_name)
        if assignment and not assignment.enabled:
            raise ValueError(f"{agent_name} is disabled")
        project = await db.projects.find_one({"_id": ObjectId(project_id)})
        if not project:
            raise ValueError("Project not found")
        from app.api.workflow import build_persistent_state

        latest_cycle = await db.cycles.find_one(
            {"project_id": project["_id"]}, sort=[("cycle_number", -1)]
        )
        state = await build_persistent_state(
            db,
            project,
            project_id,
            str(latest_cycle["_id"]) if latest_cycle else None,
        )
        state.update(state_patch)
        settings = await orchestration_engine.get_settings(db)
        plan = await orchestration_service_v2.create_explicit_plan(
            db,
            project_id=project_id,
            agent_name=agent_name,
            changed_entity=changed_entity,
            affected_domain=affected_domain,
            reason=selection_reason,
        )
        try:
            result = await narrative_studio_service.run(
                db,
                project_id=project_id,
                state=state,
                agent_names=[agent_name],
                plan_id=str(plan["_id"]),
                max_agent_calls=1,
                max_cycle_cost_usd=float(settings.max_cycle_cost_usd),
            )
            outputs = [
                item
                for item in state.get("cycle_outputs") or []
                if item.get("agent_name") == agent_name
            ]
            if not outputs:
                raise ValueError(f"{agent_name} did not return structured output")
            await orchestration_service_v2.finalize_explicit_plan(
                db,
                plan_id=plan["_id"],
                agent_name=agent_name,
                status="completed",
                actual_cost_usd=float(result.get("actual_cost_usd") or 0),
            )
        except Exception as exc:
            await orchestration_service_v2.finalize_explicit_plan(
                db,
                plan_id=plan["_id"],
                agent_name=agent_name,
                status="failed",
                error=str(exc),
            )
            raise
        trace = await db.execution_traces.find_one(
            {"project_id": ObjectId(project_id), "agent_name": agent_name},
            sort=[("created_at", -1)],
        )
        agent_metadata = outputs[-1].get("generation_metadata") or {}
        metadata = {
            "provider": agent_metadata.get("provider") or (trace or {}).get("provider"),
            "model": agent_metadata.get("model") or (trace or {}).get("model"),
            "tokens_used": agent_metadata.get("tokens") or (trace or {}).get("total_tokens"),
            "latency_ms": agent_metadata.get("latency") or (trace or {}).get("latency_ms"),
            "cost_usd": agent_metadata.get("cost") or (trace or {}).get("cost_usd"),
            "execution_trace_id": (
                agent_metadata.get("execution_trace_id")
                or str((trace or {}).get("_id") or "")
            ),
            "execution_trace_ids": agent_metadata.get("execution_trace_ids") or [],
            "corrective_retry_count": int(
                agent_metadata.get("corrective_retry_count") or 0
            ),
            "rate_limit_per_minute": ((trace or {}).get("metadata") or {}).get(
                "rate_limit_per_minute"
            ),
            "actual_cost_usd": result.get("actual_cost_usd"),
            "orchestration_plan_id": str(plan["_id"]),
        }
        return outputs[-1]["structured_output"], metadata

    async def _after_change(
        self,
        db,
        *,
        project_id: str,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        await project_intelligence_coordinator.after_change(
            db, project_id, event_type, payload,
        )

    async def generate_scene(
        self,
        db,
        project_id: str,
        scene_id: str,
        *,
        parent_version_id: str | None = None,
        change_reason: str = "",
        operation: str = "generate",
        request_id: str | None = None,
        allow_exploratory: bool = False,
        activate: bool = True,
        writer_room_id: str | None = None,
        writer_room_source_id: str | None = None,
    ) -> Dict[str, Any]:
        normalized_request_id = str(request_id or "").strip() or None
        if not normalized_request_id:
            return await self._generate_scene(
                db,
                project_id,
                scene_id,
                parent_version_id=parent_version_id,
                change_reason=change_reason,
                operation=operation,
                request_id=None,
                allow_exploratory=allow_exploratory,
                activate=activate,
                writer_room_id=writer_room_id,
                writer_room_source_id=writer_room_source_id,
            )
        key = (project_id, scene_id, normalized_request_id)
        async with self._request_locks_guard:
            lock = self._request_locks.setdefault(key, asyncio.Lock())
        try:
            async with lock:
                return await self._generate_scene(
                    db,
                    project_id,
                    scene_id,
                    parent_version_id=parent_version_id,
                    change_reason=change_reason,
                    operation=operation,
                    request_id=normalized_request_id,
                    allow_exploratory=allow_exploratory,
                    activate=activate,
                    writer_room_id=writer_room_id,
                    writer_room_source_id=writer_room_source_id,
                )
        finally:
            async with self._request_locks_guard:
                if not lock.locked():
                    self._request_locks.pop(key, None)

    async def _generate_scene(
        self,
        db,
        project_id: str,
        scene_id: str,
        *,
        parent_version_id: str | None = None,
        change_reason: str = "",
        operation: str = "generate",
        request_id: str | None = None,
        allow_exploratory: bool = False,
        activate: bool = True,
        writer_room_id: str | None = None,
        writer_room_source_id: str | None = None,
    ) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        normalized_operation = str(operation or "generate").strip().lower()
        if normalized_operation not in SCENE_OPERATIONS:
            raise ValueError(f"Unsupported writing operation: {normalized_operation}")
        normalized_request_id = str(request_id or "").strip() or None
        if normalized_request_id:
            existing = await db.scene_drafts.find_one(
                {
                    "project_id": pid,
                    "scene_id": scene_id,
                    "request_id": normalized_request_id,
                }
            )
            if existing:
                report = None
                if existing.get("continuity_report_id"):
                    report = await db.continuity_reports.find_one(
                        {
                            "project_id": pid,
                            "report_id": existing["continuity_report_id"],
                        }
                    )
                return {
                    "draft": _serialize(existing),
                    "continuity_report": _serialize(report or {}),
                    "deduplicated": True,
                }
        preflight = await draft_validation_service.preflight_scene(
            db, project_id, scene_id
        )
        exploratory = bool(preflight["result"] == "FAIL" and allow_exploratory)
        if preflight["result"] == "FAIL" and not exploratory:
            raise ValueError({"message": "Scene is not eligible", "report": preflight})
        scene = await db.scene_plans.find_one(
            {"project_id": pid, "scene_id": scene_id}
        )
        chapter = await db.chapter_plans.find_one(
            {
                "project_id": pid,
                "chapter_plan_id": scene["chapter_plan_id"],
            }
        )
        arc = await db.story_arcs.find_one(
            {"project_id": pid, "arc_id": scene["arc_id"]}
        )
        handoff = await self._scene_handoff_context(db, pid, scene, chapter)
        context = {
            "scene_plan": scene,
            "chapter_plan": chapter,
            "arc": arc,
            **handoff,
            "knowledge": await db.knowledge_entries.find(
                {"project_id": pid, "entry_id": {"$in": scene.get("knowledge_changes") or []}}
            ).to_list(length=500),
            "artifacts": await db.artifact_registry.find(
                {"project_id": pid, "artifact_id": {"$in": scene.get("artifact_interactions") or []}}
            ).to_list(length=500),
            "timeline": await db.timeline_entries.find(
                {"project_id": pid, "entry_id": {"$in": scene.get("timeline_impacts") or []}}
            ).to_list(length=500),
            "foreshadowing": await db.foreshadow_registry_v2.find(
                {"project_id": pid, "entry_id": {"$in": scene.get("foreshadow_links") or []}}
            ).to_list(length=500),
            "character_progression": await db.character_progressions.find(
                {"project_id": pid, "arc_id": scene["arc_id"]}
            ).to_list(length=500),
            "power_progression": await db.power_progressions.find(
                {"project_id": pid, "arc_id": scene["arc_id"]}
            ).to_list(length=500),
            "dependencies": await db.arc_dependencies.find(
                {"project_id": pid, "arc_id": scene["arc_id"]}
            ).to_list(length=500),
            "change_reason": change_reason,
            "writing_operation": normalized_operation,
            "writing_instruction": (
                change_reason
                or "Create the first complete draft from the approved scene plan."
            ),
        }
        payload, metadata = await self._execute(
            db,
            project_id=project_id,
            agent_name="SceneWriterAgent",
            state_patch={
                "target_arc_id": scene["arc_id"],
                "target_scene_id": scene_id,
                "target_chapter_plan_id": scene["chapter_plan_id"],
                "drafting_context": context,
                "exploratory_draft": exploratory,
            },
            changed_entity=f"scene_plan:{scene_id}",
            affected_domain="scene_draft",
            selection_reason=(
                "Explicit exploratory scene request requires SceneWriterAgent"
                if exploratory
                else "Explicit generation request for an approved scene plan requires SceneWriterAgent"
            ),
        )
        generated = payload.get("scene_draft") or {}
        continuity_claims, reference_reconciliation = self._reconcile_scene_references(
            generated, scene, context
        )
        paragraphs_data = generated.get("paragraphs") or []
        text = str(generated.get("generated_text") or "").strip()
        if not text:
            raise ValueError("SceneWriterAgent returned no reader-facing scene prose")

        latest = await db.scene_drafts.find_one(
            {"project_id": pid, "scene_id": scene_id},
            sort=[("version_number", -1)],
        )
        if parent_version_id:
            parent = await db.scene_drafts.find_one(
                {"project_id": pid, "draft_id": parent_version_id, "scene_id": scene_id}
            )
            if not parent:
                raise ValueError("Parent scene draft version not found")
        else:
            parent = latest
        now = datetime.utcnow()
        if activate:
            await db.scene_drafts.update_many(
                {"project_id": pid, "scene_id": scene_id, "active": True},
                {"$set": {"active": False, "updated_at": now}},
            )

        # Paragraph Editor content is authoritative and frozen. Seed its planning
        # skeletons once, then preserve them across whole-scene alternatives.
        existing_paragraphs = await db.scene_paragraphs.find(
            {"project_id": pid, "scene_id": scene_id}
        ).sort("order", 1).to_list(length=1000)
        paragraphs_docs = []
        if not existing_paragraphs:
            for p in paragraphs_data:
                p_id = str(uuid4())
                pipeline = {
                    stage: {
                        "status": "planned" if stage != "planning" else "completed",
                        "updated_at": now,
                        "provider": metadata.get("provider"),
                        "model": metadata.get("model"),
                        "token_usage": metadata.get("tokens_used") or 0,
                        "estimated_cost": metadata.get("cost_usd") or 0.0,
                        "retry_count": metadata.get("corrective_retry_count") or 0,
                        "notes": []
                    }
                    for stage in [
                        "planning", "expansion", "dialogue", "emotion", "style",
                        "continuity", "canon", "editorial", "approval"
                    ]
                }
                val_domains = {
                    dom: {
                        "valid": True,
                        "errors": [],
                        "warnings": [],
                        "validated_at": now
                    }
                    for dom in [
                        "canon", "timeline", "continuity", "characters",
                        "pacing", "dialogue", "world_consistency"
                    ]
                }
                p_doc = {
                    "project_id": pid,
                    "scene_id": scene_id,
                    "paragraph_id": p_id,
                    "order": int(p.get("order") or 1),
                    "purpose": str(p.get("purpose") or ""),
                    "narrative_goal": str(p.get("narrative_goal") or ""),
                    "scene_goal": str(p.get("scene_goal") or ""),
                    "emotion": str(p.get("emotion") or ""),
                    "tension_level": str(p.get("tension_level") or ""),
                    "pov": str(p.get("pov") or ""),
                    "location": str(p.get("location") or ""),
                    "dialogue_goal": str(p.get("dialogue_goal") or ""),
                    "exposition_goal": str(p.get("exposition_goal") or ""),
                    "target_word_count": int(p.get("target_word_count") or 250),
                    "is_locked": False,
                    "approval_state": "pending",
                    "version": 1,
                    "regeneration_count": 0,
                    "dependencies": {
                        "canon_facts": list(p.get("required_canon") or []),
                        "characters": list(p.get("participating_characters") or []),
                        "locations": [p.get("location")] if p.get("location") else [],
                        "relationships": [],
                        "mysteries": [],
                        "callbacks": list(p.get("callbacks") or [])
                    },
                    "processing_pipeline": pipeline,
                    "validation_domains": val_domains,
                    "comments": [],
                    "revision_notes": [],
                    "created_at": now,
                    "updated_at": now
                }
                await db.scene_paragraphs.insert_one(p_doc)
                paragraphs_docs.append(_serialize(p_doc))

        # Re-run proper validation against all paragraphs in context
        all_paragraphs = await db.scene_paragraphs.find({"project_id": pid, "scene_id": scene_id}).to_list(length=1000)
        for doc_item in all_paragraphs:
            validated_domains = await self.validate_paragraph_skeleton(db, project_id, doc_item, all_paragraphs)
            await db.scene_paragraphs.update_one(
                {"_id": doc_item["_id"]},
                {"$set": {"validation_domains": validated_domains}}
            )

        # Refetch fresh validated list
        validated_paragraphs = await db.scene_paragraphs.find({"project_id": pid, "scene_id": scene_id}).sort("order", 1).to_list(length=1000)
        paragraphs_docs = [_serialize(doc) for doc in validated_paragraphs]

        doc = {
            "project_id": pid,
            "draft_id": str(uuid4()),
            "arc_id": scene["arc_id"],
            "chapter_plan_id": scene["chapter_plan_id"],
            "scene_id": scene_id,
            "version_number": int((latest or {}).get("version_number") or 0) + 1,
            "version_label": _version_label(
                int((latest or {}).get("version_number") or 0) + 1
            ),
            "parent_version_id": str((parent or {}).get("draft_id") or "") or None,
            "status": "draft",
            "active": bool(activate),
            "exploratory": exploratory,
            "planning_gate_result": preflight["result"],
            "planning_gate_blockers": [
                value
                for key, values in preflight.items()
                if key.endswith("_violations") and isinstance(values, list)
                for value in values
            ],
            "generated_text": text,
            "paragraphs": paragraphs_docs,
            "paragraph_blueprint": paragraphs_data,
            "continuity_claims": continuity_claims,
            "reference_reconciliation": reference_reconciliation,
            "generation_notes": list(generated.get("generation_notes") or []),
            "operation": normalized_operation,
            "why": str(
                generated.get("why")
                or payload.get("reasoning")
                or "This approach follows the approved scene goal and current story context."
            ),
            "expected_impact": str(
                generated.get("expected_impact")
                or payload.get("recommendation")
                or "Advance the planned conflict while preserving story continuity."
            ),
            "affected_narrative_areas": list(
                generated.get("affected_narrative_areas") or ["continuity"]
            ),
            "estimated_change_scope": str(
                generated.get("estimated_change_scope") or "medium"
            ),
            "preserved_elements": list(
                generated.get("preserved_elements")
                or ["Approved scene plan", "Canon", "Timeline"]
            ),
            "context_evidence": list(generated.get("context_evidence") or []),
            "connection_from_previous": str(
                generated.get("connection_from_previous")
                or (
                    f"Continues after {handoff['previous_approved_scene']['title']}: "
                    f"{handoff['previous_approved_scene']['planned_outcome']}"
                    if handoff.get("previous_approved_scene")
                    else "This is the first approved scene beat in the current sequence."
                )
            ),
            "handoff_to_next": str(
                generated.get("handoff_to_next")
                or (
                    f"Leaves pressure for {handoff['next_scene_plan']['title']}."
                    if handoff.get("next_scene_plan")
                    else "Closes the current planned sequence without drafting future events."
                )
            ),
            "scene_goal": str(generated.get("scene_goal") or scene.get("purpose") or ""),
            "scene_trouble": str(
                generated.get("scene_trouble") or scene.get("conflict") or ""
            ),
            "scene_stakes": str(
                generated.get("scene_stakes") or (arc or {}).get("stakes") or ""
            ),
            "distinct_progression": str(
                generated.get("distinct_progression")
                or (
                    (context.get("timeline") or [{}])[0].get("summary")
                    or (context.get("timeline") or [{}])[0].get("title")
                    if context.get("timeline")
                    else scene.get("outcome") or ""
                )
            ),
            "favorite": False,
            "request_id": normalized_request_id,
            "writer_room_id": writer_room_id,
            "writer_room_source_id": writer_room_source_id,
            "generation_metadata": metadata,
            "generated_by": "SceneWriterAgent",
            "change_reason": change_reason,
            "created_at": now,
            "updated_at": now,
        }
        try:
            inserted = await db.scene_drafts.insert_one(doc)
        except DuplicateKeyError:
            # A concurrent process may have won the unique request identity race.
            # Reuse that logical result; never turn an idempotent retry into a 500.
            if normalized_request_id:
                existing = await db.scene_drafts.find_one(
                    {
                        "project_id": pid,
                        "scene_id": scene_id,
                        "request_id": normalized_request_id,
                    }
                )
                if existing:
                    for trace_id in metadata.get("execution_trace_ids") or [metadata.get("execution_trace_id")]:
                        await execution_trace_service.mark_application_outcome(
                            db,
                            trace_id,
                            provider_success=True,
                            parse_success=True,
                            validation_success=True,
                            reference_resolution_success=True,
                            persistence_success=True,
                            approval_eligible=str(existing.get("validation_result") or "").upper() == "PASS",
                            final_outcome="idempotent_result_reused",
                            request_id=normalized_request_id,
                        )
                    report = None
                    if existing.get("continuity_report_id"):
                        report = await db.continuity_reports.find_one(
                            {
                                "project_id": pid,
                                "report_id": existing["continuity_report_id"],
                            }
                        )
                    return {
                        "draft": _serialize(existing),
                        "continuity_report": _serialize(report or {}),
                        "deduplicated": True,
                    }
            raise
        doc["_id"] = inserted.inserted_id
        proposal_ids: list[str] = []
        for proposal in generated.get("canon_proposals") or []:
            if not isinstance(proposal, dict):
                continue
            try:
                from app.services.narrative_interaction_service import (
                    narrative_interaction_service,
                )

                created = await narrative_interaction_service.create_canon_proposal(
                    db,
                    project_id,
                    {
                        **proposal,
                        "affected_scenes": [scene_id],
                        "affected_chapters": [
                            int(chapter.get("chapter_number") or 0)
                        ] if chapter else [],
                    },
                    source_type="scene_draft",
                    source_id=doc["draft_id"],
                )
                proposal_ids.append(created["proposal_id"])
            except ValueError as exc:
                doc["generation_notes"].append(
                    f"A proposed story fact could not enter the Canon Queue: {exc}"
                )
        if proposal_ids:
            doc["canon_proposal_ids"] = proposal_ids
            await db.scene_drafts.update_one(
                {"_id": inserted.inserted_id},
                {
                    "$set": {
                        "canon_proposal_ids": proposal_ids,
                        "generation_notes": doc["generation_notes"],
                    }
                },
            )
        report = await draft_validation_service.validate_scene_draft(
            db, project_id, doc
        )
        await db.scene_drafts.update_one(
            {"_id": inserted.inserted_id},
            {
                "$set": {
                    "validation_result": report["result"],
                    "continuity_report_id": report["report_id"],
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        doc["validation_result"] = report["result"]
        doc["continuity_report_id"] = report["report_id"]
        application_outcome = {
            "provider_success": True,
            "parse_success": True,
            "validation_success": True,
            "reference_resolution_success": True,
            "persistence_success": True,
            "approval_eligible": report["result"] == "PASS" and not exploratory,
            "final_outcome": (
                "persisted_approval_eligible"
                if report["result"] == "PASS" and not exploratory
                else "persisted_author_review_required"
            ),
            "request_id": normalized_request_id,
        }
        doc["generation_metadata"]["application_outcome"] = application_outcome
        await db.scene_drafts.update_one(
            {"_id": inserted.inserted_id},
            {"$set": {"generation_metadata.application_outcome": application_outcome}},
        )
        for trace_id in metadata.get("execution_trace_ids") or [metadata.get("execution_trace_id")]:
            await execution_trace_service.mark_application_outcome(
                db,
                trace_id,
                **application_outcome,
            )
        await self._after_change(
            db,
            project_id=project_id,
            event_type="scene_draft_generated",
            payload={
                "draft_id": doc["draft_id"],
                "scene_id": scene_id,
                "chapter_plan_id": scene["chapter_plan_id"],
                "arc_id": scene["arc_id"],
                "version_number": doc["version_number"],
                "validation_result": report["result"],
            },
        )
        return {"draft": _serialize(doc), "continuity_report": _serialize(report)}

    async def generate_chapter(
        self,
        db,
        project_id: str,
        chapter_plan_id: str,
        *,
        parent_version_id: str | None = None,
        change_reason: str = "",
    ) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        chapter = await db.chapter_plans.find_one(
            {"project_id": pid, "chapter_plan_id": chapter_plan_id}
        )
        if not chapter:
            raise ValueError("Chapter plan not found")
        if str(chapter.get("status") or "").lower() != "approved":
            raise ValueError("Chapter plan is not approved")
        scenes = await db.scene_plans.find(
            {"project_id": pid, "chapter_plan_id": chapter_plan_id}
        ).sort("order", 1).to_list(length=1000)
        if not scenes:
            raise ValueError("Chapter has no scene plans")
        source_drafts = []
        for scene in scenes:
            preflight = await draft_validation_service.preflight_scene(
                db,
                project_id,
                scene["scene_id"],
                persist=False,
            )
            if preflight["result"] == "FAIL":
                raise ValueError(
                    {
                        "message": "Chapter is not eligible",
                        "scene_id": scene["scene_id"],
                        "report": preflight,
                    }
                )
            if str(scene.get("status") or "").lower() != "approved":
                raise ValueError(f"Scene plan {scene['scene_id']} is not approved")
            draft = await db.scene_drafts.find_one(
                {
                    "project_id": pid,
                    "scene_id": scene["scene_id"],
                    "active": True,
                    "status": "approved",
                }
            )
            if not draft:
                raise ValueError(
                    f"Scene {scene['scene_id']} has no active approved draft"
                )
            source_drafts.append(draft)
        payload, metadata = await self._execute(
            db,
            project_id=project_id,
            agent_name="ChapterAssemblerAgent",
            state_patch={
                "target_arc_id": chapter["arc_id"],
                "target_chapter_plan_id": chapter_plan_id,
                "drafting_context": {
                    "chapter_plan": {
                        key: chapter.get(key)
                        for key in (
                            "chapter_plan_id",
                            "arc_id",
                            "chapter_number",
                            "title",
                            "purpose",
                            "conflict",
                            "character_focus",
                            "status",
                        )
                    },
                    "scene_plans": [
                        {
                            key: scene.get(key)
                            for key in (
                                "scene_id",
                                "chapter_plan_id",
                                "title",
                                "purpose",
                                "conflict",
                                "outcome",
                                "order",
                                "status",
                            )
                        }
                        for scene in scenes
                    ],
                    "approved_scene_drafts": [
                        {
                            "draft_id": draft["draft_id"],
                            "scene_id": draft["scene_id"],
                            "version_number": draft["version_number"],
                            "generated_text": draft["generated_text"],
                        }
                        for draft in source_drafts
                    ],
                    "change_reason": change_reason,
                },
            },
            changed_entity=f"chapter_plan:{chapter_plan_id}",
            affected_domain="chapter_draft",
            selection_reason=(
                "Explicit assembly request with approved source scenes requires "
                "ChapterAssemblerAgent"
            ),
        )
        assembly = payload.get("chapter_assembly") or {}
        raw_transitions = [
            item for item in assembly.get("transitions") or []
            if isinstance(item, dict)
        ]
        source_ids = [item["draft_id"] for item in source_drafts]
        transitions = []
        by_pair: Dict[tuple[str, str], Dict[str, Any]] = {}
        unused = list(raw_transitions)
        for index, pair in enumerate(zip(source_ids, source_ids[1:])):
            matched = next(
                (
                    item
                    for item in unused
                    if str(item.get("from_scene_draft_id") or "") == pair[0]
                    and str(item.get("to_scene_draft_id") or "") == pair[1]
                ),
                None,
            )
            item = matched or (unused[0] if unused else {})
            if item in unused:
                unused.remove(item)
            transition = {
                "from_scene_draft_id": pair[0],
                "to_scene_draft_id": pair[1],
                "generated_text": str(item.get("generated_text") or "").strip(),
            }
            by_pair[pair] = transition
            transitions.append(transition)
        parts = []
        for index, source in enumerate(source_drafts):
            parts.append(str(source.get("generated_text") or "").strip())
            if index < len(source_drafts) - 1:
                pair = (source_ids[index], source_ids[index + 1])
                transition_text = (by_pair.get(pair) or {}).get("generated_text")
                if transition_text:
                    parts.append(transition_text)
        generated_text = "\n\n".join(part for part in parts if part)
        latest = await db.chapter_drafts.find_one(
            {"project_id": pid, "chapter_plan_id": chapter_plan_id},
            sort=[("version_number", -1)],
        )
        if parent_version_id:
            parent = await db.chapter_drafts.find_one(
                {
                    "project_id": pid,
                    "draft_id": parent_version_id,
                    "chapter_plan_id": chapter_plan_id,
                }
            )
            if not parent:
                raise ValueError("Parent chapter draft version not found")
        else:
            parent = latest
        now = datetime.utcnow()
        await db.chapter_drafts.update_many(
            {"project_id": pid, "chapter_plan_id": chapter_plan_id, "active": True},
            {"$set": {"active": False, "updated_at": now}},
        )
        claims = {
            key: list(dict.fromkeys(
                value
                for source in source_drafts
                for value in (source.get("continuity_claims") or {}).get(key) or []
            ))
            for key in (
                "knowledge_entry_ids",
                "artifact_ids",
                "timeline_entry_ids",
                "foreshadow_ids",
                "characters",
                "power_changes",
                "dependency_ids",
            )
        }
        doc = {
            "project_id": pid,
            "draft_id": str(uuid4()),
            "arc_id": chapter["arc_id"],
            "chapter_plan_id": chapter_plan_id,
            "version_number": int((latest or {}).get("version_number") or 0) + 1,
            "parent_version_id": str((parent or {}).get("draft_id") or "") or None,
            "status": "draft",
            "active": True,
            "source_scene_draft_ids": source_ids,
            "transitions": transitions,
            "reference_reconciliation": {
                "strategy": "server_authoritative_adjacent_scene_order",
                "resolved_transition_count": len(transitions),
                "ignored_extra_provider_transitions": len(unused),
            },
            "generated_text": generated_text,
            "continuity_claims": claims,
            "generation_notes": list(assembly.get("generation_notes") or []),
            "generation_metadata": metadata,
            "generated_by": "ChapterAssemblerAgent",
            "change_reason": change_reason,
            "created_at": now,
            "updated_at": now,
        }
        inserted = await db.chapter_drafts.insert_one(doc)
        doc["_id"] = inserted.inserted_id
        report = await draft_validation_service.validate_chapter_draft(
            db, project_id, doc
        )
        await db.chapter_drafts.update_one(
            {"_id": inserted.inserted_id},
            {
                "$set": {
                    "validation_result": report["result"],
                    "continuity_report_id": report["report_id"],
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        doc["validation_result"] = report["result"]
        doc["continuity_report_id"] = report["report_id"]
        await self._after_change(
            db,
            project_id=project_id,
            event_type="chapter_draft_generated",
            payload={
                "draft_id": doc["draft_id"],
                "chapter_plan_id": chapter_plan_id,
                "arc_id": chapter["arc_id"],
                "version_number": doc["version_number"],
                "validation_result": report["result"],
            },
        )
        return {"draft": _serialize(doc), "continuity_report": _serialize(report)}

    async def transition(
        self,
        db,
        project_id: str,
        draft_type: str,
        draft_id: str,
        status: str,
        *,
        reason: str = "",
    ) -> Dict[str, Any]:
        collection = "scene_drafts" if draft_type == "scene" else "chapter_drafts"
        pid = ObjectId(project_id)
        draft = await db[collection].find_one(
            {"project_id": pid, "draft_id": draft_id}
        )
        if not draft:
            raise ValueError("Draft not found")
        status = status.lower()
        if status not in DRAFT_STATUSES:
            raise ValueError("Unsupported draft status")
        current = str(draft.get("status") or "draft")
        if status not in TRANSITIONS.get(current, set()):
            raise ValueError(f"Invalid draft transition {current} -> {status}")
        if status == "rejected" and not reason.strip():
            raise ValueError("Rejection requires a reason")
        if status == "approved":
            if draft_type == "scene":
                report = await draft_validation_service.validate_scene_draft(
                    db, project_id, draft, stage="approval"
                )
            else:
                report = await draft_validation_service.validate_chapter_draft(
                    db, project_id, draft, stage="approval"
                )
            if report["result"] == "FAIL":
                raise ValueError({"message": "Draft validation failed", "report": report})
        else:
            report = None
        now = datetime.utcnow()
        patch: Dict[str, Any] = {
            "status": status,
            "review_reason": reason,
            "updated_at": now,
        }
        if status == "approved":
            patch["approved_at"] = now
            if draft_type == "chapter":
                patch["enrichment_status"] = "pending"
        elif status == "rejected":
            patch["rejected_at"] = now
        elif status == "archived":
            patch["archived_at"] = now
            patch["active"] = False
        await db[collection].update_one({"_id": draft["_id"]}, {"$set": patch})
        intelligence = None
        enrichment: Dict[str, Any] = {"status": "not_applicable"}
        if draft_type == "chapter" and status == "approved":
            await db[collection].update_one({"_id": draft["_id"]}, {"$set": {"enrichment_status": "running", "updated_at": datetime.utcnow()}})
            enrichment = {"status": "completed"}
            try:
                if draft.get("workflow_mode") == "discovery":
                    # Extraction is still candidate-only, but chapter intelligence
                    # should be built after it so the shared retrieval path can
                    # carry observable approved-prose facts into later chapters.
                    await discovery_writing_service.extract_approved(db, project_id, draft)
                intelligence = await chapter_intelligence_service.generate(
                    db,
                    project_id,
                    draft_id,
                )
            except Exception as exc:
                # Approval is the primary author boundary. Enrichment may fail
                # independently and must remain retryable without claiming that
                # the approved prose was lost.
                enrichment = {"status": "failed", "error": str(exc)[:500], "retryable": True}
                await db[collection].update_one({"_id": draft["_id"]}, {"$set": {"enrichment_status": "failed", "enrichment_error": str(exc)[:500], "updated_at": datetime.utcnow()}})
            else:
                await db[collection].update_one({"_id": draft["_id"]}, {"$set": {"enrichment_status": "completed", "enrichment_error": None, "updated_at": datetime.utcnow()}})
        event_type = (
            f"{draft_type}_draft_approved"
            if status == "approved"
            else f"{draft_type}_draft_changed"
        )
        await self._after_change(
            db,
            project_id=project_id,
            event_type=event_type,
            payload={
                "draft_id": draft_id,
                "status": status,
                "arc_id": draft.get("arc_id"),
                "chapter_plan_id": draft.get("chapter_plan_id"),
                "scene_id": draft.get("scene_id"),
            },
        )
        if draft_type == "chapter" and status == "approved":
            # Optional memory providers observe the same approved-prose event.
            # They cannot approve, rewrite, enrich, or otherwise mutate the
            # owning draft; the existing extraction/intelligence path remains
            # responsible for NovelForge state.
            try:
                await memory_provider_service.capture(
                    db,
                    project_id,
                    user_content=f"Approved Chapter {draft.get('chapter_number') or ''}".strip(),
                    assistant_content=str(draft.get("generated_text") or "")[:12000],
                    source_type="approved_chapter",
                    source_id=draft_id,
                )
            except Exception:
                logger.debug("Optional memory capture failed after chapter approval", exc_info=True)
        updated = await db[collection].find_one({"_id": draft["_id"]})
        return {
            "draft": _serialize(updated),
            "continuity_report": _serialize(report) if report else None,
            "chapter_intelligence": intelligence,
            "enrichment": enrichment,
        }

    async def set_scene_favorite(
        self,
        db,
        project_id: str,
        draft_id: str,
        favorite: bool,
    ) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        draft = await db.scene_drafts.find_one(
            {"project_id": pid, "draft_id": draft_id}
        )
        if not draft:
            raise ValueError("Scene draft not found")
        await db.scene_drafts.update_one(
            {"_id": draft["_id"]},
            {
                "$set": {
                    "favorite": bool(favorite),
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        return _serialize(await db.scene_drafts.find_one({"_id": draft["_id"]}))

    async def create_writers_room_options(
        self,
        db,
        project_id: str,
        draft_id: str,
        *,
        directions: list[str] | None = None,
        instruction: str = "",
        request_id: str | None = None,
    ) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        source = await db.scene_drafts.find_one(
            {"project_id": pid, "draft_id": draft_id}
        )
        if not source:
            raise ValueError("Scene draft not found")
        normalized = [
            str(item).strip().lower()
            for item in (directions or ["emotion", "action", "mystery"])[:3]
        ]
        if len(normalized) != 3 or len(set(normalized)) != 3:
            raise ValueError("Writer's Room requires three different directions")
        unsupported = [item for item in normalized if item not in SCENE_OPERATIONS]
        if unsupported:
            raise ValueError(f"Unsupported Writer's Room direction: {unsupported[0]}")
        room_id = str(request_id or "").strip() or str(uuid4())
        options = []
        try:
            for index, direction in enumerate(normalized, start=1):
                result = await self.generate_scene(
                    db,
                    project_id,
                    source["scene_id"],
                    parent_version_id=draft_id,
                    change_reason=(
                        f"Writer's Room direction: {direction}. {instruction}".strip()
                    ),
                    operation=direction,
                    request_id=f"{room_id}:{index}:{direction}",
                    allow_exploratory=bool(source.get("exploratory")),
                    activate=False,
                    writer_room_id=room_id,
                    writer_room_source_id=draft_id,
                )
                options.append(result["draft"])
        except Exception:
            # An incomplete exploratory room must not leave author-invisible
            # alternatives or proposals behind. Exact room/source identity makes
            # this cleanup bounded and never touches approved prose.
            option_ids = [str(item.get("draft_id")) for item in options if item.get("draft_id")]
            if option_ids:
                await db.canon_proposals.delete_many(
                    {
                        "project_id": pid,
                        "source_type": "scene_draft",
                        "source_id": {"$in": option_ids},
                        "status": "pending",
                    }
                )
            await db.scene_drafts.delete_many(
                {
                    "project_id": pid,
                    "scene_id": source["scene_id"],
                    "writer_room_id": room_id,
                    "writer_room_source_id": draft_id,
                    "active": False,
                    "status": {"$ne": "approved"},
                }
            )
            raise
        refreshed_source = await db.scene_drafts.find_one(
            {"project_id": pid, "draft_id": draft_id}
        )
        if not refreshed_source or any(
            refreshed_source.get(field) != source.get(field)
            for field in ("active", "status")
        ):
            raise ValueError(
                "Writer's Room stopped because the source draft changed concurrently. "
                "Your approved prose was not replaced; reload before choosing an alternative."
            )
        return {
            "room_id": room_id,
            "source_draft_id": draft_id,
            "options": options,
            "selected_draft_id": None,
            "author_choice_required": True,
            "message": (
                "Three protected alternatives are ready. Compare and favorite them; "
                "NovelForge will not choose for you."
            ),
        }

    async def compare_scene_versions(
        self,
        db,
        project_id: str,
        left_draft_id: str,
        right_draft_id: str,
    ) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        drafts = await db.scene_drafts.find(
            {
                "project_id": pid,
                "draft_id": {"$in": [left_draft_id, right_draft_id]},
            }
        ).to_list(length=2)
        by_id = {str(item.get("draft_id")): item for item in drafts}
        left = by_id.get(left_draft_id)
        right = by_id.get(right_draft_id)
        if not left or not right:
            raise ValueError("Both scene draft versions are required")
        if left.get("scene_id") != right.get("scene_id"):
            raise ValueError("Scene versions must belong to the same scene")
        left_text = str(left.get("generated_text") or "")
        right_text = str(right.get("generated_text") or "")
        matcher = SequenceMatcher(None, left_text, right_text)
        changes = []
        for tag, left_start, left_end, right_start, right_end in matcher.get_opcodes():
            if tag == "equal":
                continue
            changes.append(
                {
                    "kind": tag,
                    "before": left_text[left_start:left_end],
                    "after": right_text[right_start:right_end],
                }
            )
        left_words = len(left_text.split())
        right_words = len(right_text.split())
        right_label = right.get("version_label") or _version_label(
            int(right.get("version_number") or 1)
        )
        return {
            "scene_id": left["scene_id"],
            "left": {
                "draft_id": left_draft_id,
                "label": left.get("version_label")
                or _version_label(int(left.get("version_number") or 1)),
                "word_count": left_words,
                "text": left_text,
            },
            "right": {
                "draft_id": right_draft_id,
                "label": right_label,
                "word_count": right_words,
                "text": right_text,
            },
            "similarity_percent": round(matcher.ratio() * 100),
            "word_count_delta": right_words - left_words,
            "changes": changes[:200],
            "summary": (
                f"{right_label} is {abs(right_words - left_words)} words "
                f"{'longer' if right_words >= left_words else 'shorter'} and retains "
                f"{round(matcher.ratio() * 100)}% textual similarity."
            ),
        }

    async def merge_scene_versions(
        self,
        db,
        project_id: str,
        left_draft_id: str,
        right_draft_id: str,
        merged_text: str,
        *,
        reason: str = "",
    ) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        drafts = await db.scene_drafts.find(
            {
                "project_id": pid,
                "draft_id": {"$in": [left_draft_id, right_draft_id]},
            }
        ).to_list(length=2)
        by_id = {str(item.get("draft_id")): item for item in drafts}
        left = by_id.get(left_draft_id)
        right = by_id.get(right_draft_id)
        if not left or not right:
            raise ValueError("Both scene draft versions are required")
        if left.get("scene_id") != right.get("scene_id"):
            raise ValueError("Scene versions must belong to the same scene")
        text = str(merged_text or "").strip()
        if not text:
            raise ValueError("Merged scene text is required")
        latest = await db.scene_drafts.find_one(
            {"project_id": pid, "scene_id": left["scene_id"]},
            sort=[("version_number", -1)],
        )
        next_version = int((latest or {}).get("version_number") or 0) + 1
        now = datetime.utcnow()
        await db.scene_drafts.update_many(
            {"project_id": pid, "scene_id": left["scene_id"], "active": True},
            {"$set": {"active": False, "updated_at": now}},
        )
        merged = {
            key: value
            for key, value in right.items()
            if key not in {
                "_id",
                "draft_id",
                "version_number",
                "version_label",
                "parent_version_id",
                "status",
                "active",
                "generated_text",
                "validation_result",
                "continuity_report_id",
                "request_id",
                "writer_room_id",
                "writer_room_source_id",
                "created_at",
                "updated_at",
            }
        }
        merged.update(
            {
                "draft_id": str(uuid4()),
                "version_number": next_version,
                "version_label": _version_label(next_version),
                "parent_version_id": right_draft_id,
                "merged_from_draft_ids": [left_draft_id, right_draft_id],
                "status": "review",
                "active": True,
                "generated_text": text,
                "generated_by": "author_merge",
                "operation": "merge",
                "why": reason.strip()
                or "The author combined selected elements from two protected alternatives.",
                "expected_impact": "Keep the author's preferred parts of both versions.",
                "change_reason": reason.strip(),
                "favorite": False,
                "created_at": now,
                "updated_at": now,
            }
        )
        inserted = await db.scene_drafts.insert_one(merged)
        merged["_id"] = inserted.inserted_id
        report = await draft_validation_service.validate_scene_draft(
            db, project_id, merged, stage="author_merge"
        )
        await db.scene_drafts.update_one(
            {"_id": inserted.inserted_id},
            {
                "$set": {
                    "validation_result": report["result"],
                    "continuity_report_id": report["report_id"],
                }
            },
        )
        await self._after_change(
            db,
            project_id=project_id,
            event_type="scene_draft_merged",
            payload={
                "draft_id": merged["draft_id"],
                "scene_id": merged["scene_id"],
                "source_draft_ids": [left_draft_id, right_draft_id],
            },
        )
        merged["validation_result"] = report["result"]
        merged["continuity_report_id"] = report["report_id"]
        return {
            "draft": _serialize(merged),
            "continuity_report": _serialize(report),
        }

    async def edit_chapter_content(
        self,
        db,
        project_id: str,
        draft_id: str,
        edited_text: str,
        *,
        reason: str = "Author edited chapter prose",
    ) -> Dict[str, Any]:
        """Persist a direct author edit as a new chapter version.

        The source version remains in lineage and the new version is explicitly
        reviewable.  This is the chapter-level equivalent of the existing
        protected paragraph save path; it never edits an approved document in
        place and never silently re-approves prose.
        """
        pid = ObjectId(project_id)
        text = str(edited_text or "").strip()
        if not text:
            raise ValueError("Chapter prose cannot be empty")
        source = await db.chapter_drafts.find_one({"project_id": pid, "draft_id": draft_id})
        if not source:
            raise ValueError("Chapter draft not found")
        if source.get("status") == "archived":
            raise ValueError("Archived chapter versions cannot be edited")
        chapter_number = int(source.get("chapter_number") or 0)
        chapter_plan_id = source.get("chapter_plan_id")
        if not chapter_number and chapter_plan_id:
            chapter_plan = await db.chapter_plans.find_one({"project_id": pid, "chapter_plan_id": chapter_plan_id})
            chapter_number = int((chapter_plan or {}).get("chapter_number") or 0)
        identity_query = {"project_id": pid, "chapter_plan_id": chapter_plan_id} if chapter_plan_id else {"project_id": pid, "chapter_number": chapter_number}
        latest = await db.chapter_drafts.find_one(
            identity_query,
            sort=[("version_number", -1), ("updated_at", -1)],
        )
        now = datetime.utcnow()
        await db.chapter_drafts.update_many(
            {**identity_query, "active": True},
            {"$set": {"active": False, "updated_at": now}},
        )
        word_count = len(text.split())
        minimum = source.get("target_word_min")
        maximum = source.get("target_word_max")
        edited = {
            key: value
            for key, value in source.items()
            if key not in {
                "_id", "draft_id", "version_number", "parent_version_id", "status",
                "active", "generated_text", "word_count", "range_compliant",
                "validation_result", "continuity_report_id", "approved_at",
                "rejected_at", "enrichment_status", "enrichment_error",
                "created_at", "updated_at", "request_id",
            }
        }
        edited.update({
            "draft_id": str(uuid4()),
            "version_number": int((latest or {}).get("version_number") or 0) + 1,
            "parent_version_id": source.get("draft_id"),
            "status": "review",
            "active": True,
            "generated_text": text,
            "word_count": word_count,
            "range_compliant": (not minimum or word_count >= int(minimum)) and (not maximum or word_count <= int(maximum)),
            "generated_by": "author_editor",
            "operation": "manual_edit",
            "change_reason": str(reason or "Author edited chapter prose").strip(),
            "enrichment_status": "pending",
            "created_at": now,
            "updated_at": now,
        })
        inserted = await db.chapter_drafts.insert_one(edited)
        edited["_id"] = inserted.inserted_id
        report = await draft_validation_service.validate_chapter_draft(db, project_id, edited, stage="author_edit")
        await db.chapter_drafts.update_one(
            {"_id": inserted.inserted_id},
            {"$set": {"validation_result": report["result"], "continuity_report_id": report["report_id"], "updated_at": datetime.utcnow()}},
        )
        edited.update({"validation_result": report["result"], "continuity_report_id": report["report_id"]})
        await self._after_change(
            db,
            project_id=project_id,
            event_type="chapter_draft_edited",
            payload={"draft_id": edited["draft_id"], "parent_version_id": draft_id, "chapter_number": chapter_number, "validation_result": report["result"]},
        )
        return {"draft": _serialize(edited), "continuity_report": _serialize(report), "source_draft_id": draft_id}

    async def rollback(
        self,
        db,
        project_id: str,
        draft_type: str,
        draft_id: str,
    ) -> Dict[str, Any]:
        collection = "scene_drafts" if draft_type == "scene" else "chapter_drafts"
        identity = "scene_id" if draft_type == "scene" else "chapter_plan_id"
        pid = ObjectId(project_id)
        target = await db[collection].find_one(
            {"project_id": pid, "draft_id": draft_id}
        )
        if not target:
            raise ValueError("Draft version not found")
        if target.get("status") == "archived":
            raise ValueError("Archived draft versions cannot be activated")
        now = datetime.utcnow()
        await db[collection].update_many(
            {
                "project_id": pid,
                identity: target[identity],
                "active": True,
            },
            {"$set": {"active": False, "updated_at": now}},
        )
        await db[collection].update_one(
            {"_id": target["_id"]},
            {"$set": {"active": True, "updated_at": now}},
        )
        if draft_type == "chapter" and target.get("status") == "approved":
            await chapter_intelligence_service.activate_for_draft(
                db,
                project_id,
                draft_id,
            )
        await self._after_change(
            db,
            project_id=project_id,
            event_type=f"{draft_type}_draft_rollback",
            payload={
                "draft_id": draft_id,
                identity: target[identity],
                "arc_id": target.get("arc_id"),
                "chapter_plan_id": target.get("chapter_plan_id"),
                "scene_id": target.get("scene_id"),
            },
        )
        return _serialize(await db[collection].find_one({"_id": target["_id"]}))

    async def validate_paragraph_skeleton(
        self, db, project_id: str, p: dict, all_paragraphs: list[dict]
    ) -> dict:
        domains = {
            "canon": {"valid": True, "errors": [], "warnings": [], "validated_at": datetime.utcnow()},
            "timeline": {"valid": True, "errors": [], "warnings": [], "validated_at": datetime.utcnow()},
            "continuity": {"valid": True, "errors": [], "warnings": [], "validated_at": datetime.utcnow()},
            "characters": {"valid": True, "errors": [], "warnings": [], "validated_at": datetime.utcnow()},
            "pacing": {"valid": True, "errors": [], "warnings": [], "validated_at": datetime.utcnow()},
            "dialogue": {"valid": True, "errors": [], "warnings": [], "validated_at": datetime.utcnow()},
            "world_consistency": {"valid": True, "errors": [], "warnings": [], "validated_at": datetime.utcnow()}
        }

        pid = ObjectId(project_id)
        # 1. Required fields
        req_fields = ["pov", "location", "purpose", "narrative_goal", "scene_goal"]
        missing = [f for f in req_fields if not p.get(f)]
        if missing:
            domains["world_consistency"]["valid"] = False
            domains["world_consistency"]["errors"].append(f"Missing required fields: {', '.join(missing)}")

        # 2. Duplicate IDs
        dup_ids = [item for item in all_paragraphs if item.get("paragraph_id") == p.get("paragraph_id")]
        if len(dup_ids) > 1:
            domains["continuity"]["valid"] = False
            domains["continuity"]["errors"].append(f"Duplicate paragraph ID: {p.get('paragraph_id')}")

        # 3. Ordering
        orders = [item.get("order") for item in all_paragraphs]
        if len(orders) != len(set(orders)):
            domains["pacing"]["valid"] = False
            domains["pacing"]["errors"].append("Duplicate order numbers found in scene")
        
        # 4. Transitions
        order = p.get("order")
        # If not first, should have transition_from_previous
        if order > 1 and not p.get("transition_from_previous"):
            domains["pacing"]["valid"] = False
            domains["pacing"]["errors"].append("Missing transition from previous paragraph")
        # If not last, should have transition_to_next
        max_order = max(orders) if orders else 1
        if order < max_order and not p.get("transition_to_next"):
            domains["pacing"]["valid"] = False
            domains["pacing"]["errors"].append("Missing transition to next paragraph")

        # 5. Characters exist
        chars = p.get("dependencies", {}).get("characters") or []
        if chars:
            db_chars = await db.character_progressions.find({"project_id": pid}).to_list(length=500)
            known_char_names = {item.get("character") for item in db_chars}
            unknown_chars = [c for c in chars if c not in known_char_names]
            if unknown_chars:
                domains["characters"]["valid"] = False
                domains["characters"]["errors"].append(f"Unknown characters: {', '.join(unknown_chars)}")

        # 6. Canon references are valid
        canon_ids = p.get("dependencies", {}).get("canon_facts") or []
        if canon_ids:
            db_entries = await db.knowledge_entries.find({"project_id": pid}).to_list(length=1000)
            known_ids = {item.get("entry_id") for item in db_entries}
            unknown_ids = [cid for cid in canon_ids if cid not in known_ids]
            if unknown_ids:
                domains["canon"]["valid"] = False
                domains["canon"]["errors"].append(f"Unknown canon entry IDs: {', '.join(unknown_ids)}")

        return domains

    async def get_scene_paragraphs(self, db, project_id: str, scene_id: str) -> List[Dict[str, Any]]:
        pid = ObjectId(project_id)
        docs = await db.scene_paragraphs.find({"project_id": pid, "scene_id": scene_id}).sort("order", 1).to_list(length=1000)
        return [_serialize(doc) for doc in docs]

    async def get_paragraph_content(self, db, project_id: str, scene_id: str, paragraph_id: str) -> Dict[str, Any]:
        """Fetch the authoritative paragraph_content record for the Tiptap editor.

        Returns the stored ``paragraph_content`` document if it exists, otherwise
        synthesises a minimal response from the skeleton's ``prose`` field so the
        editor always has something to load.  The schema mirrors the MongoDB
        document written by ``update_paragraph``.
        """
        pid = ObjectId(project_id)

        # 1. Try the authoritative content store first
        doc = await db.paragraph_content.find_one(
            {"project_id": pid, "scene_id": scene_id, "paragraph_id": paragraph_id}
        )
        if doc:
            return _serialize(doc)

        # 2. Fall back to skeleton prose so the editor is never blank
        skeleton = await db.scene_paragraphs.find_one(
            {"project_id": pid, "scene_id": scene_id, "paragraph_id": paragraph_id}
        )
        if not skeleton:
            raise ValueError("Paragraph not found")

        prose = skeleton.get("prose", "")
        return _serialize({
            "project_id": pid,
            "scene_id": scene_id,
            "paragraph_id": paragraph_id,
            "prose": prose,
            "editor_state": skeleton.get("editor_state", {}),
            "current_version_id": skeleton.get("current_version_id"),
            "autosave_version": skeleton.get("autosave_version", 0),
            "word_count": len(prose.split()) if prose else 0,
            "character_count": len(prose),
            "last_saved_by": None,
            "updated_at": skeleton.get("updated_at"),
        })


    async def _save_paragraph_version(self, db, paragraph: dict, change_reason: str = "", created_by: str = "system", generation_metadata: Dict[str, Any] | None = None) -> None:
        version_doc = {
            "version_id": str(uuid4()),
            "project_id": paragraph.get("project_id"),
            "paragraph_id": paragraph["paragraph_id"],
            "version_number": paragraph["version"],
            "snapshot": {k: v for k, v in paragraph.items() if k not in ["_id", "history"]},
            "created_at": datetime.utcnow(),
            "created_by": created_by,
            "generation_metadata": generation_metadata,
            "change_reason": change_reason
        }
        await db.paragraph_versions.insert_one(version_doc)

    async def update_paragraph(
        self,
        db,
        project_id: str,
        scene_id: str,
        paragraph_id: str,
        updates: dict,
        change_reason: str = "",
        create_version: bool = False,
        created_by: str = "human",
        generation_metadata: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        p = await db.scene_paragraphs.find_one({"project_id": pid, "scene_id": scene_id, "paragraph_id": paragraph_id})
        if not p:
            raise ValueError("Paragraph skeleton not found")
        
        now = datetime.utcnow()
        new_version = p.get("version", 1)
        new_autosave_version = p.get("autosave_version", 0)

        if create_version:
            # Save snapshot of old version to paragraph_versions
            await self._save_paragraph_version(db, p, change_reason, created_by=created_by, generation_metadata=generation_metadata)
            new_version += 1
            new_autosave_version = 0
        else:
            new_autosave_version += 1

        # Handle dict nesting for dependencies
        merged_deps = {**(p.get("dependencies") or {}), **(updates.get("dependencies") or {})}
        
        updated_fields = {
            **updates,
            "dependencies": merged_deps,
            "version": new_version,
            "autosave_version": new_autosave_version,
            "updated_at": now
        }
        
        # Ensure we don't accidentally overwrite system properties unless specified
        for system_prop in ["project_id", "scene_id", "paragraph_id", "created_at"]:
            if system_prop in updated_fields:
                del updated_fields[system_prop]

        await db.scene_paragraphs.update_one(
            {"_id": p["_id"]},
            {"$set": updated_fields}
        )

        # Authoritative prose persistence in paragraph_content
        prose_val = updates.get("prose", p.get("prose", ""))
        editor_state_val = updates.get("editor_state", p.get("editor_state", {}))
        
        await db.paragraph_content.update_one(
            {"project_id": pid, "scene_id": scene_id, "paragraph_id": paragraph_id},
            {
                "$set": {
                    "project_id": pid,
                    "scene_id": scene_id,
                    "paragraph_id": paragraph_id,
                    "prose": prose_val,
                    "editor_state": editor_state_val,
                    "current_version_id": p.get("current_version_id"),
                    "autosave_version": new_autosave_version,
                    "word_count": len(prose_val.split()),
                    "character_count": len(prose_val),
                    "last_saved_by": created_by,
                    "updated_at": now
                }
            },
            upsert=True
        )

        # Re-run modular validations
        all_paragraphs = await db.scene_paragraphs.find({"project_id": pid, "scene_id": scene_id}).to_list(length=1000)
        for doc_item in all_paragraphs:
            val_domains = await self.validate_paragraph_skeleton(db, project_id, doc_item, all_paragraphs)
            await db.scene_paragraphs.update_one(
                {"_id": doc_item["_id"]},
                {"$set": {"validation_domains": val_domains}}
            )

        # Trigger domain event
        from app.services.event_bus import domain_event_bus
        domain_event_bus.publish("ParagraphUpdated", {
            "project_id": project_id,
            "scene_id": scene_id,
            "paragraph_id": paragraph_id,
            "prose": prose_val,
            "create_version": create_version,
            "created_by": created_by
        })

        updated_p = await db.scene_paragraphs.find_one({"_id": p["_id"]})
        return _serialize(updated_p)

    async def reorder_paragraphs(self, db, project_id: str, scene_id: str, reorder_payload: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        pid = ObjectId(project_id)
        for item in reorder_payload:
            await db.scene_paragraphs.update_one(
                {"project_id": pid, "scene_id": scene_id, "paragraph_id": item["paragraph_id"]},
                {"$set": {"order": int(item["order"]), "updated_at": datetime.utcnow()}}
            )
        
        # Close any gaps and sequentially re-index starting at 1
        all_p = await db.scene_paragraphs.find({"project_id": pid, "scene_id": scene_id}).sort("order", 1).to_list(length=1000)
        for idx, doc in enumerate(all_p, start=1):
            await db.scene_paragraphs.update_one(
                {"_id": doc["_id"]},
                {"$set": {"order": idx, "updated_at": datetime.utcnow()}}
            )
            
        return await self.get_scene_paragraphs(db, project_id, scene_id)

    async def lock_paragraph(self, db, project_id: str, scene_id: str, paragraph_id: str, is_locked: bool) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        await db.scene_paragraphs.update_one(
            {"project_id": pid, "scene_id": scene_id, "paragraph_id": paragraph_id},
            {"$set": {"is_locked": bool(is_locked), "updated_at": datetime.utcnow()}}
        )
        p = await db.scene_paragraphs.find_one({"project_id": pid, "scene_id": scene_id, "paragraph_id": paragraph_id})
        return _serialize(p)

    async def delete_paragraph(self, db, project_id: str, scene_id: str, paragraph_id: str) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        p = await db.scene_paragraphs.find_one({"project_id": pid, "scene_id": scene_id, "paragraph_id": paragraph_id})
        if not p:
            raise ValueError("Paragraph skeleton not found")
        
        await self._save_paragraph_version(db, p, "deleted")
        await db.scene_paragraphs.delete_one({"_id": p["_id"]})

        # Re-index remaining paragraphs to close the gap
        all_p = await db.scene_paragraphs.find({"project_id": pid, "scene_id": scene_id}).sort("order", 1).to_list(length=1000)
        for idx, doc in enumerate(all_p, start=1):
            await db.scene_paragraphs.update_one(
                {"_id": doc["_id"]},
                {"$set": {"order": idx, "updated_at": datetime.utcnow()}}
            )

        return {"status": "success", "deleted_paragraph_id": paragraph_id}

    async def duplicate_paragraph(self, db, project_id: str, scene_id: str, paragraph_id: str) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        p = await db.scene_paragraphs.find_one({"project_id": pid, "scene_id": scene_id, "paragraph_id": paragraph_id})
        if not p:
            raise ValueError("Paragraph skeleton not found")

        orig_order = p["order"]
        now = datetime.utcnow()

        # Shift orders of all subsequent paragraphs
        await db.scene_paragraphs.update_many(
            {"project_id": pid, "scene_id": scene_id, "order": {"$gt": orig_order}},
            {"$inc": {"order": 1}, "$set": {"updated_at": now}}
        )

        cloned_doc = {
            **p,
            "paragraph_id": str(uuid4()),
            "order": orig_order + 1,
            "version": 1,
            "regeneration_count": 0,
            "is_locked": False,
            "approval_state": "pending",
            "created_at": now,
            "updated_at": now
        }
        if "_id" in cloned_doc:
            del cloned_doc["_id"]

        inserted = await db.scene_paragraphs.insert_one(cloned_doc)
        cloned_doc["_id"] = inserted.inserted_id

        # Re-run validations across all paragraphs in the scene
        all_paragraphs = await db.scene_paragraphs.find({"project_id": pid, "scene_id": scene_id}).to_list(length=1000)
        for doc_item in all_paragraphs:
            val_domains = await self.validate_paragraph_skeleton(db, project_id, doc_item, all_paragraphs)
            await db.scene_paragraphs.update_one(
                {"_id": doc_item["_id"]},
                {"$set": {"validation_domains": val_domains}}
            )

        refetched = await db.scene_paragraphs.find_one({"_id": inserted.inserted_id})
        return _serialize(refetched)

    async def approve_paragraph(self, db, project_id: str, scene_id: str, paragraph_id: str, approval_state: str) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        p = await db.scene_paragraphs.find_one({"project_id": pid, "scene_id": scene_id, "paragraph_id": paragraph_id})
        if not p:
            raise ValueError("Paragraph skeleton not found")
        
        now = datetime.utcnow()
        pipeline = p.get("processing_pipeline") or {}
        if approval_state == "approved":
            pipeline["approval"] = {
                "status": "completed",
                "updated_at": now,
                "provider": "system",
                "model": "rule-engine",
                "token_usage": 0,
                "estimated_cost": 0.0,
                "retry_count": 0,
                "notes": ["Manually approved by author"]
            }
        else:
            pipeline["approval"] = {
                "status": "rejected" if approval_state == "rejected" else "planned",
                "updated_at": now,
                "provider": "system",
                "model": "rule-engine",
                "token_usage": 0,
                "estimated_cost": 0.0,
                "retry_count": 0,
                "notes": []
            }

        await db.scene_paragraphs.update_one(
            {"_id": p["_id"]},
            {"$set": {"approval_state": approval_state, "processing_pipeline": pipeline, "updated_at": now}}
        )
        updated_p = await db.scene_paragraphs.find_one({"_id": p["_id"]})
        return _serialize(updated_p)

    async def regenerate_paragraph(self, db, project_id: str, scene_id: str, paragraph_id: str, change_reason: str = "") -> Dict[str, Any]:
        pid = ObjectId(project_id)
        p = await db.scene_paragraphs.find_one({"project_id": pid, "scene_id": scene_id, "paragraph_id": paragraph_id})
        if not p:
            raise ValueError("Paragraph skeleton not found")

        # Save snapshot
        await self._save_paragraph_version(db, p, f"Regeneration triggered: {change_reason}")

        now = datetime.utcnow()
        new_version = p.get("version", 1) + 1
        new_regen_count = p.get("regeneration_count", 0) + 1

        updated_fields = {
            "version": new_version,
            "regeneration_count": new_regen_count,
            "updated_at": now,
            "purpose": f"{p['purpose']} (Refined: {change_reason})" if change_reason else p["purpose"],
            "narrative_goal": f"{p['narrative_goal']} (Adjusted for: {change_reason})" if change_reason else p["narrative_goal"],
        }
        
        await db.scene_paragraphs.update_one(
            {"_id": p["_id"]},
            {"$set": updated_fields}
        )

        # Re-run validations
        all_paragraphs = await db.scene_paragraphs.find({"project_id": pid, "scene_id": scene_id}).to_list(length=1000)
        for doc_item in all_paragraphs:
            val_domains = await self.validate_paragraph_skeleton(db, project_id, doc_item, all_paragraphs)
            await db.scene_paragraphs.update_one(
                {"_id": doc_item["_id"]},
                {"$set": {"validation_domains": val_domains}}
            )

        refetched = await db.scene_paragraphs.find_one({"_id": p["_id"]})
        return _serialize(refetched)

    async def get_paragraph_history(self, db, project_id: str, scene_id: str, paragraph_id: str) -> List[Dict[str, Any]]:
        docs = await db.paragraph_versions.find({
            "project_id": ObjectId(project_id),
            "paragraph_id": paragraph_id,
        }).sort("version_number", -1).to_list(length=1000)
        return [_serialize(doc) for doc in docs]

    async def ai_edit_paragraph(
        self,
        db,
        project_id: str,
        scene_id: str,
        paragraph_id: str,
        mode: str,
        prompt: str = ""
    ) -> Dict[str, Any]:
        from app.services.provider_gateway import provider_gateway
        from app.services.settings_service import settings_service
        from app.services.event_bus import domain_event_bus
        import os
        from jinja2 import Template

        pid = ObjectId(project_id)
        p = await db.scene_paragraphs.find_one({"project_id": pid, "scene_id": scene_id, "paragraph_id": paragraph_id})
        if not p:
            raise ValueError("Paragraph skeleton not found")

        # 1. Fetch continuity (previous prose & next planning intent)
        all_p = await db.scene_paragraphs.find({"project_id": pid, "scene_id": scene_id}).sort("order", 1).to_list(length=1000)
        curr_idx = -1
        for idx, doc in enumerate(all_p):
            if doc["paragraph_id"] == paragraph_id:
                curr_idx = idx
                break

        prev_prose = ""
        next_intent = ""
        if curr_idx > 0:
            prev_p = all_p[curr_idx - 1]
            prev_prose = prev_p.get("prose") or ""
        if curr_idx < len(all_p) - 1:
            next_p = all_p[curr_idx + 1]
            next_intent = f"Purpose: {next_p.get('purpose', '')}. Goal: {next_p.get('narrative_goal', '')}"

        # 2. Fetch characters present
        character_names = p.get("dependencies", {}).get("characters", [])
        character_context = []
        if character_names:
            char_bibles = await db.character_bibles.find(
                {"project_id": pid, "name": {"$in": character_names}}
            ).to_list(length=10)
            for cb in char_bibles:
                character_context.append(f"Character: {cb.get('name')}. Details: {cb.get('description', '')[:300]}")

        # 3. Fetch canon facts
        canon_context = []
        canon_refs = p.get("dependencies", {}).get("canon_facts", [])
        if canon_refs:
            canon_facts = await db.canon_registry.find(
                {"project_id": pid, "fact_id": {"$in": canon_refs}}
            ).to_list(length=10)
            for cf in canon_facts:
                canon_context.append(f"Canon Fact: {cf.get('title')}. Fact: {cf.get('fact_text') or cf.get('description', '')}")

        # 4. Load jinja template based on mode
        logical_name = "edit" if mode in ["rewrite", "expand", "shorten", "tone"] else "paragraph_expansion"
        from app.services.prompt_registry_service import prompt_registry
        path = prompt_registry.get_template_path(logical_name)
        prompt_version_tag = prompt_registry.get_prompt_version_tag(logical_name)
            
        with open(path, "r", encoding="utf-8") as f:
            template = Template(f.read())

        current_prose = p.get("prose") or ""

        prompt_data = {
            "purpose": p.get("purpose", ""),
            "narrative_goal": p.get("narrative_goal", ""),
            "scene_goal": p.get("scene_goal", ""),
            "pov": p.get("pov", ""),
            "location": p.get("location", ""),
            "emotion": p.get("emotion", ""),
            "tension_level": p.get("tension_level", ""),
            "dialogue_goal": p.get("dialogue_goal", ""),
            "exposition_goal": p.get("exposition_goal", ""),
            "target_word_count": p.get("target_word_count", 250),
            "prev_prose": prev_prose,
            "next_intent": next_intent,
            "current_prose": current_prose,
            "characters": character_context,
            "canon_facts": canon_context,
            "mode": mode,
            "prompt": prompt
        }

        rendered_prompt = template.render(prompt_data)

        # 5. Fetch LLM settings
        exec_settings = await settings_service.get_execution_settings()
        provider = exec_settings.get("default_provider") or "gemini"
        model = exec_settings.get("default_model") or "gemini-1.5-flash"

        # 6. Call provider gateway
        messages = [{"role": "user", "content": rendered_prompt}]
        response = await provider_gateway.generate_with_failover(
            db,
            messages=messages,
            provider=provider,
            model=model,
            agent_name="SceneWriterAgent",
        )

        new_text = response.get("content", "").strip()
        suggestion_id = str(uuid4())

        # Build default structured explanation
        explanation = {
            "editing_goal": f"Apply {mode} adjustment",
            "reasoning": f"Polish paragraph flow with instruction: '{prompt}'" if prompt else f"Auto-generated {mode} expansion",
            "summary_of_changes": "Updated style and structure based on editing instructions.",
            "trade_offs": "Improved clarity at the expense of brevity.",
            "confidence": "High"
        }
        proposed_prose = new_text

        # Try to parse a JSON structure if the model returned one
        if new_text.startswith("{") or "{" in new_text:
            try:
                import json
                start = new_text.find("{")
                end = new_text.rfind("}")
                if start != -1 and end != -1:
                    parsed = json.loads(new_text[start:end+1])
                    if "proposed_prose" in parsed:
                        proposed_prose = parsed["proposed_prose"]
                        if "explanation" in parsed and isinstance(parsed["explanation"], dict):
                            explanation.update(parsed["explanation"])
            except Exception:
                pass

        telemetry = {
            "execution_id": response.get("execution_trace_id") or str(uuid4()),
            "request_id": response.get("execution_trace_id") or str(uuid4()),
            "agent_name": "SceneWriterAgent",
            "workflow_stage": "expansion",
            "provider": provider,
            "model": model,
            "prompt_template": logical_name,
            "prompt_version": prompt_version_tag,
            "temperature": 0.7,
            "token_usage": {
                "prompt_tokens": int(response.get("tokens_used", 0) * 0.7),
                "completion_tokens": int(response.get("tokens_used", 0) * 0.3),
                "total_tokens": int(response.get("tokens_used", 0))
              },
            "latency_ms": int(response.get("latency_ms", 0)),
            "estimated_cost": float(response.get("cost", 0.0) or 0.0),
            "generation_timestamp": datetime.utcnow().isoformat()
        }

        suggestion_doc = {
            "suggestion_id": suggestion_id,
            "project_id": pid,
            "scene_id": scene_id,
            "paragraph_id": paragraph_id,
            "suggestion_type": mode,
            "provider": provider,
            "model": model,
            "created_at": datetime.utcnow(),
            "status": "pending",
            "proposed_prose": proposed_prose,
            "explanation": explanation,
            "generation_metadata": telemetry
        }
        await db.paragraph_suggestions.insert_one(suggestion_doc)

        # Raise event to signal suggestion generated
        domain_event_bus.publish("ParagraphSuggestionGenerated", {
            "project_id": project_id,
            "scene_id": scene_id,
            "paragraph_id": paragraph_id,
            "suggestion_id": suggestion_id
        })

        return _serialize(suggestion_doc)

    async def add_paragraph_comment(
        self,
        db,
        project_id: str,
        paragraph_id: str,
        author: str,
        content: str
    ) -> Dict[str, Any]:
        comment_id = str(uuid4())
        comment_doc = {
            "project_id": ObjectId(project_id),
            "paragraph_id": paragraph_id,
            "comment_id": comment_id,
            "author": author,
            "content": content,
            "status": "open",
            "replies": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await db.paragraph_comments.insert_one(comment_doc)
        return _serialize(comment_doc)

    async def reply_paragraph_comment(
        self,
        db,
        project_id: str,
        paragraph_id: str,
        comment_id: str,
        author: str,
        content: str
    ) -> Dict[str, Any]:
        reply_id = str(uuid4())
        reply = {
            "reply_id": reply_id,
            "author": author,
            "content": content,
            "created_at": datetime.utcnow()
        }
        await db.paragraph_comments.update_one(
            {"project_id": ObjectId(project_id), "paragraph_id": paragraph_id, "comment_id": comment_id},
            {
                "$push": {"replies": reply},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        updated = await db.paragraph_comments.find_one(
            {"project_id": ObjectId(project_id), "paragraph_id": paragraph_id, "comment_id": comment_id}
        )
        return _serialize(updated)

    async def resolve_paragraph_comment(
        self,
        db,
        project_id: str,
        paragraph_id: str,
        comment_id: str
    ) -> Dict[str, Any]:
        await db.paragraph_comments.update_one(
            {"project_id": ObjectId(project_id), "paragraph_id": paragraph_id, "comment_id": comment_id},
            {
                "$set": {"status": "resolved", "updated_at": datetime.utcnow()}
            }
        )
        updated = await db.paragraph_comments.find_one(
            {"project_id": ObjectId(project_id), "paragraph_id": paragraph_id, "comment_id": comment_id}
        )
        return _serialize(updated)

    async def get_paragraph_comments(
        self,
        db,
        project_id: str,
        paragraph_id: str
    ) -> List[Dict[str, Any]]:
        docs = await db.paragraph_comments.find(
            {"project_id": ObjectId(project_id), "paragraph_id": paragraph_id}
        ).to_list(length=1000)
        return [_serialize(doc) for doc in docs]

    async def get_paragraph_suggestions(
        self,
        db,
        paragraph_id: str,
        project_id: str | None = None,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"paragraph_id": paragraph_id}
        if project_id:
            query["project_id"] = ObjectId(project_id)
        docs = await db.paragraph_suggestions.find(
            query
        ).sort("created_at", -1).to_list(length=1000)
        return [_serialize(doc) for doc in docs]

    async def accept_paragraph_suggestion(
        self,
        db,
        project_id: str,
        scene_id: str,
        paragraph_id: str,
        suggestion_id: str
    ) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        sug = await db.paragraph_suggestions.find_one({"suggestion_id": suggestion_id, "paragraph_id": paragraph_id})
        if not sug:
            raise ValueError("Paragraph suggestion not found")

        p = await db.scene_paragraphs.find_one({"project_id": pid, "scene_id": scene_id, "paragraph_id": paragraph_id})
        if not p:
            raise ValueError("Paragraph skeleton not found")

        await self._save_paragraph_version(
            db, p, f"Accepted AI suggestion ({sug['suggestion_type']})", created_by="ai", generation_metadata=sug.get("generation_metadata")
        )

        now = datetime.utcnow()
        new_version = p.get("version", 1) + 1

        await db.scene_paragraphs.update_one(
            {"_id": p["_id"]},
            {
                "$set": {
                    "prose": sug["proposed_prose"],
                    "version": new_version,
                    "autosave_version": 0,
                    "updated_at": now
                }
            }
        )

        await db.paragraph_suggestions.update_one(
            {"_id": sug["_id"]},
            {"$set": {"status": "accepted"}}
        )

        await db.paragraph_suggestions.update_many(
            {"paragraph_id": paragraph_id, "suggestion_id": {"$ne": suggestion_id}, "status": "pending"},
            {"$set": {"status": "rejected"}}
        )

        await db.paragraph_content.update_one(
            {"project_id": pid, "scene_id": scene_id, "paragraph_id": paragraph_id},
            {
                "$set": {
                    "prose": sug["proposed_prose"],
                    "autosave_version": 0,
                    "updated_at": now
                }
            },
            upsert=True
        )

        all_paragraphs = await db.scene_paragraphs.find({"project_id": pid, "scene_id": scene_id}).to_list(length=1000)
        for doc_item in all_paragraphs:
            val_domains = await self.validate_paragraph_skeleton(db, project_id, doc_item, all_paragraphs)
            await db.scene_paragraphs.update_one(
                {"_id": doc_item["_id"]},
                {"$set": {"validation_domains": val_domains}}
            )

        refetched = await db.scene_paragraphs.find_one({"_id": p["_id"]})
        return _serialize(refetched)

    async def reject_paragraph_suggestion(
        self,
        db,
        project_id: str,
        scene_id: str,
        paragraph_id: str,
        suggestion_id: str
    ) -> Dict[str, Any]:
        await db.paragraph_suggestions.update_one(
            {"paragraph_id": paragraph_id, "suggestion_id": suggestion_id},
            {"$set": {"status": "rejected"}}
        )
        return {"status": "success", "suggestion_id": suggestion_id}

    async def restore_paragraph_version(
        self,
        db,
        project_id: str,
        scene_id: str,
        paragraph_id: str,
        version_id: str
    ) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        ver = await db.paragraph_versions.find_one({"paragraph_id": paragraph_id, "version_id": version_id})
        if not ver:
            raise ValueError("Paragraph version not found")

        p = await db.scene_paragraphs.find_one({"project_id": pid, "scene_id": scene_id, "paragraph_id": paragraph_id})
        if not p:
            raise ValueError("Paragraph skeleton not found")

        # Snapshot current content before restoring (Pre-restore snapshot)
        await self._save_paragraph_version(
            db, p, f"Pre-restore snapshot (restoring version {ver['version_number']})"
        )

        now = datetime.utcnow()
        new_version = p.get("version", 1) + 1

        snapshot = ver["snapshot"]
        updated_fields = {
            **snapshot,
            "version": new_version,
            "autosave_version": 0,
            "updated_at": now
        }

        # Clear system fields
        for prop in ["_id", "project_id", "scene_id", "paragraph_id", "created_at"]:
            if prop in updated_fields:
                del updated_fields[prop]

        await db.scene_paragraphs.update_one(
            {"_id": p["_id"]},
            {"$set": updated_fields}
        )

        # Restore content in paragraph_content
        prose_val = snapshot.get("prose", "")
        editor_state_val = snapshot.get("editor_state", {})
        await db.paragraph_content.update_one(
            {"project_id": pid, "scene_id": scene_id, "paragraph_id": paragraph_id},
            {
                "$set": {
                    "prose": prose_val,
                    "editor_state": editor_state_val,
                    "autosave_version": 0,
                    "updated_at": now
                }
            },
            upsert=True
        )

        all_paragraphs = await db.scene_paragraphs.find({"project_id": pid, "scene_id": scene_id}).to_list(length=1000)
        for doc_item in all_paragraphs:
            val_domains = await self.validate_paragraph_skeleton(db, project_id, doc_item, all_paragraphs)
            await db.scene_paragraphs.update_one(
                {"_id": doc_item["_id"]},
                {"$set": {"validation_domains": val_domains}}
            )

        refetched = await db.scene_paragraphs.find_one({"_id": p["_id"]})
        return _serialize(refetched)


drafting_service = DraftingService()
