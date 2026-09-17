"""Interactive consumers of the shared Narrative Analysis Engine.

This service does not analyze story content. It selects, bounds, explains, and
converses over the persisted Phase 6 graph, then routes proposed facts through
the governed canon workflow.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, Iterable
from uuid import uuid4

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.services.canon_governance_service import CANON_TYPES, canon_governance_service
from app.services.application_knowledge_service import application_knowledge_service
from app.services.change_impact_service import change_impact_service
from app.services.narrative_completeness_service import narrative_completeness_service
from app.services.narrative_analysis_engine import narrative_analysis_engine
from app.services.orchestration_engine import orchestration_engine
from app.services.project_event_service import emit_project_event
from app.services.provider_gateway import provider_gateway
from app.services.task_routing_service import task_routing_service
from app.services.model_registry_service import model_registry_service, normalize_provider
from app.services.story_bible_service import rebuild_story_bible
from app.services.writing_experience_service import writing_experience_service
from app.services.story_knowledge_projection_service import story_knowledge_projection_service
from app.services.memory_provider import memory_provider_service


ASSISTANT_MODES = {
    "story_coach": "Coach the author toward clear narrative choices without rewriting prose.",
    "developmental_editor": "Prioritize structure, pacing, tension, emotional rhythm, and chapter balance.",
    "character_interviewer": "Explore motivation, belief, memory, relationships, and internal conflict.",
    "continuity_expert": "Prioritize canon, chronology, knowledge boundaries, and causal continuity.",
    "worldbuilding_consultant": "Prioritize locations, organizations, artifacts, powers, terminology, and rules.",
    "dialogue_coach": "Prioritize established voice, vocabulary, subtext, and relationship-aware dialogue.",
}

NAVIGATION_TARGETS = {
    "story health": "story-health",
    "health": "story-health",
    "timeline": "timeline",
    "canon": "canon",
    "character intelligence": "characters",
    "characters": "characters",
    "story bible": "knowledge",
    "knowledge graph": "knowledge-graph",
    "plot threads": "threads",
    "mysteries": "mysteries",
    "canon queue": "canon-queue",
    "project timeline": "project-timeline",
    "story health history": "explainability-timeline",
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


def _clip(value: Any, limit: int = 500) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else f"{text[: limit - 1]}…"


def _unique(values: Iterable[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[str] = set()
    for value in values:
        marker = json.dumps(_serialize(value), sort_keys=True, default=str)
        if marker not in seen:
            seen.add(marker)
            result.append(value)
    return result


def _severity(item: Dict[str, Any]) -> int:
    return {
        "critical": 0,
        "error": 0,
        "high": 1,
        "warning": 2,
        "medium": 2,
        "low": 3,
        "info": 4,
    }.get(str(item.get("severity") or "warning").lower(), 5)


class NarrativeInteractionService:
    @staticmethod
    def _finding_matches_node(finding: Dict[str, Any], node: Dict[str, Any]) -> bool:
        markers = {
            str(node.get("node_id") or "").strip().lower(),
            str(node.get("source_id") or "").strip().lower(),
            str(node.get("label") or "").strip().lower(),
        } - {""}
        affected = {
            str(value).strip().lower()
            for value in [
                *(finding.get("affected_elements") or []),
                *(finding.get("affected_scenes") or []),
            ]
            if str(value).strip()
        }
        node_chapters = {int(value) for value in node.get("chapter_numbers") or [] if str(value).isdigit()}
        finding_chapters = {int(value) for value in finding.get("affected_chapters") or [] if str(value).isdigit()}
        return bool(markers & affected or node_chapters & finding_chapters)

    async def _project(self, db, project_id: str) -> tuple[ObjectId, Dict[str, Any]]:
        if not ObjectId.is_valid(project_id):
            raise ValueError("Invalid project ID")
        pid = ObjectId(project_id)
        project = await db.projects.find_one({"_id": pid})
        if not project:
            raise ValueError("Project not found")
        return pid, project

    async def _platform(self, db, project_id: str) -> Dict[str, Any]:
        return await narrative_analysis_engine.platform(db, project_id)

    async def _generate(
        self,
        db,
        *,
        agent_name: str,
        system: str,
        prompt: Dict[str, Any],
        max_tokens: int = 1800,
        task: str = "strong",
        model_preference: str = "auto",
    ) -> Dict[str, Any]:
        settings = await orchestration_engine.get_settings(db)
        auto_route = await task_routing_service.select(
            task,
            requested_provider=settings.default_provider if task == "strong" else None,
            requested_model=settings.default_model if task == "strong" else None,
            fallbacks=[],
        )
        preference = str(model_preference or "auto").strip()
        route = auto_route
        selection_reason = auto_route.get("reason")
        if preference.lower() != "auto":
            try:
                selected_provider, selected_model = preference.split("|", 1)
            except ValueError as exc:
                raise ValueError("Story Studio model preference must use a discovered provider and model") from exc
            selected_provider = normalize_provider(selected_provider.strip())
            selected_model = selected_model.strip()
            if not selected_provider or not selected_model:
                raise ValueError("Story Studio model preference must include both provider and model")
            await model_registry_service.validate_model(selected_provider, selected_model)
            fallbacks = []
            auto_key = (normalize_provider(str(auto_route.get("provider") or "")), str(auto_route.get("model") or ""))
            if auto_key[0] and auto_key[1] and auto_key != (selected_provider, selected_model):
                fallbacks.append({"provider": auto_key[0], "model": auto_key[1]})
            fallbacks.extend(auto_route.get("fallbacks") or [])
            route = await task_routing_service.select(
                task,
                requested_provider=selected_provider,
                requested_model=selected_model,
                fallbacks=fallbacks,
            )
            selection_reason = f"author selected {selected_provider}/{selected_model} for the primary response"
        result = await provider_gateway.generate_with_failover(
            db,
            [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": json.dumps(prompt, ensure_ascii=True, default=str),
                },
            ],
            provider=route["provider"],
            model=route["model"],
            temperature=0.25,
            max_tokens=max_tokens,
            agent_name=agent_name,
            expect_json=True,
            fallbacks=[
                *route.get("fallbacks", []),
            ],
            trace_context={"task_tier": route.get("tier"), "routing_reason": selection_reason or route.get("reason"), "task": task, "model_preference": preference},
        )
        return {
            "parsed": result.get("parsed") or {},
            "content": str(result.get("content") or ""),
            "metadata": {
                "provider": result.get("provider"),
                "model": result.get("model"),
                "tokens_used": result.get("tokens_used"),
                "latency_ms": result.get("latency_ms"),
                "execution_trace_id": result.get("execution_trace_id"),
                "source_type": "mock" if result.get("provider") == "mock" else "real_ai",
                "task": task,
                "task_tier": route.get("tier"),
                "model_preference": preference,
                "routing_reason": selection_reason or route.get("reason"),
            },
        }

    async def knowledge_graph(
        self,
        db,
        project_id: str,
        *,
        kinds: list[str] | None = None,
        search: str = "",
        limit: int = 1200,
    ) -> Dict[str, Any]:
        pid, _ = await self._project(db, project_id)
        platform = await self._platform(db, project_id)
        query: Dict[str, Any] = {"project_id": pid}
        if kinds:
            query["kind"] = {"$in": sorted(set(kinds))}
        if search.strip():
            query["label"] = {"$regex": re.escape(search.strip()), "$options": "i"}
        nodes = await db.narrative_nodes.find(query).sort([("kind", 1), ("label", 1)]).to_list(
            length=max(1, min(limit, 5000))
        )
        node_ids = {item["node_id"] for item in nodes}
        edges = await db.narrative_edges.find(
            {
                "project_id": pid,
                "source": {"$in": list(node_ids)},
                "target": {"$in": list(node_ids)},
            },
            {"_id": 0, "project_id": 0},
        ).to_list(length=20000)
        findings = platform.get("findings") or []
        for node in nodes:
            related = [
                item
                for item in findings
                if self._finding_matches_node(item, node)
            ]
            node["warning_count"] = len(related)
            node["story_health_warnings"] = [
                {
                    "finding_id": item.get("finding_id"),
                    "severity": item.get("severity"),
                    "explanation": item.get("explanation"),
                }
                for item in sorted(related, key=_severity)[:5]
            ]
        return _serialize(
            {
                "analysis_id": (platform.get("snapshot") or {}).get("analysis_id"),
                "graph_version": (platform.get("snapshot") or {}).get("graph_version"),
                "nodes": nodes,
                "edges": edges,
                "counts": {
                    "nodes": len(nodes),
                    "edges": len(edges),
                    "by_kind": {
                        kind: sum(1 for item in nodes if item.get("kind") == kind)
                        for kind in sorted({str(item.get("kind")) for item in nodes})
                    },
                },
                "source": "narrative_analysis_engine",
            }
        )

    async def graph_node(self, db, project_id: str, node_id: str) -> Dict[str, Any]:
        pid, _ = await self._project(db, project_id)
        node = await db.narrative_nodes.find_one({"project_id": pid, "node_id": node_id})
        if not node:
            raise ValueError("Knowledge graph node not found")
        edges = await db.narrative_edges.find(
            {"project_id": pid, "$or": [{"source": node_id}, {"target": node_id}]},
            {"_id": 0, "project_id": 0},
        ).to_list(length=5000)
        connected_ids = {
            edge["target"] if edge["source"] == node_id else edge["source"]
            for edge in edges
        }
        connected = await db.narrative_nodes.find(
            {"project_id": pid, "node_id": {"$in": list(connected_ids)}}
        ).to_list(length=5000)
        platform = await self._platform(db, project_id)
        warnings = [
            item
            for item in platform.get("findings") or []
            if self._finding_matches_node(item, node)
        ]
        return _serialize(
            {
                "node": node,
                "summary": node.get("payload") or {},
                "connected_entities": connected,
                "relationships": edges,
                "related_chapters": node.get("chapter_numbers") or [],
                "timeline_references": [item for item in connected if item.get("kind") == "timeline"],
                "canon_references": [item for item in connected if item.get("kind") == "canon"],
                "story_health_warnings": sorted(warnings, key=_severity),
                "analysis_id": (platform.get("snapshot") or {}).get("analysis_id"),
            }
        )

    async def explain_finding(self, db, project_id: str, finding_id: str) -> Dict[str, Any]:
        pid, _ = await self._project(db, project_id)
        finding = await db.narrative_findings.find_one(
            {"project_id": pid, "finding_id": finding_id}
        )
        if not finding:
            raise ValueError("Narrative finding not found")
        elements = [str(value) for value in finding.get("affected_elements") or []]
        nodes = await db.narrative_nodes.find(
            {
                "project_id": pid,
                "$or": [
                    {"node_id": {"$in": elements}},
                    {"source_id": {"$in": elements}},
                    {"label": {"$in": elements}},
                    {"chapter_numbers": {"$in": finding.get("affected_chapters") or []}},
                    {"scene_ids": {"$in": finding.get("affected_scenes") or []}},
                ],
            }
        ).to_list(length=500)
        return _serialize(
            {
                "finding_id": finding_id,
                "why": finding.get("explanation"),
                "severity": finding.get("severity"),
                "confidence": finding.get("confidence"),
                "evidence": finding.get("evidence") or [],
                "chapters": finding.get("affected_chapters") or [],
                "scenes": finding.get("affected_scenes") or [],
                "canon_facts": [item for item in nodes if item.get("kind") == "canon"],
                "timeline_events": [item for item in nodes if item.get("kind") == "timeline"],
                "story_elements": nodes,
                "recommended_actions": finding.get("recommended_actions") or [],
                "source": "narrative_analysis_engine",
            }
        )

    async def workspace_intelligence(
        self,
        db,
        project_id: str,
        *,
        surface: str,
        chapter_number: int | None = None,
        scene_id: str | None = None,
        character_name: str | None = None,
    ) -> Dict[str, Any]:
        await self._project(db, project_id)
        platform = await self._platform(db, project_id)
        findings = list(platform.get("findings") or [])
        contextual = [
            item
            for item in findings
            if (
                chapter_number is not None
                and chapter_number in (item.get("affected_chapters") or [])
            )
            or (scene_id and scene_id in (item.get("affected_scenes") or []))
            or (
                character_name
                and character_name.lower()
                in " ".join(str(value) for value in item.get("affected_elements") or []).lower()
            )
        ]
        if not contextual:
            contextual = sorted(findings, key=_severity)[:5]
        recommendations = [
            {
                "recommendation_id": item.get("finding_id"),
                "severity": item.get("severity"),
                "message": item.get("explanation"),
                "actions": item.get("recommended_actions") or [],
                "evidence": item.get("evidence") or [],
                "affected_chapters": item.get("affected_chapters") or [],
                "affected_scenes": item.get("affected_scenes") or [],
                "why": "Matched the current workspace context to a shared Narrative Analysis finding.",
                "destination": {
                    "canon": "canon", "timeline": "timeline", "character": "characters",
                    "plot": "threads", "pacing": "story-health", "continuity": "story-health",
                    "balance": "story-health",
                }.get(str(item.get("domain") or ""), "story-health"),
            }
            for item in sorted(contextual, key=_severity)[:8]
        ]
        return _serialize(
            {
                "surface": surface,
                "context": {
                    "chapter_number": chapter_number,
                    "scene_id": scene_id,
                    "character_name": character_name,
                },
                "analysis_id": (platform.get("snapshot") or {}).get("analysis_id"),
                "recommendations": recommendations,
                "cache_reused": True,
                "source": "narrative_analysis_engine",
            }
        )

    def _navigation_actions(self, query: str) -> list[Dict[str, Any]]:
        text = query.strip().lower()
        actions: list[Dict[str, Any]] = []
        chapter = re.search(r"(?:open|show|go to)\s+chapter\s+(\d+)", text)
        if chapter:
            actions.append(
                {
                    "type": "navigate",
                    "target": "chapter",
                    "section": "drafting",
                    "chapter_number": int(chapter.group(1)),
                    "label": f"Open Chapter {chapter.group(1)}",
                }
            )
        scene = re.search(r"(?:open|show|go to)\s+scene\s+([a-z0-9_-]+)", text)
        if scene:
            actions.append(
                {
                    "type": "navigate",
                    "target": "scene",
                    "section": "drafting",
                    "scene_id": scene.group(1),
                    "label": f"Open Scene {scene.group(1)}",
                }
            )
        for marker, section in NAVIGATION_TARGETS.items():
            if marker in text and any(verb in text for verb in ("open", "show", "go to", "view")):
                actions.append(
                    {
                        "type": "navigate",
                        "target": marker.replace(" ", "_"),
                        "section": section,
                        "label": f"Open {marker.title()}",
                    }
                )
                break
        return _unique(actions)

    async def _evidence_for_query(
        self, db, pid: ObjectId, platform: Dict[str, Any], query: str
    ) -> Dict[str, Any]:
        tokens = {
            token
            for token in re.findall(r"[a-z0-9_-]+", query.lower())
            if len(token) >= 4
        }
        findings = sorted(platform.get("findings") or [], key=_severity)
        matched = [
            item
            for item in findings
            if not tokens
            or any(token in json.dumps(_serialize(item), default=str).lower() for token in tokens)
        ][:16]
        nodes = await db.narrative_nodes.find({"project_id": pid}).sort("analyzed_at", -1).to_list(
            length=5000
        )
        matched_nodes = [
            item
            for item in nodes
            if tokens
            and any(
                token
                in f"{item.get('label', '')} {item.get('kind', '')} {item.get('source_id', '')}".lower()
                for token in tokens
            )
        ][:30]
        if not matched_nodes:
            matched_nodes = nodes[:20]
        return {
            "findings": matched,
            "nodes": matched_nodes,
            "chapters": sorted(
                {
                    int(value)
                    for item in matched
                    for value in item.get("affected_chapters") or []
                }
            ),
            "canon_facts": [item for item in matched_nodes if item.get("kind") == "canon"],
            "timeline_events": [item for item in matched_nodes if item.get("kind") == "timeline"],
        }

    async def assistant(
        self,
        db,
        project_id: str,
        *,
        query: str,
        mode: str = "story_coach",
        active_surface: str = "dashboard",
        intent: str | None = None,
        request_id: str | None = None,
        allow_proposals: bool = True,
        model_preference: str = "auto",
        model_scope: str = "message",
    ) -> Dict[str, Any]:
        pid, project = await self._project(db, project_id)
        normalized_request_id = str(request_id or "").strip() or None
        if normalized_request_id:
            previous = await db.narrative_assistant_messages.find_one(
                {"project_id": pid, "request_id": normalized_request_id}
            )
            if previous:
                return _serialize(previous)

        async def persist(message: Dict[str, Any]) -> Dict[str, Any]:
            if normalized_request_id:
                message["request_id"] = normalized_request_id
            try:
                await db.narrative_assistant_messages.insert_one(message)
                try:
                    await memory_provider_service.capture(
                        db,
                        project_id,
                        user_content=str(message.get("query") or ""),
                        assistant_content=str(message.get("answer") or ""),
                        source_type="story_studio_conversation",
                        source_id=str(message.get("message_id") or normalized_request_id or ""),
                    )
                except Exception:
                    # Memory observation is optional and must never make a
                    # grounded assistant answer fail after it was persisted.
                    pass
                return _serialize(message)
            except DuplicateKeyError:
                winner = await db.narrative_assistant_messages.find_one(
                    {"project_id": pid, "request_id": normalized_request_id}
                )
                if winner:
                    return _serialize(winner)
                raise
        normalized_mode = mode.strip().lower()
        if normalized_mode not in ASSISTANT_MODES:
            raise ValueError("Unsupported assistant mode")
        if not query.strip():
            raise ValueError("Assistant query is required")
        narrative_creation = intent == "narrative_creation"
        story_state_terms = (
            "chapter", "scene", "mara", "ivo", "injury", "relationship", "character", "canon",
            "mystery", "promise", "timeline", "what happened", "remember", "story truth", "northglass",
        )
        story_state_question = active_surface == "story-studio" and any(term in query.lower() for term in story_state_terms)
        layer = "project" if narrative_creation or story_state_question else application_knowledge_service.classify(query, active_surface)
        writing_question = (
            active_surface in {"drafting", "editorial", "manuscript"}
            and any(
                phrase in query.lower()
                for phrase in (
                    "blocked",
                    "what next",
                    "what should i do",
                    "how do i write",
                    "how do i revise",
                    "how do i review",
                    "how do i approve",
                    "continue writing",
                )
            )
        )
        if writing_question:
            writing = await writing_experience_service.dashboard(db, project_id)
            action = writing["next_action"]
            blockers = writing["scene_health"]["blockers"]
            blocker_text = (
                " The approval checks still open are: "
                + "; ".join(blockers[:4])
                + "."
                if blockers
                else ""
            )
            answer = (
                f"You are at {writing['workflow']['active_stage']}. "
                f"{action['explanation']}{blocker_text} "
                "An exploratory draft is safe to generate now when checks remain, but it cannot "
                "be approved until those checks pass, so your official story truth stays protected."
            )
            destination = str(action.get("target") or active_surface)
            message = {
                "project_id": pid,
                "message_id": str(uuid4()),
                "mode": normalized_mode,
                "query": query,
                "answer": answer,
                "navigation_actions": [{
                    "type": "navigate",
                    "target": destination,
                    "section": destination,
                    "label": action.get("action") or f"Open {destination}",
                }],
                "reasoning_layer": "application",
                "application_surface": active_surface,
                "evidence": {
                    "finding_ids": [],
                    "node_ids": [],
                    "chapters": [],
                    "canon_facts": [],
                    "timeline_events": [],
                    "analysis_id": None,
                    "application_topics": [active_surface],
                    "writing_workflow": writing["workflow"],
                    "writing_blockers": blockers,
                },
                "canon_proposal_ids": [],
                "generation_metadata": {
                    "provider": "writing_experience",
                    "model": None,
                    "tokens_used": 0,
                    "latency_ms": 0,
                    "execution_trace_id": None,
                    "source_type": "writing_workflow_guidance",
                },
                "created_at": datetime.utcnow(),
            }
            return await persist(message)
        application_answer = (
            application_knowledge_service.answer(query, active_surface)
            if layer in {"application", "combined"}
            else None
        )
        if layer == "application":
            now = datetime.utcnow()
            message = {
                "project_id": pid,
                "message_id": str(uuid4()),
                "mode": normalized_mode,
                "query": query,
                "answer": application_answer["answer"],
                "navigation_actions": application_answer["navigation_actions"],
                "reasoning_layer": "application",
                "application_surface": (application_answer.get("surface") or {}).get("surface_id"),
                "evidence": {
                    "finding_ids": [],
                    "node_ids": [],
                    "chapters": [],
                    "canon_facts": [],
                    "timeline_events": [],
                    "analysis_id": None,
                    "application_topics": [
                        (application_answer.get("surface") or {}).get("surface_id")
                    ],
                },
                "canon_proposal_ids": [],
                "generation_metadata": {
                    "provider": "application_knowledge",
                    "model": None,
                    "tokens_used": 0,
                    "latency_ms": 0,
                    "execution_trace_id": None,
                    "source_type": "application_knowledge",
                },
                "created_at": now,
            }
            return await persist(message)

        if layer == "combined" and "what" in query.lower() and "next" in query.lower():
            completeness = await narrative_completeness_service.calculate(db, project_id)
            next_action = (completeness.get("next_actions") or [{}])[0]
            destination = str(next_action.get("target") or "guide")
            if destination not in application_knowledge_service.valid_destinations:
                destination = "guide"
            milestone = completeness.get("current_milestone") or "your current milestone"
            label = next_action.get("label") or "Review the Creation Guide"
            reason = next_action.get("reason") or "It is the highest-priority incomplete foundation."
            message = {
                "project_id": pid,
                "message_id": str(uuid4()),
                "mode": normalized_mode,
                "query": query,
                "answer": (
                    f"{application_answer['answer']} "
                    f"Your next useful step is {label}. {reason} This supports {milestone}."
                ),
                "navigation_actions": _unique([*(application_answer.get("navigation_actions") or []), {
                    "type": "navigate", "target": destination, "section": destination,
                    "label": f"Open {application_knowledge_service.surface(destination)['label']}",
                }]),
                "reasoning_layer": "combined",
                "application_surface": destination,
                "evidence": {
                    "finding_ids": [], "node_ids": [], "chapters": [], "canon_facts": [],
                    "timeline_events": [], "analysis_id": completeness.get("analysis_id"),
                    "application_topics": [destination],
                    "completeness_action_id": next_action.get("action_id"),
                },
                "canon_proposal_ids": [],
                "generation_metadata": {
                    "provider": "application_knowledge", "model": None, "tokens_used": 0,
                    "latency_ms": 0, "execution_trace_id": None,
                    "source_type": "completeness_guidance",
                },
                "created_at": datetime.utcnow(),
            }
            return await persist(message)

        platform = await self._platform(db, project_id)
        evidence = await self._evidence_for_query(db, pid, platform, query)
        deterministic_actions = self._navigation_actions(query)
        writing_state = await writing_experience_service.state(db, project_id)
        requested_chapters = sorted({int(value) for value in re.findall(r"chapter\s+(\d+)", query.lower())})
        chapter_contexts = [
            await writing_experience_service.chapter_context(db, project_id, chapter_number)
            for chapter_number in requested_chapters[:3]
        ]
        confirmed_planning = await story_knowledge_projection_service.confirmed_planning_context(db, project_id, limit=120)
        prompt = {
            "project": {
                "project_name": project.get("project_name") or project.get("title"),
                "story_title": project.get("story_title") or "Untitled novel",
                "title": project.get("story_title") or "Untitled novel",
                "premise": _clip(project.get("premise"), 800),
                "genre": project.get("genre"),
                "tone": project.get("tone"),
            },
            "mode": normalized_mode,
            "mode_instruction": ASSISTANT_MODES[normalized_mode],
            "query": query,
            "intent": intent,
            "analysis_snapshot": platform.get("snapshot") or {},
            "current_writing_state": {
                "workflow_mode": writing_state.get("workflow_mode"),
                "chapter_count": writing_state.get("chapter_count"),
                "latest_approved_chapter": writing_state.get("latest_approved_chapter"),
                "chapters": [
                    {
                        "chapter_number": item.get("chapter_number"),
                        "title": item.get("title"),
                        "status": item.get("status"),
                        "word_count": item.get("word_count"),
                        "active_version": item.get("active_version"),
                    }
                    for item in writing_state.get("chapters") or []
                ],
            },
            "requested_chapter_context": chapter_contexts,
            "confirmed_story_studio_planning": confirmed_planning,
            "supporting_findings": evidence["findings"],
            "supporting_nodes": [
                {
                    "node_id": item.get("node_id"),
                    "kind": item.get("kind"),
                    "label": item.get("label"),
                    "chapters": item.get("chapter_numbers") or [],
                }
                for item in evidence["nodes"]
            ],
            "known_navigation_actions": deterministic_actions,
            "application_context": application_answer,
            "response_contract": {
                "answer": "grounded answer with no invented facts",
                "navigation_actions": "optional actions using the supplied section names",
                "canon_proposals": "new facts only; never modify canon directly",
            },
        }
        generated = await self._generate(
            db,
            agent_name="ProjectAssistant",
            system=(
                (
                    "You are NovelForge's collaborative story-development partner during beginner setup. "
                    "Answer the requested creative step directly with concrete, project-specific narrative "
                    "material. Do not explain the application or navigation. Return JSON with answer, empty "
                    "navigation_actions, and empty canon_proposals. The answer is an editable suggestion, not canon."
                )
                if narrative_creation
                else (
                    "You are NovelForge's project navigator. Keep application guidance separate from story evidence. "
                    "Use supplied Narrative Analysis evidence plus the current writing state and bounded approved-prose excerpts for claims about the novel. "
                    "The current writing state is authoritative for whether chapters exist and their approval status. Confirmed Story Studio planning is authoritative planning input ahead of raw conversation and candidate memory. "
                    "Never say the project has no chapters or is early-stage when current_writing_state reports approved chapters. "
                    "Return JSON with answer, navigation_actions, and canon_proposals. Explain conclusions. "
                    "Never modify story content or canon."
                )
            ),
            prompt=prompt,
            task="brainstorm" if narrative_creation else "story_studio",
            model_preference=model_preference,
        )
        parsed = generated["parsed"]
        answer = str(parsed.get("answer") or parsed.get("summary") or "").strip()
        if not answer:
            score = (platform.get("snapshot") or {}).get("scores", {}).get("overall")
            answer = (
                f"I found {len(evidence['findings'])} relevant Narrative Analysis findings"
                + (f"; the current overall Story Health score is {score}." if score is not None else ".")
            )
        actions = deterministic_actions
        for action in parsed.get("navigation_actions") or []:
            if not isinstance(action, dict):
                continue
            section = str(action.get("section") or "")
            if section == "editor":
                section = "drafting"
            if section in application_knowledge_service.valid_destinations:
                action = {**action, "section": section}
                actions.append({**action, "type": "navigate"})
        proposal_ids = []
        for proposal in ((parsed.get("canon_proposals") or []) if allow_proposals else []):
            if isinstance(proposal, dict) and proposal.get("subject") and proposal.get("field"):
                created = await self.create_canon_proposal(
                    db,
                    project_id,
                    proposal,
                    source_type="project_assistant",
                    source_id=str(uuid4()),
                )
                proposal_ids.append(created["proposal_id"])
        now = datetime.utcnow()
        message = {
            "project_id": pid,
            "message_id": str(uuid4()),
            "mode": normalized_mode,
            "query": query,
            "answer": answer,
            "navigation_actions": _unique(actions),
            "reasoning_layer": layer,
            "application_surface": (
                (application_answer or {}).get("surface") or {}
            ).get("surface_id"),
            "evidence": {
                "finding_ids": [item.get("finding_id") for item in evidence["findings"]],
                "node_ids": [item.get("node_id") for item in evidence["nodes"]],
                "chapters": evidence["chapters"],
                "canon_facts": [item.get("source_id") for item in evidence["canon_facts"]],
                "timeline_events": [item.get("source_id") for item in evidence["timeline_events"]],
                "analysis_id": (platform.get("snapshot") or {}).get("analysis_id"),
                "application_topics": [
                    ((application_answer or {}).get("surface") or {}).get("surface_id")
                ] if application_answer else [],
            },
            "canon_proposal_ids": proposal_ids,
            "generation_metadata": generated["metadata"],
            "created_at": now,
        }
        return await persist(message)

    async def assistant_history(self, db, project_id: str, limit: int = 50) -> list[Dict[str, Any]]:
        pid, _ = await self._project(db, project_id)
        rows = await db.narrative_assistant_messages.find({"project_id": pid}).sort(
            "created_at", -1
        ).to_list(length=max(1, min(limit, 200)))
        return [_serialize(item) for item in reversed(rows)]

    @staticmethod
    def _awareness_source_text(item: Dict[str, Any]) -> str:
        parts: list[str] = []
        for key in (
            "title", "label", "fact", "subject", "field", "value", "content",
            "summary", "chapter_summary", "answer", "solution", "truth", "resolution",
            "payoff", "secret",
        ):
            value = item.get(key)
            if value not in (None, "", [], {}):
                parts.append(str(value))
        return " ".join(parts)

    @staticmethod
    def _lexical_awareness_violations(
        response: str, author_message: str, forbidden_sources: list[Dict[str, Any]]
    ) -> list[Dict[str, Any]]:
        stopwords = {
            "about", "after", "again", "against", "because", "before", "being",
            "chapter", "could", "does", "from", "have", "into", "later", "might",
            "really", "secret", "should", "story", "their", "there", "these", "they",
            "thing", "those", "through", "unknown", "what", "when", "where", "which",
            "while", "with", "would", "your",
        }
        response_tokens = set(re.findall(r"[a-z0-9]+", response.lower()))
        author_tokens = set(re.findall(r"[a-z0-9]+", author_message.lower()))
        new_response_tokens = response_tokens - author_tokens
        violations: list[Dict[str, Any]] = []
        for source in forbidden_sources:
            source_text = NarrativeInteractionService._awareness_source_text(source)
            source_tokens = {
                token
                for token in re.findall(r"[a-z0-9]+", source_text.lower())
                if len(token) >= 4 and token not in stopwords
            }
            overlap = sorted(source_tokens & new_response_tokens)
            distinctive_phrase = " ".join(source_text.lower().split())
            phrase_leak = len(distinctive_phrase) >= 12 and distinctive_phrase in response.lower()
            if phrase_leak or len(overlap) >= 2:
                violations.append(
                    {
                        "source_type": source.get("source_type") or "restricted knowledge",
                        "label": source.get("label") or source.get("title") or "Later story information",
                        "chapter": source.get("chapter_number"),
                        "matched_terms": overlap[:8],
                    }
                )
        return violations

    async def _validate_character_awareness(
        self,
        db,
        *,
        response: str,
        author_message: str,
        effective_chapter: int,
        allowed_evidence: list[Dict[str, Any]],
        forbidden_sources: list[Dict[str, Any]],
    ) -> list[Dict[str, Any]]:
        lexical = self._lexical_awareness_violations(
            response, author_message, forbidden_sources
        )
        adversarial = any(
            marker in author_message.lower()
            for marker in (
                "really causing", "what happens", "later", "future", "secret",
                "doesn't know", "does not know", "behind", "hidden", "truth",
            )
        )
        if lexical or not adversarial or not forbidden_sources:
            return lexical
        # A bounded semantic check catches paraphrased leakage that token matching
        # cannot. It uses the existing CharacterInterviewer route and persists no
        # author-visible response on its own.
        validation = await self._generate(
            db,
            agent_name="CharacterInterviewer",
            system=(
                "Validate chronology only. Decide whether the candidate response states, "
                "implies, confirms, or denies by revealing any restricted fact. Return JSON "
                "with safe and violation_labels. Do not rewrite the response."
            ),
            prompt={
                "timeline_boundary": effective_chapter,
                "author_message": author_message,
                "candidate_response": response,
                "allowed_evidence": allowed_evidence,
                "restricted_information": [
                    {
                        "label": item.get("label") or item.get("title"),
                        "content": _clip(self._awareness_source_text(item), 500),
                        "chapter_number": item.get("chapter_number"),
                    }
                    for item in forbidden_sources[:80]
                ],
                "response_contract": {"safe": True, "violation_labels": []},
            },
        )
        parsed = validation.get("parsed") or {}
        if parsed.get("safe") is False:
            labels = [str(item) for item in parsed.get("violation_labels") or []]
            return [
                {
                    "source_type": "semantic chronology validation",
                    "label": label or "Restricted later story information",
                    "chapter": None,
                    "matched_terms": [],
                }
                for label in (labels or ["Restricted later story information"])
            ]
        return []

    async def _character_context(
        self, db, pid: ObjectId, character_name: str, chapter_number: int | None
    ) -> Dict[str, Any]:
        character = await db.character_bibles.find_one(
            {"project_id": pid, "name": {"$regex": f"^{re.escape(character_name)}$", "$options": "i"}}
        )
        if not character:
            raise ValueError("Character not found in the Narrative Analysis sources")
        max_chapter_doc = await db.chapter_intelligence.find_one(
            {"project_id": pid, "active": True}, sort=[("chapter_number", -1)]
        )
        latest_chapter = int((max_chapter_doc or {}).get("chapter_number") or 0)
        requested = max(0, int(chapter_number if chapter_number is not None else latest_chapter))
        death_chapter = int(character.get("death_chapter") or 0)
        is_dead = str(character.get("current_status") or "").lower() in {"dead", "deceased"}
        effective = min(requested, death_chapter) if is_dead and death_chapter else requested
        chapters = await db.chapter_intelligence.find(
            {"project_id": pid, "active": True, "chapter_number": {"$lte": effective}}
        ).sort("chapter_number", -1).to_list(length=12)
        allowed_source_ids = {
            str(value)
            for item in chapters
            for value in (
                item.get("chapter_draft_id"),
                item.get("chapter_plan_id"),
                item.get("intelligence_id"),
            )
            if value
        }
        canon_rows = await db.canon_registry.find(
            {"project_id": pid, "active": True}
        ).sort("updated_at", -1).to_list(length=5000)
        canon = [
            item
            for item in canon_rows
            if str(item.get("source_id") or "") in allowed_source_ids
            or (
                str(item.get("source_collection") or "") == "character_bibles"
                and str(item.get("subject") or "").lower()
                == str(character.get("name") or "").lower()
            )
        ][:80]
        knowledge_rows = await db.knowledge_entries.find(
            {
                "project_id": pid,
                "known_by": {"$regex": f"^{re.escape(character_name)}$", "$options": "i"},
            }
        ).to_list(length=1000)
        knowledge = [
            item
            for item in knowledge_rows
            if bool(item.get("always_known"))
            or 0
            < int(
                item.get("learned_chapter")
                or item.get("introduced_chapter")
                or item.get("chapter_number")
                or 0
            )
            <= effective
        ]
        forbidden_knowledge = [
            item
            for item in await db.knowledge_entries.find({"project_id": pid}).to_list(length=5000)
            if item not in knowledge
        ]
        relationships = await db.relationship_graphs.find(
            {
                "project_id": pid,
                "$or": [
                    {"character_a": {"$regex": f"^{re.escape(character_name)}$", "$options": "i"}},
                    {"character_b": {"$regex": f"^{re.escape(character_name)}$", "$options": "i"}},
                ],
            }
        ).to_list(length=200)
        timeline_rows = await db.narrative_nodes.find(
            {
                "project_id": pid,
                "kind": "timeline",
            }
        ).sort("analyzed_at", -1).to_list(length=100)
        timeline = [
            item
            for item in timeline_rows
            if item.get("chapter_numbers")
            and max(int(value or 0) for value in item.get("chapter_numbers") or [0]) <= effective
        ]
        future_chapters = await db.chapter_intelligence.find(
            {"project_id": pid, "active": True, "chapter_number": {"$gt": effective}}
        ).sort("chapter_number", 1).to_list(length=5000)
        future_timeline = [
            item
            for item in timeline_rows
            if not item.get("chapter_numbers")
            or max(int(value or 0) for value in item.get("chapter_numbers") or [0]) > effective
        ]
        hidden_mysteries = await db.mystery_registry.find(
            {"project_id": pid, "status": {"$ne": "resolved"}}
        ).to_list(length=2000)
        forbidden_canon = [item for item in canon_rows if item not in canon]
        memories = await db.character_conversation_memories.find(
            {
                "project_id": pid,
                "character_name": character.get("name"),
                "timeline_chapter": {"$lte": effective},
            }
        ).sort("created_at", -1).to_list(length=30)
        return {
            "character": character,
            "requested_chapter": requested,
            "effective_chapter": effective,
            "latest_project_chapter": latest_chapter,
            "death_boundary_applied": bool(is_dead and death_chapter and requested > death_chapter),
            "death_chapter": death_chapter or None,
            "recent_events": list(reversed(chapters)),
            "known_canon": canon,
            "known_information": knowledge,
            "relationships": relationships,
            "timeline_events": timeline,
            "conversation_memory": memories,
            "forbidden_sources": [
                *[
                    {**item, "source_type": "future character knowledge", "label": item.get("title")}
                    for item in forbidden_knowledge
                ],
                *[
                    {**item, "source_type": "later chapter", "label": item.get("title")}
                    for item in future_chapters
                ],
                *[
                    {**item, "source_type": "future timeline", "label": item.get("label")}
                    for item in future_timeline
                ],
                *[
                    {**item, "source_type": "hidden canon", "label": item.get("subject") or item.get("fact")}
                    for item in forbidden_canon
                ],
                *[
                    {**item, "source_type": "unresolved mystery", "label": item.get("question")}
                    for item in hidden_mysteries
                    if any(item.get(key) not in (None, "", [], {}) for key in ("answer", "solution", "truth", "resolution", "payoff", "secret"))
                ],
            ],
        }

    async def character_conversation(
        self,
        db,
        project_id: str,
        *,
        character_name: str,
        message: str,
        chapter_number: int | None = None,
        conversation_id: str | None = None,
    ) -> Dict[str, Any]:
        pid, project = await self._project(db, project_id)
        if not message.strip():
            raise ValueError("Conversation message is required")
        context = await self._character_context(db, pid, character_name, chapter_number)
        character = context["character"]
        compact_context = {
            # Project premise is intentionally excluded: a one-sentence premise often
            # contains the ending or hidden cause and is not character knowledge.
            "project": {"title": project.get("title")},
            "character": {
                key: character.get(key)
                for key in (
                    "name",
                    "role",
                    "description",
                    "personality",
                    "motivations",
                    "goals",
                    "beliefs",
                    "fears",
                    "emotional_state",
                    "dialogue_style",
                    "vocabulary",
                    "internal_conflicts",
                    "current_status",
                )
                if character.get(key) not in (None, "", [], {})
            },
            "timeline_boundary": {
                "chapter": context["effective_chapter"],
                "death_boundary_applied": context["death_boundary_applied"],
                "death_chapter": context["death_chapter"],
            },
            "recent_events": [
                {
                    "chapter_number": item.get("chapter_number"),
                    "summary": _clip(item.get("chapter_summary"), 360),
                    "events": item.get("important_events") or [],
                    "character_changes": item.get("character_changes") or [],
                }
                for item in context["recent_events"][-8:]
            ],
            "known_canon": [
                {
                    "canon_id": item.get("canon_id"),
                    "fact": item.get("fact"),
                    "subject": item.get("subject"),
                    "field": item.get("field"),
                    "value": item.get("value"),
                }
                for item in context["known_canon"][:50]
            ],
            "known_information": [
                {
                    "entry_id": item.get("entry_id"),
                    "title": item.get("title"),
                    "content": _clip(item.get("content"), 300),
                }
                for item in context["known_information"][:40]
            ],
            "relationships": [
                {
                    "relationship_id": item.get("relationship_id"),
                    "character_a": item.get("character_a"),
                    "character_b": item.get("character_b"),
                    "relationship_type": item.get("relationship_type") or item.get("type"),
                    "state": (
                        item.get("status")
                        if int(item.get("chapter_number") or item.get("updated_chapter") or 0)
                        and int(item.get("chapter_number") or item.get("updated_chapter") or 0)
                        <= context["effective_chapter"]
                        else item.get("initial_status") or item.get("starting_state")
                    ),
                }
                for item in context["relationships"][:30]
            ],
            "timeline_events": [
                {"node_id": item.get("node_id"), "label": item.get("label"), "payload": item.get("payload")}
                for item in context["timeline_events"][:30]
            ],
            "conversation_memory": [
                {
                    "summary": item.get("summary"),
                    "promises": item.get("promises") or [],
                    "opinions": item.get("opinions") or [],
                    "relationship_changes": item.get("relationship_changes") or [],
                    "emotional_history": item.get("emotional_history") or [],
                    "unresolved_conflicts": item.get("unresolved_conflicts") or [],
                }
                for item in context["conversation_memory"][:20]
            ],
            "author_message": message,
            "response_contract": {
                "response": "in-character response grounded only in supplied knowledge",
                "memory_updates": {
                    "summary": "short memory",
                    "promises": [],
                    "opinions": [],
                    "relationship_changes": [],
                    "emotional_history": [],
                    "unresolved_conflicts": [],
                },
                "canon_proposals": "new facts only; never alter canon directly",
            },
        }
        generated = await self._generate(
            db,
            agent_name="CharacterInterviewer",
            system=(
                "Speak as the supplied character at the exact timeline boundary. Never reveal later events, "
                "unknown knowledge, or future chapters. A dead character cannot cross the supplied death boundary. "
                "Preserve personality, motivations, emotional state, relationships, dialogue style, and vocabulary. "
                "Return JSON with response, memory_updates, and canon_proposals."
            ),
            prompt=compact_context,
        )
        parsed = generated["parsed"]
        response_text = str(parsed.get("response") or parsed.get("answer") or "").strip()
        if not response_text:
            response_text = (
                f"{character.get('name')} considers the question from the perspective of chapter "
                f"{context['effective_chapter']}, guided by the approved memories available there."
            )
        allowed_evidence = [
            {"kind": "chapter", "label": item.get("title"), "chapter": item.get("chapter_number")}
            for item in context["recent_events"]
        ] + [
            {"kind": "knowledge", "label": item.get("title"), "chapter": item.get("learned_chapter")}
            for item in context["known_information"]
        ]
        violations = await self._validate_character_awareness(
            db,
            response=response_text,
            author_message=message,
            effective_chapter=context["effective_chapter"],
            allowed_evidence=allowed_evidence,
            forbidden_sources=context["forbidden_sources"],
        )
        if violations:
            correction = await self._generate(
                db,
                agent_name="CharacterInterviewer",
                system=(
                    "Correct an unsafe in-character answer. Use only the supplied allowed evidence. "
                    "Do not repeat, confirm, deny by repeating, hint at, or paraphrase restricted facts. "
                    "When the character cannot know, say so naturally without naming the hidden answer. "
                    "Return JSON with response, memory_updates, and canon_proposals."
                ),
                prompt={
                    **compact_context,
                    "unsafe_response_removed": True,
                    "violations": violations,
                    "allowed_evidence": allowed_evidence,
                },
            )
            parsed = correction["parsed"]
            response_text = str(parsed.get("response") or parsed.get("answer") or "").strip()
            if not response_text:
                raise ValueError(
                    "The character conversation could not be completed safely at this chapter. "
                    "No response or memory was saved."
                )
            violations = await self._validate_character_awareness(
                db,
                response=response_text,
                author_message=message,
                effective_chapter=context["effective_chapter"],
                allowed_evidence=allowed_evidence,
                forbidden_sources=context["forbidden_sources"],
            )
            if violations:
                raise ValueError(
                    "The character conversation was withheld because it revealed knowledge from "
                    "a later point in the story. No response or memory was saved."
                )
            generated = correction
        resolved_conversation_id = conversation_id or str(uuid4())
        now = datetime.utcnow()
        turn = {
            "project_id": pid,
            "conversation_id": resolved_conversation_id,
            "turn_id": str(uuid4()),
            "character_name": character.get("name"),
            "timeline_chapter": context["effective_chapter"],
            "author_message": message,
            "character_response": response_text,
            "awareness_boundary": {
                "requested_chapter": context["requested_chapter"],
                "effective_chapter": context["effective_chapter"],
                "death_boundary_applied": context["death_boundary_applied"],
                "death_chapter": context["death_chapter"],
            },
            "evidence": {
                "canon_ids": [item.get("canon_id") for item in context["known_canon"]],
                "timeline_node_ids": [item.get("node_id") for item in context["timeline_events"]],
                "chapter_numbers": [item.get("chapter_number") for item in context["recent_events"]],
                "knowledge_entry_ids": [item.get("entry_id") for item in context["known_information"]],
                "author_labels": [item.get("label") for item in allowed_evidence if item.get("label")],
            },
            "awareness_validation": {
                "status": "safe",
                "chapter_boundary": context["effective_chapter"],
                "evidence_count": len(allowed_evidence),
            },
            "generation_metadata": generated["metadata"],
            "created_at": now,
        }
        await db.narrative_conversations.insert_one(turn)
        memory = parsed.get("memory_updates") if isinstance(parsed.get("memory_updates"), dict) else {}
        memory_doc = {
            "project_id": pid,
            "memory_id": str(uuid4()),
            "conversation_id": resolved_conversation_id,
            "turn_id": turn["turn_id"],
            "character_name": character.get("name"),
            "timeline_chapter": context["effective_chapter"],
            "summary": _clip(memory.get("summary") or f"Discussed: {message}", 500),
            "promises": list(memory.get("promises") or [])[:20],
            "opinions": list(memory.get("opinions") or [])[:20],
            "relationship_changes": list(memory.get("relationship_changes") or [])[:20],
            "emotional_history": list(memory.get("emotional_history") or [])[:20],
            "unresolved_conflicts": list(memory.get("unresolved_conflicts") or [])[:20],
            "created_at": now,
        }
        await db.character_conversation_memories.insert_one(memory_doc)
        proposal_ids = []
        for proposal in parsed.get("canon_proposals") or []:
            if isinstance(proposal, dict) and proposal.get("subject") and proposal.get("field"):
                created = await self.create_canon_proposal(
                    db,
                    project_id,
                    proposal,
                    source_type="character_conversation",
                    source_id=turn["turn_id"],
                )
                proposal_ids.append(created["proposal_id"])
        turn["memory"] = memory_doc
        turn["canon_proposal_ids"] = proposal_ids
        bible = await rebuild_story_bible(db, project_id)
        turn["story_bible_version"] = bible.get("version")
        return _serialize(turn)

    async def character_history(
        self, db, project_id: str, character_name: str, limit: int = 100
    ) -> list[Dict[str, Any]]:
        pid, _ = await self._project(db, project_id)
        rows = await db.narrative_conversations.find(
            {
                "project_id": pid,
                "character_name": {"$regex": f"^{re.escape(character_name)}$", "$options": "i"},
            }
        ).sort("created_at", 1).to_list(length=max(1, min(limit, 500)))
        return [_serialize(item) for item in rows]

    async def create_canon_proposal(
        self,
        db,
        project_id: str,
        payload: Dict[str, Any],
        *,
        source_type: str = "manual",
        source_id: str = "",
    ) -> Dict[str, Any]:
        pid, _ = await self._project(db, project_id)
        subject = str(payload.get("subject") or "").strip()
        field = str(payload.get("field") or "").strip()
        canon_type = str(payload.get("canon_type") or "world").strip().lower()
        if not subject or not field:
            raise ValueError("Canon proposal subject and field are required")
        if canon_type not in CANON_TYPES:
            raise ValueError("Unsupported canon type")
        proposal_id = str(uuid4())
        impact = await change_impact_service.analyze(
            db,
            project_id,
            change_type="canon_change",
            target={"subject": subject, "field": field},
            proposed_change={"value": payload.get("value")},
        )
        now = datetime.utcnow()
        proposal = {
            "project_id": pid,
            "proposal_id": proposal_id,
            "canon_type": canon_type,
            "subject": subject,
            "field": field,
            "value": payload.get("value"),
            "confidence": max(0.0, min(1.0, float(payload.get("confidence") or 0.5))),
            "evidence": list(payload.get("evidence") or [])[:50],
            "affected_chapters": list(payload.get("affected_chapters") or [])[:500],
            "affected_scenes": list(payload.get("affected_scenes") or [])[:1000],
            "downstream_impact": impact,
            "impact_id": impact.get("impact_id"),
            "source_type": source_type,
            "source_id": source_id,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }
        inserted = await db.canon_proposals.insert_one(proposal)
        proposal["_id"] = inserted.inserted_id
        await emit_project_event(
            db,
            project_id,
            "canon_proposal_created",
            payload={
                "proposal_id": proposal_id,
                "source_type": source_type,
                "subject": subject,
                "field": field,
                "affected_chapters": proposal["affected_chapters"],
            },
        )
        return _serialize(proposal)

    async def canon_proposals(
        self, db, project_id: str, status: str | None = None, limit: int = 200
    ) -> list[Dict[str, Any]]:
        pid, _ = await self._project(db, project_id)
        query: Dict[str, Any] = {"project_id": pid}
        if status:
            query["status"] = status
        rows = await db.canon_proposals.find(query).sort("created_at", -1).to_list(
            length=max(1, min(limit, 1000))
        )
        return [_serialize(item) for item in rows]

    async def review_canon_proposal(
        self,
        db,
        project_id: str,
        proposal_id: str,
        *,
        decision: str,
        note: str = "",
        confirm_high_impact: bool = False,
    ) -> Dict[str, Any]:
        pid, _ = await self._project(db, project_id)
        normalized = decision.strip().lower()
        if normalized not in {"approved", "rejected"}:
            raise ValueError("Proposal decision must be approved or rejected")
        proposal = await db.canon_proposals.find_one(
            {"project_id": pid, "proposal_id": proposal_id}
        )
        if not proposal:
            raise ValueError("Canon proposal not found")
        if proposal.get("status") != "pending":
            raise ValueError("Canon proposal already has a decision")
        impact = proposal.get("downstream_impact") or {}
        if normalized == "approved" and impact.get("requires_confirmation") and not confirm_high_impact:
            raise ValueError("High-impact canon proposal requires explicit confirmation")
        now = datetime.utcnow()
        operation_id = str(uuid4())
        transitional_status = "approving" if normalized == "approved" else normalized
        await db.canon_proposals.update_one(
            {"_id": proposal["_id"]},
            {
                "$set": {
                    "status": transitional_status,
                    "review_note": note.strip(),
                    "review_operation_id": operation_id,
                    "review_started_at": now,
                    "updated_at": now,
                },
                "$unset": {"review_error": ""},
            },
        )
        canon_record = None
        try:
            if normalized == "approved":
                proposal["status"] = "approved"
                canon_record = await canon_governance_service.promote(
                    db,
                    project_id,
                    canon_type=str(proposal.get("canon_type") or "world"),
                    source_collection="canon_proposals",
                    source_id=proposal_id,
                    subject=str(proposal.get("subject") or ""),
                    field=str(proposal.get("field") or ""),
                    value=proposal.get("value"),
                    authority_level="approved",
                    evidence=[
                        *list(proposal.get("evidence") or []),
                        f"canon_proposals:{proposal_id}",
                    ],
                )
                await narrative_analysis_engine.analyze(
                    db,
                    project_id,
                    changed_sources=[str(canon_record.get("canon_id") or "")],
                )
                # The Story Bible projection reads the governed proposal queue.
                # Publish the approved state before rebuilding so every
                # downstream projection observes the same decision.
                await db.canon_proposals.update_one(
                    {"_id": proposal["_id"], "review_operation_id": operation_id},
                    {"$set": {"status": "approved", "updated_at": datetime.utcnow()}},
                )
            if proposal.get("impact_id"):
                try:
                    await change_impact_service.set_status(
                        db, project_id, str(proposal["impact_id"]), normalized
                    )
                except ValueError:
                    pass
            bible = await rebuild_story_bible(db, project_id)
            await narrative_completeness_service.calculate(db, project_id)
            completed_at = datetime.utcnow()
            await db.canon_proposals.update_one(
                {"_id": proposal["_id"], "review_operation_id": operation_id},
                {"$set": {
                    "status": normalized,
                    "reviewed_at": completed_at,
                    "updated_at": completed_at,
                }},
            )
        except Exception as exc:
            await db.canon_proposals.update_one(
                {"_id": proposal["_id"], "review_operation_id": operation_id},
                {"$set": {
                    "status": "approval_failed" if normalized == "approved" else "review_failed",
                    "review_error": str(exc)[:500],
                    "updated_at": datetime.utcnow(),
                }},
            )
            raise
        updated = await db.canon_proposals.find_one({"_id": proposal["_id"]})
        result = _serialize(updated)
        result["canon_record"] = canon_record
        result["story_bible_version"] = bible.get("version")
        await emit_project_event(
            db,
            project_id,
            "canon_proposal_reviewed",
            cycle_number=int(bible.get("cycle_number") or 0),
            payload={"proposal_id": proposal_id, "decision": normalized},
        )
        return result


narrative_interaction_service = NarrativeInteractionService()


__all__ = ["ASSISTANT_MODES", "NarrativeInteractionService", "narrative_interaction_service"]
