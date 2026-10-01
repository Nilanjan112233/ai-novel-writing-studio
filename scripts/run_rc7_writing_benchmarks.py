"""Bounded RC7 writing/bootstrap benchmark for 100–1000 chapter projects."""
from __future__ import annotations

import asyncio
import json
import statistics
import time
from datetime import datetime
from uuid import uuid4

from bson import ObjectId

from app.core.database import Database
from app.services.project_lifecycle_service import project_lifecycle_service
from app.services.workspace_bootstrap_service import workspace_bootstrap_service
from app.services.writing_experience_service import writing_experience_service


SIZES = (100, 250, 500, 1000)


async def timed(call, repeats: int = 1) -> tuple[float, object]:
    samples = []
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
            "title": f"RC7 Benchmark {chapter_count}",
            "status": "draft",
            "created_at": now,
            "updated_at": now,
        }
    )
    await db.story_arcs.insert_one(
        {
            "project_id": pid,
            "arc_id": arc_id,
            "title": "Long-form benchmark arc",
            "order": 1,
            "focus_role": "current",
            "goal": "Measure writing workspace performance.",
            "conflict": "Scale.",
            "stakes": "Responsiveness.",
            "approval_status": "approved",
            "development_status": "active",
            "created_at": now,
            "updated_at": now,
        }
    )
    chapters = []
    scenes = []
    drafts = []
    for number in range(1, chapter_count + 1):
        chapter_id = f"bench-chapter-{number}"
        scene_id = f"bench-scene-{number}"
        draft_id = f"bench-draft-{number}"
        chapters.append(
            {
                "project_id": pid,
                "chapter_plan_id": chapter_id,
                "arc_id": arc_id,
                "chapter_number": number,
                "title": f"Chapter {number}",
                "purpose": "Advance one benchmark beat.",
                "conflict": "A bounded obstacle.",
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
                "title": f"Scene {number}",
                "purpose": "One clear goal.",
                "conflict": "One meaningful obstacle.",
                "outcome": "The next scene becomes necessary.",
                "character_focus": ["Benchmark protagonist"],
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
                "generated_text": (
                    "The protagonist enters with a goal. A concrete obstacle changes the "
                    "choice, and the final action creates the next scene."
                ),
                "generated_by": "SceneWriterAgent",
                "validation_result": "PASS",
                "created_at": now,
                "updated_at": now,
            }
        )
    await db.chapter_plans.insert_many(chapters)
    await db.scene_plans.insert_many(scenes)
    await db.scene_drafts.insert_many(drafts)
    return pid, project_id


async def main() -> None:
    await Database.connect()
    db = Database.get_db()
    results = []
    try:
        for size in SIZES:
            pid, project_id = await seed(db, size)
            try:
                dashboard_cold, dashboard = await timed(
                    lambda: writing_experience_service.dashboard(db, project_id)
                )
                dashboard_warm, _ = await timed(
                    lambda: writing_experience_service.dashboard(db, project_id),
                    repeats=3,
                )
                scene_load, scene_rows = await timed(
                    lambda: db.scene_drafts.find(
                        {"project_id": pid, "active": True},
                        {"_id": 0, "draft_id": 1, "scene_id": 1, "status": 1},
                    ).sort("created_at", -1).limit(100).to_list(length=100)
                )
                bootstrap_cold, _ = await timed(
                    lambda: workspace_bootstrap_service.get(db, project_id)
                )
                bootstrap_warm, _ = await timed(
                    lambda: workspace_bootstrap_service.get(db, project_id)
                )
                results.append(
                    {
                        "chapters": size,
                        "scenes": size,
                        "workspace_bootstrap_cold_ms": bootstrap_cold,
                        "workspace_bootstrap_warm_ms": bootstrap_warm,
                        "writing_dashboard_cold_ms": dashboard_cold,
                        "writing_dashboard_warm_median_ms": dashboard_warm,
                        "scene_history_100_ms": scene_load,
                        "scene_rows": len(scene_rows),
                        "dashboard_words": dashboard["metrics"]["words"],
                    }
                )
            finally:
                await project_lifecycle_service.purge(db, pid)
        print(json.dumps({"generated_at": datetime.utcnow().isoformat(), "results": results}, indent=2))
    finally:
        await Database.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
