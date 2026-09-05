"""Observability and cost accounting for orchestration cycles."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from bson import ObjectId


MODEL_COSTS_PER_1K = {
    "mock": 0.0,
    "groq": 0.0002,
    "gemini": 0.0004,
    "openrouter": 0.001,
    "openai": 0.005,
    "claude": 0.006,
    "ollama": 0.0,
    "local": 0.0,
}


def estimate_cost(tokens: int, provider: str, model: str = "") -> float:
    provider_key = (provider or "mock").lower()
    rate = MODEL_COSTS_PER_1K.get(provider_key, MODEL_COSTS_PER_1K["openrouter"])
    if "opus" in (model or "").lower():
        rate *= 4
    if "sonnet" in (model or "").lower():
        rate *= 2
    return round((tokens / 1000) * rate, 6)


class ObservabilityService:
    async def record_observation(self, db, project_id: str, cycle_number: int, event_type: str, payload: Dict[str, Any]) -> None:
        await db.observability_events.insert_one({
            "project_id": ObjectId(project_id),
            "cycle_number": cycle_number,
            "event_type": event_type,
            "payload": payload,
            "created_at": datetime.utcnow(),
        })


observability_service = ObservabilityService()
