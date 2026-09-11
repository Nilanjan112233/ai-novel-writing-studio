"""Versioned, checksummed project backups and non-destructive restores.

Backups use the existing project ownership registry. They deliberately exclude
global application settings and provider credentials. Restore creates a new
project by default, remaps Mongo identities, verifies counts, and rolls back all
new records if persistence fails.
"""
from __future__ import annotations

import hashlib
import asyncio
import json
import os
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Dict
from uuid import uuid4

from bson import ObjectId, json_util
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.core.version import APP_VERSION, BACKUP_FORMAT_VERSION, SCHEMA_VERSION
from app.services.database_audit_service import audit_project_database
from app.services.project_lifecycle_service import (
    PROJECT_OWNED_COLLECTIONS,
    project_lifecycle_service,
    project_ownership_query,
)
from app.services.story_bible_service import rebuild_story_bible


MAX_ARCHIVE_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024
BACKUP_EXTENSION = ".novelforge-backup"
DERIVED_NATIVE_INDEX_COLLECTIONS = {
    "memory_embeddings", "memory_index_checkpoints", "memory_index_events", "memory_index_staging",
    "atomic_memories", "memory_phase_b_checkpoints",
    "memory_phase_c_checkpoints",
}


class BackupError(ValueError):
    """An author-recoverable backup or restore failure."""


def backup_root() -> Path:
    configured = settings.backup_directory.strip()
    root = Path(configured).expanduser() if configured else Path.home() / ".novelforge" / "backups"
    return root.resolve()


def _safe_path(path_value: str) -> Path:
    root = backup_root()
    candidate = Path(path_value).resolve()
    if candidate.parent != root:
        raise BackupError("The backup location is outside NovelForge's protected backup folder.")
    return candidate


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-._")
    return (cleaned or "untitled")[:60]


def _json_line(document: Dict[str, Any]) -> bytes:
    return (json_util.dumps(document, json_options=json_util.CANONICAL_JSON_OPTIONS) + "\n").encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


async def _collection_rows(db, name: str, project_id: ObjectId) -> AsyncIterator[Dict[str, Any]]:
    query: Dict[str, Any] = project_ownership_query(project_id)
    if name == "agent_outputs":
        run_ids = [
            row["_id"]
            async for row in db.runs.find(project_ownership_query(project_id), {"_id": 1})
            if row.get("_id")
        ]
        query = {"$or": [project_ownership_query(project_id), {"run_id": {"$in": run_ids}}]}
    async for row in db[name].find(query):
        yield row


def _manifest_public(manifest: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "backup_id": manifest["backup_id"],
        "format_version": manifest["format_version"],
        "app_version": manifest["app_version"],
        "schema_version": manifest["schema_version"],
        "project_id": manifest["project_id"],
        "project_title": manifest["project_title"],
        "created_at": manifest["created_at"],
        "collection_counts": manifest["collection_counts"],
        "document_count": sum(manifest["collection_counts"].values()) + 1,
        "excluded_data": manifest["excluded_data"],
    }


class ProjectBackupService:
    async def create(self, db, project_id: ObjectId, *, reason: str = "manual") -> Dict[str, Any]:
        project = await db.projects.find_one({"_id": project_id})
        if not project:
            raise BackupError("Project not found.")

        root = backup_root()
        root.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(root)
        minimum = max(1, int(settings.minimum_free_space_mb)) * 1024 * 1024
        if usage.free < minimum:
            raise BackupError(
                f"A backup cannot be created because less than {settings.minimum_free_space_mb} MB is available. "
                "Your project is unchanged. Free some disk space and try again."
            )

        backup_id = str(uuid4())
        created_at = datetime.utcnow()
        filename = f"{_slug(str(project.get('title') or 'project'))}-{created_at.strftime('%Y%m%d-%H%M%S')}-{backup_id[:8]}{BACKUP_EXTENSION}"
        final_path = root / filename
        temp_path = root / f".{filename}.tmp"
        entries: Dict[str, Dict[str, Any]] = {}
        counts: Dict[str, int] = {}

        try:
            with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                project_name = "project.ndjson"
                project_snapshot = dict(project)
                # A process lease is runtime coordination, not portable project
                # state. Restoring it could make a recovered copy look busy.
                project_snapshot.pop("development_lock", None)
                project_payload = _json_line(project_snapshot)
                archive.writestr(project_name, project_payload)
                entries[project_name] = {
                    "sha256": hashlib.sha256(project_payload).hexdigest(),
                    "bytes": len(project_payload),
                    "documents": 1,
                }

                for collection_name in PROJECT_OWNED_COLLECTIONS:
                    if collection_name in DERIVED_NATIVE_INDEX_COLLECTIONS:
                        continue
                    entry_name = f"collections/{collection_name}.ndjson"
                    digest = hashlib.sha256()
                    byte_count = 0
                    document_count = 0
                    with archive.open(entry_name, "w") as stream:
                        async for row in _collection_rows(db, collection_name, project_id):
                            payload = _json_line(row)
                            stream.write(payload)
                            digest.update(payload)
                            byte_count += len(payload)
                            document_count += 1
                    if document_count:
                        entries[entry_name] = {
                            "sha256": digest.hexdigest(),
                            "bytes": byte_count,
                            "documents": document_count,
                        }
                        counts[collection_name] = document_count

                manifest = {
                    "product": "NovelForge",
                    "backup_id": backup_id,
                    "format_version": BACKUP_FORMAT_VERSION,
                    "app_version": APP_VERSION,
                    "schema_version": SCHEMA_VERSION,
                    "project_id": str(project_id),
                    "project_title": str(project.get("title") or "Untitled Project"),
                    "created_at": created_at.isoformat() + "Z",
                    "reason": reason,
                    "collection_counts": counts,
                    "entries": entries,
                    "excluded_data": [
                        "AI provider credentials",
                        "global application settings",
                        "local access tokens",
                        "publication files stored outside the database",
                    ],
                }
                archive.writestr(
                    "manifest.json",
                    json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8"),
                )
            os.replace(temp_path, final_path)
            archive_sha = _sha256_file(final_path)
            metadata = {
                "backup_id": backup_id,
                "project_id": project_id,
                "project_title": manifest["project_title"],
                "created_at": created_at,
                "reason": reason,
                "status": "available",
                "format_version": BACKUP_FORMAT_VERSION,
                "app_version": APP_VERSION,
                "schema_version": SCHEMA_VERSION,
                "archive_sha256": archive_sha,
                "archive_bytes": final_path.stat().st_size,
                "file_path": str(final_path),
                "collection_counts": counts,
            }
            await db.project_backups.insert_one(metadata)
            await self._apply_retention(db, project_id)
            return {**_manifest_public(manifest), "archive_sha256": archive_sha, "archive_bytes": metadata["archive_bytes"], "status": "available"}
        except Exception:
            temp_path.unlink(missing_ok=True)
            final_path.unlink(missing_ok=True)
            raise

    async def _apply_retention(self, db, project_id: ObjectId) -> None:
        retain = max(1, int(settings.backup_retention_count))
        stale = await db.project_backups.find(
            {"project_id": project_id, "status": "available"}
        ).sort("created_at", -1).skip(retain).to_list(length=None)
        for record in stale:
            try:
                path = _safe_path(str(record.get("file_path") or ""))
                path.unlink(missing_ok=True)
                await db.project_backups.update_one(
                    {"_id": record["_id"]},
                    {"$set": {"status": "expired", "expired_at": datetime.utcnow()}},
                )
            except (OSError, BackupError):
                await db.project_backups.update_one(
                    {"_id": record["_id"]},
                    {"$set": {"retention_error": True}},
                )

    async def list(self, db, project_id: ObjectId) -> list[Dict[str, Any]]:
        rows = await db.project_backups.find({"project_id": project_id}).sort("created_at", -1).to_list(length=100)
        return [
            {
                "backup_id": row["backup_id"],
                "project_id": str(row["project_id"]),
                "project_title": row.get("project_title", "Untitled Project"),
                "created_at": row["created_at"].isoformat() + "Z",
                "reason": row.get("reason", "manual"),
                "status": row.get("status", "available"),
                "app_version": row.get("app_version", "unknown"),
                "schema_version": row.get("schema_version", 0),
                "archive_bytes": row.get("archive_bytes", 0),
                "document_count": sum((row.get("collection_counts") or {}).values()) + 1,
                "collection_counts": row.get("collection_counts") or {},
            }
            for row in rows
        ]

    async def _record(self, db, backup_id: str) -> Dict[str, Any]:
        record = await db.project_backups.find_one({"backup_id": backup_id})
        if not record or record.get("status") != "available":
            raise BackupError("This backup is no longer available.")
        return record

    async def file_path(self, db, backup_id: str) -> Path:
        record = await self._record(db, backup_id)
        path = _safe_path(str(record.get("file_path") or ""))
        if not path.is_file():
            raise BackupError("The backup file is missing. Your current project is unchanged.")
        return path

    async def import_archive(
        self,
        db,
        chunks: AsyncIterator[bytes],
        *,
        original_filename: str = "imported-backup",
    ) -> Dict[str, Any]:
        root = backup_root()
        root.mkdir(parents=True, exist_ok=True)
        temp = root / f".import-{uuid4().hex}.tmp"
        final: Path | None = None
        byte_count = 0
        digest = hashlib.sha256()
        try:
            with temp.open("wb") as stream:
                async for chunk in chunks:
                    if not chunk:
                        continue
                    byte_count += len(chunk)
                    if byte_count > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                        raise BackupError("This backup file is too large to import safely.")
                    stream.write(chunk)
                    digest.update(chunk)
            try:
                with zipfile.ZipFile(temp, "r") as archive:
                    manifest = json.loads(archive.read("manifest.json"))
            except (zipfile.BadZipFile, KeyError, json.JSONDecodeError) as exc:
                raise BackupError("This file is not a valid NovelForge project backup.") from exc
            if manifest.get("product") != "NovelForge" or not manifest.get("backup_id"):
                raise BackupError("This file is not a valid NovelForge project backup.")
            backup_id = str(manifest["backup_id"])
            existing = await db.project_backups.find_one({"backup_id": backup_id})
            archive_sha = digest.hexdigest()
            if existing:
                if existing.get("archive_sha256") == archive_sha and existing.get("status") == "available":
                    temp.unlink(missing_ok=True)
                    return await self.validate(db, backup_id)
                raise BackupError("A different backup with the same identity already exists. Nothing was imported.")
            project_id = str(manifest.get("project_id") or "")
            if not ObjectId.is_valid(project_id):
                raise BackupError("The backup does not contain a valid project identity.")
            try:
                source_created_at = (
                    datetime.fromisoformat(str(manifest.get("created_at")).replace("Z", "+00:00")).replace(tzinfo=None)
                    if manifest.get("created_at")
                    else datetime.utcnow()
                )
            except ValueError as exc:
                raise BackupError("The backup creation date is invalid.") from exc
            final = root / f"{_slug(str(manifest.get('project_title') or original_filename))}-imported-{backup_id[:8]}{BACKUP_EXTENSION}"
            os.replace(temp, final)
            try:
                await db.project_backups.insert_one({
                    "backup_id": backup_id,
                    "project_id": ObjectId(project_id),
                    "project_title": str(manifest.get("project_title") or "Imported Project"),
                    "created_at": source_created_at,
                    "imported_at": datetime.utcnow(),
                    "reason": "imported recovery backup",
                    "status": "available",
                    "format_version": int(manifest.get("format_version") or 0),
                    "app_version": str(manifest.get("app_version") or "unknown"),
                    "schema_version": int(manifest.get("schema_version") or 0),
                    "archive_sha256": archive_sha,
                    "archive_bytes": byte_count,
                    "file_path": str(final),
                    "collection_counts": manifest.get("collection_counts") or {},
                })
            except Exception:
                final.unlink(missing_ok=True)
                raise
            try:
                validated = await self.validate(db, backup_id)
            except Exception:
                final.unlink(missing_ok=True)
                await db.project_backups.delete_one({"backup_id": backup_id})
                raise
            return {**validated, "imported": True}
        except Exception:
            temp.unlink(missing_ok=True)
            raise

    async def validate(self, db, backup_id: str) -> Dict[str, Any]:
        record = await self._record(db, backup_id)
        path = await self.file_path(db, backup_id)
        actual_archive_sha = _sha256_file(path)
        if actual_archive_sha != record.get("archive_sha256"):
            raise BackupError("The backup file has changed or is damaged. Restore was not started.")
        try:
            with zipfile.ZipFile(path, "r") as archive:
                total_size = sum(item.file_size for item in archive.infolist())
                if total_size > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                    raise BackupError("The backup is too large to validate safely.")
                manifest = json.loads(archive.read("manifest.json"))
                if manifest.get("product") != "NovelForge":
                    raise BackupError("This file is not a NovelForge project backup.")
                if int(manifest.get("format_version") or 0) > BACKUP_FORMAT_VERSION:
                    raise BackupError("This backup was created by a newer, incompatible NovelForge version.")
                if int(manifest.get("schema_version") or 0) > SCHEMA_VERSION:
                    raise BackupError("Update NovelForge before restoring this newer project backup.")
                if str(manifest.get("backup_id") or "") != backup_id:
                    raise BackupError("The backup identity does not match its recovery record.")
                if not ObjectId.is_valid(str(manifest.get("project_id") or "")):
                    raise BackupError("The backup project identity is invalid.")
                collection_counts = manifest.get("collection_counts") or {}
                invalid_collections = sorted(set(collection_counts) - set(PROJECT_OWNED_COLLECTIONS))
                if invalid_collections:
                    raise BackupError("The backup contains unsupported project data and cannot be restored safely.")
                allowed_entries = {"project.ndjson", *{f"collections/{name}.ndjson" for name in collection_counts}}
                if set((manifest.get("entries") or {}).keys()) != allowed_entries:
                    raise BackupError("The backup manifest contains unexpected data and cannot be restored safely.")
                for entry_name, expected in (manifest.get("entries") or {}).items():
                    if entry_name not in archive.namelist():
                        raise BackupError(f"The backup is incomplete: {entry_name} is missing.")
                    digest = hashlib.sha256()
                    size = 0
                    documents = 0
                    with archive.open(entry_name) as stream:
                        for line in stream:
                            if not line.strip():
                                continue
                            digest.update(line)
                            size += len(line)
                            documents += 1
                            json_util.loads(line.decode("utf-8"))
                    if digest.hexdigest() != expected.get("sha256") or size != expected.get("bytes") or documents != expected.get("documents"):
                        raise BackupError(f"The backup is damaged: {entry_name} did not pass its checksum.")
                    if entry_name == "project.ndjson" and documents != 1:
                        raise BackupError("The backup project record is incomplete.")
                    if entry_name.startswith("collections/"):
                        collection_name = entry_name.removeprefix("collections/").removesuffix(".ndjson")
                        if documents != int(collection_counts.get(collection_name) or 0):
                            raise BackupError(f"The backup count for {collection_name} is inconsistent.")
        except zipfile.BadZipFile as exc:
            raise BackupError("The backup archive is damaged and cannot be restored.") from exc
        except (KeyError, json.JSONDecodeError) as exc:
            raise BackupError("The backup manifest is missing or invalid.") from exc
        return {**_manifest_public(manifest), "valid": True, "compatible": True, "archive_bytes": path.stat().st_size}

    @staticmethod
    def _replace_references(value: Any, identity_map: Dict[str, ObjectId]) -> Any:
        if isinstance(value, ObjectId):
            return identity_map.get(str(value), value)
        if isinstance(value, str) and value in identity_map:
            return str(identity_map[value])
        if isinstance(value, list):
            return [ProjectBackupService._replace_references(item, identity_map) for item in value]
        if isinstance(value, dict):
            return {key: ProjectBackupService._replace_references(item, identity_map) for key, item in value.items()}
        return value

    async def restore_as_copy(
        self,
        db,
        backup_id: str,
        *,
        title: str = "",
        request_id: str = "",
    ) -> Dict[str, Any]:
        preview = await self.validate(db, backup_id)
        path = await self.file_path(db, backup_id)
        new_project_id = ObjectId()
        identity_map: Dict[str, ObjectId] = {preview["project_id"]: new_project_id}
        inserted_counts: Dict[str, int] = {}
        operation_id = str(uuid4())
        started_at = datetime.utcnow()
        normalized_request_id = request_id.strip()
        operation = {
            "operation_id": operation_id,
            "backup_id": backup_id,
            "source_project_id": preview["project_id"],
            "target_project_id": new_project_id,
            "status": "running",
            "created_at": started_at,
        }
        if normalized_request_id:
            operation["request_id"] = normalized_request_id
            operation["requested_title"] = title.strip()
        try:
            await db.restore_operations.insert_one(operation)
        except DuplicateKeyError:
            # A response may be lost after the original restore commits. Reuse
            # that operation instead of creating another restored project.
            for _ in range(1800):
                existing = await db.restore_operations.find_one(
                    {"request_id": normalized_request_id}
                )
                if existing and (
                    existing.get("backup_id") != backup_id
                    or str(existing.get("requested_title") or "") != title.strip()
                ):
                    raise BackupError(
                        "This recovery request was already used for a different restore. Start a new restore preview."
                    )
                if existing and existing.get("status") == "completed" and existing.get("result"):
                    return existing["result"]
                if existing and existing.get("status") == "failed":
                    raise BackupError(
                        "The earlier restore attempt failed safely. The original project is unchanged."
                    )
                await asyncio.sleep(0.1)
            raise BackupError(
                "This restore is still running. Wait a moment and retry; NovelForge will reuse the same result."
            )
        try:
            with zipfile.ZipFile(path, "r") as archive:
                manifest = json.loads(archive.read("manifest.json"))
                for entry_name in manifest.get("entries", {}):
                    if entry_name == "project.ndjson":
                        continue
                    with archive.open(entry_name) as stream:
                        for line in stream:
                            if not line.strip():
                                continue
                            document = json_util.loads(line.decode("utf-8"))
                            if isinstance(document, dict) and isinstance(document.get("_id"), ObjectId):
                                identity_map[str(document["_id"])] = ObjectId()

                with archive.open("project.ndjson") as stream:
                    project = json_util.loads(next(line for line in stream if line.strip()).decode("utf-8"))
                project = self._replace_references(project, identity_map)
                project["_id"] = new_project_id
                project["title"] = title.strip() or f"{preview['project_title']} (Restored)"
                if project.get("status") == "trashed":
                    project["status"] = "draft"
                project["restored_from_backup_id"] = backup_id
                project["restored_from_project_id"] = preview["project_id"]
                project["schema_version"] = SCHEMA_VERSION
                project["app_version"] = APP_VERSION
                project["created_at"] = started_at
                project["updated_at"] = started_at
                await db.projects.insert_one(project)

                for collection_name, expected_count in (manifest.get("collection_counts") or {}).items():
                    if collection_name in DERIVED_NATIVE_INDEX_COLLECTIONS:
                        # Old backups may contain V1/Phase A derived state. It
                        # is intentionally discarded because all identifiers
                        # were remapped and owners are the restore authority.
                        continue
                    entry_name = f"collections/{collection_name}.ndjson"
                    batch = []
                    with archive.open(entry_name) as stream:
                        for line in stream:
                            if not line.strip():
                                continue
                            document = self._replace_references(
                                json_util.loads(line.decode("utf-8")), identity_map
                            )
                            document["project_id"] = new_project_id
                            batch.append(document)
                            if len(batch) >= 250:
                                await db[collection_name].insert_many(batch, ordered=True)
                                inserted_counts[collection_name] = inserted_counts.get(collection_name, 0) + len(batch)
                                batch = []
                        if batch:
                            await db[collection_name].insert_many(batch, ordered=True)
                            inserted_counts[collection_name] = inserted_counts.get(collection_name, 0) + len(batch)
                    if inserted_counts.get(collection_name, 0) != expected_count:
                        raise BackupError(f"Restore verification failed for {collection_name}. The restored copy was removed.")

            if not await db.story_bibles.find_one({"project_id": new_project_id}):
                await rebuild_story_bible(db, str(new_project_id))
            from app.services.memory_incremental_index_service import memory_incremental_index_service
            await memory_incremental_index_service.mark_needs_verification(
                db, str(new_project_id), "restored_project_requires_index_rebuild"
            )
            audit = await audit_project_database(db, str(new_project_id))
            result = {
                "operation_id": operation_id,
                "backup_id": backup_id,
                "project_id": str(new_project_id),
                "project_title": project["title"],
                "status": "completed",
                "restored_as_copy": True,
                "original_project_unchanged": True,
                "collection_counts": inserted_counts,
                "integrity": audit,
            }
            await db.restore_operations.update_one(
                {"operation_id": operation_id},
                {"$set": {
                    "status": "completed",
                    "finished_at": datetime.utcnow(),
                    "inserted_counts": inserted_counts,
                    "integrity_status": audit["status"],
                    "result": result,
                }},
            )
            return result
        except Exception as exc:
            await project_lifecycle_service.purge(db, new_project_id)
            await db.restore_operations.update_one(
                {"operation_id": operation_id},
                {"$set": {
                    "status": "failed",
                    "finished_at": datetime.utcnow(),
                    "error_type": type(exc).__name__,
                    "rolled_back": True,
                }},
            )
            raise


project_backup_service = ProjectBackupService()
