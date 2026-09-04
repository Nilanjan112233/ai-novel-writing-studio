"""Credential validation independent from model parsing and health checks."""
from __future__ import annotations

from typing import Any, Dict

import httpx

from app.services.ai_provider import ai_provider
from app.services.provider_registry import normalize_provider


class ProviderValidationError(Exception):
    def __init__(self, provider: str, error_type: str, message: str):
        super().__init__(message)
        self.provider = provider
        self.error_type = error_type


class ProviderValidationService:
    async def settings_with_api_key(self, provider: str, api_key: str) -> Dict[str, Any]:
        settings = await ai_provider.get_settings()
        providers = settings.setdefault("providers", {})
        config = dict(providers.get(provider, {}))
        config["api_key"] = api_key.strip()
        providers[provider] = config
        return settings

    async def save_settings(self, settings: Dict[str, Any]) -> None:
        if not await ai_provider.update_settings(settings):
            raise RuntimeError("Failed to persist provider credential")

    @staticmethod
    def _classify_exception(exc: Exception) -> str:
        if isinstance(exc, httpx.TimeoutException):
            return "TIMEOUT"
        if isinstance(exc, httpx.ConnectError):
            return "NETWORK_ERROR"
        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
            text = exc.response.text.lower()
            if status in {401, 403}:
                return "QUOTA_EXCEEDED" if "quota" in text or "exceeded" in text else "INVALID_API_KEY"
            if status == 400 and ("api key" in text or "invalid key" in text or "invalid_argument" in text):
                return "INVALID_API_KEY"
            if status == 429:
                return "QUOTA_EXCEEDED" if "quota" in text or "insufficient" in text else "RATE_LIMITED"
            if status >= 500:
                return "PROVIDER_UNAVAILABLE"
        return "PROVIDER_UNAVAILABLE"

    async def _api_key(self, provider: str, api_key: str | None) -> str:
        if api_key:
            return api_key.strip()
        settings = await ai_provider.get_settings()
        return str(settings.get("providers", {}).get(provider, {}).get("api_key", "")).strip()

    async def validate(
        self,
        provider: str,
        *,
        api_key: str | None = None,
    ) -> Dict[str, Any]:
        normalized = normalize_provider(provider)
        if normalized in {"mock", "ollama"}:
            return {"provider": normalized, "valid": True, "catalog": {}}

        key = await self._api_key(normalized, api_key)
        if not key:
            raise ProviderValidationError(normalized, "INVALID_API_KEY", f"{normalized} API key is not configured")

        requests = {
            "gemini": (
                "https://generativelanguage.googleapis.com/v1beta/models",
                {"x-goog-api-key": key},
            ),
            "openrouter": (
                "https://openrouter.ai/api/v1/models",
                {"Authorization": f"Bearer {key}"},
            ),
            "openai": (
                "https://api.openai.com/v1/models",
                {"Authorization": f"Bearer {key}"},
            ),
            "anthropic": (
                "https://api.anthropic.com/v1/models",
                {"x-api-key": key, "anthropic-version": "2023-06-01"},
            ),
            "groq": (
                "https://api.groq.com/openai/v1/models",
                {"Authorization": f"Bearer {key}"},
            ),
        }
        if normalized not in requests:
            raise ProviderValidationError(normalized, "PROVIDER_UNAVAILABLE", f"Unsupported provider: {normalized}")

        url, headers = requests[normalized]
        try:
            async with httpx.AsyncClient() as client:
                if normalized == "openrouter":
                    auth_response = await client.get(
                        "https://openrouter.ai/api/v1/auth/key",
                        headers=headers,
                        timeout=20,
                    )
                    auth_response.raise_for_status()
                response = await client.get(url, headers=headers, timeout=20)
                response.raise_for_status()
                catalog = response.json()
            return {"provider": normalized, "valid": True, "catalog": catalog}
        except Exception as exc:
            error_type = self._classify_exception(exc)
            raise ProviderValidationError(normalized, error_type, str(exc)) from exc


provider_validation_service = ProviderValidationService()
