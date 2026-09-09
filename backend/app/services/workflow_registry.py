"""Agent Workflow Registry for dynamic registration and customization of pipeline stages."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class WorkflowStage(BaseModel):
    """Represents a discrete stage in the paragraph generation pipeline."""
    name: str = Field(..., description="Unique name of the stage (e.g. Dialogue, Emotion)")
    agent_name: str = Field(..., description="Target AI agent handling the generation or audit")
    depends_on: List[str] = Field(default_factory=list, description="Names of stages that must complete first")
    handler_route: str = Field(..., description="API target or internal method path representing action execution")
    retry_policy: Dict[str, Any] = Field(default_factory=lambda: {"max_retries": 3, "backoff_factor": 2})
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional custom settings for the agent execution")

class AgentWorkflowRegistry:
    """Manages dynamic registrations of paragraph workflow processing stages."""
    
    _instance: AgentWorkflowRegistry | None = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AgentWorkflowRegistry, cls).__new__(cls, *args, **kwargs)
            cls._instance._stages = {}
            cls._instance._default_sequence = []
            cls._instance._initialize_default_stages()
        return cls._instance

    def register_stage(self, stage: WorkflowStage) -> None:
        """Register or overwrite a workflow stage in the registry."""
        self._stages[stage.name.lower()] = stage
        logger.info(f"Registered workflow stage: {stage.name} (handled by: {stage.agent_name})")

    def unregister_stage(self, name: str) -> None:
        """Remove a workflow stage from the registry."""
        name_lower = name.lower()
        if name_lower in self._stages:
            del self._stages[name_lower]
            logger.info(f"Unregistered workflow stage: {name}")

    def get_stage(self, name: str) -> Optional[WorkflowStage]:
        """Retrieve a specific stage definition by name."""
        return self._stages.get(name.lower())

    def get_all_stages(self) -> List[WorkflowStage]:
        """Get all currently registered stages."""
        return list(self._stages.values())

    def get_pipeline_sequence(self) -> List[WorkflowStage]:
        """Resolves dependencies and returns stages in the correct execution order.
        
        Uses Kahn's algorithm or simple sorting by dependency constraints.
        For ease of ordering in V2, we fall back to the registered depends_on order.
        """
        # Build topological sort of registered stages
        in_degree = {name: 0 for name in self._stages}
        adj_list = {name: [] for name in self._stages}
        
        for name, stage in self._stages.items():
            for dep in stage.depends_on:
                dep_lower = dep.lower()
                if dep_lower in adj_list:
                    adj_list[dep_lower].append(name)
                    in_degree[name] += 1
                else:
                    # Prerequisite not registered yet or missing
                    pass
        
        # Standard BFS topological sort
        queue = [name for name, deg in in_degree.items() if deg == 0]
        # To maintain a stable sequence, sort alphabetical or by initial registration order if tie
        queue.sort(key=lambda x: self._default_sequence.index(x) if x in self._default_sequence else len(self._default_sequence))
        
        sorted_names = []
        while queue:
            curr = queue.pop(0)
            sorted_names.append(curr)
            for neighbor in adj_list[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Return sorted list of stage objects
        return [self._stages[name] for name in sorted_names]

    def _initialize_default_stages(self) -> None:
        """Seeds the standard workflow sequence: Planning -> Expansion -> Dialogue -> Emotion -> Style -> Continuity -> Canon -> Editorial -> Approval"""
        default_stages = [
            WorkflowStage(
                name="Planning",
                agent_name="ScenePlannerAgent",
                depends_on=[],
                handler_route="internal://planning",
                retry_policy={"max_retries": 1, "backoff_factor": 1}
            ),
            WorkflowStage(
                name="Expansion",
                agent_name="ParagraphExpansionAgent",
                depends_on=["Planning"],
                handler_route="/api/generation/expand",
                retry_policy={"max_retries": 3, "backoff_factor": 2}
            ),
            WorkflowStage(
                name="Dialogue",
                agent_name="DialogueAgent",
                depends_on=["Expansion"],
                handler_route="/api/generation/dialogue",
                retry_policy={"max_retries": 2, "backoff_factor": 2}
            ),
            WorkflowStage(
                name="Emotion",
                agent_name="EmotionAgent",
                depends_on=["Dialogue"],
                handler_route="/api/generation/emotion",
                retry_policy={"max_retries": 2, "backoff_factor": 1}
            ),
            WorkflowStage(
                name="Style",
                agent_name="StyleAgent",
                depends_on=["Emotion"],
                handler_route="/api/generation/style",
                retry_policy={"max_retries": 3, "backoff_factor": 2}
            ),
            WorkflowStage(
                name="Continuity",
                agent_name="ContinuityAgent",
                depends_on=["Style"],
                handler_route="/api/generation/continuity",
                retry_policy={"max_retries": 1, "backoff_factor": 1}
            ),
            WorkflowStage(
                name="Canon",
                agent_name="CanonAgent",
                depends_on=["Continuity"],
                handler_route="/api/generation/canon",
                retry_policy={"max_retries": 2, "backoff_factor": 1}
            ),
            WorkflowStage(
                name="Editorial",
                agent_name="EditorialAgent",
                depends_on=["Canon"],
                handler_route="/api/generation/editorial",
                retry_policy={"max_retries": 1, "backoff_factor": 1}
            ),
            WorkflowStage(
                name="Approval",
                agent_name="ApprovalAgent",
                depends_on=["Editorial"],
                handler_route="internal://approval",
                retry_policy={"max_retries": 1, "backoff_factor": 1}
            )
        ]
        
        self._default_sequence = [s.name.lower() for s in default_stages]
        for stage in default_stages:
            self.register_stage(stage)

# Singleton workflow registry instance
workflow_registry = AgentWorkflowRegistry()
