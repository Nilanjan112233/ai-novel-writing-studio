"""Phase C bounded lexical candidate generation over the rebuildable Native index.

Authority and eligibility remain owned by the P0 policy.  This service only
narrows the derived records which that policy and the ranker subsequently see.
If readiness cannot be proven, callers must use the complete Phase B path.
"""
from __future__ import annotations

import time
from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, List

from bson import ObjectId

from app.services.memory_phase_c_ranker import (
    PHASE_C_RANKER_VERSION,
    expanded_query_terms,
    select_discriminative_terms,
    story_candidate_domain,
)


READY = "READY"


class MemoryPhaseCService:
    def __init__(self) -> None:
        self._candidate_cache: OrderedDict[tuple[str, int, str], tuple[List[Dict[str, Any]], Dict[str, Any]]] = OrderedDict()

    def invalidate(self, project_id: str) -> None:
        for key in list(self._candidate_cache):
            if key[0] == str(project_id):
                self._candidate_cache.pop(key, None)

    async def get_status(self, db, project_id: str) -> Dict[str, Any]:
        if not ObjectId.is_valid(project_id):
            return {"status": "INCOMPLETE", "complete": False, "fallback_reason": "invalid_project_id"}
        checkpoint = await db.memory_phase_c_checkpoints.find_one({"project_id": ObjectId(project_id)})
        if not checkpoint:
            return {
                "status": "INCOMPLETE", "complete": False,
                "ranker_version": PHASE_C_RANKER_VERSION,
                "fallback_reason": "phase_c_checkpoint_missing",
            }
        return {
            "status": str(checkpoint.get("status") or "INCOMPLETE"),
            "complete": bool(checkpoint.get("complete")),
            "ranker_version": int(checkpoint.get("ranker_version") or 0),
            "processed_version": int(checkpoint.get("processed_version") or 0),
            "indexed_records": int(checkpoint.get("indexed_records") or 0),
            "last_rebuild": checkpoint.get("last_rebuild"),
            "last_successful_update": checkpoint.get("last_successful_update"),
            "fallback_reason": checkpoint.get("fallback_reason"),
        }

    async def mark_rebuild_complete(
        self, db, project_id: str, *, processed_version: int, indexed_records: int,
    ) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        self.invalidate(project_id)
        now = datetime.utcnow()
        actual = await db.memory_embeddings.count_documents({
            "project_id": pid, "active": True,
            "phase_c_ranker_version": PHASE_C_RANKER_VERSION,
            "search_terms": {"$exists": True},
        })
        total = await db.memory_embeddings.count_documents({"project_id": pid, "active": True})
        complete = actual == total == int(indexed_records)
        status = READY if complete else "INCOMPLETE"
        reason = None if complete else "lexical_index_count_mismatch"
        await db.memory_phase_c_checkpoints.update_one(
            {"project_id": pid},
            {"$set": {
                "status": status, "complete": complete,
                "ranker_version": PHASE_C_RANKER_VERSION,
                "processed_version": int(processed_version),
                "indexed_records": int(actual), "expected_records": int(indexed_records),
                "last_rebuild": now, "last_successful_update": now if complete else None,
                "fallback_reason": reason, "updated_at": now,
            }, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        return {"status": status, "complete": complete, "actual": actual, "expected": int(indexed_records), "fallback_reason": reason}

    async def mark_incremental_processed(self, db, project_id: str, *, processed_version: int) -> None:
        """Advance only an already-complete projection; never bless a legacy partial index."""
        pid = ObjectId(project_id)
        now = datetime.utcnow()
        self.invalidate(project_id)
        await db.memory_phase_c_checkpoints.update_one(
            {"project_id": pid, "status": READY, "complete": True, "ranker_version": PHASE_C_RANKER_VERSION},
            {"$set": {"processed_version": int(processed_version), "last_successful_update": now, "updated_at": now}},
        )

    async def mark_failed(self, db, project_id: str, reason: str) -> None:
        self.invalidate(project_id)
        await db.memory_phase_c_checkpoints.update_one(
            {"project_id": ObjectId(project_id)},
            {"$set": {"status": "FAILED", "complete": False, "fallback_reason": str(reason)[:200], "updated_at": datetime.utcnow()}},
            upsert=True,
        )

    async def prepare_candidates(self, db, project_id: str, query: str) -> tuple[List[Dict[str, Any]] | None, Dict[str, Any]]:
        """Return complete matches for selected rare terms, or None for Phase B fallback."""
        started = time.perf_counter()
        status = await self.get_status(db, project_id)
        diagnostics: Dict[str, Any] = {"phase_c_status": status["status"], "phase_c_ranker_version": status.get("ranker_version")}
        if status["status"] != READY or not status["complete"] or status.get("ranker_version") != PHASE_C_RANKER_VERSION:
            diagnostics.update({"fallback_reason": status.get("fallback_reason") or "phase_c_not_ready", "candidate_generation_ms": round((time.perf_counter() - started) * 1000, 3)})
            return None, diagnostics

        cache_key = (str(project_id), int(status.get("processed_version") or 0), str(query or "").strip().lower())
        cached = self._candidate_cache.get(cache_key)
        if cached is not None:
            self._candidate_cache.move_to_end(cache_key)
            rows, cached_diagnostics = cached
            diagnostics.update({**cached_diagnostics, "phase_c_candidate_cache_hit": True, "candidate_generation_ms": round((time.perf_counter() - started) * 1000, 3)})
            return list(rows), diagnostics

        pid = ObjectId(project_id)
        base: Dict[str, Any] = {"project_id": pid, "active": True, "phase_c_ranker_version": PHASE_C_RANKER_VERSION}
        domain = story_candidate_domain(query)
        if domain:
            base["$or"] = [{"source_type": {"$in": sorted(domain)}}, {"metadata.predicate": {"$in": sorted(domain)}}]
        try:
            population = await db.memory_embeddings.count_documents(base)
            terms = expanded_query_terms(query)
            if not terms:
                diagnostics.update({"candidate_population": population, "candidate_count": 0, "records_scored": 0, "fallback_reason": "query_has_no_lexical_terms", "candidate_generation_ms": round((time.perf_counter() - started) * 1000, 3)})
                return None, diagnostics
            pipeline = [
                {"$match": {**base, "search_terms": {"$in": terms}}},
                {"$project": {"matched": {"$setIntersection": ["$search_terms", terms]}}},
                {"$unwind": "$matched"},
                {"$group": {"_id": "$matched", "count": {"$sum": 1}}},
            ]
            frequencies = {str(row["_id"]): int(row["count"]) async for row in db.memory_embeddings.aggregate(pipeline)}
            selected = select_discriminative_terms(query, frequencies, population)
            if not selected:
                # A domain-specific empty answer is complete (for example a
                # POV character has no matching knowledge). General queries
                # retain the complete Phase B fallback.
                diagnostics.update({"candidate_population": population, "candidate_count": 0, "records_scored": 0, "selected_terms": [], "coverage": "domain_complete_empty" if domain else "unknown", "candidate_generation_ms": round((time.perf_counter() - started) * 1000, 3)})
                return ([], diagnostics) if domain else (None, {**diagnostics, "fallback_reason": "no_indexed_query_term"})
            rows = await db.memory_embeddings.find({**base, "search_terms": {"$in": selected}}).to_list(length=None)
            diagnostics.update({
                "candidate_population": population, "candidate_count": len(rows),
                "records_scored": len(rows), "selected_terms": selected,
                "coverage": "all_matches_for_selected_terms", "fallback_reason": None,
                "candidate_generation_ms": round((time.perf_counter() - started) * 1000, 3),
                "phase_c_candidate_cache_hit": False,
            })
            self._candidate_cache[cache_key] = (list(rows), dict(diagnostics))
            self._candidate_cache.move_to_end(cache_key)
            while len(self._candidate_cache) > 256:
                self._candidate_cache.popitem(last=False)
            return rows, diagnostics
        except Exception as exc:
            diagnostics.update({"fallback_reason": f"phase_c_index_unavailable:{type(exc).__name__}", "candidate_generation_ms": round((time.perf_counter() - started) * 1000, 3)})
            return None, diagnostics


memory_phase_c_service = MemoryPhaseCService()
