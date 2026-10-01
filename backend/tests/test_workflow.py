import pytest
from app.graph.workflow import WorkflowGraph
from app.graph.state import StoryState
from app.core.config import settings


@pytest.mark.asyncio
async def test_workflow_graph_initialization():
    """Test that the workflow graph initializes correctly."""
    workflow = WorkflowGraph()
    assert workflow.graph is not None
    assert workflow.intake_agent is not None
    assert workflow.brainstorm_agent is not None
    assert workflow.critic_agent is not None
    assert workflow.architect_agent is not None
    assert workflow.question_agent is not None
    assert workflow.revision_agent is not None


@pytest.mark.skip(reason="Retired chapter-first workflow no longer executes in production")
@pytest.mark.asyncio
async def test_workflow_run_mock():
    """Test running the full workflow with mock LLM."""
    settings.use_mock_llm = True
    
    workflow = WorkflowGraph()
    
    initial_state: StoryState = {
        "project_id": "test-project",
        "premise": "A young prince discovers he can hear dead gods",
        "genre": "Dark Fantasy",
        "tone": "Dark",
        "ideas": [],
        "critiques": [],
        "questions": [],
        "answers": [],
        "outline": {},
        "characters": [],
        "world_bible": {},
        "current_agent": "",
        "logs": []
    }
    
    result = await workflow.run(initial_state)
    
    assert result is not None
    assert "outline" in result
    assert "premise" in result["outline"]
    assert "themes" in result["outline"]
    assert "acts" in result["outline"]
    assert "chapters" in result["outline"]
    assert "questions" in result
    assert "logs" in result
    assert len(result["logs"]) > 0


@pytest.mark.asyncio
async def test_workflow_should_wait_for_user():
    """Test the conditional logic for waiting for user input."""
    workflow = WorkflowGraph()
    
    # Case 1: Questions exist but no answers - should wait
    state1 = {
        "project_id": "test",
        "premise": "Test",
        "genre": "",
        "tone": "",
        "ideas": [],
        "critiques": [],
        "questions": [{"text": "Q1"}],
        "answers": [],
        "outline": {},
        "characters": [],
        "world_bible": {},
        "current_agent": "",
        "logs": []
    }
    decision = workflow.should_wait_for_user(state1)
    assert decision == "wait"
    
    # Case 2: Questions and answers match - should continue
    state2 = {
        "project_id": "test",
        "premise": "Test",
        "genre": "",
        "tone": "",
        "ideas": [],
        "critiques": [],
        "questions": [{"text": "Q1"}],
        "answers": ["A1"],
        "outline": {},
        "characters": [],
        "world_bible": {},
        "current_agent": "",
        "logs": []
    }
    decision = workflow.should_wait_for_user(state2)
    assert decision == "continue"
    
    # Case 3: No questions - should continue
    state3 = {
        "project_id": "test",
        "premise": "Test",
        "genre": "",
        "tone": "",
        "ideas": [],
        "critiques": [],
        "questions": [],
        "answers": [],
        "outline": {},
        "characters": [],
        "world_bible": {},
        "current_agent": "",
        "logs": []
    }
    decision = workflow.should_wait_for_user(state3)
    assert decision == "continue"
