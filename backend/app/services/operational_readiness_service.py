"""Author-language readiness for the supported local/private-beta runtime."""
from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from app.core.config import settings
from app.core.version import APP_VERSION, SCHEMA_VERSION
from app.services.project_backup_service import backup_root
from app.services.settings_service import settings_service


def _storage_check(path: Path, label: str) -> Dict[str, Any]:
    path = path.expanduser().resolve()
    probe = path / f".novelforge-write-{uuid4().hex}.tmp"
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        usage = shutil.disk_usage(path)
        free_mb = round(usage.free / 1024 / 1024)
        minimum = max(1, int(settings.minimum_free_space_mb))
        status = "ready" if free_mb >= minimum else "attention"
        explanation = (
            f"{label} is writable with {free_mb:,} MB free."
            if status == "ready"
            else f"{label} is writable, but only {free_mb:,} MB is free. Free space before generating or backing up more work."
        )
        return {"status": status, "explanation": explanation, "free_mb": free_mb, "path": str(path)}
    except OSError:
        probe.unlink(missing_ok=True)
        return {
            "status": "blocked",
            "explanation": f"NovelForge cannot write to {label.lower()}. Existing database work is unchanged.",
            "path": str(path),
        }


class OperationalReadinessService:
    async def snapshot(self, db) -> Dict[str, Any]:
        checked_at = datetime.utcnow()
        checks: Dict[str, Dict[str, Any]] = {}
        database_available = True

        try:
            await db.command("ping")
            probe_id = f"readiness:{uuid4()}"
            await db.operational_probes.insert_one({"_id": probe_id, "created_at": checked_at})
            await db.operational_probes.delete_one({"_id": probe_id})
            checks["database"] = {
                "status": "ready",
                "explanation": "Your project library is available and NovelForge can save changes.",
            }
        except Exception:
            database_available = False
            checks["database"] = {
                "status": "blocked",
                "explanation": "NovelForge cannot save to its local project database. Existing files have not been changed.",
                "action": "Start MongoDB, then check again.",
            }

        # Do not keep issuing database operations after the availability probe
        # fails. Besides making the readiness check unnecessarily slow, those
        # follow-up calls used to escape as a generic HTTP 500 and hid the
        # recovery guidance this endpoint exists to provide.
        if not database_available:
            checks["database_version"] = {
                "status": "blocked",
                "explanation": "NovelForge cannot verify the project data version until the local database is available.",
                "schema_version": None,
                "expected_schema_version": SCHEMA_VERSION,
                "migration_status": "unknown",
            }
            checks["backup_storage"] = _storage_check(backup_root(), "Backup storage")
            export_root = Path(settings.publication_export_directory or "./exports")
            checks["export_storage"] = _storage_check(export_root, "Publication storage")
            checks["ai"] = {
                "status": "unavailable",
                "explanation": "AI readiness cannot be checked while the local project database is unavailable.",
                "provider": None,
                "model": None,
                "configured": False,
                "action": "Restore the local database connection, then check again.",
                "destination": "/settings",
            }
            blocking = ["database", "database_version"]
            attention = [
                name
                for name, check in checks.items()
                if check["status"] in {"attention", "needs_setup", "configured_untested", "unavailable"}
            ]
            return {
                "status": "blocked",
                "summary": "NovelForge cannot safely open or save projects until its local database is available.",
                "app_version": APP_VERSION,
                "schema_version": SCHEMA_VERSION,
                "supported_deployment": "local_private_beta",
                "first_run": False,
                "project_count": 0,
                "existing_work_available": False,
                "ai_required_for_existing_work": False,
                "checks": checks,
                "blocking_checks": blocking,
                "attention_checks": attention,
                "last_backup_at": None,
                "checked_at": checked_at.isoformat() + "Z",
            }

        app_settings = await db.app_settings.find_one({"_id": "global_settings"}) or {}
        application = app_settings.get("application") or {}
        migration_ok = (
            int(application.get("schema_version") or 0) == SCHEMA_VERSION
            and int((app_settings.get("migrations") or {}).get("rc9_version") or 0) >= 1
            and application.get("migration_status") in {None, "completed"}
        )
        checks["database_version"] = {
            "status": "ready" if migration_ok else "blocked",
            "explanation": (
                "Project data is compatible with this NovelForge release."
                if migration_ok
                else "The database update did not finish. Do not continue editing until startup recovery succeeds."
            ),
            "schema_version": int(application.get("schema_version") or 0),
            "expected_schema_version": SCHEMA_VERSION,
            "migration_status": application.get("migration_status") or "completed",
        }

        checks["backup_storage"] = _storage_check(backup_root(), "Backup storage")
        export_root = Path(settings.publication_export_directory or "./exports")
        checks["export_storage"] = _storage_check(export_root, "Publication storage")

        public_settings = await settings_service.get_public_provider_settings()
        execution = await settings_service.get_execution_settings()
        provider = str(execution.get("default_provider") or "gemini")
        model = str(execution.get("default_model") or "")
        provider_config = (public_settings.get("providers") or {}).get(provider) or {}
        configured = bool(provider_config.get("configured") or (provider == "ollama" and provider_config.get("enabled")))
        health = await db.provider_health.find_one({"provider": provider}) or {}
        provider_status = str(health.get("status") or "untested")
        if settings.use_mock_llm:
            ai_status = "test_mode"
            ai_explanation = "NovelForge is using mock AI for development tests. Real story generation is not active."
        elif not configured or not model:
            ai_status = "needs_setup"
            ai_explanation = "Your projects are available, but AI writing needs a provider key and selected model."
        elif provider_status in {"degraded", "offline"}:
            ai_status = "unavailable"
            ai_explanation = "Your projects remain available, but the AI service recently failed. You can keep reviewing and editing existing work."
        elif provider_status == "online":
            ai_status = "ready"
            ai_explanation = f"{provider.title()} is ready for AI-assisted writing."
        else:
            ai_status = "configured_untested"
            ai_explanation = "AI is configured but has not been tested in this session. Existing project work is available."
        checks["ai"] = {
            "status": ai_status,
            "explanation": ai_explanation,
            "provider": provider,
            "model": model or None,
            "configured": configured,
            "action": "Open AI Connections & Settings" if ai_status != "ready" else None,
            "destination": "/settings#ai-provider" if ai_status != "ready" else None,
        }

        latest_backup = await db.project_backups.find_one(
            {"status": "available"}, sort=[("created_at", -1)]
        )
        project_count = await db.projects.count_documents({"status": {"$ne": "trashed"}})
        blocking = [name for name, check in checks.items() if check["status"] == "blocked"]
        attention = [name for name, check in checks.items() if check["status"] in {"attention", "needs_setup", "configured_untested", "unavailable"}]
        if blocking:
            status = "blocked"
            summary = "NovelForge needs attention before it can safely save new work."
        elif checks["ai"]["status"] in {"needs_setup", "unavailable", "configured_untested"}:
            status = "offline_ready"
            summary = "Your local projects are ready. AI assistance needs setup or recovery."
        else:
            status = "ready"
            summary = "NovelForge is ready for local writing and AI assistance."
        return {
            "status": status,
            "summary": summary,
            "app_version": APP_VERSION,
            "schema_version": SCHEMA_VERSION,
            "supported_deployment": "local_private_beta",
            "first_run": project_count == 0,
            "project_count": project_count,
            "existing_work_available": checks["database"]["status"] == "ready",
            "ai_required_for_existing_work": False,
            "checks": checks,
            "blocking_checks": blocking,
            "attention_checks": attention,
            "last_backup_at": latest_backup.get("created_at").isoformat() + "Z" if latest_backup and latest_backup.get("created_at") else None,
            "checked_at": checked_at.isoformat() + "Z",
        }


operational_readiness_service = OperationalReadinessService()
