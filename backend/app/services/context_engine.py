"""Layered context construction for narrative agents."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from bson import ObjectId
from pydantic import BaseModel, Field

from app.services.memory_provider import memory_provider_service
from app.services.memory_retrieval_policy import (
    RetrievalEligibilityContext,
    metadata_for_source,
    retrieval_eligibility_policy,
)
from app.services.provider_gateway import estimate_tokens
from app.services.memory_phase_b_service import compact_retrieval_hit


class ContextPacket(BaseModel):
    agent_name: str
    task: str
    active_context: List[Dict[str, Any]] = Field(default_factory=list)
    working_memory: List[Dict[str, Any]] = Field(default_factory=list)
    retrieved_memory: List[Dict[str, Any]] = Field(default_factory=list)
    compressed_memory: List[Dict[str, Any]] = Field(default_factory=list)
    token_estimate: int = 0


def _packet_tokens(packet: ContextPacket) -> int:
    # Mongo documents can carry ObjectId values. They are valid persistence
    # values but not JSON-native prompt values; stringify only at the context
    # measurement boundary so retrieval remains lossless in Mongo.
    import json
    return estimate_tokens(json.dumps(packet.model_dump(), default=str, ensure_ascii=True))


def _deduplicate_retrieved(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Last-mile logical deduplication before a provider packet is packed."""
    selected: Dict[str, Dict[str, Any]] = {}
    for item in items:
        metadata = item.get("metadata") or {}
        key = str(
            metadata.get("logical_identity")
            or item.get("logical_identity")
            or f"{item.get('source_type') or item.get('type')}:{item.get('source_id')}:{metadata.get('source_version') or 1}"
        )
        current = selected.get(key)
        if current is None:
            selected[key] = item
            continue
        current_tokens = int((current.get("metadata") or {}).get("estimated_tokens") or 10**9)
        candidate_tokens = int(metadata.get("estimated_tokens") or 10**9)
        if candidate_tokens < current_tokens:
            selected[key] = item
    return list(selected.values())


class ContextEngine:
    async def build_context_packet(
        self,
        db,
        *,
        project_id: str,
        agent_name: str,
        task: str,
        cycle_number: int,
        target_artifact: str | None = None,
        max_context_tokens: int = 120000,
        current_chapter: int | None = None,
        current_scene: int | None = None,
        pov_character: str | None = None,
        branch_id: str | None = None,
        safe_for_writing: bool = True,
        include_conversation_history: bool = True,
        persist: bool = True,
    ) -> ContextPacket:
        pid = ObjectId(project_id)
        recent_messages = []
        if include_conversation_history:
            recent_messages = await db.timeline_messages.find(
                {"project_id": pid}
            ).sort("created_at", -1).to_list(length=20)
        cycle = await db.cycles.find_one({"project_id": pid, "cycle_number": cycle_number}) or {}
        project = await db.projects.find_one({"_id": pid}) or {}

        active_context = [
            {"type": "project", "project_name": project.get("project_name") or project.get("title"), "story_title": project.get("story_title") or "Untitled novel", "title": project.get("story_title") or "Untitled novel", "idea_dump": project.get("idea_dump"), "premise": project.get("premise")},
            {"type": "cycle", "cycle_number": cycle_number, "status": cycle.get("status"), "target_artifact": target_artifact},
            *[{"type": "message", "role": m.get("role"), "agent_name": m.get("agent_name"), "content": m.get("content"), "created_at": m.get("created_at")} for m in reversed(recent_messages)],
        ]

        working_memory: List[Dict[str, Any]] = []
        eligibility_context = RetrievalEligibilityContext(
            safe_for_writing=safe_for_writing,
            consumer=agent_name,
            project_id=project_id,
            branch_id=branch_id,
            as_of_chapter=current_chapter,
            as_of_scene=current_scene,
            pov_character=pov_character,
        )

        def eligible(source_type: str, document: Dict[str, Any]) -> bool:
            if not safe_for_writing:
                return True
            indexed_shape = {
                **document,
                "source_type": source_type,
                "metadata": metadata_for_source(source_type, document),
            }
            return retrieval_eligibility_policy.evaluate(
                indexed_shape, eligibility_context
            ).eligible
        # Authority-first context: these records are small, durable, and must
        # outrank conversational recollection or candidate extraction.
        authority_specs = [
            ("canon", db.canon_registry.find({"project_id": pid, "active": {"$ne": False}}).sort("updated_at", -1), 40),
            ("approved_decision", db.decision_registry.find({"project_id": pid, "status": {"$in": ["approved", "resolved"]}}).sort("updated_at", -1), 30),
            ("timeline", db.timeline_entries.find({"project_id": pid, "status": {"$nin": ["rejected", "candidate"]}, "$or": [{"authority_status": {"$exists": False}}, {"authority_status": {"$in": ["approved", "confirmed", "active"]}}]}).sort("order", 1), 40),
        ]
        for memory_type, cursor, length in authority_specs:
            docs = await cursor.to_list(length=length)
            for doc in docs:
                source_type = {
                    "canon": "canon",
                    "approved_decision": "decision",
                    "timeline": "timeline_v2",
                }[memory_type]
                if not eligible(source_type, doc):
                    continue
                chapter = doc.get("chapter_number") or doc.get("source_chapter")
                if current_chapter is not None and chapter is not None and int(chapter) > int(current_chapter):
                    continue
                doc.pop("_id", None); doc.pop("project_id", None)
                working_memory.append({"type": memory_type, "authority": "authoritative", "content": doc})
        specs = [
            ("characters", db.character_bibles.find({"project_id": pid, "$or": [{"authority_status": {"$exists": False}}, {"authority_status": {"$in": ["approved", "confirmed", "active"]}}]}).sort("updated_at", -1), 12),
            ("plot_threads", db.plot_threads.find({"project_id": pid, "status": {"$ne": "resolved"}, "$or": [{"authority_status": {"$exists": False}}, {"authority_status": {"$in": ["approved", "confirmed", "active"]}}]}).sort("updated_at", -1), 10),
            ("themes", db.theme_registry.find({"project_id": pid}), 3),
            ("questions", db.questions.find({"project_id": pid, "answered": False, "$or": [{"authority_status": {"$exists": False}}, {"authority_status": {"$in": ["approved", "confirmed", "active"]}}]}).sort("created_at", 1), 8),
        ]
        for memory_type, cursor, length in specs:
            docs = await cursor.to_list(length=length)
            for doc in docs:
                source_type = {
                    "characters": "character",
                    "plot_threads": "plot_thread",
                    "themes": "theme",
                    "questions": "question",
                }[memory_type]
                if not eligible(source_type, doc):
                    continue
                chapter = doc.get("chapter_number") or doc.get("source_chapter")
                if current_chapter is not None and chapter is not None and int(chapter) > int(current_chapter):
                    continue
                doc.pop("_id", None)
                doc.pop("project_id", None)
                working_memory.append({"type": memory_type, "content": doc})

        query = " ".join([task or "", " ".join(str(item.get("content", "")) for item in active_context[-8:])])
        provider_recall = await memory_provider_service.recall(
            db, project_id, query, top_k=8, safe_for_writing=safe_for_writing,
            consumer=agent_name,
            as_of_chapter=current_chapter,
            as_of_scene=current_scene,
            pov_character=pov_character,
            branch_id=branch_id,
        )
        retrieved_memory = provider_recall.get("primary", {}).get("hits") or []
        retrieved_memory = _deduplicate_retrieved(retrieved_memory)
        retrieved_memory = [compact_retrieval_hit(item) for item in retrieved_memory]
        retrieved_memory = sorted(
            retrieved_memory,
            key=lambda item: {"canon": 0, "decision": 1, "timeline_v2": 2, "knowledge": 3}.get(str(item.get("memory_type") or item.get("type") or ""), 4),
        )
        compressed = await db.compressed_memories.find({"project_id": pid}).sort("created_at", -1).to_list(length=5)
        compressed_memory = [
            {"summary": doc.get("summary", ""), "preserved_items": doc.get("preserved_items", []), "created_at": doc.get("created_at")}
            for doc in compressed
        ]

        packet = ContextPacket(
            agent_name=agent_name,
            task=task,
            active_context=active_context,
            working_memory=working_memory,
            retrieved_memory=retrieved_memory,
            compressed_memory=compressed_memory,
        )
        packet.token_estimate = _packet_tokens(packet)

        while packet.token_estimate > max_context_tokens and packet.retrieved_memory:
            packet.retrieved_memory.pop()
            packet.token_estimate = _packet_tokens(packet)
        while packet.token_estimate > max_context_tokens and packet.active_context:
            packet.active_context.pop(0)
            packet.token_estimate = _packet_tokens(packet)

        if persist:
            await db.context_packets.insert_one({
                "project_id": pid,
                "cycle_number": cycle_number,
                "agent_name": agent_name,
                "task": task,
                "target_artifact": target_artifact,
                "consumer_context": {
                    "current_chapter": current_chapter,
                    "current_scene": current_scene,
                    "pov_character": pov_character,
                    "branch_id": branch_id,
                    "safe_for_writing": safe_for_writing,
                    "include_conversation_history": include_conversation_history,
                },
                "packet": packet.model_dump(),
                "token_estimate": packet.token_estimate,
                "tokens_by_section": {
                    "task": estimate_tokens(task or ""),
                    "active_context": estimate_tokens(str(packet.active_context)),
                    "working_memory": estimate_tokens(str(packet.working_memory)),
                    "retrieved_memory": estimate_tokens(str(packet.retrieved_memory)),
                    "compressed_memory": estimate_tokens(str(packet.compressed_memory)),
                },
                "created_at": datetime.utcnow(),
            })
        return packet


context_engine = ContextEngine()
