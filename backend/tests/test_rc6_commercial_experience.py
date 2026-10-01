import time
from datetime import datetime

from bson import ObjectId
from pymongo import MongoClient

from app.core.config import settings as app_config
from app.services.narrative_analysis_engine import narrative_analysis_engine


def _db():
    return MongoClient(app_config.mongodb_url)[app_config.database_name]


def _project(client, title="RC6"):
    response = client.post("/api/projects", json={
        "title": f"{title} {time.time_ns()}",
        "premise": "A mapmaker discovers that roads remember everyone who vanished on them.",
        "idea_dump": "A quiet fantasy about memory, grief, and a road that should not exist.",
        "genre": "Fantasy",
        "tone": "Hopeful mystery",
        "themes": ["memory"],
    })
    assert response.status_code in {200, 201}, response.text
    return response.json()


def test_beginner_flow_reaches_first_scene_without_replacing_existing_services(client):
    project = _project(client, "Beginner Flow")
    endpoint = f"/api/projects/{project['id']}/beginner-flow"
    flow = client.get(endpoint)
    assert flow.status_code == 200, flow.text
    assert [item["step_id"] for item in flow.json()["steps"]] == [
        "story_idea", "main_character", "world", "conflict",
        "first_decision", "first_arc", "first_scene",
    ]

    values = {
        "story_idea": ("The Remembering Roads", "A mapmaker follows a road erased from every map."),
        "main_character": ("Mara Vale", "A patient mapmaker who fears forgetting her missing sister."),
        "world": ("The Folded Kingdom", "Roads store memories when travelers make promises."),
        "conflict": ("The vanishing road", "Mara must follow the road before it consumes her sister's last memory."),
        "first_decision": ("Trust the road", "Mara chooses to follow the road despite the guild's warning."),
        "first_arc": ("The Road Opens", "Mara finds the road, breaks guild law, and crosses its first threshold."),
        "first_scene": ("The impossible line", "Mara sees a new road draw itself across her map at midnight."),
    }
    for step_id, (title, details) in values.items():
        response = client.put(f"{endpoint}/{step_id}", json={
            "action": "save",
            "title": title,
            "details": details,
            "source_mode": "manual",
        })
        assert response.status_code == 200, response.text

    completed = client.get(endpoint).json()
    assert completed["completed_steps"] == completed["total_steps"] == 7
    assert completed["completion"] == 100
    pid = ObjectId(project["id"])
    db = _db()
    assert db.character_bibles.count_documents({"project_id": pid}) == 1
    assert db.world_bibles.count_documents({"project_id": pid}) == 1
    assert db.story_arcs.count_documents({"project_id": pid}) == 1
    assert db.scene_plans.count_documents({"project_id": pid}) == 1
    db.client.close()


def test_decision_change_undo_reopen_and_structured_context_supersession(client):
    project = _project(client, "Decision History")
    pid = ObjectId(project["id"])
    db = _db()
    question_id = db.questions.insert_one({
        "project_id": pid,
        "text": "Why did Mara's sister disappear?",
        "story_area": "mystery",
        "subject": "Mara's sister",
        "field": "disappearance_reason",
        "answered": True,
        "answer": "She was taken by the map guild.",
        "decision_version": 1,
        "decision_history": [{
            "version": 1,
            "answer": "She was taken by the map guild.",
            "action": "answered",
            "reason": "",
            "created_at": datetime.utcnow(),
        }],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }).inserted_id
    db.client.close()

    base = f"/api/projects/{project['id']}/decisions/{question_id}"
    preview = client.get(f"{base}/impact")
    assert preview.status_code == 200, preview.text
    assert preview.json()["impact_preview"]["risk"] in {"low", "medium", "high"}

    changed = client.put(base, json={
        "answer": "She entered the remembering road willingly.",
        "reason": "This gives her more agency.",
    })
    assert changed.status_code == 200, changed.text
    assert changed.json()["version"] == 2
    assert changed.json()["can_undo"] is True

    undone = client.post(f"{base}/undo", json={"reason": "Restore the earlier mystery."})
    assert undone.status_code == 200, undone.text
    assert undone.json()["current_answer"] == "She was taken by the map guild."
    assert undone.json()["version"] == 3

    reopened = client.post(f"{base}/reopen", json={"reason": "Decide after the midpoint."})
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["answered"] is False
    assert reopened.json()["can_reopen"] is False


def test_workspace_entry_bootstrap_and_project_library_are_actionable_and_paginated(client):
    project = _project(client, "Bootstrap")
    entry = client.post(f"/api/projects/{project['id']}/workspace-entries", json={
        "area": "theme",
        "title": "What memory costs",
        "details": "The story asks whether preserving every memory prevents people from healing.",
        "source_mode": "manual",
    })
    assert entry.status_code == 200, entry.text
    assert entry.json()["target"] == "themes"

    bootstrap = client.get(f"/api/projects/{project['id']}/workspace-bootstrap")
    assert bootstrap.status_code == 200, bootstrap.text
    payload = bootstrap.json()
    assert payload["version"] == "rc6-v1"
    assert {"project", "story_bible", "story_health", "completeness", "companion"} <= set(payload)

    db = _db()
    now = datetime.utcnow()
    db.projects.insert_many([
        {
            "title": f"Road Test {index:02}",
            "status": "draft",
            "genre": "Fantasy",
            "tone": "Quiet",
            "favorite": index == 0,
            "created_at": now,
            "updated_at": now,
        }
        for index in range(13)
    ])
    db.client.close()
    first = client.get("/api/project-library?status=active&search=Road%20Test&page=1&page_size=6")
    assert first.status_code == 200, first.text
    assert len(first.json()["items"]) == 6
    assert first.json()["has_next"] is True
    second = client.get("/api/project-library?status=active&search=Road%20Test&page=2&page_size=6")
    assert second.status_code == 200
    assert len(second.json()["items"]) == 6


def test_story_health_scores_each_semantic_issue_once():
    duplicated = [
        {
            "finding_id": "source-a",
            "semantic_issue_id": "canon:moon-color",
            "domain": "canon",
            "severity": "high",
        },
        {
            "finding_id": "source-b",
            "semantic_issue_id": "canon:moon-color",
            "domain": "canon",
            "severity": "high",
        },
    ]
    one = narrative_analysis_engine._scores([duplicated[0]])
    two = narrative_analysis_engine._scores(duplicated)
    assert two == one
