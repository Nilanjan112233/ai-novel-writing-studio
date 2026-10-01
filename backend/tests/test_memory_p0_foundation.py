"""Permanent P0 memory correctness and replay regression cases."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings as app_config
from app.services.draft_validation_service import draft_validation_service
from app.services.context_engine import context_engine
from app.services.memory_retrieval_policy import (
    RetrievalEligibilityContext,
    retrieval_eligibility_policy,
)
from app.services.memory_retrieval_service import (
    embed_text,
    find_logical_memory_duplicates,
    index_memory,
    index_project_memory,
    repair_logical_memory_duplicates,
    retrieve_relevant_context,
)


FIXTURE = Path(__file__).parent / "fixtures" / "memory_p0_cases.json"


def _motor():
    client = AsyncIOMotorClient(app_config.mongodb_url)
    return client, client[app_config.database_name]


def _embedding(
    project_id: ObjectId,
    source_type: str,
    source_id: str,
    content: str,
    *,
    version: int = 1,
    metadata: dict | None = None,
) -> dict:
    return {
        "project_id": project_id,
        "source_type": source_type,
        "source_id": source_id,
        "source_version": version,
        "active": True,
        "content_hash": f"fixture-{source_type}-{source_id}-{version}",
        "content": content,
        "embedding": embed_text(content),
        "metadata": metadata or {},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


def test_labelled_p0_corpus_is_complete():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    ids = {case["id"] for case in payload["cases"]}
    assert {
        "duplicate_chapter_intelligence", "elias_chronology", "pov_person_shift",
        "relationship_extraction_error", "rejected_brainstorming",
        "candidate_leakage", "superseded_state", "future_knowledge",
        "character_knowledge",
    } <= ids


def test_central_policy_rejects_unsafe_status_future_and_private_knowledge():
    base = {
        "project_id": "p1",
        "source_type": "knowledge",
        "active": True,
        "metadata": {"known_by": ["Ivo"], "valid_from_chapter": 8},
    }
    context = RetrievalEligibilityContext(
        safe_for_writing=True,
        project_id="p1",
        as_of_chapter=5,
        pov_character="Mara",
    )
    decision = retrieval_eligibility_policy.evaluate(base, context)
    assert decision.eligible is False
    assert "future_chapter" in decision.reasons
    assert "not_known_by_pov" in decision.reasons

    for field, value in (
        ("status", "rejected"),
        ("authority_status", "candidate"),
        ("approval_status", "reconsidered"),
    ):
        document = {"project_id": "p1", "source_type": "character", field: value}
        assert retrieval_eligibility_policy.evaluate(document, context).eligible is False


@pytest.mark.asyncio
async def test_logical_identity_is_idempotent_and_duplicate_aliases_collapse(client):
    motor, db = _motor()
    try:
        pid = ObjectId()
        project_id = str(pid)
        intelligence_oid = ObjectId()
        intelligence_id = "intel-logical-1"
        await db.chapter_intelligence.insert_one({
            "_id": intelligence_oid,
            "project_id": pid,
            "intelligence_id": intelligence_id,
            "version_number": 1,
            "chapter_number": 1,
            "chapter_summary": "Mara finds the Northglass ledger.",
        })
        await db.memory_embeddings.insert_many([
            _embedding(pid, "chapter_intelligence", str(intelligence_oid), "Mara finds the Northglass ledger."),
            _embedding(pid, "chapter_intelligence", intelligence_id, "Chapter 1: Mara finds the Northglass ledger."),
        ])

        duplicates = await find_logical_memory_duplicates(db, project_id)
        assert len(duplicates) == 1
        hits = await retrieve_relevant_context(
            db, project_id, "Mara Northglass ledger", top_k=10,
            refresh_index=False, safe_for_writing=True,
        )
        assert sum(hit["source_id"] == intelligence_id for hit in hits) == 1
        selected = next(hit for hit in hits if hit["source_id"] == intelligence_id)
        assert selected["metadata"]["duplicate_representations_collapsed"] == 1
        assert len(selected["metadata"]["evidence_pointers"]) == 2

        repair = await repair_logical_memory_duplicates(db, project_id, dry_run=False)
        assert repair["authority_records_deleted"] == 0
        assert await db.chapter_intelligence.count_documents({"_id": intelligence_oid}) == 1
        assert await find_logical_memory_duplicates(db, project_id) == []

        for _ in range(2):
            await index_memory(
                db,
                project_id=project_id,
                source_type="canon",
                source_id="canon-1",
                source_version=3,
                content="The Northglass river remembers names.",
                metadata={"logical_source_id": "canon-1", "owner_source_version": 3},
            )
        assert await db.memory_embeddings.count_documents({
            "project_id": pid,
            "source_type": "canon",
            "source_id": "canon-1",
            "source_version": 3,
            "active": True,
        }) == 1

        await index_memory(
            db, project_id=project_id, source_type="artifact",
            source_id="bounded-owner", source_version=1,
            content="Northglass belongs to Mara.",
            metadata={
                "logical_source_id": "bounded-owner", "owner_source_version": 1,
                "valid_from_chapter": 1, "valid_to_chapter": 7,
            },
        )
        await index_memory(
            db, project_id=project_id, source_type="artifact",
            source_id="bounded-owner", source_version=2,
            content="Northglass belongs to Ivo.",
            metadata={
                "logical_source_id": "bounded-owner", "owner_source_version": 2,
                "valid_from_chapter": 8,
            },
        )
        assert await db.memory_embeddings.count_documents({
            "project_id": pid, "source_type": "artifact",
            "source_id": "bounded-owner", "active": True,
        }) == 2
    finally:
        await db.memory_embeddings.delete_many({"project_id": pid})
        await db.chapter_intelligence.delete_many({"project_id": pid})
        motor.close()


@pytest.mark.asyncio
async def test_safe_retrieval_filters_leaks_and_respects_as_of_state(client):
    motor, db = _motor()
    try:
        pid = ObjectId()
        project_id = str(pid)
        documents = [
            _embedding(pid, "timeline", "rejected-chat", "Maybe Elias is secretly the villain.", metadata={"status": "rejected"}),
            _embedding(pid, "character", "candidate-1", "Candidate: Elias is secretly the villain.", metadata={"authority_status": "candidate"}),
            _embedding(pid, "knowledge", "future-1", "Elias is alive in the eastern tower.", metadata={"valid_from_chapter": 8, "known_by": ["Ivo"]}),
            _embedding(pid, "artifact", "northglass", "Northglass belongs to Mara.", version=1, metadata={"logical_source_id": "northglass", "owner_source_version": 1, "authority_status": "approved", "valid_from_chapter": 3, "valid_to_chapter": 7}),
            _embedding(pid, "artifact", "northglass", "Northglass belongs to Ivo.", version=2, metadata={"logical_source_id": "northglass", "owner_source_version": 2, "authority_status": "approved", "valid_from_chapter": 8}),
        ]
        await db.memory_embeddings.insert_many(documents)

        early = await retrieve_relevant_context(
            db, project_id, "Elias Northglass owner", top_k=20,
            refresh_index=False, safe_for_writing=True,
            as_of_chapter=5, pov_character="Mara", consumer="discovery_writer",
        )
        early_content = " ".join(hit["content"] for hit in early)
        assert "belongs to Mara" in early_content
        assert "belongs to Ivo" not in early_content
        assert "secretly the villain" not in early_content
        assert "eastern tower" not in early_content

        late = await retrieve_relevant_context(
            db, project_id, "Northglass owner", top_k=20,
            refresh_index=False, safe_for_writing=True,
            as_of_chapter=10, consumer="discovery_writer",
        )
        late_content = " ".join(hit["content"] for hit in late)
        assert "belongs to Ivo" in late_content
        assert "belongs to Mara" not in late_content
    finally:
        await db.memory_embeddings.delete_many({"project_id": pid})
        motor.close()


@pytest.mark.asyncio
async def test_safe_discovery_packet_has_no_raw_chat_or_candidate_bypass(client, monkeypatch):
    motor, db = _motor()
    try:
        pid = ObjectId()
        project_id = str(pid)
        await db.projects.insert_one({"_id": pid, "title": "Safe packet fixture"})
        await db.timeline_messages.insert_one({
            "project_id": pid,
            "role": "user",
            "content": "Maybe Elias is secretly the villain.",
            "status": "rejected",
            "created_at": datetime.utcnow(),
        })
        await db.character_bibles.insert_many([
            {
                "project_id": pid,
                "character_id": "candidate-elias",
                "name": "Villain Elias",
                "description": "Candidate villain concept.",
                "authority_status": "candidate",
            },
            {
                "project_id": pid,
                "character_id": "confirmed-mara",
                "name": "Mara",
                "description": "Confirmed protagonist.",
                "authority_status": "confirmed",
            },
        ])
        async def native_config(_db, runtime=True):
            return {"mode": "native"}

        monkeypatch.setattr(
            "app.services.memory_provider.memory_provider_service.config",
            native_config,
        )
        packet = await context_engine.build_context_packet(
            db,
            project_id=project_id,
            agent_name="DiscoveryWriterAgent",
            task="Continue Mara's search.",
            cycle_number=0,
            current_chapter=1,
            safe_for_writing=True,
            include_conversation_history=False,
            persist=False,
        )
        serialized = json.dumps(packet.model_dump(), default=str)
        assert "secretly the villain" not in serialized
        assert "Candidate villain concept" not in serialized
        assert "Confirmed protagonist" in serialized
    finally:
        for collection in (
            "projects", "timeline_messages", "character_bibles",
            "memory_embeddings", "memory_provider_events",
            "memory_provider_comparisons",
        ):
            await db[collection].delete_many({"project_id": pid})
        await db.projects.delete_many({"_id": pid})
        motor.close()


@pytest.mark.asyncio
async def test_retrieval_and_refresh_do_not_silently_truncate_at_2000_or_1000(client):
    motor, db = _motor()
    try:
        pid = ObjectId()
        project_id = str(pid)
        embeddings = [
            _embedding(pid, "plot_thread", f"filler-{index}", f"ordinary filler thread {index}")
            for index in range(2004)
        ]
        embeddings.append(
            _embedding(pid, "plot_thread", "rare-last", "Dormant callback Zephyrglass-500 awakens.")
        )
        await db.memory_embeddings.insert_many(embeddings)
        hits = await retrieve_relevant_context(
            db, project_id, "Zephyrglass-500", top_k=3,
            refresh_index=False, safe_for_writing=True,
        )
        assert any(hit["source_id"] == "rare-last" for hit in hits)

        owners = [{
            "project_id": pid,
            "thread_id": f"owner-{index}",
            "title": f"Thread {index}",
            "description": "Controlled refresh fixture",
            "status": "open",
            "authority_status": "approved",
        } for index in range(1005)]
        await db.plot_threads.insert_many(owners)
        stats = await index_project_memory(db, project_id)
        assert stats["indexed"] >= 1005
        assert await db.memory_embeddings.count_documents({
            "project_id": pid,
            "source_type": "plot_thread",
            "source_id": {"$regex": "^owner-"},
            "active": True,
        }) == 1005
    finally:
        await db.memory_embeddings.delete_many({"project_id": pid})
        await db.plot_threads.delete_many({"project_id": pid})
        motor.close()


@pytest.mark.asyncio
async def test_discovery_continuity_detects_pov_chronology_relationship_ownership_and_knowledge(client):
    motor, db = _motor()
    try:
        pid = ObjectId()
        project_id = str(pid)
        await db.chapter_drafts.insert_one({
            "project_id": pid,
            "draft_id": "approved-chapter-1",
            "workflow_mode": "discovery",
            "chapter_number": 1,
            "version_number": 1,
            "status": "approved",
            "active": True,
            "generated_text": "She crossed the room. Mara watched him leave. She held the ledger while he closed the door.",
        })
        await db.timeline_entries.insert_one({
            "project_id": pid,
            "entry_id": "elias-time",
            "title": "Elias disappeared five years ago.",
            "status": "approved",
            "authority_status": "confirmed",
        })
        await db.relationship_graphs.insert_one({
            "project_id": pid,
            "relationship_id": "mara-lindon",
            "character_a": "Mara",
            "character_b": "Lindon",
            "relationship": "Mara and Lindon are not siblings.",
            "status": "active",
            "authority_status": "confirmed",
        })
        await db.artifact_registry.insert_one({
            "project_id": pid,
            "artifact_id": "northglass",
            "item": "Northglass",
            "owner": "Mara",
            "status": "active",
            "authority_status": "confirmed",
            "valid_from_chapter": 1,
        })
        await db.knowledge_entries.insert_one({
            "project_id": pid,
            "entry_id": "elias-alive",
            "title": "Elias alive",
            "content": "Elias is alive in the eastern tower.",
            "known_by": ["Ivo"],
            "not_known_by": ["Mara"],
            "status": "active",
            "authority_status": "confirmed",
        })
        await db.canon_registry.insert_one({
            "project_id": pid,
            "canon_id": "river-state",
            "fact": "The river is not dry.",
            "active": True,
        })

        report = await draft_validation_service.validate_chapter_draft(
            db,
            project_id,
            {
                "workflow_mode": "discovery",
                "draft_id": "bad-chapter-2",
                "chapter_number": 2,
                "version_number": 1,
                "generated_text": (
                    "I returned to Northglass two years ago. I carried the ledger. "
                    "I told Lindon that Mara was his brother. Ivo holds Northglass. "
                    "I knew Elias was alive in the eastern tower. The river is dry."
                ),
                "discovery_metadata": {"pov_character": "Mara", "instruction": "Continue the chapter."},
            },
            persist=False,
        )
        categories = {finding["category"] for finding in report["continuity_findings"]}
        assert report["result"] == "FAIL"
        assert {
            "pov_person_shift", "chronology_contradiction",
            "relationship_contradiction", "ownership_state_contradiction",
            "character_knowledge_leakage", "authority_direct_conflict",
        } <= categories
    finally:
        for collection in (
            "chapter_drafts", "timeline_entries", "relationship_graphs",
            "artifact_registry", "knowledge_entries", "canon_registry",
        ):
            await db[collection].delete_many({"project_id": pid})
        motor.close()


@pytest.mark.asyncio
async def test_explicitly_planned_pov_change_is_not_rejected(client):
    motor, db = _motor()
    try:
        pid = ObjectId()
        project_id = str(pid)
        await db.chapter_drafts.insert_one({
            "project_id": pid,
            "draft_id": "approved-third-person",
            "workflow_mode": "discovery",
            "chapter_number": 1,
            "version_number": 1,
            "status": "approved",
            "active": True,
            "generated_text": "She crossed the room. Mara watched him leave. She held the ledger while he waited.",
        })
        report = await draft_validation_service.validate_chapter_draft(
            db,
            project_id,
            {
                "workflow_mode": "discovery",
                "draft_id": "planned-first-person",
                "chapter_number": 2,
                "generated_text": "I cross the room. I watch him leave. I hold the ledger and I wait.",
                "discovery_metadata": {
                    "pov_character": "Mara",
                    "pov_person": "first person",
                    "intentional_pov_change": True,
                    "instruction": "Switch POV to first person.",
                },
            },
            persist=False,
        )
        assert "pov_person_shift" not in {
            finding["category"] for finding in report["continuity_findings"]
        }
    finally:
        await db.chapter_drafts.delete_many({"project_id": pid})
        motor.close()
