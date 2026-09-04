"""Real-inference model health persistence and provider-wide verification."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List

from app.services.model_registry_service import model_registry_service, normalize_provider


class ModelHealthService:
    async def record_result(self, db, result: Dict[str, Any]) -> Dict[str, Any]:
        provider = normalize_provider(result.get("provider", ""))
        model = result.get("model", "")
        document = {
            "provider": provider,
            "model": model,
            "last_checked": datetime.utcnow(),
            "latency": int(result.get("latency_ms") or 0),
            "success": bool(result.get("success")),
            "tokens_used": int(result.get("tokens_used") or 0),
            "error": result.get("error"),
            "error_type": result.get("error_type"),
            "request_payload": result.get("request_payload"),
            "response_payload": result.get("response_payload") or result.get("response"),
        }
        await db.provider_model_health.update_one(
            {"provider": provider, "model": model},
            {"$set": document},
            upsert=True,
        )
        return document

    async def verify_provider(self, db, provider: str, gateway) -> Dict[str, Any]:
        normalized = normalize_provider(provider)
        models = await model_registry_service.get_models(normalized)
        semaphore = asyncio.Semaphore(4)

        async def verify(model) -> Dict[str, Any]:
            async with semaphore:
                result = await gateway.test_model(normalized, model.model_id, db=db)
                await self.record_result(db, result)
                return {
                    "provider": normalized,
                    "model": model.model_id,
                    "display_name": model.display_name,
                    "success": bool(result.get("success")),
                    "working": bool(result.get("success")),
                    "latency": int(result.get("latency_ms") or 0),
                    "tokens_used": int(result.get("tokens_used") or 0),
                    "error_type": result.get("error_type"),
                    "error": result.get("error"),
                    "last_checked": datetime.utcnow(),
                }

        results: List[Dict[str, Any]] = await asyncio.gather(*(verify(model) for model in models))
        return {
            "provider": normalized,
            "total": len(results),
            "working": sum(1 for result in results if result["success"]),
            "failed": sum(1 for result in results if not result["success"]),
            "results": results,
        }

    async def get_results(self, db, provider: str | None = None) -> List[Dict[str, Any]]:
        normalized = normalize_provider(provider or "")
        query = {"provider": normalized} if normalized else {}
        documents = await db.provider_model_health.find(query).sort(
            [("success", -1), ("latency", 1), ("model", 1)]
        ).to_list(length=5000)
        for document in documents:
            document["_id"] = str(document["_id"])
        return documents


model_health_service = ModelHealthService()
