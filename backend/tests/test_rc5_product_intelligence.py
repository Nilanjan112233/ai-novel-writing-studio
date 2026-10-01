import time
from datetime import datetime

from bson import ObjectId
from pymongo import MongoClient

from app.core.config import settings as app_config
from app.services.application_knowledge_service import application_knowledge_service


def _db():
    return MongoClient(app_config.mongodb_url)[app_config.database_name]


def _project(client, title="RC5 Product Intelligence"):
    response = client.post("/api/projects", json={
        "title": f"{title} {time.time_ns()}",
        "premise": "An archivist must reconcile a divided city's memories before dawn.",
        "genre": "Fantasy mystery",
        "tone": "Hopeful",
    })
    assert response.status_code in {200, 201}, response.text
    return response.json()


def test_application_knowledge_is_complete_and_separate_from_story_reasoning(client):
    project = _project(client, "Application Knowledge")
    project_id = project["id"]
    response = client.get(f"/api/projects/{project_id}/application-knowledge")
    assert response.status_code == 200, response.text
    catalog = response.json()
    assert len(catalog["surfaces"]) >= 30
    assert {"dashboard", "story-health", "canon-queue", "project-timeline", "explainability-timeline"} <= set(catalog["surfaces"])
    for surface in catalog["surfaces"].values():
        assert surface["purpose"] and surface["why_it_matters"]
        assert surface["what_to_do"] and surface["what_happens_next"]
        assert all(action["destination"] in catalog["surfaces"] for action in surface["actions"])

    answer = client.post(f"/api/projects/{project_id}/assistant", json={
        "query": "What does Arc Board do?", "mode": "story_coach", "active_surface": "dashboard",
    })
    assert answer.status_code == 200, answer.text
    data = answer.json()
    assert data["reasoning_layer"] == "application"
    assert data["generation_metadata"]["provider"] == "application_knowledge"
    assert data["generation_metadata"]["tokens_used"] == 0
    assert data["evidence"]["analysis_id"] is None
    assert data["navigation_actions"][0]["section"] == "arcs"
    assert any(action["section"] == "arc-development" for action in data["navigation_actions"])
    assert application_knowledge_service.classify("Summarize Character Alice") == "project"
    assert application_knowledge_service.classify("What is Character Intelligence?") == "application"
    assert application_knowledge_service.classify("Why is Story Health 82?") == "project"


def test_project_and_explainability_timelines_use_existing_project_evidence(client):
    project = _project(client, "Evolution Timeline")
    project_id = project["id"]
    pid = ObjectId(project_id)
    now = datetime.utcnow()
    db = _db()
    db.chapter_intelligence.insert_one({
        "project_id": pid, "intelligence_id": "chapter-1", "chapter_number": 1,
        "chapter_summary": "The archivist enters the city.", "active": True,
        "characters_present": ["Ilya"], "updated_at": now,
    })
    db.client.close()
    first = client.post(f"/api/projects/{project_id}/narrative-analysis", json={"force": True})
    assert first.status_code == 200, first.text

    db = _db()
    db.continuity_reports.insert_one({
        "project_id": pid, "report_id": "continuity-1", "result": "FAIL",
        "message": "The journey completes before it begins.", "evidence": ["Chapter 1"],
        "chapter_numbers": [1], "updated_at": datetime.utcnow(),
    })
    db.client.close()
    second = client.post(f"/api/projects/{project_id}/narrative-analysis", json={"force": True})
    assert second.status_code == 200, second.text

    timeline = client.get(f"/api/projects/{project_id}/project-timeline")
    assert timeline.status_code == 200, timeline.text
    assert timeline.json()["story_timeline_is_separate"] is True
    assert any(entry["action"] == "Project created" for entry in timeline.json()["entries"])

    explainability = client.get(f"/api/projects/{project_id}/explainability-timeline")
    assert explainability.status_code == 200, explainability.text
    changes = explainability.json()["changes"]
    assert changes
    assert all(item["what_happened"] and item["why_it_matters"] for item in changes)
    assert any(reason["destination"] == "story-health" for item in changes for reason in item["reasons"])


def test_companion_recommendations_have_stable_identity_and_lifecycle(client):
    project = _project(client, "Companion Lifecycle")
    project_id = project["id"]
    pid = ObjectId(project_id)
    first = client.get(f"/api/projects/{project_id}/workspace-companion")
    assert first.status_code == 200, first.text
    first_data = first.json()
    assert first_data["state"] in {"idle", "working", "celebrating", "notifying"}
    recommendation = next((item for item in first_data["messages"] if item["kind"] == "recommendation"), None)
    assert recommendation is not None
    assert recommendation["target"]
    assert recommendation["recommendation_key"].startswith("next:")

    dismissed = client.put(
        f"/api/projects/{project_id}/workspace-companion/messages/{recommendation['message_id']}",
        json={"dismissed": True},
    )
    assert dismissed.status_code == 200, dismissed.text
    assert dismissed.json()["state"] == "dismissed"

    second = client.get(f"/api/projects/{project_id}/workspace-companion")
    assert second.status_code == 200, second.text
    assert all(item["message_id"] != recommendation["message_id"] for item in second.json()["messages"])
    db = _db()
    assert db.workspace_companion_messages.count_documents({
        "project_id": pid, "recommendation_key": recommendation["recommendation_key"],
    }) == 1
    db.client.close()


def test_rc5_migration_indexes_and_cleanup(client):
    project = _project(client, "RC5 Migration")
    pid = ObjectId(project["id"])
    db = _db()
    settings = db.app_settings.find_one({"_id": "global_settings"})
    assert settings["migrations"]["rc5_version"] == 1
    assert "analysis_history_identity" in db.narrative_analysis_history.index_information()
    assert "companion_recommendation_identity" in db.workspace_companion_messages.index_information()
    db.narrative_analysis_history.insert_one({"project_id": pid, "analysis_id": "cleanup", "calculated_at": datetime.utcnow()})
    db.workspace_companion_state.insert_one({"project_id": pid, "state": "idle"})
    db.client.close()
    deleted = client.delete(f"/api/projects/{project['id']}")
    assert deleted.status_code == 200, deleted.text
    db = _db()
    assert db.narrative_analysis_history.count_documents({"project_id": pid}) == 0
    assert db.workspace_companion_state.count_documents({"project_id": pid}) == 0
    db.client.close()
