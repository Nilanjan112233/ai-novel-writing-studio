"""Bounded in-process cache of the complete active Native index.

This is a read optimization, not a persistence or authority layer.  The cache
is keyed by the durable processed index version and can always be rebuilt from
Mongo.  Incremental writes invalidate the affected project entry.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, List

from bson import ObjectId


class MemoryIndexCache:
    def __init__(self, max_projects: int = 12):
        self.max_projects = max(1, int(max_projects))
        self._projects: OrderedDict[tuple[str, int], List[Dict[str, Any]]] = OrderedDict()

    def invalidate(self, project_id: str) -> None:
        for key in list(self._projects):
            if key[0] == str(project_id):
                self._projects.pop(key, None)

    async def load(
        self,
        db,
        project_id: str,
        processed_version: int,
    ) -> tuple[List[Dict[str, Any]], bool]:
        key = (str(project_id), int(processed_version or 0))
        cached = self._projects.get(key)
        if cached is not None:
            self._projects.move_to_end(key)
            # Retrieval copies each row and metadata before attribution. A
            # shallow list copy avoids re-copying thousands of immutable
            # embedding floats on every query.
            return list(cached), True

        rows: List[Dict[str, Any]] = []
        async for document in db.memory_embeddings.find(
            {
                "project_id": ObjectId(project_id),
                "active": {"$ne": False},
            },
            {
                "project_id": 1,
                "source_type": 1,
                "source_id": 1,
                "source_version": 1,
                "active": 1,
                "content_hash": 1,
                "content": 1,
                "embedding": 1,
                "metadata": 1,
                "created_at": 1,
                "updated_at": 1,
            },
        ):
            rows.append(document)
        self._projects[key] = rows
        self._projects.move_to_end(key)
        while len(self._projects) > self.max_projects:
            self._projects.popitem(last=False)
        return list(rows), False

    def prime(
        self,
        project_id: str,
        processed_version: int,
        documents: List[Dict[str, Any]],
    ) -> None:
        self.invalidate(project_id)
        key = (str(project_id), int(processed_version or 0))
        self._projects[key] = list(documents)
        self._projects.move_to_end(key)


memory_index_cache = MemoryIndexCache()
