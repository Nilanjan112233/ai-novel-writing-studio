"""Author-facing writing workspace assembled from existing NovelForge truth."""
from __future__ import annotations

from datetime import datetime, timedelta
import difflib
from typing import Any, Dict

from bson import ObjectId

from app.services.draft_validation_service import draft_validation_service


def _iso(value: Any) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None


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


def _violations(report: Dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key, items in report.items():
        if key.endswith("_violations") and isinstance(items, list):
            values.extend(str(item) for item in items if item)
    return list(dict.fromkeys(values))


class WritingExperienceService:
    @staticmethod
    def _candidate_groups(extraction: Dict[str, Any] | None) -> Dict[str, list[str]]:
        grouped: Dict[str, list[str]] = {}
        noise = {"the", "and", "one", "two", "three", "four", "last", "said", "did", "open", "because", "stay", "toward", "you", "her", "his", "their", "nothing", "found"}
        for candidate in (extraction or {}).get("candidates") or []:
            kind = str(candidate.get("candidate_type") or candidate.get("type") or "story detail")
            description = candidate.get("description") or candidate.get("value") or candidate.get("subject") or ""
            if isinstance(description, dict):
                description = candidate.get("subject") or str(description)
            text = " ".join(str(description).split()).strip(" .,:;[]")
            if not text or text.casefold() in noise or text.casefold().startswith(("and ", "chapter ", "let ", "keep ", "end ")):
                continue
            if len(text) < 3 or text in grouped.get(kind, []):
                continue
            grouped.setdefault(kind, []).append(text)
        return grouped

    async def state(self, db, project_id: str) -> Dict[str, Any]:
        """Return one author-facing projection over structured and Discovery writing.

        This is a read model only. Drafts, approvals, intelligence, canon, and
        manuscript records remain owned by their existing collections/services.
        """
        pid = ObjectId(project_id)
        project = await db.projects.find_one({"_id": pid})
        if not project:
            raise ValueError("Project not found")

        chapter_docs = await db.chapter_drafts.find({"project_id": pid}).sort(
            [("chapter_number", 1), ("version_number", 1), ("created_at", 1)]
        ).to_list(length=10000)
        active_chapters = [item for item in chapter_docs if item.get("active", True)]
        by_number: Dict[int, list[Dict[str, Any]]] = {}
        for item in active_chapters:
            number = int(item.get("chapter_number") or 0)
            if number:
                by_number.setdefault(number, []).append(item)

        extractions = await db.discovery_extractions.find({"project_id": pid}).sort(
            [("chapter_number", 1), ("created_at", -1)]
        ).to_list(length=10000)
        extraction_by_draft = {str(item.get("source_draft_id")): item for item in extractions}
        extraction_by_number: Dict[int, Dict[str, Any]] = {}
        for item in extractions:
            number = int(item.get("chapter_number") or 0)
            if number and number not in extraction_by_number:
                extraction_by_number[number] = item

        intelligence = await db.chapter_intelligence.find({"project_id": pid}).sort(
            [("chapter_number", 1), ("chapter_draft_version", -1), ("updated_at", -1)]
        ).to_list(length=10000)
        intelligence_by_draft: Dict[str, Dict[str, Any]] = {}
        intelligence_by_number: Dict[int, Dict[str, Any]] = {}
        for item in intelligence:
            draft_key = str(item.get("chapter_draft_id") or item.get("draft_id") or "")
            number = int(item.get("chapter_number") or 0)
            if draft_key and draft_key not in intelligence_by_draft:
                intelligence_by_draft[draft_key] = item
            if number and number not in intelligence_by_number:
                intelligence_by_number[number] = item

        reports = await db.continuity_reports.find({
            "project_id": pid,
            "subject_type": "chapter_draft",
        }).sort("created_at", -1).to_list(length=10000)
        report_by_draft: Dict[str, Dict[str, Any]] = {}
        for item in reports:
            subject_id = str(item.get("subject_id") or item.get("draft_id") or "")
            if subject_id and subject_id not in report_by_draft:
                report_by_draft[subject_id] = item

        chapter_rows: list[Dict[str, Any]] = []
        for number in sorted(by_number):
            versions = by_number[number]
            active = next((item for item in reversed(versions) if item.get("active", True)), versions[-1])
            draft_id = str(active.get("draft_id") or "")
            extraction = extraction_by_draft.get(draft_id) or extraction_by_number.get(number)
            intel = intelligence_by_draft.get(draft_id) or intelligence_by_number.get(number)
            report = report_by_draft.get(draft_id)
            chapter_rows.append({
                "chapter_number": number,
                "title": active.get("title") or f"Chapter {number}",
                "workflow_mode": active.get("workflow_mode") or ("discovery" if active.get("discovery_id") else "structured"),
                "status": active.get("status") or "draft",
                "active_version": int(active.get("version_number") or 1),
                "version_count": len(versions),
                "draft_id": draft_id,
                "word_count": int(active.get("word_count") or len(str(active.get("generated_text") or "").split())),
                "updated_at": _iso(active.get("updated_at")) or _iso(active.get("created_at")),
                "approved_at": _iso(active.get("approved_at")),
                "validation_result": active.get("validation_result") or (report or {}).get("result") or "NOT_ANALYZED",
                "continuity_report_id": active.get("continuity_report_id") or (report or {}).get("report_id"),
                "extraction": {
                    "status": (extraction or {}).get("status") or ("not_started" if active.get("status") != "approved" else "pending"),
                    "candidate_count": len((extraction or {}).get("candidates") or []),
                    "extraction_id": (extraction or {}).get("extraction_id"),
                    "updated_at": _iso((extraction or {}).get("updated_at")),
                },
                "intelligence": {
                    "status": "ready" if intel else ("pending" if active.get("status") == "approved" else "not_started"),
                    "intelligence_id": (intel or {}).get("intelligence_id"),
                    "finding_count": len((intel or {}).get("findings") or []),
                },
            })

        latest = chapter_rows[-1] if chapter_rows else None
        latest_approved = next((item for item in reversed(chapter_rows) if item["status"] == "approved"), None)
        pending_review = sum(1 for item in chapter_rows if item["status"] in {"draft", "review"})
        enrichment_pending = sum(1 for item in chapter_rows if item["status"] == "approved" and item["extraction"]["status"] != "candidate")
        structured_plans = await db.chapter_plans.count_documents({"project_id": pid})
        structured_scenes = await db.scene_plans.count_documents({"project_id": pid})
        pending_proposals = await db.canon_proposals.count_documents({"project_id": pid, "status": "pending"})
        pending_decisions = await db.questions.count_documents({"project_id": pid, "answered": {"$ne": True}, "blocking": True})
        next_action = "Start your first chapter"
        next_target = "story-studio"
        if pending_review:
            next_action = f"Review Chapter {next((item['chapter_number'] for item in chapter_rows if item['status'] in {'draft', 'review'}), latest['chapter_number'] if latest else 1)}"
            next_target = "writing"
        elif latest_approved:
            next_action = f"Continue with Chapter {latest_approved['chapter_number'] + 1}"
            next_target = "writing"
        elif structured_plans or structured_scenes:
            next_action = "Continue structured drafting"
            next_target = "drafting"
        if enrichment_pending:
            next_action = "Finish updating story context"
            next_target = "writing"
        return _serialize({
            "project_id": project_id,
            "workflow_mode": "discovery" if chapter_rows and not structured_plans and not structured_scenes else ("mixed" if chapter_rows else "structured"),
            "chapter_count": len(chapter_rows),
            "latest_chapter": latest,
            "latest_approved_chapter": latest_approved,
            "chapters": chapter_rows,
            "structured": {"chapter_plans": structured_plans, "scene_plans": structured_scenes},
            "pending": {"review": pending_review, "enrichment": enrichment_pending, "canon_proposals": pending_proposals, "author_decisions": pending_decisions},
            "next_action": {"label": next_action, "target": next_target},
            "last_activity_at": (latest or {}).get("updated_at") or _iso(project.get("updated_at")) or _iso(project.get("created_at")),
        })

    async def chapter_context(self, db, project_id: str, chapter_number: int) -> Dict[str, Any]:
        """Compact author-facing view of context relevant to a chapter."""
        pid = ObjectId(project_id)
        extraction = await db.discovery_extractions.find_one({"project_id": pid, "chapter_number": chapter_number}, sort=[("created_at", -1)])
        intel = await db.chapter_intelligence.find_one({"project_id": pid, "chapter_number": chapter_number, "active": True}, sort=[("updated_at", -1)])
        packet = await db.context_packets.find_one({"project_id": pid, "target_artifact": f"discovery-chapter:{chapter_number}"}, sort=[("created_at", -1)])
        draft = await db.chapter_drafts.find_one(
            {"project_id": pid, "chapter_number": chapter_number, "status": "approved"},
            sort=[("version_number", -1), ("updated_at", -1)],
        )
        candidates = list((extraction or {}).get("candidates") or [])
        grouped = self._candidate_groups(extraction)
        retrieved = []
        source_labels = {"project": "Story premise", "chapter_intelligence": "Earlier chapter context", "story_bible": "Story Bible", "canon": "Approved canon", "decision": "Author decision"}
        for item in ((packet or {}).get("packet") or {}).get("retrieved_memory") or []:
            source_type = str(item.get("source_type") or "Story record")
            content = " ".join(str(item.get("content") or "").replace("[]", "").split())
            if not content:
                continue
            if source_type == "chapter_intelligence":
                content = content.lstrip("0123456789 ")
                if content.startswith("Chapter "):
                    content = content.split(":", 1)[-1].strip()
            retrieved.append({"source_type": source_labels.get(source_type, source_type.replace("_", " ").title()), "content": content[:420], "score": item.get("score")})
        previous_extraction = await db.discovery_extractions.find_one(
            {"project_id": pid, "chapter_number": {"$lt": chapter_number}},
            sort=[("chapter_number", -1), ("created_at", -1)],
        )
        previous_intelligence = await db.chapter_intelligence.find_one(
            {"project_id": pid, "chapter_number": {"$lt": chapter_number}, "active": True},
            sort=[("chapter_number", -1), ("updated_at", -1)],
        )
        canon_changes = await db.canon_proposals.count_documents({
            "project_id": pid,
            "status": {"$in": ["approved", "accepted"]},
            "$or": [{"affected_chapters": chapter_number}, {"chapter_number": chapter_number}],
        })
        return _serialize({
            "project_id": project_id,
            "chapter_number": chapter_number,
            "learned_from_chapter": {"candidate_status": (extraction or {}).get("status") or "not_available", "groups": grouped, "candidate_count": len(candidates)},
            "chapter_intelligence": {"summary": (intel or {}).get("chapter_summary"), "events": (intel or {}).get("important_events") or [], "open_questions": (intel or {}).get("open_questions") or [], "characters": (intel or {}).get("characters_present") or [], "relationships": (intel or {}).get("relationships") or [], "artifacts": (intel or {}).get("artifacts") or []},
            "approved_prose_excerpt": str((draft or {}).get("generated_text") or (draft or {}).get("content") or "")[:2400],
            "carried_into_generation": retrieved,
            "approval_change": {
                "before": {
                    "source": f"Earlier approved context before Chapter {chapter_number}",
                    "candidate_groups": self._candidate_groups(previous_extraction),
                    "summary": (previous_intelligence or {}).get("chapter_summary"),
                },
                "new_information": {"candidate_groups": grouped, "candidate_status": (extraction or {}).get("status") or "not_available"},
                "carried_forward": retrieved[:8],
                "canon_changed": bool(canon_changes),
                "canon_change_count": canon_changes,
                "open_threads": (intel or {}).get("open_questions") or [],
                "next_chapter_influence": retrieved[:6] or [{"source_type": "Approved story context", "content": "Use approved prose and governed story records when continuing."}],
            },
            "source": "existing chapter drafts, discovery extraction, chapter intelligence, and context packets",
        })

    async def compare_chapter_versions(self, db, project_id: str, chapter_number: int) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        versions = await db.chapter_drafts.find({"project_id": pid, "chapter_number": chapter_number}).sort(
            [("version_number", 1), ("created_at", 1)]
        ).to_list(length=1000)
        if len(versions) < 2:
            return {"chapter_number": chapter_number, "available": False, "message": "This chapter has one saved version. Create a revision to compare versions."}
        left, right = versions[-2], versions[-1]
        left_text = str(left.get("generated_text") or left.get("content") or "")
        right_text = str(right.get("generated_text") or right.get("content") or "")
        diff = "".join(difflib.unified_diff(left_text.splitlines(True), right_text.splitlines(True), fromfile=f"Version {left.get('version_number', 1)}", tofile=f"Version {right.get('version_number', 1)}"))
        return _serialize({
            "chapter_number": chapter_number,
            "available": True,
            "left": {"draft_id": left.get("draft_id"), "version": left.get("version_number"), "status": left.get("status"), "word_count": left.get("word_count")},
            "right": {"draft_id": right.get("draft_id"), "version": right.get("version_number"), "status": right.get("status"), "word_count": right.get("word_count"), "active": right.get("active", False)},
            "diff": diff[:12000],
            "source": "existing chapter draft lineage",
        })

    async def activity(self, db, project_id: str) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        items: list[Dict[str, Any]] = []
        jobs = await db.story_studio_jobs.find({"project_id": pid}).sort("updated_at", -1).to_list(length=20)
        for job in jobs:
            items.append({"kind": "story_studio", "label": "Story Studio request", "status": job.get("status"), "summary": job.get("query") or "Story Studio work", "updated_at": job.get("updated_at") or job.get("created_at"), "safe_prose": True, "retryable": job.get("status") == "failed"})
        analyses = await db.narrative_analysis_jobs.find({"project_id": pid}).sort("created_at", -1).to_list(length=10)
        for job in analyses:
            items.append({"kind": "narrative_analysis", "label": "Story context refresh", "status": job.get("status"), "summary": "Updating continuity and Story Health", "updated_at": job.get("updated_at") or job.get("created_at"), "safe_prose": True, "retryable": job.get("status") in {"failed", "interrupted"}})
        drafts = await db.chapter_drafts.find({"project_id": pid, "status": "approved", "enrichment_status": {"$in": ["pending", "running", "failed"]}}).sort("updated_at", -1).to_list(length=20)
        for draft in drafts:
            status = draft.get("enrichment_status")
            items.append({"kind": "chapter_enrichment", "label": f"Chapter {draft.get('chapter_number')} story context", "status": status, "summary": "Approved prose is safe; updating extracted story context", "updated_at": draft.get("updated_at") or draft.get("approved_at"), "safe_prose": True, "retryable": status == "failed"})
        items.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
        return _serialize({
            "items": items[:30],
            "running": [item for item in items if item.get("status") in {"queued", "running", "pending"}],
            "attention": [item for item in items if item.get("status") in {"failed", "interrupted", "waiting"}],
            "source": "durable Story Studio, chapter enrichment, and Narrative Analysis job records",
        })
    async def dashboard(self, db, project_id: str) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        project = await db.projects.find_one({"_id": pid})
        if not project:
            raise ValueError("Project not found")

        arcs = await db.story_arcs.find({"project_id": pid}).sort("order", 1).to_list(length=1000)
        chapters = await db.chapter_plans.find({"project_id": pid}).sort(
            "chapter_number", 1
        ).to_list(length=5000)
        scenes = await db.scene_plans.find({"project_id": pid}).to_list(length=20000)
        chapter_numbers = {
            str(item.get("chapter_plan_id")): int(item.get("chapter_number") or 0)
            for item in chapters
        }
        scenes.sort(
            key=lambda item: (
                chapter_numbers.get(str(item.get("chapter_plan_id")), 10**9),
                int(item.get("order") or 0),
                str(item.get("title") or "").casefold(),
            )
        )
        drafts = await db.scene_drafts.find({"project_id": pid}).sort(
            [("created_at", -1), ("version_number", -1)]
        ).to_list(length=20000)
        active_by_scene = {
            str(item.get("scene_id")): item
            for item in drafts
            if item.get("active")
        }

        current_arc = next(
            (item for item in arcs if item.get("focus_role") == "current"),
            arcs[0] if arcs else None,
        )
        current_scenes = [
            item
            for item in scenes
            if not current_arc or item.get("arc_id") == current_arc.get("arc_id")
        ]
        current_scene = next(
            (
                item
                for item in current_scenes
                if str((active_by_scene.get(str(item.get("scene_id"))) or {}).get("status") or "")
                != "approved"
            ),
            current_scenes[-1] if current_scenes else None,
        )
        current_draft = (
            active_by_scene.get(str(current_scene.get("scene_id")))
            if current_scene
            else None
        )
        current_chapter = next(
            (
                item
                for item in chapters
                if current_scene
                and item.get("chapter_plan_id") == current_scene.get("chapter_plan_id")
            ),
            None,
        )

        preflight: Dict[str, Any] | None = None
        blockers: list[str] = []
        if current_scene:
            preflight = await draft_validation_service.preflight_scene(
                db,
                project_id,
                str(current_scene["scene_id"]),
                persist=False,
            )
            blockers = _violations(preflight)
        planning_coaching: list[str] = []
        if current_scene:
            signature = tuple(
                " ".join(str(current_scene.get(field) or "").lower().split())
                for field in ("purpose", "conflict", "outcome")
            )
            repeated = [
                item
                for item in scenes
                if item.get("scene_id") != current_scene.get("scene_id")
                and signature
                == tuple(
                    " ".join(str(item.get(field) or "").lower().split())
                    for field in ("purpose", "conflict", "outcome")
                )
            ]
            if repeated:
                planning_coaching.append(
                    "This scene repeats the same purpose, conflict, and outcome as "
                    f"{len(repeated)} other planned scene{'s' if len(repeated) != 1 else ''}. "
                    "Give it a distinct event, decision, discovery, or reversal before final approval."
                )

        paragraph_content = await db.paragraph_content.find(
            {"project_id": pid},
            {"scene_id": 1, "prose": 1, "updated_at": 1},
        ).to_list(length=100000)
        paragraph_scenes = {
            str(item.get("scene_id"))
            for item in paragraph_content
            if str(item.get("prose") or "").strip()
        }
        prose = " ".join(str(item.get("prose") or "") for item in paragraph_content)
        prose += " " + " ".join(
            str(item.get("generated_text") or "")
            for item in active_by_scene.values()
            if str(item.get("scene_id")) not in paragraph_scenes
        )
        word_count = len(prose.split())
        character_count = len(prose)

        activity_dates = {
            value.date()
            for value in [
                *[item.get("updated_at") for item in paragraph_content],
                *[item.get("updated_at") for item in drafts],
            ]
            if isinstance(value, datetime)
        }
        streak = 0
        cursor = datetime.utcnow().date()
        if cursor not in activity_dates and cursor - timedelta(days=1) in activity_dates:
            cursor -= timedelta(days=1)
        while cursor in activity_dates:
            streak += 1
            cursor -= timedelta(days=1)

        pending_suggestions = await db.paragraph_suggestions.count_documents(
            {"project_id": pid, "status": "pending"}
        )
        pending_revisions = await db.revision_branches.count_documents(
            {"project_id": pid, "status": {"$in": ["draft", "review"]}}
        )
        approved_scenes = sum(
            1 for item in active_by_scene.values() if item.get("status") == "approved"
        )
        total_scenes = len(scenes)

        if not current_scene:
            next_action = {
                "title": "Plan your first scene",
                "explanation": "A scene plan gives the writing partner a goal, conflict and outcome.",
                "action": "Open scene planning",
                "target": "guide",
            }
        elif not current_draft:
            next_action = {
                "title": "Generate your first draft",
                "explanation": (
                    "You can explore the scene now. If planning checks remain, the draft stays "
                    "unapproved until those checks are resolved."
                    + (
                        " Its plan resembles another scene, so review the coaching note before "
                        "treating this as final prose."
                        if planning_coaching
                        else ""
                    )
                ),
                "action": "Generate draft",
                "target": "drafting",
                "scene_id": current_scene["scene_id"],
                "allow_exploratory": bool(blockers),
            }
        elif current_draft.get("status") == "draft":
            next_action = {
                "title": "Review this draft",
                "explanation": "Read the scene and inspect what the AI used before requesting revisions.",
                "action": "Start review",
                "target": "drafting",
                "draft_id": current_draft["draft_id"],
            }
        elif current_draft.get("status") == "review":
            next_action = {
                "title": "Revise or approve",
                "explanation": "Choose a focused revision pass, or approve if the scene already works.",
                "action": "Open revision",
                "target": "editorial",
                "draft_id": current_draft["draft_id"],
            }
        else:
            next_action = {
                "title": "Continue writing",
                "explanation": "The scene is approved. Move to the next planned scene.",
                "action": "Continue",
                "target": "drafting",
            }

        stages = [
            ("Scene plan", bool(current_scene)),
            ("Generate draft", bool(current_draft)),
            ("Review draft", bool(current_draft and current_draft.get("status") in {"review", "approved"})),
            ("Revise", bool(current_draft and (current_draft.get("operation") not in {None, "generate"} or pending_revisions))),
            ("Approve", bool(current_draft and current_draft.get("status") == "approved")),
            ("Continue writing", bool(total_scenes and approved_scenes == total_scenes)),
        ]
        active_stage = next((title for title, complete in stages if not complete), "Continue writing")

        used_context = {
            "characters": await db.character_bibles.count_documents({"project_id": pid}),
            "canon_facts": await db.canon_registry.count_documents(
                {"project_id": pid, "active": {"$ne": False}}
            ),
            "timeline_events": (
                await db.timeline_entries.count_documents({"project_id": pid})
                + await db.story_timelines.count_documents({"project_id": pid})
            ),
            "plot_threads": await db.plot_threads.count_documents({"project_id": pid}),
            "approved_decisions": await db.decision_registry.count_documents(
                {
                    "project_id": pid,
                    "$or": [
                        {"status": {"$in": ["approved", "active", "accepted"]}},
                        {"status": {"$exists": False}},
                    ],
                }
            ),
            "relationships": await db.relationship_graphs.count_documents({"project_id": pid}),
            "world_sections": await db.world_bibles.count_documents({"project_id": pid}),
            "themes": await db.theme_registry.count_documents({"project_id": pid}),
        }
        last_edited = max(
            [
                value
                for value in [
                    *[item.get("updated_at") for item in paragraph_content],
                    *[item.get("updated_at") for item in drafts],
                ]
                if isinstance(value, datetime)
            ],
            default=project.get("updated_at") or project.get("created_at"),
        )
        return {
            "project_id": project_id,
            "current_arc": {
                "arc_id": current_arc.get("arc_id"),
                "title": current_arc.get("title"),
            } if current_arc else None,
            "current_chapter": {
                "chapter_plan_id": current_chapter.get("chapter_plan_id"),
                "number": current_chapter.get("chapter_number"),
                "title": current_chapter.get("title"),
            } if current_chapter else None,
            "current_scene": {
                "scene_id": current_scene.get("scene_id"),
                "title": current_scene.get("title"),
                "status": current_scene.get("status"),
            } if current_scene else None,
            "current_draft": {
                "draft_id": current_draft.get("draft_id"),
                "version_label": current_draft.get("version_label")
                or f"Version {chr(64 + min(int(current_draft.get('version_number') or 1), 26))}",
                "status": current_draft.get("status"),
                "exploratory": bool(current_draft.get("exploratory")),
                "favorite": bool(current_draft.get("favorite")),
            } if current_draft else None,
            "metrics": {
                "words": word_count,
                "characters": character_count,
                "reading_minutes": max(1, round(word_count / 225)) if word_count else 0,
                "writing_streak_days": streak,
                "last_edited": _iso(last_edited),
                "pending_ai_suggestions": pending_suggestions,
                "pending_revisions": pending_revisions,
                "approved_scenes": approved_scenes,
                "total_scenes": total_scenes,
            },
            "workflow": {
                "active_stage": active_stage,
                "steps": [
                    {"title": title, "complete": complete, "current": title == active_stage}
                    for title, complete in stages
                ],
            },
            "scene_health": {
                "result": (current_draft or {}).get("validation_result")
                or (preflight or {}).get("result")
                or "NOT_ANALYZED",
                "blockers": blockers,
                "evidence": list((preflight or {}).get("evidence") or []),
                "coaching_notes": planning_coaching,
            },
            "next_action": next_action,
            "context_used": used_context,
            "generated_at": datetime.utcnow().isoformat(),
        }


writing_experience_service = WritingExperienceService()
