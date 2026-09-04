"""Provider model discovery and provider_models persistence."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from app.core.database import Database
from app.services.provider_registry import MOCK_MODELS, configured_models, normalize_provider
from app.services.provider_validation_service import ProviderValidationError, provider_validation_service


class ModelDiscoveryService:
    async def discover(self, provider: str, *, api_key: str | None = None) -> Dict[str, Any]:
        normalized = normalize_provider(provider)
        now = datetime.utcnow()
        try:
            validation = await provider_validation_service.validate(normalized, api_key=api_key)
            models = self._parse_models(normalized, validation.get("catalog") or {})
            await self._replace_models(normalized, models, now)
            if api_key:
                settings = await provider_validation_service.settings_with_api_key(normalized, api_key)
                await provider_validation_service.save_settings(settings)
            await self._record_status(
                normalized,
                status="online",
                key_valid=True,
                discovery_succeeded=True,
                discovered_model_count=len(models),
                error_type=None,
                error=None,
                checked_at=now,
            )
            return {
                "provider": normalized,
                "status": "online",
                "discovered_model_count": len(models),
                "discovered_at": now,
                "models": models,
            }
        except ProviderValidationError as exc:
            await self._record_status(
                normalized,
                status="offline",
                key_valid=False if exc.error_type == "INVALID_API_KEY" else None,
                discovery_succeeded=False,
                discovered_model_count=await self.count(normalized),
                error_type=exc.error_type,
                error=str(exc),
                checked_at=now,
            )
            raise

    def _parse_models(self, provider: str, catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
        if provider == "anthropic":
            return configured_models("anthropic")
        if provider == "mock":
            return [dict(item) for item in MOCK_MODELS]

        raw_models = catalog.get("models", []) if provider == "gemini" else catalog.get("data", [])
        models: List[Dict[str, Any]] = []
        for item in raw_models:
            if provider == "gemini":
                raw_name = item.get("name", "")
                model_id = raw_name.split("/", 1)[-1]
                methods = item.get("supportedGenerationMethods", [])
                lowered = model_id.lower()
                if "generateContent" not in methods or not lowered.startswith("gemini-"):
                    continue
                if any(kind in lowered for kind in ["embedding", "aqa", "imagen", "image", "tts", "veo", "computer-use", "robotics"]):
                    continue
                models.append({
                    "model_id": model_id,
                    "model_name": item.get("displayName") or model_id,
                    "context_window": item.get("inputTokenLimit"),
                    "supports_large_context": (item.get("inputTokenLimit") or 0) >= 100000,
                    "supports_multimodal": True,
                    "supports_streaming": "streamGenerateContent" in methods,
                    "recommended_for": ["gemini"],
                    "tags": ["large-context", "fast"] if "flash" in lowered else ["large-context", "reasoning"],
                })
                continue

            model_id = item.get("id")
            if not model_id:
                continue
            pricing = item.get("pricing") or {}
            prompt_price = self._number(pricing.get("prompt"))
            completion_price = self._number(pricing.get("completion"))
            context_window = item.get("context_length") or item.get("context_window")
            models.append({
                "model_id": model_id,
                "model_name": item.get("name") or model_id,
                "context_window": context_window,
                "pricing_input": prompt_price,
                "pricing_output": completion_price,
                "free_tier": model_id.endswith(":free") or (
                    prompt_price == 0 and completion_price == 0 and provider == "openrouter"
                ),
                "supports_large_context": (context_window or 0) >= 100000,
                "recommended_for": [provider],
                "tags": ["free"] if model_id.endswith(":free") else [],
            })
        return models

    @staticmethod
    def _number(value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def _replace_models(self, provider: str, models: List[Dict[str, Any]], discovered_at: datetime) -> None:
        db = Database.get_db()
        await db.provider_models.delete_many({"provider": provider})
        model_ids = [model["model_id"] for model in models]
        await db.provider_model_health.delete_many({
            "provider": provider,
            "model": {"$nin": model_ids},
        })
        if not models:
            return
        documents = [
            {
                **model,
                "provider": provider,
                "model_id": model["model_id"],
                "model_name": model.get("model_name") or model["model_id"],
                "discovered_at": discovered_at,
            }
            for model in models
        ]
        await db.provider_models.insert_many(documents)

    async def _record_status(self, provider: str, **fields: Any) -> None:
        db = Database.get_db()
        await db.provider_status.update_one(
            {"provider": provider},
            {"$set": {"provider": provider, **fields}},
            upsert=True,
        )

    async def count(self, provider: str) -> int:
        return await Database.get_db().provider_models.count_documents({"provider": normalize_provider(provider)})


model_discovery_service = ModelDiscoveryService()
