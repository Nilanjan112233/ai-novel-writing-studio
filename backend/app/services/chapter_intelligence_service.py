"""Deterministic, versioned chapter intelligence and bounded chapter memory."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Iterable
from uuid import NAMESPACE_URL, uuid5

from bson import ObjectId

from app.services.story_quality_service import story_quality_service
from app.services.memory_phase_b_service import build_episode_memory, compact_episode_packet


async def _notify_intelligence_index(db, project_id: str, doc: Dict[str, Any]) -> None:
    """Best-effort derived update; chapter approval remains authoritative."""
    from app.services.memory_incremental_index_service import memory_incremental_index_service
    intelligence_id = str(doc.get("intelligence_id") or "")
    version = int(doc.get("version_number") or doc.get("source_version") or 1)
    key = f"chapter-intelligence:{project_id}:{intelligence_id}:v{version}:{doc.get('source_hash') or ''}"
    try:
        await memory_incremental_index_service.enqueue_change(
            db,
            project_id,
            source_type="chapter_intelligence",
            operation="refresh",
            logical_source_id=intelligence_id,
            event_key=key,
        )
        await memory_incremental_index_service.process_pending(db, project_id, limit=32)
    except Exception as exc:
        await memory_incremental_index_service.record_hook_failure(
            db, project_id, f"chapter_intelligence:{type(exc).__name__}:{str(exc)}"
        )


def _serialize(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {
            ("id" if key == "_id" else key): _serialize(item)
            for key, item in value.items()
        }
    return value


def _unique(values: Iterable[Any]) -> list[Any]:
    result = []
    seen = set()
    for value in values:
        if value is None or value == "":
            continue
        marker = repr(value)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(value)
    return result


def _words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", str(text or "")))


def _summary(plan: Dict[str, Any], scenes: list[Dict[str, Any]]) -> str:
    parts = [
        str(plan.get("purpose") or "").strip(),
        *[
            str(scene.get("outcome") or scene.get("purpose") or "").strip()
            for scene in scenes
        ],
    ]
    return " ".join(_unique(part for part in parts if part))[:1800]


class ChapterIntelligenceService:
    async def generate(
        self,
        db,
        project_id: str,
        chapter_draft_id: str,
    ) -> Dict[str, Any]:
        if not ObjectId.is_valid(project_id):
            raise ValueError("Invalid project ID")
        pid = ObjectId(project_id)
        draft = await db.chapter_drafts.find_one(
            {
                "project_id": pid,
                "draft_id": chapter_draft_id,
                "status": "approved",
            }
        )
        if not draft:
            raise ValueError("Chapter intelligence requires an approved chapter draft")
        if draft.get("workflow_mode") == "discovery":
            generated_text = str(draft.get("generated_text") or "")
            chapter_number = int(draft.get("chapter_number") or 0)
            intelligence_id = str(uuid5(NAMESPACE_URL, f"novelforge:discovery-intelligence:{project_id}:{draft['draft_id']}:{draft.get('version_number', 1)}"))
            quality = story_quality_service.analyze_text(generated_text)
            extraction = await db.discovery_extractions.find_one({"project_id": pid, "source_draft_id": draft["draft_id"]}) or {}
            candidates = [item for item in extraction.get("candidates") or [] if isinstance(item, dict)]
            def values_for(*types: str) -> list[Any]:
                return _unique([
                    item.get("subject") or item.get("value") or item.get("description")
                    for item in candidates
                    if str(item.get("candidate_type") or item.get("type") or "") in types
                ])
            important_events = values_for("timeline_event", "plot_thread", "knowledge_change")
            characters = values_for("character")
            relationships = values_for("relationship")
            artifacts = values_for("artifact")
            mysteries = values_for("mystery", "unresolved_element")
            obligations = values_for("promise", "foreshadowing", "plot_thread", "unresolved_element", "mystery")
            world_facts = values_for("world_fact", "knowledge_change")
            candidate_summary = "; ".join(str(value) for value in [*important_events[:3], *mysteries[:3], *obligations[:3]] if value)
            chapter_summary = candidate_summary[:1800] or str(draft.get("change_reason") or "Discovery-written chapter")
            now = datetime.utcnow()
            doc = {
                "project_id": pid,
                "intelligence_id": intelligence_id,
                "chapter_plan_id": None,
                "chapter_draft_id": draft["draft_id"],
                "chapter_draft_version": int(draft.get("version_number") or 1),
                "chapter_number": chapter_number,
                "arc_id": None,
                "title": f"Chapter {chapter_number}",
                "active": bool(draft.get("active", True)),
                "chapter_summary": chapter_summary,
                "important_events": important_events,
                "characters_present": characters,
                "character_changes": [],
                "knowledge_revealed": world_facts,
                "mysteries_introduced": mysteries,
                "mysteries_advanced": [],
                "mysteries_resolved": [],
                "foreshadowing_introduced": values_for("foreshadowing"),
                "foreshadowing_advanced": [],
                "foreshadowing_resolved": [],
                "artifact_usage": artifacts,
                "relationship_changes": relationships,
                "timeline_impact": values_for("timeline_event"),
                "canon_impact": [],
                "unresolved_questions": mysteries,
                "future_obligations": obligations,
                "word_count": _words(generated_text),
                "quality_findings": quality["findings"],
                "source_hash": draft.get("content_hash") or draft.get("generated_text_hash"),
                "workflow_mode": "discovery",
                "created_at": now,
                "updated_at": now,
            }
            doc["episode_memory"] = build_episode_memory(doc)
            doc["episode_derivation_version"] = doc["episode_memory"]["derivation_version"]
            await db.chapter_intelligence.update_many({"project_id": pid, "chapter_draft_id": draft["draft_id"], "intelligence_id": {"$ne": intelligence_id}}, {"$set": {"active": False, "updated_at": now}})
            await db.chapter_intelligence.update_one({"project_id": pid, "intelligence_id": intelligence_id}, {"$set": {key: value for key, value in doc.items() if key != "created_at"}, "$setOnInsert": {"created_at": now}}, upsert=True)
            await _notify_intelligence_index(db, project_id, doc)
            return _serialize(doc)
        plan = await db.chapter_plans.find_one(
            {
                "project_id": pid,
                "chapter_plan_id": draft.get("chapter_plan_id"),
            }
        )
        if not plan:
            raise ValueError("Approved chapter has no project-owned chapter plan")
        scenes = await db.scene_plans.find(
            {
                "project_id": pid,
                "chapter_plan_id": plan["chapter_plan_id"],
            }
        ).sort("order", 1).to_list(length=1000)
        source_ids = list(
            draft.get("source_scene_draft_ids")
            or draft.get("source_draft_ids")
            or []
        )
        source_drafts = await db.scene_drafts.find(
            {"project_id": pid, "draft_id": {"$in": source_ids}}
        ).to_list(length=1000)
        claims = [
            item.get("continuity_claims") or {} for item in source_drafts
        ]

        knowledge_ids = _unique(
            [
                *(plan.get("knowledge_changes") or []),
                *[
                    value
                    for scene in scenes
                    for value in (scene.get("knowledge_changes") or [])
                ],
                *[
                    value
                    for claim in claims
                    for value in (claim.get("knowledge_entry_ids") or [])
                ],
            ]
        )
        knowledge = await db.knowledge_entries.find(
            {"project_id": pid, "entry_id": {"$in": knowledge_ids}}
        ).to_list(length=1000)
        knowledge_by_id = {
            str(item.get("entry_id")): item for item in knowledge
        }

        foreshadow_ids = _unique(
            [
                *[
                    value
                    for scene in scenes
                    for value in (scene.get("foreshadow_links") or [])
                ],
                *[
                    value
                    for claim in claims
                    for value in (claim.get("foreshadow_ids") or [])
                ],
            ]
        )
        foreshadow = await db.foreshadow_registry_v2.find(
            {"project_id": pid, "entry_id": {"$in": foreshadow_ids}}
        ).to_list(length=1000)
        chains = await db.foreshadow_chains.find(
            {
                "project_id": pid,
                "$or": [
                    {"chapter_plan_id": plan["chapter_plan_id"]},
                    {"scene_id": {"$in": [item.get("scene_id") for item in scenes]}},
                ],
            }
        ).sort("order", 1).to_list(length=1000)

        artifact_ids = _unique(
            [
                *(plan.get("artifact_links") or []),
                *[
                    value
                    for scene in scenes
                    for value in (scene.get("artifact_interactions") or [])
                ],
                *[
                    value
                    for claim in claims
                    for value in (claim.get("artifact_ids") or [])
                ],
            ]
        )
        artifacts = await db.artifact_registry.find(
            {"project_id": pid, "artifact_id": {"$in": artifact_ids}}
        ).to_list(length=1000)
        artifact_by_id = {
            str(item.get("artifact_id")): item for item in artifacts
        }

        timeline_ids = _unique(
            [
                *(plan.get("timeline_links") or []),
                *[
                    value
                    for scene in scenes
                    for value in (scene.get("timeline_impacts") or [])
                ],
                *[
                    value
                    for claim in claims
                    for value in (claim.get("timeline_entry_ids") or [])
                ],
            ]
        )
        timeline = await db.timeline_entries.find(
            {"project_id": pid, "entry_id": {"$in": timeline_ids}}
        ).to_list(length=1000)
        timeline_by_id = {
            str(item.get("entry_id")): item for item in timeline
        }

        mysteries = await db.mystery_registry.find(
            {"project_id": pid}
        ).to_list(length=1000)
        chapter_number = int(plan.get("chapter_number") or 0)
        mystery_rows = {"introduced": [], "advanced": [], "resolved": []}
        for mystery in mysteries:
            references = " ".join(
                str(value)
                for value in (
                    mystery.get("reveal_target"),
                    mystery.get("chapter_plan_id"),
                    mystery.get("arc_id"),
                )
                if value
            )
            linked = (
                plan["chapter_plan_id"] in references
                or str(plan.get("arc_id") or "") == str(mystery.get("arc_id") or "")
                or any(
                    str(mystery.get("question") or "").lower()
                    in str(event).lower()
                    for event in [
                        *(plan.get("mysteries") or []),
                        *[scene.get("purpose") for scene in scenes],
                    ]
                    if event
                )
            )
            if not linked:
                continue
            status = str(mystery.get("status") or "open").lower()
            bucket = (
                "resolved"
                if status in {"resolved", "closed", "paid_off"}
                else "introduced"
                if int(mystery.get("introduced_chapter") or 0) == chapter_number
                else "advanced"
            )
            mystery_rows[bucket].append(
                {
                    "mystery_id": str(
                        mystery.get("mystery_id") or mystery.get("_id")
                    ),
                    "question": mystery.get("question"),
                }
            )

        foreshadow_rows = {"introduced": [], "advanced": [], "resolved": []}
        for row in [*foreshadow, *chains]:
            event_type = str(
                row.get("event_type") or row.get("status") or "seed"
            ).lower()
            bucket = (
                "resolved"
                if event_type in {"payoff", "resolved", "paid_off"}
                else "introduced"
                if event_type in {"seed", "introduced", "planted"}
                else "advanced"
            )
            foreshadow_rows[bucket].append(
                {
                    "entry_id": str(
                        row.get("entry_id")
                        or row.get("chain_node_id")
                        or row.get("_id")
                    ),
                    "summary": row.get("seed")
                    or row.get("summary")
                    or row.get("payoff_target"),
                }
            )

        relationships = await db.relationship_graphs.find(
            {
                "project_id": pid,
                "$or": [
                    {"character_a": {"$in": plan.get("character_focus") or []}},
                    {"character_b": {"$in": plan.get("character_focus") or []}},
                ],
            }
        ).to_list(length=1000)
        active_canon = await db.canon_registry.find(
            {
                "project_id": pid,
                "active": True,
                "$or": [
                    {"source_id": plan["chapter_plan_id"]},
                    {"source_id": chapter_draft_id},
                ],
            }
        ).to_list(length=1000)

        characters = _unique(
            [
                *(plan.get("character_focus") or []),
                *[
                    value
                    for scene in scenes
                    for value in (scene.get("character_focus") or [])
                ],
                *[
                    value
                    for claim in claims
                    for value in (claim.get("characters") or [])
                ],
            ]
        )
        important_events = _unique(
            [
                str(value)
                for value in [
                    plan.get("purpose"),
                    plan.get("conflict"),
                    *[scene.get("outcome") for scene in scenes],
                ]
                if value
            ]
        )
        character_changes = _unique(
            [
                {
                    "character": ", ".join(scene.get("character_focus") or []),
                    "change": scene.get("character_change"),
                }
                for scene in scenes
                if scene.get("character_change")
            ]
        )
        unresolved_questions = _unique(
            [
                item.get("question")
                for item in mysteries
                if str(item.get("status") or "open").lower()
                not in {"resolved", "closed", "paid_off"}
                and (
                    str(item.get("arc_id") or "")
                    in {"", str(plan.get("arc_id") or "")}
                )
            ]
        )
        future_obligations = _unique(
            [
                *unresolved_questions,
                *[
                    item.get("payoff_target")
                    for item in foreshadow
                    if str(item.get("status") or "").lower()
                    not in {"resolved", "paid_off"}
                ],
                *[
                    item.get("future_relevance")
                    for item in artifacts
                    if item.get("future_relevance")
                    and str(item.get("status") or "active").lower()
                    not in {"resolved", "destroyed", "archived"}
                ],
            ]
        )
        generated_text = str(draft.get("generated_text") or "")
        quality = story_quality_service.analyze_text(generated_text)
        version_number = int(draft.get("version_number") or 1)
        intelligence_id = str(
            uuid5(
                NAMESPACE_URL,
                (
                    f"novelforge:chapter-intelligence:{project_id}:"
                    f"{plan['chapter_plan_id']}:{version_number}"
                ),
            )
        )
        now = datetime.utcnow()
        doc = {
            "project_id": pid,
            "intelligence_id": intelligence_id,
            "chapter_plan_id": plan["chapter_plan_id"],
            "chapter_draft_id": chapter_draft_id,
            "chapter_draft_version": version_number,
            "chapter_number": chapter_number,
            "arc_id": plan.get("arc_id"),
            "title": plan.get("title") or f"Chapter {chapter_number}",
            "active": bool(draft.get("active", True)),
            "chapter_summary": _summary(plan, scenes),
            "important_events": important_events,
            "characters_present": characters,
            "character_changes": character_changes,
            "knowledge_revealed": [
                {
                    "entry_id": entry_id,
                    "title": knowledge_by_id.get(entry_id, {}).get("title"),
                    "content": knowledge_by_id.get(entry_id, {}).get("content"),
                    "known_by": knowledge_by_id.get(entry_id, {}).get("known_by")
                    or [],
                }
                for entry_id in knowledge_ids
            ],
            "mysteries_introduced": mystery_rows["introduced"],
            "mysteries_advanced": mystery_rows["advanced"],
            "mysteries_resolved": mystery_rows["resolved"],
            "foreshadowing_introduced": foreshadow_rows["introduced"],
            "foreshadowing_advanced": foreshadow_rows["advanced"],
            "foreshadowing_resolved": foreshadow_rows["resolved"],
            "artifact_usage": [
                {
                    "artifact_id": artifact_id,
                    "name": artifact_by_id.get(artifact_id, {}).get("name")
                    or artifact_by_id.get(artifact_id, {}).get("item"),
                    "status": artifact_by_id.get(artifact_id, {}).get("status"),
                }
                for artifact_id in artifact_ids
            ],
            "relationship_changes": [
                {
                    "relationship_id": str(
                        item.get("relationship_id") or item.get("_id")
                    ),
                    "character_a": item.get("character_a"),
                    "character_b": item.get("character_b"),
                    "status": item.get("status"),
                    "future_payoff": item.get("future_payoff"),
                }
                for item in relationships
            ],
            "timeline_impact": [
                {
                    "entry_id": entry_id,
                    "title": timeline_by_id.get(entry_id, {}).get("title"),
                    "summary": timeline_by_id.get(entry_id, {}).get("summary"),
                }
                for entry_id in timeline_ids
            ],
            "canon_impact": [
                {
                    "canon_id": item.get("canon_id"),
                    "canon_type": item.get("canon_type"),
                    "subject": item.get("subject"),
                    "field": item.get("field"),
                }
                for item in active_canon
            ],
            "unresolved_questions": unresolved_questions,
            "future_obligations": future_obligations,
            "word_count": _words(generated_text),
            "quality_findings": quality["findings"],
            "source_hash": draft.get("content_hash")
            or draft.get("generated_text_hash"),
            "created_at": now,
            "updated_at": now,
        }
        doc["episode_memory"] = build_episode_memory(doc)
        doc["episode_derivation_version"] = doc["episode_memory"]["derivation_version"]
        await db.chapter_intelligence.update_many(
            {
                "project_id": pid,
                "chapter_plan_id": plan["chapter_plan_id"],
                "intelligence_id": {"$ne": intelligence_id},
            },
            {"$set": {"active": False, "updated_at": now}},
        )
        await db.chapter_intelligence.update_one(
            {"project_id": pid, "intelligence_id": intelligence_id},
            {
                "$set": {
                    key: value
                    for key, value in doc.items()
                    if key != "created_at"
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        await _notify_intelligence_index(db, project_id, doc)
        return _serialize(doc)

    async def activate_for_draft(
        self, db, project_id: str, chapter_draft_id: str
    ) -> Dict[str, Any] | None:
        pid = ObjectId(project_id)
        draft = await db.chapter_drafts.find_one(
            {"project_id": pid, "draft_id": chapter_draft_id}
        )
        if not draft or draft.get("status") != "approved":
            return None
        return await self.generate(db, project_id, chapter_draft_id)

    async def backfill(self, db, project_id: str) -> Dict[str, int]:
        pid = ObjectId(project_id)
        drafts = await db.chapter_drafts.find(
            {"project_id": pid, "status": "approved", "active": True},
            {"draft_id": 1},
        ).to_list(length=10000)
        generated = 0
        for draft in drafts:
            await self.generate(db, project_id, draft["draft_id"])
            generated += 1
        return {"approved_chapters": len(drafts), "generated": generated}

    async def memory_packet(
        self,
        db,
        project_id: str,
        *,
        recent_limit: int = 12,
        obligation_limit: int = 12,
    ) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        recent = await db.chapter_intelligence.find(
            {"project_id": pid, "active": True}
        ).sort("chapter_number", -1).to_list(length=recent_limit)
        oldest_obligations = await db.chapter_intelligence.find(
            {
                "project_id": pid,
                "active": True,
                "future_obligations.0": {"$exists": True},
            }
        ).sort("chapter_number", 1).to_list(length=10000)
        recent_ids = {item["_id"] for item in recent}
        all_chapters = await db.chapter_intelligence.find(
            {"project_id": pid, "active": True}
        ).sort("chapter_number", 1).to_list(length=10000)
        unresolved = []
        for item in oldest_obligations:
            chapter_number = int(item.get("chapter_number") or 0)
            open_values = []
            for obligation in item.get("future_obligations") or []:
                resolved_later = any(
                    str(obligation).lower()
                    in " ".join(
                        str(value)
                        for key in (
                            "important_events",
                            "mysteries_resolved",
                            "foreshadowing_resolved",
                        )
                        for value in later.get(key, [])
                    ).lower()
                    for later in all_chapters
                    if int(later.get("chapter_number") or 0) > chapter_number
                )
                if not resolved_later:
                    open_values.append(obligation)
            if open_values:
                unresolved.append({**item, "future_obligations": open_values})
        obligations = [
            item
            for item in unresolved
            if item["_id"] not in recent_ids
        ][:obligation_limit]
        return {
            "recent": [
                _serialize(
                    {
                        "intelligence_id": item.get("intelligence_id"),
                        "chapter_number": item.get("chapter_number"),
                        "title": item.get("title"),
                        "episode": compact_episode_packet(item),
                        "chapter_summary": item.get("chapter_summary"),
                        "important_events": item.get("important_events"),
                        "characters_present": item.get("characters_present"),
                        "character_changes": item.get("character_changes"),
                        "knowledge_revealed": item.get("knowledge_revealed"),
                        "mysteries_resolved": item.get("mysteries_resolved"),
                        "foreshadowing_resolved": item.get("foreshadowing_resolved"),
                        "artifact_usage": item.get("artifact_usage"),
                        "relationship_changes": item.get("relationship_changes"),
                        "timeline_impact": item.get("timeline_impact"),
                        "canon_impact": item.get("canon_impact"),
                        "unresolved_questions": item.get("unresolved_questions"),
                        "future_obligations": item.get("future_obligations"),
                    }
                )
                for item in reversed(recent)
            ],
            "long_range_obligations": [
                _serialize(
                    {
                        "intelligence_id": item.get("intelligence_id"),
                        "chapter_number": item.get("chapter_number"),
                        "title": item.get("title"),
                        "future_obligations": item.get("future_obligations"),
                        "evidence_pointer": (item.get("episode_memory") or build_episode_memory(item)).get("evidence_pointer"),
                    }
                )
                for item in obligations
            ],
        }


chapter_intelligence_service = ChapterIntelligenceService()
