"""Governed projections for knowledge noticed in conversation or approved prose.

Projected records live in the existing owner collections, but remain visibly
candidate-only until an author confirms them. Candidate records are excluded
from authoritative context queries by ``authority_status``.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List
from uuid import uuid4

from bson import ObjectId

from app.services.project_event_service import emit_project_event
from app.services.story_bible_service import rebuild_story_bible


def _clean(value: Any) -> str:
    return " ".join(str(value or "").replace("\u00a0", " ").split()).strip()


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _clean(value).lower()).strip()


def _candidate_id(project_id: str, item: Dict[str, Any], source_chapter: int | None, index: int = 0) -> str:
    raw = "|".join([project_id, str(source_chapter or ""), str(item.get("type") or ""), _clean(item.get("value") or item.get("subject") or item.get("description")), str(index)])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:24]


def _source_text(item: Dict[str, Any]) -> str:
    return _clean(item.get("subject") or item.get("description") or item.get("value") or item.get("content"))


def _character_name(text: str) -> str:
    first = re.split(r"\s[-–—]\s|,", text, maxsplit=1)[0].strip()
    return first[:120]


def _planning_character_name(text: str) -> str:
    first = _character_name(text)
    if ":" in first:
        first = first.split(":", 1)[0].strip()
    subject = re.match(r"^(?:the\s+|a\s+|an\s+)?([A-Z][\w'\-]*(?:\s+[A-Z][\w'\-]*)?)\s+(?:is|was|has|had|seems|appears|becomes|remains)\b", first)
    if not subject:
        # Planning capture sometimes describes a character through an
        # intentional relationship or desire instead of using "is":
        # "Ivo distrusts Mara at first" should project to Ivo, not create a
        # character whose name is the entire sentence.
        subject = re.match(
            r"^([A-Z][\w'\-]*)\s+(?:distrusts|trusts|wants|needs|fears|loves|hates|protects|follows|avoids|seeks|hides|knows|believes|becomes|changes)\b",
            first,
        )
    return subject.group(1).strip() if subject else first


def _pair(text: str) -> tuple[str, str] | None:
    match = re.search(r"(?:^|\b)([A-Z][\w'’-]*(?:\s+[A-Z][\w'’-]*)?)\s+and\s+([A-Z][\w'’-]*(?:\s+[A-Z][\w'’-]*)?)\s+(?:are|were|have|had|share|remain|become)\b", text)
    if match:
        return _clean(match.group(1)), _clean(match.group(2))
    directed = re.search(r"(?:^|\b)([A-Z][A-Za-z0-9'_-]*)\s+(?:distrusts|trusts|loves|hates|protects|fears|avoids|follows|owes|needs)\s+([A-Z][A-Za-z0-9'_-]*)\b", text)
    if directed:
        return _clean(directed.group(1)), _clean(directed.group(2))
    return None


def _provenance(source_type: str, source_id: str | None, chapter: int | None) -> Dict[str, Any]:
    return {
        "source_type": source_type,
        "source_id": source_id,
        "source_chapter": chapter,
        "authority_status": "candidate",
        "candidate_status": "pending",
        "provenance": {"source_type": source_type, "source_id": source_id, "chapter_number": chapter},
    }


class StoryKnowledgeProjectionService:
    async def repair_confirmed_projection_statuses(self, db, project_id: str) -> bool:
        """Bring legacy confirmed projections into the owning model's normal status vocabulary."""
        pid = ObjectId(project_id)
        changed_any = False
        for collection, field, value in (
            ("relationship_graphs", "status", "active"),
            ("mystery_registry", "status", "open"),
            ("plot_threads", "status", "open"),
            ("timeline_entries", "status", "planned"),
            ("artifact_registry", "status", "active"),
            ("knowledge_entries", "status", "active"),
            ("story_arcs", "development_status", "planned"),
        ):
            result = await db[collection].update_many(
                {"project_id": pid, "authority_status": "confirmed", field: "candidate"},
                {"$set": {field: value, "updated_at": datetime.utcnow()}},
            )
            changed_any = changed_any or result.modified_count > 0
        world = await db.world_bibles.find_one({"project_id": pid})
        if world:
            world_changed = False
            rules = list(world.get("world_rules") or [])
            locations = list(world.get("locations") or [])
            for item in world.get("suggested_world_facts") or []:
                if not isinstance(item, dict) or item.get("authority_status") != "confirmed":
                    continue
                value = _clean(item.get("text"))
                if not value:
                    continue
                target = locations if item.get("candidate_kind") == "location" else rules
                if not any(_norm(entry.get("description") if isinstance(entry, dict) else entry) == _norm(value) for entry in target):
                    target.append({"name": value, "description": value, "source": item.get("source_type") or "Story knowledge"} if target is locations else value)
                    world_changed = True
            if world_changed:
                await db.world_bibles.update_one({"_id": world["_id"]}, {"$set": {"world_rules": rules, "locations": locations, "updated_at": datetime.utcnow()}})
                changed_any = True
        return changed_any

    async def normalize_planning_character_names(self, db, project_id: str) -> int:
        """Repair legacy planning captures whose display name contains the sentence."""
        pid = ObjectId(project_id)
        changed = 0
        docs = await db.character_bibles.find({"project_id": pid, "source_type": "story_studio_planning"}).to_list(length=1000)
        for doc in docs:
            raw_name = _clean(doc.get("name"))
            normalized_name = _planning_character_name(raw_name)
            if normalized_name and normalized_name != raw_name and (
                " is " in raw_name.lower()
                or ":" in raw_name
                or re.match(r"^[A-Z][\w'\-]*\s+(?:distrusts|trusts|wants|needs|fears|loves|hates|protects|follows|avoids|seeks|hides|knows|believes|becomes|changes)\b", raw_name)
            ):
                result = await db.character_bibles.update_one({"_id": doc["_id"]}, {"$set": {"name": normalized_name, "updated_at": datetime.utcnow()}})
                changed += result.modified_count
        return changed

    async def project_candidates(
        self,
        db,
        project_id: str,
        candidates: Iterable[Dict[str, Any]],
        *,
        source_type: str,
        source_id: str | None = None,
        source_chapter: int | None = None,
    ) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        counts: Dict[str, int] = {}
        projected: List[Dict[str, Any]] = []
        for index, raw in enumerate(candidates):
            if not isinstance(raw, dict):
                continue
            kind = _clean(raw.get("type") or raw.get("candidate_type")).lower()
            text = _source_text(raw)
            if not kind or not text or len(text) < 3:
                continue
            candidate_id = str(raw.get("candidate_id") or _candidate_id(project_id, raw, source_chapter, index))
            meta = _provenance(source_type, source_id, source_chapter)
            meta.update({"candidate_id": candidate_id, "confidence": raw.get("confidence"), "updated_at": datetime.utcnow()})
            saved = await self._project_one(db, pid, kind, text, raw, meta)
            if saved:
                counts[kind] = counts.get(kind, 0) + 1
                projected.append({"candidate_id": candidate_id, "type": kind, "label": saved})

        if projected:
            await emit_project_event(db, project_id, "story_knowledge_candidates_projected", payload={"source_type": source_type, "source_chapter": source_chapter, "counts": counts})
        return {"counts": counts, "projected": projected, "status": "candidate"}

    async def _project_one(self, db, pid: ObjectId, kind: str, text: str, raw: Dict[str, Any], meta: Dict[str, Any]) -> str | None:
        now = meta["updated_at"]
        if kind == "character":
            name = _planning_character_name(text)
            if not name or len(name) < 2 or _norm(name) in {"the", "neither", "about", "water", "three", "four", "reeds", "because", "one", "even", "give", "behind", "let", "but", "which", "straight", "follow", "ahead", "just", "last", "said", "did", "open", "stay", "toward", "and", "you", "your", "nothing", "thank", "constable", "councillor", "didn", "her", "found", "she", "came", "his", "searched", "left", "mill street", "bellwether", "northglass", "about elias", "but ivo", "and elias", "harlow", "below", "told", "yes", "look", "darkness", "somewhere", "toward bellwether", "toward vale"}:
                return None
            existing = await db.character_bibles.find_one({"project_id": pid, "name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}, "authority_status": {"$ne": "rejected"}})
            if not existing:
                for possible in await db.character_bibles.find({"project_id": pid, "authority_status": {"$in": ["candidate", "suggested"]}}).to_list(length=100):
                    possible_name = _norm(possible.get("name"))
                    if _norm(name) in possible_name.split():
                        existing = possible
                        break
                    if possible_name in _norm(name).split() and len(possible_name) < len(_norm(name)):
                        await db.character_bibles.update_one({"_id": possible["_id"]}, {"$set": {"name": name, "description": text, "updated_at": now}, "$addToSet": {"source_chapters": meta.get("source_chapter")}})
                        return name
            if existing and str(existing.get("authority_status") or "approved") not in {"candidate", "suggested"}:
                existing_description = _norm(existing.get("description") or existing.get("current_arc_state") or "")
                incoming_description = _norm(text)
                if existing_description and incoming_description and existing_description != incoming_description and incoming_description not in existing_description and existing_description not in incoming_description:
                    conflict_doc = {"project_id": pid, "name": name, "description": text, "role": "", "goals": [], "fears": [], "future_payoffs": [], "reconciliation_status": "conflict", "conflicts_with": str(existing.get("_id") or existing.get("candidate_id") or ""), **meta}
                    await db.character_bibles.update_one({"project_id": pid, "candidate_id": meta["candidate_id"]}, {"$set": conflict_doc, "$setOnInsert": {"created_at": now}}, upsert=True)
                    return name
                return name
            if existing and str(existing.get("authority_status") or "") in {"candidate", "suggested"}:
                existing_name = _clean(existing.get("name"))
                keep_existing_name = len(_norm(existing_name)) > len(_norm(name)) and _norm(name) in _norm(existing_name).split()
                await db.character_bibles.update_one({"_id": existing["_id"]}, {"$addToSet": {"source_chapters": meta.get("source_chapter")}, "$set": {"name": existing_name if keep_existing_name else name, "description": text, "updated_at": now}})
                return existing_name if keep_existing_name else name
            doc = {"project_id": pid, "name": name, "description": text, "role": "", "goals": [], "fears": [], "future_payoffs": [], "source_type": meta["source_type"], "source_id": meta.get("source_id"), "source_chapter": meta["source_chapter"], "source_chapters": [meta.get("source_chapter")], "authority_status": "candidate", "candidate_status": "pending", "candidate_id": meta["candidate_id"], "provenance": meta["provenance"], "updated_at": now}
            await db.character_bibles.update_one({"project_id": pid, "candidate_id": meta["candidate_id"]}, {"$set": doc, "$setOnInsert": {"created_at": now}}, upsert=True)
            return name

        if kind == "relationship":
            pair = _pair(text)
            if not pair:
                return None
            a, b = pair
            doc = {"project_id": pid, "character_a": a, "character_b": b, "type": "suggested relationship", "relationship": text, "status": "candidate", **meta}
            await db.relationship_graphs.update_one({"project_id": pid, "candidate_id": meta["candidate_id"]}, {"$set": doc, "$setOnInsert": {"created_at": now}}, upsert=True)
            return f"{a} and {b}"

        if kind in {"world_fact", "location"}:
            world = await db.world_bibles.find_one({"project_id": pid}) or {"project_id": pid}
            facts = list(world.get("suggested_world_facts") or [])
            if not any(_norm(item.get("text")) == _norm(text) for item in facts if isinstance(item, dict)):
                facts.append({"candidate_id": meta["candidate_id"], "text": text, "candidate_kind": kind, **{key: value for key, value in meta.items() if key != "updated_at"}})
                await db.world_bibles.update_one({"project_id": pid}, {"$set": {"suggested_world_facts": facts, "updated_at": now}, "$setOnInsert": {"created_at": now}}, upsert=True)
            return text

        if kind in {"mystery", "foreshadowing", "unresolved_element"}:
            question = text
            doc = {"project_id": pid, "question": question, "setup": question, "truth": "", "status": "candidate", "reveal_target": "", **meta}
            await db.mystery_registry.update_one({"project_id": pid, "candidate_id": meta["candidate_id"]}, {"$set": doc, "$setOnInsert": {"created_at": now}}, upsert=True)
            return question

        if kind in {"plot_thread", "promise"}:
            doc = {"project_id": pid, "title": text[:160], "description": text, "status": "candidate", **meta}
            await db.plot_threads.update_one({"project_id": pid, "candidate_id": meta["candidate_id"]}, {"$set": doc, "$setOnInsert": {"created_at": now}}, upsert=True)
            return text

        if kind == "arc":
            doc = {"project_id": pid, "arc_id": f"candidate-{meta['candidate_id']}", "title": text[:160], "goal": text, "order": 5000, "development_status": "candidate", "approval_status": "candidate", **meta}
            await db.story_arcs.update_one({"project_id": pid, "candidate_id": meta["candidate_id"]}, {"$set": doc, "$setOnInsert": {"created_at": now}}, upsert=True)
            return text

        if kind == "author_intention":
            doc = {"project_id": pid, "question_id": f"candidate-{meta['candidate_id']}", "text": text, "story_area": "author intention", "answered": False, "status": "candidate", **meta}
            await db.questions.update_one({"project_id": pid, "candidate_id": meta["candidate_id"]}, {"$set": doc, "$setOnInsert": {"created_at": now}}, upsert=True)
            return text

        if kind == "timeline_event":
            doc = {"project_id": pid, "entry_id": str(uuid4()), "title": text[:160], "summary": text, "importance": "major", "status": "candidate", "certainty": "unknown", "order": int((meta.get("source_chapter") or 0) * 1000), **meta}
            await db.timeline_entries.update_one({"project_id": pid, "candidate_id": meta["candidate_id"]}, {"$set": doc, "$setOnInsert": {"created_at": now}}, upsert=True)
            return text

        if kind == "artifact":
            item = _character_name(text)
            doc = {"project_id": pid, "artifact_id": str(uuid4()), "item": item, "history": text, "status": "candidate", **meta}
            await db.artifact_registry.update_one({"project_id": pid, "candidate_id": meta["candidate_id"]}, {"$set": doc, "$setOnInsert": {"created_at": now}}, upsert=True)
            return item

        if kind == "knowledge_change":
            doc = {"project_id": pid, "entry_id": str(uuid4()), "title": text[:160], "content": text, "knowledge_type": "CHARACTER_KNOWLEDGE", "status": "candidate", **meta}
            await db.knowledge_entries.update_one({"project_id": pid, "candidate_id": meta["candidate_id"]}, {"$set": doc, "$setOnInsert": {"created_at": now}}, upsert=True)
            return text
        return None

    async def list_candidates(self, db, project_id: str) -> List[Dict[str, Any]]:
        pid = ObjectId(project_id)
        needs_rebuild = (await self.normalize_planning_character_names(db, project_id)) > 0
        needs_rebuild = (await self.repair_confirmed_projection_statuses(db, project_id)) or needs_rebuild
        latest_bible = await db.story_bibles.find_one({"project_id": pid}, sort=[("updated_at", -1)])
        if latest_bible and latest_bible.get("updated_at"):
            for collection in ("character_bibles", "relationship_graphs", "mystery_registry", "plot_threads", "story_arcs", "questions", "timeline_entries", "artifact_registry", "knowledge_entries"):
                latest_confirmed = await db[collection].find_one({"project_id": pid, "authority_status": "confirmed"}, sort=[("updated_at", -1)])
                if latest_confirmed and latest_confirmed.get("updated_at") and latest_confirmed["updated_at"] > latest_bible["updated_at"]:
                    needs_rebuild = True
                    break
        if needs_rebuild:
            await rebuild_story_bible(db, project_id)
        rows: List[Dict[str, Any]] = []
        for collection, kind in [("character_bibles", "character"), ("relationship_graphs", "relationship"), ("mystery_registry", "mystery"), ("plot_threads", "plot_thread"), ("story_arcs", "arc"), ("questions", "author_intention"), ("timeline_entries", "timeline_event"), ("artifact_registry", "artifact"), ("knowledge_entries", "knowledge_change")]:
            docs = await db[collection].find({"project_id": pid, "authority_status": "candidate", "candidate_status": "pending"}).to_list(length=1000)
            for doc in docs:
                if kind == "character" and doc.get("source_type") == "story_studio_planning":
                    raw_name = _clean(doc.get("name"))
                    normalized_name = _planning_character_name(raw_name)
                    if normalized_name and normalized_name != raw_name and (" is " in raw_name.lower() or ":" in raw_name):
                        await db[collection].update_one({"_id": doc["_id"]}, {"$set": {"name": normalized_name, "updated_at": datetime.utcnow()}})
                        doc["name"] = normalized_name
                doc.pop("_id", None)
                doc["type"] = kind
                doc["project_id"] = str(doc.get("project_id"))
                rows.append(doc)
        world = await db.world_bibles.find_one({"project_id": pid}) or {}
        for item in world.get("suggested_world_facts") or []:
            if isinstance(item, dict) and item.get("candidate_status") == "pending":
                rows.append({**item, "type": "world_fact"})
        return rows

    async def confirmed_planning_context(self, db, project_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        """Return confirmed planning captured through Story Studio.

        This is a read projection over the existing owner collections. It is
        intentionally separate from raw chat and excludes candidates, rejected
        records, and stale authority.
        """
        pid = ObjectId(project_id)
        rows: List[Dict[str, Any]] = []
        specs = (
            ("character_bibles", "character", ("name", "description", "role")),
            ("relationship_graphs", "relationship", ("character_a", "character_b", "relationship", "type")),
            ("mystery_registry", "mystery", ("question", "setup", "reveal_target")),
            ("plot_threads", "plot_thread", ("title", "description", "status")),
            ("story_arcs", "arc", ("title", "goal", "order")),
            ("timeline_entries", "timeline_event", ("title", "summary", "order")),
            ("artifact_registry", "artifact", ("item", "history", "status")),
            ("knowledge_entries", "knowledge_change", ("title", "content", "knowledge_type")),
            ("questions", "author_intention", ("text", "story_area", "answer")),
        )
        for collection, kind, fields in specs:
            docs = await db[collection].find({"project_id": pid, "source_type": "story_studio_planning", "authority_status": "confirmed"}).sort("updated_at", -1).to_list(length=limit)
            for doc in docs:
                values = {field: doc.get(field) for field in fields if doc.get(field) not in (None, "", [])}
                if not values:
                    continue
                rows.append({
                    "type": kind,
                    "values": values,
                    "source": "Story Studio planning",
                    "source_id": str(doc.get("source_id") or doc.get("candidate_id") or ""),
                    "updated_at": doc.get("updated_at"),
                })
        world = await db.world_bibles.find_one({"project_id": pid})
        for item in (world or {}).get("suggested_world_facts") or []:
            if isinstance(item, dict) and item.get("source_type") == "story_studio_planning" and item.get("authority_status") == "confirmed":
                rows.append({
                    "type": item.get("candidate_kind") or "world_fact",
                    "values": {"text": item.get("text")},
                    "source": "Story Studio planning",
                    "source_id": str(item.get("source_id") or item.get("candidate_id") or ""),
                    "updated_at": item.get("updated_at"),
                })
        return rows[:limit]

    async def decide(self, db, project_id: str, candidate_id: str, decision: str) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        decision = _clean(decision).lower()
        if decision not in {"confirm", "reject", "reconsider"}:
            raise ValueError("decision must be confirm, reject, or reconsider")
        changed = 0
        for collection in ("character_bibles", "relationship_graphs", "mystery_registry", "plot_threads", "story_arcs", "questions", "timeline_entries", "artifact_registry", "knowledge_entries"):
            query_status = "rejected" if decision == "reconsider" else "candidate"
            status_updates = {
                "candidate_status": "pending" if decision == "reconsider" else ("confirmed" if decision == "confirm" else "rejected"),
                "authority_status": "candidate" if decision == "reconsider" else ("confirmed" if decision == "confirm" else "rejected"),
                "approval_status": "candidate" if decision == "reconsider" else ("approved" if decision == "confirm" else "rejected"),
                "updated_at": datetime.utcnow(),
            }
            if decision == "confirm":
                status_updates.update({
                    "mystery_registry": {"status": "open"},
                    "plot_threads": {"status": "open"},
                    "story_arcs": {"development_status": "planned"},
                    "timeline_entries": {"status": "planned"},
                    "artifact_registry": {"status": "active"},
                    "knowledge_entries": {"status": "active"},
                    "relationship_graphs": {"status": "active"},
                }.get(collection, {}))
            result = await db[collection].update_one({"project_id": pid, "candidate_id": candidate_id, "authority_status": query_status}, {"$set": status_updates})
            changed += result.modified_count
        world = await db.world_bibles.find_one({"project_id": pid})
        if world:
            facts = list(world.get("suggested_world_facts") or [])
            touched = False
            for item in facts:
                if isinstance(item, dict) and item.get("candidate_id") == candidate_id:
                    item["candidate_status"] = "pending" if decision == "reconsider" else ("confirmed" if decision == "confirm" else "rejected")
                    item["authority_status"] = "candidate" if decision == "reconsider" else ("confirmed" if decision == "confirm" else "rejected")
                    if decision == "confirm":
                        field = "locations" if item.get("candidate_kind") == "location" else "world_rules"
                        existing_values = list(world.get(field) or [])
                        value = item.get("text") or ""
                        if value and not any(_norm(entry.get("description") if isinstance(entry, dict) else entry) == _norm(value) for entry in existing_values):
                            existing_values.append({"name": value, "description": value, "source": item.get("source_type") or "Story knowledge"} if field == "locations" else value)
                            world[field] = existing_values
                    touched = True
            if touched:
                update = {"suggested_world_facts": facts, "updated_at": datetime.utcnow()}
                if decision == "confirm":
                    update.update({key: world[key] for key in ("world_rules", "locations") if key in world})
                await db.world_bibles.update_one({"_id": world["_id"]}, {"$set": update})
                changed += 1
        if decision == "confirm":
            # Confirmed candidates are now part of the owning structured model.
            # Canon promotion remains a separate existing governance decision.
            await rebuild_story_bible(db, project_id)
            await emit_project_event(db, project_id, "story_knowledge_candidate_confirmed", payload={"candidate_id": candidate_id})
        elif decision == "reconsider":
            await emit_project_event(db, project_id, "story_knowledge_candidate_reconsidered", payload={"candidate_id": candidate_id})
        else:
            await emit_project_event(db, project_id, "story_knowledge_candidate_rejected", payload={"candidate_id": candidate_id})
        return {"candidate_id": candidate_id, "decision": decision, "changed": changed}


story_knowledge_projection_service = StoryKnowledgeProjectionService()
