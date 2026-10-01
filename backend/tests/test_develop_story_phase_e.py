"""Phase E role projections, safety boundaries, budgets, and handoffs."""
from __future__ import annotations

import json
from datetime import datetime

import pytest
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings as app_config
from app.services.develop_story_context_service import develop_story_context_service


def _state() -> dict:
    repeated = "Mara follows the Northglass river clues while protecting the Chapter 10 reveal. " * 80
    return {
        "cycle_number": 3,
        "new_messages": [{"role": "user", "content": "Strengthen Mara's mystery arc."}],
        "canon_facts": [{"canon_id": "c1", "fact": "Elias disappeared five years ago.", "approval_status": "approved"}],
        "decision_registry": [{"decision_id": "d1", "decision": "Reveal Elias may be alive around Chapter 10.", "status": "approved"}],
        "confirmed_story_studio_planning": [{"planning_id": "p1", "content": "Elias's disappearance is the central mystery.", "authority_status": "confirmed"}],
        "rejected_decisions": [{"decision_id": "r1", "content": "Elias is secretly the villain.", "status": "rejected"}],
        "arc_focus": {"target_arc_id": "arc-1", "development_status": "active"},
        "story_bible": {
            "story_vision": {"premise": "Mara searches Northglass."},
            "relationships": [
                {"relationship_id": "rel-1", "character_a": "Mara", "character_b": "Elias", "relationship": "siblings", "approval_status": "approved"},
                {"candidate_id": "bad", "character_a": "Mara", "character_b": "Lindon", "relationship": "lovers", "status": "candidate", "authority_status": "candidate"},
            ],
            "mysteries": [{"mystery_id": "m1", "question": "Where is Elias?", "reveal_target": "Chapter 10", "authority_status": "confirmed"}],
            "timeline": [
                {"entry_id": "t1", "summary": "Elias disappeared five years ago.", "approval_status": "approved"},
                {"entry_id": "t2", "summary": "Elias disappeared two years ago.", "status": "candidate", "authority_status": "candidate"},
            ],
            "characters": [{"character_id": "mara", "name": "Mara", "goal": "Find Elias", "approval_status": "approved"}],
            "story_intelligence": {"huge_repeated_analysis": repeated * 40},
            "approved_story_content": [repeated] * 12,
            "editorial": {"history": repeated * 5},
        },
        "chapter_memory": {"recent": [{"chapter": 2, "summary": repeated}]},
        "cycle_handoffs": [{
            "specialist": "MysteryAgent", "cycle_number": 3,
            "claims": ["The clue sequence remains bounded."], "recommendations": ["Escalate without revealing Elias."],
            "affected_entities": ["Mara", "Elias"], "constraints_preserved": ["Chapter 10 reveal"],
            "new_conflicts": [], "open_questions": [], "accepted_state": "pending", "evidence_refs": ["mystery:m1"],
        }],
    }


def _retrieval() -> list:
    return [
        {"logical_identity": f"memory:{index}", "content": f"Relevant Northglass evidence {index}", "authority_level": "derived"}
        for index in range(8)
    ]


def test_role_manifest_projects_only_relevant_safe_sections():
    state = _state()
    built = develop_story_context_service.build_packet(
        agent_name="MysteryAgent",
        project={"title": "Memory Fantasy", "genre": "fantasy"},
        state=state,
        retrieved_memory=_retrieval(),
        agent_memory={"core": state["canon_facts"], "recent": [], "important": [], "compressed": []},
    )
    context = built["context"]
    projection = context["role_specific_structured_context"]
    assert built["fallback_required"] is False
    assert "mysteries" in projection
    assert "timeline" in projection
    assert "story_intelligence" not in projection
    assert "approved_story_content" not in projection
    assert "editorial" not in projection
    serialized = json.dumps(context, default=str)
    assert "two years ago" not in serialized
    assert "lovers" not in serialized
    assert "five years ago" in serialized
    assert "Chapter 10" in serialized


def test_shared_authority_is_complete_and_not_duplicated_through_agent_core():
    state = _state()
    built = develop_story_context_service.build_packet(
        agent_name="RelationshipAgent",
        project={"title": "Memory Fantasy"},
        state=state,
        retrieved_memory=[],
        agent_memory={"core": state["canon_facts"] + state["decision_registry"], "recent": [], "important": [], "compressed": []},
    )
    attribution = built["attribution"]
    assert attribution["authority_complete"] is True
    assert attribution["authority_expected"] == attribution["authority_actual"]
    assert built["context"]["agent_workflow_memory"] == []
    serialized = json.dumps(built["context"], default=str)
    assert serialized.count("Elias disappeared five years ago") == 1


def test_role_packet_reduces_broad_legacy_context_by_more_than_half():
    state = _state()
    legacy = {
        "project": {"title": "Memory Fantasy"},
        "current_story_plan": state["story_bible"],
        "canon_facts": state["canon_facts"],
        "approved_decisions": state["decision_registry"],
        "confirmed_story_studio_planning": state["confirmed_story_studio_planning"],
        "agent_memory": {"core": state["canon_facts"]},
        "chapter_memory": state["chapter_memory"],
    }
    built = develop_story_context_service.build_packet(
        agent_name="ArcArchitectAgent",
        project={"title": "Memory Fantasy"},
        state=state,
        retrieved_memory=_retrieval(),
        agent_memory={"core": state["canon_facts"], "recent": [], "important": [], "compressed": []},
    )
    legacy_tokens = len(json.dumps(legacy, default=str)) // 4
    compact_tokens = built["attribution"]["final_context_tokens"]
    assert compact_tokens < legacy_tokens * 0.5
    assert built["attribution"]["authority_complete"] is True


def test_delta_handoffs_are_role_bounded_and_keep_evidence():
    handoff = develop_story_context_service.build_handoff(
        agent_name="MysteryAgent",
        cycle_number=3,
        payload={
            "summary": "Preserve the Chapter 10 boundary.",
            "recommendation": "Escalate the river clue first.",
            "concerns": ["Must preserve confirmed chronology."],
            "mysteries": [{"mystery_id": "m1", "title": "Elias disappearance"}],
        },
        counts={"mysteries": 1},
        contradiction_reports=[],
        proposal_id="proposal-1",
        run_id="run-1",
    )
    assert handoff["specialist"] == "MysteryAgent"
    assert handoff["accepted_state"] == "pending"
    assert "Elias disappearance" in handoff["affected_entities"]
    assert "artifact:mysteries" in handoff["evidence_refs"]
    assert "proposal:proposal-1" in handoff["evidence_refs"]
    assert len(json.dumps(handoff)) < 5000


@pytest.mark.asyncio
async def test_handoff_persistence_is_idempotent_and_resumable():
    motor = AsyncIOMotorClient(app_config.mongodb_url)
    db = motor[app_config.database_name]
    pid, run_id = ObjectId(), ObjectId()
    handoff = develop_story_context_service.build_handoff(
        agent_name="RelationshipAgent", cycle_number=2,
        payload={"summary": "Mara still distrusts Ivo.", "recommendation": "Preserve distance."},
        counts={"relationships": 1}, contradiction_reports=[], proposal_id="p1", run_id=str(run_id),
    )
    try:
        await develop_story_context_service.persist_handoff(db, str(pid), str(run_id), handoff)
        await develop_story_context_service.persist_handoff(db, str(pid), str(run_id), handoff)
        assert await db.develop_story_handoffs.count_documents({"project_id": pid, "run_id": run_id}) == 1
        loaded = await develop_story_context_service.load_handoffs(db, str(pid), str(run_id), 2)
        assert len(loaded) == 1
        assert loaded[0]["claims"] == ["Mara still distrusts Ivo."]
    finally:
        await db.develop_story_handoffs.delete_many({"project_id": pid})
        motor.close()


def test_budget_failure_falls_back_instead_of_dropping_authority():
    state = _state()
    state["canon_facts"] = [
        {"canon_id": f"c{index}", "fact": ("Binding canon fact " + str(index) + " ") * 300, "approval_status": "approved"}
        for index in range(60)
    ]
    built = develop_story_context_service.build_packet(
        agent_name="RelationshipAgent", project={"title": "Huge Canon"}, state=state,
        retrieved_memory=_retrieval(), agent_memory={"recent": [], "important": [], "compressed": [], "core": []},
    )
    assert built["fallback_required"] is True
    assert built["attribution"]["fallback_reason"] == "mandatory_role_context_exceeds_budget"
    assert built["attribution"]["authority_complete"] is True
