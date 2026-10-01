import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from bson import ObjectId
from pymongo import MongoClient

from app.core.config import settings
from app.services import project_backup_service as backup_module


def _database():
    client = MongoClient(settings.mongodb_url)
    return client, client[settings.database_name]


def _create_project(client, title="RC9 Backup Story") -> str:
    response = client.post(
        "/api/projects",
        json={
            "title": title,
            "premise": "A watchmaker must decide which hour the city is allowed to remember.",
            "genre": "Fantasy",
            "tone": "Hopeful",
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_backup_validates_and_restores_complete_copy(client, tmp_path):
    previous = settings.backup_directory
    settings.backup_directory = str(tmp_path / "backups")
    mongo, db = _database()
    try:
        project_id = _create_project(client)
        pid = ObjectId(project_id)
        character_id = ObjectId()
        db.character_bibles.insert_one({
            "_id": character_id,
            "project_id": pid,
            "name": "Mara",
            "goals": ["Restore noon"],
            "created_at": backup_module.datetime.utcnow(),
        })
        db.scene_plans.insert_one({
            "project_id": pid,
            "scene_id": "scene-opening",
            "title": "The Missing Hour",
            "character_id": character_id,
            "order": 1,
        })

        created = client.post(
            f"/api/projects/{project_id}/backups", json={"reason": "before revision"}
        )
        assert created.status_code == 200, created.text
        backup = created.json()
        assert backup["status"] == "available"
        assert backup["schema_version"] == 9
        assert backup["collection_counts"]["character_bibles"] == 1
        assert backup["collection_counts"]["scene_plans"] == 1
        assert "AI provider credentials" in backup["excluded_data"]

        validation = client.post(f"/api/backups/{backup['backup_id']}/validate")
        assert validation.status_code == 200, validation.text
        assert validation.json()["valid"] is True

        restored = client.post(
            f"/api/backups/{backup['backup_id']}/restore",
            json={"title": "The Hours We Kept"},
        )
        assert restored.status_code == 200, restored.text
        payload = restored.json()
        assert payload["restored_as_copy"] is True
        assert payload["original_project_unchanged"] is True
        restored_id = ObjectId(payload["project_id"])
        assert restored_id != pid
        assert db.projects.find_one({"_id": pid}) is not None
        assert db.projects.find_one({"_id": restored_id})["title"] == "The Hours We Kept"
        restored_character = db.character_bibles.find_one({"project_id": restored_id})
        restored_scene = db.scene_plans.find_one({"project_id": restored_id})
        assert restored_character["_id"] != character_id
        assert restored_scene["character_id"] == restored_character["_id"]
        assert db.story_bibles.find_one({"project_id": restored_id}) is not None
        checkpoint = client.get(f"/api/projects/{restored_id}/memory/index/status")
        assert checkpoint.status_code == 200
        assert checkpoint.json()["status"] == "INCOMPLETE"
        assert checkpoint.json()["fallback_reason"] == "restored_project_requires_index_rebuild"
        rebuilt = client.post(f"/api/projects/{restored_id}/memory/index/rebuild")
        assert rebuilt.status_code == 200, rebuilt.text
        assert rebuilt.json()["status"] == "READY"
        recalled = client.get(
            f"/api/projects/{restored_id}/memory/search",
            params={"q": "Who must restore noon?", "top_k": 8},
        )
        assert recalled.status_code == 200
        assert any("Mara" in row["content"] for row in recalled.json())
    finally:
        settings.backup_directory = previous
        mongo.close()


def test_corrupt_backup_is_rejected_before_restore(client, tmp_path):
    previous = settings.backup_directory
    settings.backup_directory = str(tmp_path / "backups")
    mongo, db = _database()
    try:
        project_id = _create_project(client, "Corruption Check")
        created = client.post(f"/api/projects/{project_id}/backups", json={})
        assert created.status_code == 200
        backup_id = created.json()["backup_id"]
        record = db.project_backups.find_one({"backup_id": backup_id})
        path = Path(record["file_path"])
        path.write_bytes(path.read_bytes() + b"damaged")

        validation = client.post(f"/api/backups/{backup_id}/validate")
        assert validation.status_code == 409
        assert "damaged" in validation.json()["detail"].lower()
        assert db.projects.count_documents({"restored_from_backup_id": backup_id}) == 0
    finally:
        settings.backup_directory = previous
        mongo.close()


def test_restore_rolls_back_copy_when_post_restore_verification_fails(client, tmp_path, monkeypatch):
    previous = settings.backup_directory
    settings.backup_directory = str(tmp_path / "backups")
    mongo, db = _database()
    try:
        project_id = _create_project(client, "Rollback Check")
        db.character_bibles.insert_one({
            "project_id": ObjectId(project_id), "name": "Tarin", "goals": ["Return home"]
        })
        created = client.post(f"/api/projects/{project_id}/backups", json={})
        backup_id = created.json()["backup_id"]

        async def fail_audit(*_args, **_kwargs):
            raise RuntimeError("simulated post-restore failure")

        monkeypatch.setattr(backup_module, "audit_project_database", fail_audit)
        restored = client.post(f"/api/backups/{backup_id}/restore", json={})
        assert restored.status_code == 500
        assert "original project is unchanged" in restored.json()["detail"].lower()
        assert db.projects.count_documents({"restored_from_backup_id": backup_id}) == 0
        operation = db.restore_operations.find_one({"backup_id": backup_id}, sort=[("created_at", -1)])
        assert operation["status"] == "failed"
        assert operation["rolled_back"] is True
    finally:
        settings.backup_directory = previous
        mongo.close()


def test_backup_checksum_matches_downloaded_archive(client, tmp_path):
    previous = settings.backup_directory
    settings.backup_directory = str(tmp_path / "backups")
    try:
        project_id = _create_project(client, "Download Check")
        created = client.post(f"/api/projects/{project_id}/backups", json={})
        payload = created.json()
        download = client.get(f"/api/backups/{payload['backup_id']}/download")
        assert download.status_code == 200
        assert download.headers["x-novelforge-backup"] == payload["backup_id"]
        assert hashlib.sha256(download.content).hexdigest() == payload["archive_sha256"]
    finally:
        settings.backup_directory = previous


def test_downloaded_backup_can_be_imported_after_metadata_loss(client, tmp_path):
    previous = settings.backup_directory
    settings.backup_directory = str(tmp_path / "backups")
    mongo, db = _database()
    try:
        project_id = _create_project(client, "Portable Recovery")
        db.decision_registry.insert_one({
            "project_id": ObjectId(project_id),
            "question_id": "first-choice",
            "answer": "Trust the mapmaker",
        })
        created = client.post(f"/api/projects/{project_id}/backups", json={})
        backup_id = created.json()["backup_id"]
        downloaded = client.get(f"/api/backups/{backup_id}/download")
        assert downloaded.status_code == 200

        record = db.project_backups.find_one_and_delete({"backup_id": backup_id})
        Path(record["file_path"]).unlink()
        imported = client.post(
            "/api/backups/import",
            content=downloaded.content,
            headers={
                "Content-Type": "application/octet-stream",
                "X-NovelForge-Filename": "portable.novelforge-backup",
            },
        )
        assert imported.status_code == 200, imported.text
        assert imported.json()["backup_id"] == backup_id
        assert imported.json()["valid"] is True
        assert imported.json()["imported"] is True

        restored = client.post(
            f"/api/backups/{backup_id}/restore", json={"title": "Portable Recovery Restored"}
        )
        assert restored.status_code == 200, restored.text
        restored_id = ObjectId(restored.json()["project_id"])
        assert db.decision_registry.find_one({
            "project_id": restored_id,
            "answer": "Trust the mapmaker",
        }) is not None
    finally:
        settings.backup_directory = previous
        mongo.close()


def test_restore_request_is_idempotent_for_concurrent_and_retried_responses(client, tmp_path):
    previous = settings.backup_directory
    settings.backup_directory = str(tmp_path / "backups")
    mongo, db = _database()
    try:
        project_id = _create_project(client, "Unicode Recovery")
        created = client.post(f"/api/projects/{project_id}/backups", json={})
        assert created.status_code == 200, created.text
        backup_id = created.json()["backup_id"]
        payload = {
            "title": "Unicode Recovery — Restored",
            "request_id": "restore-lost-response-001",
        }

        def restore_once():
            return client.post(f"/api/backups/{backup_id}/restore", json=payload)

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(lambda _index: restore_once(), range(2)))
        assert all(response.status_code == 200 for response in responses), [r.text for r in responses]
        restored_ids = {response.json()["project_id"] for response in responses}
        assert len(restored_ids) == 1

        retry = restore_once()
        assert retry.status_code == 200, retry.text
        assert retry.json()["project_id"] in restored_ids
        assert db.projects.count_documents({
            "restored_from_backup_id": backup_id,
            "title": "Unicode Recovery — Restored",
        }) == 1
    finally:
        settings.backup_directory = previous
        mongo.close()


def test_all_projects_backup_reports_partial_failures_without_rolling_back_completed_archives(client, monkeypatch):
    mongo, db = _database()
    try:
        first = _create_project(client, "All Projects One")
        second = _create_project(client, "All Projects Two")
        seen = []

        async def fake_create(_db, project_id, *, reason):
            seen.append(str(project_id))
            project = db.projects.find_one({"_id": project_id})
            if str(project_id) == second:
                raise backup_module.BackupError("Backup destination is unavailable.")
            return {
                "backup_id": f"backup-{project_id}",
                "project_id": str(project_id),
                "project_title": project["title"],
                "status": "available",
                "reason": reason,
            }

        monkeypatch.setattr(backup_module.project_backup_service, "create", fake_create)
        response = client.post("/api/operations/backups", json={"reason": "beta safety copy"})
        assert response.status_code == 200, response.text
        payload = response.json()
        assert first in seen and second in seen
        assert payload["succeeded"] >= 1
        assert payload["failed"] == 1
        assert payload["complete"] is False
        assert payload["failures"][0]["project_title"] == "All Projects Two"
        assert "Completed archives remain available" in payload["explanation"]
    finally:
        mongo.close()
