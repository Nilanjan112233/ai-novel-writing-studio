"""Durable Phase A maintenance for NovelForge's derived Native memory index.

Mongo owner collections remain authoritative.  Events, checkpoints, staging
rows, embeddings, and the in-process cache are all disposable/rebuildable.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List
from uuid import uuid4

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.services.memory_index_cache import memory_index_cache
from app.services.memory_retrieval_policy import (
    AUTHORITY_PRIORITY,
    RetrievalEligibilityContext,
    SOURCE_ID_FIELDS,
    logical_identity,
    retrieval_eligibility_policy,
)
from app.services.memory_retrieval_service import (
    SOURCE_SPECS,
    embed_text,
    index_memory,
    materialize_owner_memory,
)

READY = "READY"
LAGGING = "LAGGING"
INCOMPLETE = "INCOMPLETE"
REBUILDING = "REBUILDING"
FAILED = "FAILED"
KNOWN_STATUSES = {READY, LAGGING, INCOMPLETE, REBUILDING, FAILED}
SYNC_PENDING_LIMIT = 32


def _pid(project_id: str) -> ObjectId:
    if not ObjectId.is_valid(project_id):
        raise ValueError("Invalid project id")
    return ObjectId(project_id)


def _stable_hash(rows: Iterable[Dict[str, Any]]) -> str:
    values = sorted(
        f"{row['source_type']}|{row['logical_source_id']}|{row['source_version']}|{row['content_hash']}"
        for row in rows
    )
    return hashlib.sha256("\n".join(values).encode("utf-8")).hexdigest()


class MemoryIncrementalIndexService:
    async def _ensure_checkpoint(
        self,
        db,
        project_id: str,
        *,
        new_project: bool = False,
    ) -> Dict[str, Any]:
        pid = _pid(project_id)
        now = datetime.utcnow()
        await db.memory_index_checkpoints.update_one(
            {"project_id": pid},
            {"$setOnInsert": {
                "project_id": pid,
                "authority_state_version": 0,
                "processed_version": 0,
                "status": READY if new_project else INCOMPLETE,
                "index_complete": bool(new_project),
                "verification_required": not new_project,
                "pending_updates": 0,
                "failed_updates": 0,
                "created_at": now,
                "updated_at": now,
                "fallback_reason": None if new_project else "legacy_checkpoint_missing",
            }},
            upsert=True,
        )
        return await db.memory_index_checkpoints.find_one({"project_id": pid})

    async def mark_needs_verification(self, db, project_id: str, reason: str) -> Dict[str, Any]:
        checkpoint = await self._ensure_checkpoint(db, project_id)
        await db.memory_index_checkpoints.update_one(
            {"_id": checkpoint["_id"]},
            {"$set": {
                "status": INCOMPLETE,
                "index_complete": False,
                "verification_required": True,
                "fallback_reason": reason,
                "updated_at": datetime.utcnow(),
            }},
        )
        memory_index_cache.invalidate(project_id)
        return await self.get_status(db, project_id)

    async def get_status(self, db, project_id: str) -> Dict[str, Any]:
        pid = _pid(project_id)
        checkpoint = await db.memory_index_checkpoints.find_one({"project_id": pid})
        if not checkpoint:
            from app.services.memory_phase_c_service import memory_phase_c_service
            return {
                "project_id": project_id,
                "status": INCOMPLETE,
                "authority_state_version": 0,
                "processed_version": 0,
                "index_complete": False,
                "pending_updates": 0,
                "failed_updates": 0,
                "verification_required": True,
                "fallback_reason": "legacy_checkpoint_missing",
                "phase_c": await memory_phase_c_service.get_status(db, project_id),
            }
        pending = await db.memory_index_events.count_documents(
            {"project_id": pid, "status": {"$in": ["pending", "processing"]}}
        )
        failed = await db.memory_index_events.count_documents(
            {"project_id": pid, "status": "failed"}
        )
        status = str(checkpoint.get("status") or INCOMPLETE)
        if status not in KNOWN_STATUSES:
            status = INCOMPLETE
        state_version = int(checkpoint.get("authority_state_version") or 0)
        processed_version = int(checkpoint.get("processed_version") or 0)
        if failed:
            status = FAILED
        elif pending and status == READY:
            status = LAGGING
        elif not pending and state_version != processed_version and status != REBUILDING:
            status = INCOMPLETE
        from app.services.memory_phase_c_service import memory_phase_c_service
        return {
            "project_id": project_id,
            "status": status,
            "authority_state_version": state_version,
            "processed_version": processed_version,
            "index_complete": bool(checkpoint.get("index_complete")),
            "pending_updates": int(pending),
            "failed_updates": int(failed),
            "verification_required": bool(checkpoint.get("verification_required")),
            "last_successful_update": checkpoint.get("last_successful_update"),
            "last_processed_event": checkpoint.get("last_processed_event"),
            "last_rebuild": checkpoint.get("last_rebuild"),
            "records_indexed": int(checkpoint.get("records_indexed") or 0),
            "records_invalidated": int(checkpoint.get("records_invalidated") or 0),
            "duplicate_prevention": int(checkpoint.get("duplicate_prevention") or 0),
            "index_lag": max(
                0,
                state_version - processed_version,
            ),
            "repair_required": status in {INCOMPLETE, FAILED},
            "fallback_reason": checkpoint.get("fallback_reason"),
            "rebuild": checkpoint.get("rebuild"),
            "phase_c": await memory_phase_c_service.get_status(db, project_id),
        }

    async def recover_interrupted(self, db) -> Dict[str, int]:
        """Make in-flight event work retryable after process termination."""
        now = datetime.utcnow()
        events = await db.memory_index_events.update_many(
            {"status": "processing"},
            {"$set": {"status": "pending", "recovered_after_crash": True, "updated_at": now}},
        )
        checkpoints = await db.memory_index_checkpoints.update_many(
            {"status": LAGGING},
            {"$set": {"fallback_reason": "recovered_pending_updates", "updated_at": now}},
        )
        return {"events_requeued": int(events.modified_count), "checkpoints_touched": int(checkpoints.modified_count)}

    async def enqueue_change(
        self,
        db,
        project_id: str,
        *,
        source_type: str,
        operation: str,
        logical_source_id: str | None = None,
        physical_source_id: str | None = None,
        selector: Dict[str, Any] | None = None,
        source_types: Iterable[str] | None = None,
        changed_since: datetime | None = None,
        event_key: str | None = None,
        project_event_id: str | None = None,
        new_project: bool = False,
    ) -> Dict[str, Any]:
        pid = _pid(project_id)
        checkpoint = await self._ensure_checkpoint(db, project_id, new_project=new_project)
        payload = {
            "source_type": source_type,
            "operation": operation,
            "logical_source_id": logical_source_id,
            "physical_source_id": physical_source_id,
            "selector": selector or {},
            "source_types": sorted(set(source_types or [])),
            "changed_since": changed_since,
        }
        key_material = json.dumps(payload, default=str, sort_keys=True)
        key = event_key or hashlib.sha256(f"{project_id}|{key_material}".encode()).hexdigest()
        now = datetime.utcnow()
        try:
            result = await db.memory_index_events.insert_one({
                "project_id": pid,
                "event_key": key,
                "project_event_id": project_event_id,
                "status": "unsequenced",
                "payload": payload,
                "attempts": 0,
                "created_at": now,
                "updated_at": now,
            })
        except DuplicateKeyError:
            existing = await db.memory_index_events.find_one({"event_key": key})
            return {
                "event_id": str(existing.get("_id")) if existing else None,
                "event_key": key,
                "duplicate_delivery": True,
                "sequence": existing.get("sequence") if existing else None,
            }
        checkpoint = await db.memory_index_checkpoints.find_one_and_update(
            {"_id": checkpoint["_id"]},
            {"$inc": {"authority_state_version": 1, "pending_updates": 1}, "$set": {
                "status": LAGGING,
                "updated_at": now,
                "fallback_reason": "pending_index_updates",
            }},
            return_document=ReturnDocument.AFTER,
        )
        sequence = int(checkpoint.get("authority_state_version") or 0)
        await db.memory_index_events.update_one(
            {"_id": result.inserted_id},
            {"$set": {"sequence": sequence, "status": "pending", "updated_at": datetime.utcnow()}},
        )
        memory_index_cache.invalidate(project_id)
        return {
            "event_id": str(result.inserted_id),
            "event_key": key,
            "duplicate_delivery": False,
            "sequence": sequence,
        }

    async def recover_unsequenced_events(self, db, project_id: str) -> int:
        pid = _pid(project_id)
        recovered = 0
        async for event in db.memory_index_events.find(
            {"project_id": pid, "status": "unsequenced"}, sort=[("created_at", 1), ("_id", 1)]
        ):
            checkpoint = await self._ensure_checkpoint(db, project_id)
            checkpoint = await db.memory_index_checkpoints.find_one_and_update(
                {"_id": checkpoint["_id"]},
                {"$inc": {"authority_state_version": 1, "pending_updates": 1}, "$set": {
                    "status": LAGGING,
                    "index_complete": False,
                    "verification_required": True,
                    "fallback_reason": "recovered_unsequenced_event",
                    "updated_at": datetime.utcnow(),
                }},
                return_document=ReturnDocument.AFTER,
            )
            await db.memory_index_events.update_one(
                {"_id": event["_id"], "status": "unsequenced"},
                {"$set": {
                    "sequence": int(checkpoint.get("authority_state_version") or 0),
                    "status": "pending",
                    "updated_at": datetime.utcnow(),
                }},
            )
            recovered += 1
        return recovered

    async def _find_owner(self, db, project_id: str, source_type: str, payload: Dict[str, Any]):
        pid = _pid(project_id)
        if source_type == "project":
            return await db.projects.find_one({"_id": pid})
        spec = SOURCE_SPECS.get(source_type)
        if not spec:
            return None
        collection_name, _fields = spec
        physical = str(payload.get("physical_source_id") or "")
        if physical and ObjectId.is_valid(physical):
            owner = await db[collection_name].find_one({"_id": ObjectId(physical), "project_id": pid})
            if owner:
                return owner
        selector = dict(payload.get("selector") or {})
        if selector:
            selector["project_id"] = pid
            owner = await db[collection_name].find_one(selector)
            if owner:
                return owner
        logical_id = str(payload.get("logical_source_id") or "")
        if logical_id:
            conditions = [{field: logical_id} for field in SOURCE_ID_FIELDS.get(source_type, ())]
            if ObjectId.is_valid(logical_id):
                conditions.append({"_id": ObjectId(logical_id)})
            if conditions:
                return await db[collection_name].find_one({"project_id": pid, "$or": conditions})
        return None

    async def _apply_owner(self, db, project_id: str, source_type: str, owner: Dict[str, Any]) -> Dict[str, int]:
        phase_b_writes = phase_b_invalidated = 0
        if source_type != "atomic_memory":
            from app.services.memory_phase_b_service import memory_phase_b_service
            derived = await memory_phase_b_service.sync_owner(db, project_id, source_type, owner)
            phase_b_writes += int(derived.get("writes") or 0)
            phase_b_invalidated += int(derived.get("invalidated") or 0)
            for atomic in derived.get("documents") or []:
                if atomic.get("active") is False:
                    atomic_id = str(atomic.get("memory_id") or "")
                    result = await db.memory_embeddings.update_many(
                        {"project_id": _pid(project_id), "source_type": "atomic_memory", "source_id": atomic_id, "active": {"$ne": False}},
                        {"$set": {"active": False, "updated_at": datetime.utcnow()}},
                    )
                    phase_b_invalidated += int(result.modified_count)
                    continue
                atomic_materialized = materialize_owner_memory("atomic_memory", atomic)
                if not atomic_materialized:
                    continue
                atomic_result = await index_memory(
                    db,
                    project_id=project_id,
                    source_type="atomic_memory",
                    source_id=atomic_materialized["logical_source_id"],
                    source_version=atomic_materialized["source_version"],
                    physical_source_id=atomic_materialized["physical_source_id"],
                    content=atomic_materialized["content"],
                    metadata=atomic_materialized["metadata"],
                )
                phase_b_writes += int(atomic_result.get("writes") or 0)
                phase_b_invalidated += int(atomic_result.get("invalidated") or 0)
        materialized = materialize_owner_memory(source_type, owner)
        if not materialized:
            return {"owners_inspected": 1, "writes": 0, "invalidated": 0, "unchanged": 1, "phase_b_writes": phase_b_writes, "phase_b_invalidated": phase_b_invalidated}
        result = await index_memory(
            db,
            project_id=project_id,
            source_type=source_type,
            source_id=materialized["logical_source_id"],
            source_version=materialized["source_version"],
            physical_source_id=materialized["physical_source_id"],
            content=materialized["content"],
            metadata=materialized["metadata"],
        )
        return {
            "owners_inspected": 1,
            "writes": int(result.get("writes") or 0),
            "invalidated": int(result.get("invalidated") or 0),
            "unchanged": int(bool(result.get("unchanged"))),
            "phase_b_writes": phase_b_writes,
            "phase_b_invalidated": phase_b_invalidated,
        }

    async def _apply_event(self, db, project_id: str, event: Dict[str, Any]) -> Dict[str, int]:
        payload = dict(event.get("payload") or {})
        source_type = str(payload.get("source_type") or "")
        totals = {"owners_inspected": 0, "writes": 0, "invalidated": 0, "unchanged": 0}
        if source_type == "source_batch":
            since = payload.get("changed_since")
            if isinstance(since, str):
                try:
                    since = datetime.fromisoformat(since.rstrip("Z"))
                except ValueError:
                    since = None
            for item_type in payload.get("source_types") or SOURCE_SPECS.keys():
                spec = SOURCE_SPECS.get(item_type)
                if not spec:
                    continue
                query: Dict[str, Any] = {"project_id": _pid(project_id)}
                if since:
                    query["updated_at"] = {"$gte": since}
                async for owner in db[spec[0]].find(query):
                    stats = await self._apply_owner(db, project_id, item_type, owner)
                    for key in totals:
                        totals[key] += stats[key]
            return totals

        owner = await self._find_owner(db, project_id, source_type, payload)
        if owner:
            return await self._apply_owner(db, project_id, source_type, owner)

        # Resolve current state, not event order: only invalidate when the owner
        # is actually absent.  This prevents a delayed delete from overriding a
        # later recreate/update.
        logical_source = str(payload.get("logical_source_id") or "")
        physical_source = str(payload.get("physical_source_id") or "")
        filters: List[Dict[str, Any]] = []
        if logical_source:
            filters.append({"source_id": logical_source})
            filters.append({"metadata.logical_source_id": logical_source})
        if physical_source:
            filters.append({"metadata.physical_source_id": physical_source})
        if not filters:
            return totals
        if logical_source and source_type != "atomic_memory":
            from app.services.memory_phase_b_service import memory_phase_b_service
            atomic_invalidated = await memory_phase_b_service.invalidate_owner(
                db, project_id, source_type, logical_source
            )
            totals["phase_b_invalidated"] = atomic_invalidated
        result = await db.memory_embeddings.update_many(
            {
                "project_id": _pid(project_id),
                "source_type": source_type,
                "active": {"$ne": False},
                "$or": filters,
            },
            {"$set": {
                "active": False,
                "invalidated_by_event": str(event.get("_id") or ""),
                "updated_at": datetime.utcnow(),
            }},
        )
        memory_index_cache.invalidate(project_id)
        totals["invalidated"] = int(result.modified_count)
        totals["writes"] = int(result.modified_count)
        return totals

    async def process_pending(self, db, project_id: str, *, limit: int = SYNC_PENDING_LIMIT) -> Dict[str, Any]:
        pid = _pid(project_id)
        await self.recover_unsequenced_events(db, project_id)
        started = time.perf_counter()
        aggregate = {"processed": 0, "owners_inspected": 0, "writes": 0, "invalidated": 0, "unchanged": 0}
        cursor = db.memory_index_events.find(
            {"project_id": pid, "status": {"$in": ["pending", "failed"]}},
            sort=[("sequence", 1), ("created_at", 1)],
        ).limit(max(1, int(limit)))
        async for event in cursor:
            claimed = await db.memory_index_events.find_one_and_update(
                {"_id": event["_id"], "status": {"$in": ["pending", "failed"]}},
                {"$set": {"status": "processing", "started_at": datetime.utcnow()}, "$inc": {"attempts": 1}},
                return_document=ReturnDocument.AFTER,
            )
            if not claimed:
                continue
            try:
                stats = await self._apply_event(db, project_id, claimed)
                await db.memory_index_events.update_one(
                    {"_id": claimed["_id"]},
                    {"$set": {"status": "processed", "result": stats, "processed_at": datetime.utcnow(), "updated_at": datetime.utcnow()}, "$unset": {"error": ""}},
                )
                aggregate["processed"] += 1
                for key in ("owners_inspected", "writes", "invalidated", "unchanged"):
                    aggregate[key] += int(stats.get(key) or 0)
            except Exception as exc:
                await db.memory_index_events.update_one(
                    {"_id": claimed["_id"]},
                    {"$set": {"status": "failed", "error": f"{type(exc).__name__}: {str(exc)[:500]}", "updated_at": datetime.utcnow()}},
                )
                await db.memory_index_checkpoints.update_one(
                    {"project_id": pid},
                    {"$set": {
                        "status": FAILED,
                        "index_complete_before_failure": bool((await self._ensure_checkpoint(db, project_id)).get("index_complete")),
                        "index_complete": False,
                        "fallback_reason": "index_event_failed",
                        "updated_at": datetime.utcnow(),
                    }},
                )
                memory_index_cache.invalidate(project_id)
                aggregate["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
                break

        pending = await db.memory_index_events.count_documents(
            {"project_id": pid, "status": {"$in": ["pending", "processing", "failed", "unsequenced"]}}
        )
        last = await db.memory_index_events.find_one(
            {"project_id": pid, "status": "processed"}, sort=[("sequence", -1)]
        )
        checkpoint = await self._ensure_checkpoint(db, project_id)
        complete_before = bool(
            checkpoint.get("index_complete")
            or checkpoint.get("index_complete_before_failure")
        )
        final_status = READY if pending == 0 and complete_before else (FAILED if aggregate.get("error") else (LAGGING if complete_before else INCOMPLETE))
        update: Dict[str, Any] = {
            "status": final_status,
            "pending_updates": pending,
            "failed_updates": 1 if aggregate.get("error") else 0,
            "updated_at": datetime.utcnow(),
            "last_successful_update": datetime.utcnow() if aggregate["processed"] else checkpoint.get("last_successful_update"),
            "last_processed_event": str(last.get("_id")) if last else checkpoint.get("last_processed_event"),
            "records_indexed": int(checkpoint.get("records_indexed") or 0) + aggregate["writes"],
            "records_invalidated": int(checkpoint.get("records_invalidated") or 0) + aggregate["invalidated"],
            "duplicate_prevention": int(checkpoint.get("duplicate_prevention") or 0) + aggregate["unchanged"],
            "fallback_reason": None if final_status == READY else ("index_event_failed" if aggregate.get("error") else "index_not_complete"),
            "index_complete": complete_before if final_status == READY else bool(checkpoint.get("index_complete")),
        }
        if last:
            update["processed_version"] = int(last.get("sequence") or checkpoint.get("processed_version") or 0)
        await db.memory_index_checkpoints.update_one({"project_id": pid}, {"$set": update})
        if final_status == READY:
            from app.services.memory_phase_c_service import memory_phase_c_service
            await memory_phase_c_service.mark_incremental_processed(
                db, project_id, processed_version=int(update.get("processed_version") or checkpoint.get("processed_version") or 0),
            )
        if final_status == READY:
            await db.memory_index_checkpoints.update_one(
                {"project_id": pid}, {"$unset": {"index_complete_before_failure": ""}}
            )
        aggregate["pending"] = int(pending)
        aggregate["latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
        aggregate["status"] = final_status
        return aggregate

    async def prepare_for_retrieval(
        self,
        db,
        project_id: str,
        *,
        strict_writing: bool,
    ) -> Dict[str, Any]:
        started = time.perf_counter()
        status = await self.get_status(db, project_id)
        action = "read_existing_index"
        processing = None
        if status["status"] == LAGGING and status["pending_updates"] <= SYNC_PENDING_LIMIT:
            processing = await self.process_pending(db, project_id, limit=SYNC_PENDING_LIMIT)
            status = await self.get_status(db, project_id)
            action = "applied_bounded_pending_updates"
        fallback = bool(strict_writing and status["status"] != READY)
        reason = None
        if fallback:
            reason = {
                LAGGING: "known_lag_exceeds_sync_bound",
                INCOMPLETE: "index_incomplete_or_unverified",
                REBUILDING: "index_rebuilding",
                FAILED: "index_update_failed",
            }.get(status["status"], "index_not_ready")
            action = "safe_direct_authority_fallback"
        return {
            **status,
            "action": action,
            "fallback_required": fallback,
            "fallback_reason": reason or status.get("fallback_reason"),
            "checkpoint_verification_ms": round((time.perf_counter() - started) * 1000, 3),
            "synchronous_update": processing,
        }

    async def direct_authority_documents(self, db, project_id: str) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
        pid = _pid(project_id)
        rows: List[Dict[str, Any]] = []
        inspected = 0
        project = await db.projects.find_one({"_id": pid})
        owners = [("project", project)] if project else []
        for source_type, (collection, _fields) in SOURCE_SPECS.items():
            async for owner in db[collection].find({"project_id": pid}):
                owners.append((source_type, owner))
        context = RetrievalEligibilityContext(safe_for_writing=True, consumer="strict_fallback", project_id=project_id)
        for source_type, owner in owners:
            inspected += 1
            materialized = materialize_owner_memory(source_type, owner)
            if not materialized:
                continue
            level = str(materialized["metadata"].get("authority_level") or "derived")
            if AUTHORITY_PRIORITY.get(level, 0) < AUTHORITY_PRIORITY["project"]:
                continue
            row = {
                "_id": f"direct:{materialized['logical_source_id']}:{materialized['source_version']}",
                "project_id": pid,
                "source_type": source_type,
                "source_id": materialized["logical_source_id"],
                "source_version": materialized["source_version"],
                "content": materialized["content"],
                "content_hash": materialized["content_hash"],
                "embedding": embed_text(materialized["content"]),
                "metadata": materialized["metadata"],
                "active": True,
            }
            if retrieval_eligibility_policy.evaluate(row, context).eligible:
                rows.append(row)
        return rows, {"full_source_scans_query": len(SOURCE_SPECS) + 1, "owner_records_inspected_query": inspected, "index_writes_query": 0}

    async def rebuild(
        self,
        db,
        project_id: str,
        *,
        dry_run: bool = False,
        resume: bool = True,
        interrupt_after_sources: int | None = None,
    ) -> Dict[str, Any]:
        pid = _pid(project_id)
        started = time.perf_counter()
        if not dry_run:
            from app.services.memory_phase_b_service import memory_phase_b_service
            await memory_phase_b_service.rebuild_project(db, project_id)
        checkpoint = await self._ensure_checkpoint(db, project_id)
        previous = dict(checkpoint.get("rebuild") or {})
        rebuild_id = str(previous.get("rebuild_id") or uuid4()) if resume else str(uuid4())
        source_order = ["project", *SOURCE_SPECS.keys()]
        source_index = int(previous.get("next_source_index") or 0) if resume and previous.get("rebuild_id") == rebuild_id else 0
        if resume and previous.get("rebuild_id") == rebuild_id and "start_authority_version" in previous:
            start_version = int(previous.get("start_authority_version") or 0)
        else:
            start_version = int(checkpoint.get("authority_state_version") or 0)
        if not dry_run:
            await db.memory_index_checkpoints.update_one(
                {"project_id": pid},
                {"$set": {
                    "status": REBUILDING,
                    "index_complete": False,
                    "fallback_reason": "index_rebuilding",
                    "rebuild": {
                        "rebuild_id": rebuild_id,
                        "start_authority_version": start_version,
                        "next_source_index": source_index,
                        "started_at": previous.get("started_at") or datetime.utcnow(),
                    },
                    "updated_at": datetime.utcnow(),
                }},
            )
        materialized_rows: List[Dict[str, Any]] = []
        sources_completed = 0
        for position, source_type in enumerate(source_order):
            if position < source_index and not dry_run:
                continue
            if source_type == "project":
                project = await db.projects.find_one({"_id": pid})
                owner_rows = [project] if project else []
            else:
                owner_rows = []
                async for owner in db[SOURCE_SPECS[source_type][0]].find({"project_id": pid}, sort=[("_id", 1)]):
                    owner_rows.append(owner)
            for owner in owner_rows:
                row = materialize_owner_memory(source_type, owner)
                if not row:
                    continue
                materialized_rows.append(row)
                if not dry_run:
                    await db.memory_index_staging.replace_one(
                        {
                            "project_id": pid,
                            "rebuild_id": rebuild_id,
                            "source_type": row["source_type"],
                            "logical_source_id": row["logical_source_id"],
                            "source_version": row["source_version"],
                        },
                        {**row, "project_id": pid, "rebuild_id": rebuild_id, "staged_at": datetime.utcnow()},
                        upsert=True,
                    )
            sources_completed += 1
            if not dry_run:
                await db.memory_index_checkpoints.update_one(
                    {"project_id": pid},
                    {"$set": {"rebuild.next_source_index": position + 1, "rebuild.last_source_type": source_type, "updated_at": datetime.utcnow()}},
                )
            if interrupt_after_sources and sources_completed >= interrupt_after_sources:
                return {
                    "status": REBUILDING,
                    "interrupted": True,
                    "rebuild_id": rebuild_id,
                    "next_source_index": position + 1,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                }

        if dry_run:
            unique = {(row["source_type"], row["logical_source_id"], row["source_version"]) for row in materialized_rows}
            return {
                "dry_run": True,
                "owner_records": len(materialized_rows),
                "logical_records": len(unique),
                "duplicates": len(materialized_rows) - len(unique),
                "logical_hash": _stable_hash(materialized_rows),
                "authority_mutations": 0,
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            }

        staged = await db.memory_index_staging.find({"project_id": pid, "rebuild_id": rebuild_id}).to_list(length=None)
        identities = {(row["source_type"], row["logical_source_id"], int(row["source_version"])) for row in staged}
        if len(identities) != len(staged):
            await self.mark_needs_verification(db, project_id, "rebuild_duplicate_logical_identity")
            return {"status": INCOMPLETE, "validated": False, "reason": "duplicate_logical_identity"}
        latest = await db.memory_index_checkpoints.find_one({"project_id": pid})
        if int(latest.get("authority_state_version") or 0) != start_version:
            await self.mark_needs_verification(db, project_id, "owner_changed_during_rebuild")
            return {"status": INCOMPLETE, "validated": False, "reason": "owner_changed_during_rebuild", "restart_required": True}

        writes = invalidated = unchanged = 0
        active_keys = set()
        for row in staged:
            result = await index_memory(
                db,
                project_id=project_id,
                source_type=row["source_type"],
                source_id=row["logical_source_id"],
                source_version=int(row["source_version"]),
                physical_source_id=row.get("physical_source_id"),
                content=row["content"],
                metadata=row["metadata"],
            )
            writes += int(result.get("writes") or 0)
            invalidated += int(result.get("invalidated") or 0)
            unchanged += int(bool(result.get("unchanged")))
            active_keys.add(logical_identity(row["source_type"], row["logical_source_id"], int(row["source_version"])))
        async for indexed in db.memory_embeddings.find({"project_id": pid, "active": {"$ne": False}}):
            metadata = indexed.get("metadata") or {}
            key = str(metadata.get("logical_identity") or logical_identity(
                str(indexed.get("source_type") or "memory"),
                str(metadata.get("logical_source_id") or indexed.get("source_id") or ""),
                int(metadata.get("owner_source_version") or indexed.get("source_version") or 1),
            ))
            if key not in active_keys:
                result = await db.memory_embeddings.update_one(
                    {"_id": indexed["_id"]},
                    {"$set": {"active": False, "invalidated_by_rebuild": rebuild_id, "updated_at": datetime.utcnow()}},
                )
                invalidated += int(result.modified_count)
                writes += int(result.modified_count)
        logical_hash = _stable_hash(staged)
        finished = datetime.utcnow()
        # The validated snapshot includes every owner change represented by
        # events up to the rebuild watermark. Those events can be acknowledged
        # without replaying writes against the just-validated index.
        acknowledged = await db.memory_index_events.update_many(
            {
                "project_id": pid,
                "sequence": {"$lte": start_version},
                "status": {"$in": ["pending", "processing", "failed"]},
            },
            {"$set": {
                "status": "processed",
                "processed_by_rebuild": rebuild_id,
                "processed_at": finished,
                "updated_at": finished,
            }, "$unset": {"error": ""}},
        )
        await db.memory_index_checkpoints.update_one(
            {"project_id": pid},
            {"$set": {
                "status": READY,
                "index_complete": True,
                "verification_required": False,
                "processed_version": start_version,
                "pending_updates": 0,
                "failed_updates": 0,
                "last_rebuild": finished,
                "last_successful_update": finished,
                "records_indexed": len(staged),
                "records_invalidated": invalidated,
                "duplicate_prevention": unchanged,
                "logical_record_count": len(staged),
                "logical_hash": logical_hash,
                "fallback_reason": None,
                "rebuild": {
                    "rebuild_id": rebuild_id,
                    "start_authority_version": start_version,
                    "next_source_index": len(source_order),
                    "status": "completed",
                    "completed_at": finished,
                },
                "updated_at": finished,
            }},
        )
        from app.services.memory_phase_c_service import memory_phase_c_service
        phase_c = await memory_phase_c_service.mark_rebuild_complete(
            db, project_id, processed_version=start_version, indexed_records=len(staged),
        )
        memory_index_cache.invalidate(project_id)
        return {
            "status": READY,
            "validated": True,
            "resumable": True,
            "rebuild_id": rebuild_id,
            "logical_records": len(staged),
            "logical_hash": logical_hash,
            "writes": writes,
            "invalidated": invalidated,
            "unchanged": unchanged,
            "authority_mutations": 0,
            "events_acknowledged": int(acknowledged.modified_count),
            "phase_c": phase_c,
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
        }

    async def verify(self, db, project_id: str) -> Dict[str, Any]:
        dry = await self.rebuild(db, project_id, dry_run=True)
        checkpoint = await self.get_status(db, project_id)
        actual_rows = []
        async for row in db.memory_embeddings.find({"project_id": _pid(project_id), "active": {"$ne": False}}):
            metadata = row.get("metadata") or {}
            actual_rows.append({
                "source_type": row.get("source_type"),
                "logical_source_id": metadata.get("logical_source_id") or row.get("source_id"),
                "source_version": int(metadata.get("owner_source_version") or row.get("source_version") or 1),
                "content_hash": row.get("content_hash") or hashlib.sha256(str(row.get("content") or "").encode()).hexdigest(),
            })
        actual_hash = _stable_hash(actual_rows)
        expected_hash = dry["logical_hash"]
        complete = dry["logical_records"] == len(actual_rows) and expected_hash == actual_hash
        if not complete:
            await self.mark_needs_verification(db, project_id, "checkpoint_or_index_mismatch")
        return {
            "complete": complete,
            "expected_count": dry["logical_records"],
            "actual_count": len(actual_rows),
            "expected_hash": expected_hash,
            "actual_hash": actual_hash,
            "checkpoint_status_before": checkpoint["status"],
            "mismatch_detected": not complete,
            "authority_mutations": 0,
        }

    async def notify_project_event(
        self,
        db,
        project_id: str,
        event_type: str,
        payload: Dict[str, Any],
        *,
        project_event_id: str,
        created_at: datetime,
    ) -> Dict[str, Any] | None:
        exact: Dict[str, tuple[str, str]] = {
            "project_created": ("project", "create"),
            "project_updated": ("project", "update"),
            "story_vision_updated": ("story_vision", "update"),
            "question_resolved": ("decision", "confirm"),
            "decision_changed": ("decision", "supersede"),
            "question_reopened": ("decision", "reconsider"),
            "canon_proposal_reviewed": ("canon", "approve"),
        }
        if event_type in exact:
            source_type, operation = exact[event_type]
            selector: Dict[str, Any] = {}
            logical_id = None
            for key in ("decision_id", "question_id", "canon_id", "vision_id", "record_id"):
                if payload.get(key):
                    logical_id = str(payload[key])
                    break
            return await self.enqueue_change(
                db, project_id,
                source_type=source_type,
                operation=operation,
                logical_source_id=logical_id,
                selector=selector,
                event_key=f"project_event:{project_event_id}",
                project_event_id=project_event_id,
                new_project=event_type == "project_created",
            )
        if event_type.startswith("story_knowledge_candidate_"):
            return await self.enqueue_change(
                db, project_id,
                source_type="source_batch",
                operation=event_type.rsplit("_", 1)[-1],
                source_types=("character", "relationship", "plot_thread", "story_arc", "timeline_v2", "knowledge", "artifact", "mystery"),
                changed_since=created_at - timedelta(seconds=10),
                event_key=f"project_event:{project_event_id}",
                project_event_id=project_event_id,
            )
        broad_events = {
            "story_bible_updated", "agent_completed", "discussion_decision",
            "workspace_entry_created", "shared_narrative_context_updated",
            "project_intelligence_refreshed", "story_knowledge_candidates_projected",
        }
        if event_type in broad_events:
            checkpoint = await self._ensure_checkpoint(db, project_id)
            since = checkpoint.get("last_successful_update") or (created_at - timedelta(minutes=10))
            return await self.enqueue_change(
                db, project_id,
                source_type="source_batch",
                operation="refresh_changed_owners",
                source_types=SOURCE_SPECS.keys(),
                changed_since=since - timedelta(seconds=1) if isinstance(since, datetime) else None,
                event_key=f"project_event:{project_event_id}",
                project_event_id=project_event_id,
            )
        return None

    async def record_hook_failure(self, db, project_id: str, reason: str) -> None:
        try:
            await self.mark_needs_verification(db, project_id, f"event_hook_failed:{reason[:180]}")
        except Exception:
            # The authority mutation has already committed.  Startup/first-use
            # verification still detects the missing checkpoint.
            return


memory_incremental_index_service = MemoryIncrementalIndexService()
