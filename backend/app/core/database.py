from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from app.core.config import settings
from app.migrations.provider_models import migrate_provider_models
from app.migrations.phase_1a import migrate_phase_1a
from app.migrations.phase_1b import migrate_phase_1b
from app.migrations.phase_2a import migrate_phase_2a
from app.migrations.phase_2b import migrate_phase_2b
from app.migrations.phase_3a import migrate_phase_3a
from app.migrations.phase_3b import migrate_phase_3b
from app.migrations.phase_3c import migrate_phase_3c
from app.migrations.phase_6 import migrate_phase_6
from app.migrations.phase_7 import migrate_phase_7
from app.migrations.product_completion import migrate_product_completion
from app.migrations.rc5 import migrate_rc5
from app.migrations.post_rc5_hardening import migrate_post_rc5_hardening
from app.migrations.rc8 import migrate_rc8
from app.migrations.rc9 import migrate_rc9
from app.migrations.product_audit_hardening import migrate_product_audit_hardening
from app.migrations.evolution import migrate_evolution
from app.migrations.memory_phase_a import migrate_memory_phase_a
from app.migrations.phase_e import migrate_phase_e
from app.migrations.memory_phase_b import migrate_memory_phase_b
from app.migrations.memory_phase_c import migrate_memory_phase_c
from app.core.version import APP_VERSION, SCHEMA_VERSION
from datetime import datetime
from uuid import uuid4
from datetime import timedelta
import asyncio
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError


class Database:
    client: Optional[AsyncIOMotorClient] = None
    db = None

    @classmethod
    async def _acquire_migration_lock(cls, run_id: str, db=None) -> None:
        """Serialize startup migrations across accidental concurrent launches."""
        target_db = db if db is not None else cls.db
        for _attempt in range(60):
            now = datetime.utcnow()
            try:
                lock = await target_db.migration_locks.find_one_and_update(
                    {
                        "_id": "schema_migration",
                        "$or": [
                            {"status": {"$ne": "running"}},
                            {"lease_expires_at": {"$lte": now}},
                            {"owner": run_id},
                        ],
                    },
                    {"$set": {
                        "status": "running",
                        "owner": run_id,
                        "started_at": now,
                        "lease_expires_at": now + timedelta(minutes=30),
                        "app_version": APP_VERSION,
                    }},
                    upsert=True,
                    return_document=ReturnDocument.AFTER,
                )
            except DuplicateKeyError:
                lock = None
            if lock and lock.get("owner") == run_id:
                return
            await asyncio.sleep(2)
        raise RuntimeError("Another NovelForge process is still updating the local database")
    
    @classmethod
    async def connect(cls):
        if cls.client is None:
            # A local database outage should become an actionable readiness
            # result quickly instead of leaving the author at a spinner for
            # the driver's default ~30 second selection window.
            cls.client = AsyncIOMotorClient(
                settings.mongodb_url,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
            )
            cls.db = cls.client[settings.database_name]
            run_id = str(uuid4())
            migrations = (
                ("provider_models", migrate_provider_models),
                ("phase_1a", migrate_phase_1a),
                ("phase_1b", migrate_phase_1b),
                ("phase_2a", migrate_phase_2a),
                ("phase_2b", migrate_phase_2b),
                ("phase_3a", migrate_phase_3a),
                ("phase_3b", migrate_phase_3b),
                ("phase_3c", migrate_phase_3c),
                ("phase_6", migrate_phase_6),
                ("phase_7", migrate_phase_7),
                ("product_completion", migrate_product_completion),
                ("rc5", migrate_rc5),
                ("post_rc5_hardening", migrate_post_rc5_hardening),
                ("rc8", migrate_rc8),
                ("rc9", migrate_rc9),
                ("product_audit_hardening", migrate_product_audit_hardening),
                ("evolution", migrate_evolution),
                ("memory_phase_a", migrate_memory_phase_a),
                ("phase_e", migrate_phase_e),
                ("memory_phase_b", migrate_memory_phase_b),
                ("memory_phase_c", migrate_memory_phase_c),
            )
            try:
                await cls.db.command("ping")
                await cls._acquire_migration_lock(run_id)
                await cls.db.app_settings.update_one(
                    {"_id": "global_settings"},
                    {"$set": {
                        "application.migration_status": "running",
                        "application.migration_run_id": run_id,
                        "application.migration_started_at": datetime.utcnow(),
                    }},
                    upsert=True,
                )
                for name, migration in migrations:
                    started_at = datetime.utcnow()
                    try:
                        result = await migration(cls.db)
                    except Exception as exc:
                        await cls.db.migration_runs.update_one(
                            {"run_id": run_id, "migration": name},
                            {"$set": {
                                "status": "failed",
                                "started_at": started_at,
                                "finished_at": datetime.utcnow(),
                                "app_version": APP_VERSION,
                                "schema_version": SCHEMA_VERSION,
                                "error_type": type(exc).__name__,
                            }},
                            upsert=True,
                        )
                        await cls.db.app_settings.update_one(
                            {"_id": "global_settings"},
                            {"$set": {
                                "application.migration_status": "failed",
                                "application.migration_failed_step": name,
                                "application.migration_failed_at": datetime.utcnow(),
                                "application.migration_error_type": type(exc).__name__,
                            }},
                        )
                        await cls.db.migration_locks.update_one(
                            {"_id": "schema_migration", "owner": run_id},
                            {"$set": {"status": "failed", "finished_at": datetime.utcnow()}},
                        )
                        raise
                    await cls.db.migration_runs.update_one(
                        {"run_id": run_id, "migration": name},
                        {"$set": {
                            "status": "completed",
                            "started_at": started_at,
                            "finished_at": datetime.utcnow(),
                            "app_version": APP_VERSION,
                            "schema_version": SCHEMA_VERSION,
                            "result": result if isinstance(result, dict) else {},
                        }},
                        upsert=True,
                    )
                await cls.db.app_settings.update_one(
                    {"_id": "global_settings"},
                    {"$set": {
                        "application.migration_status": "completed",
                        "application.migration_completed_at": datetime.utcnow(),
                        "application.version": APP_VERSION,
                        "application.schema_version": SCHEMA_VERSION,
                    }, "$unset": {
                        "application.migration_failed_step": "",
                        "application.migration_failed_at": "",
                        "application.migration_error_type": "",
                    }},
                )
                await cls.db.migration_locks.update_one(
                    {"_id": "schema_migration", "owner": run_id},
                    {"$set": {
                        "status": "completed",
                        "finished_at": datetime.utcnow(),
                        "schema_version": SCHEMA_VERSION,
                    }, "$unset": {"lease_expires_at": ""}},
                )
                # In-process background work cannot survive a restart. Convert
                # persisted running records into an honest, recoverable state
                # before any workspace reads them.
                from app.services.development_state_service import development_state_service
                await development_state_service.recover_interrupted(cls.db)
                from app.services.story_studio_service import story_studio_service
                recovered_story_studio = await story_studio_service.recover_interrupted_jobs(cls.db)
                if recovered_story_studio:
                    print(f"Recovered {recovered_story_studio} interrupted Story Studio job(s)")
                from app.services.memory_incremental_index_service import memory_incremental_index_service
                recovered_memory = await memory_incremental_index_service.recover_interrupted(cls.db)
                if recovered_memory.get("events_requeued"):
                    print(f"Recovered {recovered_memory['events_requeued']} interrupted memory index event(s)")
            except Exception:
                cls.client.close()
                cls.client = None
                cls.db = None
                raise
            print(f"Connected to MongoDB: {settings.database_name} ({APP_VERSION})")
    
    @classmethod
    async def disconnect(cls):
        if cls.client:
            cls.client.close()
            print("Disconnected from MongoDB")
        cls.client = None
        cls.db = None
    
    @classmethod
    def get_db(cls):
        if cls.db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return cls.db
