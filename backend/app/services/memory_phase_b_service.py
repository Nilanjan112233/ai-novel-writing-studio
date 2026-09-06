"""Phase B derived atomic facts and compact Chapter Intelligence episodes.

Everything in this module is disposable projection data.  It never writes to
canon, decisions, planning, prose, or any structured story owner.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List
from uuid import NAMESPACE_URL, uuid5

from bson import ObjectId
from pymongo import ReturnDocument

from app.services.memory_retrieval_policy import BAD_AUTHORITY_STATUSES, authority_level, canonical_source_id, normalized_values, owner_source_version


DERIVATION_VERSION = 1
DERIVABLE_SOURCE_TYPES = {
    "canon", "decision", "chapter_plan", "character", "relationship", "world",
    "plot_thread", "timeline_v2", "knowledge", "artifact", "mystery",
    "chapter_intelligence",
}
_AUTHORITY_PRIORITY = {"canon": 600, "author_decision": 550, "confirmed_planning": 500, "structured_owner": 400, "project": 350, "derived": 100}


def _clean(value: Any, *, limit: int = 700) -> str:
    if isinstance(value, dict):
        value = value.get("content") or value.get("summary") or value.get("title") or value.get("question") or value.get("change") or value
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def _unique(values: Iterable[Any], *, limit: int = 40) -> List[Any]:
    result: List[Any] = []
    seen: set[str] = set()
    for value in values:
        if value in (None, "", [], {}):
            continue
        marker = json.dumps(value, default=str, sort_keys=True, ensure_ascii=True).lower()
        if marker in seen:
            continue
        seen.add(marker)
        result.append(value)
        if len(result) >= limit:
            break
    return result


def build_episode_memory(intelligence: Dict[str, Any]) -> Dict[str, Any]:
    """Return one non-repetitive, versioned episode projection."""
    raw_changes = _unique([
        *(intelligence.get("character_changes") or []),
        *(intelligence.get("relationship_changes") or []),
        *(intelligence.get("artifact_usage") or []),
        *(intelligence.get("timeline_impact") or []),
    ], limit=12)
    changes = []
    for item in raw_changes:
        if isinstance(item, dict):
            projected = {key: _clean(item.get(key), limit=180) for key in ("character", "character_a", "character_b", "change", "status", "name", "title", "summary") if item.get(key) not in (None, "", [], {})}
            changes.append(projected or _clean(item, limit=220))
        else:
            changes.append(_clean(item, limit=220))
    mystery_progress = _unique([
        *[{"state": "introduced", **item} if isinstance(item, dict) else {"state": "introduced", "summary": item} for item in intelligence.get("mysteries_introduced") or []],
        *[{"state": "advanced", **item} if isinstance(item, dict) else {"state": "advanced", "summary": item} for item in intelligence.get("mysteries_advanced") or []],
        *[{"state": "resolved", **item} if isinstance(item, dict) else {"state": "resolved", "summary": item} for item in intelligence.get("mysteries_resolved") or []],
    ], limit=12)
    knowledge = []
    for item in intelligence.get("knowledge_revealed") or []:
        if isinstance(item, dict):
            compact = {key: (_clean(item.get(key), limit=220) if key in {"title", "content"} else item.get(key)) for key in ("entry_id", "title", "content", "known_by", "not_known_by") if item.get(key) not in (None, "", [], {})}
            knowledge.append(compact)
        else:
            knowledge.append(_clean(item))
    episode = {
        "episode_id": str(uuid5(NAMESPACE_URL, f"novelforge:episode:{intelligence.get('project_id')}:{intelligence.get('intelligence_id')}:{intelligence.get('chapter_draft_version') or intelligence.get('version_number') or 1}:d{DERIVATION_VERSION}")),
        "derivation_version": DERIVATION_VERSION,
        "chapter_number": int(intelligence.get("chapter_number") or 0),
        "scene_scope": intelligence.get("scene_scope") or [],
        "source_version": int(intelligence.get("chapter_draft_version") or intelligence.get("version_number") or 1),
        "summary": _clean(intelligence.get("chapter_summary"), limit=500),
        "material_events": [_clean(item, limit=220) for item in _unique(intelligence.get("important_events") or [], limit=8)],
        "participants": [_clean(item, limit=100) for item in _unique(intelligence.get("characters_present") or [], limit=20)],
        "state_changes": changes,
        "knowledge_changes": _unique(knowledge, limit=10),
        "mystery_progress": mystery_progress,
        "open_obligations": [_clean(item, limit=180) for item in _unique([
            *(intelligence.get("future_obligations") or []),
            *(intelligence.get("unresolved_questions") or []),
        ], limit=10)],
        "evidence_pointer": {
            "source_type": "chapter_intelligence",
            "logical_source_id": str(intelligence.get("intelligence_id") or ""),
            "source_version": int(intelligence.get("chapter_draft_version") or intelligence.get("version_number") or 1),
            "chapter_draft_id": str(intelligence.get("chapter_draft_id") or ""),
            "chapter_number": int(intelligence.get("chapter_number") or 0),
        },
        "authority_class": "derived",
        "status": "active" if intelligence.get("active") is not False else "historical",
    }
    return {key: value for key, value in episode.items() if value not in (None, "", [], {})}


def episode_text(intelligence: Dict[str, Any]) -> str:
    episode = intelligence.get("episode_memory") or build_episode_memory(intelligence)
    lines = [f"Chapter {episode.get('chapter_number')}: {episode.get('summary', '')}".strip()]
    labels = (
        ("Events", "material_events"), ("Changes", "state_changes"),
        ("Knowledge", "knowledge_changes"), ("Mysteries", "mystery_progress"),
        ("Open obligations", "open_obligations"),
    )
    for label, key in labels:
        values = episode.get(key) or []
        if values:
            lines.append(f"{label}: " + "; ".join(_clean(item, limit=500) for item in values))
    # This projection is the bounded retrieval unit. The complete Chapter
    # Intelligence owner and evidence pointer remain available for drill-down.
    return "\n".join(line for line in lines if line.strip())[:2800]


def compact_episode_packet(intelligence: Dict[str, Any]) -> Dict[str, Any]:
    """Small prompt projection; the complete episode remains persisted."""
    episode = intelligence.get("episode_memory") or build_episode_memory(intelligence)
    projected = {
        "episode_id": episode.get("episode_id"),
        "chapter_number": episode.get("chapter_number"),
        "source_version": episode.get("source_version"),
        "summary": _clean(episode.get("summary"), limit=360),
        "events": [_clean(item, limit=140) for item in (episode.get("material_events") or [])[:4]],
        "changes": [_clean(item, limit=140) for item in (episode.get("state_changes") or [])[:4]],
        "knowledge": [_clean(item, limit=140) for item in (episode.get("knowledge_changes") or [])[:4]],
        "mysteries": [_clean(item, limit=140) for item in (episode.get("mystery_progress") or [])[:4]],
        "open_obligations": [_clean(item, limit=140) for item in (episode.get("open_obligations") or [])[:4]],
        "evidence_pointer": episode.get("evidence_pointer"),
        "authority_class": "derived",
    }
    return {key: value for key, value in projected.items() if value not in (None, "", [], {})}


def compact_chapter_memory_context(packet: Dict[str, Any]) -> Dict[str, Any]:
    """Strip compatibility fields from the specialist-only episode packet."""
    return {
        "recent": [
            {key: item.get(key) for key in ("intelligence_id", "chapter_number", "title", "episode") if item.get(key) not in (None, "", [], {})}
            for item in (packet.get("recent") or [])[-12:]
        ],
        "long_range_obligations": [
            {key: item.get(key) for key in ("intelligence_id", "chapter_number", "title", "future_obligations", "evidence_pointer") if item.get(key) not in (None, "", [], {})}
            for item in (packet.get("long_range_obligations") or [])[:12]
        ],
    }


def _observations(source_type: str, owner: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    def add(subject: Any, predicate: str, value: Any, *, known_by=None, not_known_by=None, chapter=None, confidence=1.0):
        value_text = _clean(value)
        subject_text = _clean(subject, limit=180) or source_type
        if not value_text:
            return
        rows.append({
            "subject": subject_text,
            "predicate": predicate,
            "compact_value": value_text,
            "known_by": list(known_by or []),
            "not_known_by": list(not_known_by or []),
            "source_chapter": chapter,
            "confidence": confidence,
        })

    chapter = owner.get("chapter_number") or owner.get("source_chapter")
    if source_type == "canon":
        add(owner.get("subject") or "canon", owner.get("field") or owner.get("canon_type") or "fact", owner.get("fact") or owner.get("value") or owner.get("content"), chapter=chapter)
    elif source_type == "decision":
        add(owner.get("subject") or owner.get("question_text") or "author decision", "decision", owner.get("decision") or owner.get("answer"), chapter=chapter)
    elif source_type == "relationship":
        pair = " / ".join(filter(None, [_clean(owner.get("character_a"), limit=100), _clean(owner.get("character_b"), limit=100)]))
        add(pair or owner.get("relationship_id"), "relationship_state", owner.get("relationship") or owner.get("type") or owner.get("status"), chapter=chapter)
    elif source_type == "artifact":
        subject = owner.get("name") or owner.get("item") or owner.get("artifact_id")
        add(subject, "owner", owner.get("owner"), chapter=chapter)
        add(subject, "state", owner.get("status"), chapter=chapter)
    elif source_type == "knowledge":
        add(owner.get("subject") or owner.get("title") or owner.get("entry_id"), "knowledge", owner.get("content") or owner.get("fact") or owner.get("knowledge"), known_by=owner.get("known_by"), not_known_by=owner.get("not_known_by"), chapter=chapter)
    elif source_type == "mystery":
        add(owner.get("question") or owner.get("mystery_id"), "mystery_state", owner.get("status") or "open", chapter=chapter)
        if owner.get("truth"):
            add(owner.get("question") or owner.get("mystery_id"), "mystery_truth", owner.get("truth"), known_by=owner.get("known_by"), not_known_by=owner.get("not_known_by"), chapter=chapter)
    elif source_type in {"timeline_v2", "plot_thread", "chapter_plan", "character", "world"}:
        subject = owner.get("title") or owner.get("name") or canonical_source_id(source_type, owner)
        value = owner.get("summary") or owner.get("description") or owner.get("purpose") or owner.get("current_arc_state") or owner.get("world_rules")
        add(subject, {"timeline_v2": "timeline_event", "plot_thread": "plot_thread_state", "chapter_plan": "planned_event", "character": "character_state", "world": "world_rule"}[source_type], value, chapter=chapter)
    elif source_type == "chapter_intelligence":
        for event in owner.get("important_events") or []:
            add(f"Chapter {chapter}", "event", event, chapter=chapter, confidence=0.92)
        for item in owner.get("character_changes") or []:
            add((item or {}).get("character") if isinstance(item, dict) else f"Chapter {chapter}", "character_change", (item or {}).get("change") if isinstance(item, dict) else item, chapter=chapter, confidence=0.9)
        for item in owner.get("relationship_changes") or []:
            if isinstance(item, dict):
                pair = " / ".join(filter(None, [_clean(item.get("character_a"), limit=100), _clean(item.get("character_b"), limit=100)]))
                add(pair or item.get("relationship_id"), "relationship_observation", item.get("status") or item.get("future_payoff") or item, chapter=chapter, confidence=0.85)
        for item in owner.get("knowledge_revealed") or []:
            if isinstance(item, dict):
                add(item.get("title") or item.get("entry_id") or f"Chapter {chapter}", "knowledge", item.get("content") or item.get("title"), known_by=item.get("known_by"), not_known_by=item.get("not_known_by"), chapter=chapter, confidence=0.9)
        for item in owner.get("artifact_usage") or []:
            add((item or {}).get("name") if isinstance(item, dict) else item, "artifact_observation", (item or {}).get("status") if isinstance(item, dict) else "used", chapter=chapter, confidence=0.8)
        for item in owner.get("future_obligations") or []:
            add(f"Chapter {chapter}", "open_obligation", item, chapter=chapter, confidence=0.85)
    return rows


def derive_atomic_documents(project_id: str, source_type: str, owner: Dict[str, Any]) -> List[Dict[str, Any]]:
    if source_type not in DERIVABLE_SOURCE_TYPES:
        return []
    logical_source_id = canonical_source_id(source_type, owner)
    source_version = owner_source_version(owner)
    authority = authority_level(source_type, owner)
    unsafe_owner_statuses = set(normalized_values(owner.get("status"))) & BAD_AUTHORITY_STATUSES
    pointer = {
        "source_type": source_type,
        "logical_source_id": logical_source_id,
        "source_version": source_version,
        "physical_source_id": str(owner.get("_id") or ""),
    }
    results = []
    for observation in _observations(source_type, owner):
        normalized = "|".join([
            observation["subject"].lower(), observation["predicate"].lower(),
            observation["compact_value"].lower(),
            ",".join(sorted(str(item).lower() for item in observation.get("known_by") or [])),
            str(observation.get("source_chapter") or ""),
        ])
        fact_key = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        memory_id = str(uuid5(NAMESPACE_URL, f"novelforge:atomic:{project_id}:{fact_key}:d{DERIVATION_VERSION}"))
        chapter = observation.get("source_chapter")
        owner_key = f"{source_type}:{logical_source_id}:v{source_version}"
        results.append({
            "project_id": ObjectId(project_id),
            "memory_id": memory_id,
            "fact_key": fact_key,
            "subject": observation["subject"],
            "predicate": observation["predicate"],
            "compact_value": observation["compact_value"],
            "content": f"{observation['subject']}: {observation['compact_value']}",
            "source_owners": [pointer],
            "source_versions": [source_version],
            "evidence_pointers": [pointer],
            "source_chapter": chapter,
            "valid_from_chapter": owner.get("valid_from_chapter") or chapter,
            "valid_to_chapter": owner.get("valid_to_chapter"),
            "valid_from_scene": owner.get("valid_from_scene"),
            "valid_to_scene": owner.get("valid_to_scene"),
            "known_by": observation.get("known_by") or [],
            "not_known_by": observation.get("not_known_by") or [],
            "knowledge_scope": "character" if observation.get("known_by") or observation.get("not_known_by") else "story_truth",
            "entity_refs": [observation["subject"]],
            "authority_class": authority,
            "authority_status": owner.get("authority_status"),
            # Atomic lifecycle status remains active/historical. Preserve an
            # owner's candidate/rejected state independently so the P0 policy
            # cannot lose it during derivation.
            "candidate_status": owner.get("candidate_status") or (next(iter(unsafe_owner_statuses)) if unsafe_owner_statuses else None),
            "approval_status": owner.get("approval_status"),
            "confidence": observation.get("confidence", 1.0),
            "status": "active" if owner.get("active") is not False else "historical",
            "active": owner.get("active") is not False,
            "derivation_version": DERIVATION_VERSION,
            "owner_key": owner_key,
            "owner_keys": [owner_key],
            "version_number": source_version,
            "provenance": {"derivation": "phase_b_deterministic", "evidence": [pointer]},
        })
        results[-1]["derivation_hash"] = hashlib.sha256(json.dumps(results[-1], default=str, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()
    return results


class MemoryPhaseBService:
    async def _label_conflicts(self, db, project_id: str, subject: str, predicate: str) -> int:
        query = {"project_id": ObjectId(project_id), "subject": subject, "predicate": predicate, "active": {"$ne": False}}
        rows = await db.atomic_memories.find(query).to_list(length=1000)
        changed = 0
        for row in rows:
            start = int(row.get("valid_from_chapter") or row.get("source_chapter") or -10**9)
            end = int(row.get("valid_to_chapter") or 10**9)
            overlapping = [
                other for other in rows
                if str(other.get("compact_value") or "").lower() != str(row.get("compact_value") or "").lower()
                and max(start, int(other.get("valid_from_chapter") or other.get("source_chapter") or -10**9))
                <= min(end, int(other.get("valid_to_chapter") or 10**9))
            ]
            if not overlapping:
                if row.get("conflict_status") or row.get("conflicts_with"):
                    result = await db.atomic_memories.update_one({"_id": row["_id"]}, {"$unset": {"conflict_status": "", "conflicts_with": ""}})
                    changed += int(result.modified_count)
                continue
            comparison = [row, *overlapping]
            best = max(_AUTHORITY_PRIORITY.get(str(item.get("authority_class") or "derived"), 0) for item in comparison)
            best_rows = [item for item in comparison if _AUTHORITY_PRIORITY.get(str(item.get("authority_class") or "derived"), 0) == best]
            winning_values = {str(item.get("compact_value") or "").lower() for item in best_rows}
            winners = [str(item.get("memory_id")) for item in best_rows]
            value = str(row.get("compact_value") or "").lower()
            priority = _AUTHORITY_PRIORITY.get(str(row.get("authority_class") or "derived"), 0)
            status = "authority_supported" if value in winning_values else ("conflicts_with_authority" if priority < best else "unresolved_conflict")
            conflicts = [item for item in winners if item != str(row.get("memory_id"))]
            if row.get("conflict_status") == status and list(row.get("conflicts_with") or []) == conflicts:
                continue
            result = await db.atomic_memories.update_one({"_id": row["_id"]}, {"$set": {"conflict_status": status, "conflicts_with": conflicts, "updated_at": datetime.utcnow()}})
            changed += int(result.modified_count)
        return changed

    async def sync_owner(self, db, project_id: str, source_type: str, owner: Dict[str, Any]) -> Dict[str, Any]:
        if source_type not in DERIVABLE_SOURCE_TYPES:
            return {"derived": 0, "writes": 0, "invalidated": 0}
        logical_id = canonical_source_id(source_type, owner)
        version = owner_source_version(owner)
        owner_key = f"{source_type}:{logical_id}:v{version}"
        docs = derive_atomic_documents(project_id, source_type, owner)
        active_ids = [doc["memory_id"] for doc in docs]
        now = datetime.utcnow()
        writes = 0
        changed_historical: List[Dict[str, Any]] = []
        # Resolve current owner version before adding the new observations.
        # Older projections remain stored, and remain as-of eligible only when
        # the owner supplied a later chapter boundary.
        existing_rows = await db.atomic_memories.find({"project_id": ObjectId(project_id), "active": {"$ne": False}}).to_list(length=None)
        for row in existing_rows:
            matching = [pointer for pointer in row.get("source_owners") or [] if str(pointer.get("source_type")) == source_type and str(pointer.get("logical_source_id")) == logical_id and int(pointer.get("source_version") or 1) != version]
            if not matching:
                continue
            remaining = [pointer for pointer in row.get("source_owners") or [] if pointer not in matching]
            update: Dict[str, Any] = {"source_owners": remaining, "evidence_pointers": remaining, "owner_keys": [f"{item.get('source_type')}:{item.get('logical_source_id')}:v{int(item.get('source_version') or 1)}" for item in remaining], "updated_at": now}
            if not remaining:
                new_from = owner.get("valid_from_chapter") or owner.get("chapter_number") or owner.get("source_chapter")
                old_from = row.get("valid_from_chapter") or row.get("source_chapter")
                if new_from is not None and old_from is not None and int(new_from) > int(old_from):
                    update.update({"valid_to_chapter": int(new_from) - 1, "status": "historical", "active": True})
                else:
                    update.update({"status": "superseded", "active": False})
            result = await db.atomic_memories.find_one_and_update({"_id": row["_id"]}, {"$set": update}, return_document=ReturnDocument.AFTER)
            if result:
                changed_historical.append(result)
                writes += 1
        for doc in docs:
            existing = await db.atomic_memories.find_one({"project_id": ObjectId(project_id), "memory_id": doc["memory_id"]})
            if existing:
                pointers = [*(existing.get("source_owners") or []), *(doc.get("source_owners") or [])]
                unique_pointers = []
                seen_pointers = set()
                for pointer in pointers:
                    marker = (str(pointer.get("source_type")), str(pointer.get("logical_source_id")), int(pointer.get("source_version") or 1))
                    if marker not in seen_pointers:
                        seen_pointers.add(marker); unique_pointers.append(pointer)
                doc["source_owners"] = unique_pointers
                doc["evidence_pointers"] = list(unique_pointers)
                doc["source_versions"] = sorted({int(item.get("source_version") or 1) for item in unique_pointers})
                doc["owner_keys"] = sorted(set(existing.get("owner_keys") or [existing.get("owner_key")]) | {owner_key} - {None})
                current_priority = _AUTHORITY_PRIORITY.get(str(existing.get("authority_class") or "derived"), 0)
                new_priority = _AUTHORITY_PRIORITY.get(str(doc.get("authority_class") or "derived"), 0)
                if current_priority > new_priority:
                    doc["authority_class"] = existing.get("authority_class")
                doc["provenance"] = {"derivation": "phase_b_deterministic", "evidence": unique_pointers}
                hash_shape = {key: value for key, value in doc.items() if key not in {"derivation_hash", "updated_at", "created_at"}}
                doc["derivation_hash"] = hashlib.sha256(json.dumps(hash_shape, default=str, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()
            if existing and existing.get("derivation_hash") == doc.get("derivation_hash") and existing.get("active") is not False:
                continue
            doc["updated_at"] = now
            result = await db.atomic_memories.update_one(
                {"project_id": ObjectId(project_id), "memory_id": doc["memory_id"]},
                {"$set": doc, "$setOnInsert": {"created_at": now}}, upsert=True,
            )
            writes += int(bool(result.modified_count or result.upserted_id))
        invalidated_count = 0
        stale = await db.atomic_memories.find({"project_id": ObjectId(project_id), "$or": [{"owner_key": owner_key}, {"owner_keys": owner_key}], "memory_id": {"$nin": active_ids}, "active": {"$ne": False}}).to_list(length=None)
        for row in stale:
            remaining = [item for item in row.get("source_owners") or [] if f"{item.get('source_type')}:{item.get('logical_source_id')}:v{int(item.get('source_version') or 1)}" != owner_key]
            if remaining:
                result = await db.atomic_memories.update_one({"_id": row["_id"]}, {"$set": {"source_owners": remaining, "evidence_pointers": remaining, "owner_keys": [f"{item.get('source_type')}:{item.get('logical_source_id')}:v{int(item.get('source_version') or 1)}" for item in remaining], "updated_at": now}})
            else:
                result = await db.atomic_memories.update_one({"_id": row["_id"]}, {"$set": {"active": False, "status": "superseded", "updated_at": now}})
            invalidated_count += int(result.modified_count)
        for subject, predicate in {(doc["subject"], doc["predicate"]) for doc in docs}:
            writes += await self._label_conflicts(db, project_id, subject, predicate)
        refreshed = await db.atomic_memories.find({"project_id": ObjectId(project_id), "memory_id": {"$in": active_ids}}).to_list(length=None) if active_ids else []
        return {"derived": len(docs), "writes": writes, "invalidated": invalidated_count, "documents": [*changed_historical, *refreshed]}

    async def invalidate_owner(self, db, project_id: str, source_type: str, logical_source_id: str) -> int:
        prefix = f"{source_type}:{logical_source_id}:v"
        rows = await db.atomic_memories.find({"project_id": ObjectId(project_id), "active": {"$ne": False}}).to_list(length=None)
        changed = 0
        for row in rows:
            keys = row.get("owner_keys") or [row.get("owner_key")]
            matching = {key for key in keys if str(key or "").startswith(prefix)}
            if not matching:
                continue
            remaining = [item for item in row.get("source_owners") or [] if not f"{item.get('source_type')}:{item.get('logical_source_id')}:v{int(item.get('source_version') or 1)}".startswith(prefix)]
            update = {"source_owners": remaining, "evidence_pointers": remaining, "owner_keys": [key for key in keys if key not in matching], "updated_at": datetime.utcnow()}
            if not remaining:
                update.update({"active": False, "status": "superseded"})
            result = await db.atomic_memories.update_one({"_id": row["_id"]}, {"$set": update})
            changed += int(result.modified_count)
        return changed

    async def rebuild_project(self, db, project_id: str) -> Dict[str, Any]:
        """Provider-free idempotent rebuild from current owners."""
        from app.services.memory_retrieval_service import SOURCE_SPECS
        started = datetime.utcnow()
        pid = ObjectId(project_id)
        await db.atomic_memories.update_many({"project_id": pid}, {"$set": {"rebuild_seen": False}})
        owners = derived = writes = 0
        for source_type in sorted(DERIVABLE_SOURCE_TYPES):
            spec = SOURCE_SPECS.get(source_type)
            if not spec:
                continue
            async for owner in db[spec[0]].find({"project_id": pid}):
                owners += 1
                if source_type == "chapter_intelligence":
                    episode = build_episode_memory(owner)
                    if owner.get("episode_memory") != episode or int(owner.get("episode_derivation_version") or 0) != DERIVATION_VERSION:
                        await db.chapter_intelligence.update_one(
                            {"_id": owner["_id"]},
                            {"$set": {"episode_memory": episode, "episode_derivation_version": DERIVATION_VERSION}},
                        )
                        owner = {**owner, "episode_memory": episode, "episode_derivation_version": DERIVATION_VERSION}
                result = await self.sync_owner(db, project_id, source_type, owner)
                derived += int(result["derived"]); writes += int(result["writes"])
                if result["documents"]:
                    await db.atomic_memories.update_many({"project_id": pid, "memory_id": {"$in": [item["memory_id"] for item in result["documents"]]}}, {"$set": {"rebuild_seen": True}})
        invalidated = await db.atomic_memories.update_many({"project_id": pid, "rebuild_seen": {"$ne": True}, "active": {"$ne": False}}, {"$set": {"active": False, "status": "superseded", "updated_at": datetime.utcnow()}})
        count = await db.atomic_memories.count_documents({"project_id": pid, "active": {"$ne": False}})
        digest_rows = await db.atomic_memories.find({"project_id": pid, "active": {"$ne": False}}, {"memory_id": 1, "fact_key": 1}).sort("memory_id", 1).to_list(length=None)
        logical_hash = hashlib.sha256(json.dumps(digest_rows, default=str, sort_keys=True).encode("utf-8")).hexdigest()
        finished = datetime.utcnow()
        await db.memory_phase_b_checkpoints.update_one({"project_id": pid}, {"$set": {
            "project_id": pid, "status": "READY", "complete": True, "derivation_version": DERIVATION_VERSION,
            "owner_records": owners, "atomic_records": count, "logical_hash": logical_hash,
            "provider_calls": 0, "last_rebuild": finished, "updated_at": finished,
        }, "$setOnInsert": {"created_at": started}}, upsert=True)
        return {"status": "READY", "owners": owners, "atomic_records": count, "derived_observations": derived, "writes": writes, "invalidated": int(invalidated.modified_count), "logical_hash": logical_hash, "provider_calls": 0, "duration_ms": round((finished - started).total_seconds() * 1000, 3)}


def compact_retrieval_hit(item: Dict[str, Any]) -> Dict[str, Any]:
    metadata = item.get("metadata") or {}
    return {key: value for key, value in {
        "content": _clean(item.get("content"), limit=1100),
        "score": item.get("score"),
        "source_type": item.get("source_type"),
        "source_id": item.get("source_id"),
        "logical_identity": metadata.get("logical_identity") or item.get("logical_identity"),
        "authority_level": metadata.get("authority_level") or item.get("authority_level"),
        "validity": metadata.get("validity") or item.get("validity"),
        "chapter_number": metadata.get("chapter_number"),
        "known_by": metadata.get("known_by") or [],
        "evidence_pointer": metadata.get("evidence_pointer") or metadata.get("evidence_pointers") or metadata.get("provenance"),
        "why_selected": metadata.get("why_selected") or item.get("why_selected"),
        "rank": metadata.get("rank") or item.get("rank"),
    }.items() if value not in (None, "", [], {})}


memory_phase_b_service = MemoryPhaseBService()
