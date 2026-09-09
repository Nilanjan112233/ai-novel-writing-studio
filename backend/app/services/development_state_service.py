"""Author-visible lifecycle for long-running automatic story development."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from bson import ObjectId
from pymongo import ReturnDocument


LEASE_MINUTES = 60


class DevelopmentStateService:
    async def start_story_studio_development(
        self,
        db,
        project_id: str,
        *,
        instruction: str,
        story_studio_job_id: str,
        targeted: bool = False,
    ) -> dict[str, Any]:
        """Start the existing workflow engine from a Story Studio request.

        Story Studio is only the author-facing trigger. The durable run, cycle,
        lease, orchestration plan, Story Bible rebuild, and recovery behavior
        remain the existing workflow authorities.
        """
        from app.api.workflow import (
            MAX_AUTOMATIC_CYCLES_PER_ADVANCE,
            next_cycle_number,
            run_cycle_async,
            run_workflow_async,
        )

        if not ObjectId.is_valid(project_id):
            raise ValueError("Invalid project ID")
        if not await db.projects.find_one({"_id": ObjectId(project_id)}):
            raise ValueError("Project not found")

        lease_token = await self.acquire(db, project_id)
        if not lease_token:
            raise ValueError("Story development is already running for this project. Follow the existing activity before starting another pass.")

        now = datetime.utcnow()
        cycle_number = await next_cycle_number(db, project_id)
        message = {
            "project_id": ObjectId(project_id),
            "cycle_number": cycle_number,
            "role": "user",
            "content": instruction,
            "message_type": "story_studio_development",
            "source_type": "story_studio",
            "story_studio_job_id": story_studio_job_id,
            "created_at": now,
        }
        message_result = await db.timeline_messages.insert_one(message)
        cycle = {
            "project_id": ObjectId(project_id),
            "cycle_number": cycle_number,
            "trigger_message_ids": [message_result.inserted_id],
            "agents_run": [],
            "started_at": now,
            "finished_at": None,
            "status": "running",
            "source_type": "story_studio",
            "story_studio_job_id": story_studio_job_id,
        }
        cycle_result = await db.cycles.insert_one(cycle)
        cycle_id = str(cycle_result.inserted_id)
        run = {
            "project_id": ObjectId(project_id),
            "status": "running",
            "current_agent": "OrchestratorAgent",
            "started_at": now,
            "finished_at": None,
            "metadata": {
                "cycle_id": cycle_id,
                "cycle_number": cycle_number,
                "automatic_development": not targeted,
                "max_automatic_cycles": MAX_AUTOMATIC_CYCLES_PER_ADVANCE,
                "story_studio_job_id": story_studio_job_id,
                "source_type": "story_studio",
                "author_phase": "Reviewing confirmed story planning",
            },
        }
        try:
            run_result = await db.runs.insert_one(run)
            run_id = str(run_result.inserted_id)
            await self.attach_run(db, project_id, lease_token, run_id)
        except Exception:
            await self.release(db, project_id)
            raise

        runner = run_cycle_async if targeted else run_workflow_async
        task = asyncio.create_task(runner(project_id, run_id, cycle_id))
        # Keep an explicit reference until completion so an event-loop task is
        # not prematurely collected by an aggressive runtime.
        task.add_done_callback(lambda completed: completed.exception() if not completed.cancelled() else None)
        return {
            "run_id": run_id,
            "cycle_id": cycle_id,
            "cycle_number": cycle_number,
            "targeted": targeted,
            "message": "I started a governed story-development pass using your confirmed planning. I will keep the work in the existing project workflow and stop for a meaningful decision if one is needed.",
        }

    async def acquire(self, db, project_id: str) -> str | None:
        """Acquire one project-scoped development lease atomically."""
        pid = ObjectId(project_id)
        now = datetime.utcnow()
        token = str(uuid4())
        project = await db.projects.find_one_and_update(
            {
                "_id": pid,
                "$or": [
                    {"development_lock": {"$exists": False}},
                    {"development_lock.status": {"$ne": "running"}},
                    {"development_lock.lease_expires_at": {"$lte": now}},
                ],
            },
            {
                "$set": {
                    "development_lock": {
                        "token": token,
                        "status": "running",
                        "started_at": now,
                        "heartbeat_at": now,
                        "lease_expires_at": now + timedelta(minutes=LEASE_MINUTES),
                    }
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return token if project else None

    async def attach_run(self, db, project_id: str, token: str, run_id: str) -> None:
        await db.projects.update_one(
            {"_id": ObjectId(project_id), "development_lock.token": token},
            {"$set": {"development_lock.run_id": ObjectId(run_id)}},
        )

    async def heartbeat(self, db, project_id: str, run_id: str) -> None:
        now = datetime.utcnow()
        await db.projects.update_one(
            {
                "_id": ObjectId(project_id),
                "development_lock.run_id": ObjectId(run_id),
            },
            {"$set": {
                "development_lock.heartbeat_at": now,
                "development_lock.lease_expires_at": now + timedelta(minutes=LEASE_MINUTES),
            }},
        )

    async def release(self, db, project_id: str, run_id: str | None = None) -> None:
        query: dict[str, Any] = {"_id": ObjectId(project_id)}
        if run_id and ObjectId.is_valid(run_id):
            query["development_lock.run_id"] = ObjectId(run_id)
        await db.projects.update_one(query, {"$unset": {"development_lock": ""}})

    async def recover_interrupted(self, db) -> dict[str, int]:
        """A background task cannot survive an application process restart."""
        now = datetime.utcnow()
        running = await db.runs.find(
            {"status": {"$in": ["queued", "running"]}},
            {"_id": 1, "project_id": 1, "current_agent": 1},
        ).to_list(length=10000)
        run_ids = [item["_id"] for item in running]
        project_ids = list({item["project_id"] for item in running if item.get("project_id")})
        if run_ids:
            for item in running:
                await db.runs.update_one(
                    {"_id": item["_id"]},
                    {"$set": {
                        "status": "interrupted",
                        "finished_at": now,
                        "error_code": "APPLICATION_RESTARTED",
                        "error": "Story development stopped when NovelForge restarted. Completed work was kept and development can be safely continued.",
                        "metadata.interrupted_agent": item.get("current_agent"),
                        "metadata.recovery_action": "continue_development",
                    }, "$unset": {"current_agent": ""}},
                )
        cycle_result = await db.cycles.update_many(
            {"status": "running"},
            {"$set": {"status": "interrupted", "finished_at": now}},
        )
        plan_result = await db.orchestration_plans.update_many(
            {"status": {"$in": ["pending", "running"]}},
            {"$set": {
                "status": "interrupted",
                "completed_at": now,
                "error": "Application restarted before this development plan completed.",
            }},
        )
        task_result = await db.orchestration_tasks.update_many(
            {"status": "running"},
            {"$set": {
                "status": "interrupted",
                "completed_at": now,
                "reason": "Application restarted during this task.",
            }},
        )
        if project_ids:
            await db.projects.update_many(
                {"_id": {"$in": project_ids}},
                {"$unset": {"development_lock": ""}},
            )
            for item in running:
                await db.project_events.insert_one({
                    "project_id": item["project_id"],
                    "event_type": "workflow_interrupted",
                    "cycle_number": 0,
                    "payload": {
                        "run_id": str(item["_id"]),
                        "interrupted_agent": item.get("current_agent"),
                    },
                    "created_at": now,
                })
        else:
            await db.projects.update_many(
                {"development_lock.status": "running"},
                {"$unset": {"development_lock": ""}},
            )
        return {
            "runs": len(run_ids),
            "cycles": cycle_result.modified_count,
            "plans": plan_result.modified_count,
            "tasks": task_result.modified_count,
        }


development_state_service = DevelopmentStateService()
