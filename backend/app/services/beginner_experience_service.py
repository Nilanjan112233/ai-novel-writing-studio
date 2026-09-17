"""RC6 beginner-author facade over the existing NovelForge story services."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from bson import ObjectId

from app.services.narrative_completeness_service import narrative_completeness_service
from app.services.project_event_service import emit_project_event
from app.services.shared_narrative_context_service import shared_narrative_context_service
from app.services.story_bible_service import get_story_bible, rebuild_story_bible


STEP_DEFINITIONS = (
    ("story_idea", "Story Idea", "Describe the story promise in your own words.", "vision"),
    ("main_character", "Main Character", "Name the person whose choices will drive the novel.", "characters"),
    ("world", "World", "Describe where the story happens and one rule that shapes it.", "world"),
    ("conflict", "Conflict", "Define what stands in the protagonist's way and why it matters.", "arcs"),
    ("first_decision", "First Decision", "Choose one truth the story should treat as intentional.", "questions"),
    ("first_arc", "First Arc", "Give the opening movement a goal, obstacle, and direction.", "arc-development"),
    ("first_scene", "First Scene", "Plan the opening scene's purpose, conflict, and outcome.", "drafting"),
)


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


class BeginnerExperienceService:
    async def _project(self, db, project_id: str) -> tuple[ObjectId, Dict[str, Any]]:
        if not ObjectId.is_valid(project_id):
            raise ValueError("Invalid project ID")
        pid = ObjectId(project_id)
        project = await db.projects.find_one({"_id": pid, "status": {"$ne": "trashed"}})
        if not project:
            raise ValueError("Project not found")
        return pid, project

    async def _inferred_completion(self, db, pid: ObjectId, project: Dict[str, Any]) -> Dict[str, bool]:
        vision = await db.story_visions.find_one({"project_id": pid}) or {}
        character = await db.character_bibles.find_one({"project_id": pid})
        world = await db.world_bibles.find_one({"project_id": pid})
        arc = await db.story_arcs.find_one({"project_id": pid})
        scene = await db.scene_plans.find_one({"project_id": pid})
        decision = await db.beginner_setup_steps.find_one(
            {"project_id": pid, "step_id": "first_decision", "status": "completed"}
        )
        return {
            "story_idea": bool(
                str(vision.get("premise") or project.get("premise") or project.get("idea_dump") or "").strip()
            ),
            "main_character": bool(character),
            "world": bool(world),
            "conflict": bool(
                str(vision.get("central_conflict") or "").strip()
                or (arc and str(arc.get("conflict") or "").strip())
            ),
            "first_decision": bool(decision),
            "first_arc": bool(arc),
            "first_scene": bool(scene),
        }

    async def get(self, db, project_id: str) -> Dict[str, Any]:
        pid, project = await self._project(db, project_id)
        inferred = await self._inferred_completion(db, pid, project)
        persisted = {
            item["step_id"]: item
            for item in await db.beginner_setup_steps.find({"project_id": pid}).to_list(length=20)
        }
        steps = []
        for order, (step_id, label, description, target) in enumerate(STEP_DEFINITIONS, start=1):
            state = persisted.get(step_id) or {}
            status = str(state.get("status") or ("completed" if inferred[step_id] else "not_started"))
            if inferred[step_id] and status == "not_started":
                status = "completed"
            steps.append({
                "step_id": step_id,
                "order": order,
                "label": label,
                "description": description,
                "target": target,
                "status": status,
                "title": str(state.get("title") or ""),
                "details": str(state.get("details") or ""),
                "can_skip": True,
                "can_edit": True,
                "ai_prompt": (
                    f"Help me define my {label.lower()} for this project. Give one focused suggestion, "
                    "explain why it fits the existing story idea, and leave the final choice to me."
                ),
                "completed_at": state.get("completed_at"),
            })
        completed = sum(1 for item in steps if item["status"] in {"completed", "skipped"})
        current = next((item for item in steps if item["status"] not in {"completed", "skipped"}), steps[-1])
        return _serialize({
            "project_id": project_id,
            "current_step": current["step_id"],
            "completed_steps": completed,
            "total_steps": len(steps),
            "completion": round(completed / len(steps) * 100),
            "first_scene_ready": inferred["first_scene"],
            "steps": steps,
            "next_action": {
                "label": f"Continue with {current['label']}",
                "target": current["target"],
                "step_id": current["step_id"],
                "reason": current["description"],
            },
        })

    async def update(
        self,
        db,
        project_id: str,
        step_id: str,
        *,
        action: str,
        title: str = "",
        details: str = "",
        source_mode: str = "manual",
    ) -> Dict[str, Any]:
        pid, project = await self._project(db, project_id)
        definition = next((item for item in STEP_DEFINITIONS if item[0] == step_id), None)
        if not definition:
            raise ValueError("Beginner step not found")
        now = datetime.utcnow()
        if action == "reopen":
            await db.beginner_setup_steps.update_one(
                {"project_id": pid, "step_id": step_id},
                {"$set": {"status": "not_started", "updated_at": now}, "$unset": {"completed_at": ""}},
                upsert=True,
            )
        elif action == "skip":
            await db.beginner_setup_steps.update_one(
                {"project_id": pid, "step_id": step_id},
                {"$set": {
                    "status": "skipped",
                    "title": title.strip(),
                    "details": details.strip(),
                    "source_mode": source_mode,
                    "completed_at": now,
                    "updated_at": now,
                }, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
        elif action == "save":
            cleaned_title = title.strip()
            cleaned_details = details.strip()
            if not (cleaned_title or cleaned_details):
                raise ValueError("Add a short answer before saving this step")
            await self._apply_step(
                db, project_id, pid, project, step_id, cleaned_title, cleaned_details, source_mode, now
            )
            await db.beginner_setup_steps.update_one(
                {"project_id": pid, "step_id": step_id},
                {"$set": {
                    "status": "completed",
                    "title": cleaned_title,
                    "details": cleaned_details,
                    "source_mode": source_mode,
                    "completed_at": now,
                    "updated_at": now,
                }, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
        else:
            raise ValueError("Unsupported beginner step action")

        bible = await rebuild_story_bible(db, project_id)
        await narrative_completeness_service.calculate(db, project_id)
        await emit_project_event(
            db,
            project_id,
            "beginner_step_updated",
            payload={"step_id": step_id, "action": action, "story_bible_version": bible.get("version")},
        )
        return await self.get(db, project_id)

    async def _apply_step(
        self,
        db,
        project_id: str,
        pid: ObjectId,
        project: Dict[str, Any],
        step_id: str,
        title: str,
        details: str,
        source_mode: str,
        now: datetime,
    ) -> None:
        value = details or title
        source = f"beginner_{source_mode}"
        if step_id == "story_idea":
            premise = value
            await db.projects.update_one(
                {"_id": pid},
                {"$set": {"premise": premise, "idea_dump": premise, "updated_at": now}},
            )
            await db.story_visions.update_one(
                {"project_id": pid},
                {"$set": {"premise": premise, "source_type": source, "updated_at": now},
                 "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
        elif step_id == "main_character":
            name = title or "Protagonist"
            await db.character_bibles.update_one(
                {"project_id": pid, "beginner_primary": True},
                {"$set": {
                    "name": name,
                    "role": "protagonist",
                    "description": details,
                    "motivations": [details] if details else [],
                    "current_status": "active",
                    "beginner_primary": True,
                    "source_type": source,
                    "updated_at": now,
                }, "$setOnInsert": {
                    "character_id": str(uuid4()),
                    "created_at": now,
                }},
                upsert=True,
            )
        elif step_id == "world":
            await db.world_bibles.update_one(
                {"project_id": pid},
                {"$set": {
                    "setting": title or value,
                    "summary": details,
                    "world_rules": [details] if details else [title],
                    "source_type": source,
                    "updated_at": now,
                }, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
        elif step_id == "conflict":
            await db.story_visions.update_one(
                {"project_id": pid},
                {"$set": {"central_conflict": value, "updated_at": now},
                 "$addToSet": {"narrative_goals": value},
                 "$setOnInsert": {
                     "premise": project.get("premise") or project.get("idea_dump") or "",
                     "created_at": now,
                 }},
                upsert=True,
            )
        elif step_id == "first_decision":
            await shared_narrative_context_service.ingest(
                db,
                project_id,
                content=value,
                source_type="beginner_decision",
                source_id="beginner:first_decision",
                source_excerpt=value,
                structured={
                    "domain": "general",
                    "subject": title or "Opening story decision",
                    "field": "author_decision",
                    "value": value,
                    "confidence": .99,
                },
                create_canon_proposal=False,
            )
        elif step_id == "first_arc":
            conflict = (await db.story_visions.find_one({"project_id": pid}) or {}).get("central_conflict") or details
            await db.story_arcs.update_one(
                {"project_id": pid, "beginner_primary": True},
                {"$set": {
                    "title": title or "Opening Arc",
                    "purpose": details,
                    "goal": details,
                    "conflict": conflict,
                    "stakes": details,
                    "approval_status": "draft",
                    "development_status": "idea",
                    "focus_role": "current",
                    "readiness_status": "NOT_READY",
                    "drafting_eligible": False,
                    "beginner_primary": True,
                    "source_type": source,
                    "updated_at": now,
                }, "$setOnInsert": {
                    "arc_id": str(uuid4()),
                    "order": 1,
                    "chapter_range": [],
                    "created_at": now,
                }},
                upsert=True,
            )
        elif step_id == "first_scene":
            arc = await db.story_arcs.find_one({"project_id": pid}, sort=[("order", 1)])
            if not arc:
                arc_id = str(uuid4())
                arc = {
                    "project_id": pid,
                    "arc_id": arc_id,
                    "title": "Opening Arc",
                    "purpose": "Begin the story",
                    "goal": value,
                    "conflict": value,
                    "approval_status": "draft",
                    "development_status": "idea",
                    "focus_role": "current",
                    "readiness_status": "NOT_READY",
                    "drafting_eligible": False,
                    "beginner_primary": True,
                    "order": 1,
                    "chapter_range": [],
                    "created_at": now,
                    "updated_at": now,
                }
                await db.story_arcs.insert_one(arc)
            chapter = await db.chapter_plans.find_one({"project_id": pid}, sort=[("chapter_number", 1)])
            if not chapter:
                chapter = {
                    "project_id": pid,
                    "chapter_plan_id": str(uuid4()),
                    "arc_id": arc["arc_id"],
                    "chapter_number": 1,
                    "title": "Chapter 1",
                    "purpose": details,
                    "conflict": details,
                    "status": "planned",
                    "created_at": now,
                    "updated_at": now,
                }
                await db.chapter_plans.insert_one(chapter)
            await db.scene_plans.update_one(
                {"project_id": pid, "beginner_first_scene": True},
                {"$set": {
                    "arc_id": arc["arc_id"],
                    "chapter_plan_id": chapter["chapter_plan_id"],
                    "title": title or "Opening Scene",
                    "purpose": details,
                    "conflict": details,
                    "outcome": "",
                    "status": "planned",
                    "order": 1,
                    "beginner_first_scene": True,
                    "source_type": source,
                    "updated_at": now,
                }, "$setOnInsert": {
                    "scene_id": str(uuid4()),
                    "created_at": now,
                }},
                upsert=True,
            )


beginner_experience_service = BeginnerExperienceService()
