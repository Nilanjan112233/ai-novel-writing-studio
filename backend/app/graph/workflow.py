from typing import Dict, Any
from langgraph.graph import StateGraph, END
from app.graph.state import StoryState
from app.agents.intake_agent import IntakeAgent
from app.agents.brainstorm_agent import BrainstormAgent
from app.agents.critic_agent import CriticAgent
from app.agents.story_architect_agent import StoryArchitectAgent
from app.agents.question_agent import QuestionAgent
from app.agents.revision_agent import RevisionAgent
import logging

logger = logging.getLogger(__name__)


class WorkflowGraph:
    """LangGraph workflow for the AI Writers' Room."""
    
    def __init__(self):
        self.intake_agent = IntakeAgent()
        self.brainstorm_agent = BrainstormAgent()
        self.critic_agent = CriticAgent()
        self.architect_agent = StoryArchitectAgent()
        self.question_agent = QuestionAgent()
        self.revision_agent = RevisionAgent()
        
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(StoryState)
        
        workflow.add_node("intake", self.intake_node)
        workflow.add_node("brainstorm", self.brainstorm_node)
        workflow.add_node("critic", self.critic_node)
        workflow.add_node("architect", self.architect_node)
        workflow.add_node("question_agent", self.questions_node)
        workflow.add_node("revision", self.revision_node)
        
        workflow.set_entry_point("intake")
        workflow.add_edge("intake", "brainstorm")
        workflow.add_edge("brainstorm", "critic")
        workflow.add_edge("critic", "architect")
        workflow.add_edge("architect", "question_agent")
        workflow.add_conditional_edges(
            "question_agent",
            self.should_wait_for_user,
            {
                "wait": END,
                "continue": "revision"
            }
        )
        workflow.add_edge("revision", END)
        
        return workflow.compile()
    
    async def _notify_progress(self, state: StoryState, phase: str, node_name: str, payload: StoryState | None = None) -> None:
        handler = state.get("_on_progress")
        if handler:
            await handler(phase, node_name, payload if payload is not None else state)

    async def intake_node(self, state: StoryState) -> Dict[str, Any]:
        """Intake agent node."""
        logger.info("Running IntakeAgent")
        await self._notify_progress(state, "start", "intake")
        state["current_agent"] = "intake"
        state["logs"].append({"agent": "IntakeAgent", "status": "started"})
        
        result = await self.intake_agent.run(state)
        result["logs"].append({"agent": "IntakeAgent", "status": "completed"})
        await self._notify_progress(state, "complete", "intake", result)
        return result
    
    async def brainstorm_node(self, state: StoryState) -> Dict[str, Any]:
        """Brainstorm agent node."""
        logger.info("Running BrainstormAgent")
        await self._notify_progress(state, "start", "brainstorm")
        state["current_agent"] = "brainstorm"
        state["logs"].append({"agent": "BrainstormAgent", "status": "started"})
        
        result = await self.brainstorm_agent.run(state)
        result["logs"].append({"agent": "BrainstormAgent", "status": "completed"})
        await self._notify_progress(state, "complete", "brainstorm", result)
        return result
    
    async def critic_node(self, state: StoryState) -> Dict[str, Any]:
        """Critic agent node."""
        logger.info("Running CriticAgent")
        await self._notify_progress(state, "start", "critic")
        state["current_agent"] = "critic"
        state["logs"].append({"agent": "CriticAgent", "status": "started"})
        
        result = await self.critic_agent.run(state)
        result["logs"].append({"agent": "CriticAgent", "status": "completed"})
        await self._notify_progress(state, "complete", "critic", result)
        return result
    
    async def architect_node(self, state: StoryState) -> Dict[str, Any]:
        """Story architect agent node."""
        logger.info("Running StoryArchitectAgent")
        await self._notify_progress(state, "start", "architect")
        state["current_agent"] = "story_architect"
        state["logs"].append({"agent": "StoryArchitectAgent", "status": "started"})
        
        result = await self.architect_agent.run(state)
        result["logs"].append({"agent": "StoryArchitectAgent", "status": "completed"})
        await self._notify_progress(state, "complete", "architect", result)
        return result
    
    async def questions_node(self, state: StoryState) -> Dict[str, Any]:
        """Question agent node."""
        logger.info("Running QuestionAgent")
        await self._notify_progress(state, "start", "question_agent")
        state["current_agent"] = "question"
        state["logs"].append({"agent": "QuestionAgent", "status": "started"})
        
        result = await self.question_agent.run(state)
        result["logs"].append({"agent": "QuestionAgent", "status": "completed"})
        await self._notify_progress(state, "complete", "question_agent", result)
        return result
    
    async def revision_node(self, state: StoryState) -> Dict[str, Any]:
        """Revision agent node."""
        logger.info("Running RevisionAgent")
        await self._notify_progress(state, "start", "revision")
        state["current_agent"] = "revision"
        state["logs"].append({"agent": "RevisionAgent", "status": "started"})
        
        result = await self.revision_agent.run(state)
        result["logs"].append({"agent": "RevisionAgent", "status": "completed"})
        await self._notify_progress(state, "complete", "revision", result)
        return result
    
    def should_wait_for_user(self, state: StoryState) -> str:
        """Determine if workflow should wait for user input."""
        questions = state.get("questions", [])
        answers = state.get("answers", [])
        
        if questions and len(answers) < len(questions):
            return "wait"
        return "continue"
    
    async def run(self, initial_state: StoryState, on_progress=None) -> StoryState:
        """Run the workflow."""
        if on_progress:
            initial_state["_on_progress"] = on_progress
        logger.info("Starting workflow")
        result = await self.graph.ainvoke(initial_state)
        logger.info("Workflow completed")
        return result
