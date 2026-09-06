"""Bounded, versioned memory owned by individual Narrative Studio agents."""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Dict, Iterable, List

from bson import ObjectId


TIER_LIMITS = {
    # L1: exact recent observations and unresolved concerns.
    "recent": 12,
    "important": 20,
    # L2: compact scenario/history summaries.
    "compressed": 8,
    # L3: stable canon and author decisions used to orient the agent quickly.
    "core": 16,
}
COMPACTION_INTERVAL = 5


def _memory_view(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document.get("_id") or ""),
        "memory_type": document.get("memory_type"),
        "content": document.get("content", ""),
        "importance": int(document.get("importance") or 0),
        "source_type": document.get("source_type"),
        "source_id": document.get("source_id"),
        "source_version": int(document.get("source_version") or 1),
        "updated_at": (
            document.get("updated_at").isoformat()
            if isinstance(document.get("updated_at"), datetime)
            else document.get("updated_at")
        ),
    }


class AgentMemoryService:
    async def remember(
        self,
        db,
        *,
        project_id: str,
        agent_name: str,
        memory_type: str,
        content: str,
        source_type: str,
        source_id: str,
        importance: int = 0,
        metadata: Dict[str, Any] | None = None,
    ) -> None:
        if memory_type not in TIER_LIMITS:
            raise ValueError(f"Unsupported agent memory type: {memory_type}")
        content = str(content or "").strip()
        if not content:
            return
        pid = ObjectId(project_id)
        identity = {
            "project_id": pid,
            "agent_name": agent_name,
            "memory_type": memory_type,
            "source_type": source_type,
            "source_id": str(source_id),
        }
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        existing = await db.agent_memories.find_one(
            {**identity, "content_hash": content_hash, "active": True},
            sort=[("source_version", -1)],
        )
        now = datetime.utcnow()
        if existing:
            await db.agent_memories.update_one(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "importance": max(
                            int(existing.get("importance") or 0), int(importance)
                        ),
                        "metadata": metadata or existing.get("metadata") or {},
                        "updated_at": now,
                    }
                },
            )
            return
        latest = await db.agent_memories.find_one(
            identity, {"source_version": 1}, sort=[("source_version", -1)]
        )
        await db.agent_memories.update_many(identity, {"$set": {"active": False}})
        await db.agent_memories.insert_one(
            {
                **identity,
                "source_version": int((latest or {}).get("source_version") or 0) + 1,
                "active": True,
                "content_hash": content_hash,
                "content": content,
                "importance": max(0, min(int(importance), 100)),
                "metadata": metadata or {},
                "created_at": now,
                "updated_at": now,
            }
        )
        await self.cleanup(db, project_id=project_id, agent_name=agent_name)

    async def sync_important(
        self,
        db,
        *,
        project_id: str,
        agent_name: str,
        canon_facts: Iterable[Any],
        decisions: Iterable[Any],
    ) -> None:
        for index, fact in enumerate(list(canon_facts)[-10:]):
            content = (
                fact.get("fact") if isinstance(fact, dict) else str(fact or "")
            )
            source_id = (
                str(fact.get("id") or fact.get("_id") or index)
                if isinstance(fact, dict)
                else f"canon-{index}"
            )
            await self.remember(
                db,
                project_id=project_id,
                agent_name=agent_name,
                memory_type="core",
                content=content,
                source_type="canon",
                source_id=source_id,
                importance=100,
            )
        for index, decision in enumerate(list(decisions)[-10:]):
            content = (
                decision.get("decision")
                or decision.get("answer")
                if isinstance(decision, dict)
                else str(decision or "")
            )
            source_id = (
                str(decision.get("id") or decision.get("_id") or index)
                if isinstance(decision, dict)
                else f"decision-{index}"
            )
            await self.remember(
                db,
                project_id=project_id,
                agent_name=agent_name,
                memory_type="core",
                content=content,
                source_type="decision",
                source_id=source_id,
                importance=90,
            )

    async def get_context(
        self,
        db,
        *,
        project_id: str,
        agent_name: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        pid = ObjectId(project_id)
        result: Dict[str, List[Dict[str, Any]]] = {}
        for memory_type, limit in TIER_LIMITS.items():
            documents = await db.agent_memories.find(
                {
                    "project_id": pid,
                    "agent_name": agent_name,
                    "memory_type": memory_type,
                    "active": True,
                }
            ).sort(
                [("importance", -1), ("updated_at", -1)]
            ).to_list(length=limit)
            result[memory_type] = [_memory_view(document) for document in documents]
        return result

    async def record_result(
        self,
        db,
        *,
        project_id: str,
        agent_name: str,
        cycle_number: int,
        summary: str,
        concerns: Iterable[Any] | None = None,
    ) -> None:
        await self.remember(
            db,
            project_id=project_id,
            agent_name=agent_name,
            memory_type="recent",
            content=summary,
            source_type="cycle_summary",
            source_id=f"{cycle_number}",
            importance=50,
            metadata={"cycle_number": cycle_number},
        )
        concern_text = "; ".join(str(item) for item in (concerns or []) if item)
        if concern_text:
            await self.remember(
                db,
                project_id=project_id,
                agent_name=agent_name,
                memory_type="important",
                content=concern_text,
                source_type="unresolved_questions",
                source_id=f"{cycle_number}",
                importance=75,
                metadata={"cycle_number": cycle_number},
            )
        if cycle_number % COMPACTION_INTERVAL == 0:
            await self.compact(db, project_id=project_id, agent_name=agent_name)

    async def compact(self, db, *, project_id: str, agent_name: str) -> int:
        pid = ObjectId(project_id)
        documents = await db.agent_memories.find(
            {
                "project_id": pid,
                "agent_name": agent_name,
                "memory_type": "recent",
                "active": True,
            }
        ).sort("updated_at", 1).to_list(length=1000)
        if len(documents) <= TIER_LIMITS["recent"]:
            return 0
        compact_count = len(documents) - (TIER_LIMITS["recent"] // 2)
        selected = documents[:compact_count]
        summary = " | ".join(
            str(document.get("content") or "").strip()[:320]
            for document in selected
            if document.get("content")
        )[:3000]
        if not summary:
            return 0
        latest_cycle = max(
            int((document.get("metadata") or {}).get("cycle_number") or 0)
            for document in selected
        )
        await self.remember(
            db,
            project_id=project_id,
            agent_name=agent_name,
            memory_type="compressed",
            content=summary,
            source_type="compaction",
            source_id=f"through-cycle-{latest_cycle}",
            importance=65,
            metadata={
                "through_cycle": latest_cycle,
                "source_memory_ids": [str(document["_id"]) for document in selected],
            },
        )
        # Keep the lower-level evidence available for provenance and drill-down.
        # It is no longer injected into prompts, but the L2 summary points back
        # to these records through source_memory_ids.
        result = await db.agent_memories.update_many(
            {"_id": {"$in": [document["_id"] for document in selected]}},
            {"$set": {
                "active": False,
                "archived": True,
                "compacted_into": f"through-cycle-{latest_cycle}",
                "updated_at": datetime.utcnow(),
            }},
        )
        await self.cleanup(db, project_id=project_id, agent_name=agent_name)
        return result.modified_count

    async def cleanup(
        self,
        db,
        *,
        project_id: str | None = None,
        agent_name: str | None = None,
    ) -> int:
        query: Dict[str, Any] = {}
        if project_id:
            query["project_id"] = ObjectId(project_id)
        if agent_name:
            query["agent_name"] = agent_name
        deleted_ids = []

        for memory_type, limit in TIER_LIMITS.items():
            type_query = {**query, "memory_type": memory_type, "active": True}
            active = await db.agent_memories.find(type_query, {"_id": 1}).sort(
                [("importance", -1), ("updated_at", -1)]
            ).skip(limit).to_list(length=10000)
            deleted_ids.extend(document["_id"] for document in active)

        stale = await db.agent_memories.find(
            {**query, "active": False, "archived": {"$ne": True}},
            {
                "_id": 1,
                "project_id": 1,
                "agent_name": 1,
                "memory_type": 1,
                "source_type": 1,
                "source_id": 1,
                "source_version": 1,
                "updated_at": 1,
            },
        ).to_list(length=100000)
        grouped: Dict[tuple[str, ...], List[Dict[str, Any]]] = {}
        for document in stale:
            key = (
                str(document.get("project_id") or ""),
                str(document.get("agent_name") or ""),
                str(document.get("memory_type") or ""),
                str(document.get("source_type") or ""),
                str(document.get("source_id") or ""),
            )
            grouped.setdefault(key, []).append(document)
        for documents in grouped.values():
            documents.sort(
                key=lambda item: (
                    int(item.get("source_version") or 0),
                    item.get("updated_at") or datetime.min,
                ),
                reverse=True,
            )
            deleted_ids.extend(document["_id"] for document in documents[1:])
        if not deleted_ids:
            return 0
        result = await db.agent_memories.delete_many(
            {"_id": {"$in": list(set(deleted_ids))}}
        )
        return result.deleted_count


agent_memory_service = AgentMemoryService()
