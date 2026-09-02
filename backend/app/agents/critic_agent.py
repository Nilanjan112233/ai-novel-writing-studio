from typing import Dict, Any
from app.agents.base_agent import BaseAgent


class CriticAgent(BaseAgent):
    """Finds clichés, weak motivations, and logical gaps in the ideas."""
    
    def __init__(self):
        system_prompt = """You are a critical story editor. Review the BrainstormAgent's output and challenge it.

REVIEW THE BRAINSTORM OUTPUT FIRST:
- What story possibilities were generated?
- What conflicts were proposed?
- What twists were suggested?
- What thematic directions were explored?

CHALLENGE THESE FINDINGS. Don't just accept them. Ask:
1. Are any of these clichés or overused tropes?
2. Are character motivations weak or unclear?
3. Are there logical gaps or inconsistencies?
4. Do these ideas actually fit the user's original vision?
5. What's missing? What hasn't been considered?

Be constructive but critical. Help strengthen the story by identifying weaknesses.

Return as JSON:
{
    "critiques": ["critique1", "critique2", ...],
    "weaknesses": ["weakness1", "weakness2", ...],
    "suggestions": ["suggestion1", "suggestion2", ...],
    "missing_elements": ["missing1", "missing2", ...]
}"""
        super().__init__(name="CriticAgent", system_prompt=system_prompt)
    
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        idea_dump = state.get("idea_dump", "")
        ideas = state.get("ideas", [])
        conflicts = state.get("conflicts", [])
        twists = state.get("twists", [])
        theme_directions = state.get("theme_directions", [])
        scene_ideas = state.get("scene_ideas", [])
        
        context = f"ORIGINAL IDEA DUMP:\n{idea_dump}\n\n"
        context += f"BRAINSTORM OUTPUT:\n"
        context += f"Story Possibilities: {ideas}\n"
        context += f"Conflicts: {conflicts}\n"
        context += f"Twists: {twists}\n"
        context += f"Thematic Directions: {theme_directions}\n"
        context += f"Scene Ideas: {scene_ideas}\n"
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Critique the BrainstormAgent\'s output:\n\n{self._build_context_prompt(state)}\n\n{context}"}
        ]
        
        result = await self.call_llm(messages, expect_json=True)
        
        critique = result.get("parsed", {})
        
        state["critiques"] = critique.get("critiques", [])
        state["weaknesses"] = critique.get("weaknesses", [])
        state["suggestions"] = critique.get("suggestions", [])
        state["missing_elements"] = critique.get("missing_elements", [])
        
        return state
