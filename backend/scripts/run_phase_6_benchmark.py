"""Reproducible 500-chapter Phase 6 full/cached/incremental benchmark."""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from time import perf_counter

from bson import ObjectId

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import Database
from app.services.narrative_analysis_engine import narrative_analysis_engine


async def main() -> None:
    await Database.connect()
    db = Database.get_db()
    pid = ObjectId()
    project_id = str(pid)
    now = datetime.utcnow()
    await db.projects.insert_one({
        "_id": pid, "title": "Phase 6 Performance Benchmark",
        "premise": "A bounded synthetic project used only for Narrative Analysis benchmarking.",
        "genre": "Benchmark", "created_at": now, "updated_at": now,
    })
    await db.chapter_intelligence.insert_many([{
        "project_id": pid, "intelligence_id": f"benchmark-{number}",
        "chapter_plan_id": f"plan-{number}", "chapter_draft_id": f"draft-{number}",
        "chapter_draft_version": 1, "chapter_number": number,
        "title": f"Chapter {number}", "chapter_summary": f"Mara advances event {number}.",
        "important_events": [
            f"event-{number}",
            *( [f"benchmark-{number - 1}"] if number > 1 else [] ),
        ], "characters_present": ["Mara", "Soren"],
        "character_changes": [], "future_obligations": [], "mysteries_resolved": [],
        "foreshadowing_resolved": [], "word_count": 1700, "active": True,
        "updated_at": now,
    } for number in range(1, 501)])
    try:
        started = perf_counter()
        full = await narrative_analysis_engine.analyze(db, project_id, force=True)
        full_seconds = perf_counter() - started
        started = perf_counter()
        cached = await narrative_analysis_engine.analyze(db, project_id)
        cached_seconds = perf_counter() - started
        await db.chapter_intelligence.update_one(
            {"project_id": pid, "intelligence_id": "benchmark-250"},
            {"$set": {"chapter_summary": "Mara changes the midpoint event.", "updated_at": datetime.utcnow()}},
        )
        started = perf_counter()
        incremental = await narrative_analysis_engine.analyze(db, project_id)
        incremental_seconds = perf_counter() - started
        print(json.dumps({
            "chapters": 500,
            "full": {"wall_seconds": round(full_seconds, 4), **full["snapshot"]["stats"]},
            "cached": {"wall_seconds": round(cached_seconds, 4), **cached["snapshot"]["stats"]},
            "single_chapter_edit": {"wall_seconds": round(incremental_seconds, 4), **incremental["snapshot"]["stats"]},
        }, indent=2))
    finally:
        for collection in [
            "chapter_intelligence", "narrative_nodes", "narrative_edges",
            "narrative_findings", "narrative_analysis_snapshots", "projects",
        ]:
            await db[collection].delete_many({"project_id": pid} if collection != "projects" else {"_id": pid})
        await Database.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
