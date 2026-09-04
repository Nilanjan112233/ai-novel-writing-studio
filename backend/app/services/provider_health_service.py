"""Provider status derived from discovery and per-model health checks."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from app.core.config import settings as app_config


def utc_day() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


class ProviderHealthService:
    async def record_success(
        self,
        db,
        provider: str,
        model: str,
        latency_ms: int,
        tokens_used: int,
        cost_usd: float = 0.0,
    ) -> None:
        day = utc_day()
        now = datetime.utcnow()
        await db.provider_health.update_one(
            {"provider": provider},
            {
                "$set": {
                    "provider": provider,
                    "status": "online",
                    "active_model": model,
                    "last_success_at": now,
                    "last_latency_ms": latency_ms,
                    "last_error": None,
                    "updated_at": now,
                },
                "$inc": {"success_count": 1},
            },
            upsert=True,
        )
        await db.provider_quota_usage.update_one(
            {"provider": provider, "day": day},
            {
                "$set": {"provider": provider, "day": day, "updated_at": now},
                "$inc": {"requests": 1, "tokens": tokens_used, "estimated_cost_usd": cost_usd},
            },
            upsert=True,
        )

    async def record_failure(self, db, provider: str, model: str, error_type: str, message: str) -> None:
        """A model failure can degrade a provider, but never marks it offline."""
        now = datetime.utcnow()
        await db.provider_health.update_one(
            {"provider": provider},
            {
                "$set": {
                    "provider": provider,
                    "status": "degraded",
                    "active_model": model,
                    "last_error": {"type": error_type, "message": message, "created_at": now},
                    "updated_at": now,
                },
                "$inc": {"failure_count": 1},
            },
            upsert=True,
        )

    async def health_snapshot(self, db) -> list[Dict[str, Any]]:
        discovery = await db.provider_status.find().to_list(length=100)
        runtime = await db.provider_health.find().to_list(length=100)
        usage = await db.provider_quota_usage.find({"day": utc_day()}).to_list(length=100)
        validations = await db.provider_model_health.find().to_list(length=5000)

        providers = {
            item.get("provider")
            for group in (discovery, runtime, validations)
            for item in group
            if item.get("provider")
        }
        usage_by_provider = {item.get("provider"): item for item in usage}
        discovery_by_provider = {item.get("provider"): item for item in discovery}
        runtime_by_provider = {item.get("provider"): item for item in runtime}

        snapshot: list[Dict[str, Any]] = []
        for provider in sorted(providers):
            if provider == "mock" and not app_config.use_mock_llm:
                continue
            discovered = discovery_by_provider.get(provider, {})
            health = runtime_by_provider.get(provider, {})
            discovery_succeeded = discovered.get("discovery_succeeded")
            if discovery_succeeded is False:
                status = "offline"
            elif discovery_succeeded is True:
                status = "online"
            else:
                status = health.get("status", "online") if provider in {"mock", "ollama"} else "untested"

            failed_models = [
                item for item in validations
                if item.get("provider") == provider and item.get("success") is False
            ]
            working_models = [
                item for item in validations
                if item.get("provider") == provider and item.get("success") is True
            ]
            if status == "online" and failed_models:
                status = "degraded"

            daily = {
                key: value
                for key, value in usage_by_provider.get(
                    provider,
                    {"requests": 0, "tokens": 0, "estimated_cost_usd": 0},
                ).items()
                if key != "_id"
            }
            item = {
                **{key: value for key, value in health.items() if key != "_id"},
                **{key: value for key, value in discovered.items() if key != "_id"},
                "provider": provider,
                "status": status,
                "daily_usage": daily,
                "failed_model_count": len(failed_models),
                "working_model_count": len(working_models),
            }
            if discovered.get("error"):
                item["last_error"] = {
                    "type": discovered.get("error_type", "PROVIDER_UNAVAILABLE"),
                    "message": discovered["error"],
                    "created_at": discovered.get("checked_at"),
                }
            snapshot.append(item)
        return snapshot


provider_health_service = ProviderHealthService()
