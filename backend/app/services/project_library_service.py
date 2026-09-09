"""Paginated commercial project-library projection."""
from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any, Dict

from bson import ObjectId


class ProjectLibraryService:
    def _status_query(self, status: str) -> Dict[str, Any]:
        if status == "archived":
            return {"status": "archived"}
        if status == "trashed":
            return {"status": "trashed"}
        if status == "all":
            return {}
        return {"status": {"$nin": ["archived", "trashed"]}}

    async def page(
        self,
        db,
        *,
        status: str = "active",
        search: str = "",
        page: int = 1,
        page_size: int = 24,
        favorites_only: bool = False,
    ) -> Dict[str, Any]:
        page = max(1, int(page))
        page_size = max(6, min(int(page_size), 100))
        query = self._status_query(status)
        if search.strip():
            query["$or"] = [
                {"title": {"$regex": re.escape(search.strip()), "$options": "i"}},
                {"project_name": {"$regex": re.escape(search.strip()), "$options": "i"}},
                {"story_title": {"$regex": re.escape(search.strip()), "$options": "i"}},
                {"genre": {"$regex": re.escape(search.strip()), "$options": "i"}},
                {"premise": {"$regex": re.escape(search.strip()), "$options": "i"}},
                {"idea_dump": {"$regex": re.escape(search.strip()), "$options": "i"}},
            ]
        if favorites_only:
            query["favorite"] = True
        total = await db.projects.count_documents(query)
        projects = await db.projects.find(query).sort([
            ("favorite", -1),
            ("last_opened_at", -1),
            ("updated_at", -1),
        ]).skip((page - 1) * page_size).limit(page_size).to_list(length=page_size)
        project_ids = [item["_id"] for item in projects]
        health_rows = await db.story_health_snapshots.find({
            "project_id": {"$in": project_ids},
            "snapshot_type": "current",
        }).to_list(length=page_size)
        completeness_rows = await db.narrative_completeness_snapshots.find({
            "project_id": {"$in": project_ids},
            "snapshot_type": "current",
        }).to_list(length=page_size)
        health = {row["project_id"]: row for row in health_rows}
        completeness = {row["project_id"]: row for row in completeness_rows}
        items = []
        for project in projects:
            health_row = health.get(project["_id"]) or {}
            completeness_row = completeness.get(project["_id"]) or {}
            items.append({
                "id": str(project["_id"]),
                "title": str(project.get("project_name") or project.get("title") or "Untitled project"),
                "project_name": str(project.get("project_name") or project.get("title") or "Untitled project"),
                "story_title": str(project.get("story_title") or "") or None,
                "status": str(project.get("status") or "draft"),
                "genre": str(project.get("genre") or ""),
                "tone": str(project.get("tone") or ""),
                "favorite": bool(project.get("favorite")),
                "created_at": project.get("created_at") or datetime.utcnow(),
                "updated_at": project.get("updated_at") or project.get("created_at") or datetime.utcnow(),
                "last_opened_at": project.get("last_opened_at"),
                "story_consistency": health_row.get("story_health_score"),
                "completeness": completeness_row.get("overall_completion"),
                "milestone": str(completeness_row.get("current_milestone") or "Getting Started"),
            })
        counts = {
            "active": await db.projects.count_documents({"status": {"$nin": ["archived", "trashed"]}}),
            "archived": await db.projects.count_documents({"status": "archived"}),
            "trashed": await db.projects.count_documents({"status": "trashed"}),
            "favorites": await db.projects.count_documents({"favorite": True, "status": {"$ne": "trashed"}}),
        }
        pages = max(1, math.ceil(total / page_size))
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": pages,
            "has_next": page < pages,
            "counts": counts,
        }

    async def set_favorite(self, db, project_id: str, favorite: bool) -> Dict[str, Any]:
        if not ObjectId.is_valid(project_id):
            raise ValueError("Invalid project ID")
        pid = ObjectId(project_id)
        result = await db.projects.update_one(
            {"_id": pid, "status": {"$ne": "trashed"}},
            {"$set": {"favorite": bool(favorite), "updated_at": datetime.utcnow()}},
        )
        if result.matched_count == 0:
            raise ValueError("Project not found")
        return {"project_id": project_id, "favorite": bool(favorite)}

    async def touch(self, db, project_id: str) -> Dict[str, Any]:
        if not ObjectId.is_valid(project_id):
            raise ValueError("Invalid project ID")
        result = await db.projects.update_one(
            {"_id": ObjectId(project_id), "status": {"$ne": "trashed"}},
            {"$set": {"last_opened_at": datetime.utcnow()}},
        )
        if result.matched_count == 0:
            raise ValueError("Project not found")
        return {"project_id": project_id, "touched": True}


project_library_service = ProjectLibraryService()
