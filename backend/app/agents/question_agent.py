import re
from typing import Dict, Any
from app.agents.base_agent import BaseAgent


class QuestionAgent(BaseAgent):
    """Generates high-value questions for the user to clarify the story."""
    
    def __init__(self):
        system_prompt = """You are a story consultant. Generate 3-5 high-value questions that will help clarify and improve the story.

REVIEW ALL PREVIOUS WORK:
1. IntakeAgent: What was extracted from the idea dump?
2. BrainstormAgent: What ideas were generated?
3. CriticAgent: What weaknesses were identified? What's missing?
4. StoryArchitectAgent: What outline was created?

IDENTIFY UNCERTAINTY. Look for:
- Ambiguous character motivations
- Unclear world-building details
- Thematic contradictions
- Plot gaps or logic issues
- Missing elements the critic identified

Ask questions that will resolve these uncertainties. Each question should address a real gap or ambiguity in the story.
Never ask for information already present in LOCKED CANON FACTS or LOCKED USER DECISIONS.

For each question, provide 2-3 possible answer choices.

Return as JSON:
{
    "questions": [
        {
            "text": "Question text",
            "choices": ["choice1", "choice2", "choice3"]
        },
        ...
    ]
}"""
        super().__init__(name="QuestionAgent", system_prompt=system_prompt)
    
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        idea_dump = state.get("idea_dump", "")
        outline = state.get("outline", {})
        premise = outline.get("premise", state.get("premise", ""))
        themes = outline.get("themes", state.get("themes", []))
        missing_elements = state.get("missing_elements", [])
        weaknesses = state.get("weaknesses", [])
        canon_facts = state.get("canon_facts", [])
        decisions = state.get("decision_registry", [])
        
        context = f"ORIGINAL IDEA DUMP:\n{idea_dump}\n\n"
        context += f"CURRENT OUTLINE:\n"
        context += f"Premise: {premise}\n"
        context += f"Themes: {themes}\n"
        context += f"Acts: {len(outline.get('acts', []))}\n"
        context += f"Chapters: {len(outline.get('chapters', []))}\n\n"
        if missing_elements:
            context += f"MISSING ELEMENTS (from Critic): {missing_elements}\n\n"
        if weaknesses:
            context += f"WEAKNESSES (from Critic): {weaknesses}\n\n"
        if canon_facts:
            context += f"LOCKED CANON FACTS (do not contradict or re-ask): {canon_facts}\n\n"
        if decisions:
            context += f"LOCKED USER DECISIONS (do not re-ask): {decisions}\n\n"
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Generate clarifying questions for:\n\n{self._build_context_prompt(state)}\n\n{context}"}
        ]
        
        result = await self.call_llm(messages, expect_json=True)
        
        questions_data = result.get("parsed", {})
        questions = questions_data.get("questions", [])
        locked_text = " ".join([str(item) for item in canon_facts + decisions])
        locked_tokens = _tokens(locked_text)
        filtered = []
        for question in questions:
            q_tokens = _tokens(" ".join([question.get("text", ""), " ".join(question.get("choices", []))]))
            overlap = len(q_tokens & locked_tokens) / max(1, min(len(q_tokens), len(locked_tokens)))
            if overlap < 0.45:
                filtered.append(question)
        
        state["questions"] = filtered
        
        return state


def _tokens(text: str) -> set[str]:
    stopwords = {"and", "the", "that", "this", "what", "which", "should", "would", "with", "from", "does", "uses", "use"}
    return {
        token
        for token in re.findall(r"[a-z0-9']+", (text or "").lower())
        if token not in stopwords and len(token) > 2
    }
