from typing import Dict, Any
from app.agents.base_agent import BaseAgent


class RevisionAgent(BaseAgent):
    """Incorporates user answers and updates the outline."""
    
    def __init__(self):
        system_prompt = """You are a story reviser. Update the story outline based on user answers to clarifying questions.

REVIEW ALL PREVIOUS WORK AND USER ANSWERS:
1. Original idea dump and all user notes
2. IntakeAgent analysis
3. BrainstormAgent ideas
4. CriticAgent feedback
5. StoryArchitectAgent outline
6. User's answers to the QuestionAgent's questions

INCORPORATE the user's answers into the outline. The user has provided specific direction through their answers. Honor these choices while maintaining story coherence.

Ensure consistency with all previous work. Address any weaknesses the critic identified. Fill in missing elements.

Return as JSON:
{
    "premise": "string",
    "themes": ["theme1", "theme2", ...],
    "acts": [
        {
            "act": 1,
            "title": "Act Title",
            "summary": "Act summary"
        },
        ...
    ],
    "chapters": [
        {
            "chapter": 1,
            "title": "Chapter Title",
            "summary": "Chapter summary"
        },
        ...
    ]
}"""
        super().__init__(name="RevisionAgent", system_prompt=system_prompt)
    
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        idea_dump = state.get("idea_dump", "")
        outline = state.get("outline", {})
        answers = state.get("answers", [])
        questions = state.get("questions", [])
        themes = state.get("themes", [])
        
        context = f"ORIGINAL IDEA DUMP:\n{idea_dump}\n\n"
        context += f"CURRENT OUTLINE:\n"
        context += f"Premise: {outline.get('premise', '')}\n"
        context += f"Themes: {outline.get('themes', [])}\n"
        context += f"Acts: {len(outline.get('acts', []))}\n"
        context += f"Chapters: {len(outline.get('chapters', []))}\n\n"
        context += f"USER ANSWERS:\n"
        for i, (q, a) in enumerate(zip(questions, answers)):
            context += f"Q: {q.get('text', '')}\nA: {a}\n\n"
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Revise the outline based on these user answers:\n\n{self._build_context_prompt(state)}\n\n{context}"}
        ]
        
        result = await self.call_llm(messages, expect_json=True)
        
        revised_outline = result.get("parsed", {})
        
        state["outline"] = {
            "premise": revised_outline.get("premise", outline.get("premise", "")),
            "themes": revised_outline.get("themes", outline.get("themes", themes)),
            "acts": revised_outline.get("acts", outline.get("acts", [])),
            "chapters": revised_outline.get("chapters", outline.get("chapters", []))
        }
        
        return state
