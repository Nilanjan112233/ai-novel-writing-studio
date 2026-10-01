"""Phase B atomic/episode derivation, provenance, safety, and rebuild tests."""
from __future__ import annotations

from datetime import datetime

import pytest
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings as app_config
from app.services.memory_phase_b_service import (
    build_episode_memory,
    derive_atomic_documents,
    episode_text,
    memory_phase_b_service,
)
from app.services.memory_retrieval_policy import RetrievalEligibilityContext, metadata_for_source, retrieval_eligibility_policy
from app.services.memory_incremental_index_service import memory_incremental_index_service
from app.services.memory_provider import NativeNovelForgeMemoryProvider


def _motor():
    client = AsyncIOMotorClient(app_config.mongodb_url)
    return client, client[app_config.database_name]


async def _cleanup(db, pid):
    for name in (
        "projects", "canon_registry", "artifact_registry", "knowledge_entries",
        "chapter_intelligence", "atomic_memories", "memory_phase_b_checkpoints",
        "memory_embeddings", "memory_index_checkpoints", "memory_index_events", "memory_index_staging",
    ):
        await db[name].delete_many({"project_id": pid})
    await db.projects.delete_many({"_id": pid})


def test_episode_is_versioned_compact_and_provenanced():
    pid = ObjectId()
    intelligence = {
        "project_id": pid, "intelligence_id": "intel-4", "chapter_draft_id": "draft-4",
        "chapter_draft_version": 2, "chapter_number": 4, "active": True,
        "chapter_summary": "Mara enters the marsh and confronts Ivo.",
        "important_events": ["Mara enters the marsh.", "Mara enters the marsh.", "Ivo reveals Northglass."],
        "characters_present": ["Mara", "Ivo", "Mara"],
        "character_changes": [{"character": "Mara", "change": "She begins to trust Ivo."}],
        "relationship_changes": [{"character_a": "Mara", "character_b": "Ivo", "status": "uneasy allies"}],
        "knowledge_revealed": [{"entry_id": "k1", "content": "Elias is alive.", "known_by": ["Ivo"]}],
        "mysteries_advanced": [{"mystery_id": "m1", "question": "Where is Elias?"}],
        "future_obligations": ["Return Northglass."],
    }
    episode = build_episode_memory(intelligence)
    assert episode["derivation_version"] == 1
    assert episode["source_version"] == 2
    assert episode["material_events"].count("Mara enters the marsh.") == 1
    assert episode["evidence_pointer"]["logical_source_id"] == "intel-4"
    assert len(episode_text({**intelligence, "episode_memory": episode})) < len(str(intelligence))


@pytest.mark.asyncio
async def test_atomic_derivation_is_idempotent_provenanced_and_pov_safe(client):
    motor, db = _motor(); pid = ObjectId()
    try:
        owner = {
            "_id": ObjectId(), "project_id": pid, "entry_id": "elias-alive", "version_number": 3,
            "title": "Elias survival", "content": "Elias is alive.", "known_by": ["Ivo"],
            "not_known_by": ["Mara"], "chapter_number": 8, "status": "confirmed", "active": True,
        }
        first = await memory_phase_b_service.sync_owner(db, str(pid), "knowledge", owner)
        second = await memory_phase_b_service.sync_owner(db, str(pid), "knowledge", owner)
        assert first["derived"] == 1
        assert second["writes"] == 0
        assert await db.atomic_memories.count_documents({"project_id": pid, "active": True}) == 1
        atomic = await db.atomic_memories.find_one({"project_id": pid})
        assert atomic["source_owners"][0]["source_version"] == 3
        assert atomic["provenance"]["evidence"][0]["logical_source_id"] == "elias-alive"
        indexed = {**atomic, "source_type": "atomic_memory", "metadata": metadata_for_source("atomic_memory", atomic)}
        decision = retrieval_eligibility_policy.evaluate(indexed, RetrievalEligibilityContext(
            safe_for_writing=True, project_id=str(pid), as_of_chapter=10, pov_character="Mara",
        ))
        assert decision.eligible is False
        assert "explicitly_not_known_by_pov" in decision.reasons
    finally:
        await _cleanup(db, pid); motor.close()


@pytest.mark.asyncio
async def test_conflicting_derived_observation_is_labelled_below_authority(client):
    motor, db = _motor(); pid = ObjectId()
    try:
        base = {"project_id": pid, "subject": "Elias", "predicate": "absence_duration", "active": True, "status": "active"}
        await db.atomic_memories.insert_many([
            {**base, "memory_id": "authority", "fact_key": "a", "compact_value": "five years", "content": "Elias: five years", "authority_class": "canon", "version_number": 1},
            {**base, "memory_id": "derived", "fact_key": "b", "compact_value": "two years", "content": "Elias: two years", "authority_class": "derived", "version_number": 1},
        ])
        await memory_phase_b_service._label_conflicts(db, str(pid), "Elias", "absence_duration")
        authority = await db.atomic_memories.find_one({"memory_id": "authority"})
        derived = await db.atomic_memories.find_one({"memory_id": "derived"})
        assert authority["conflict_status"] == "authority_supported"
        assert derived["conflict_status"] == "conflicts_with_authority"
        indexed = {**derived, "source_type": "atomic_memory", "metadata": {**metadata_for_source("atomic_memory", derived), "conflict_status": derived["conflict_status"]}}
        assert retrieval_eligibility_policy.evaluate(indexed, RetrievalEligibilityContext(safe_for_writing=True, project_id=str(pid))).eligible is False
    finally:
        await _cleanup(db, pid); motor.close()


@pytest.mark.asyncio
async def test_phase_a_rebuild_recreates_atomic_index_without_provider(client):
    motor, db = _motor(); pid = ObjectId()
    try:
        await db.projects.insert_one({"_id": pid, "title": "Phase B"})
        await db.artifact_registry.insert_one({
            "project_id": pid, "artifact_id": "northglass", "item": "Northglass", "owner": "Ivo",
            "status": "active", "authority_status": "confirmed", "version_number": 1, "updated_at": datetime.utcnow(),
        })
        rebuilt = await memory_incremental_index_service.rebuild(db, str(pid))
        assert rebuilt["status"] == "READY"
        checkpoint = await db.memory_phase_b_checkpoints.find_one({"project_id": pid})
        assert checkpoint["provider_calls"] == 0
        assert checkpoint["atomic_records"] >= 1
        provider = NativeNovelForgeMemoryProvider(db)
        recall = await provider.recall(project_id=str(pid), query="Who owns Northglass?", top_k=8, retrieval_context={"safe_for_writing": True, "consumer": "test"})
        assert any("Ivo" in hit.content for hit in recall.hits)
        assert await db.memory_embeddings.count_documents({"project_id": pid, "source_type": "atomic_memory", "active": True}) >= 1
    finally:
        await _cleanup(db, pid); motor.close()


@pytest.mark.asyncio
async def test_new_owner_version_supersedes_current_atomic_but_keeps_history(client):
    motor, db = _motor(); pid = ObjectId()
    try:
        first = {"project_id": pid, "artifact_id": "northglass", "item": "Northglass", "owner": "Mara", "status": "confirmed", "version_number": 1, "valid_from_chapter": 3, "active": True}
        second = {**first, "owner": "Ivo", "version_number": 2, "valid_from_chapter": 8}
        await memory_phase_b_service.sync_owner(db, str(pid), "artifact", first)
        await memory_phase_b_service.sync_owner(db, str(pid), "artifact", second)
        old = await db.atomic_memories.find_one({"project_id": pid, "predicate": "owner", "compact_value": "Mara"})
        current = await db.atomic_memories.find_one({"project_id": pid, "predicate": "owner", "compact_value": "Ivo"})
        assert old["status"] == "historical" and old["valid_to_chapter"] == 7
        assert current["active"] is True and current.get("valid_to_chapter") is None
        assert old.get("conflict_status") is None
        old_indexed = {**old, "source_type": "atomic_memory", "metadata": metadata_for_source("atomic_memory", old)}
        assert retrieval_eligibility_policy.evaluate(old_indexed, RetrievalEligibilityContext(safe_for_writing=True, project_id=str(pid), as_of_chapter=5)).eligible is True
    finally:
        await _cleanup(db, pid); motor.close()
