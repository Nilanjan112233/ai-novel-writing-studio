import pytest
from app.agents.intake_agent import IntakeAgent
from app.agents.brainstorm_agent import BrainstormAgent
from app.agents.critic_agent import CriticAgent
from app.agents.story_architect_agent import StoryArchitectAgent
from app.agents.question_agent import QuestionAgent
from app.agents.revision_agent import RevisionAgent
from app.core.config import settings

pytestmark = pytest.mark.skip(
    reason="Retired chapter-first agents no longer execute in the Narrative Studio production workflow"
)


@pytest.mark.asyncio
async def test_intake_agent_mock():
    """Test IntakeAgent with mock LLM."""
    settings.use_mock_llm = True
    agent = IntakeAgent()
    
    state = {
        "project_id": "test",
        "premise": "A young prince discovers he can hear dead gods",
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
    
    result = await agent.run(state)
    
    assert "genre" in result
    assert result["genre"] == "Dark Fantasy"
    assert "themes" in result
    assert len(result["themes"]) > 0
    assert "hooks" in result
    assert len(result["hooks"]) > 0


@pytest.mark.asyncio
async def test_brainstorm_agent_mock():
    """Test BrainstormAgent with mock LLM."""
    settings.use_mock_llm = True
    agent = BrainstormAgent()
    
    state = {
        "project_id": "test",
        "premise": "A young prince discovers he can hear dead gods",
        "genre": "Dark Fantasy",
        "tone": "Dark",
        "themes": ["Death", "Power"],
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
    
    result = await agent.run(state)
    
    assert "ideas" in result
    assert len(result["ideas"]) > 0
    assert "conflicts" in result
    assert len(result["conflicts"]) > 0
    assert "twists" in result
    assert len(result["twists"]) > 0


@pytest.mark.asyncio
async def test_critic_agent_mock():
    """Test CriticAgent with mock LLM."""
    settings.use_mock_llm = True
    agent = CriticAgent()
    
    state = {
        "project_id": "test",
        "premise": "A young prince discovers he can hear dead gods",
        "genre": "Dark Fantasy",
        "tone": "Dark",
        "ideas": ["Idea 1", "Idea 2"],
        "critiques": [],
        "questions": [],
        "answers": [],
        "outline": {},
        "characters": [],
        "world_bible": {},
        "current_agent": "",
        "logs": []
    }
    
    result = await agent.run(state)
    
    assert "critiques" in result
    assert len(result["critiques"]) > 0
    assert "weaknesses" in result
    assert "suggestions" in result


@pytest.mark.asyncio
async def test_story_architect_agent_mock():
    """Test StoryArchitectAgent with mock LLM."""
    settings.use_mock_llm = True
    agent = StoryArchitectAgent()
    
    state = {
        "project_id": "test",
        "premise": "A young prince discovers he can hear dead gods",
        "genre": "Dark Fantasy",
        "tone": "Dark",
        "ideas": ["Idea 1", "Idea 2"],
        "critiques": ["Critique 1"],
        "suggestions": ["Suggestion 1"],
        "questions": [],
        "answers": [],
        "outline": {},
        "characters": [],
        "world_bible": {},
        "current_agent": "",
        "logs": []
    }
    
    result = await agent.run(state)
    
    assert "outline" in result
    assert "premise" in result["outline"]
    assert "themes" in result["outline"]
    assert "acts" in result["outline"]
    assert len(result["outline"]["acts"]) > 0
    assert "chapters" in result["outline"]
    assert len(result["outline"]["chapters"]) > 0


@pytest.mark.asyncio
async def test_question_agent_mock():
    """Test QuestionAgent with mock LLM."""
    settings.use_mock_llm = True
    agent = QuestionAgent()
    
    state = {
        "project_id": "test",
        "premise": "A young prince discovers he can hear dead gods",
        "genre": "Dark Fantasy",
        "tone": "Dark",
        "ideas": [],
        "critiques": [],
        "questions": [],
        "answers": [],
        "outline": {
            "premise": "Test premise",
            "themes": ["Power", "Sacrifice"],
            "acts": [],
            "chapters": []
        },
        "characters": [],
        "world_bible": {},
        "current_agent": "",
        "logs": []
    }
    
    result = await agent.run(state)
    
    assert "questions" in result
    assert len(result["questions"]) > 0
    assert "text" in result["questions"][0]
    assert "choices" in result["questions"][0]


@pytest.mark.asyncio
async def test_revision_agent_mock():
    """Test RevisionAgent with mock LLM."""
    settings.use_mock_llm = True
    agent = RevisionAgent()
    
    state = {
        "project_id": "test",
        "premise": "A young prince discovers he can hear dead gods",
        "genre": "Dark Fantasy",
        "tone": "Dark",
        "ideas": [],
        "critiques": [],
        "questions": [
            {"text": "Question 1", "choices": ["A", "B", "C"]},
            {"text": "Question 2", "choices": ["X", "Y", "Z"]}
        ],
        "answers": ["A", "X"],
        "outline": {
            "premise": "Test premise",
            "themes": ["Power"],
            "acts": [],
            "chapters": []
        },
        "characters": [],
        "world_bible": {},
        "current_agent": "",
        "logs": []
    }
    
    result = await agent.run(state)
    
    assert "outline" in result
    assert "premise" in result["outline"]
    assert "themes" in result["outline"]
    assert "acts" in result["outline"]
    assert "chapters" in result["outline"]
