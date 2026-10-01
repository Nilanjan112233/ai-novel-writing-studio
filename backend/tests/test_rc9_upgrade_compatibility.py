import asyncio
from datetime import datetime, timedelta

from bson import ObjectId
from pymongo import MongoClient

from app.core.config import settings
from app.core.database import Database
from app.core.version import APP_VERSION, SCHEMA_VERSION
from app.migrations.rc9 import migrate_rc9


def _database():
    client = MongoClient(settings.mongodb_url)
    return client, client[settings.database_name]


def test_project_library_reads_legacy_projects_without_timestamps(client):
    mongo, db = _database()
    project_id = db.projects.insert_one({
        "title": "Legacy project without timestamps",
        "premise": "An older private-beta record.",
        "status": "draft",
    }).inserted_id
    try:
        response = client.get("/api/projects")
        assert response.status_code == 200
        project = next(item for item in response.json() if item["id"] == str(project_id))
        assert project["created_at"]
        assert project["updated_at"] == project["created_at"]
    finally:
        db.projects.delete_one({"_id": project_id})
        mongo.close()


def test_rc9_migration_preserves_legacy_project_content_and_is_idempotent(client):
    mongo, db = _database()
    fixtures = [
        {"title": "Pre RC6", "premise": "An old premise", "notes": "keep rc5", "status": "draft"},
        {"title": "RC6", "premise": "A guided premise", "favorite": True, "status": "draft"},
        {"title": "RC7", "premise": "A writing premise", "last_opened_at": datetime.utcnow(), "status": "archived"},
        {"title": "RC8", "premise": "A hardened premise", "restored_from_backup_id": "historic", "status": "draft"},
    ]
    ids = []
    legacy_collection_names = [
        "scene_versions",
        "paragraph_versions",
        "canon_facts",
        "decision_registry",
        "story_bibles",
        "narrative_analysis_snapshots",
    ]
    try:
        for fixture in fixtures:
            document = {
                **fixture,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            ids.append(db.projects.insert_one(document).inserted_id)
        legacy_project_id = ids[0]
        legacy_records = {
            "scene_versions": {
                "project_id": legacy_project_id,
                "version_id": "legacy-scene-version",
                "content": "The old prose must survive exactly.",
                "status": "approved",
            },
            "paragraph_versions": {
                "project_id": legacy_project_id,
                "paragraph_id": "legacy-paragraph",
                "content": "An author-edited paragraph.",
                "version_number": 3,
            },
            "canon_facts": {
                "project_id": legacy_project_id,
                "fact_id": "legacy-canon",
                "statement": "The city has seven gates.",
                "status": "approved",
            },
            "decision_registry": {
                "project_id": legacy_project_id,
                "question_id": "legacy-decision",
                "answer": "The protagonist stays.",
            },
            "story_bibles": {
                "project_id": legacy_project_id,
                "version": 4,
                "entries": [{"name": "Old Harbor", "type": "location"}],
            },
            "narrative_analysis_snapshots": {
                "project_id": legacy_project_id,
                "snapshot_type": "current",
                "analysis_version": "legacy-analysis",
                "findings": [{"kind": "continuity", "severity": "medium"}],
            },
        }
        for collection_name, record in legacy_records.items():
            db[collection_name].insert_one({**record, "fixture_marker": "rc9-legacy-preservation"})
        before = {
            row["_id"]: {key: value for key, value in row.items() if key not in {"_id"}}
            for row in db.projects.find({"_id": {"$in": ids}})
        }

        async def run_twice():
            from motor.motor_asyncio import AsyncIOMotorClient
            async_client = AsyncIOMotorClient(settings.mongodb_url)
            async_db = async_client[settings.database_name]
            try:
                return await migrate_rc9(async_db), await migrate_rc9(async_db)
            finally:
                async_client.close()

        first, second = asyncio.run(run_twice())
        assert first["legacy_projects_normalized"] >= 4
        assert second["legacy_projects_normalized"] == 0

        for row in db.projects.find({"_id": {"$in": ids}}):
            original = before[row["_id"]]
            for key, value in original.items():
                assert row[key] == value
            assert row["schema_version"] == SCHEMA_VERSION
            assert row["created_with_app_version"] == "legacy_pre_rc9"
            assert row["last_migrated_with_app_version"] == APP_VERSION

        for collection_name, original in legacy_records.items():
            preserved = db[collection_name].find_one({
                "project_id": legacy_project_id,
                "fixture_marker": "rc9-legacy-preservation",
            })
            assert preserved is not None
            for key, value in original.items():
                assert preserved[key] == value
    finally:
        for collection_name in legacy_collection_names:
            db[collection_name].delete_many({"fixture_marker": "rc9-legacy-preservation"})
        db.projects.delete_many({"_id": {"$in": ids}})
        mongo.close()


def test_startup_migration_result_and_lock_are_durable(client):
    mongo, db = _database()
    try:
        settings_doc = db.app_settings.find_one({"_id": "global_settings"})
        assert settings_doc["application"]["version"] == APP_VERSION
        assert settings_doc["application"]["schema_version"] == SCHEMA_VERSION
        assert settings_doc["application"]["migration_status"] == "completed"
        lock = db.migration_locks.find_one({"_id": "schema_migration"})
        assert lock["status"] == "completed"
        assert "lease_expires_at" not in lock
        rc9_run = db.migration_runs.find_one({"migration": "rc9"}, sort=[("finished_at", -1)])
        assert rc9_run["status"] == "completed"
    finally:
        mongo.close()


def test_expired_migration_lock_can_be_recovered_without_deleting_data(client):
    mongo, db = _database()
    original = db.migration_locks.find_one({"_id": "schema_migration"})
    try:
        db.migration_locks.replace_one(
            {"_id": "schema_migration"},
            {
                "_id": "schema_migration",
                "status": "running",
                "owner": "crashed-process",
                "lease_expires_at": datetime.utcnow() - timedelta(minutes=1),
            },
            upsert=True,
        )
        async def recover_lock():
            from motor.motor_asyncio import AsyncIOMotorClient
            async_client = AsyncIOMotorClient(settings.mongodb_url)
            async_db = async_client[settings.database_name]
            try:
                await Database._acquire_migration_lock("recovery-run", async_db)
            finally:
                async_client.close()

        asyncio.run(recover_lock())
        recovered = db.migration_locks.find_one({"_id": "schema_migration"})
        assert recovered["status"] == "running"
        assert recovered["owner"] == "recovery-run"
        assert recovered["lease_expires_at"] > datetime.utcnow()
    finally:
        if original:
            db.migration_locks.replace_one({"_id": "schema_migration"}, original, upsert=True)
        mongo.close()
