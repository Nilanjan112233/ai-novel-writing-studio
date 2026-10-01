"""Create the provider_models discovery cache."""
from __future__ import annotations


async def migrate_provider_models(db) -> None:
    await db.provider_models.create_index(
        [("provider", 1), ("model_id", 1)],
        unique=True,
        name="provider_models_provider_model_id",
    )
    await db.provider_models.create_index(
        [("provider", 1), ("discovered_at", -1)],
        name="provider_models_provider_discovered_at",
    )
    await db.provider_status.create_index("provider", unique=True, name="provider_status_provider")
    await db.provider_model_health.create_index(
        [("provider", 1), ("model", 1)],
        unique=True,
        name="provider_model_health_provider_model",
    )
    await db.provider_model_health.create_index(
        [("provider", 1), ("success", -1), ("latency", 1)],
        name="provider_model_health_provider_success_latency",
    )
