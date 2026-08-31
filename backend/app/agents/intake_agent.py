from typing import Dict, Any
from app.agents.base_agent import BaseAgent


class IntakeAgent(BaseAgent):
    """Analyzes user premise and extracts genre, themes, hooks, and assumptions."""
    
    def __init__(self):
        system_prompt = """You are a story analyst. Analyze the user's complete idea dump and extract:
1. Genre (primary and secondary)
2. Core themes (3-5 themes)
3. Narrative hooks (what makes this interesting)
4. Key assumptions (what we're taking as given)
5. Premise candidates (1-3 possible core premises)
6. Character concepts (from character notes)
7. Setting ideas (from world notes)
8. Plot seeds (from plot notes)

Analyze ALL provided notes: idea_dump, themes, inspirations, character_notes, world_notes, plot_notes, notes.
Preserve the user's unique ideas and voice. Extract and organize, don't invent.

Return your analysis as JSON with this structure:
{
    "genre": "string",
    "themes": ["theme1", "theme2", ...],
    "hooks": ["hook1", "hook2", ...],
    "assumptions": ["assumption1", "assumption2", ...],
    "premise_candidates": ["premise1", "premise2", ...],
    "character_concepts": ["concept1", "concept2", ...],
    "setting_ideas": ["idea1", "idea2", ...],
    "plot_seeds": ["seed1", "seed2", ...]
}"""
        super().__init__(name="IntakeAgent", system_prompt=system_prompt)
    
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        idea_dump = state.get("idea_dump", "")
        premise = state.get("premise", "")
        themes = state.get("themes", [])
        inspirations = state.get("inspirations", [])
        character_notes = state.get("character_notes", "")
        world_notes = state.get("world_notes", "")
        plot_notes = state.get("plot_notes", "")
        notes = state.get("notes", "")
        
        context = f"Title: {state.get('title', '')}\n\n"
        if idea_dump:
            context += f"IDEA DUMP:\n{idea_dump}\n\n"
        if premise:
            context += f"PREMISE:\n{premise}\n\n"
        if themes:
            context += f"THEMES: {', '.join(themes)}\n\n"
        if inspirations:
            context += f"INSPIRATIONS: {', '.join(inspirations)}\n\n"
        if character_notes:
            context += f"CHARACTER NOTES:\n{character_notes}\n\n"
        if world_notes:
            context += f"WORLD NOTES:\n{world_notes}\n\n"
        if plot_notes:
            context += f"PLOT NOTES:\n{plot_notes}\n\n"
        if notes:
            context += f"ADDITIONAL NOTES:\n{notes}\n\n"
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Analyze this complete story idea:\n\n{self._build_context_prompt(state)}\n\n{context}"}
        ]
        
        result = await self.call_llm(messages, expect_json=True)
        
        analysis = result.get("parsed", {})
        
        state["genre"] = analysis.get("genre", state.get("genre", ""))
        state["themes"] = analysis.get("themes", state.get("themes", []))
        state["hooks"] = analysis.get("hooks", [])
        state["assumptions"] = analysis.get("assumptions", [])
        state["premise_candidates"] = analysis.get("premise_candidates", [])
        state["character_concepts"] = analysis.get("character_concepts", [])
        state["setting_ideas"] = analysis.get("setting_ideas", [])
        state["plot_seeds"] = analysis.get("plot_seeds", [])
        
        return state
