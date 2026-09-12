"""Small manual/import facade for empty RC6 workspaces.

The service writes the established collections and rebuilds the existing Story
Bible projection; it does not introduce a parallel story model.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from bson import ObjectId

from app.services.narrative_completeness_service import narrative_completeness_service
from app.services.project_event_service import emit_project_event
from app.services.story_bible_service import rebuild_story_bible


class WorkspaceEntryService:
    async def create(
        self,
        db,
        project_id: str,
        *,
        area: str,
        title: str,
        details: str,
        source_mode: str,
    ) -> Dict[str, Any]:
        if not ObjectId.is_valid(project_id):
            raise ValueError("Invalid project ID")
        pid = ObjectId(project_id)
        if not await db.projects.find_one({"_id": pid, "status": {"$ne": "trashed"}}):
            raise ValueError("Project not found")
        now = datetime.utcnow()
        record_id = str(uuid4())
        source_type = f"author_{source_mode}"
        target = {
            "character": "characters",
            "world": "world",
            "timeline": "timeline",
            "power": "power",
            "relationship": "relationships",
            "theme": "themes",
            "plot_thread": "threads",
            "arc": "arcs",
            "mystery": "mysteries",
            "faction": "factions",
            "scene": "drafting",
        }[area]

        if area == "character":
            await db.character_bibles.insert_one({
                "project_id": pid,
                "character_id": record_id,
                "name": title,
                "role": "supporting",
                "description": details,
                "motivations": [details] if details else [],
                "current_status": "active",
                "source_type": source_type,
                "created_at": now,
                "updated_at": now,
            })
        elif area == "world":
            await db.world_bibles.update_one(
                {"project_id": pid},
                {"$set": {"setting": title, "summary": details, "updated_at": now, "source_type": source_type},
                 "$addToSet": {"world_rules": details or title},
                 "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
        elif area == "timeline":
            await db.timeline_entries.insert_one({
                "project_id": pid,
                "entry_id": record_id,
                "title": title,
                "event": details,
                "certainty": "known",
                "importance": "major",
                "order": await db.timeline_entries.count_documents({"project_id": pid}) + 1,
                "source_type": source_type,
                "created_at": now,
                "updated_at": now,
            })
        elif area == "power":
            await db.power_systems.update_one(
                {"project_id": pid},
                {"$set": {"name": title, "summary": details, "updated_at": now, "source_type": source_type},
                 "$addToSet": {"rules": details or title},
                 "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
        elif area == "relationship":
            names = [item.strip() for item in title.replace("/", "&").split("&") if item.strip()]
            await db.relationship_graphs.insert_one({
                "project_id": pid,
                "relationship_id": record_id,
                "character_a": names[0] if names else title,
                "character_b": names[1] if len(names) > 1 else "Undecided",
                "relationship": details or "Relationship to define",
                "status": "active",
                "source_type": source_type,
                "created_at": now,
                "updated_at": now,
            })
        elif area == "theme":
            await db.theme_registry.update_one(
                {"project_id": pid},
                {"$addToSet": {"themes": title},
                 "$set": {"updated_at": now, "source_type": source_type},
                 "$setOnInsert": {"created_at": now, "motifs": [], "symbols": []}},
                upsert=True,
            )
        elif area == "plot_thread":
            await db.plot_threads.insert_one({
                "project_id": pid,
                "thread_id": record_id,
                "title": title,
                "description": details,
                "status": "open",
                "references": [],
                "source_type": source_type,
                "created_at": now,
                "updated_at": now,
            })
        elif area == "arc":
            await db.story_arcs.insert_one({
                "project_id": pid,
                "arc_id": record_id,
                "title": title,
                "purpose": details,
                "goal": details,
                "conflict": details,
                "stakes": details,
                "approval_status": "draft",
                "development_status": "idea",
                "focus_role": "future",
                "chapter_range": [],
                "readiness_status": "NOT_READY",
                "drafting_eligible": False,
                "arc_maturity_score": 0,
                "order": await db.story_arcs.count_documents({"project_id": pid}) + 1,
                "source_type": source_type,
                "created_at": now,
                "updated_at": now,
            })
        elif area == "mystery":
            await db.mystery_registry.insert_one({
                "project_id": pid,
                "mystery_id": record_id,
                "question": title,
                "truth": details,
                "status": "open",
                "known_clues": [],
                "hidden_clues": [],
                "source_type": source_type,
                "created_at": now,
                "updated_at": now,
            })
        elif area == "faction":
            await db.factions.insert_one({
                "project_id": pid,
                "faction_id": record_id,
                "name": title,
                "agenda": details,
                "goals": [details] if details else [],
                "source_type": source_type,
                "created_at": now,
                "updated_at": now,
            })
        elif area == "scene":
            arc = await db.story_arcs.find_one({"project_id": pid}, sort=[("order", 1)])
            if not arc:
                raise ValueError("Create an arc before adding a scene")
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
            await db.scene_plans.insert_one({
                "project_id": pid,
                "scene_id": record_id,
                "arc_id": arc["arc_id"],
                "chapter_plan_id": chapter["chapter_plan_id"],
                "title": title,
                "purpose": details,
                "conflict": details,
                "outcome": "",
                "status": "planned",
                "order": await db.scene_plans.count_documents({"project_id": pid}) + 1,
                "source_type": source_type,
                "created_at": now,
                "updated_at": now,
            })
        else:
            raise ValueError("Unsupported workspace area")

        bible = await rebuild_story_bible(db, project_id)
        await narrative_completeness_service.calculate(db, project_id)
        await emit_project_event(
            db,
            project_id,
            "workspace_entry_created",
            payload={"area": area, "record_id": record_id, "target": target},
        )
        return {
            "area": area,
            "record_id": record_id,
            "target": target,
            "story_bible_version": int(bible.get("version") or 0),
            "message": f"{title} was added to {target.replace('-', ' ')}.",
        }


workspace_entry_service = WorkspaceEntryService()
