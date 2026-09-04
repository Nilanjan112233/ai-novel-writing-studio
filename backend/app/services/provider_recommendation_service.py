"""Context-aware provider and model recommendations."""
from __future__ import annotations

from typing import Dict, List

from app.services.model_registry_service import ModelInfo, model_registry_service


TASK_TAGS = {
    "routing": ["fast", "cheap"],
    "brainstorming": ["free", "fast"],
    "character": ["large-context", "reasoning"],
    "critic": ["reasoning", "free"],
    "continuity": ["large-context", "reasoning"],
    "themes": ["reasoning"],
    "architect": ["large-context", "reasoning"],
    "drafting": ["drafting", "premium"],
}

# Tier is a routing policy label, not a permanent model assignment. Provider
# validation, author overrides, and failover remain authoritative at runtime.
TASK_TIERS = {
    "routing": "lightweight",
    "classification": "lightweight",
    "extraction": "lightweight",
    "summarization": "lightweight",
    "brainstorming": "cheap",
    "character": "cheap",
    "critic": "cheap",
    "continuity": "strong",
    "architect": "strong",
    "drafting": "strong",
    "revision": "strong",
}


class ProviderRecommendationService:
    async def recommend(
        self,
        *,
        task_type: str,
        budget_preference: str = "balanced",
        quality_preference: str = "balanced",
        latency_preference: str = "balanced",
        context_tokens: int = 0,
        tier: str | None = None,
    ) -> Dict[str, object]:
        models = await model_registry_service.get_verified_models()
        if not models:
            raise RuntimeError("No verified model available")
        resolved_tier = tier or TASK_TIERS.get(task_type, "lightweight")
        tags = set(TASK_TAGS.get(task_type, ["fast"]))
        if resolved_tier == "lightweight":
            tags.update({"fast", "cheap"})
        elif resolved_tier == "cheap":
            tags.add("cheap")
        elif resolved_tier in {"strong", "premium"}:
            tags.add("reasoning")
        if budget_preference == "cheap":
            tags.add("free")
        if quality_preference == "high":
            tags.add("reasoning")
        if latency_preference == "fast":
            tags.add("fast")
        if context_tokens > 100000:
            tags.add("large-context")

        scored: List[tuple[int, ModelInfo]] = []
        for model in models:
            score = len(tags & set(model.tags))
            if task_type in model.recommended_for:
                score += 3
            if model.free_tier and budget_preference == "cheap":
                score += 2
            if model.supports_large_context and context_tokens > 100000:
                score += 3
            scored.append((score, model))
        scored.sort(key=lambda item: item[0], reverse=True)
        best = scored[0][1]
        alternatives = [model.model_dump() for _, model in scored[1:4]]
        return {
            "provider": best.provider,
            "model": best.model_id,
            "display_name": best.display_name,
            "reason": f"Best match for {task_type} with tags {', '.join(sorted(tags))}.",
            "task_tier": resolved_tier,
            "alternatives": alternatives,
        }


provider_recommendation_service = ProviderRecommendationService()
