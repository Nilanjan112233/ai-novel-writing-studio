import time
from datetime import datetime, timedelta

from bson import ObjectId
from pymongo import MongoClient

from app.core.config import settings as app_config


def create_project(client, title="The Chronicles of Elysium"):
    response = client.post(
        "/api/projects",
        json={
            "title": title,
            "premise": "A guardian maps the memories of a world waking from divine sleep.",
            "idea_dump": "Each arc reveals only the knowledge needed for the next choice.",
            "genre": "Fantasy",
            "tone": "Mythic and intimate",
            "themes": ["Memory", "Responsibility"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def run_cycle(client, project_id):
    response = client.post(f"/api/projects/{project_id}/cycle")
    assert response.status_code == 200, response.text
    for _ in range(200):
        runs = client.get(f"/api/projects/{project_id}/runs").json()
        if runs and runs[0]["status"] in {"completed", "waiting_for_user", "failed"}:
            assert runs[0]["status"] != "failed"
            break
        time.sleep(0.05)
    return client.get(
        f"/api/projects/{project_id}/orchestration/latest"
    ).json()


def create_arc(client, project_id, title, status, order):
    response = client.post(
        f"/api/projects/{project_id}/arcs",
        json={
            "title": title,
            "purpose": f"Develop {title} without defining later arcs.",
            "goal": f"Complete the central choice of {title}.",
            "conflict": "The guardian's duty conflicts with a personal promise.",
            "stakes": "A community may lose its shared memory.",
            "approval_status": status,
            "chapter_range": [1 + ((order - 1) * 10), order * 10],
            "order": order,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def create_requirement(client, project_id, arc_id, title, status):
    response = client.post(
        f"/api/projects/{project_id}/readiness",
        json={
            "arc_id": arc_id,
            "category": "Arc Foundation",
            "title": title,
            "description": f"{title} must be settled for this arc.",
            "priority": "required",
            "status": status,
            "evidence": [f"Approved note for {title}"] if status == "approved" else [],
            "blocking": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_arc_scoped_readiness_allows_gradual_story_discovery(client):
    project_id = create_project(client)["id"]
    arc1 = create_arc(client, project_id, "Arc 1: The Waking Map", "approved", 1)
    arc2 = create_arc(client, project_id, "Arc 2: The Divided Archive", "discussed", 2)
    arc3 = create_arc(client, project_id, "Arc 3: Beyond the Veil", "draft", 3)

    for title in ["Protagonist", "Arc Goal", "Major Conflict"]:
        create_requirement(client, project_id, arc1["arc_id"], title, "approved")
    create_requirement(client, project_id, arc2["arc_id"], "Protagonist", "approved")
    create_requirement(client, project_id, arc2["arc_id"], "Arc Goal", "missing")

    arc1_report = client.get(
        f"/api/projects/{project_id}/readiness/report",
        params={"arc_id": arc1["arc_id"]},
    ).json()
    arc2_report = client.get(
        f"/api/projects/{project_id}/readiness/report",
        params={"arc_id": arc2["arc_id"]},
    ).json()
    arc3_report = client.get(
        f"/api/projects/{project_id}/readiness/report",
        params={"arc_id": arc3["arc_id"]},
    ).json()

    assert arc1_report["status"] == "READY"
    assert arc1_report["drafting_eligible"] is True
    assert arc2_report["status"] == "PARTIALLY_READY"
    assert arc2_report["drafting_eligible"] is False
    assert arc3_report["status"] == "NOT_READY"
    assert arc3_report["drafting_eligible"] is False

    blocked = client.post(
        f"/api/projects/{project_id}/draft-scenes",
        json={"arc_id": arc2["arc_id"]},
    )
    assert blocked.status_code == 409


def test_typed_ledgers_represent_unknown_future_and_hidden_reader_layer(client):
    project_id = create_project(client, "Elysium Ledgers")["id"]
    arc1 = create_arc(client, project_id, "Arc 1", "approved", 1)
    arc3 = create_arc(client, project_id, "Arc 3", "draft", 3)

    unknown = client.post(
        f"/api/projects/{project_id}/timeline-v2",
        json={
            "arc_id": arc3["arc_id"],
            "title": "Unknown future turning point",
            "summary": "",
            "importance": "major",
            "status": "planned",
            "certainty": "unknown",
            "dependencies": [],
            "chapter_range": [],
            "order": 30,
        },
    )
    assert unknown.status_code == 200, unknown.text
    assert unknown.json()["certainty"] == "unknown"

    progression = client.post(
        f"/api/projects/{project_id}/character-progressions",
        json={
            "arc_id": arc1["arc_id"],
            "character": "Elara",
            "current_state": "Protects memory through secrecy",
            "desired_state": "Shares truth with accountable allies",
            "skills": ["Memory cartography"],
            "powers": ["Echo sight"],
            "beliefs": ["Truth is dangerous"],
            "relationships": [{"character": "Soren", "state": "guarded trust"}],
            "maturity": "Learns to delegate",
            "trauma": ["The Archive fire"],
            "goals": ["Restore the Waking Map"],
        },
    )
    assert progression.status_code == 200, progression.text

    truth = client.post(
        f"/api/projects/{project_id}/knowledge",
        json={
            "arc_id": arc1["arc_id"],
            "title": "The compass contains a sleeping name",
            "content": "The compass is a vessel for the forgotten god Elys.",
            "knowledge_type": "WORLD_TRUTH",
            "known_by": [],
            "not_known_by": ["Elara", "Soren"],
            "learned_how": "Story-world truth",
            "is_false": False,
            "confidence": 1,
            "source": "canon",
            "reveal_target": "Arc 2",
        },
    )
    assert truth.status_code == 200, truth.text
    truth_id = truth.json()["entry_id"]

    reader_clue = client.post(
        f"/api/projects/{project_id}/knowledge",
        json={
            "arc_id": arc1["arc_id"],
            "title": "The compass glows near the old name",
            "content": "Readers see the compass glow when Elys is mentioned.",
            "knowledge_type": "READER_KNOWLEDGE",
            "known_by": ["Reader"],
            "not_known_by": ["Elara", "Soren"],
            "learned_how": "Visual clue in a planned scene",
            "is_false": False,
            "confidence": 0.75,
            "source": "foreshadow",
            "reveal_target": "Arc 2",
            "world_truth_entry_id": truth_id,
        },
    )
    assert reader_clue.status_code == 200, reader_clue.text
    clue = reader_clue.json()
    assert clue["known_by"] == ["Reader"]
    assert "Elara" in clue["not_known_by"]

    contradiction = client.post(
        f"/api/projects/{project_id}/knowledge",
        json={
            "title": "Impossible visibility",
            "content": "Elara both knows and does not know.",
            "knowledge_type": "CHARACTER_KNOWLEDGE",
            "known_by": ["Elara"],
            "not_known_by": ["Elara"],
        },
    )
    assert contradiction.status_code == 400

    foreshadow = client.post(
        f"/api/projects/{project_id}/foreshadowing-v2",
        json={
            "seed": "The compass glows and is ignored.",
            "arc_planted": arc1["arc_id"],
            "chapter_planted": 3,
            "payoff_target": "Elara learns who sleeps in the compass.",
            "payoff_arc_id": arc3["arc_id"],
            "status": "seeded",
            "timeline_entry_ids": [unknown.json()["entry_id"]],
        },
    )
    assert foreshadow.status_code == 200, foreshadow.text

    artifact = client.post(
        f"/api/projects/{project_id}/artifacts",
        json={
            "item": "The Elysian Compass",
            "owner": "Elara",
            "power": "Finds memories that still have living witnesses",
            "hidden_power": "Houses the name of Elys",
            "cost": "Erases one private memory per use",
            "limitations": ["Cannot reveal a memory without a witness"],
            "history": "Recovered from the Archive fire",
            "future_relevance": "Unlocks the Arc 3 threshold",
            "status": "active",
            "arc_ids": [arc1["arc_id"], arc3["arc_id"]],
            "character_ids": ["Elara"],
            "timeline_entry_ids": [unknown.json()["entry_id"]],
            "knowledge_entry_ids": [truth_id, clue["entry_id"]],
        },
    )
    assert artifact.status_code == 200, artifact.text


def test_phase_1b_changes_route_only_affected_agents(client):
    project_id = create_project(client, "Elysium Routing")["id"]
    run_cycle(client, project_id)
    arc = create_arc(client, project_id, "The First Threshold", "draft", 1)
    create_requirement(client, project_id, arc["arc_id"], "Arc Goal", "proposed")
    readiness_plan = run_cycle(client, project_id)
    assert "ReadinessAgent" in readiness_plan["selected_agents"]
    assert "WorldAgent" in readiness_plan["skipped_agents"]

    client.post(
        f"/api/projects/{project_id}/knowledge",
        json={
            "arc_id": arc["arc_id"],
            "title": "Reader-only clue",
            "content": "The reader sees a name reflected backward.",
            "knowledge_type": "READER_KNOWLEDGE",
            "known_by": ["Reader"],
            "not_known_by": ["Elara"],
            "confidence": 0.6,
        },
    )
    knowledge_plan = run_cycle(client, project_id)
    assert "KnowledgeAgent" in knowledge_plan["selected_agents"]
    assert "PowerSystemAgent" in knowledge_plan["skipped_agents"]
    assert len(knowledge_plan["selected_agents"]) < len(knowledge_plan["tasks"])


def test_agent_memory_is_bounded_and_compactable(client):
    project_id = create_project(client, "Elysium Memory")["id"]
    mongo = MongoClient(app_config.mongodb_url)
    collection = mongo[app_config.database_name].agent_memories
    pid = ObjectId(project_id)
    now = datetime.utcnow()
    collection.insert_many(
        [
            {
                "project_id": pid,
                "agent_name": "KnowledgeAgent",
                "memory_type": "recent",
                "source_type": "test",
                "source_id": str(index),
                "source_version": 1,
                "active": True,
                "content": f"Memory {index}",
                "content_hash": str(index),
                "importance": 50,
                "metadata": {"cycle_number": index},
                "created_at": now - timedelta(minutes=20 - index),
                "updated_at": now - timedelta(minutes=20 - index),
            }
            for index in range(16)
        ]
    )
    response = client.post(
        f"/api/projects/{project_id}/agent-memories/KnowledgeAgent/compact"
    )
    assert response.status_code == 200, response.text
    context = client.get(
        f"/api/projects/{project_id}/agent-memories",
        params={"agent_name": "KnowledgeAgent"},
    ).json()
    assert len(context["recent"]) <= 12
    assert 1 <= len(context["compressed"]) <= 6
    mongo.close()
