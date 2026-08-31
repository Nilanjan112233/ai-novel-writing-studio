from abc import ABC, abstractmethod
from typing import Dict, Any
from app.services.llm import call_llm_with_fallback
from app.core.database import Database
from app.services.model_registry_service import normalize_provider
from app.services.orchestration_engine import AgentModelAssignment, orchestration_engine
from app.services.provider_gateway import ProviderError, provider_gateway
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all AI agents in the NovelForge system."""
    
    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt
    
    @abstractmethod
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's logic.
        
        Args:
            state: The current workflow state
            
        Returns:
            Updated state with agent's output
        """
        pass

    def _build_context_prompt(self, state: Dict[str, Any]) -> str:
        """Build a shared context prompt for all agents."""
        context = []
        context.append(f"Cycle Number: {state.get('cycle_number', 1)}")
        context.append(f"Original Idea Dump: {state.get('idea_dump')}")
        context.append(
            "Operating instructions: preserve strong existing ideas, integrate new user input, "
            "challenge weak assumptions, improve structure, and ask only high-value questions."
        )
        if state.get("new_messages"):
            context.append("\nNew User Input For This Cycle:")
            for msg in state["new_messages"]:
                context.append(f"- {msg.get('content', '')}")
        
        if state.get("timeline_messages"):
            context.append("\nTimeline Context (Prior discussion and user input):")
            for msg in state["timeline_messages"]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                agent_name = msg.get("agent_name")
                name = agent_name if agent_name else role.capitalize()
                context.append(f"{name}: {content}")

        if state.get("previous_outline"):
            context.append(f"\nPrevious Outline: {state['previous_outline']}")

        if state.get("previous_characters"):
            context.append(f"\nPrevious Characters: {state['previous_characters']}")

        if state.get("previous_world_bible"):
            context.append(f"\nPrevious World Bible: {state['previous_world_bible']}")

        if state.get("unresolved_questions"):
            context.append(f"\nUnresolved Questions: {state['unresolved_questions']}")
            
        if state.get("answers"):
            context.append(f"\nUser Answers to Previous Questions: {', '.join(state['answers'])}")

        return "\n".join(context)
    
    async def call_llm(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        expect_json: bool = True
    ) -> Dict[str, Any]:
        """
        Call LLM with fallback using the unified service.
        
        Args:
            messages: List of message dicts with role and content
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            expect_json: Whether to expect JSON output
            
        Returns:
            Dict with content, parsed, provider, model
        """
        try:
            db = Database.get_db()
            execution_settings = await orchestration_engine.get_settings(db)
            assignments = {item.agent_name: item for item in await orchestration_engine.get_assignments(db)}
            assignment = assignments.get(
                self.name,
                AgentModelAssignment(
                    agent_name=self.name,
                    provider=execution_settings.default_provider,
                    model=execution_settings.default_model,
                ),
            )
            assigned_provider = normalize_provider(assignment.provider or execution_settings.default_provider)
            assigned_model = assignment.model or execution_settings.default_model

            provider = assigned_provider
            model = assigned_model
            if execution_settings.execution_mode == "mock":
                provider = "mock"
                model = "mock-narrative-intelligence"
            elif execution_settings.execution_mode == "full" and provider == "mock":
                provider = normalize_provider(execution_settings.default_provider)
                model = execution_settings.default_model
                if provider == "mock":
                    raise ProviderError(
                        "INVALID_MODEL",
                        f"{self.name} is configured for mock while execution mode is FULL",
                        provider,
                        model,
                    )

            fallbacks = []

            logger.info(
                "Workflow provider selection before inference: agent=%s execution_mode=%s provider=%s model=%s assignments=%s",
                self.name,
                execution_settings.execution_mode,
                provider,
                model,
                {name: {"provider": value.provider, "model": value.model, "enabled": value.enabled, "use_mock_in_hybrid": value.use_mock_in_hybrid} for name, value in assignments.items()},
            )

            result = await provider_gateway.generate_with_failover(
                db,
                messages,
                provider=provider,
                model=model,
                fallbacks=fallbacks,
                temperature=temperature,
                max_tokens=max_tokens,
                agent_name=self.name,
                expect_json=expect_json,
            )
            if expect_json and not result.get("parsed"):
                raise ProviderError(
                    "JSON_PARSE_FAILED",
                    f"{self.name} expected JSON but {result.get('provider')} / {result.get('model')} returned non-JSON",
                    result.get("provider", provider),
                    result.get("model", model),
                )
            logger.info(
                "\nAGENT EXECUTION\n\nagent=%s\nexecution_mode=%s\nassigned_provider=%s\nassigned_model=%s\nactual_provider=%s\nactual_model=%s\nfallback_used=%s\n",
                self.name,
                execution_settings.execution_mode,
                assigned_provider,
                assigned_model,
                result.get("provider"),
                result.get("model"),
                result.get("fallback_used", False),
            )
            return result
        except ProviderError:
            logger.exception("Provider execution failed for %s", self.name)
            raise
        except RuntimeError:
            logger.warning("Database unavailable for %s provider selection; using legacy LLM fallback", self.name)

        return await call_llm_with_fallback(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            expect_json=expect_json
        )
    
