"""Quiet, event-driven workspace companion built from existing project intelligence."""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict
from uuid import uuid4

from bson import ObjectId

from app.services.narrative_completeness_service import narrative_completeness_service
from app.services.story_health_service import story_health_service
from app.services.story_knowledge_projection_service import story_knowledge_projection_service
from app.services.writing_experience_service import writing_experience_service


def _serialize(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {("id" if key == "_id" else key): _serialize(item) for key, item in value.items()}
    return value


EVENT_COPY = {
    "canon_validated": ("status", "Canon validation completed."),
    "canon_promoted": ("celebration", "Approved canon is now reflected across the workspace."),
    "question_resolved": ("celebration", "I remembered your answer and shared it with the project intelligence."),
    "story_audit_completed": ("status", "Narrative review completed. The evidence is ready to inspect."),
    "narrative_analysis_completed": ("status", "Background narrative analysis completed."),
    "project_created": ("guide", "Let's turn the initial concept into a story-ready foundation."),
    "scene_draft_generated": ("status", "A new scene draft is ready for your review."),
    "scene_draft_approved": ("celebration", "Your scene is approved. The next planned scene is ready when you are."),
    "revision_version_created": ("status", "Your focused revision proposal is ready to compare."),
    "revision_applied_to_draft": ("status", "The approved revision is now a protected draft version for final review."),
}


class WorkspaceCompanionService:
    async def _project(self, db, project_id: str) -> ObjectId:
        if not ObjectId.is_valid(project_id):
            raise ValueError("Invalid project ID")
        pid = ObjectId(project_id)
        if not await db.projects.find_one({"_id": pid}):
            raise ValueError("Project not found")
        return pid

    async def _store(self, db, pid: ObjectId, *, kind: str, title: str, message: str,
                     target: str, source_key: str, priority: int = 50,
                     evidence: list[Any] | None = None,
                     recommendation_key: str | None = None,
                     cooldown_hours: int = 24,
                     dependencies: list[str] | None = None,
                     action_label: str | None = None,
                     explanation: str | None = None) -> Dict[str, Any]:
        fingerprint = hashlib.sha256(f"{source_key}|{message}|{target}".encode("utf-8")).hexdigest()
        now = datetime.utcnow()
        identity = recommendation_key or fingerprint
        existing = await db.workspace_companion_messages.find_one(
            {"project_id": pid, "recommendation_key": identity}
        )
        if existing and existing.get("state") in {"dismissed", "completed", "superseded"}:
            return existing
        cooldown_until = (existing or {}).get("cooldown_until")
        if existing and isinstance(cooldown_until, datetime) and cooldown_until > now:
            await db.workspace_companion_messages.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "active": True,
                    "state": "active",
                    "last_seen_at": now,
                    # Cooldown limits repeated presentation; it must not freeze
                    # live progress or leave the Companion describing an agent
                    # that already finished.
                    "message": message,
                    "title": title,
                    "target": target,
                    "priority": priority,
                    "evidence": evidence or [],
                    "dependencies": dependencies or [],
                    "action_label": action_label or title,
                    "explanation": explanation or message,
                }},
            )
            return await db.workspace_companion_messages.find_one({"_id": existing["_id"]})
        await db.workspace_companion_messages.update_one(
            {"project_id": pid, "recommendation_key": identity},
            {
                "$set": {
                    "last_seen_at": now, "active": True, "message": message,
                    "title": title, "target": target, "priority": priority,
                    "state": "active", "evidence": evidence or [],
                    "dependencies": dependencies or [],
                    "action_label": action_label or title,
                    "explanation": explanation or message,
                },
                "$setOnInsert": {
                    "project_id": pid,
                    "message_id": str(uuid4()),
                    "kind": kind,
                    "fingerprint": fingerprint,
                    "recommendation_key": identity,
                    "read": False,
                    "dismissed": False,
                    "presentation_count": 0,
                    "cooldown_hours": cooldown_hours,
                    "created_at": now,
                },
            },
            upsert=True,
        )
        return await db.workspace_companion_messages.find_one({"project_id": pid, "recommendation_key": identity})

    async def refresh(
        self,
        db,
        project_id: str,
        *,
        active_surface: str = "",
    ) -> Dict[str, Any]:
        pid = await self._project(db, project_id)
        await db.workspace_companion_messages.update_many(
            {"project_id": pid, "kind": {"$in": ["status", "recommendation", "attention", "guide", "celebration"]}},
            {"$set": {"active": False}},
        )
        # Companion reads the intelligence projections. It only creates a
        # first snapshot when a project has never been analyzed; opening the
        # companion must not run two project-wide analyses every 30 seconds.
        project = await db.projects.find_one({"_id": pid}) or {}
        completeness = await db.narrative_completeness_snapshots.find_one(
            {"project_id": pid, "snapshot_type": "current"}
        )
        project_updated = project.get("updated_at")
        completeness_calculated = (completeness or {}).get("calculated_at")
        if (
            not completeness
            or (
                isinstance(project_updated, datetime)
                and isinstance(completeness_calculated, datetime)
                and project_updated > completeness_calculated
            )
        ):
            completeness = await narrative_completeness_service.calculate(db, project_id)
        health = await db.story_health_snapshots.find_one(
            {"project_id": pid, "snapshot_type": "current"}
        )
        if not health:
            health = await story_health_service.calculate(db, project_id)
        messages: list[Dict[str, Any]] = []
        active_recommendation_keys: set[str] = set()
        writing_surface = active_surface in {"drafting", "editorial", "manuscript"}

        latest_run = await db.runs.find_one(
            {"project_id": pid}, sort=[("started_at", -1)]
        )
        if latest_run and latest_run.get("status") in {"queued", "running", "failed", "interrupted", "waiting_for_user"}:
            status = str(latest_run.get("status"))
            metadata = latest_run.get("metadata") or {}
            if status in {"queued", "running"}:
                title = "Your story team is working"
                message = str(metadata.get("author_phase") or "Preparing the next story task")
                kind = "status"
                priority = 100
            elif status == "waiting_for_user":
                title = "Your direction is needed"
                message = "NovelForge paused at an important story choice. Your completed planning is saved."
                kind = "attention"
                priority = 100
            elif status == "failed":
                title = "Story development needs attention"
                message = str(latest_run.get("error") or "Completed work was saved. You can retry safely from the Dashboard.")
                kind = "attention"
                priority = 100
            else:
                title = "Development stopped safely"
                message = "NovelForge restarted during development. Completed work was saved and can be continued."
                kind = "attention"
                priority = 100
            progress_total = int(metadata.get("progress_total") or 0)
            progress_completed = int(metadata.get("progress_completed") or 0)
            if status in {"queued", "running"} and progress_total:
                message = f"{message} {progress_completed} of {progress_total} tasks are finished."
            messages.append(await self._store(
                db, pid, kind=kind, title=title, message=message,
                target="questions" if status == "waiting_for_user" else "workflow",
                source_key=f"development:{latest_run['_id']}", priority=priority,
                recommendation_key=f"development:{latest_run['_id']}", cooldown_hours=1,
                action_label="Review story development",
            ))

        events = await db.project_events.find({"project_id": pid}).sort("created_at", -1).to_list(length=30)
        seen_event_types: set[str] = set()
        for event in events:
            event_type = str(event.get("event_type") or "")
            if event_type not in EVENT_COPY or event_type in seen_event_types:
                continue
            seen_event_types.add(event_type)
            kind, message = EVENT_COPY[event_type]
            messages.append(await self._store(
                db, pid, kind=kind, title="Workspace update", message=message,
                target="canon" if event_type.startswith("canon") else "dashboard",
                    source_key=f"event:{event.get('_id')}", evidence=[{"event_type": event_type, "payload": event.get("payload") or {}}],
                    recommendation_key=f"event:{event.get('_id')}", cooldown_hours=168,
            ))

        history = await db.narrative_completeness_history.find({"project_id": pid}).sort("calculated_at", -1).to_list(length=2)
        if len(history) >= 2:
            previous = int(history[1].get("overall_completion") or 0)
            current = int(history[0].get("overall_completion") or 0)
            if current > previous:
                await db.workspace_companion_messages.update_many(
                    {
                        "project_id": pid,
                        "kind": "celebration",
                        "title": "Progress improved",
                    },
                    {
                        "$set": {
                            "active": False,
                            "state": "superseded",
                            "superseded_at": datetime.utcnow(),
                        }
                    },
                )
                messages.append(await self._store(
                    db, pid, kind="celebration", title="Progress improved",
                    message=f"Narrative completeness improved from {previous}% to {current}%.",
                    target="guide", source_key=f"completeness:{history[0].get('fingerprint')}", priority=65,
                    recommendation_key=f"progress:{history[0].get('fingerprint')}", cooldown_hours=168,
                ))

        for milestone in completeness.get("milestones") or []:
            if milestone.get("achieved"):
                messages.append(await self._store(
                    db, pid, kind="milestone", title=milestone["label"],
                    message=f"Milestone achieved: {milestone['label']}.", target="guide",
                    source_key=f"milestone:{milestone['gate_id']}", priority=80,
                    recommendation_key=f"milestone:{milestone['gate_id']}", cooldown_hours=720,
                ))

        next_actions = completeness.get("next_actions") or []
        writing_dashboard = None
        writing_state = await writing_experience_service.state(db, project_id)
        discovery_progress = writing_state.get("workflow_mode") in {"discovery", "mixed"} and int(writing_state.get("chapter_count") or 0) > 0
        if writing_surface and not discovery_progress:
            writing_dashboard = await writing_experience_service.dashboard(
                db, project_id
            )
            action = writing_dashboard["next_action"]
            recommendation_key = (
                f"writing:{writing_dashboard['workflow']['active_stage']}:"
                f"{action.get('scene_id') or action.get('draft_id') or 'project'}"
            )
            active_recommendation_keys.add(recommendation_key)
            messages.append(
                await self._store(
                    db,
                    pid,
                    kind="recommendation",
                    title=action["title"],
                    message=action["explanation"],
                    target=action["target"],
                    source_key=recommendation_key,
                    priority=95,
                    evidence=[
                        {
                            "workflow": writing_dashboard["workflow"],
                            "scene_health": writing_dashboard["scene_health"],
                        }
                    ],
                    recommendation_key=recommendation_key,
                    cooldown_hours=12,
                    action_label=action["action"],
                    explanation=action["explanation"],
                )
            )
        elif discovery_progress:
            state_action = writing_state.get("next_action") or {}
            title = str(state_action.get("label") or "Continue writing")
            target = str(state_action.get("target") or "writing")
            recommendation_key = f"writing:{writing_state.get('workflow_mode')}:{writing_state.get('latest_approved_chapter_number') or (writing_state.get('latest_approved_chapter') or {}).get('chapter_number') or writing_state.get('chapter_count') or 'project'}"
            active_recommendation_keys.add(recommendation_key)
            messages.append(await self._store(
                db, pid, kind="recommendation", title=title,
                message="Your latest approved writing is ready. Continue from the Writing workspace." if title.startswith("Continue with Chapter") else "Review the current writing state before choosing the next chapter step.",
                target=target, source_key=recommendation_key, priority=95,
                evidence=[{"writing_state": writing_state}], recommendation_key=recommendation_key,
                cooldown_hours=12, action_label="Open Writing",
                explanation="This recommendation comes from your approved chapters and their current lifecycle.",
            ))
        elif next_actions:
            action = next_actions[0]
            recommendation_key = f"next:{action.get('action_id')}"
            active_recommendation_keys.add(recommendation_key)
            messages.append(await self._store(
                db, pid, kind="recommendation", title="What should I do next?",
                message=action.get("reason") or action.get("label"), target=action.get("target") or "dashboard",
                source_key=recommendation_key, priority=75,
                evidence=[action],
                recommendation_key=recommendation_key, cooldown_hours=24,
                action_label=action.get("label") or "Continue",
                explanation=action.get("reason") or "This is the next incomplete requirement for the current milestone.",
            ))

        await db.workspace_companion_messages.update_many(
            {
                "project_id": pid, "kind": "recommendation", "state": "active",
                "recommendation_key": {"$nin": list(active_recommendation_keys)},
            },
            {"$set": {"state": "completed", "active": False, "completed_at": datetime.utcnow()}},
        )

        pending = await db.canon_proposals.count_documents({"project_id": pid, "status": "pending"})
        if pending:
            messages.append(await self._store(
                db, pid, kind="attention", title="Canon proposals need review",
                message=f"You have {pending} canon proposal{'s' if pending != 1 else ''} waiting for a decision.",
                target="canon-queue", source_key="pending-canon-proposals", priority=85,
                recommendation_key="attention:canon-proposals", cooldown_hours=12,
            ))

        # Candidate knowledge is a governed author task, not a background
        # failure. Surface it as a compact review reminder so Discovery and
        # conversational planning do not silently disappear into memory.
        pending_knowledge = await story_knowledge_projection_service.list_candidates(db, project_id)
        if pending_knowledge:
            messages.append(await self._store(
                db, pid, kind="attention", title="Story suggestions need your review",
                message=f"{len(pending_knowledge)} detail{'s' if len(pending_knowledge) != 1 else ''} noticed in planning or approved writing can be confirmed or dismissed.",
                target=active_surface or "characters", source_key=f"pending-story-knowledge:{len(pending_knowledge)}",
                priority=82, recommendation_key="attention:story-knowledge", cooldown_hours=12,
                action_label="Review story suggestions",
            ))

        active_finding_rows = await db.narrative_findings.find({
            "project_id": pid, "status": {"$in": ["open", "acknowledged"]}, "severity": {"$in": ["high", "critical"]},
        }, {"semantic_issue_id": 1, "finding_id": 1}).to_list(length=10000)
        active_findings = len({
            str(item.get("semantic_issue_id") or item.get("finding_id") or item.get("_id"))
            for item in active_finding_rows
        })
        if active_findings:
            messages.append(await self._store(
                db, pid, kind="attention", title="Story issues need attention",
                message=f"I found {active_findings} high-priority narrative issue{'s' if active_findings != 1 else ''} with supporting evidence.",
                target="story-health", source_key=f"health:{active_findings}", priority=90,
                recommendation_key="attention:story-health", cooldown_hours=12,
            ))

        now = datetime.utcnow()
        feed = await db.workspace_companion_messages.find({
            "project_id": pid,
            "active": True,
            "state": "active",
            "dismissed": {"$ne": True},
        }).sort([("priority", -1), ("created_at", -1)]).to_list(length=50)
        displayed_ids = [
            item.get("message_id")
            for item in feed[:5]
            if item.get("message_id") and (
                not item.get("last_presented_at")
                or (now - item["last_presented_at"]).total_seconds() >= 60 * 60
            )
        ]
        if displayed_ids:
            await db.workspace_companion_messages.update_many(
                {"project_id": pid, "message_id": {"$in": displayed_ids}},
                {"$set": {"last_presented_at": now, "cooldown_until": now + timedelta(hours=12)}, "$inc": {"presentation_count": 1}},
            )
        background_running = bool(await db.narrative_analysis_jobs.count_documents({
            "project_id": pid, "status": {"$in": ["queued", "running"]}
        })) or bool(await db.runs.count_documents({
            "project_id": pid, "status": {"$in": ["queued", "running"]}
        }))
        companion_state = "working" if background_running else (
            "celebrating" if any(item.get("kind") in {"celebration", "milestone"} for item in feed[:3])
            else "notifying" if feed else "idle"
        )
        previous_state = await db.workspace_companion_state.find_one({"project_id": pid}) or {}
        previous_seen = previous_state.get("last_seen_at")
        welcome_back = bool(previous_seen and (now - previous_seen).total_seconds() > 6 * 60 * 60)
        await db.workspace_companion_state.update_one(
            {"project_id": pid},
            {"$set": {"state": companion_state, "last_seen_at": now, "previous_seen_at": previous_seen,
                      "last_headline_key": (feed[0].get("recommendation_key") if feed else None)},
             "$setOnInsert": {"created_at": now}}, upsert=True,
        )
        return _serialize({
            "messages": feed,
            "headline": feed[0] if feed else None,
            "story_health": health.get("story_health_score"),
            "current_milestone": completeness.get("current_milestone"),
            "next_actions": next_actions,
            "state": companion_state,
            "welcome_back": welcome_back,
            "recap": (
                f"Welcome back. Your next useful step is {writing_dashboard['next_action']['title']}."
                if welcome_back and writing_dashboard
                else (
                    f"Welcome back. Your next useful step is {next_actions[0].get('label')}."
                    if welcome_back and next_actions
                    else None
                )
            ),
            "active_surface": active_surface or None,
            "behavior": {"motion": "subtle", "interruptive": False, "respects_reduced_motion": True},
            "refreshed_at": datetime.utcnow(),
        })

    async def set_message_state(self, db, project_id: str, message_id: str, *, read: bool | None = None,
                                dismissed: bool | None = None, completed: bool | None = None,
                                snooze_hours: int | None = None) -> Dict[str, Any]:
        pid = await self._project(db, project_id)
        patch: Dict[str, Any] = {"updated_at": datetime.utcnow()}
        if read is not None:
            patch["read"] = bool(read)
        if dismissed is not None:
            patch["dismissed"] = bool(dismissed)
            patch["state"] = "dismissed" if dismissed else "active"
            patch["active"] = not bool(dismissed)
        if completed is not None:
            patch["state"] = "completed" if completed else "active"
            patch["active"] = not bool(completed)
            if completed:
                patch["completed_at"] = datetime.utcnow()
        if snooze_hours is not None:
            hours = max(1, min(int(snooze_hours), 720))
            patch["state"] = "snoozed"
            patch["active"] = False
            patch["cooldown_until"] = datetime.utcnow() + timedelta(hours=hours)
        result = await db.workspace_companion_messages.find_one_and_update(
            {"project_id": pid, "message_id": message_id}, {"$set": patch}, return_document=True,
        )
        if not result:
            raise ValueError("Companion message not found")
        return _serialize(result)

    async def mark_feed_read(self, db, project_id: str) -> Dict[str, Any]:
        """Mark currently active companion messages as seen in one write."""
        pid = await self._project(db, project_id)
        result = await db.workspace_companion_messages.update_many(
            {
                "project_id": pid,
                "active": True,
                "state": "active",
                "read": {"$ne": True},
            },
            {"$set": {"read": True, "read_at": datetime.utcnow()}},
        )
        return {"updated": result.modified_count}


workspace_companion_service = WorkspaceCompanionService()
