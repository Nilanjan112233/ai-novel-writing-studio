"""Phase A incremental indexing, recovery, and safety regressions."""
from __future__ import annotations

from datetime import datetime

import pytest
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings as app_config
from app.services.memory_incremental_index_service import (
    FAILED,
    INCOMPLETE,
    READY,
    REBUILDING,
    memory_incremental_index_service,
)
from app.services.memory_provider import NativeNovelForgeMemoryProvider


def _motor():
    client = AsyncIOMotorClient(app_config.mongodb_url)
    return client, client[app_config.database_name]


async def _cleanup(db, pid):
    for name in (
        "projects", "plot_threads", "character_bibles", "knowledge_entries",
        "memory_embeddings", "memory_index_checkpoints", "memory_index_events",
        "memory_index_staging", "memory_provider_events",
    ):
        await db[name].delete_many({"project_id": pid})
    await db.projects.delete_many({"_id": pid})


@pytest.mark.asyncio
async def test_rebuild_makes_retrieval_read_only_and_cacheable(client):
    motor, db = _motor()
    pid = ObjectId()
    try:
        await db.projects.insert_one({"_id": pid, "title": "Phase A", "premise": "Mara guards Northglass."})
        await db.plot_threads.insert_one({
            "project_id": pid, "thread_id": "northglass", "title": "Northglass",
            "description": "Mara guards Northglass.", "status": "open",
            "authority_status": "confirmed", "updated_at": datetime.utcnow(),
        })
        assert (await memory_incremental_index_service.get_status(db, str(pid)))["status"] == INCOMPLETE
        rebuilt = await memory_incremental_index_service.rebuild(db, str(pid))
        assert rebuilt["status"] == READY
        provider = NativeNovelForgeMemoryProvider(db)
        first = await provider.recall(
            project_id=str(pid), query="Who guards Northglass?", top_k=8,
            retrieval_context={"safe_for_writing": True, "consumer": "discovery_writer"},
        )
        second = await provider.recall(
            project_id=str(pid), query="Who guards Northglass?", top_k=8,
            retrieval_context={"safe_for_writing": True, "consumer": "discovery_writer"},
        )
        assert any("Mara" in hit.content for hit in first.hits)
        assert first.diagnostics["full_source_scans_query"] == 0
        assert first.diagnostics["owner_records_inspected_query"] == 0
        assert first.diagnostics["index_writes_query"] == 0
        assert second.diagnostics["index_cache_hit"] is True
    finally:
        await _cleanup(db, pid)
        motor.close()


@pytest.mark.asyncio
async def test_single_mutation_is_idempotent_and_inspects_one_owner(client):
    motor, db = _motor()
    pid = ObjectId()
    try:
        await db.projects.insert_one({"_id": pid, "title": "Mutation"})
        owner = {
            "project_id": pid, "thread_id": "rare-thread", "title": "Dormant thread",
            "description": "The Zephyrglass sleeps.", "status": "open",
            "authority_status": "confirmed", "updated_at": datetime.utcnow(),
        }
        inserted = await db.plot_threads.insert_one(owner)
        await memory_incremental_index_service.rebuild(db, str(pid))
        await db.plot_threads.update_one(
            {"_id": inserted.inserted_id},
            {"$set": {"description": "The Zephyrglass wakes.", "updated_at": datetime.utcnow()}},
        )
        event = await memory_incremental_index_service.enqueue_change(
            db, str(pid), source_type="plot_thread", operation="update",
            physical_source_id=str(inserted.inserted_id), event_key="mutation-one",
        )
        duplicate = await memory_incremental_index_service.enqueue_change(
            db, str(pid), source_type="plot_thread", operation="update",
            physical_source_id=str(inserted.inserted_id), event_key="mutation-one",
        )
        assert event["duplicate_delivery"] is False
        assert duplicate["duplicate_delivery"] is True
        processed = await memory_incremental_index_service.process_pending(db, str(pid))
        assert processed["owners_inspected"] == 1
        assert processed["writes"] == 1
        again = await memory_incremental_index_service.process_pending(db, str(pid))
        assert again["writes"] == 0
        assert await db.memory_embeddings.count_documents({
            "project_id": pid, "source_type": "plot_thread", "source_id": "rare-thread", "active": True,
        }) == 1
        assert (await memory_incremental_index_service.get_status(db, str(pid)))["status"] == READY
    finally:
        await _cleanup(db, pid)
        motor.close()


@pytest.mark.asyncio
async def test_crash_duplicate_order_and_failure_recovery(client, monkeypatch):
    motor, db = _motor()
    pid = ObjectId()
    try:
        await db.projects.insert_one({"_id": pid, "title": "Recovery"})
        owner_id = ObjectId()
        await db.plot_threads.insert_one({
            "_id": owner_id, "project_id": pid, "thread_id": "ordered",
            "title": "Current owner", "description": "Current state wins.",
            "status": "open", "authority_status": "confirmed", "updated_at": datetime.utcnow(),
        })
        await memory_incremental_index_service.rebuild(db, str(pid))
        event = await memory_incremental_index_service.enqueue_change(
            db, str(pid), source_type="plot_thread", operation="delete",
            logical_source_id="ordered", event_key="late-delete",
        )
        await db.memory_index_events.update_one(
            {"_id": ObjectId(event["event_id"])}, {"$set": {"status": "processing"}},
        )
        recovered = await memory_incremental_index_service.recover_interrupted(db)
        assert recovered["events_requeued"] >= 1
        result = await memory_incremental_index_service.process_pending(db, str(pid))
        assert result["processed"] == 1
        assert await db.memory_embeddings.find_one({
            "project_id": pid, "source_type": "plot_thread", "source_id": "ordered", "active": True,
        })

        await memory_incremental_index_service.enqueue_change(
            db, str(pid), source_type="plot_thread", operation="update",
            physical_source_id=str(owner_id), event_key="temporary-mongo-failure",
        )
        original = memory_incremental_index_service._apply_event

        async def fail_once(*_args, **_kwargs):
            raise RuntimeError("temporary Mongo failure")

        monkeypatch.setattr(memory_incremental_index_service, "_apply_event", fail_once)
        failed = await memory_incremental_index_service.process_pending(db, str(pid))
        assert failed["status"] == FAILED
        monkeypatch.setattr(memory_incremental_index_service, "_apply_event", original)
        retried = await memory_incremental_index_service.process_pending(db, str(pid))
        assert retried["status"] == READY
    finally:
        await _cleanup(db, pid)
        motor.close()


@pytest.mark.asyncio
async def test_interrupted_rebuild_resumes_and_owner_change_blocks_commit(client):
    motor, db = _motor()
    pid = ObjectId()
    try:
        await db.projects.insert_one({"_id": pid, "title": "Resume"})
        await db.character_bibles.insert_one({
            "project_id": pid, "character_id": "mara", "name": "Mara",
            "description": "Keeper of Northglass", "authority_status": "confirmed",
            "updated_at": datetime.utcnow(),
        })
        interrupted = await memory_incremental_index_service.rebuild(
            db, str(pid), interrupt_after_sources=2
        )
        assert interrupted["status"] == REBUILDING
        resumed = await memory_incremental_index_service.rebuild(db, str(pid), resume=True)
        assert resumed["status"] == READY
        assert resumed["validated"] is True

        interrupted = await memory_incremental_index_service.rebuild(
            db, str(pid), resume=False, interrupt_after_sources=1
        )
        assert interrupted["status"] == REBUILDING
        await memory_incremental_index_service.enqueue_change(
            db, str(pid), source_type="character", operation="update",
            logical_source_id="mara", event_key="owner-changed-mid-rebuild",
        )
        refused = await memory_incremental_index_service.rebuild(db, str(pid), resume=True)
        assert refused["status"] == INCOMPLETE
        assert refused["reason"] == "owner_changed_during_rebuild"
        assert refused["restart_required"] is True
    finally:
        await _cleanup(db, pid)
        motor.close()


@pytest.mark.asyncio
async def test_verify_detects_missing_and_corrupted_derived_rows(client):
    motor, db = _motor()
    pid = ObjectId()
    try:
        await db.projects.insert_one({"_id": pid, "title": "Verify"})
        await db.plot_threads.insert_one({
            "project_id": pid, "thread_id": "verify-thread", "title": "Verify thread",
            "description": "A dormant callback.", "status": "open",
            "authority_status": "confirmed", "updated_at": datetime.utcnow(),
        })
        await memory_incremental_index_service.rebuild(db, str(pid))
        good = await memory_incremental_index_service.verify(db, str(pid))
        assert good["complete"] is True
        await db.memory_embeddings.update_one(
            {"project_id": pid, "source_type": "plot_thread"},
            {"$set": {"content_hash": "corrupted"}},
        )
        bad = await memory_incremental_index_service.verify(db, str(pid))
        assert bad["mismatch_detected"] is True
        assert (await memory_incremental_index_service.get_status(db, str(pid)))["status"] == INCOMPLETE
    finally:
        await _cleanup(db, pid)
        motor.close()
