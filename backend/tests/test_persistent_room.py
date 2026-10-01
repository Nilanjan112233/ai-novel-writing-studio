import time
from bson import ObjectId
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.core.config import settings


def sync_db():
    return MongoClient(settings.mongodb_url)[settings.database_name]


def create_room_project(client: TestClient, title: str):
    response = client.post("/api/projects", json={
        "title": title,
        "idea_dump": "A large free-form idea dump about a haunted observatory and a loyal mentor.",
        "genre": "Fantasy",
        "tone": "Eerie",
    })
    assert response.status_code == 200
    return response.json()


def wait_for_terminal_run(client: TestClient, project_id: str):
    for _ in range(60):
        runs = client.get(f"/api/projects/{project_id}/runs").json()
        if runs and runs[0]["status"] in ("completed", "waiting_for_user", "failed"):
            return runs[0]
        time.sleep(0.25)
    raise AssertionError("workflow run did not finish")


def test_timeline_message_endpoints_and_project_sorting(client: TestClient):
    older = create_room_project(client, f"Older Room {time.time_ns()}")
    newer = create_room_project(client, f"Newer Room {time.time_ns()}")

    message = client.post(
        f"/api/projects/{older['id']}/messages",
        json={"content": "The mentor should be genuinely good."},
    )
    assert message.status_code == 200
    assert message.json()["role"] == "user"

    timeline = client.get(f"/api/projects/{older['id']}/timeline")
    assert timeline.status_code == 200
    assert timeline.json()[0]["content"] == "The mentor should be genuinely good."

    projects = client.get("/api/projects").json()
    ids = [project["id"] for project in projects]
    assert ids.index(older["id"]) < ids.index(newer["id"])


def test_discussion_cycle_persists_outputs_cycles_and_timeline(client: TestClient):
    project = create_room_project(client, f"Cycle Room {time.time_ns()}")
    project_id = project["id"]
    client.post(
        f"/api/projects/{project_id}/messages",
        json={"content": "Make the mentor a sincere ally, not a twist villain."},
    )

    cycle_response = client.post(f"/api/projects/{project_id}/cycle")
    assert cycle_response.status_code == 200
    run = wait_for_terminal_run(client, project_id)
    assert run["status"] in ("completed", "waiting_for_user")

    cycles = client.get(f"/api/projects/{project_id}/cycles").json()
    assert cycles
    assert cycles[-1]["status"] == "completed"
    assert cycles[-1]["trigger_message_ids"]

    outputs = client.get(f"/api/projects/{project_id}/outputs").json()
    assert len(outputs) >= 4
    assert all("cycle_number" in output["metadata"] for output in outputs)

    discussion = client.get(f"/api/projects/{project_id}/discussion").json()
    assert any(message["role"] == "agent" for message in discussion)


def test_delete_project_cascades_persistent_room_collections(client: TestClient):
    project = create_room_project(client, f"Delete Room {time.time_ns()}")
    project_id = project["id"]
    pid = ObjectId(project_id)
    db = sync_db()
    run_id = db.runs.insert_one({"project_id": pid, "status": "completed"}).inserted_id
    db.agent_outputs.insert_one({"project_id": pid, "run_id": run_id, "content": "x"})
    db.questions.insert_one({"project_id": pid, "text": "Q?", "answered": False})
    db.answers.insert_one({"project_id": pid, "answer": "A"})
    db.outlines.insert_one({"project_id": pid, "premise": "P"})
    db.characters.insert_one({"project_id": pid, "name": "N"})
    db.world_bibles.insert_one({"project_id": pid, "setting": "S"})
    db.timeline_messages.insert_one({"project_id": pid, "content": "M"})
    db.cycles.insert_one({"project_id": pid, "cycle_number": 1})
    db.character_bibles.insert_one({"project_id": pid, "name": "Mentor"})
    db.plot_threads.insert_one({"project_id": pid, "title": "Thread"})
    db.story_timelines.insert_one({"project_id": pid, "event_title": "Event"})
    db.theme_registry.insert_one({"project_id": pid, "themes": ["Mercy"]})
    db.foreshadow_registry.insert_one({"project_id": pid, "setup": "Setup"})
    db.scene_registry.insert_one({"project_id": pid, "title": "Scene"})
    db.relationship_graphs.insert_one({"project_id": pid, "character_a": "A", "character_b": "B"})
    db.continuity_reports.insert_one({"project_id": pid, "cycle_number": 1})
    db.scene_drafts.insert_one({"project_id": pid, "title": "Draft"})
    db.memory_embeddings.insert_one({"project_id": pid, "source_type": "test"})

    response = client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 200

    for collection in [
        "projects",
        "runs",
        "agent_outputs",
        "questions",
        "answers",
        "outlines",
        "characters",
        "world_bibles",
        "timeline_messages",
        "cycles",
        "character_bibles",
        "plot_threads",
        "story_timelines",
        "theme_registry",
        "foreshadow_registry",
        "scene_registry",
        "relationship_graphs",
        "continuity_reports",
        "scene_drafts",
        "memory_embeddings",
    ]:
        assert db[collection].count_documents({"project_id": pid}) == 0
    assert db.projects.count_documents({"_id": pid}) == 0
