"""Compatibility wrapper for provider-wide real inference verification."""
from __future__ import annotations

from typing import Any, Dict

from app.services.model_health_service import model_health_service
from app.services.provider_gateway import provider_gateway


class GeminiValidationService:
    async def validate_provider(self, db, provider: str = "gemini", refresh: bool = False) -> Dict[str, Any]:
        return await model_health_service.verify_provider(db, provider, provider_gateway)


gemini_validation_service = GeminiValidationService()
