"""Discovered model lookup plus runtime compatibility metadata."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.database import Database
from app.services.model_discovery_service import model_discovery_service
from app.services.provider_registry import configured_models, normalize_provider
from app.core.config import settings as app_config


class ModelInfo(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    provider: str
    model_id: str
    display_name: str
    discovered_at: Optional[datetime] = None
    context_window: Optional[int] = None
    pricing_input: Optional[float] = None
    pricing_output: Optional[float] = None
    supports_json: bool = True
    supports_streaming: bool = True
    supports_tools: bool = False
    supports_large_context: bool = False
    supports_reasoning: bool = False
    supports_multimodal: bool = False
    free_tier: bool = False
    recommended_for: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


def _model_info(provider: str, item: Dict[str, Any]) -> ModelInfo:
    payload = {key: value for key, value in item.items() if key != "_id"}
    payload["provider"] = normalize_provider(provider or payload.get("provider", ""))
    payload["display_name"] = payload.pop("model_name", None) or payload.get("display_name") or payload["model_id"]
    return ModelInfo(**payload)


class ModelRegistryService:
    def curated_models(self, provider: str | None = None) -> List[ModelInfo]:
        """Compatibility metadata for routing and existing saved runtime settings."""
        normalized = normalize_provider(provider or "")
        providers = [normalized] if normalized else ["gemini", "openrouter", "groq", "openai", "anthropic", "ollama"]
        if app_config.use_mock_llm and not normalized:
            providers.insert(0, "mock")
        return [
            _model_info(item_provider, item)
            for item_provider in providers
            for item in configured_models(item_provider)
        ]

    async def get_models(
        self,
        provider: str | None = None,
        refresh: bool = False,
        api_key: str | None = None,
    ) -> List[ModelInfo]:
        normalized = normalize_provider(provider or "")
        if refresh:
            if not normalized:
                raise ValueError("provider is required when refreshing model discovery")
            await model_discovery_service.discover(normalized, api_key=api_key)

        query = {"provider": normalized} if normalized else {}
        documents = await Database.get_db().provider_models.find(query).sort(
            [("provider", 1), ("model_name", 1)]
        ).to_list(length=5000)
        models = [_model_info(item.get("provider", ""), item) for item in documents]

        # Mock and local models are application-owned rather than remote catalogs.
        static_providers = {"ollama"}
        if app_config.use_mock_llm:
            static_providers.add("mock")
        requested_static = static_providers if not normalized else ({normalized} & static_providers)
        existing = {(model.provider, model.model_id) for model in models}
        for static_provider in requested_static:
            for model in self.curated_models(static_provider):
                if (model.provider, model.model_id) not in existing:
                    models.append(model)
        return sorted(models, key=lambda model: (model.provider, model.display_name.lower(), model.model_id))

    async def discover_models(self, provider: str, api_key: str | None = None) -> Dict[str, Any]:
        return await model_discovery_service.discover(provider, api_key=api_key)

    async def get_discovered_model(self, provider: str, model_id: str) -> Optional[ModelInfo]:
        normalized = normalize_provider(provider)
        if normalized in {"mock", "ollama"}:
            return next((model for model in self.curated_models(normalized) if model.model_id == model_id), None)
        document = await Database.get_db().provider_models.find_one(
            {"provider": normalized, "model_id": model_id}
        )
        return _model_info(normalized, document) if document else None

    async def get_model(self, provider: str, model_id: str) -> Optional[ModelInfo]:
        discovered = await self.get_discovered_model(provider, model_id)
        if discovered:
            return discovered
        normalized = normalize_provider(provider)
        return next((model for model in self.curated_models(normalized) if model.model_id == model_id), None)

    async def validate_discovered_model(self, provider: str, model_id: str) -> ModelInfo:
        model = await self.get_discovered_model(provider, model_id)
        if not model:
            raise ValueError(
                f"INVALID_MODEL: {normalize_provider(provider)} model '{model_id}' has not been discovered"
            )
        return model

    async def validate_model(self, provider: str, model_id: str) -> ModelInfo:
        """Preserve saved runtime assignments while discovery-backed UI replaces them."""
        model = await self.get_model(provider, model_id)
        if not model:
            raise ValueError(f"INVALID_MODEL: {normalize_provider(provider)} does not support model '{model_id}'")
        return model

    async def get_validation_results(self, provider: str | None = None) -> List[Dict[str, Any]]:
        normalized = normalize_provider(provider or "")
        query = {"provider": normalized} if normalized else {}
        db = Database.get_db()
        results = await db.provider_model_health.find(query).sort("last_checked", -1).to_list(length=5000)
        discovered = {
            (model.provider, model.model_id)
            for model in await self.get_models(normalized or None)
        }
        results = [
            item for item in results
            if (item.get("provider"), item.get("model")) in discovered
        ]
        for item in results:
            item["_id"] = str(item["_id"])
            item["working"] = bool(item.get("success"))
            item["latency_ms"] = item.get("latency")
            item["tested_at"] = item.get("last_checked")
            item["error_message"] = item.get("error")
            item["supports_json"] = False
            item["supports_streaming"] = False
        return results

    async def get_verified_models(self, provider: str | None = None) -> List[ModelInfo]:
        normalized = normalize_provider(provider or "")
        db = Database.get_db()
        query: Dict[str, Any] = {"success": True}
        if normalized:
            query["provider"] = normalized
        validations = await db.provider_model_health.find(query).sort("latency", 1).to_list(length=5000)
        models: List[ModelInfo] = []
        seen: set[tuple[str, str]] = set()
        for validation in validations:
            key = (validation.get("provider", ""), validation.get("model", ""))
            if key in seen:
                continue
            seen.add(key)
            model = await self.get_discovered_model(*key)
            if model:
                models.append(model)
        return models


model_registry_service = ModelRegistryService()

__all__ = ["ModelInfo", "model_registry_service", "normalize_provider"]
