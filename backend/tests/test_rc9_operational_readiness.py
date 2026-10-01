import json
import zipfile
from pathlib import Path

import httpx
from pymongo import MongoClient

from app.core.config import settings
from app.core.database import Database
from app.services.llm import _call_gemini
from app.services.ai_provider import ai_provider
from app.services.operational_readiness_service import operational_readiness_service


def _database():
    client = MongoClient(settings.mongodb_url)
    return client, client[settings.database_name]


def test_readiness_explains_local_and_ai_states(client, tmp_path):
    previous_backup = settings.backup_directory
    previous_export = settings.publication_export_directory
    settings.backup_directory = str(tmp_path / "backups")
    settings.publication_export_directory = str(tmp_path / "exports")
    try:
        response = client.get("/api/operations/readiness")
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["supported_deployment"] == "local_private_beta"
        assert payload["checks"]["database"]["status"] == "ready"
        assert payload["checks"]["database_version"]["status"] == "ready"
        assert payload["checks"]["backup_storage"]["status"] == "ready"
        assert payload["checks"]["export_storage"]["status"] == "ready"
        assert payload["checks"]["ai"]["status"] == "test_mode"
        assert payload["ai_required_for_existing_work"] is False
        assert response.headers.get("x-novelforge-reference")
        privacy = client.get("/api/operations/privacy")
        assert privacy.status_code == 200
        assert privacy.json()["locations"]["backup_folder"] == str((tmp_path / "backups").resolve())
        assert privacy.json()["hosted_saas_supported"] is False
    finally:
        settings.backup_directory = previous_backup
        settings.publication_export_directory = previous_export


def test_existing_projects_remain_available_when_ai_needs_setup(client, tmp_path):
    previous_mock = settings.use_mock_llm
    previous_backup = settings.backup_directory
    settings.use_mock_llm = False
    settings.backup_directory = str(tmp_path / "backups")
    mongo, db = _database()
    try:
        created = client.post("/api/projects", json={"title": "Offline-safe story"})
        assert created.status_code == 200
        db.app_settings.update_one(
            {"_id": "global_settings"},
            {"$set": {
                "providers.gemini.configured": False,
                "providers.gemini.api_key_encrypted": "",
                "providers.gemini.model": "",
                "execution.default_provider": "gemini",
                "execution.default_model": "",
                "execution.execution_mode": "full",
            }},
        )
        readiness = client.get("/api/operations/readiness")
        assert readiness.status_code == 200
        assert readiness.json()["status"] == "offline_ready"
        assert readiness.json()["existing_work_available"] is True
        assert readiness.json()["checks"]["ai"]["status"] == "needs_setup"
        projects = client.get("/api/projects")
        assert projects.status_code == 200
        assert any(item["id"] == created.json()["id"] for item in projects.json())
    finally:
        settings.use_mock_llm = previous_mock
        settings.backup_directory = previous_backup
        mongo.close()


def test_support_bundle_is_sanitized_and_contains_no_story_or_credentials(client, tmp_path):
    previous_support = settings.support_bundle_directory
    previous_backup = settings.backup_directory
    settings.support_bundle_directory = str(tmp_path / "support")
    settings.backup_directory = str(tmp_path / "backups")
    secret = "AIza-NOT-A-REAL-KEY-RC9"
    story = "THE SILVER MOON STORY SENTENCE MUST NEVER APPEAR"
    mongo, db = _database()
    try:
        db.provider_health.insert_one({
            "provider": "gemini",
            "status": "degraded",
            "active_model": "gemini-test",
            "last_error": {"type": "TEST", "message": f"key={secret} {story}"},
        })
        db.execution_traces.insert_one({
            "request_id": "trace-safe",
            "provider": "gemini",
            "model": "gemini-test",
            "status": "failed",
            "error_type": "TEST",
            "error_message": f"Bearer {secret} {story}",
            "metadata": {"prompt": story, "api_key": secret},
        })
        created = client.post("/api/operations/support-bundles")
        assert created.status_code == 200, created.text
        payload = created.json()
        assert payload["story_content_included"] is False
        assert payload["credentials_included"] is False
        download = client.get(payload["download_url"])
        assert download.status_code == 200
        archive_path = tmp_path / "bundle.zip"
        archive_path.write_bytes(download.content)
        with zipfile.ZipFile(archive_path) as archive:
            combined = "\n".join(
                archive.read(name).decode("utf-8") for name in archive.namelist()
            )
        assert secret not in combined
        assert story not in combined
        manifest = json.loads(zipfile.ZipFile(archive_path).read("manifest.json"))
        assert manifest["privacy"]["story_content_included"] is False
    finally:
        settings.support_bundle_directory = previous_support
        settings.backup_directory = previous_backup
        mongo.close()


def test_feedback_diagnostics_are_explicit_and_never_attach_story(client, tmp_path):
    previous_support = settings.support_bundle_directory
    previous_backup = settings.backup_directory
    settings.support_bundle_directory = str(tmp_path / "support")
    settings.backup_directory = str(tmp_path / "backups")
    try:
        response = client.post(
            "/api/operations/feedback",
            json={
                "category": "startup",
                "message": "The readiness explanation helped, but startup was slow.",
                "include_diagnostics": True,
                "include_story_content": True,
            },
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "saved_locally"
        assert payload["diagnostics_attached"] is True
        assert payload["story_content_attached"] is False
        assert payload["support_id"]
    finally:
        settings.support_bundle_directory = previous_support
        settings.backup_directory = previous_backup


def test_legacy_gemini_client_uses_header_not_query_parameter(monkeypatch):
    calls = []

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": "OK"}]}}]}

        def raise_for_status(self):
            return None

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return FakeResponse()

    monkeypatch.setattr("app.services.llm.httpx.AsyncClient", FakeClient)
    import asyncio

    result = asyncio.run(_call_gemini(
        [{"role": "user", "content": "health check"}],
        "gemini-test",
        "private-test-key",
        0,
        64,
    ))
    assert result == "OK"
    assert calls
    url, kwargs = calls[0]
    assert "private-test-key" not in url
    assert "?key=" not in url
    assert kwargs["headers"]["x-goog-api-key"] == "private-test-key"


def test_provider_connection_check_never_puts_gemini_key_in_url(monkeypatch):
    calls = []

    class FakeResponse:
        status_code = 200

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url, **kwargs):
            calls.append((url, kwargs))
            return FakeResponse()

    monkeypatch.setattr("app.services.ai_provider.httpx.AsyncClient", FakeClient)
    import asyncio

    result = asyncio.run(ai_provider._test_gemini("private-connection-key"))
    assert result == {"success": True}
    url, kwargs = calls[0]
    assert "private-connection-key" not in url
    assert "?key=" not in url
    assert kwargs["headers"]["x-goog-api-key"] == "private-connection-key"


def test_every_api_response_has_support_reference(client):
    response = client.get("/api/projects/not-a-project")
    assert response.status_code == 400
    reference = response.headers.get("x-novelforge-reference")
    assert reference and len(reference) >= 8


def test_database_outage_detection_uses_an_author_facing_timeout(client):
    assert Database.client is not None
    assert Database.client.options.server_selection_timeout == 5.0
    assert Database.client.options.pool_options.connect_timeout == 5.0


def test_readiness_returns_structured_recovery_when_database_is_unavailable():
    class FailingDatabase:
        async def command(self, _command):
            raise RuntimeError("database unavailable")

        def __getattr__(self, name):
            raise AssertionError(f"readiness performed a second database operation: {name}")

    import asyncio

    payload = asyncio.run(operational_readiness_service.snapshot(FailingDatabase()))
    assert payload["status"] == "blocked"
    assert payload["existing_work_available"] is False
    assert payload["checks"]["database"]["status"] == "blocked"
    assert payload["checks"]["database"]["action"] == "Start MongoDB, then check again."
    assert payload["checks"]["database_version"]["migration_status"] == "unknown"
    assert payload["checks"]["ai"]["status"] == "unavailable"
