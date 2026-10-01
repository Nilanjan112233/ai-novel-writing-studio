"""Reproducible Phase 7 graph and contextual-intelligence benchmark."""
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
from app.services.narrative_interaction_service import narrative_interaction_service


async def main() -> None:
    await Database.connect()
    db = Database.get_db()
    pid = ObjectId()
    project_id = str(pid)
    now = datetime.utcnow()
    await db.projects.insert_one(
        {
            "_id": pid,
            "title": "Phase 7 Interaction Benchmark",
            "premise": "A synthetic 500-chapter project used only for read-path benchmarking.",
            "genre": "Benchmark",
            "created_at": now,
            "updated_at": now,
        }
    )
    await db.character_bibles.insert_many(
        [
            {
                "project_id": pid,
                "name": f"Character {number}",
                "role": "benchmark participant",
                "current_status": "active",
                "updated_at": now,
            }
            for number in range(1, 101)
        ]
    )
    await db.chapter_intelligence.insert_many(
        [
            {
                "project_id": pid,
                "intelligence_id": f"phase7-benchmark-{number}",
                "chapter_plan_id": f"plan-{number}",
                "chapter_draft_id": f"draft-{number}",
                "chapter_number": number,
                "title": f"Chapter {number}",
                "chapter_summary": f"Character {number % 100 + 1} advances event {number}.",
                "important_events": [
                    f"event-{number}",
                    *([f"phase7-benchmark-{number - 1}"] if number > 1 else []),
                ],
                "characters_present": [f"Character {number % 100 + 1}"],
                "future_obligations": [f"Resolve promise {number}"] if number % 50 == 0 else [],
                "mysteries_resolved": [],
                "foreshadowing_resolved": [],
                "word_count": 1700,
                "active": True,
                "updated_at": now,
            }
            for number in range(1, 501)
        ]
    )
    try:
        await narrative_analysis_engine.analyze(db, project_id, force=True)

        started = perf_counter()
        graph = await narrative_interaction_service.knowledge_graph(
            db, project_id, limit=5000
        )
        graph_seconds = perf_counter() - started

        started = perf_counter()
        cached_graph = await narrative_interaction_service.knowledge_graph(
            db, project_id, limit=5000
        )
        cached_graph_seconds = perf_counter() - started

        started = perf_counter()
        recommendations = await narrative_interaction_service.workspace_intelligence(
            db,
            project_id,
            surface="chapter",
            chapter_number=500,
        )
        recommendation_seconds = perf_counter() - started

        print(
            json.dumps(
                {
                    "chapters": 500,
                    "characters": 100,
                    "analysis_id": graph["analysis_id"],
                    "graph": {
                        "wall_seconds": round(graph_seconds, 4),
                        **graph["counts"],
                    },
                    "cached_graph": {
                        "wall_seconds": round(cached_graph_seconds, 4),
                        "same_analysis_id": cached_graph["analysis_id"] == graph["analysis_id"],
                        "nodes": cached_graph["counts"]["nodes"],
                        "edges": cached_graph["counts"]["edges"],
                    },
                    "workspace_intelligence": {
                        "wall_seconds": round(recommendation_seconds, 4),
                        "recommendations": len(recommendations["recommendations"]),
                        "cache_reused": recommendations["cache_reused"],
                    },
                },
                indent=2,
            )
        )
    finally:
        for collection in [
            "character_bibles",
            "chapter_intelligence",
            "narrative_nodes",
            "narrative_edges",
            "narrative_findings",
            "narrative_analysis_snapshots",
        ]:
            await db[collection].delete_many({"project_id": pid})
        await db.projects.delete_one({"_id": pid})
        await Database.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
