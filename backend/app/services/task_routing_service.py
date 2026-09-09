"""Task-aware provider selection over the existing provider gateway.

This module selects a tier and a validated-compatible model. It does not make
provider calls or create a second provider system; the gateway remains the
only execution path.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.services.ai_provider import ai_provider
from app.services.settings_service import settings_service


TASK_TIERS: Dict[str, str] = {
    "intent": "lightweight",
    "extraction": "lightweight",
    "planning_capture": "lightweight",
    "candidate_grouping": "lightweight",
    "chapter_summary": "lightweight",
    "evidence": "deterministic",
    "status": "deterministic",
    "story_studio": "cheap",
    "brainstorm": "cheap",
    "humanization": "lightweight",
    "continuity": "strong",
    "prose": "strong",
    "editorial": "strong",
}


class TaskRoutingService:
    async def _configured(self) -> Dict[str, Dict[str, Any]]:
        settings = await ai_provider.get_settings()
        return settings.get("providers") or {}

    async def select(
        self,
        task: str,
        *,
        fallbacks: List[Dict[str, str]] | None = None,
        requested_provider: str | None = None,
        requested_model: str | None = None,
    ) -> Dict[str, Any]:
        execution = await settings_service.get_execution_settings()
        configured = await self._configured()
        tier = TASK_TIERS.get(task, "strong")

        if requested_provider and requested_model:
            return {
                "tier": tier,
                "provider": requested_provider,
                "model": requested_model,
                "fallbacks": fallbacks or [],
                "reason": "explicit task assignment",
            }

        default_provider = str(execution.get("default_provider") or "gemini")
        default_model = str(execution.get("default_model") or "")
        strong_fallback = [{"provider": default_provider, "model": default_model}] if default_model else []
        configured_gemini_model = str((configured.get("gemini") or {}).get("model") or "").strip()
        lightweight_gemini_model = configured_gemini_model or "gemini-3.1-flash-lite"

        if tier == "deterministic":
            return {"tier": tier, "provider": "none", "model": "", "fallbacks": [], "reason": "application state is authoritative"}

        if tier == "lightweight":
            # Prefer an explicitly configured Gemini lightweight model. If the
            # provider is unavailable, use a free OpenRouter model, then the
            # configured default as the final gateway fallback.
            if configured.get("gemini", {}).get("api_key") or configured.get("gemini", {}).get("api_key_encrypted"):
                primary = {"provider": "gemini", "model": lightweight_gemini_model}
                safe = [*strong_fallback]
            elif configured.get("openrouter", {}).get("api_key") or configured.get("openrouter", {}).get("api_key_encrypted"):
                primary = {"provider": "openrouter", "model": "google/gemma-3-27b-it:free"}
                safe = [{"provider": "gemini", "model": "gemini-2.5-flash"}, *strong_fallback]
            else:
                primary = {"provider": default_provider, "model": default_model}
                safe = []
        elif tier == "cheap":
            if configured.get("gemini", {}).get("api_key") or configured.get("gemini", {}).get("api_key_encrypted"):
                primary = {"provider": "gemini", "model": lightweight_gemini_model}
                safe = [*strong_fallback]
            else:
                primary = {"provider": default_provider, "model": default_model}
                safe = [*strong_fallback]
        else:
            primary = {"provider": default_provider, "model": default_model}
            safe = fallbacks or []

        combined: List[Dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for item in [*safe, *(fallbacks or [])]:
            key = (str(item.get("provider") or ""), str(item.get("model") or ""))
            if key != (primary["provider"], primary["model"]) and key not in seen:
                seen.add(key)
                combined.append(item)
        return {
            "tier": tier,
            "provider": primary["provider"],
            "model": primary["model"],
            "fallbacks": combined,
            "reason": f"task tier: {tier}",
        }


task_routing_service = TaskRoutingService()
