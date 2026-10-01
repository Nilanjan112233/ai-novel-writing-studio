import httpx
import pytest
from pymongo import MongoClient

from app.core.config import settings
from app.services.provider_gateway import provider_gateway


@pytest.fixture(autouse=True)
def restore_provider_discovery_collections():
    providers = ["gemini", "openrouter", "openai"]
    client = MongoClient(settings.mongodb_url)
    db = client[settings.database_name]
    collections = [
        "provider_models",
        "provider_model_health",
        "provider_status",
        "provider_model_validation",
        "provider_health",
        "provider_quota_usage",
    ]
    snapshots = {
        collection: list(db[collection].find({"provider": {"$in": providers}}))
        for collection in collections
    }
    settings_snapshot = db.app_settings.find_one({"_id": "global_settings"})
    for collection in collections:
        db[collection].delete_many({"provider": {"$in": providers}})
    yield
    for collection in collections:
        db[collection].delete_many({"provider": {"$in": providers}})
        if snapshots[collection]:
            db[collection].insert_many(snapshots[collection])
    if settings_snapshot:
        db.app_settings.replace_one({"_id": "global_settings"}, settings_snapshot, upsert=True)
    else:
        db.app_settings.delete_one({"_id": "global_settings"})
    client.close()


class StubClient:
    def __init__(self, response_factory, calls):
        self.response_factory = response_factory
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self.response_factory(url)


def response(status_code, payload):
    request = httpx.Request("GET", "https://provider.test/models")
    return httpx.Response(status_code, json=payload, request=request)


@pytest.mark.parametrize(
    ("provider", "payload", "expected_model", "header", "header_prefix"),
    [
        (
            "gemini",
            {
                "models": [{
                    "name": "models/gemini-test-flash",
                    "displayName": "Gemini Test Flash",
                    "supportedGenerationMethods": ["generateContent", "streamGenerateContent"],
                    "inputTokenLimit": 100000,
                }]
            },
            "gemini-test-flash",
            "x-goog-api-key",
            "test-key",
        ),
        (
            "openrouter",
            {"data": [{"id": "vendor/test:free", "name": "Router Test", "context_length": 32000, "pricing": {"prompt": "0", "completion": "0"}}]},
            "vendor/test:free",
            "Authorization",
            "Bearer test-key",
        ),
        (
            "openai",
            {"data": [{"id": "gpt-test", "owned_by": "openai"}]},
            "gpt-test",
            "Authorization",
            "Bearer test-key",
        ),
    ],
)
def test_provider_discovery_mocks(client, monkeypatch, provider, payload, expected_model, header, header_prefix):
    calls = []
    monkeypatch.setattr(
        "app.services.provider_validation_service.httpx.AsyncClient",
        lambda: StubClient(lambda _url: response(200, payload), calls),
    )

    result = client.post(
        f"/api/settings/providers/{provider}/discover",
        json={"api_key": "test-key"},
    )

    assert result.status_code == 200
    body = result.json()
    assert body["status"] == "online"
    assert body["discovered_model_count"] == 1
    assert any(model["model_id"] == expected_model for model in body["models"])
    assert calls[0]["headers"][header] == header_prefix


def test_invalid_key_marks_provider_offline(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.provider_validation_service.httpx.AsyncClient",
        lambda: StubClient(lambda _url: response(401, {"error": "invalid key"}), []),
    )

    result = client.post(
        "/api/settings/providers/openai/discover",
        json={"api_key": "invalid"},
    ).json()

    assert result["status"] == "offline"
    assert result["error_type"] == "INVALID_API_KEY"
    health = client.get("/api/settings/health").json()
    assert next(item for item in health if item["provider"] == "openai")["status"] == "offline"


def test_provider_online_degraded_and_offline_statuses(client, monkeypatch):
    payload = {"data": [{"id": "gpt-status-test", "owned_by": "openai"}]}
    monkeypatch.setattr(
        "app.services.provider_validation_service.httpx.AsyncClient",
        lambda: StubClient(lambda _url: response(200, payload), []),
    )
    client.post("/api/settings/providers/openai/discover", json={"api_key": "valid"})
    health = client.get("/api/settings/health").json()
    assert next(item for item in health if item["provider"] == "openai")["status"] == "online"

    async def failed_model_test(provider, model, db=None):
        return {
            "success": False,
            "provider": provider,
            "model": model,
            "latency_ms": 1,
            "tokens_used": 0,
            "json_valid": False,
            "streaming_supported": False,
            "error_type": "INVALID_MODEL",
            "error": "model failed",
        }

    monkeypatch.setattr(provider_gateway, "test_model", failed_model_test)
    client.post("/api/ai/test-model", json={"provider": "openai", "model": "gpt-status-test"})
    health = client.get("/api/settings/health").json()
    assert next(item for item in health if item["provider"] == "openai")["status"] == "degraded"

    monkeypatch.setattr(
        "app.services.provider_validation_service.httpx.AsyncClient",
        lambda: StubClient(lambda _url: response(401, {"error": "invalid key"}), []),
    )
    client.post("/api/settings/providers/openai/discover", json={"api_key": "invalid"})
    health = client.get("/api/settings/health").json()
    assert next(item for item in health if item["provider"] == "openai")["status"] == "offline"


def test_model_test_alias_returns_structured_result(client):
    result = client.post(
        "/api/ai/test-model",
        json={"provider": "mock", "model": "mock-narrative-intelligence"},
    )
    assert result.status_code == 200
    body = result.json()
    assert body["success"] is True
    assert body["latency_ms"] >= 0
    assert body["tokens_used"] > 0
    assert "error" not in body


def test_validate_all_uses_only_discovered_models(client, monkeypatch):
    async def fake_test_model(provider, model, db=None):
        return {
            "success": True,
            "provider": provider,
            "model": model,
            "latency_ms": 1,
            "tokens_used": 1,
            "json_valid": True,
            "streaming_supported": True,
        }

    monkeypatch.setattr(provider_gateway, "test_model", fake_test_model)
    result = client.post("/api/settings/validate-models", json={"provider": "openai"})
    assert result.status_code == 200
    body = result.json()
    discovered = client.get("/api/settings/models", params={"provider": "openai"}).json()
    assert body["total"] == len(discovered)
    assert {item["model"] for item in body["results"]} == {item["model_id"] for item in discovered}
