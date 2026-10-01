from pymongo import MongoClient

from app.core.config import settings


def _project(client, sample_project):
    response = client.post("/api/projects", json=sample_project)
    assert response.status_code == 200
    return response.json()["id"]


def test_all_candidate_categories_materialize_and_remain_governed(client, sample_project):
    project_id = _project(client, sample_project)
    mongo = MongoClient(settings.mongodb_url)
    try:
        db = mongo[settings.database_name]
        db.discovery_extractions.insert_one({
            "project_id": __import__("bson").ObjectId(project_id),
            "extraction_id": "projection-test",
            "source_draft_id": "draft-projection-test",
            "chapter_number": 3,
            "candidates": [
                {"type": "character", "description": "Mara is the cartographer protagonist."},
                {"type": "relationship", "description": "Mara and Elias are siblings."},
                {"type": "world_fact", "description": "Northglass changes its streets at night."},
                {"type": "mystery", "description": "Where did Elias go?"},
                {"type": "timeline_event", "description": "Elias disappeared five years ago."},
                {"type": "plot_thread", "description": "Mara searches for Elias."},
                {"type": "artifact", "description": "The brass compass points to lost roads."},
                {"type": "knowledge_change", "description": "Mara learns the river remembers names."},
                {"type": "arc", "description": "The search for Elias becomes impossible to abandon."},
                {"type": "author_intention", "description": "Keep the sibling mystery central through Chapter 10."},
            ],
        })
    finally:
        mongo.close()

    projected = client.post(f"/api/projects/{project_id}/story-knowledge/reproject")
    assert projected.status_code == 200
    candidates = client.get(f"/api/projects/{project_id}/story-knowledge/candidates").json()
    assert {item["type"] for item in candidates} == {
        "character", "relationship", "world_fact", "mystery", "timeline_event",
        "plot_thread", "artifact", "knowledge_change", "arc", "author_intention",
    }
    assert all(item["authority_status"] == "candidate" and item["candidate_status"] == "pending" for item in candidates)
    assert all(item.get("source_chapter") == 3 for item in candidates if item["type"] != "world_fact")

    rejected = next(item for item in candidates if item["type"] == "mystery")
    rejected_response = client.post(
        f"/api/projects/{project_id}/story-knowledge/candidates/{rejected['candidate_id']}/decision",
        json={"decision": "reject"},
    )
    assert rejected_response.status_code == 200
    remaining = client.get(f"/api/projects/{project_id}/story-knowledge/candidates").json()
    assert rejected["candidate_id"] not in {item["candidate_id"] for item in remaining}

    reconsidered = client.post(
        f"/api/projects/{project_id}/story-knowledge/candidates/{rejected['candidate_id']}/decision",
        json={"decision": "reconsider"},
    )
    assert reconsidered.status_code == 200
    reconsidered_candidates = client.get(f"/api/projects/{project_id}/story-knowledge/candidates").json()
    assert rejected["candidate_id"] in {item["candidate_id"] for item in reconsidered_candidates}

    confirmed = next(item for item in reconsidered_candidates if item["type"] == "character")
    confirmed_response = client.post(
        f"/api/projects/{project_id}/story-knowledge/candidates/{confirmed['candidate_id']}/decision",
        json={"decision": "confirm"},
    )
    assert confirmed_response.status_code == 200
    world_candidate = next(item for item in reconsidered_candidates if item["type"] == "world_fact")
    world_confirm_response = client.post(
        f"/api/projects/{project_id}/story-knowledge/candidates/{world_candidate['candidate_id']}/decision",
        json={"decision": "confirm"},
    )
    assert world_confirm_response.status_code == 200
    mongo = MongoClient(settings.mongodb_url)
    try:
        character = mongo[settings.database_name].character_bibles.find_one({"project_id": __import__("bson").ObjectId(project_id), "candidate_id": confirmed["candidate_id"]})
        assert character["authority_status"] == "confirmed"
        assert character["provenance"]["chapter_number"] == 3
        world = mongo[settings.database_name].world_bibles.find_one({"project_id": __import__("bson").ObjectId(project_id)})
        assert any(item.get("candidate_id") == world_candidate["candidate_id"] and item.get("authority_status") == "confirmed" for item in world.get("suggested_world_facts", []))
        assert world_candidate["text"] in world.get("world_rules", [])
    finally:
        mongo.close()


def test_confirming_same_candidate_is_idempotent(client, sample_project):
    project_id = _project(client, sample_project)
    mongo = MongoClient(settings.mongodb_url)
    try:
        mongo[settings.database_name].character_bibles.insert_one({
            "project_id": __import__("bson").ObjectId(project_id),
            "candidate_id": "idempotent-candidate",
            "name": "Mara",
            "authority_status": "candidate",
            "candidate_status": "pending",
            "provenance": {"source_chapter": 1},
        })
    finally:
        mongo.close()
    path = f"/api/projects/{project_id}/story-knowledge/candidates/idempotent-candidate/decision"
    assert client.post(path, json={"decision": "confirm"}).status_code == 200
    assert client.post(path, json={"decision": "confirm"}).status_code == 200
