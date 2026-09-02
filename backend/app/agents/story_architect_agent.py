from typing import Dict, Any
from app.agents.base_agent import BaseAgent


class StoryArchitectAgent(BaseAgent):
    """Produces premise statement, three-act structure, and chapter roadmap."""
    
    def __init__(self):
        system_prompt = """You are a story architect. Create a structured outline based on ALL previous agent work.

REVIEW ALL PREVIOUS OUTPUTS:
1. IntakeAgent: What premise candidates, character concepts, setting ideas, and plot seeds were identified?
2. BrainstormAgent: What story possibilities, conflicts, twists, and scene ideas were generated?
3. CriticAgent: What weaknesses were identified? What suggestions were made? What's missing?

SYNTHESIZE these perspectives into a coherent outline. Address the critic's concerns. Incorporate the best brainstorm ideas. Build on the intake analysis.

Create:
1. A refined premise statement (1-2 sentences - choose or combine the best premise candidates)
2. Three-act structure with summaries (use the conflicts and twists)
3. Chapter roadmap (at least 10 chapters - incorporate scene ideas)

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
        super().__init__(name="StoryArchitectAgent", system_prompt=system_prompt)
    
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        idea_dump = state.get("idea_dump", "")
        premise = state.get("premise", "")
        premise_candidates = state.get("premise_candidates", [])
        themes = state.get("themes", [])
        ideas = state.get("ideas", [])
        conflicts = state.get("conflicts", [])
        twists = state.get("twists", [])
        scene_ideas = state.get("scene_ideas", [])
        critiques = state.get("critiques", [])
        weaknesses = state.get("weaknesses", [])
        suggestions = state.get("suggestions", [])
        missing_elements = state.get("missing_elements", [])
        
        context = f"ORIGINAL IDEA DUMP:\n{idea_dump}\n\n"
        context += f"INTAKE ANALYSIS:\n"
        context += f"Premise Candidates: {premise_candidates}\n"
        context += f"Themes: {themes}\n\n"
        context += f"BRAINSTORM OUTPUT:\n"
        context += f"Ideas: {ideas}\n"
        context += f"Conflicts: {conflicts}\n"
        context += f"Twists: {twists}\n"
        context += f"Scene Ideas: {scene_ideas}\n\n"
        context += f"CRITIC REVIEW:\n"
        context += f"Critiques: {critiques}\n"
        context += f"Weaknesses: {weaknesses}\n"
        context += f"Suggestions: {suggestions}\n"
        context += f"Missing Elements: {missing_elements}\n"
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Create a structured outline synthesizing all previous work:\n\n{self._build_context_prompt(state)}\n\n{context}"}
        ]
        
        result = await self.call_llm(messages, expect_json=True)
        
        outline = result.get("parsed", {})
        
        state["outline"] = {
            "premise": outline.get("premise", premise),
            "themes": outline.get("themes", themes),
            "acts": outline.get("acts", []),
            "chapters": outline.get("chapters", [])
        }
        
        return state
