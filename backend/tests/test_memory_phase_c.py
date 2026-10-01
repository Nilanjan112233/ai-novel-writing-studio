"""Phase C lexical candidates, ranking, incremental integration, and fallback."""
from __future__ import annotations

from datetime import datetime

import pytest
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings as app_config
from app.services.memory_incremental_index_service import memory_incremental_index_service
from app.services.memory_phase_c_ranker import PHASE_C_RANKER_VERSION
from app.services.memory_phase_c_service import memory_phase_c_service
from app.services.memory_provider import NativeNovelForgeMemoryProvider


def _motor():
    client = AsyncIOMotorClient(app_config.mongodb_url)
    return client, client[app_config.database_name]


async def _cleanup(db, pid):
    for name in (
        "projects", "artifact_registry", "knowledge_entries", "plot_threads",
        "memory_embeddings", "memory_index_checkpoints", "memory_index_events",
        "memory_index_staging", "atomic_memories", "memory_phase_b_checkpoints",
        "memory_phase_c_checkpoints",
    ):
        await db[name].delete_many({"project_id": pid})
    await db.projects.delete_many({"_id": pid})


async def _seed_and_rebuild(db, pid):
    await db.projects.insert_one({"_id": pid, "title": "Phase C"})
    await db.artifact_registry.insert_many([
        {"project_id": pid, "artifact_id": "northglass-v1", "item": "Northglass", "owner": "Mara", "status": "confirmed", "authority_status": "confirmed", "version_number": 1, "valid_from_chapter": 3, "valid_to_chapter": 7, "active": True},
        {"project_id": pid, "artifact_id": "northglass-v2", "item": "Northglass", "owner": "Ivo", "status": "confirmed", "authority_status": "confirmed", "version_number": 2, "valid_from_chapter": 8, "active": True},
        {"project_id": pid, "artifact_id": "asterlock", "item": "Asterlock-500", "owner": "Seraphine Quill", "history": "Recovered from the drowned archive", "status": "confirmed", "authority_status": "confirmed", "version_number": 1, "active": True},
    ])
    await db.knowledge_entries.insert_one({
        "project_id": pid, "entry_id": "elias-private", "title": "Elias survival", "content": "Elias is alive in the eastern tower.",
        "known_by": ["Ivo"], "not_known_by": ["Mara"], "status": "confirmed", "authority_status": "confirmed",
        "version_number": 1, "valid_from_chapter": 8, "active": True,
    })
    await db.plot_threads.insert_many([
        {"project_id": pid, "thread_id": "bell", "title": "Broken bell promise", "description": "Return the broken bell before the thaw.", "status": "open", "version_number": 1, "active": True},
        {"project_id": pid, "thread_id": "rejected", "title": "Elias villain", "description": "Maybe Elias is secretly the villain.", "status": "rejected", "version_number": 1, "active": True},
    ])
    return await memory_incremental_index_service.rebuild(db, str(pid))


@pytest.mark.asyncio
async def test_phase_c_rebuild_indexes_lexical_fields_and_ranks_exact_callbacks(client):
    motor, db = _motor(); pid = ObjectId()
    try:
        rebuilt = await _seed_and_rebuild(db, pid)
        assert rebuilt["phase_c"]["status"] == "READY"
        status = await memory_phase_c_service.get_status(db, str(pid))
        assert status["complete"] is True and status["ranker_version"] == PHASE_C_RANKER_VERSION
        assert await db.memory_embeddings.count_documents({"project_id": pid, "active": True, "search_terms": "asterlock-500"}) >= 1

        provider = NativeNovelForgeMemoryProvider(db)
        recall = await provider.recall(project_id=str(pid), query="Asterlock-500 drowned archive", top_k=8, retrieval_context={"safe_for_writing": True, "consumer": "test", "as_of_chapter": 10})
        assert recall.strategy == "metadata_lexical_hash_weighted"
        assert recall.hits and "Asterlock-500" in recall.hits[0].content
        assert recall.diagnostics["embedding_records_scored"] < await db.memory_embeddings.count_documents({"project_id": pid, "active": True})
        assert recall.diagnostics["coverage"] == "all_matches_for_selected_terms"
    finally:
        await _cleanup(db, pid); motor.close()


@pytest.mark.asyncio
async def test_phase_c_preserves_temporal_knowledge_and_rejection_safety(client):
    motor, db = _motor(); pid = ObjectId()
    try:
        await _seed_and_rebuild(db, pid)
        provider = NativeNovelForgeMemoryProvider(db)
        old = await provider.recall(project_id=str(pid), query="Who held Northglass?", top_k=8, retrieval_context={"safe_for_writing": True, "as_of_chapter": 5, "consumer": "test"})
        current = await provider.recall(project_id=str(pid), query="Who holds Northglass?", top_k=8, retrieval_context={"safe_for_writing": True, "as_of_chapter": 10, "consumer": "test"})
        mara = await provider.recall(project_id=str(pid), query="What does Mara know about Elias alive?", top_k=8, retrieval_context={"safe_for_writing": True, "as_of_chapter": 10, "pov_character": "Mara", "consumer": "test"})
        writing = await provider.recall(project_id=str(pid), query="Elias secretly villain", top_k=8, retrieval_context={"safe_for_writing": True, "as_of_chapter": 10, "consumer": "test"})
        studio = await provider.recall(project_id=str(pid), query="What did I reject about Elias?", top_k=8, retrieval_context={"safe_for_writing": False, "consumer": "story_studio"})
        assert any("Mara" in hit.content for hit in old.hits) and not any("Ivo" in hit.content for hit in old.hits)
        assert any("Ivo" in hit.content for hit in current.hits) and not any("Mara" in hit.content for hit in current.hits)
        assert not any("eastern tower" in hit.content for hit in mara.hits)
        assert not any("secretly the villain" in hit.content for hit in writing.hits)
        assert any("secretly the villain" in hit.content for hit in studio.hits)
    finally:
        await _cleanup(db, pid); motor.close()


@pytest.mark.asyncio
async def test_phase_c_falls_back_to_complete_phase_b_and_incremental_update_is_bounded(client):
    motor, db = _motor(); pid = ObjectId()
    try:
        await _seed_and_rebuild(db, pid)
        await memory_phase_c_service.mark_failed(db, str(pid), "simulated_corrupt_index")
        provider = NativeNovelForgeMemoryProvider(db)
        fallback = await provider.recall(project_id=str(pid), query="Asterlock-500", top_k=8, retrieval_context={"safe_for_writing": True, "consumer": "test"})
        assert fallback.strategy == "phase_b_complete_scan_fallback"
        assert any("Asterlock-500" in hit.content for hit in fallback.hits)
        assert fallback.diagnostics["fallback_reason"] == "simulated_corrupt_index"

        # A rebuild restores readiness. One owner mutation then changes only
        # its owner/atomic projections and advances both checkpoints.
        await memory_incremental_index_service.rebuild(db, str(pid))
        before = await db.memory_embeddings.count_documents({"project_id": pid, "active": True})
        owner = await db.artifact_registry.find_one({"project_id": pid, "artifact_id": "asterlock"})
        await db.artifact_registry.update_one({"_id": owner["_id"]}, {"$set": {"owner": "Mara", "version_number": 2, "updated_at": datetime.utcnow()}})
        event = await memory_incremental_index_service.enqueue_change(
            db, str(pid), source_type="artifact", physical_source_id=str(owner["_id"]),
            operation="update", event_key="phase-c-bounded-mutation",
        )
        processed = await memory_incremental_index_service.process_pending(db, str(pid))
        after = await db.memory_embeddings.count_documents({"project_id": pid, "active": True})
        status = await memory_phase_c_service.get_status(db, str(pid))
        assert event["duplicate_delivery"] is False and processed["owners_inspected"] <= 3
        assert abs(after - before) <= 3
        assert status["status"] == "READY"
        updated = await provider.recall(project_id=str(pid), query="Who owns Asterlock-500?", top_k=8, retrieval_context={"safe_for_writing": True, "consumer": "test", "as_of_chapter": 10})
        assert any("Mara" in hit.content for hit in updated.hits)
    finally:
        await _cleanup(db, pid); motor.close()
