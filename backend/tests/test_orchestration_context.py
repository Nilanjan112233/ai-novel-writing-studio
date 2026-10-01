import time
from pymongo import MongoClient

from app.core.config import settings as app_config
from app.services.narrative_studio import _compact_cycle_outputs


def create_project(client):
    response = client.post("/api/projects", json={
        "title": f"Orchestration Context {time.time_ns()}",
        "idea_dump": "A tragic mentor hides guilt while preserving mercy as the main theme.",
        "genre": "Fantasy",
        "tone": "Mythic",
    })
    assert response.status_code == 200
    return response.json()["id"]


def wait_for_run(client, project_id):
    for _ in range(80):
        runs = client.get(f"/api/projects/{project_id}/runs").json()
        if runs and runs[0]["status"] in ("completed", "waiting_for_user", "failed"):
            return runs[0]
        time.sleep(0.25)
    raise AssertionError("run did not finish")


def test_mock_provider_validation_returns_structured_json(client):
    result = client.post("/api/settings/test-model", json={"provider": "mock", "model": "mock-narrative-intelligence"})
    assert result.status_code == 200
    body = result.json()
    assert body["success"] is True
    assert body["json_valid"] is True
    assert body["tokens_used"] > 0
    assert body["provider"] == "mock"
    assert body["streaming_supported"] is True


def test_model_registry_and_invalid_model_validation(client):
    models = client.get("/api/settings/models", params={"provider": "mock"}).json()
    assert any(model["model_id"] == "mock-narrative-intelligence" for model in models)

    invalid = client.post("/api/settings/test-model", json={"provider": "gemini", "model": "fake-model-name"})
    assert invalid.status_code == 200
    body = invalid.json()
    assert body["success"] is False
    assert body["error_type"] == "PROVIDER_UNAVAILABLE" or "INVALID_MODEL" in body["error"]


def test_settings_reject_invalid_model_before_save(client):
    response = client.put("/api/settings/execution", json={
        "default_provider": "gemini",
        "default_model": "not-a-real-model",
    })
    assert response.status_code == 400
    assert "INVALID_MODEL" in response.json()["detail"]


def test_recommendations_and_health_dashboard_contract(client):
    validation = client.post("/api/settings/validate-models", json={"provider": "mock"})
    assert validation.status_code == 200
    assert validation.json()["working"] == 1

    recommendation = client.get("/api/settings/recommendations", params={"task_type": "continuity", "context_tokens": 140000}).json()
    assert recommendation["provider"] in {"mock", "gemini", "anthropic", "openrouter", "openai"}
    assert recommendation["model"]

    client.post("/api/settings/test-model", json={"provider": "mock", "model": "mock-narrative-intelligence"})
    health = client.get("/api/settings/health").json()
    assert any(item["provider"] == "mock" and item["status"] == "online" for item in health)


def test_canonical_settings_persist_and_verified_models_contract(client):
    payload = client.get("/api/settings/ai").json()
    payload["providers"]["gemini"]["api_key"] = "test-key"
    payload["providers"]["gemini"]["model"] = ""
    saved = client.put("/api/settings/ai", json=payload)
    assert saved.status_code == 200

    loaded = client.get("/api/settings/ai").json()
    assert "api_key" not in loaded["providers"]["gemini"]
    assert loaded["providers"]["gemini"]["configured"] is True
    assert "providers" in loaded
    mongo = MongoClient(app_config.mongodb_url)
    stored = mongo[app_config.database_name].app_settings.find_one(
        {"_id": "global_settings"}
    )
    mongo.close()
    gemini = stored["providers"]["gemini"]
    assert "api_key" not in gemini
    assert gemini["api_key_encrypted"]
    assert gemini["api_key_encrypted"] != "test-key"

    validation = client.post("/api/settings/validate-models", json={"provider": "mock"})
    assert validation.status_code == 200
    verified = client.get("/api/settings/models", params={"provider": "mock", "verified_only": True}).json()
    assert verified[0]["model_id"] == "mock-narrative-intelligence"

    traces = client.get("/api/settings/execution-traces").json()
    assert any(trace["provider"] == "mock" for trace in traces)


def test_cycle_output_context_is_compact_and_bounded():
    large_payload = "x" * 50000
    compact = _compact_cycle_outputs(
        [
            {
                "agent_name": "StoryArchitectAgent",
                "summary": "Arc structure proposed.",
                "structured_output": {
                    "summary": large_payload,
                    "reasoning": large_payload,
                    "recommendation": "Keep the first turn focused.",
                    "concerns": ["One", "Two", "Three", "Four"],
                    "arcs": [{"title": large_payload}],
                },
                "artifacts_created": {"arcs": 1},
            }
        ]
    )
    assert compact == [
        {
            "agent_name": "StoryArchitectAgent",
            "summary": "Arc structure proposed.",
            "recommendation": "Keep the first turn focused.",
            "concerns": ["One", "Two", "Three"],
            "artifacts_created": {"arcs": 1},
        }
    ]


def test_context_engine_and_orchestration_are_recorded(client):
    project_id = create_project(client)
    client.post(
        f"/api/projects/{project_id}/messages",
        json={"content": "Make the mentor more tragic but genuinely good."},
    )
    response = client.post(f"/api/projects/{project_id}/cycle")
    assert response.status_code == 200
    run = wait_for_run(client, project_id)
    assert run["status"] in ("completed", "waiting_for_user")

    context = client.get(f"/api/projects/{project_id}/context/latest").json()
    assert context["packet"]["active_context"]
    assert context["packet"]["working_memory"]
    assert context["token_estimate"] > 0

    orchestration = client.get(f"/api/projects/{project_id}/orchestration/latest").json()
    assert orchestration["selected_agents"]
    assert orchestration["skipped_agents"]
    assert len(orchestration["tasks"]) == len(orchestration["selected_agents"]) + len(
        orchestration["skipped_agents"]
    )
    assert all(task["reason"] for task in orchestration["tasks"])
    assert orchestration["actual_cost_usd"] == 0
    assert len(orchestration["selected_agents"]) < 12

    outputs = client.get(f"/api/projects/{project_id}/outputs").json()
    assert outputs
    assert all(output["metadata"]["canon_decisions_read"] >= 1 for output in outputs)


def test_narrative_retrieval_ranking_prefers_relevant_memory(client):
    project_id = create_project(client)
    client.post(
        f"/api/projects/{project_id}/messages",
        json={"content": "The mentor should be more tragic and emotionally central."},
    )
    client.post(f"/api/projects/{project_id}/cycle")
    wait_for_run(client, project_id)

    hits = client.get(
        f"/api/projects/{project_id}/memory/search",
        params={"q": "tragic mentor guilt", "top_k": 3},
    ).json()
    assert hits
    assert hits[0]["score"] >= hits[-1]["score"]
    assert any(hit["source_type"] in {"character", "plot_thread", "theme"} for hit in hits[:3])


def test_budget_and_call_limits_actively_skip_agents_with_reasons(client):
    settings = client.put("/api/settings/execution", json={
        "execution_mode": "mock",
        "max_cycle_cost_usd": 0.0,
        "max_agent_calls_per_cycle": 2,
    })
    assert settings.status_code == 200
    project_id = create_project(client)
    client.post(f"/api/projects/{project_id}/cycle")
    wait_for_run(client, project_id)
    orchestration = client.get(f"/api/projects/{project_id}/orchestration/latest").json()
    assert orchestration["selected_agents"] == []
    assert orchestration["actual_agent_calls"] == 0
    assert all(task["status"] == "skipped" for task in orchestration["tasks"])
    assert any(
        "max_cycle_cost_usd" in task["reason"]
        for task in orchestration["tasks"]
    )

    client.put("/api/settings/execution", json={
        "execution_mode": "mock",
        "max_cycle_cost_usd": 2.0,
        "max_agent_calls_per_cycle": 8,
    })
