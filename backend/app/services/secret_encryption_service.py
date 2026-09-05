"""Encryption helpers for provider credentials stored in MongoDB."""
from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path
from typing import Any, Dict

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class SecretEncryptionService:
    def __init__(self) -> None:
        self._fernet: Fernet | None = None

    def _key(self) -> bytes:
        configured = (settings.settings_encryption_key or "").strip()
        if configured:
            try:
                decoded = base64.urlsafe_b64decode(configured.encode("ascii"))
                if len(decoded) == 32:
                    return configured.encode("ascii")
            except Exception:
                pass
            return base64.urlsafe_b64encode(
                hashlib.sha256(configured.encode("utf-8")).digest()
            )

        key_path = Path(
            settings.settings_key_file
            or (Path.home() / ".novelforge" / "settings.key")
        ).expanduser()
        if key_path.exists():
            return key_path.read_bytes().strip()
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key = Fernet.generate_key()
        key_path.write_bytes(key)
        try:
            os.chmod(key_path, 0o600)
        except OSError:
            pass
        return key

    def _cipher(self) -> Fernet:
        if self._fernet is None:
            self._fernet = Fernet(self._key())
        return self._fernet

    def encrypt(self, value: str) -> str:
        if not value:
            return ""
        return self._cipher().encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, value: str) -> str:
        if not value:
            return ""
        try:
            return self._cipher().decrypt(value.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError) as exc:
            raise RuntimeError(
                "Provider credential cannot be decrypted with the configured key"
            ) from exc

    def prepare_provider_storage(
        self,
        providers: Dict[str, Any],
        existing: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        existing = existing or {}
        prepared: Dict[str, Any] = {}
        for provider, raw_config in (providers or {}).items():
            config = dict(raw_config or {})
            prior = dict(existing.get(provider) or {})
            supplied_key = str(config.pop("api_key", "") or "")
            clear_key = bool(config.pop("clear_api_key", False))
            encrypted = str(config.get("api_key_encrypted") or "")
            if clear_key:
                encrypted = ""
            elif supplied_key and supplied_key != "***redacted***":
                encrypted = self.encrypt(supplied_key)
            elif not encrypted:
                encrypted = str(prior.get("api_key_encrypted") or "")
            config["api_key_encrypted"] = encrypted
            config["configured"] = bool(encrypted)
            prepared[provider] = config
        for provider, raw_config in existing.items():
            if provider not in prepared:
                prepared[provider] = dict(raw_config or {})
        return prepared

    def runtime_providers(self, providers: Dict[str, Any]) -> Dict[str, Any]:
        runtime: Dict[str, Any] = {}
        for provider, raw_config in (providers or {}).items():
            config = dict(raw_config or {})
            encrypted = str(config.pop("api_key_encrypted", "") or "")
            config["api_key"] = self.decrypt(encrypted) if encrypted else ""
            config["configured"] = bool(encrypted)
            runtime[provider] = config
        return runtime

    def public_providers(self, providers: Dict[str, Any]) -> Dict[str, Any]:
        public: Dict[str, Any] = {}
        for provider, raw_config in (providers or {}).items():
            config = dict(raw_config or {})
            encrypted = str(config.pop("api_key_encrypted", "") or "")
            config.pop("api_key", None)
            config["configured"] = bool(encrypted)
            public[provider] = config
        return public


secret_encryption_service = SecretEncryptionService()


async def migrate_provider_secrets(db) -> int:
    """Encrypt legacy plaintext provider keys in the canonical settings row."""
    document = await db.app_settings.find_one({"_id": "global_settings"})
    if not document:
        return 0
    providers = document.get("providers") or {}
    prepared = secret_encryption_service.prepare_provider_storage(
        providers,
        providers,
    )
    if prepared == providers:
        return 0
    await db.app_settings.update_one(
        {"_id": "global_settings"},
        {"$set": {"providers": prepared}},
    )
    return 1
