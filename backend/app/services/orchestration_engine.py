"""Adaptive AI orchestration around the persistent writers' room."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal
import logging

from bson import ObjectId
from pydantic import BaseModel

from app.services.context_engine import context_engine
from app.services.memory_compaction_service import memory_compaction_service
from app.services.observability_service import estimate_cost, observability_service
from app.services.provider_gateway import provider_gateway
from app.services.model_registry_service import model_registry_service, normalize_provider
from app.services.provider_recommendation_service import provider_recommendation_service
from app.services.settings_service import AGENT_NAMES, settings_service
from app.core.config import settings as app_config

logger = logging.getLogger(__name__)

class AIExecutionSettings(BaseModel):
    execution_mode: Literal["mock", "hybrid", "full"] = "full"
    default_provider: str = "gemini"
    default_model: str = ""
    enable_streaming: bool = True
    enable_reflection_loops: bool = True
    enable_dynamic_routing: bool = True
    max_context_tokens: int = 120000
    max_cycle_cost_usd: float = 2.0
    max_agent_calls_per_cycle: int = 10
    max_orchestration_depth: int = 5
    provider_requests_per_minute: int = 5
    max_reflection_loops: int = 2


class AgentModelAssignment(BaseModel):
    agent_name: str
    provider: str = "gemini"
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    enabled: bool = True
    use_mock_in_hybrid: bool = False


DEFAULT_ASSIGNMENTS = [
    AgentModelAssignment(agent_name=name).model_dump()
    for name in AGENT_NAMES
]


PRESETS: Dict[str, Dict[str, Any]] = {
    "cheap": {"default_provider": "groq", "default_model": "llama-3.1-8b-instant", "max_cycle_cost_usd": 0.25},
    "creative": {"default_provider": "gemini", "default_model": "gemini-2.5-flash", "max_cycle_cost_usd": 1.0},
    "balanced": {"default_provider": "openrouter", "default_model": "anthropic/claude-3.5-sonnet", "max_cycle_cost_usd": 1.5},
    "drafting": {"default_provider": "openai", "default_model": "gpt-4o", "max_cycle_cost_usd": 2.0},
    "continuity": {"default_provider": "anthropic", "default_model": "claude-3-5-sonnet-latest", "max_cycle_cost_usd": 1.25},
}


class OrchestrationEngine:
    async def get_settings(self, db) -> AIExecutionSettings:
        return AIExecutionSettings(**await settings_service.get_execution_settings())

    async def update_settings(self, db, payload: Dict[str, Any]) -> AIExecutionSettings:
        current = (await self.get_settings(db)).model_dump()
        current.update(payload)
        current["default_provider"] = normalize_provider(current.get("default_provider", "mock"))
        if not app_config.use_mock_llm and (
            current.get("execution_mode") == "mock"
            or current["default_provider"] == "mock"
            or current.get("default_model") == "mock-narrative-intelligence"
        ):
            raise ValueError("Mock AI execution is disabled")
        await model_registry_service.validate_model(current["default_provider"], current.get("default_model", ""))
        settings = AIExecutionSettings(**current)
        await settings_service.save_execution_settings(settings.model_dump())
        return settings

    async def get_assignments(self, db) -> List[AgentModelAssignment]:
        return [AgentModelAssignment(**item) for item in await settings_service.get_agent_assignments()]

    async def update_assignments(self, db, payload: List[Dict[str, Any]]) -> List[AgentModelAssignment]:
        normalized_assignments: List[Dict[str, Any]] = []
        for item in payload:
            item = {**item, "provider": normalize_provider(item.get("provider", "mock"))}
            if not app_config.use_mock_llm and (
                item.get("provider") == "mock"
                or item.get("model") == "mock-narrative-intelligence"
            ):
                raise ValueError("Mock agent assignments are disabled")
            if item.get("enabled", True):
                await model_registry_service.validate_model(item.get("provider", "mock"), item.get("model", ""))
            assignment = AgentModelAssignment(**item)
            normalized_assignments.append(assignment.model_dump())
        await settings_service.save_agent_assignments(normalized_assignments)
        return await self.get_assignments(db)

    async def apply_preset(self, db, preset: str) -> AIExecutionSettings:
        settings = PRESETS.get(preset.lower())
        if not settings:
            raise ValueError(f"Unknown preset: {preset}")
        return await self.update_settings(db, settings)

    async def run_cycle_observability(
        self,
        db,
        *,
        project_id: str,
        cycle_number: int,
        selected_agents: List[str],
        query: str,
    ) -> Dict[str, Any]:
        settings = await self.get_settings(db)
        assignment_list = await self.get_assignments(db)
        assignments = {a.agent_name: a for a in assignment_list}
        logger.info("Orchestration execution_mode before workflow observability: %s", settings.execution_mode)
        logger.info(
            "Orchestration agent assignments: %s",
            [
                {key: value for key, value in item.model_dump().items() if key in {"agent_name", "provider", "model", "enabled", "use_mock_in_hybrid"}}
                for item in assignment_list
            ],
        )
        now = datetime.utcnow()
        planned = selected_agents if settings.enable_dynamic_routing else AGENT_NAMES[:6]
        planned = [agent for agent in planned if assignments.get(agent, AgentModelAssignment(agent_name=agent)).enabled]
        planned = planned[: settings.max_agent_calls_per_cycle]

        records: List[Dict[str, Any]] = []
        delegated: List[str] = []
        total_tokens = 0
        total_cost = 0.0
        reflection_loops = 0

        for agent_name in planned:
            assignment = assignments.get(agent_name, AgentModelAssignment(agent_name=agent_name, provider=settings.default_provider, model=settings.default_model))
            assigned_provider = normalize_provider(assignment.provider or settings.default_provider)
            assigned_model = assignment.model or settings.default_model
            provider = assigned_provider
            model = assigned_model
            if settings.execution_mode == "mock":
                provider = "mock"
                model = "mock-narrative-intelligence"
            elif settings.execution_mode == "full" and provider == "mock":
                provider = normalize_provider(settings.default_provider)
                model = settings.default_model

            packet = await context_engine.build_context_packet(
                db,
                project_id=project_id,
                agent_name=agent_name,
                task=query or f"{agent_name} cycle update",
                cycle_number=cycle_number,
                max_context_tokens=settings.max_context_tokens,
            )
            estimated_cost = estimate_cost(packet.token_estimate + assignment.max_tokens, provider, model)
            if settings.max_cycle_cost_usd == 0.0 or total_cost + estimated_cost > settings.max_cycle_cost_usd:
                records.append({"agent_name": agent_name, "status": "skipped_budget", "estimated_cost_usd": estimated_cost, "reason": "cycle budget would be exceeded"})
                continue

            cognition = f"{agent_name}: reviewing {len(packet.retrieved_memory)} retrieved memories with {packet.token_estimate} context tokens."
            await db.cognition_events.insert_one({
                "project_id": ObjectId(project_id),
                "cycle_number": cycle_number,
                "agent_name": agent_name,
                "content": cognition,
                "created_at": datetime.utcnow(),
            })
            await db.timeline_messages.insert_one({
                "project_id": ObjectId(project_id),
                "cycle_number": cycle_number,
                "role": "agent",
                "agent_name": agent_name,
                "message_type": "summary",
                "content": cognition,
                "created_at": datetime.utcnow(),
            })

            recommendation = await provider_recommendation_service.recommend(
                task_type=self._task_type_for_agent(agent_name),
                budget_preference="cheap" if settings.max_cycle_cost_usd <= 0.5 else "balanced",
                context_tokens=packet.token_estimate,
            )
            fallbacks = [
                {"provider": recommendation["provider"], "model": recommendation["model"]},
                {"provider": "openrouter", "model": "google/gemma-3-27b-it:free"},
            ]
            fallbacks = [
                item for item in fallbacks
                if normalize_provider(item["provider"]) != "mock" and item["model"] != model
            ]
            result = await provider_gateway.generate_with_failover(
                db,
                [{"role": "system", "content": "You are an adaptive NovelForge narrative intelligence agent."},
                 {"role": "user", "content": packet.model_dump_json()}],
                provider=provider,
                model=model,
                fallbacks=fallbacks,
                temperature=assignment.temperature,
                max_tokens=assignment.max_tokens,
                agent_name=agent_name,
            )
            tokens = int(result.get("tokens_used", packet.token_estimate))
            actual_provider = result.get("provider", provider)
            actual_model = result.get("model", model)
            cost = estimate_cost(tokens, actual_provider, actual_model)
            total_tokens += tokens
            total_cost += cost
            recs = (result.get("parsed") or {}).get("recommended_next_agents") or []
            delegated.extend([name for name in recs if name in AGENT_NAMES and name not in planned and name not in delegated])
            records.append({
                "agent_name": agent_name,
                "status": "completed",
                "assigned_provider": assigned_provider,
                "assigned_model": assigned_model,
                "provider": actual_provider,
                "model": actual_model,
                "token_estimate": packet.token_estimate,
                "tokens_used": tokens,
                "cost_usd": cost,
                "retrieved_memory_count": len(packet.retrieved_memory),
                "recommended_next_agents": recs,
                "fallback_used": result.get("fallback_used", False),
                "attempts": result.get("attempts", 1),
            })
            logger.info(
                "\nAGENT EXECUTION\n\nagent=%s\nexecution_mode=%s\nassigned_provider=%s\nassigned_model=%s\nactual_provider=%s\nactual_model=%s\nfallback_used=%s\n",
                agent_name,
                settings.execution_mode,
                assigned_provider,
                assigned_model,
                actual_provider,
                actual_model,
                result.get("fallback_used", False),
            )

        if settings.enable_reflection_loops and delegated:
            reflection_loops = min(settings.max_reflection_loops, len(delegated))
            for agent_name in delegated[:reflection_loops]:
                await db.cognition_events.insert_one({
                    "project_id": ObjectId(project_id),
                    "cycle_number": cycle_number,
                    "agent_name": agent_name,
                    "content": f"{agent_name}: delegated reflection pass requested by prior agent output.",
                    "created_at": datetime.utcnow(),
                })

        if cycle_number > 2:
            await memory_compaction_service.compact_project_memory(db, project_id, before_cycle=cycle_number - 1)

        run_doc = {
            "project_id": ObjectId(project_id),
            "cycle_number": cycle_number,
            "selected_agents": planned,
            "routing_reason": "Dynamic cognitive routing selected agents from latest user intent and changed artifacts.",
            "agent_records": records,
            "delegated_agents": delegated[:reflection_loops],
            "reflection_loops": reflection_loops,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 6),
            "budget_limit_usd": settings.max_cycle_cost_usd,
            "execution_mode": settings.execution_mode,
            "created_at": now,
        }
        await db.orchestration_runs.insert_one(run_doc)
        await db.cycle_costs.insert_one({
            "project_id": ObjectId(project_id),
            "cycle_number": cycle_number,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 6),
            "created_at": now,
        })
        await observability_service.record_observation(db, project_id, cycle_number, "routing_decision", run_doc)
        return run_doc

    def _task_type_for_agent(self, agent_name: str) -> str:
        mapping = {
            "IntentRouterAgent": "routing",
            "BrainstormAgent": "brainstorming",
            "CharacterAgent": "character",
            "CriticAgent": "critic",
            "ContinuityAgent": "continuity",
            "ThemeAgent": "themes",
            "NarrativeDirectorAgent": "routing",
            "ArcArchitectAgent": "architect",
            "PowerSystemAgent": "worldbuilding",
            "CharacterJourneyAgent": "character",
            "PacingAgent": "continuity",
            "MysteryAgent": "continuity",
            "RelationshipAgent": "character",
            "FactionAgent": "worldbuilding",
            "StoryArchitectAgent": "architect",
            "ReadinessAgent": "continuity",
            "KnowledgeAgent": "continuity",
            "StoryDevelopmentAgent": "architect",
            "SceneWriterAgent": "drafting",
            "ChapterAssemblerAgent": "drafting",
            "EditorAgent": "continuity",
            "DialogueAgent": "continuity",
            "RevisionAgent": "drafting",
            "ManuscriptAgent": "continuity",
            "CanonAgent": "continuity",
        }
        return mapping.get(agent_name, "routing")


orchestration_engine = OrchestrationEngine()
