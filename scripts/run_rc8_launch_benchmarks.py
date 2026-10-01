"""RC8 commercial-launch scale benchmark with exact project cleanup.

The 100-1000 chapter rows are launch targets.  The 2000 chapter row is a
stress observation, as required by the RC8 release specification.
"""
from __future__ import annotations

import asyncio
import json
import os
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from bson import ObjectId


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.database import Database  # noqa: E402
from app.services.project_lifecycle_service import project_lifecycle_service  # noqa: E402
from app.services.workspace_bootstrap_service import workspace_bootstrap_service  # noqa: E402
from app.services.writing_experience_service import writing_experience_service  # noqa: E402


SIZES = (100, 250, 500, 1000, 2000)


def working_set_mb() -> float | None:
    try:
        import psutil

        return round(psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024, 2)
    except ImportError:
        return None


async def timed(call, repeats: int = 1):
    samples: list[float] = []
    value = None
    for _ in range(repeats):
        started = time.perf_counter()
        value = await call()
        samples.append((time.perf_counter() - started) * 1000)
    return round(statistics.median(samples), 2), value


async def seed(db, chapter_count: int) -> tuple[ObjectId, str]:
    pid = ObjectId()
    project_id = str(pid)
    now = datetime.utcnow()
    arc_id = str(uuid4())
    await db.projects.insert_one(
        {
            "_id": pid,
            "title": f"RC8 Benchmark {chapter_count}",
            "premise": "A courier must preserve a truthful record across a long journey.",
            "status": "draft",
            "created_at": now,
            "updated_at": now,
        }
    )
    await db.story_arcs.insert_one(
        {
            "project_id": pid,
            "arc_id": arc_id,
            "title": "The Long Record",
            "order": 1,
            "goal": "Deliver the record without changing it.",
            "conflict": "Each destination pressures the courier to revise the truth.",
            "stakes": "The public record will become unreliable.",
            "approval_status": "approved",
            "development_status": "active",
            "created_at": now,
            "updated_at": now,
        }
    )
    chapters: list[dict] = []
    scenes: list[dict] = []
    drafts: list[dict] = []
    revisions: list[dict] = []
    proposals: list[dict] = []
    events: list[dict] = []
    for number in range(1, chapter_count + 1):
        chapter_id = f"bench-chapter-{chapter_count}-{number:05d}"
        scene_id = f"bench-scene-{chapter_count}-{number:05d}"
        draft_id = f"bench-draft-{chapter_count}-{number:05d}"
        chapters.append(
            {
                "project_id": pid,
                "chapter_plan_id": chapter_id,
                "arc_id": arc_id,
                "chapter_number": number,
                "title": f"Chapter {number}",
                "purpose": "Advance one causal beat.",
                "conflict": "A bounded obstacle changes the next choice.",
                "status": "approved",
                "created_at": now,
                "updated_at": now,
            }
        )
        scenes.append(
            {
                "project_id": pid,
                "scene_id": scene_id,
                "chapter_plan_id": chapter_id,
                "arc_id": arc_id,
                "title": f"The record at stop {number}",
                "purpose": "Protect one fact.",
                "conflict": "A local official demands a change.",
                "outcome": "The courier's answer creates the next problem.",
                "character_focus": ["The Courier"],
                "order": 1,
                "status": "approved",
                "created_at": now,
                "updated_at": now,
            }
        )
        drafts.append(
            {
                "project_id": pid,
                "draft_id": draft_id,
                "scene_id": scene_id,
                "chapter_plan_id": chapter_id,
                "arc_id": arc_id,
                "version_number": 1,
                "version_label": "Version A",
                "status": "approved" if number < chapter_count else "review",
                "active": True,
                "generated_text": "The courier arrives with a goal. A concrete demand forces a choice, and the consequence points toward the next stop.",
                "generated_by": "SceneWriterAgent",
                "validation_result": "PASS",
                "created_at": now,
                "updated_at": now,
            }
        )
        revisions.append(
            {
                "project_id": pid,
                "report_id": f"bench-revision-{chapter_count}-{number:05d}",
                "subject_id": draft_id,
                "subject_type": "scene",
                "report_type": "editorial",
                "revision_pass": "continuity",
                "status": "complete" if number % 3 else "pending",
                "summary": "A bounded editorial target.",
                "created_at": now,
            }
        )
        proposals.append(
            {
                "project_id": pid,
                "proposal_id": f"bench-proposal-{chapter_count}-{number:05d}",
                "fact_type": "event",
                "subject": "The Courier",
                "predicate": "visited",
                "value": f"Stop {number}",
                "status": "pending" if number % 4 else "approved",
                "confidence": 0.88,
                "evidence": [f"Chapter {number}, Scene 1"],
                "created_at": now,
                "updated_at": now,
            }
        )
        events.append(
            {
                "project_id": pid,
                "event_id": f"bench-event-{chapter_count}-{number:05d}",
                "event_type": "scene_draft_changed",
                "summary": f"Chapter {number} Scene 1 draft generated",
                "chapter_number": number,
                "scene_id": scene_id,
                "system": "writing",
                "created_at": now,
            }
        )
    for collection, rows in (
        (db.chapter_plans, chapters),
        (db.scene_plans, scenes),
        (db.scene_drafts, drafts),
        (db.editorial_reports, revisions),
        (db.canon_proposals, proposals),
        (db.project_events, events),
    ):
        await collection.insert_many(rows, ordered=False)
    return pid, project_id


async def bounded_list(db, collection: str, pid: ObjectId, sort):
    return await db[collection].find({"project_id": pid}, {"_id": 0}).sort(sort).limit(60).to_list(length=60)


async def main() -> None:
    await Database.connect()
    db = Database.get_db()
    results: list[dict] = []
    try:
        for size in SIZES:
            pid, project_id = await seed(db, size)
            memory_before = working_set_mb()
            try:
                await workspace_bootstrap_service.invalidate(db, project_id)
                bootstrap_cold, cold_payload = await timed(lambda: workspace_bootstrap_service.get(db, project_id))
                bootstrap_warm, warm_payload = await timed(lambda: workspace_bootstrap_service.get(db, project_id), 3)
                writing_desk, dashboard = await timed(lambda: writing_experience_service.dashboard(db, project_id), 3)
                drafting, drafting_rows = await timed(
                    lambda: bounded_list(db, "scene_plans", pid, [("chapter_plan_id", 1), ("order", 1)])
                )
                editorial, editorial_rows = await timed(
                    lambda: bounded_list(db, "editorial_reports", pid, [("created_at", -1)])
                )
                canon, canon_rows = await timed(
                    lambda: bounded_list(db, "canon_proposals", pid, [("created_at", -1)])
                )
                timeline, timeline_rows = await timed(
                    lambda: bounded_list(db, "project_events", pid, [("created_at", -1)])
                )
                results.append(
                    {
                        "chapters": size,
                        "classification": "launch_target" if size <= 1000 else "stress_observation",
                        "workspace_bootstrap_cold_ms": bootstrap_cold,
                        "workspace_bootstrap_warm_median_ms": bootstrap_warm,
                        "workspace_cache_hit": bool(warm_payload.get("cache", {}).get("hit")),
                        "workspace_stages_ms": cold_payload.get("performance", {}),
                        "writing_desk_median_ms": writing_desk,
                        "drafting_first_60_ms": drafting,
                        "editorial_first_60_ms": editorial,
                        "canon_queue_first_60_ms": canon,
                        "project_timeline_first_60_ms": timeline,
                        "bounded_rows": {
                            "drafting": len(drafting_rows),
                            "editorial": len(editorial_rows),
                            "canon_queue": len(canon_rows),
                            "timeline": len(timeline_rows),
                        },
                        "dashboard_words": dashboard["metrics"]["words"],
                        "process_working_set_before_mb": memory_before,
                        "process_working_set_after_mb": working_set_mb(),
                    }
                )
            finally:
                await project_lifecycle_service.purge(db, pid)
        report = {
            "generated_at_utc": datetime.utcnow().isoformat(),
            "database": Database.get_db().name,
            "exact_cleanup": True,
            "results": results,
        }
        output = ROOT / "artifacts" / "rc8-launch-performance.json"
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        await Database.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
