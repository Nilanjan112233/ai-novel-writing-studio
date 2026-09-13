"""Demand-driven production orchestration for Narrative Studio cycles."""
from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Any, Dict, Iterable, List, Tuple

from bson import ObjectId

from app.services.narrative_studio import STUDIO_AGENT_NAMES
from app.services.observability_service import estimate_cost
from app.services.orchestration_engine import orchestration_engine


MAX_AGENT_CALLS_PER_CYCLE = 10
MAX_ORCHESTRATION_DEPTH = 5

PLANNING_AGENTS = list(STUDIO_AGENT_NAMES)

DOMAIN_AGENT_SEEDS: Dict[str, List[str]] = {
    "concept": [
        "NarrativeDirectorAgent",
        "StoryArchitectAgent",
        "QuestionAgent",
    ],
    "character": ["CharacterJourneyAgent", "RelationshipAgent"],
    "world": ["WorldAgent", "FactionAgent"],
    "power": ["PowerSystemAgent", "CharacterJourneyAgent"],
    "faction": ["FactionAgent", "RelationshipAgent"],
    "relationship": ["RelationshipAgent", "CharacterJourneyAgent"],
    "theme": ["ThemeAgent", "ArcArchitectAgent"],
    "mystery": ["MysteryAgent", "ArcArchitectAgent"],
    "arc": ["ArcArchitectAgent", "PacingAgent"],
    "question": ["QuestionAgent", "NarrativeDirectorAgent"],
    "readiness": ["ReadinessAgent"],
    "knowledge": ["KnowledgeAgent", "MysteryAgent"],
    "timeline": ["ArcArchitectAgent", "PacingAgent"],
    "progression": ["CharacterJourneyAgent", "RelationshipAgent"],
    "foreshadow": ["MysteryAgent", "ArcArchitectAgent"],
    "artifact": ["WorldAgent", "PowerSystemAgent", "CharacterJourneyAgent"],
    "arc_development": ["StoryDevelopmentAgent"],
    "chapter_plan": ["StoryDevelopmentAgent", "ArcArchitectAgent", "PacingAgent"],
    "scene_plan": ["StoryDevelopmentAgent"],
    "automatic_scene_planning": ["ScenePlannerAgent"],
    "power_progression": ["PowerSystemAgent", "CharacterJourneyAgent"],
    "knowledge_evolution": ["KnowledgeAgent", "StoryDevelopmentAgent"],
    "foreshadow_chain": ["MysteryAgent", "ArcArchitectAgent", "StoryDevelopmentAgent"],
    "artifact_evolution": ["WorldAgent", "PowerSystemAgent", "StoryDevelopmentAgent"],
    "scene_draft": ["SceneWriterAgent"],
    "chapter_draft": ["ChapterAssemblerAgent"],
    "draft_continuity": ["KnowledgeAgent", "StoryDevelopmentAgent"],
    "editorial_review": ["EditorAgent"],
    "dialogue_review": ["DialogueAgent"],
    "revision": ["RevisionAgent"],
    "manuscript_review": ["ManuscriptAgent"],
    "canon_validation": ["CanonAgent"],
    "story_audit": ["StoryAuditorAgent"],
}

# Edges mean "a change handled by the source can require the target".
AGENT_IMPACT_GRAPH: Dict[str, List[str]] = {
    "NarrativeDirectorAgent": [],
    "StoryArchitectAgent": ["ArcArchitectAgent"],
    "CharacterJourneyAgent": ["RelationshipAgent", "ArcArchitectAgent"],
    "WorldAgent": ["FactionAgent"],
    "PowerSystemAgent": ["CharacterJourneyAgent", "ArcArchitectAgent"],
    "FactionAgent": [],
    # Character work owns the relationship hand-off. The reverse edge created
    # a cycle and could schedule Character Journey twice without new evidence.
    "RelationshipAgent": [],
    "ThemeAgent": ["ArcArchitectAgent"],
    "MysteryAgent": ["ArcArchitectAgent"],
    "ArcArchitectAgent": ["PacingAgent"],
    "PacingAgent": [],
    "QuestionAgent": ["NarrativeDirectorAgent"],
    "ReadinessAgent": [],
    "KnowledgeAgent": ["MysteryAgent", "ArcArchitectAgent"],
    "StoryDevelopmentAgent": [],
    "ScenePlannerAgent": [],
    "SceneWriterAgent": [],
    "ChapterAssemblerAgent": [],
    "EditorAgent": [],
    "DialogueAgent": [],
    "RevisionAgent": [],
    "ManuscriptAgent": [],
    "CanonAgent": [],
    "StoryAuditorAgent": [],
}

AGENT_PRIMARY_DOMAIN = {
    "NarrativeDirectorAgent": "concept",
    "StoryArchitectAgent": "concept",
    "CharacterJourneyAgent": "character",
    "WorldAgent": "world",
    "PowerSystemAgent": "power system",
    "FactionAgent": "faction",
    "RelationshipAgent": "relationship",
    "ThemeAgent": "theme",
    "MysteryAgent": "mystery",
    "ArcArchitectAgent": "arc",
    "PacingAgent": "arc or pacing",
    "QuestionAgent": "open-question",
    "ReadinessAgent": "readiness",
    "KnowledgeAgent": "knowledge",
    "StoryDevelopmentAgent": "arc development",
    "SceneWriterAgent": "scene drafting",
    "ChapterAssemblerAgent": "chapter assembly",
    "EditorAgent": "editorial review",
    "DialogueAgent": "dialogue review",
    "RevisionAgent": "revision proposal",
    "ManuscriptAgent": "manuscript review",
    "CanonAgent": "canon validation",
    "StoryAuditorAgent": "story audit",
}

FIELD_DOMAINS = {
    "title": {"concept"},
    "premise": {"concept"},
    "idea_dump": {"concept"},
    "genre": {"concept"},
    "tone": {"concept"},
    "target_length": {"concept"},
    "audience": {"concept"},
    "narrative_goals": {"concept"},
    "inspirations": {"concept"},
    "notes": {"concept"},
    "plot_notes": {"concept", "arc"},
    "character_notes": {"character"},
    "world_notes": {"world"},
    "themes": {"theme"},
}

DOMAIN_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "character": (
        "character", "protagonist", "antagonist", "hero", "villain", "mentor",
        "personality", "flaw", "goal", "fear", "belief",
    ),
    "relationship": (
        "relationship", "romance", "friendship", "trust", "betrayal", "ally",
        "rival",
    ),
    "world": (
        "world", "kingdom", "city", "society", "culture", "history", "religion",
        "technology", "location", "civilization",
    ),
    "power": (
        "power", "magic", "ability", "spell", "skill", "cultivation", "rank",
        "level",
    ),
    "faction": (
        "faction", "guild", "empire", "order", "organization", "army", "court",
    ),
    "theme": ("theme", "moral", "meaning", "motif", "symbol"),
    "mystery": ("mystery", "secret", "clue", "reveal", "riddle"),
    "arc": (
        "arc", "plot", "turning point", "climax", "stakes", "conflict",
        "escalation", "ending", "resolution",
    ),
    "question": ("question", "answer", "clarify", "unclear", "unknown"),
    "concept": ("premise", "concept", "genre", "tone", "story idea"),
    "readiness": ("readiness", "ready", "blocked", "blocking", "missing"),
    "knowledge": ("knowledge", "reader knows", "character knows", "world truth"),
    "timeline": ("timeline", "future event", "chronology", "unknown future"),
    "progression": ("progression", "maturity", "trauma", "character growth"),
    "foreshadow": ("foreshadow", "seed", "payoff", "planted"),
    "artifact": ("artifact", "relic", "weapon", "treasure", "inheritance"),
    "arc_development": ("arc development", "maturity", "checklist", "story room"),
    "chapter_plan": ("chapter plan", "chapter purpose", "chapter conflict"),
    "scene_plan": ("scene plan", "scene purpose", "scene outcome"),
    "power_progression": ("power progression", "power growth", "ability mastery"),
    "knowledge_evolution": ("knowledge evolution", "misunderstanding", "confirmation"),
    "foreshadow_chain": ("foreshadow chain", "reinforcement", "seed chain"),
    "artifact_evolution": ("artifact evolution", "awakening", "artifact transfer"),
    "scene_draft": ("scene draft", "draft scene", "scene prose"),
    "chapter_draft": ("chapter draft", "assemble chapter", "chapter assembly"),
    "draft_continuity": ("continuity violation", "draft validation", "draft contradiction"),
    "editorial_review": ("editorial review", "style review", "voice consistency"),
    "dialogue_review": ("dialogue review", "dialogue analysis", "speaker voice"),
    "revision": ("revision request", "revision branch", "revision proposal"),
    "manuscript_review": (
        "manuscript review",
        "book review",
        "manuscript continuity",
    ),
    "canon_validation": (
        "canon review",
        "canon validation",
        "canon conflict",
    ),
    "story_audit": (
        "story audit",
        "story health",
        "abandoned thread",
        "narrative contradiction",
        "ai writing",
    ),
}

EVENT_DOMAINS: Dict[str, List[str]] = {
    "readiness_changed": ["readiness"],
    "arc_changed": ["arc", "readiness", "arc_development"],
    "timeline_v2_changed": ["timeline", "arc"],
    "character_progression_changed": ["progression"],
    "knowledge_changed": ["knowledge"],
    "foreshadow_changed": ["foreshadow"],
    "artifact_changed": ["artifact"],
    "arc_development_changed": ["arc_development"],
    "arc_focus_changed": ["arc_development"],
    "arc_checklist_changed": ["arc_development"],
    "arc_dependency_changed": ["arc_development"],
    "chapter_plan_changed": ["chapter_plan"],
    "scene_plan_changed": ["scene_plan"],
    "power_progression_changed": ["power_progression"],
    "knowledge_evolution_changed": ["knowledge_evolution"],
    "foreshadow_chain_changed": ["foreshadow_chain"],
    "artifact_evolution_changed": ["artifact_evolution"],
    # Draft generation is an explicit author action with its own one-agent plan.
    # These events synchronize state but must not replay prose agents in a later cycle.
    "scene_draft_generated": [],
    "scene_draft_changed": [],
    "scene_draft_approved": [],
    "scene_draft_rollback": [],
    "chapter_draft_generated": [],
    "chapter_draft_changed": [],
    "chapter_draft_approved": [],
    "chapter_draft_rollback": [],
    "draft_continuity_failed": ["draft_continuity"],
    # Editorial provider calls are explicit author actions. These events update
    # queues and projections without replaying editorial agents in later cycles.
    "editorial_report_created": [],
    "revision_branch_created": [],
    "revision_version_created": [],
    "revision_branch_changed": [],
    # Phase 3B actions update projections but never replay governance agents.
    "manuscript_created": [],
    "manuscript_assembled": [],
    "manuscript_status_changed": [],
    "manuscript_rollback": [],
    "manuscript_reviewed": [],
    "canon_promoted": [],
    "canon_record_changed": [],
    "canon_validated": [],
    "canon_reviewed": [],
    "story_audit_completed": [],
}

BEGINNER_STEP_DOMAINS: Dict[str, List[str]] = {
    "story_idea": ["concept"],
    "main_character": ["character", "relationship", "arc"],
    "world": ["world", "faction", "arc"],
    "conflict": ["concept", "arc", "theme"],
    "first_decision": [
        "concept", "character", "world", "relationship", "theme",
        "mystery", "arc", "timeline", "knowledge", "arc_development",
    ],
    "first_arc": ["arc", "timeline", "arc_development"],
    "first_scene": ["scene_plan", "chapter_plan", "arc_development"],
}

WORKSPACE_AREA_DOMAINS: Dict[str, List[str]] = {
    "character": ["character", "relationship", "arc"],
    "world": ["world", "faction", "arc"],
    "timeline": ["timeline", "arc"],
    "power": ["power", "character", "arc"],
    "relationship": ["relationship", "character"],
    "theme": ["theme", "arc"],
    "plot_thread": ["concept", "arc"],
    "arc": ["arc", "timeline", "arc_development"],
    "mystery": ["mystery", "arc", "foreshadow"],
    "faction": ["faction", "relationship", "world"],
    "scene": ["scene_plan", "arc_development"],
}


def _unique(values: Iterable[str]) -> List[str]:
    seen = set()
    ordered = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _domains_from_text(text: str) -> List[str]:
    normalized = (text or "").lower()
    return [
        domain
        for domain, keywords in DOMAIN_KEYWORDS.items()
        if any(keyword in normalized for keyword in keywords)
    ]


def _serialize(document: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in document.items():
        output_key = "id" if key == "_id" else key
        if isinstance(value, ObjectId):
            result[output_key] = str(value)
        elif isinstance(value, datetime):
            result[output_key] = value.isoformat()
        elif isinstance(value, list):
            result[output_key] = [
                str(item) if isinstance(item, ObjectId) else item for item in value
            ]
        else:
            result[output_key] = value
    return result


class OrchestrationServiceV2:
    async def _automatic_missing_domains(
        self,
        db,
        *,
        project_id: str,
        project: Dict[str, Any],
    ) -> Tuple[List[str], List[str]]:
        """Find planning areas NovelForge can develop without author busywork.

        This is intentionally an inventory of missing planning, not a second
        readiness engine. Deterministic domain services still own readiness and
        approval. The inventory only gives the orchestrator useful work for an
        automatic Advance Project run after the initial event has been handled.
        """
        pid = ObjectId(project_id)
        entities: List[str] = []
        domains: List[str] = []

        async def missing(collection_name: str, domain: str) -> bool:
            exists = await db[collection_name].find_one(
                {"project_id": pid, "authority_status": {"$ne": "stale"}},
                {"_id": 1},
            )
            if exists:
                return False
            entities.append(f"missing:{collection_name}")
            domains.append(domain)
            return True

        await missing("story_visions", "concept")
        characters_missing = await missing("character_bibles", "character")
        await missing("world_bibles", "world")
        await missing("theme_registry", "theme")
        arcs_missing = await missing("story_arcs", "arc")
        await missing("plot_threads", "concept")
        await missing("timeline_entries", "timeline")

        character_count = 0 if characters_missing else await db.character_bibles.count_documents(
            {"project_id": pid, "authority_status": {"$ne": "stale"}}, limit=2
        )
        if character_count >= 2:
            await missing("relationship_graphs", "relationship")

        story_text = " ".join(
            str(project.get(field) or "")
            for field in ("genre", "premise", "idea_dump", "world_notes", "plot_notes")
        ).lower()
        if any(term in story_text for term in ("magic", "power", "ability", "supernatural", "fantasy", "cultivation")):
            await missing("power_systems", "power")
        if any(term in story_text for term in ("faction", "guild", "empire", "kingdom", "court", "organization", "army")):
            await missing("factions", "faction")
        if any(term in story_text for term in ("mystery", "secret", "clue", "reveal", "thriller", "crime")):
            await missing("mystery_registry", "mystery")

        if not arcs_missing:
            current_arc = await db.story_arcs.find_one(
                {
                    "project_id": pid,
                    "authority_status": {"$ne": "stale"},
                    "development_status": {"$nin": ["completed", "archived"]},
                },
                sort=[("focus_role", 1), ("order", 1)],
            )
            if current_arc:
                arc_id = str(current_arc.get("arc_id") or "")
                if not await db.arc_checklists.find_one(
                    {"project_id": pid, "arc_id": arc_id}, {"_id": 1}
                ):
                    entities.append(f"missing:arc_checklists:{arc_id}")
                    domains.append("arc_development")
                if not await db.chapter_plans.find_one(
                    {"project_id": pid, "arc_id": arc_id}, {"_id": 1}
                ):
                    entities.append(f"missing:chapter_plans:{arc_id}")
                    domains.append("chapter_plan")
                elif bool(current_arc.get("drafting_eligible")) and not await db.scene_plans.find_one(
                    {"project_id": pid, "arc_id": arc_id}, {"_id": 1}
                ):
                    entities.append(f"missing:scene_plans:{arc_id}")
                    domains.append("automatic_scene_planning")

        await missing("story_readiness", "readiness")
        return _unique(entities), _unique(domains)

    async def _changes(
        self,
        db,
        *,
        project_id: str,
        project: Dict[str, Any],
        state: Dict[str, Any],
    ) -> Tuple[str, List[str], List[str], List[str]]:
        pid = ObjectId(project_id)
        previous_plan = await db.orchestration_plans.find_one(
            {"project_id": pid},
            sort=[("created_at", -1)],
        )
        event_query: Dict[str, Any] = {"project_id": pid}
        if previous_plan and previous_plan.get("created_at"):
            event_query["created_at"] = {"$gt": previous_plan["created_at"]}
        events = await db.project_events.find(event_query).sort("created_at", 1).to_list(
            length=1000
        )

        changed_entities: List[str] = []
        domains: List[str] = []
        direct_agents: List[str] = []
        trigger_type = "manual"

        for message in state.get("new_messages") or []:
            content = str(message.get("content") or "")
            if message.get("role") == "user":
                trigger_type = "message"
                changed_entities.append(f"message:{message.get('id') or 'new'}")
            elif message.get("message_type") == "queued_task":
                changed_entities.append(f"queued_task:{message.get('id') or 'new'}")
                if message.get("agent_name") in PLANNING_AGENTS:
                    direct_agents.append(message["agent_name"])
            domains.extend(_domains_from_text(content))

        for event in events:
            event_type = str(event.get("event_type") or "")
            payload = event.get("payload") or {}
            if event_type == "project_created":
                changed_entities.append("project:created")
                domains.append("concept")
                for field, field_domains in FIELD_DOMAINS.items():
                    if project.get(field):
                        changed_entities.append(f"project.{field}")
                        domains.extend(field_domains)
            elif event_type == "project_updated":
                for field in payload.get("changed_fields") or []:
                    changed_entities.append(f"project.{field}")
                    domains.extend(FIELD_DOMAINS.get(field, {"concept"}))
            elif event_type == "story_vision_updated":
                for field in payload.get("changed_fields") or []:
                    changed_entities.append(f"story_vision.{field}")
                    domains.extend(FIELD_DOMAINS.get(field, {"concept"}))
            elif event_type == "user_message":
                trigger_type = "message"
                changed_entities.append(f"message:{payload.get('message_id') or event['_id']}")
            elif event_type == "question_resolved":
                trigger_type = "answer"
                changed_entities.append(
                    f"question:{payload.get('question_id') or event['_id']}"
                )
                question_id = payload.get("question_id")
                if question_id and ObjectId.is_valid(question_id):
                    question = await db.questions.find_one(
                        {"_id": ObjectId(question_id), "project_id": pid}
                    )
                    if question:
                        domains.extend(_domains_from_text(question.get("text", "")))
                domains.append("question")
            elif event_type == "discussion_decision":
                action = str(payload.get("action") or "")
                trigger_type = "approval" if action == "approve" else (
                    "rejection" if action in {"reject", "modify"} else "manual"
                )
                changed_entities.append(
                    f"proposal:{payload.get('proposal_id') or event['_id']}"
                )
                proposal_id = payload.get("proposal_id")
                if proposal_id and ObjectId.is_valid(proposal_id):
                    proposal = await db.discussion_messages.find_one(
                        {"_id": ObjectId(proposal_id), "project_id": pid}
                    )
                    if proposal:
                        domains.extend(_domains_from_text(
                            " ".join(
                                [
                                    str(proposal.get("summary") or ""),
                                    str(proposal.get("content") or ""),
                                    " ".join(proposal.get("references") or []),
                                ]
                            )
                        ))
                        author = proposal.get("author")
                        if author in PLANNING_AGENTS:
                            direct_agents.append(author)
            elif event_type == "beginner_step_updated":
                step_id = str(payload.get("step_id") or "")
                action = str(payload.get("action") or "")
                changed_entities.append(f"beginner_step:{step_id}:{action}")
                domains.extend(BEGINNER_STEP_DOMAINS.get(step_id, ["concept"]))
            elif event_type == "workspace_entry_created":
                area = str(payload.get("area") or "")
                changed_entities.append(
                    f"workspace_entry:{area}:{payload.get('record_id') or event['_id']}"
                )
                domains.extend(WORKSPACE_AREA_DOMAINS.get(area, ["concept"]))
            elif event_type in {"decision_changed", "question_reopened"}:
                question_id = str(payload.get("question_id") or "")
                changed_entities.append(f"{event_type}:{question_id or event['_id']}")
                domains.extend(["question", "knowledge", "concept", "arc"])
                if question_id and ObjectId.is_valid(question_id):
                    question = await db.questions.find_one(
                        {"_id": ObjectId(question_id), "project_id": pid}
                    )
                    if question:
                        domains.extend(
                            _domains_from_text(
                                " ".join(
                                    str(question.get(field) or "")
                                    for field in ("text", "answer", "decision")
                                )
                            )
                        )
            elif event_type == "shared_narrative_context_updated":
                context_id = str(payload.get("context_id") or "")
                changed_entities.append(f"shared_context:{context_id or event['_id']}")
                domains.append("knowledge")
                context = await db.shared_narrative_context.find_one(
                    {"project_id": pid, "context_id": context_id}
                ) if context_id else None
                if context:
                    domains.extend(
                        _domains_from_text(
                            " ".join(
                                str(context.get(field) or "")
                                for field in ("content", "subject", "field", "value")
                            )
                        )
                    )
            elif event_type in {"canon_promoted", "canon_record_changed", "canon_proposal_reviewed"}:
                changed_entities.append(
                    f"{event_type}:{payload.get('proposal_id') or payload.get('record_id') or event['_id']}"
                )
                domains.append("knowledge")
            elif event_type in EVENT_DOMAINS:
                payload_id = (
                    payload.get("item_id")
                    or payload.get("arc_id")
                    or payload.get("entry_id")
                    or payload.get("artifact_id")
                    or payload.get("dependency_id")
                    or payload.get("chapter_plan_id")
                    or payload.get("scene_id")
                    or payload.get("evolution_id")
                    or payload.get("chain_node_id")
                    or event["_id"]
                )
                changed_entities.append(f"{event_type}:{payload_id}")
                domains.extend(EVENT_DOMAINS[event_type])

        if state.get("automatic_development"):
            missing_entities, missing_domains = await self._automatic_missing_domains(
                db,
                project_id=project_id,
                project=project,
            )
            changed_entities.extend(missing_entities)
            domains.extend(missing_domains)
            pending_invalidations = await db.planning_invalidations.find(
                {"project_id": pid, "status": "pending"},
                {"_id": 1, "required_agents": 1},
            ).to_list(length=500)
            for invalidation in pending_invalidations:
                changed_entities.append(f"planning_invalidation:{invalidation['_id']}")
                direct_agents.extend(
                    agent
                    for agent in invalidation.get("required_agents") or []
                    if agent in PLANNING_AGENTS
                )
        if not previous_plan and not changed_entities:
            changed_entities.append("project:initial_state")
            domains.append("concept")
            for field, field_domains in FIELD_DOMAINS.items():
                if project.get(field):
                    domains.extend(field_domains)

        return (
            trigger_type,
            _unique(changed_entities),
            _unique(domains),
            _unique(direct_agents),
        )

    def _traverse(
        self,
        domains: List[str],
        direct_agents: List[str],
        *,
        max_depth: int,
        expand_impacts: bool,
    ) -> Tuple[List[str], Dict[str, str], Dict[str, int], List[Dict[str, str]]]:
        queue: deque[Tuple[str, int, str]] = deque()
        for domain in domains:
            for agent_name in DOMAIN_AGENT_SEEDS.get(domain, []):
                queue.append((agent_name, 0, f"{domain} change requires {agent_name}"))
        for agent_name in direct_agents:
            queue.append((agent_name, 0, "Queued work explicitly targets this agent"))

        ordered: List[str] = []
        reasons: Dict[str, str] = {}
        depths: Dict[str, int] = {}
        edges: List[Dict[str, str]] = []
        while queue:
            agent_name, depth, reason = queue.popleft()
            if agent_name not in PLANNING_AGENTS or depth > max_depth:
                continue
            if agent_name in depths and depths[agent_name] <= depth:
                continue
            if agent_name not in ordered:
                ordered.append(agent_name)
            depths[agent_name] = depth
            reasons.setdefault(agent_name, reason)
            if not expand_impacts or depth >= max_depth:
                continue
            for impacted in AGENT_IMPACT_GRAPH.get(agent_name, []):
                edges.append({"from": agent_name, "to": impacted})
                queue.append(
                    (
                        impacted,
                        depth + 1,
                        f"Impacted by {agent_name} through the dependency graph",
                    )
                )
        return ordered, reasons, depths, edges

    async def create_explicit_plan(
        self,
        db,
        *,
        project_id: str,
        agent_name: str,
        changed_entity: str,
        affected_domain: str,
        reason: str,
    ) -> Dict[str, Any]:
        if agent_name not in PLANNING_AGENTS:
            raise ValueError(f"Unknown orchestrated agent {agent_name}")
        pid = ObjectId(project_id)
        settings = await orchestration_engine.get_settings(db)
        assignments = {
            assignment.agent_name: assignment
            for assignment in await orchestration_engine.get_assignments(db)
        }
        assignment = assignments.get(agent_name)
        if assignment and not assignment.enabled:
            raise ValueError(f"{agent_name} is disabled")
        call_limit = max(
            0,
            min(int(settings.max_agent_calls_per_cycle), MAX_AGENT_CALLS_PER_CYCLE),
        )
        if call_limit < 1:
            raise ValueError("max_agent_calls_per_cycle prevents draft generation")
        provider = (assignment.provider if assignment else "") or settings.default_provider
        model = (assignment.model if assignment else "") or settings.default_model
        token_estimate = 6000 + min(
            int(assignment.max_tokens if assignment else 4096),
            3000,
        )
        estimated_cost = estimate_cost(token_estimate, provider, model)
        cycle_budget = max(0.0, float(settings.max_cycle_cost_usd))
        if cycle_budget == 0.0 or estimated_cost > cycle_budget:
            raise ValueError(
                f"Estimated ${estimated_cost:.6f} call would exceed "
                f"max_cycle_cost_usd=${cycle_budget:.6f}"
            )
        latest_cycle = await db.cycles.find_one(
            {"project_id": pid},
            sort=[("cycle_number", -1)],
        )
        now = datetime.utcnow()
        selection_reasons = {
            name: (
                reason
                if name == agent_name
                else f"Explicit {affected_domain} request does not require {name}"
            )
            for name in PLANNING_AGENTS
        }
        skipped = [name for name in PLANNING_AGENTS if name != agent_name]
        plan = {
            "project_id": pid,
            "cycle_number": int((latest_cycle or {}).get("cycle_number") or 0),
            "trigger_type": "manual",
            "changed_entities": [changed_entity],
            "affected_domains": [affected_domain],
            "selected_agents": [agent_name],
            "skipped_agents": skipped,
            "selection_reasons": selection_reasons,
            "execution_graph": {
                "nodes": [{"agent_name": agent_name, "depth": 0, "selected": True}],
                "edges": [],
            },
            "limits": {
                "max_agent_calls_per_cycle": call_limit,
                "max_orchestration_depth": min(
                    int(settings.max_orchestration_depth),
                    MAX_ORCHESTRATION_DEPTH,
                ),
                "max_cycle_cost_usd": cycle_budget,
            },
            "estimated_cost_usd": round(estimated_cost, 6),
            "actual_cost_usd": 0.0,
            "actual_agent_calls": 0,
            "stop_reason": None,
            "created_at": now,
            "started_at": now,
            "status": "running",
        }
        inserted = await db.orchestration_plans.insert_one(plan)
        plan["_id"] = inserted.inserted_id
        await db.orchestration_tasks.insert_many(
            [
                {
                    "plan_id": inserted.inserted_id,
                    "agent_name": name,
                    "status": "running" if name == agent_name else "skipped",
                    "reason": selection_reasons[name],
                    "order": 0 if name == agent_name else None,
                    "started_at": now if name == agent_name else None,
                    "completed_at": now if name != agent_name else None,
                }
                for name in PLANNING_AGENTS
            ]
        )
        return plan

    async def finalize_explicit_plan(
        self,
        db,
        *,
        plan_id: ObjectId,
        agent_name: str,
        status: str,
        actual_cost_usd: float = 0.0,
        error: str | None = None,
    ) -> None:
        now = datetime.utcnow()
        task_status = "completed" if status == "completed" else "failed"
        await db.orchestration_tasks.update_one(
            {"plan_id": plan_id, "agent_name": agent_name},
            {
                "$set": {
                    "status": task_status,
                    "completed_at": now,
                    **({"reason": error} if error else {}),
                }
            },
        )
        await db.orchestration_plans.update_one(
            {"_id": plan_id},
            {
                "$set": {
                    "status": status,
                    "completed_at": now,
                    "actual_agent_calls": 1 if status == "completed" else 0,
                    "actual_cost_usd": round(float(actual_cost_usd), 6),
                    **({"error": error} if error else {}),
                }
            },
        )

    async def create_plan(
        self,
        db,
        *,
        project_id: str,
        run_id: str,
        cycle_id: str,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        project = await db.projects.find_one({"_id": pid}) or {}
        settings = await orchestration_engine.get_settings(db)
        assignments = {
            assignment.agent_name: assignment
            for assignment in await orchestration_engine.get_assignments(db)
        }
        trigger_type, changed_entities, domains, direct_agents = await self._changes(
            db,
            project_id=project_id,
            project=project,
            state=state,
        )
        depth_limit = max(
            0,
            min(
                int(getattr(settings, "max_orchestration_depth", MAX_ORCHESTRATION_DEPTH)),
                MAX_ORCHESTRATION_DEPTH,
            ),
        )
        ordered, reasons, depths, edges = self._traverse(
            domains,
            direct_agents,
            max_depth=depth_limit,
            expand_impacts=bool(settings.enable_dynamic_routing),
        )

        call_limit = max(
            0,
            min(
                int(settings.max_agent_calls_per_cycle),
                MAX_AGENT_CALLS_PER_CYCLE,
            ),
        )
        cycle_budget = max(0.0, float(settings.max_cycle_cost_usd))
        selected: List[str] = []
        estimated_cost = 0.0
        skip_reasons: Dict[str, str] = {}

        for agent_name in ordered:
            assignment = assignments.get(agent_name)
            if assignment and not assignment.enabled:
                skip_reasons[agent_name] = "Agent is disabled in execution settings"
                continue
            if len(selected) >= call_limit:
                skip_reasons[agent_name] = (
                    f"Skipped by max_agent_calls_per_cycle={call_limit}"
                )
                continue
            provider = (
                (assignment.provider if assignment else "")
                or settings.default_provider
            )
            model = (
                (assignment.model if assignment else "")
                or settings.default_model
            )
            token_estimate = 6000 + min(
                int((assignment.max_tokens if assignment else 4096)),
                3000,
            )
            agent_cost = estimate_cost(token_estimate, provider, model)
            if cycle_budget == 0.0 or estimated_cost + agent_cost > cycle_budget:
                skip_reasons[agent_name] = (
                    f"Estimated ${agent_cost:.6f} call would exceed "
                    f"max_cycle_cost_usd=${cycle_budget:.6f}"
                )
                continue
            selected.append(agent_name)
            estimated_cost += agent_cost

        selection_reasons: Dict[str, str] = {}
        for agent_name in PLANNING_AGENTS:
            if agent_name in selected:
                selection_reasons[agent_name] = reasons.get(
                    agent_name, "Selected by impact graph"
                )
            elif agent_name in skip_reasons:
                selection_reasons[agent_name] = skip_reasons[agent_name]
            else:
                domain = AGENT_PRIMARY_DOMAIN.get(agent_name, "relevant")
                selection_reasons[agent_name] = (
                    f"No {domain}-related changes detected"
                )

        now = datetime.utcnow()
        skipped = [name for name in PLANNING_AGENTS if name not in selected]
        stop_reason = (
            "NO_CHANGE_TERMINATION: no meaningful changes detected"
            if not changed_entities and not domains and not direct_agents
            else None
        )
        plan = {
            "project_id": pid,
            # Phase 1a intentionally allows one primary plan per user-visible
            # run. Automatic continuation cycles keep their own plan history
            # under root_run_id without weakening that established index.
            "root_run_id": ObjectId(run_id),
            "cycle_id": ObjectId(cycle_id),
            "cycle_number": int(state.get("cycle_number") or 1),
            "trigger_type": trigger_type,
            "changed_entities": changed_entities,
            "affected_domains": domains,
            "selected_agents": selected,
            "skipped_agents": skipped,
            "selection_reasons": selection_reasons,
            "execution_graph": {
                "nodes": [
                    {
                        "agent_name": name,
                        "depth": depths.get(name),
                        "selected": name in selected,
                    }
                    for name in ordered
                ],
                "edges": edges,
            },
            "limits": {
                "max_agent_calls_per_cycle": call_limit,
                "max_orchestration_depth": depth_limit,
                "max_cycle_cost_usd": cycle_budget,
            },
            "estimated_cost_usd": round(estimated_cost, 6),
            "actual_cost_usd": 0.0,
            "actual_agent_calls": 0,
            "stop_reason": stop_reason,
            "created_at": now,
            "status": "pending",
        }
        if state.get("primary_run_plan", True):
            plan["run_id"] = ObjectId(run_id)
        result = await db.orchestration_plans.insert_one(plan)
        plan["_id"] = result.inserted_id
        if PLANNING_AGENTS:
            await db.orchestration_tasks.insert_many(
                [
                    {
                        "plan_id": result.inserted_id,
                        "agent_name": agent_name,
                        "status": "pending" if agent_name in selected else "skipped",
                        "reason": selection_reasons[agent_name],
                        "order": (
                            selected.index(agent_name)
                            if agent_name in selected
                            else None
                        ),
                        "started_at": None,
                        "completed_at": now if agent_name not in selected else None,
                    }
                    for agent_name in PLANNING_AGENTS
                ]
            )
        return plan

    async def execute_plan(
        self,
        db,
        *,
        project_id: str,
        run_id: str,
        cycle_id: str,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        plan = await self.create_plan(
            db,
            project_id=project_id,
            run_id=run_id,
            cycle_id=cycle_id,
            state=state,
        )
        plan_id = plan["_id"]
        selected = plan["selected_agents"]
        await db.runs.update_one(
            {"_id": ObjectId(run_id), "project_id": ObjectId(project_id)},
            {"$set": {
                "metadata.planned_agents": selected,
                "metadata.completed_agents": [],
                "metadata.progress_completed": 0,
                "metadata.progress_total": len(selected),
                "metadata.author_phase": "Choosing the right story specialists" if not selected else "Developing the story plan",
                "metadata.active_plan_id": plan_id,
            }},
        )
        await db.orchestration_plans.update_one(
            {"_id": plan_id},
            {"$set": {"status": "running", "started_at": datetime.utcnow()}},
        )
        if not selected:
            now = datetime.utcnow()
            await db.orchestration_plans.update_one(
                {"_id": plan_id},
                {
                    "$set": {
                        "status": "completed",
                        "completed_at": now,
                        "stop_reason": plan.get("stop_reason")
                        or "No executable agents remained after limits",
                    }
                },
            )
            return {
                "agents_run": [],
                "artifacts": {},
                "story_bible_version": None,
                "plan_id": str(plan_id),
                "actual_cost_usd": 0.0,
            }

        from app.services.narrative_studio import narrative_studio_service

        try:
            current_arc = await db.story_arcs.find_one(
                {
                    "project_id": ObjectId(project_id),
                    "authority_status": {"$ne": "stale"},
                    "focus_role": "current",
                    "development_status": {"$nin": ["completed", "archived"]},
                },
                sort=[("order", 1)],
            )
            if current_arc:
                state["target_arc_id"] = current_arc.get("arc_id")
            result = await narrative_studio_service.run(
                db,
                project_id=project_id,
                state=state,
                run_id=run_id,
                agent_names=selected,
                plan_id=str(plan_id),
                max_cycle_cost_usd=float(
                    plan["limits"]["max_cycle_cost_usd"]
                ),
                max_agent_calls=int(
                    plan["limits"]["max_agent_calls_per_cycle"]
                ),
            )
            now = datetime.utcnow()
            agents_run = result.get("agents_run") or []
            await db.orchestration_tasks.update_many(
                {
                    "plan_id": plan_id,
                    "status": "pending",
                },
                {
                    "$set": {
                        "status": "skipped",
                        "reason": result.get("stop_reason")
                        or "Execution stopped before this task",
                        "completed_at": now,
                    }
                },
            )
            await db.orchestration_plans.update_one(
                {"_id": plan_id},
                {
                    "$set": {
                        "status": "completed",
                        "completed_at": now,
                        "actual_agent_calls": len(agents_run),
                        "actual_cost_usd": round(
                            float(result.get("actual_cost_usd") or 0), 6
                        ),
                        "stop_reason": result.get("stop_reason"),
                    }
                },
            )
            return {**result, "plan_id": str(plan_id)}
        except Exception as exc:
            now = datetime.utcnow()
            await db.orchestration_tasks.update_many(
                {"plan_id": plan_id, "status": "pending"},
                {
                    "$set": {
                        "status": "skipped",
                        "reason": "Plan failed before task execution",
                        "completed_at": now,
                    }
                },
            )
            await db.orchestration_plans.update_one(
                {"_id": plan_id},
                {
                    "$set": {
                        "status": "failed",
                        "completed_at": now,
                        "error": str(exc),
                    }
                },
            )
            raise

    async def get_plan(self, db, plan: Dict[str, Any]) -> Dict[str, Any]:
        tasks = await db.orchestration_tasks.find(
            {"plan_id": plan["_id"]}
        ).sort([("order", 1), ("agent_name", 1)]).to_list(length=100)
        serialized = _serialize(plan)
        serialized["tasks"] = [_serialize(task) for task in tasks]
        return serialized


orchestration_service_v2 = OrchestrationServiceV2()
