"""One post-mutation refresh boundary for shared project intelligence."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from bson import ObjectId

from app.services.project_event_service import emit_project_event
from app.services.story_bible_service import rebuild_story_bible


class ProjectIntelligenceCoordinator:
    async def after_change(
        self,
        db,
        project_id: str,
        event_type: str,
        payload: Dict[str, Any],
        *,
        touch_project: bool = False,
    ) -> Dict[str, Any]:
        """Refresh shared knowledge once and emit one versioned project event."""
        if touch_project:
            await db.projects.update_one(
                {"_id": ObjectId(project_id)},
                {"$set": {"updated_at": datetime.utcnow()}},
            )
        if event_type in {"chapter_draft_approved", "scene_draft_approved"}:
            # Discovery chapters have no scene plan, so the existing narrative
            # engine must be refreshed from the shared chapter-intelligence
            # source after approval. This remains a projection refresh, not a
            # second graph or authority.
            from app.services.narrative_analysis_engine import narrative_analysis_engine
            await narrative_analysis_engine.analyze(db, project_id, force=True)
        bible = await rebuild_story_bible(db, project_id)
        await emit_project_event(
            db,
            project_id,
            event_type,
            cycle_number=int(bible.get("cycle_number") or 0),
            payload={**payload, "story_bible_version": bible.get("version")},
        )
        from app.services.workspace_bootstrap_service import (
            workspace_bootstrap_service,
        )

        await workspace_bootstrap_service.invalidate(db, project_id)
        return bible


project_intelligence_coordinator = ProjectIntelligenceCoordinator()
