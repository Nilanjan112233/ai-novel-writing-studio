from typing import Dict, Any
from app.agents.base_agent import BaseAgent


class BrainstormAgent(BaseAgent):
    """Generates plot ideas, conflicts, twists, and thematic directions."""
    
    def __init__(self):
        system_prompt = """You are a creative brainstormer. Generate story possibilities based on the IntakeAgent's analysis and the user's original idea dump.

REVIEW THE INTAKE ANALYSIS FIRST:
- What premise candidates were identified?
- What character concepts emerged?
- What setting ideas were found?
- What plot seeds were discovered?

BUILD ON THESE FINDINGS. Don't start from scratch. Expand, twist, and deepen what the IntakeAgent found.

Generate:
1. 10 story possibilities (different directions the story could go - build on premise candidates)
2. 5 central conflicts (what drives the story - connect to character concepts)
3. 5 potential twists (surprising developments - use plot seeds)
4. 3 thematic directions (how themes could be explored - deepen the themes)
5. 5 scene ideas (specific scenes that could work)

Return as JSON:
{
    "ideas": ["idea1", "idea2", ...],
    "conflicts": ["conflict1", "conflict2", ...],
    "twists": ["twist1", "twist2", ...],
    "theme_directions": ["theme_direction1", "theme_direction2", ...],
    "scene_ideas": ["scene1", "scene2", ...]
}"""
        super().__init__(name="BrainstormAgent", system_prompt=system_prompt)
    
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        idea_dump = state.get("idea_dump", "")
        premise = state.get("premise", "")
        genre = state.get("genre", "")
        themes = state.get("themes", [])
        premise_candidates = state.get("premise_candidates", [])
        character_concepts = state.get("character_concepts", [])
        setting_ideas = state.get("setting_ideas", [])
        plot_seeds = state.get("plot_seeds", [])
        
        context = f"ORIGINAL IDEA DUMP:\n{idea_dump}\n\n"
        context += f"INTAKE ANALYSIS:\n"
        context += f"Genre: {genre}\n"
        context += f"Themes: {', '.join(themes)}\n"
        if premise_candidates:
            context += f"Premise Candidates: {', '.join(premise_candidates)}\n"
        if character_concepts:
            context += f"Character Concepts: {', '.join(character_concepts)}\n"
        if setting_ideas:
            context += f"Setting Ideas: {', '.join(setting_ideas)}\n"
        if plot_seeds:
            context += f"Plot Seeds: {', '.join(plot_seeds)}\n"
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Brainstorm story possibilities building on the IntakeAgent\'s analysis:\n\n{self._build_context_prompt(state)}\n\n{context}"}
        ]
        
        result = await self.call_llm(messages, expect_json=True)
        
        brainstorm = result.get("parsed", {})
        
        state["ideas"] = brainstorm.get("ideas", [])
        state["conflicts"] = brainstorm.get("conflicts", [])
        state["twists"] = brainstorm.get("twists", [])
        state["theme_directions"] = brainstorm.get("theme_directions", [])
        state["scene_ideas"] = brainstorm.get("scene_ideas", [])
        
        return state
