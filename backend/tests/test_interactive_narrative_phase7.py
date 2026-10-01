import time
from datetime import datetime

from bson import ObjectId
from pymongo import MongoClient

from app.core.config import settings as app_config


def _db():
    return MongoClient(app_config.mongodb_url)[app_config.database_name]


def _project(client, title="Interactive Narrative"):
    response = client.post(
        "/api/projects",
        json={
            "title": f"{title} {time.time_ns()}",
            "premise": "An archivist must decide which version of history deserves to survive.",
            "genre": "Literary fantasy",
            "tone": "Intimate and uncertain",
        },
    )
    assert response.status_code in {200, 201}, response.text
    return response.json()


def _seed_intelligence(project_id: str):
    db = _db()
    pid = ObjectId(project_id)
    now = datetime.utcnow()
    db.character_bibles.insert_many(
        [
            {
                "project_id": pid,
                "name": "Mara Venn",
                "role": "archivist",
                "personality": ["observant", "defensive"],
                "motivations": ["protect the dockworkers' pact"],
                "beliefs": ["easy consensus hides a cost"],
                "emotional_state": "wary",
                "dialogue_style": "precise, with strategic omissions",
                "vocabulary": ["record", "oath", "witness"],
                "internal_conflicts": ["truth versus mercy"],
                "current_status": "dead",
                "death_chapter": 3,
                "updated_at": now,
            },
            {
                "project_id": pid,
                "name": "Soren Vale",
                "role": "bell keeper",
                "current_status": "active",
                "updated_at": now,
            },
        ]
    )
    db.chapter_intelligence.insert_many(
        [
            {
                "project_id": pid,
                "intelligence_id": f"chapter-intelligence-{number}",
                "chapter_plan_id": f"chapter-plan-{number}",
                "chapter_draft_id": f"chapter-draft-{number}",
                "chapter_number": number,
                "title": f"Chapter {number}",
                "chapter_summary": (
                    "Mara hears the bell distort an oath."
                    if number <= 3
                    else "Soren discovers that the council caused Mara's death."
                ),
                "important_events": [f"Event {number}"],
                "characters_present": ["Mara Venn"] if number <= 3 else ["Soren Vale"],
                "future_obligations": ["Return the cracked seal"] if number == 1 else [],
                "mysteries_resolved": [],
                "foreshadowing_resolved": [],
                "word_count": 1600,
                "active": True,
                "updated_at": now,
            }
            for number in range(1, 9)
        ]
    )
    db.timeline_entries.insert_many(
        [
            {
                "project_id": pid,
                "entry_id": f"timeline-{number}",
                "title": f"Timeline event {number}",
                "chapter_number": number,
                "order": number,
                "updated_at": now,
            }
            for number in range(1, 9)
        ]
    )
    db.relationship_graphs.insert_one(
        {
            "project_id": pid,
            "relationship_id": "mara-soren",
            "character_a": "Mara Venn",
            "character_b": "Soren Vale",
            "relationship_type": "allies",
            "initial_status": "guarded trust",
            "status": "grief and regret",
            "updated_chapter": 7,
            "updated_at": now,
        }
    )
    db.knowledge_entries.insert_many(
        [
            {
                "project_id": pid,
                "entry_id": "known-early",
                "title": "The bell erases agreement",
                "content": "Mara learned the bell alters collective memory.",
                "knowledge_type": "CHARACTER_KNOWLEDGE",
                "known_by": ["Mara Venn"],
                "learned_chapter": 2,
            },
            {
                "project_id": pid,
                "entry_id": "known-late",
                "title": "The council caused Mara's death",
                "content": "This is learned after Mara dies.",
                "knowledge_type": "CHARACTER_KNOWLEDGE",
                "known_by": ["Mara Venn"],
                "learned_chapter": 7,
            },
        ]
    )
    db.power_progressions.insert_one(
        {
            "project_id": pid,
            "progression_id": "bell-memory",
            "name": "Bell Memory",
            "character": "Mara Venn",
            "limitations": ["cannot restore consent"],
            "updated_at": now,
        }
    )
    db.mystery_registry.insert_one(
        {
            "project_id": pid,
            "mystery_id": "bell-origin",
            "question": "Who taught the bell to erase agreement?",
            "status": "open",
            "introduced_chapter": 1,
            "updated_at": now,
        }
    )
    db.client.close()


def _analyze(client, project_id: str):
    response = client.post(
        f"/api/projects/{project_id}/narrative-analysis", json={"force": True}
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_live_knowledge_graph_explainability_and_workspace_intelligence(client):
    project = _project(client)
    _seed_intelligence(project["id"])
    analysis = _analyze(client, project["id"])

    graph_response = client.get(f"/api/projects/{project['id']}/knowledge-graph")
    assert graph_response.status_code == 200, graph_response.text
    graph = graph_response.json()
    assert graph["analysis_id"] == analysis["snapshot"]["analysis_id"]
    assert graph["source"] == "narrative_analysis_engine"
    assert {"character", "timeline", "power", "mystery"} <= {
        node["kind"] for node in graph["nodes"]
    }
    mara = next(node for node in graph["nodes"] if node["label"] == "Mara Venn")
    detail = client.get(
        f"/api/projects/{project['id']}/knowledge-graph/nodes/{mara['node_id']}"
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["analysis_id"] == graph["analysis_id"]
    assert "connected_entities" in detail.json()

    finding = analysis["findings"][0]
    explanation = client.get(
        f"/api/projects/{project['id']}/narrative-findings/{finding['finding_id']}/explanation"
    )
    assert explanation.status_code == 200, explanation.text
    explained = explanation.json()
    assert explained["why"]
    assert explained["evidence"]
    assert explained["source"] == "narrative_analysis_engine"

    contextual = client.post(
        f"/api/projects/{project['id']}/workspace-intelligence",
        json={"surface": "chapter", "chapter_number": 1},
    )
    assert contextual.status_code == 200, contextual.text
    assert contextual.json()["analysis_id"] == graph["analysis_id"]
    assert contextual.json()["cache_reused"] is True
    assert contextual.json()["recommendations"]


def test_project_assistant_modes_navigation_and_grounded_history(client):
    project = _project(client, "Assistant")
    _seed_intelligence(project["id"])
    analysis = _analyze(client, project["id"])

    modes = client.get(f"/api/projects/{project['id']}/interactive/modes")
    assert modes.status_code == 200
    assert {item["id"] for item in modes.json()} >= {
        "story_coach",
        "developmental_editor",
        "character_interviewer",
        "continuity_expert",
        "worldbuilding_consultant",
        "dialogue_coach",
    }
    answer = client.post(
        f"/api/projects/{project['id']}/assistant",
        json={
            "query": "Open Chapter 12 and show canon conflicts. Why is Story Health lower?",
            "mode": "continuity_expert",
        },
    )
    assert answer.status_code == 200, answer.text
    payload = answer.json()
    assert payload["answer"]
    assert any(item.get("chapter_number") == 12 for item in payload["navigation_actions"])
    assert payload["evidence"]["analysis_id"] == analysis["snapshot"]["analysis_id"]
    assert payload["generation_metadata"]["provider"] == "mock"

    history = client.get(f"/api/projects/{project['id']}/assistant/history").json()
    assert history[-1]["message_id"] == payload["message_id"]
    invalid = client.post(
        f"/api/projects/{project['id']}/assistant",
        json={"query": "Help", "mode": "invent_unrelated_analysis"},
    )
    assert invalid.status_code == 409


def test_character_conversation_enforces_timeline_and_updates_story_bible(client):
    project = _project(client, "Character Conversation")
    _seed_intelligence(project["id"])
    _analyze(client, project["id"])

    first = client.post(
        f"/api/projects/{project['id']}/character-conversations",
        json={
            "character_name": "Mara Venn",
            "message": "What do you believe happened to the founding oath?",
            "chapter_number": 8,
        },
    )
    assert first.status_code == 200, first.text
    turn = first.json()
    assert turn["awareness_boundary"] == {
        "requested_chapter": 8,
        "effective_chapter": 3,
        "death_boundary_applied": True,
        "death_chapter": 3,
    }
    assert max(turn["evidence"]["chapter_numbers"]) == 3
    assert "known-early" in turn["evidence"]["knowledge_entry_ids"]
    assert "known-late" not in turn["evidence"]["knowledge_entry_ids"]

    second = client.post(
        f"/api/projects/{project['id']}/character-conversations",
        json={
            "character_name": "Mara Venn",
            "message": "Remember what you promised me.",
            "chapter_number": 3,
            "conversation_id": turn["conversation_id"],
        },
    )
    assert second.status_code == 200, second.text
    history = client.get(
        f"/api/projects/{project['id']}/character-conversations/Mara%20Venn"
    ).json()
    assert len(history) == 2
    assert {item["conversation_id"] for item in history} == {turn["conversation_id"]}

    bible = client.get(f"/api/projects/{project['id']}/story-bible").json()
    interactive = bible["sections"]["interactive_intelligence"]
    assert len(interactive["character_conversations"]) == 2
    assert len(interactive["character_memories"]) == 2
    assert interactive["source_policy"] == "narrative_analysis_grounded_and_canon_governed"


def test_canon_proposal_requires_review_then_refreshes_canon_graph_and_bible(client):
    project = _project(client, "Canon Proposal")
    _seed_intelligence(project["id"])
    _analyze(client, project["id"])

    unsupported = client.post(
        f"/api/projects/{project['id']}/canon/proposals",
        json={
            "canon_type": "unregistered_type",
            "subject": "Cracked seal",
            "field": "material",
            "value": "bell bronze",
        },
    )
    assert unsupported.status_code == 409

    created = client.post(
        f"/api/projects/{project['id']}/canon/proposals",
        json={
            "canon_type": "artifact",
            "subject": "Cracked seal",
            "field": "material",
            "value": "bell bronze",
            "confidence": 0.88,
            "evidence": ["Chapter 1 introduces the cracked seal."],
            "affected_chapters": [1],
        },
    )
    assert created.status_code == 200, created.text
    proposal = created.json()
    assert proposal["status"] == "pending"
    db = _db()
    assert db.canon_registry.count_documents(
        {"project_id": ObjectId(project["id"]), "subject": "Cracked seal"}
    ) == 0
    db.client.close()

    queue = client.get(
        f"/api/projects/{project['id']}/canon/proposals?status=pending"
    ).json()
    assert queue[0]["proposal_id"] == proposal["proposal_id"]
    approved = client.put(
        f"/api/projects/{project['id']}/canon/proposals/{proposal['proposal_id']}",
        json={
            "decision": "approved",
            "note": "Supported by the approved chapter.",
            "confirm_high_impact": True,
        },
    )
    assert approved.status_code == 200, approved.text
    result = approved.json()
    assert result["status"] == "approved"
    assert result["canon_record"]["source_collection"] == "canon_proposals"
    assert result["story_bible_version"]

    graph = client.get(f"/api/projects/{project['id']}/knowledge-graph").json()
    assert any(
        node["kind"] == "canon" and node["payload"].get("subject") == "Cracked seal"
        for node in graph["nodes"]
    )
    bible = client.get(f"/api/projects/{project['id']}/story-bible").json()
    assert any(
        item["proposal_id"] == proposal["proposal_id"]
        and item["status"] == "approved"
        for item in bible["sections"]["interactive_intelligence"]["canon_proposals"]
    )
    audit = client.get(f"/api/projects/{project['id']}/audit")
    assert audit.status_code == 200, audit.text
    assert audit.json()["status"] == "pass", audit.json()["findings"]
    assert audit.json()["collection_counts"]["canon_proposals"] == 1
    deleted = client.delete(f"/api/projects/{project['id']}")
    assert deleted.status_code == 200, deleted.text
    db = _db()
    pid = ObjectId(project["id"])
    for collection in (
        "narrative_nodes",
        "narrative_edges",
        "narrative_findings",
        "narrative_analysis_snapshots",
        "canon_proposals",
        "change_impacts",
        "story_bibles",
    ):
        assert db[collection].count_documents({"project_id": pid}) == 0
    db.client.close()


def test_phase7_migration_indexes_are_installed(client):
    _project(client, "Migration")
    db = _db()
    settings = db.app_settings.find_one({"_id": "global_settings"})
    assert settings["migrations"]["phase_7_version"] == 1
    assert "narrative_conversation_turn_identity" in db.narrative_conversations.index_information()
    assert "canon_proposal_identity" in db.canon_proposals.index_information()
    db.client.close()
