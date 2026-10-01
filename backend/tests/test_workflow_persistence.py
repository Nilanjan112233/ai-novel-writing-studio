import pytest
from bson import ObjectId
from app.services.workflow_persistence import extract_agent_content, build_initial_state


def test_build_initial_state_includes_idea_dump():
    project = {
        "title": "T",
        "premise": "P",
        "idea_dump": "Big idea dump",
        "genre": "Fantasy",
        "tone": "Dark",
        "themes": ["grief"],
        "inspirations": ["LOTR"],
    }
    state = build_initial_state(project, "proj1")
    assert state["idea_dump"] == "Big idea dump"
    assert state["themes"] == ["grief"]


def test_extract_intake_content():
    state = {
        "genre": "Fantasy",
        "themes": ["death"],
        "hooks": ["hook1"],
    }
    content = extract_agent_content("intake", state)
    assert "Fantasy" in content
    assert "death" in content


@pytest.mark.asyncio
async def test_workflow_saves_outputs_to_db(client, sample_project):
    """Run workflow in background and verify outputs endpoint returns data."""
    create = client.post("/api/projects", json={
        **sample_project,
        "idea_dump": "A prince hears dead gods in a decaying kingdom.",
    })
    project_id = create.json()["id"]

    run_resp = client.post(f"/api/projects/{project_id}/run")
    assert run_resp.status_code == 200
    run_id = run_resp.json()["id"]

    import time
    for _ in range(60):
        runs = client.get(f"/api/projects/{project_id}/runs").json()
        if runs and runs[0]["status"] in ("completed", "waiting_for_user", "failed"):
            break
        time.sleep(0.5)

    runs = client.get(f"/api/projects/{project_id}/runs").json()
    assert runs[0]["status"] in ("completed", "waiting_for_user")

    outputs = client.get(f"/api/projects/{project_id}/outputs").json()
    assert isinstance(outputs, list)
    assert len(outputs) >= 4

    questions = client.get(f"/api/projects/{project_id}/questions").json()
    assert isinstance(questions, list)

    bible = client.get(f"/api/projects/{project_id}/story-bible").json()
    assert bible["sections"]["story_vision"]["premise"]
    assert bible["sections"]["arcs"]
