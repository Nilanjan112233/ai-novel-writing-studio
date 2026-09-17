"""Editable author decisions layered over the existing question workflow."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from bson import ObjectId

from app.services.change_impact_service import change_impact_service
from app.services.narrative_completeness_service import narrative_completeness_service
from app.services.project_event_service import emit_project_event
from app.services.shared_narrative_context_service import shared_narrative_context_service
from app.services.story_bible_service import rebuild_story_bible
from app.services.canon_service import record_answer_decision
from app.services.planning_authority_service import planning_authority_service
from app.services.narrative_analysis_engine import narrative_analysis_engine


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


class DecisionHistoryService:
    async def _project(self, db, project_id: str) -> ObjectId:
        if not ObjectId.is_valid(project_id):
            raise ValueError("Invalid project ID")
        pid = ObjectId(project_id)
        if not await db.projects.find_one({"_id": pid, "status": {"$ne": "trashed"}}):
            raise ValueError("Project not found")
        return pid

    async def _question(self, db, pid: ObjectId, question_id: str) -> Dict[str, Any]:
        if not ObjectId.is_valid(question_id):
            raise ValueError("Invalid question ID")
        question = await db.questions.find_one({"_id": ObjectId(question_id), "project_id": pid})
        if not question:
            raise ValueError("Question not found")
        return question

    def _history(self, question: Dict[str, Any]) -> list[Dict[str, Any]]:
        history = list(question.get("decision_history") or [])
        if not history and question.get("answer"):
            history.append({
                "version": 1,
                "answer": str(question.get("answer")),
                "action": "answered",
                "reason": "",
                "created_at": question.get("answered_at") or question.get("updated_at") or question.get("created_at") or datetime.utcnow(),
            })
        return history

    def _response(self, question: Dict[str, Any], impact: Dict[str, Any] | None = None) -> Dict[str, Any]:
        history = self._history(question)
        return _serialize({
            "question_id": str(question["_id"]),
            "question": str(question.get("text") or ""),
            "answered": bool(question.get("answered")),
            "current_answer": question.get("answer"),
            "version": int(question.get("decision_version") or (history[-1]["version"] if history else 0)),
            "history": history,
            "impact_preview": impact or {
                "status": "available",
                "message": "Preview affected story records before changing this decision.",
            },
            "can_change": bool(question.get("answered")),
            "can_undo": len(history) >= 2,
            "can_reopen": bool(question.get("answered")),
        })

    async def list(self, db, project_id: str) -> Dict[str, Any]:
        pid = await self._project(db, project_id)
        questions = await db.questions.find({"project_id": pid}).sort("created_at", -1).to_list(length=1000)
        return {
            "project_id": project_id,
            "decisions": [self._response(item) for item in questions],
        }

    async def preview(self, db, project_id: str, question_id: str) -> Dict[str, Any]:
        pid = await self._project(db, project_id)
        question = await self._question(db, pid, question_id)
        answer = str(question.get("answer") or question.get("text") or "")
        story_area = str(question.get("story_area") or "").lower()
        change_type = "timeline_change" if "timeline" in story_area else "arc_change"
        impact = await change_impact_service.analyze(
            db,
            project_id,
            change_type=change_type,
            target={"decision": answer, "question": str(question.get("text") or "")},
            proposed_change={"operation": "change_author_decision", "question_id": question_id},
        )
        return self._response(question, impact)

    async def change(
        self,
        db,
        project_id: str,
        question_id: str,
        *,
        answer: str,
        reason: str = "",
        action: str = "changed",
    ) -> Dict[str, Any]:
        pid = await self._project(db, project_id)
        question = await self._question(db, pid, question_id)
        cleaned = answer.strip()
        if not cleaned:
            raise ValueError("Decision answer is required")
        now = datetime.utcnow()
        previous_answer = str(question.get("answer") or "")
        history = self._history(question)
        version = int(question.get("decision_version") or (history[-1]["version"] if history else 0)) + 1
        history.append({
            "version": version,
            "answer": cleaned,
            "action": action,
            "reason": reason.strip(),
            "created_at": now,
        })
        await db.questions.update_one(
            {"_id": question["_id"], "project_id": pid},
            {"$set": {
                "answered": True,
                "answer": cleaned,
                "decision_version": version,
                "decision_history": history,
                "answered_at": now,
                "updated_at": now,
            }, "$unset": {"reopened_at": ""}},
        )
        await db.answers.insert_one({
            "project_id": pid,
            "question_id": question["_id"],
            "answer": cleaned,
            "version": version,
            "action": action,
            "reason": reason.strip(),
            "created_at": now,
        })
        invalidation = await planning_authority_service.supersede_for_decision(
            db,
            project_id=project_id,
            question_id=question_id,
            question_text=str(question.get("text") or ""),
            previous_answer=previous_answer,
            new_answer=cleaned,
        )
        await record_answer_decision(
            db,
            project_id=project_id,
            question=question,
            answer=cleaned,
        )
        await db.shared_narrative_context.update_many(
            {"project_id": pid, "source_id": question_id, "active": True},
            {"$set": {"active": False, "status": "superseded", "updated_at": now}},
        )
        await shared_narrative_context_service.ingest(
            db,
            project_id,
            content=cleaned,
            source_type="decision_change",
            source_id=question_id,
            source_excerpt=f"{question.get('text', '')} Answer: {cleaned}",
            structured={
                "domain": str(question.get("story_area") or "general"),
                "subject": str(question.get("subject") or question.get("topic") or "Author answer"),
                "field": str(question.get("field") or "resolved_question"),
                "value": cleaned,
                "confidence": .99,
            },
        )
        await emit_project_event(
            db,
            project_id,
            "decision_changed",
            cycle_number=int(question.get("cycle_number") or 0),
            payload={
                "question_id": question_id,
                "version": version,
                "action": action,
                "affected_planning_records": invalidation.get("affected_count", 0),
            },
        )
        await narrative_analysis_engine.analyze(db, project_id, force=True)
        bible = await rebuild_story_bible(db, project_id)
        await narrative_completeness_service.calculate(db, project_id)
        updated = await db.questions.find_one({"_id": question["_id"]})
        return self._response(updated)

    async def undo(self, db, project_id: str, question_id: str, *, reason: str = "") -> Dict[str, Any]:
        pid = await self._project(db, project_id)
        question = await self._question(db, pid, question_id)
        history = self._history(question)
        if len(history) < 2:
            raise ValueError("No earlier decision is available to restore")
        previous = history[-2]
        return await self.change(
            db,
            project_id,
            question_id,
            answer=str(previous["answer"]),
            reason=reason or f"Restored decision version {previous['version']}.",
            action="undo",
        )

    async def reopen(self, db, project_id: str, question_id: str, *, reason: str = "") -> Dict[str, Any]:
        pid = await self._project(db, project_id)
        question = await self._question(db, pid, question_id)
        now = datetime.utcnow()
        await db.questions.update_one(
            {"_id": question["_id"], "project_id": pid},
            {"$set": {
                "answered": False,
                "reopened_at": now,
                "reopen_reason": reason.strip(),
                "updated_at": now,
            }},
        )
        await db.shared_narrative_context.update_many(
            {"project_id": pid, "source_id": question_id, "active": True},
            {"$set": {"active": False, "status": "reopened", "updated_at": now}},
        )
        bible = await rebuild_story_bible(db, project_id)
        await narrative_completeness_service.calculate(db, project_id)
        await emit_project_event(
            db,
            project_id,
            "question_reopened",
            cycle_number=int(question.get("cycle_number") or 0),
            payload={"question_id": question_id, "story_bible_version": bible.get("version")},
        )
        updated = await db.questions.find_one({"_id": question["_id"]})
        return self._response(updated)


decision_history_service = DecisionHistoryService()
