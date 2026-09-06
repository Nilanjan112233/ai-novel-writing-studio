"""Canon and decision registry helpers.

These registries are intentionally plain Mongo documents. They sit between
free-form writers-room discussion and structured story artifacts so user
decisions become durable narrative constraints for future agents.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Iterable, List

from bson import ObjectId


STOPWORDS = {
    "a", "an", "and", "are", "as", "be", "by", "do", "does", "for", "from",
    "how", "i", "in", "is", "it", "of", "on", "or", "should", "that", "the",
    "their", "this", "to", "uses", "use", "what", "when", "where", "which",
    "who", "why", "with", "would",
}


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9']+", (text or "").lower())
        if token and token not in STOPWORDS and len(token) > 2
    }


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _fact_from_question_answer(question: str, answer: str) -> str:
    question = _normalize(question)
    answer = _normalize(answer)
    if not question:
        return answer
    if not answer:
        return question
    return f"{question} Answer: {answer}"


def _fact_from_user_message(content: str) -> str:
    content = _normalize(content)
    lower = content.lower()
    prefixes = ("i want ", "i want the ", "make ", "set ", "use ", "the ")
    if lower.startswith(prefixes):
        return content
    return content


async def get_canon_context(db, project_id: str) -> Dict[str, Any]:
    if not ObjectId.is_valid(project_id):
        return {"locked_facts": [], "decisions": [], "rejected_decisions": [], "unresolved_questions": []}

    pid = ObjectId(project_id)
    facts = await db.canon_registry.find(
        {"project_id": pid, "status": "LOCKED"}
    ).sort("updated_at", -1).to_list(length=500)
    decisions = await db.decision_registry.find(
        {"project_id": pid}
    ).sort("updated_at", -1).to_list(length=500)
    return {
        "locked_facts": [doc.get("fact", "") for doc in facts if doc.get("fact")],
        "decisions": [
            {
                "decision": doc.get("decision", ""),
                "answer": doc.get("answer", ""),
                "status": doc.get("status", "approved"),
                "cycle_number": doc.get("cycle_number", 1),
                "source": doc.get("source", ""),
            }
            for doc in decisions
        ],
        "rejected_decisions": [
            doc.get("decision", "")
            for doc in decisions
            if str(doc.get("status", "")).lower() == "rejected" and doc.get("decision")
        ],
        "unresolved_questions": [
            doc.get("question_text", "")
            for doc in decisions
            if str(doc.get("status", "")).lower() == "unresolved" and doc.get("question_text")
        ],
    }


async def record_user_message_decision(
    db,
    *,
    project_id: str,
    content: str,
    cycle_number: int,
    message_id: ObjectId | None = None,
) -> Dict[str, Any] | None:
    fact = _fact_from_user_message(content)
    if len(_tokens(fact)) < 2:
        return None
    now = datetime.utcnow()
    pid = ObjectId(project_id)
    source_id = str(message_id) if message_id else ""
    decision_doc = {
        "project_id": pid,
        "decision": fact,
        "answer": content,
        "decision_type": "user_override",
        "status": "approved",
        "source": "user_message",
        "source_id": source_id,
        "cycle_number": cycle_number,
        "updated_at": now,
    }
    await db.decision_registry.update_one(
        {"project_id": pid, "source": "user_message", "source_id": source_id or fact},
        {"$set": decision_doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    await upsert_canon_fact(
        db,
        project_id=project_id,
        fact=fact,
        source="user_message",
        source_id=source_id,
        cycle_number=cycle_number,
    )
    return decision_doc


async def record_answer_decision(
    db,
    *,
    project_id: str,
    question: Dict[str, Any],
    answer: str,
) -> Dict[str, Any]:
    now = datetime.utcnow()
    pid = ObjectId(project_id)
    question_text = question.get("text", "")
    cycle_number = int(question.get("cycle_number") or question.get("cycle") or 1)
    fact = _fact_from_question_answer(question_text, answer)
    doc = {
        "project_id": pid,
        "question_id": question.get("_id"),
        "question_text": question_text,
        "choices": question.get("choices") or [],
        "answer": answer,
        "decision": fact,
        "decision_type": "accepted",
        "status": "approved",
        "source": "question_answer",
        "source_id": str(question.get("_id", "")),
        "cycle_number": cycle_number,
        "updated_at": now,
    }
    await db.decision_registry.update_one(
        {"project_id": pid, "question_id": question.get("_id")},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    await db.canon_registry.update_many(
        {
            "project_id": pid,
            "source": "question_answer",
            "source_id": str(question.get("_id", "")),
            "status": "LOCKED",
        },
        {"$set": {
            "status": "SUPERSEDED",
            "active": False,
            "superseded_at": now,
            "superseded_by_answer": answer,
        }},
    )
    await upsert_canon_fact(
        db,
        project_id=project_id,
        fact=fact,
        source="question_answer",
        source_id=str(question.get("_id", "")),
        cycle_number=cycle_number,
    )
    return doc


async def upsert_canon_fact(
    db,
    *,
    project_id: str,
    fact: str,
    source: str,
    source_id: str,
    cycle_number: int,
) -> None:
    fact = _normalize(fact)
    if not fact:
        return
    now = datetime.utcnow()
    pid = ObjectId(project_id)
    fingerprint = " ".join(sorted(_tokens(fact)))[:240] or fact[:240].lower()
    await db.canon_registry.update_one(
        {"project_id": pid, "fingerprint": fingerprint},
        {
            "$set": {
                "project_id": pid,
                "fact": fact,
                "fingerprint": fingerprint,
                "status": "LOCKED",
                "active": True,
                "source": source,
                "source_id": source_id,
                "cycle_number": cycle_number,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )


def _overlap(a: Iterable[str], b: Iterable[str]) -> float:
    left = set(a)
    right = set(b)
    if not left or not right:
        return 0.0
    return len(left & right) / max(1, min(len(left), len(right)))


async def question_is_solved(
    db,
    *,
    project_id: str,
    text: str,
    choices: List[str] | None = None,
) -> bool:
    context = await get_canon_context(db, project_id)
    question_tokens = _tokens(" ".join([text or "", " ".join(choices or [])]))
    if not question_tokens:
        return False

    for fact in context["locked_facts"]:
        fact_tokens = _tokens(fact)
        if _overlap(question_tokens, fact_tokens) >= 0.45:
            return True
    for decision in context["decisions"]:
        if str(decision.get("status", "")).lower() not in {"locked", "approved"}:
            continue
        decision_tokens = _tokens(" ".join([decision.get("decision", ""), decision.get("answer", "")]))
        if _overlap(question_tokens, decision_tokens) >= 0.45:
            return True
    return False
