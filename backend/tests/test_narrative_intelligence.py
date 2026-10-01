import time
import asyncio
from bson import ObjectId
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.api.workflow import stream_project_events


def create_project(client: TestClient):
    response = client.post("/api/projects", json={
        "title": f"Narrative Intelligence {time.time_ns()}",
        "idea_dump": "A prince hears dead gods. His mentor should be genuinely good and tragic. Mercy is a core theme.",
        "genre": "Fantasy",
        "tone": "Mythic",
    })
    assert response.status_code == 200
    return response.json()["id"]


def wait_for_run(client: TestClient, project_id: str):
    for _ in range(80):
        runs = client.get(f"/api/projects/{project_id}/runs").json()
        if runs and runs[0]["status"] in ("completed", "waiting_for_user", "failed"):
            return runs[0]
        time.sleep(0.25)
    raise AssertionError("run did not finish")


def test_narrative_artifacts_are_created_by_cycle(client: TestClient):
    project_id = create_project(client)
    response = client.post(f"/api/projects/{project_id}/cycle")
    assert response.status_code == 200
    run = wait_for_run(client, project_id)
    assert run["status"] in ("completed", "waiting_for_user")

    threads = client.get(f"/api/projects/{project_id}/plot-threads").json()
    assert any("Mentor" in thread["title"] for thread in threads)

    timeline = client.get(f"/api/projects/{project_id}/story-timeline").json()
    bible = client.get(f"/api/projects/{project_id}/story-bible").json()
    assert timeline
    assert bible["sections"]["ai_insights"]["consistency_score"] == 82
    plan = client.get(
        f"/api/projects/{project_id}/orchestration/latest"
    ).json()
    assert len(plan["selected_agents"]) < 12
    assert "CharacterJourneyAgent" in plan["skipped_agents"]
    assert "WorldAgent" in plan["skipped_agents"]
    assert "No character-related changes detected" in plan["selection_reasons"]["CharacterJourneyAgent"]


def test_memory_retrieval_and_dynamic_routing(client: TestClient):
    project_id = create_project(client)
    client.post(
        f"/api/projects/{project_id}/messages",
        json={"content": "The mentor should be more tragic and emotionally central."},
    )
    client.post(f"/api/projects/{project_id}/cycle")
    wait_for_run(client, project_id)

    memory = client.get(f"/api/projects/{project_id}/memory/search", params={"q": "tragic mentor mercy"}).json()
    assert memory
    assert memory[0]["score"] >= 0

    cycles = client.get(f"/api/projects/{project_id}/cycles").json()
    assert cycles
    assert "CharacterJourneyAgent" in cycles[-1]["agents_run"]
    assert "RelationshipAgent" in cycles[-1]["agents_run"]
    assert "WorldAgent" not in cycles[-1]["agents_run"]
    assert len(cycles[-1]["agents_run"]) < 12


def test_scene_planning_requires_arc_maturity_and_preserves_relationships(
    client: TestClient,
):
    project_id = create_project(client)
    client.put(
        f"/api/projects/{project_id}",
        json={"character_notes": "The prince and mentor begin with damaged trust."},
    )
    client.post(f"/api/projects/{project_id}/cycle")
    wait_for_run(client, project_id)

    arc_response = client.post(
        f"/api/projects/{project_id}/arcs",
        json={
            "title": "The First Voice",
            "goal": "Resolve the first divine warning.",
            "conflict": "The court rejects the warning.",
            "stakes": "The city remains exposed.",
            "approval_status": "approved",
            "chapter_range": [1, 8],
            "order": 1,
        },
    )
    assert arc_response.status_code == 200
    arc_id = arc_response.json()["arc_id"]
    for title in ["Protagonist", "Arc Goal", "Major Conflict"]:
        readiness = client.post(
            f"/api/projects/{project_id}/readiness",
            json={
                "arc_id": arc_id,
                "category": "Arc Foundation",
                "title": title,
                "priority": "required",
                "status": "approved",
                "evidence": [title],
                "blocking": True,
            },
        )
        assert readiness.status_code == 200

    draft = client.post(
        f"/api/projects/{project_id}/draft-scenes",
        json={"arc_id": arc_id},
    )
    assert draft.status_code == 409
    assert "maturity" in draft.text.lower() or "checklist" in draft.text.lower()

    relationships = client.get(f"/api/projects/{project_id}/relationships").json()

    assert relationships


def test_stream_endpoint_returns_sse(client: TestClient):
    project_id = create_project(client)
    request = Request({
        "type": "http",
        "method": "GET",
        "path": f"/api/projects/{project_id}/stream",
        "headers": [],
        "query_string": b"",
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
        "scheme": "http",
    })
    response = asyncio.run(stream_project_events(project_id, request))
    assert response.media_type == "text/event-stream"
