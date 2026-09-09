"""Author-facing project evolution and Story Health change projections."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from bson import ObjectId


DOMAIN_LABELS = {
    "character": "Character consistency", "canon": "Canon", "timeline": "Timeline",
    "plot": "Plot threads", "pacing": "Pacing", "continuity": "Continuity",
    "balance": "Narrative balance", "overall": "Overall Story Health",
}

EVENT_COPY = {
    "project_created": ("Project created", "You created the project and established its starting point.", "dashboard", ["Project"]),
    "project_updated": ("Project details updated", "You refined the project's foundation.", "vision", ["Story Vision"]),
    "story_vision_updated": ("Story Vision updated", "The creative direction was clarified.", "vision", ["Story Vision"]),
    "canon_proposal_created": ("Canon proposal added", "A possible story fact entered the review queue.", "canon-queue", ["Canon"]),
    "canon_proposal_reviewed": ("Canon proposal reviewed", "An author decision was recorded and dependent knowledge refreshed.", "canon-queue", ["Canon", "Story Bible", "Story Intelligence"]),
    "shared_narrative_context_updated": ("Project knowledge updated", "An author answer became reusable project knowledge.", "knowledge", ["Story Bible", "Canon", "Knowledge Graph"]),
    "arc_changed": ("Story arc updated", "An arc's structure or status changed.", "arcs", ["Arcs"]),
    "chapter_plan_changed": ("Chapter plan updated", "A planned chapter changed.", "arc-development", ["Chapters", "Arcs"]),
    "scene_plan_changed": ("Scene plan updated", "A planned scene changed.", "arc-development", ["Scenes", "Arcs"]),
    "timeline_v2_changed": ("Story chronology updated", "An event inside the novel was changed.", "timeline", ["Story Timeline", "Story Health"]),
    "character_progression_changed": ("Character journey updated", "A character's planned progression changed.", "characters", ["Character Intelligence"]),
    "knowledge_changed": ("Story knowledge updated", "Approved project knowledge changed.", "knowledge", ["Story Bible", "Knowledge Graph"]),
    "scene_draft_generated": ("Scene draft created", "NovelForge produced a governed scene draft for review.", "drafting", ["Drafting"]),
    "chapter_draft_generated": ("Chapter draft created", "NovelForge produced a governed chapter draft for review.", "drafting", ["Drafting"]),
    "scene_draft_approved": ("Scene draft approved", "You approved a scene version as the active writing source.", "drafting", ["Drafting", "Story Intelligence"]),
    "chapter_draft_approved": ("Chapter draft approved", "You approved an assembled chapter version.", "drafting", ["Drafting", "Story Intelligence"]),
    "scene_draft_changed": ("Scene draft status changed", "You changed a scene draft's review status.", "drafting", ["Drafting"]),
    "chapter_draft_changed": ("Chapter draft status changed", "You changed a chapter draft's review status.", "drafting", ["Drafting"]),
    "manuscript_approved": ("Manuscript approved", "A manuscript version passed the author approval boundary.", "manuscript", ["Manuscript", "Readiness"]),
}


def _iso(value: Any) -> str:
    return value.isoformat() if isinstance(value, datetime) else str(value or "")


class ProjectEvolutionService:
    async def _project(self, db, project_id: str):
        if not ObjectId.is_valid(project_id):
            raise ValueError("Invalid project ID")
        pid = ObjectId(project_id)
        project = await db.projects.find_one({"_id": pid})
        if not project:
            raise ValueError("Project not found")
        return pid, project

    def _event_entry(
        self,
        event: Dict[str, Any],
        chapters: Dict[str, Dict[str, Any]] | None = None,
        scenes: Dict[str, Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        event_type = str(event.get("event_type") or "project_updated")
        label, summary, destination, systems = EVENT_COPY.get(
            event_type,
            (event_type.replace("_", " ").title(), "The project changed and affected work was refreshed.", "workflow", ["Project Activity"]),
        )
        payload = event.get("payload") or {}
        chapter = (chapters or {}).get(str(payload.get("chapter_plan_id") or "")) or {}
        scene = (scenes or {}).get(str(payload.get("scene_id") or "")) or {}
        chapter_number = int(chapter.get("chapter_number") or payload.get("chapter_number") or 0)
        scene_order = int(scene.get("order") or payload.get("scene_order") or 0)
        location = ""
        if chapter_number:
            location = f"Chapter {chapter_number}"
        if scene_order:
            location += f" Scene {scene_order}"
        if event_type == "scene_draft_generated" and location:
            label = f"{location} draft generated"
            summary = f"NovelForge created a review draft for {scene.get('title') or location}."
        elif event_type == "scene_draft_approved" and location:
            label = f"{location} approved"
            summary = f"You approved {scene.get('title') or location} as the active scene version."
        elif event_type == "chapter_draft_generated" and chapter_number:
            label = f"Chapter {chapter_number} assembled"
            summary = f"NovelForge assembled {chapter.get('title') or f'Chapter {chapter_number}'} from approved scenes."
        elif event_type == "canon_proposal_created" and payload.get("subject"):
            label = f"New canon proposal: {payload.get('subject')}"
            summary = f"A possible {str(payload.get('field') or 'story fact').replace('_', ' ')} entered the author review queue."
        return {
            "entry_id": f"event:{event.get('_id')}", "date": _iso(event.get("created_at")),
            "action": label, "summary": summary, "actor": "You" if event_type in {
                "project_created", "project_updated", "story_vision_updated", "canon_proposal_reviewed",
                "shared_narrative_context_updated", "arc_changed", "chapter_plan_changed",
                "scene_plan_changed", "timeline_v2_changed", "character_progression_changed",
            } else "NovelForge",
            "affected_systems": systems, "destination": destination,
            "chapter_number": chapter_number or None,
            "scene_order": scene_order or None,
            "scene_label": scene.get("title"),
            "changes": {"story_health": payload.get("story_health_delta"), "canon": payload.get("canon_delta"), "timeline": payload.get("timeline_delta")},
            "replay": {"event": label, "outcome": summary, "destination": destination},
        }

    async def timeline(self, db, project_id: str, limit: int = 300) -> Dict[str, Any]:
        pid, project = await self._project(db, project_id)
        events = await db.project_events.find({"project_id": pid}).sort("created_at", -1).to_list(length=max(1, min(limit, 1000)))
        chapter_ids = list({str((event.get("payload") or {}).get("chapter_plan_id") or "") for event in events} - {""})
        scene_ids = list({str((event.get("payload") or {}).get("scene_id") or "") for event in events} - {""})
        chapter_rows = await db.chapter_plans.find({"project_id": pid, "chapter_plan_id": {"$in": chapter_ids}}).to_list(length=5000)
        scene_rows = await db.scene_plans.find({"project_id": pid, "scene_id": {"$in": scene_ids}}).to_list(length=10000)
        chapter_map = {str(item.get("chapter_plan_id")): item for item in chapter_rows}
        scene_map = {str(item.get("scene_id")): item for item in scene_rows}
        entries = [self._event_entry(event, chapter_map, scene_map) for event in events]
        created_marker = any(str(event.get("event_type")) == "project_created" for event in events)
        if not created_marker:
            entries.append({
                "entry_id": f"project:{project_id}", "date": _iso(project.get("created_at")),
                "action": "Project created", "summary": "You created the project and established its starting point.",
                "actor": "You", "affected_systems": ["Project"], "destination": "dashboard",
                "changes": {"story_health": None, "canon": None, "timeline": None},
                "replay": {"event": "Project created", "outcome": "The novel workspace began here.", "destination": "dashboard"},
            })
        completeness = await db.narrative_completeness_history.find({"project_id": pid}).sort("calculated_at", 1).to_list(length=1000)
        achieved: set[str] = set()
        for snapshot in completeness:
            for gate in snapshot.get("milestones") or []:
                gate_id = str(gate.get("gate_id") or "")
                if gate.get("achieved") and gate_id not in achieved:
                    achieved.add(gate_id)
                    entries.append({
                        "entry_id": f"milestone:{gate_id}:{snapshot.get('snapshot_id')}",
                        "date": _iso(snapshot.get("calculated_at")), "action": f"{gate.get('label')} reached",
                        "summary": "The project satisfied every current criterion for this production milestone.",
                        "actor": "NovelForge", "affected_systems": ["Creation Guide", "Narrative Completeness"],
                        "destination": "guide", "changes": {"story_health": None, "canon": None, "timeline": None},
                        "replay": {"event": f"{gate.get('label')} reached", "outcome": "All milestone blockers were cleared at this point.", "destination": "guide"},
                    })
        entries.sort(key=lambda item: item.get("date") or "", reverse=True)
        return {"project_id": project_id, "entries": entries[:limit], "count": min(len(entries), limit), "story_timeline_is_separate": True}

    async def explainability(self, db, project_id: str, limit: int = 100) -> Dict[str, Any]:
        pid, _ = await self._project(db, project_id)
        rows = await db.narrative_analysis_history.find({"project_id": pid}).sort("calculated_at", 1).to_list(length=max(2, min(limit + 1, 501)))
        changes = []
        for previous, current in zip(rows, rows[1:]):
            old_scores, new_scores = previous.get("scores") or {}, current.get("scores") or {}
            previous_findings = {item.get("finding_id"): item for item in previous.get("findings") or [] if item.get("finding_id")}
            current_findings = {item.get("finding_id"): item for item in current.get("findings") or [] if item.get("finding_id")}
            introduced = [current_findings[key] for key in current_findings.keys() - previous_findings.keys()]
            resolved = [previous_findings[key] for key in previous_findings.keys() - current_findings.keys()]
            score_changes = [
                {"category": domain, "label": DOMAIN_LABELS.get(domain, domain.title()), "from": old_scores.get(domain), "to": new_scores.get(domain), "delta": int(new_scores.get(domain, 0)) - int(old_scores.get(domain, 0))}
                for domain in sorted(set(old_scores) | set(new_scores))
                if old_scores.get(domain) != new_scores.get(domain)
            ]
            reasons = [
                {"direction": "improved", "domain": item.get("domain"), "message": f"Resolved: {item.get('explanation')}", "finding_id": item.get("finding_id"), "destination": self._domain_destination(item.get("domain"))}
                for item in resolved
            ] + [
                {"direction": "declined", "domain": item.get("domain"), "message": f"New concern: {item.get('explanation')}", "finding_id": item.get("finding_id"), "destination": self._domain_destination(item.get("domain"))}
                for item in introduced
            ]
            changes.append({
                "change_id": f"{previous.get('analysis_id')}:{current.get('analysis_id')}",
                "date": _iso(current.get("calculated_at")), "from_analysis": previous.get("analysis_id"),
                "to_analysis": current.get("analysis_id"), "overall": {
                    "from": old_scores.get("overall"), "to": new_scores.get("overall"),
                    "delta": int(new_scores.get("overall", 0)) - int(old_scores.get("overall", 0)),
                },
                "score_changes": score_changes, "reasons": reasons,
                "what_happened": "Story Health changed after NovelForge refreshed the approved project evidence." if score_changes else "The analysis refreshed without changing Story Health.",
                "why_it_matters": "This comparison shows which resolved or newly detected concerns moved the score.",
                "suggested_next_step": (reasons[0].get("destination") if reasons else "story-health"),
            })
        changes.reverse()
        return {"project_id": project_id, "changes": changes[:limit], "count": min(len(changes), limit)}

    @staticmethod
    def _domain_destination(domain: Any) -> str:
        return {"character": "characters", "canon": "canon", "timeline": "timeline", "plot": "threads", "pacing": "story-health", "continuity": "story-health", "balance": "story-health"}.get(str(domain), "story-health")


project_evolution_service = ProjectEvolutionService()
