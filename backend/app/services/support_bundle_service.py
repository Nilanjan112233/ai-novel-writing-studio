"""Privacy-preserving local diagnostics for private-beta support."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from bson import ObjectId

from app.core.config import settings
from app.core.version import APP_VERSION, SCHEMA_VERSION
from app.services.operational_readiness_service import operational_readiness_service


SENSITIVE_KEY = re.compile(r"(api.?key|authorization|password|secret|token|prompt|response|content|prose|premise)", re.I)
SECRET_TEXT = re.compile(r"(?i)(key|token|authorization)=([^&\s]+)|bearer\s+[a-z0-9._-]+")


def sanitize(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat() + "Z"
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            normalized_key = str(key).lower()
            is_disclosure_flag = normalized_key.endswith(("_included", "_requested"))
            if SENSITIVE_KEY.search(str(key)) and not is_disclosure_flag:
                result[key] = "[redacted]"
            else:
                result[key] = sanitize(item)
        return result
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        return SECRET_TEXT.sub("[redacted]", value)
    return value


def support_root() -> Path:
    configured = settings.support_bundle_directory.strip()
    root = Path(configured).expanduser() if configured else Path.home() / ".novelforge" / "support"
    return root.resolve()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class SupportBundleService:
    async def create(self, db) -> Dict[str, Any]:
        support_id = str(uuid4())
        created_at = datetime.utcnow()
        root = support_root()
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"novelforge-support-{created_at.strftime('%Y%m%d-%H%M%S')}-{support_id[:8]}.zip"
        temp = root / f".{path.name}.tmp"
        readiness = await operational_readiness_service.snapshot(db)
        migrations = await db.migration_runs.find().sort("finished_at", -1).limit(50).to_list(length=50)
        provider_health = await db.provider_health.find({}, {
            "provider": 1,
            "status": 1,
            "active_model": 1,
            "last_success_at": 1,
            "last_latency_ms": 1,
            "failure_count": 1,
            "success_count": 1,
            "updated_at": 1,
            "last_error.type": 1,
            "last_error.created_at": 1,
        }).to_list(length=50)
        traces = await db.execution_traces.find({}, {
            "request_id": 1,
            "provider": 1,
            "model": 1,
            "agent_name": 1,
            "latency_ms": 1,
            "status": 1,
            "error_type": 1,
            "retry_count": 1,
            "fallback_used": 1,
            "application_outcome": 1,
            "created_at": 1,
        }).sort("created_at", -1).limit(100).to_list(length=100)
        backups = await db.project_backups.find({}, {
            "backup_id": 1,
            "status": 1,
            "app_version": 1,
            "schema_version": 1,
            "archive_bytes": 1,
            "created_at": 1,
        }).sort("created_at", -1).limit(50).to_list(length=50)
        manifest = {
            "product": "NovelForge",
            "support_id": support_id,
            "app_version": APP_VERSION,
            "schema_version": SCHEMA_VERSION,
            "created_at": created_at.isoformat() + "Z",
            "privacy": {
                "story_content_included": False,
                "provider_credentials_included": False,
                "database_connection_string_included": False,
                "description": "This bundle contains operational status only. It does not contain story prose, prompts, provider responses, or credentials.",
            },
        }
        documents = {
            "manifest.json": manifest,
            "readiness.json": readiness,
            "runtime.json": {
                "os": platform.system(),
                "os_release": platform.release(),
                "architecture": platform.machine(),
                "python": platform.python_version(),
            },
            "migrations.json": migrations,
            "provider-health.json": provider_health,
            "operation-outcomes.json": traces,
            "backup-history.json": backups,
        }
        try:
            with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, data in documents.items():
                    archive.writestr(name, json.dumps(sanitize(data), indent=2, sort_keys=True, default=str))
            os.replace(temp, path)
        except Exception:
            temp.unlink(missing_ok=True)
            path.unlink(missing_ok=True)
            raise
        checksum = _sha256_file(path)
        await db.support_bundles.insert_one({
            "support_id": support_id,
            "file_path": str(path),
            "created_at": created_at,
            "app_version": APP_VERSION,
            "schema_version": SCHEMA_VERSION,
            "archive_sha256": checksum,
            "archive_bytes": path.stat().st_size,
            "story_content_included": False,
            "credentials_included": False,
        })
        return {
            "support_id": support_id,
            "created_at": manifest["created_at"],
            "archive_sha256": checksum,
            "archive_bytes": path.stat().st_size,
            "story_content_included": False,
            "credentials_included": False,
            "download_url": f"/api/operations/support-bundles/{support_id}/download",
        }

    async def file_path(self, db, support_id: str) -> Path:
        record = await db.support_bundles.find_one({"support_id": support_id})
        if not record:
            raise ValueError("Support bundle not found.")
        root = support_root()
        path = Path(record["file_path"]).resolve()
        if path.parent != root or not path.is_file():
            raise ValueError("Support bundle is no longer available.")
        if _sha256_file(path) != record.get("archive_sha256"):
            raise ValueError("Support bundle integrity check failed.")
        return path


support_bundle_service = SupportBundleService()
