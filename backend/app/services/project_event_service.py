"""Project-scoped change events used by the realtime workspace."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from bson import ObjectId


async def emit_project_event(
    db,
    project_id: str,
    event_type: str,
    *,
    cycle_number: int = 0,
    payload: Dict[str, Any] | None = None,
) -> str:
    created_at = datetime.utcnow()
    result = await db.project_events.insert_one({
        "project_id": ObjectId(project_id),
        "event_type": event_type,
        "cycle_number": int(cycle_number or 0),
        "payload": payload or {},
        "created_at": created_at,
    })
    # The project event is durable and is committed before the rebuildable
    # memory update is enqueued.  Indexing failure must never roll back or
    # overwrite the owning story state.
    try:
        from app.services.memory_incremental_index_service import memory_incremental_index_service
        await memory_incremental_index_service.notify_project_event(
            db,
            project_id,
            event_type,
            payload or {},
            project_event_id=str(result.inserted_id),
            created_at=created_at,
        )
    except Exception as exc:
        try:
            await memory_incremental_index_service.record_hook_failure(
                db, project_id, f"{type(exc).__name__}: {str(exc)}"
            )
        except Exception:
            pass
    return str(result.inserted_id)
