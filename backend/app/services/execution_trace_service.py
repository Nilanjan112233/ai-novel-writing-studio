"""Execution tracing for every provider call."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from bson import ObjectId
from app.services.observability_service import estimate_cost


class ExecutionTraceService:
    async def mark_application_outcome(
        self,
        db,
        trace_id: str | None,
        **outcome: Any,
    ) -> None:
        """Attach product-stage success to an existing provider transport trace.

        A provider response can be HTTP-successful while parsing, authority
        validation, reference reconciliation, or persistence later fails.  Keeping
        these stages on the same trace makes that distinction operator-visible.
        """
        if not trace_id or not ObjectId.is_valid(str(trace_id)):
            return
        normalized = {
            key: value
            for key, value in outcome.items()
            if value is not None
        }
        normalized["recorded_at"] = datetime.utcnow()
        await db.execution_traces.update_one(
            {"_id": ObjectId(str(trace_id))},
            {
                "$set": {
                    "application_outcome": normalized,
                    "metadata.application_outcome": normalized,
                    "updated_at": datetime.utcnow(),
                }
            },
        )

    async def record(
        self,
        db,
        *,
        provider: str,
        model: str,
        prompt_tokens: int,
        response_tokens: int = 0,
        latency_ms: int = 0,
        status: str = "success",
        agent_name: Optional[str] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        retry_count: int = 0,
        fallback_used: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
        run_id: Optional[str] = None,
        cycle_number: Optional[int] = None,
        plan_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        request_id = str(ObjectId())
        meta = metadata or {}
        if kwargs:
            meta = {**meta, **kwargs}
        doc = {
            "request_id": request_id,
            "provider": provider,
            "model": model,
            "agent_name": agent_name,
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens,
            "total_tokens": prompt_tokens + response_tokens,
            "cost_usd": estimate_cost(prompt_tokens + response_tokens, provider, model),
            "response_length": int(meta.get("response_length", 0)),
            "latency_ms": latency_ms,
            "status": status,
            "error_type": error_type,
            "error_message": error_message,
            "retry_count": retry_count,
            "fallback_used": fallback_used,
            "metadata": meta,
            "created_at": datetime.utcnow(),
        }
        if project_id and ObjectId.is_valid(project_id):
            doc["project_id"] = ObjectId(project_id)
        if run_id and ObjectId.is_valid(run_id):
            doc["run_id"] = ObjectId(run_id)
        if plan_id and ObjectId.is_valid(plan_id):
            doc["plan_id"] = ObjectId(plan_id)
        if cycle_number is not None:
            doc["cycle_number"] = int(cycle_number)
        result = await db.execution_traces.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return doc

    async def latest(self, db, limit: int = 50) -> List[Dict[str, Any]]:
        traces = await db.execution_traces.find().sort("created_at", -1).to_list(length=max(1, min(limit, 200)))
        for trace in traces:
            trace["_id"] = str(trace["_id"])
            for field in ("project_id", "run_id", "plan_id"):
                if isinstance(trace.get(field), ObjectId):
                    trace[field] = str(trace[field])
        return traces


execution_trace_service = ExecutionTraceService()
