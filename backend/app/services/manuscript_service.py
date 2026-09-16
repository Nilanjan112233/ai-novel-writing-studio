"""Immutable manuscript assembly and deterministic book-level governance."""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from bson import ObjectId

from app.services.canon_governance_service import canon_governance_service
from app.services.narrative_studio import narrative_studio_service
from app.services.orchestration_engine import orchestration_engine
from app.services.orchestration_service_v2 import orchestration_service_v2
from app.services.project_intelligence_coordinator import project_intelligence_coordinator


MANUSCRIPT_STATUSES = {"draft", "review", "validated", "approved", "archived"}
MANUSCRIPT_TRANSITIONS = {
    "draft": {"review", "archived"},
    "review": {"validated", "draft", "archived"},
    "validated": {"approved", "draft", "archived"},
    "approved": {"archived"},
    "archived": set(),
}


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


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ManuscriptService:
    async def _project(self, db, project_id: str) -> tuple[ObjectId, Dict[str, Any]]:
        if not ObjectId.is_valid(project_id):
            raise ValueError("Invalid project ID")
        pid = ObjectId(project_id)
        project = await db.projects.find_one({"_id": pid})
        if not project:
            raise ValueError("Project not found")
        return pid, project

    async def _manuscript(
        self, db, project_id: str, manuscript_id: str
    ) -> Dict[str, Any]:
        pid, _ = await self._project(db, project_id)
        manuscript = await db.manuscripts.find_one(
            {"project_id": pid, "manuscript_id": manuscript_id}
        )
        if not manuscript:
            raise ValueError("Manuscript not found")
        return manuscript

    async def _after_change(
        self,
        db,
        project_id: str,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        await project_intelligence_coordinator.after_change(
            db, project_id, event_type, payload,
        )

    async def create(
        self, db, project_id: str, *, title: str = ""
    ) -> Dict[str, Any]:
        pid, project = await self._project(db, project_id)
        existing = await db.manuscripts.find_one(
            {"project_id": pid, "active": True}
        )
        if existing:
            return _serialize(existing)
        now = datetime.utcnow()
        doc = {
            "project_id": pid,
            "manuscript_id": str(uuid4()),
            "title": title.strip()
            or f"{project.get('story_title') or 'Untitled novel'} Manuscript",
            "status": "draft",
            "active": True,
            "version": 0,
            "current_version_id": None,
            "created_at": now,
            "updated_at": now,
        }
        inserted = await db.manuscripts.insert_one(doc)
        doc["_id"] = inserted.inserted_id
        await self._after_change(
            db,
            project_id,
            "manuscript_created",
            {"manuscript_id": doc["manuscript_id"]},
        )
        return _serialize(doc)

    async def _source_chapters(
        self,
        db,
        pid: ObjectId,
        chapter_draft_ids: list[str] | None,
    ) -> list[Dict[str, Any]]:
        query: Dict[str, Any] = {
            "project_id": pid,
            "status": "approved",
            "active": True,
        }
        if chapter_draft_ids:
            query["draft_id"] = {"$in": list(dict.fromkeys(chapter_draft_ids))}
        drafts = await db.chapter_drafts.find(query).to_list(length=5000)
        if chapter_draft_ids and len(drafts) != len(set(chapter_draft_ids)):
            raise ValueError("Every selected chapter must be an active approved project draft")
        if not drafts:
            raise ValueError("Manuscript assembly requires approved chapter drafts")
        plan_ids = [draft.get("chapter_plan_id") for draft in drafts]
        plans = await db.chapter_plans.find(
            {"project_id": pid, "chapter_plan_id": {"$in": plan_ids}}
        ).to_list(length=5000)
        by_id = {plan.get("chapter_plan_id"): plan for plan in plans}
        if any(draft.get("chapter_plan_id") not in by_id for draft in drafts):
            raise ValueError("A chapter draft has no project-owned chapter plan")
        drafts.sort(
            key=lambda draft: (
                int(by_id[draft["chapter_plan_id"]].get("chapter_number") or 0),
                str(draft.get("draft_id")),
            )
        )
        numbers = [
            int(by_id[draft["chapter_plan_id"]].get("chapter_number") or 0)
            for draft in drafts
        ]
        if len(numbers) != len(set(numbers)):
            raise ValueError("Manuscript cannot contain duplicate chapter numbers")
        result = []
        for draft in drafts:
            plan = by_id[draft["chapter_plan_id"]]
            text = str(draft.get("generated_text") or "")
            result.append(
                {
                    "chapter_number": int(plan.get("chapter_number") or 0),
                    "chapter_plan_id": plan["chapter_plan_id"],
                    "chapter_draft_id": draft["draft_id"],
                    "chapter_draft_version": int(draft.get("version_number") or 1),
                    "arc_id": draft.get("arc_id") or plan.get("arc_id"),
                    "title": plan.get("title") or f"Chapter {plan.get('chapter_number')}",
                    "text": text,
                    "text_sha256": _hash(text),
                    "source_scene_draft_ids": list(
                        draft.get("source_scene_draft_ids")
                        or draft.get("source_draft_ids")
                        or []
                    ),
                }
            )
        return result

    async def assemble(
        self,
        db,
        project_id: str,
        manuscript_id: str,
        *,
        chapter_draft_ids: list[str] | None = None,
    ) -> Dict[str, Any]:
        manuscript = await self._manuscript(db, project_id, manuscript_id)
        pid = manuscript["project_id"]
        chapters = await self._source_chapters(db, pid, chapter_draft_ids)
        latest = await db.manuscript_versions.find_one(
            {"project_id": pid, "manuscript_id": manuscript_id},
            sort=[("version_number", -1)],
        )
        now = datetime.utcnow()
        version_number = int((latest or {}).get("version_number") or 0) + 1
        version = {
            "project_id": pid,
            "version_id": str(uuid4()),
            "manuscript_id": manuscript_id,
            "version_number": version_number,
            "parent_version_id": (latest or {}).get("version_id"),
            "source_chapters": chapters,
            "assembled_text": "\n\n".join(
                chapter["text"] for chapter in chapters
            ),
            "chapter_count": len(chapters),
            "validation_result": "PENDING",
            "created_at": now,
        }
        inserted = await db.manuscript_versions.insert_one(version)
        version["_id"] = inserted.inserted_id
        await db.manuscripts.update_one(
            {"_id": manuscript["_id"]},
            {
                "$set": {
                    "version": version_number,
                    "current_version_id": version["version_id"],
                    "status": "draft",
                    "updated_at": now,
                }
            },
        )
        validation = await self.validate(
            db, project_id, manuscript_id, version_id=version["version_id"]
        )
        await self._after_change(
            db,
            project_id,
            "manuscript_assembled",
            {
                "manuscript_id": manuscript_id,
                "version_id": version["version_id"],
                "version_number": version_number,
            },
        )
        return {
            "version": _serialize(
                await db.manuscript_versions.find_one({"_id": inserted.inserted_id})
            ),
            "validation": validation,
        }

    async def validate(
        self,
        db,
        project_id: str,
        manuscript_id: str,
        *,
        version_id: str | None = None,
    ) -> Dict[str, Any]:
        manuscript = await self._manuscript(db, project_id, manuscript_id)
        pid = manuscript["project_id"]
        resolved_version_id = version_id or manuscript.get("current_version_id")
        version = await db.manuscript_versions.find_one(
            {
                "project_id": pid,
                "manuscript_id": manuscript_id,
                "version_id": resolved_version_id,
            }
        )
        if not version:
            raise ValueError("Manuscript version not found")
        failures: list[Dict[str, Any]] = []
        warnings: list[Dict[str, Any]] = []
        chapters = list(version.get("source_chapters") or [])
        numbers = [int(item.get("chapter_number") or 0) for item in chapters]
        if not chapters:
            failures.append({"type": "structure", "message": "Manuscript has no chapters"})
        elif numbers != sorted(numbers) or len(numbers) != len(set(numbers)):
            failures.append({"type": "structure", "message": "Chapter order is invalid"})
        elif numbers != list(range(min(numbers), max(numbers) + 1)):
            failures.append({"type": "structure", "message": "Chapter sequence has gaps"})

        draft_ids = [item.get("chapter_draft_id") for item in chapters]
        drafts = await db.chapter_drafts.find(
            {"project_id": pid, "draft_id": {"$in": draft_ids}}
        ).to_list(length=5000)
        by_id = {draft.get("draft_id"): draft for draft in drafts}
        for source in chapters:
            draft = by_id.get(source.get("chapter_draft_id"))
            if not draft:
                failures.append(
                    {
                        "type": "source",
                        "message": f"Missing chapter draft {source.get('chapter_draft_id')}",
                    }
                )
                continue
            if draft.get("status") != "approved":
                failures.append(
                    {
                        "type": "source",
                        "message": f"Chapter {source.get('chapter_number')} is no longer approved",
                    }
                )
            if _hash(str(draft.get("generated_text") or "")) != source.get("text_sha256"):
                failures.append(
                    {
                        "type": "immutability",
                        "message": f"Chapter {source.get('chapter_number')} source text changed",
                    }
                )

        continuity = await db.continuity_reports.find(
            {
                "project_id": pid,
                "subject_id": {"$in": draft_ids},
                "result": {"$in": ["FAIL", "WARNING"]},
            }
        ).sort("created_at", -1).to_list(length=5000)
        if any(item.get("result") == "FAIL" for item in continuity):
            failures.append(
                {"type": "continuity", "message": "A source chapter has a continuity failure"}
            )
        elif continuity:
            warnings.append(
                {"type": "continuity", "message": "Source chapters have continuity warnings"}
            )

        editorial = await db.editorial_reports.find(
            {"project_id": pid, "subject_id": {"$in": draft_ids}}
        ).to_list(length=5000)
        if any(item.get("blockers") for item in editorial):
            failures.append(
                {"type": "editorial", "message": "Unresolved chapter editorial blockers exist"}
            )
        scores = await db.editorial_scores.find(
            {
                "project_id": pid,
                "subject_type": "chapter",
                "subject_id": {"$in": draft_ids},
            }
        ).sort("calculated_at", -1).to_list(length=5000)
        latest_scores: Dict[str, int] = {}
        for score in scores:
            latest_scores.setdefault(str(score.get("subject_id")), int(score.get("score") or 0))
        if any(value < 60 for value in latest_scores.values()):
            warnings.append(
                {"type": "editorial", "message": "One or more chapter scores are below 60"}
            )

        canon = await canon_governance_service.validate(db, project_id)
        if canon["result"] == "FAIL":
            failures.append(
                {"type": "canon", "message": "Open high-severity canon conflicts exist"}
            )
        elif canon["result"] == "WARNING":
            warnings.append(
                {"type": "canon", "message": "Open canon warnings exist"}
            )

        result = "FAIL" if failures else ("WARNING" if warnings else "PASS")
        now = datetime.utcnow()
        report = {
            "project_id": pid,
            "report_id": str(uuid4()),
            "manuscript_id": manuscript_id,
            "version_id": version["version_id"],
            "report_type": "deterministic_validation",
            "result": result,
            "findings": [*failures, *warnings],
            "failures": failures,
            "warnings": warnings,
            "evidence": [
                f"chapter:{item.get('chapter_draft_id')}:{item.get('text_sha256')}"
                for item in chapters
            ],
            "created_at": now,
        }
        inserted = await db.manuscript_reports.insert_one(report)
        report["_id"] = inserted.inserted_id
        await db.manuscript_versions.update_one(
            {"_id": version["_id"]},
            {
                "$set": {
                    "validation_result": result,
                    "validation_report_id": report["report_id"],
                    "validated_at": now,
                }
            },
        )
        return _serialize(report)

    async def review(
        self, db, project_id: str, manuscript_id: str
    ) -> Dict[str, Any]:
        manuscript = await self._manuscript(db, project_id, manuscript_id)
        pid, project = await self._project(db, project_id)
        version = await db.manuscript_versions.find_one(
            {
                "project_id": pid,
                "manuscript_id": manuscript_id,
                "version_id": manuscript.get("current_version_id"),
            }
        )
        if not version:
            raise ValueError("Assemble the manuscript before review")
        assignments = {
            item.agent_name: item
            for item in await orchestration_engine.get_assignments(db)
        }
        assignment = assignments.get("ManuscriptAgent")
        if assignment and not assignment.enabled:
            raise ValueError("ManuscriptAgent is disabled")
        from app.api.workflow import build_persistent_state

        latest_cycle = await db.cycles.find_one(
            {"project_id": pid}, sort=[("cycle_number", -1)]
        )
        state = await build_persistent_state(
            db,
            project,
            project_id,
            str(latest_cycle["_id"]) if latest_cycle else None,
        )
        state["manuscript_context"] = {
            "manuscript": _serialize(manuscript),
            "version": {
                key: _serialize(version.get(key))
                for key in (
                    "version_id",
                    "version_number",
                    "parent_version_id",
                    "chapter_count",
                    "validation_result",
                )
            },
            "approved_chapters": [
                {
                    **{
                        key: _serialize(chapter.get(key))
                        for key in (
                            "chapter_number",
                            "chapter_plan_id",
                            "chapter_draft_id",
                            "chapter_draft_version",
                            "arc_id",
                            "title",
                            "text_sha256",
                            "source_scene_draft_ids",
                        )
                    },
                    "text_excerpt": str(chapter.get("text") or "")[:1200],
                }
                for chapter in (version.get("source_chapters") or [])[:20]
            ],
            "active_canon": _serialize(
                await db.canon_registry.find(
                    {"project_id": pid, "active": True}
                ).to_list(length=200)
            ),
        }
        settings = await orchestration_engine.get_settings(db)
        plan = await orchestration_service_v2.create_explicit_plan(
            db,
            project_id=project_id,
            agent_name="ManuscriptAgent",
            changed_entity=f"manuscript:{manuscript_id}",
            affected_domain="manuscript_review",
            reason="Explicit manuscript review requires ManuscriptAgent",
        )
        try:
            result = await narrative_studio_service.run(
                db,
                project_id=project_id,
                state=state,
                agent_names=["ManuscriptAgent"],
                plan_id=str(plan["_id"]),
                max_agent_calls=1,
                max_cycle_cost_usd=float(settings.max_cycle_cost_usd),
            )
            outputs = [
                item
                for item in state.get("cycle_outputs") or []
                if item.get("agent_name") == "ManuscriptAgent"
            ]
            if not outputs:
                raise ValueError("ManuscriptAgent did not return structured output")
            await orchestration_service_v2.finalize_explicit_plan(
                db,
                plan_id=plan["_id"],
                agent_name="ManuscriptAgent",
                status="completed",
                actual_cost_usd=float(result.get("actual_cost_usd") or 0),
            )
        except Exception as exc:
            await orchestration_service_v2.finalize_explicit_plan(
                db,
                plan_id=plan["_id"],
                agent_name="ManuscriptAgent",
                status="failed",
                error=str(exc),
            )
            raise
        raw = outputs[-1]["structured_output"].get("manuscript_review") or {}
        now = datetime.utcnow()
        report = {
            "project_id": pid,
            "report_id": str(uuid4()),
            "manuscript_id": manuscript_id,
            "version_id": version["version_id"],
            "report_type": "manuscript_review",
            "result": str(raw.get("result") or "WARNING").upper(),
            "findings": list(raw.get("findings") or []),
            "recommendations": list(raw.get("recommendations") or []),
            "evidence": list(raw.get("evidence") or []),
            "generated_by": "ManuscriptAgent",
            "orchestration_plan_id": str(plan["_id"]),
            "created_at": now,
        }
        inserted = await db.manuscript_reports.insert_one(report)
        report["_id"] = inserted.inserted_id
        await self._after_change(
            db,
            project_id,
            "manuscript_reviewed",
            {"manuscript_id": manuscript_id, "report_id": report["report_id"]},
        )
        return _serialize(report)

    async def transition(
        self,
        db,
        project_id: str,
        manuscript_id: str,
        status: str,
    ) -> Dict[str, Any]:
        manuscript = await self._manuscript(db, project_id, manuscript_id)
        status = status.lower()
        current = str(manuscript.get("status") or "draft")
        if status not in MANUSCRIPT_STATUSES:
            raise ValueError("Unsupported manuscript status")
        if status not in MANUSCRIPT_TRANSITIONS.get(current, set()):
            raise ValueError(f"Cannot transition manuscript {current} -> {status}")
        version = await db.manuscript_versions.find_one(
            {
                "project_id": manuscript["project_id"],
                "version_id": manuscript.get("current_version_id"),
            }
        )
        if status in {"validated", "approved"}:
            if not version or version.get("validation_result") == "FAIL":
                raise ValueError("A failing or missing validation blocks this transition")
        if status == "approved" and current != "validated":
            raise ValueError("Manuscript must be validated before manual approval")
        now = datetime.utcnow()
        patch: Dict[str, Any] = {"status": status, "updated_at": now}
        if status == "approved":
            patch["approved_at"] = now
            patch["readiness_policy_version"] = "rc6"
        elif status == "archived":
            patch.update({"archived_at": now, "active": False})
        await db.manuscripts.update_one(
            {"_id": manuscript["_id"]}, {"$set": patch}
        )
        await self._after_change(
            db,
            project_id,
            "manuscript_status_changed",
            {"manuscript_id": manuscript_id, "status": status},
        )
        return _serialize(
            await db.manuscripts.find_one({"_id": manuscript["_id"]})
        )

    async def rollback(
        self,
        db,
        project_id: str,
        manuscript_id: str,
        version_id: str,
    ) -> Dict[str, Any]:
        manuscript = await self._manuscript(db, project_id, manuscript_id)
        version = await db.manuscript_versions.find_one(
            {
                "project_id": manuscript["project_id"],
                "manuscript_id": manuscript_id,
                "version_id": version_id,
            }
        )
        if not version:
            raise ValueError("Manuscript version not found")
        now = datetime.utcnow()
        await db.manuscripts.update_one(
            {"_id": manuscript["_id"]},
            {
                "$set": {
                    "current_version_id": version_id,
                    "version": int(version.get("version_number") or 0),
                    "status": "draft",
                    "updated_at": now,
                }
            },
        )
        await self._after_change(
            db,
            project_id,
            "manuscript_rollback",
            {"manuscript_id": manuscript_id, "version_id": version_id},
        )
        return _serialize(
            await db.manuscripts.find_one({"_id": manuscript["_id"]})
        )

    async def dashboard(self, db, project_id: str) -> Dict[str, Any]:
        pid, _ = await self._project(db, project_id)
        manuscripts = await db.manuscripts.find({"project_id": pid}).sort(
            "updated_at", -1
        ).to_list(length=100)
        versions = await db.manuscript_versions.find({"project_id": pid}).sort(
            [("manuscript_id", 1), ("version_number", -1)]
        ).to_list(length=5000)
        reports = await db.manuscript_reports.find({"project_id": pid}).sort(
            "created_at", -1
        ).to_list(length=5000)
        return {
            "manuscripts": _serialize(manuscripts),
            "versions": _serialize(versions),
            "reports": _serialize(reports),
        }


manuscript_service = ManuscriptService()
