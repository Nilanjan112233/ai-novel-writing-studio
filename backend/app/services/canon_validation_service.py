"""Validate proposed structured artifacts against locked canon."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List

from bson import ObjectId

from app.services.canon_service import get_canon_context


NEGATIONS = {"not", "never", "no", "without", "cannot", "can't", "isn't", "doesn't"}
STOPWORDS = {
    "a", "an", "and", "answer", "are", "as", "at", "be", "by", "for",
    "from", "how", "in", "is", "it", "of", "on", "or", "should", "that",
    "the", "their", "this", "to", "what", "when", "where", "which", "who",
    "why", "with",
}


def _tokens(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9']+", (text or "").lower())
        if token not in STOPWORDS
    }


def _fragments(value: Any) -> List[str]:
    if isinstance(value, dict):
        fragments: List[str] = []
        for key, item in value.items():
            fragments.extend(f"{key} {fragment}" for fragment in _fragments(item))
        return fragments
    if isinstance(value, list):
        fragments: List[str] = []
        for item in value:
            fragments.extend(_fragments(item))
        return fragments
    text = str(value or "").strip()
    return [text] if text else []


async def validate_against_canon(
    db,
    *,
    project_id: str,
    agent_name: str,
    cycle_number: int,
    structured_output: Dict[str, Any],
) -> List[Dict[str, Any]]:
    context = await get_canon_context(db, project_id)
    output_fragments = _fragments(structured_output)
    reports: List[Dict[str, Any]] = []
    for fact in context["locked_facts"]:
        fact_tokens = _tokens(fact)
        if len(fact_tokens) < 3:
            continue
        fact_negated = bool(fact_tokens & NEGATIONS)
        contradictory_fragment = None
        for fragment in output_fragments:
            fragment_tokens = _tokens(fragment)
            shared = fact_tokens & fragment_tokens
            overlap = len(shared) / max(1, min(len(fact_tokens), len(fragment_tokens)))
            if len(shared) < 3 or overlap < 0.65:
                continue
            if fact_negated != bool(fragment_tokens & NEGATIONS):
                contradictory_fragment = fragment
                break
        if contradictory_fragment:
            reports.append({
                "project_id": ObjectId(project_id),
                "agent_name": agent_name,
                "cycle_number": cycle_number,
                "canon_fact": fact,
                "status": "open",
                "severity": "high",
                "message": "Structured output may contradict a locked canon fact.",
                "contradictory_fragment": contradictory_fragment[:1000],
                "created_at": datetime.utcnow(),
            })
    if reports:
        await db.contradiction_reports.insert_many(reports)
    return reports
