"""Structured, project-wide knowledge captured from meaningful author input."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from bson import ObjectId


DOMAIN_KEYWORDS = {
    "character": {"character", "protagonist", "antagonist", "motivation", "backstory", "personality", "believes", "wants"},
    "world": {"kingdom", "empire", "city", "country", "world", "location", "culture", "language", "history"},
    "power": {"power", "magic", "spell", "ability", "rule", "cost", "limitation"},
    "timeline": {"before", "after", "year", "date", "timeline", "event", "day", "century"},
    "relationship": {"relationship", "loves", "hates", "trusts", "sibling", "parent", "ally", "enemy"},
    "plot": {"mystery", "clue", "plot", "secret", "reveal", "arc", "foreshadow", "promise"},
    "canon": {"canon", "official", "always", "never", "fact"},
}

ROUTES = {
    "character": ["story_bible", "character_intelligence", "canon", "knowledge_graph", "future_agents"],
    "world": ["story_bible", "world", "canon", "knowledge_graph", "future_agents"],
    "power": ["story_bible", "power_system", "canon", "knowledge_graph", "future_agents"],
    "timeline": ["story_bible", "timeline", "canon", "knowledge_graph", "future_agents"],
    "relationship": ["story_bible", "relationship_graph", "canon", "knowledge_graph", "future_agents"],
    "plot": ["story_bible", "plot_threads", "knowledge_graph", "future_agents"],
    "canon": ["story_bible", "canon", "knowledge_graph", "future_agents"],
    "general": ["story_bible", "knowledge_graph", "future_agents"],
}

COMMAND_PREFIXES = (
    "open ", "show ", "go to ", "navigate ", "run ", "create ", "review ",
    "explain ", "why ", "how ", "where ", "what ", "which ", "who ",
    "can you ", "could you ", "would you ", "please ",
)


def _serialize(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {("id" if key == "_id" else key): _serialize(item) for key, item in value.items()}
    return value


def _normalize(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    return re.sub(r"\s+", " ", str(value or "").strip())


def _tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", value.lower())


class SharedNarrativeContextService:
    async def _project(self, db, project_id: str) -> ObjectId:
        if not ObjectId.is_valid(project_id):
            raise ValueError("Invalid project ID")
        pid = ObjectId(project_id)
        if not await db.projects.find_one({"_id": pid}):
            raise ValueError("Project not found")
        return pid

    def classify(self, content: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        body = payload or {}
        text = _normalize(content or body.get("value"))
        lower = text.lower()
        structured = all(body.get(key) not in (None, "") for key in ("domain", "subject", "field")) and "value" in body
        meaningful = bool(text) and len(_tokens(text)) >= 3
        transient = (
            not meaningful
            or text.endswith("?")
            or lower.startswith(COMMAND_PREFIXES)
            or lower in {"yes", "no", "okay", "ok", "continue", "thanks", "thank you"}
        )
        if structured:
            transient = False

        domain = str(body.get("domain") or "").strip().lower()
        if not domain:
            scores = {
                candidate: sum(1 for keyword in keywords if re.search(rf"\b{re.escape(keyword)}\b", lower))
                for candidate, keywords in DOMAIN_KEYWORDS.items()
            }
            domain = max(scores, key=scores.get) if scores and max(scores.values()) else "general"
        if domain not in ROUTES:
            domain = "general"

        subject = str(body.get("subject") or "").strip()
        field = str(body.get("field") or "").strip()
        value = body.get("value", text)
        if not subject:
            match = re.match(r"(?:the\s+)?(.{2,80}?)\s+(?:has|have|is|are|uses|contains|rules?)\b", text, re.I)
            subject = (match.group(1).strip() if match else domain.title())[:80]
        if not field:
            predicates = {
                "character": "author_statement", "world": "world_fact", "power": "system_rule",
                "timeline": "chronology_fact", "relationship": "relationship_fact", "plot": "plot_fact",
                "canon": "official_fact", "general": "author_statement",
            }
            field = predicates[domain]

        source_type = str(body.get("source_type") or "user_message")
        confidence = float(body.get("confidence") or (
            0.98 if source_type == "question_answer"
            else 0.95 if structured
            else 0.92 if source_type == "discussion_decision"
            else 0.90
        ))
        importance = int(body.get("importance") or (95 if confidence >= .95 else 85 if confidence >= .9 else 70))
        return {
            "persist": not transient and confidence >= .75,
            "domain": domain,
            "subject": subject,
            "field": field,
            "value": value,
            "confidence": round(max(0.0, min(confidence, 1.0)), 3),
            "importance": max(0, min(importance, 100)),
            "routed_subsystems": ROUTES[domain],
            "requires_canon_proposal": domain in {"character", "world", "power", "timeline", "relationship", "canon"} and confidence >= .9,
            "reason": "explicit structured author knowledge" if structured else "declarative author knowledge",
        }

    async def ingest(
        self,
        db,
        project_id: str,
        *,
        content: str,
        source_type: str = "user_message",
        source_id: str = "",
        source_excerpt: str | None = None,
        structured: Dict[str, Any] | None = None,
        create_canon_proposal: bool = True,
    ) -> Dict[str, Any]:
        pid = await self._project(db, project_id)
        payload = {**(structured or {}), "source_type": source_type}
        classification = self.classify(content, payload)
        if not classification["persist"]:
            return {"persisted": False, "reason": "Input is transient, ambiguous, or below the confidence threshold."}
        identity_basis = "|".join([
            classification["domain"],
            classification["subject"].lower(),
            classification["field"].lower(),
        ])
        identity_fingerprint = hashlib.sha256(identity_basis.encode("utf-8")).hexdigest()
        fingerprint_basis = "|".join([
            classification["domain"], classification["subject"].lower(), classification["field"].lower(),
            _normalize(classification["value"]).lower(),
        ])
        fingerprint = hashlib.sha256(fingerprint_basis.encode("utf-8")).hexdigest()
        now = datetime.utcnow()
        existing = await db.shared_narrative_context.find_one({
            "project_id": pid, "dedupe_fingerprint": fingerprint, "active": True,
        })
        provenance = {
            "source_type": source_type,
            "source_id": str(source_id or ""),
            "source_excerpt": _normalize(source_excerpt or content)[:500],
            "recorded_at": now,
        }
        if existing:
            await db.shared_narrative_context.update_one(
                {"_id": existing["_id"]},
                {"$set": {"updated_at": now, "confidence": max(float(existing.get("confidence") or 0), classification["confidence"])},
                 "$addToSet": {"provenance": provenance}},
            )
            result = await db.shared_narrative_context.find_one({"_id": existing["_id"]})
            return {"persisted": True, "deduplicated": True, "entry": _serialize(result)}

        doc = {
            "project_id": pid,
            "context_id": str(uuid4()),
            **{key: classification[key] for key in (
                "domain", "subject", "field", "value", "confidence", "importance",
                "routed_subsystems", "reason",
            )},
            "entity_refs": list((structured or {}).get("entity_refs") or []),
            "status": "approved_author_input",
            "active": True,
            "source_type": source_type,
            "source_id": str(source_id or ""),
            "source_version": 1,
            "provenance": [provenance],
            "identity_fingerprint": identity_fingerprint,
            "dedupe_fingerprint": fingerprint,
            "created_at": now,
            "updated_at": now,
            "approved_at": now,
        }
        inserted = await db.shared_narrative_context.insert_one(doc)
        doc["_id"] = inserted.inserted_id
        superseded = await db.shared_narrative_context.update_many(
            {
                "project_id": pid,
                "_id": {"$ne": inserted.inserted_id},
                "active": True,
                "$or": [
                    {"identity_fingerprint": identity_fingerprint},
                    {
                        "identity_fingerprint": {"$exists": False},
                        "domain": classification["domain"],
                        "subject": classification["subject"],
                        "field": classification["field"],
                    },
                ],
            },
            {"$set": {
                "active": False,
                "status": "superseded",
                "superseded_at": now,
                "superseded_by_context_id": doc["context_id"],
                "updated_at": now,
            }},
        )

        proposal_id = None
        if create_canon_proposal and classification["requires_canon_proposal"]:
            existing_proposal = await db.canon_proposals.find_one({
                "project_id": pid, "source_context_id": doc["context_id"], "status": {"$in": ["pending", "approved"]},
            })
            if existing_proposal:
                proposal_id = existing_proposal.get("proposal_id")
            else:
                from app.services.narrative_interaction_service import narrative_interaction_service
                canon_type = classification["domain"] if classification["domain"] in {"character", "world", "power", "timeline", "relationship"} else "world"
                proposal = await narrative_interaction_service.create_canon_proposal(
                    db,
                    project_id,
                    {
                        "canon_type": canon_type,
                        "subject": classification["subject"],
                        "field": classification["field"],
                        "value": classification["value"],
                        "confidence": classification["confidence"],
                        "evidence": [provenance["source_excerpt"]],
                    },
                    source_type="author_context",
                    source_id=doc["context_id"],
                )
                proposal_id = proposal.get("proposal_id")
                await db.canon_proposals.update_one(
                    {"project_id": pid, "proposal_id": proposal_id},
                    {"$set": {"source_context_id": doc["context_id"]}},
                )
        return {
            "persisted": True,
            "deduplicated": False,
            "superseded_count": superseded.modified_count,
            "entry": _serialize(doc),
            "canon_proposal_id": proposal_id,
        }

    async def list(
        self, db, project_id: str, *, domain: str | None = None, active: bool | None = True, limit: int = 500,
    ) -> list[Dict[str, Any]]:
        pid = await self._project(db, project_id)
        query: Dict[str, Any] = {"project_id": pid}
        if domain:
            query["domain"] = domain
        if active is not None:
            query["active"] = active
        rows = await db.shared_narrative_context.find(query).sort("updated_at", -1).to_list(length=limit)
        return _serialize(rows)

    async def set_active(self, db, project_id: str, context_id: str, active: bool) -> Dict[str, Any]:
        pid = await self._project(db, project_id)
        row = await db.shared_narrative_context.find_one({"project_id": pid, "context_id": context_id})
        if not row:
            raise ValueError("Shared narrative context entry not found")
        await db.shared_narrative_context.update_one(
            {"_id": row["_id"]}, {"$set": {"active": bool(active), "updated_at": datetime.utcnow()}},
        )
        return _serialize(await db.shared_narrative_context.find_one({"_id": row["_id"]}))


shared_narrative_context_service = SharedNarrativeContextService()
