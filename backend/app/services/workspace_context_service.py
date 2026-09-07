"""Workspace Context Service to retrieve current project, chapter, scene, and approval states."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from bson import ObjectId
from app.services.project_lifecycle_service import project_ownership_query

logger = logging.getLogger(__name__)

def _serialize(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {
            ("id" if key == "_id" else key): _serialize(item)
            for key, item in value.items()
        }
    return value

class WorkspaceContextService:
    """Consolidates active workspace context statistics and metrics for AI routing and onboarding."""
    
    async def get_workspace_context(self, db, project_id: str) -> Dict[str, Any]:
        if not ObjectId.is_valid(project_id):
            raise ValueError("Invalid project ID")
        pid = ObjectId(project_id)
        
        # 1. Fetch Project Info
        project = await db.projects.find_one({"_id": pid})
        if not project:
            raise ValueError("Project not found")

        # 2. Identify Active Chapter / Scene / Paragraph based on recent modifications
        active_chapter = None
        active_scene = None
        active_paragraph = None

        # Find most recently modified scene paragraph
        recent_paragraph = await db.scene_paragraphs.find_one(
            project_ownership_query(pid),
            sort=[("updated_at", -1)]
        )
        if recent_paragraph:
            active_paragraph = {
                "paragraph_id": recent_paragraph.get("paragraph_id"),
                "scene_id": recent_paragraph.get("scene_id"),
                "updated_at": recent_paragraph.get("updated_at")
            }
            
            # Match active scene
            scene = await db.scene_plans.find_one(
                {"project_id": pid, "scene_id": recent_paragraph.get("scene_id")}
            )
            if scene:
                active_scene = {
                    "scene_id": scene.get("scene_id"),
                    "title": scene.get("title") or f"Scene {scene.get('scene_number', '')}",
                    "chapter_plan_id": scene.get("chapter_plan_id")
                }
                
                # Match chapter plan
                chapter = await db.chapter_plans.find_one(
                    {"project_id": pid, "chapter_plan_id": scene.get("chapter_plan_id")}
                )
                if chapter:
                    active_chapter = {
                        "chapter_plan_id": chapter.get("chapter_plan_id"),
                        "title": chapter.get("title") or f"Chapter {chapter.get('chapter_number', '')}"
                    }

        # Fallbacks if no paragraphs are updated yet
        if not active_scene:
            scene = await db.scene_plans.find_one({"project_id": pid})
            if scene:
                active_scene = {
                    "scene_id": scene.get("scene_id"),
                    "title": scene.get("title") or "First Scene",
                    "chapter_plan_id": scene.get("chapter_plan_id")
                }
                chapter = await db.chapter_plans.find_one(
                    {"project_id": pid, "chapter_plan_id": scene.get("chapter_plan_id")}
                )
                if chapter:
                    active_chapter = {
                        "chapter_plan_id": chapter.get("chapter_plan_id"),
                        "title": chapter.get("title") or "First Chapter"
                    }

        # 3. Pending Approvals
        pending_paragraphs = await db.scene_paragraphs.count_documents({
            **project_ownership_query(pid),
            "approval_state": {"$ne": "approved"}
        })
        pending_canon = await db.canon_proposals.count_documents({
            "project_id": pid,
            "status": "pending"
        })
        pending_canon += await db.proposed_canon.count_documents({
            "project_id": {"$in": [pid, str(pid)]},
            "status": {"$in": ["proposed", "pending"]},
        })

        # 4. Story Health Score
        health_snapshot = await db.story_health_snapshots.find_one({
            "project_id": pid,
            "snapshot_type": "current"
        })
        health_score = health_snapshot.get("story_health_score") if health_snapshot else None
        metrics = (health_snapshot or {}).get("metrics", {})
        health_status = "available" if health_score is not None else "not_analyzed"

        # 5. Unresolved Warnings
        canon_conflicts = await db.canon_conflicts.count_documents({
            "project_id": pid,
            "status": {"$in": ["open", "acknowledged"]}
        })
        continuity_warnings = await db.continuity_reports.count_documents({
            "project_id": pid,
            "result": {"$in": ["WARNING", "FAIL"]}
        })

        unresolved_warnings = []
        if canon_conflicts > 0:
            unresolved_warnings.append(f"{canon_conflicts} open canon conflicts exist")
        if continuity_warnings > 0:
            unresolved_warnings.append(f"{continuity_warnings} continuity failures/warnings detected")

        # 6. Suggested Action Logic
        suggested_next_action = {
            "action": "plan_paragraphs",
            "reason": "Initialize paragraph skeletons to start planning chapters.",
            "target_id": None
        }
        
        if canon_conflicts > 0:
            suggested_next_action = {
                "action": "resolve_canon",
                "reason": "Resolve open conflicts in story bible facts.",
                "target_id": project_id
            }
        elif pending_canon > 0:
            suggested_next_action = {
                "action": "approve_canon",
                "reason": "Approve pending proposed canon facts to compile manuscript.",
                "target_id": project_id
            }
        elif active_paragraph:
            scene_title = (active_scene or {}).get("title") or "your active scene"
            chapter_title = (active_chapter or {}).get("title") or "the current chapter"
            suggested_next_action = {
                "action": "write_prose",
                "reason": f"Continue drafting '{scene_title}' in '{chapter_title}'.",
                "target_id": (active_scene or {}).get("scene_id")
            }

        return _serialize({
            "active_project": {
                "id": str(project.get("_id")),
                "title": project.get("title") or "Untitled Project"
            },
            "active_chapter": active_chapter,
            "active_scene": active_scene,
            "active_paragraph": active_paragraph,
            "pending_approvals": {
                "paragraphs": pending_paragraphs,
                "canon": pending_canon
            },
            "story_health": {
                "score": health_score,
                "metrics": metrics,
                "status": health_status,
            },
            "unresolved_warnings": unresolved_warnings,
            "suggested_next_action": suggested_next_action
        })

workspace_context_service = WorkspaceContextService()
