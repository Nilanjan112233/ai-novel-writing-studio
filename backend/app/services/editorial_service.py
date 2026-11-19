"""Editorial review, deterministic scoring, and immutable revision branches."""
from __future__ import annotations

import difflib
import hashlib
import re
from datetime import datetime
from statistics import mean
from typing import Any, Dict, Iterable
from uuid import uuid4

from bson import ObjectId

from app.services.draft_validation_service import draft_validation_service
from app.services.narrative_studio import narrative_studio_service
from app.services.orchestration_engine import orchestration_engine
from app.services.orchestration_service_v2 import orchestration_service_v2
from app.services.project_intelligence_coordinator import project_intelligence_coordinator
from app.services.story_quality_service import story_quality_service
from app.services.task_routing_service import task_routing_service
from app.services.model_registry_service import model_registry_service, normalize_provider


BRANCH_STATUSES = {"draft", "review", "approved", "rejected", "archived"}
REVISION_PASSES = {
    "development",
    "line",
    "copy",
    "style",
    "continuity",
    "dialogue",
    "emotion",
    "description",
    "consistency",
    "grammar",
}
BRANCH_TRANSITIONS = {
    "draft": {"review", "rejected", "archived"},
    "review": {"approved", "rejected", "archived"},
    "approved": {"archived"},
    "rejected": {"archived"},
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


def _clamp(value: Any, default: int = 50) -> int:
    try:
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError):
        return default


def _dimension_scores(values: Any) -> Dict[str, int]:
    if not isinstance(values, dict):
        return {}
    numeric: Dict[str, float] = {}
    for key, value in values.items():
        try:
            numeric[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    if not numeric:
        return {}
    multiplier = 10 if max(numeric.values()) <= 10 else 1
    return {
        key: _clamp(value * multiplier)
        for key, value in numeric.items()
    }


def _unique(values: Iterable[Any]) -> list[Any]:
    result = []
    seen = set()
    for value in values:
        marker = repr(value)
        if marker not in seen:
            result.append(value)
            seen.add(marker)
    return result


def _splice_selected_revision(source_text: str, selected_text: str, revised_text: str) -> str:
    """Put a revised passage back into the full source text.

    If the model already returned something chapter-sized, it is kept as is.
    Otherwise the selected passage is replaced in place (whitespace-tolerant,
    because text selected in the browser may differ in line breaks).
    """
    selected = selected_text.strip()
    revised = revised_text.strip()
    if not selected or not revised or len(revised) >= 0.8 * len(source_text):
        return revised_text
    if selected in source_text:
        return source_text.replace(selected, revised, 1)
    pattern = r"\s+".join(re.escape(token) for token in selected.split())
    match = re.search(pattern, source_text)
    if match:
        return source_text[: match.start()] + revised + source_text[match.end():]
    raise ValueError(
        "The selected passage was not found in the chapter. Select the text again and retry."
    )


def _humanization_quality_failure(source_text: str, generated_text: str) -> str | None:
    """Reject light polish that silently turns a chapter into a summary."""
    source_words = len(re.findall(r"\b[\w'-]+\b", source_text or ""))
    generated_words = len(re.findall(r"\b[\w'-]+\b", generated_text or ""))
    if not source_words or not generated_words:
        return "Humanization returned no usable prose."
    # A style pass may tighten prose, but it must remain a chapter-level
    # alternative rather than an accidental synopsis. Short excerpts are
    # intentionally exempt from the chapter threshold.
    if source_words >= 500 and generated_words < max(350, int(source_words * 0.72)):
        return (
            f"Humanization reduced the source from {source_words} to "
            f"{generated_words} words, below the safe chapter-level floor."
        )
    return None


def _findings(values: Any, category: str) -> list[Dict[str, Any]]:
    if not isinstance(values, list):
        values = [values] if values else []
    result = []
    for value in values:
        if isinstance(value, dict):
            message = str(
                value.get("message")
                or value.get("finding")
                or value.get("issue")
                or ""
            ).strip()
            if not message:
                continue
            result.append(
                {
                    "category": str(value.get("category") or category),
                    "severity": str(value.get("severity") or "warning").lower(),
                    "message": message,
                    "evidence": list(value.get("evidence") or []),
                }
            )
        else:
            message = str(value).strip()
            if message:
                result.append(
                    {
                        "category": category,
                        "severity": "warning",
                        "message": message,
                        "evidence": [],
                    }
                )
    return result


def _text_metrics(text: str) -> Dict[str, Any]:
    words = re.findall(r"[A-Za-z0-9']+", text)
    sentences = [
        item.strip()
        for item in re.split(r"(?<=[.!?])\s+", text.strip())
        if item.strip()
    ]
    paragraphs = [item.strip() for item in text.splitlines() if item.strip()]
    lengths = [len(re.findall(r"[A-Za-z0-9']+", item)) for item in sentences]
    normalized_words = [word.lower() for word in words]
    bigrams = list(zip(normalized_words, normalized_words[1:]))
    repeated_bigrams = len(bigrams) - len(set(bigrams))
    quoted_words = sum(
        len(re.findall(r"[A-Za-z0-9']+", fragment))
        for fragment in re.findall(r'["“](.*?)["”]', text, flags=re.DOTALL)
    )
    return {
        "word_count": len(words),
        "sentence_count": len(sentences),
        "paragraph_count": len(paragraphs),
        "average_sentence_words": round(mean(lengths), 2) if lengths else 0,
        "sentence_length_range": (
            [min(lengths), max(lengths)] if lengths else [0, 0]
        ),
        "repeated_bigram_ratio": round(
            repeated_bigrams / max(1, len(bigrams)), 4
        ),
        "dialogue_word_ratio": round(quoted_words / max(1, len(words)), 4),
    }


class EditorialService:
    async def _project(self, db, project_id: str) -> tuple[ObjectId, Dict[str, Any]]:
        if not ObjectId.is_valid(project_id):
            raise ValueError("Invalid project ID")
        pid = ObjectId(project_id)
        project = await db.projects.find_one({"_id": pid})
        if not project:
            raise ValueError("Project not found")
        return pid, project

    async def _draft(
        self,
        db,
        project_id: str,
        draft_type: str,
        draft_id: str,
        *,
        approved: bool = True,
        allowed_statuses: set[str] | None = None,
    ) -> Dict[str, Any]:
        pid, _ = await self._project(db, project_id)
        collection = {
            "scene": "scene_drafts",
            "chapter": "chapter_drafts",
        }.get(draft_type)
        if not collection:
            raise ValueError("draft_type must be scene or chapter")
        draft = await db[collection].find_one(
            {"project_id": pid, "draft_id": draft_id}
        )
        if not draft:
            raise ValueError(f"{draft_type.title()} draft not found")
        if allowed_statuses and str(draft.get("status") or "") not in allowed_statuses:
            raise ValueError(
                "Editorial work requires a draft in review or approved status"
            )
        if not allowed_statuses and approved and draft.get("status") != "approved":
            raise ValueError("Editorial review requires an approved draft")
        return draft

    async def _execute(
        self,
        db,
        *,
        project_id: str,
        agent_name: str,
        editorial_context: Dict[str, Any],
        changed_entity: str,
        affected_domain: str,
        reason: str,
        routing_task: str | None = None,
        model_preference: str = "auto",
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        pid, project = await self._project(db, project_id)
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
        state.update(
            {
                "target_arc_id": editorial_context.get("arc_id"),
                "editorial_context": editorial_context,
            }
        )
        if routing_task:
            preference = str(model_preference or "auto").strip()
            if preference.lower() != "auto":
                try:
                    requested_provider, requested_model = preference.split("|", 1)
                except ValueError as exc:
                    raise ValueError("Model preference must use a discovered provider and model") from exc
                requested_provider = normalize_provider(requested_provider.strip())
                requested_model = requested_model.strip()
                await model_registry_service.validate_model(requested_provider, requested_model)
                automatic = await task_routing_service.select(routing_task)
                fallbacks = ([{"provider": automatic.get("provider"), "model": automatic.get("model")}] if automatic.get("provider") and automatic.get("model") else []) + list(automatic.get("fallbacks") or [])
                route = await task_routing_service.select(
                    routing_task,
                    requested_provider=requested_provider,
                    requested_model=requested_model,
                    fallbacks=fallbacks,
                )
            else:
                route = await task_routing_service.select(routing_task)
            state["agent_model_overrides"] = {
                agent_name: {
                    "provider": route.get("provider"),
                    "model": route.get("model"),
                    "fallbacks": route.get("fallbacks") or [],
                    "routing_task": routing_task,
                    "model_preference": preference,
                }
            }
        settings = await orchestration_engine.get_settings(db)
        plan = await orchestration_service_v2.create_explicit_plan(
            db,
            project_id=project_id,
            agent_name=agent_name,
            changed_entity=changed_entity,
            affected_domain=affected_domain,
            reason=reason,
        )
        try:
            result = await narrative_studio_service.run(
                db,
                project_id=project_id,
                state=state,
                agent_names=[agent_name],
                plan_id=str(plan["_id"]),
                max_agent_calls=1,
                max_cycle_cost_usd=float(settings.max_cycle_cost_usd),
            )
            outputs = [
                item
                for item in state.get("cycle_outputs") or []
                if item.get("agent_name") == agent_name
            ]
            if not outputs:
                raise ValueError(f"{agent_name} did not return structured output")
            await orchestration_service_v2.finalize_explicit_plan(
                db,
                plan_id=plan["_id"],
                agent_name=agent_name,
                status="completed",
                actual_cost_usd=float(result.get("actual_cost_usd") or 0),
            )
        except Exception as exc:
            await orchestration_service_v2.finalize_explicit_plan(
                db,
                plan_id=plan["_id"],
                agent_name=agent_name,
                status="failed",
                error=str(exc),
            )
            raise
        trace = await db.execution_traces.find_one(
            {"project_id": pid, "agent_name": agent_name},
            sort=[("created_at", -1)],
        )
        agent_metadata = outputs[-1].get("generation_metadata") or {}
        metadata = {
            "provider": agent_metadata.get("provider") or (trace or {}).get("provider"),
            "model": agent_metadata.get("model") or (trace or {}).get("model"),
            "tokens_used": agent_metadata.get("tokens") or (trace or {}).get("total_tokens"),
            "latency_ms": agent_metadata.get("latency") or (trace or {}).get("latency_ms"),
            "cost_usd": agent_metadata.get("cost") or (trace or {}).get("cost_usd"),
            "execution_trace_id": (
                agent_metadata.get("execution_trace_id")
                or str((trace or {}).get("_id") or "")
            ),
            "execution_trace_ids": agent_metadata.get("execution_trace_ids") or [],
            "corrective_retry_count": int(
                agent_metadata.get("corrective_retry_count") or 0
            ),
            "rate_limit_per_minute": ((trace or {}).get("metadata") or {}).get(
                "rate_limit_per_minute"
            ),
            "rate_limit_acquired_at": ((trace or {}).get("metadata") or {}).get(
                "rate_limit_acquired_at"
            ),
            "orchestration_plan_id": str(plan["_id"]),
        }
        return outputs[-1]["structured_output"], metadata

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

    async def _draft_context(
        self,
        db,
        pid: ObjectId,
        draft_type: str,
        draft: Dict[str, Any],
    ) -> Dict[str, Any]:
        context: Dict[str, Any] = {
            "subject_type": draft_type,
            "subject_id": draft["draft_id"],
            "draft_id": draft["draft_id"],
            "version_number": draft.get("version_number"),
            "arc_id": draft.get("arc_id"),
            "chapter_plan_id": draft.get("chapter_plan_id"),
            "scene_id": draft.get("scene_id"),
            "approved_text": draft.get("generated_text") or "",
            "continuity_claims": draft.get("continuity_claims") or {},
            "text_metrics": _text_metrics(draft.get("generated_text") or ""),
        }
        context["arc"] = await db.story_arcs.find_one(
            {"project_id": pid, "arc_id": draft.get("arc_id")}
        ) or {}
        context["chapter_plan"] = await db.chapter_plans.find_one(
            {
                "project_id": pid,
                "chapter_plan_id": draft.get("chapter_plan_id"),
            }
        ) or {}
        if draft_type == "scene":
            context["scene_plan"] = await db.scene_plans.find_one(
                {"project_id": pid, "scene_id": draft.get("scene_id")}
            ) or {}
        else:
            source_ids = list(draft.get("source_scene_draft_ids") or [])
            context["source_scene_drafts"] = await db.scene_drafts.find(
                {"project_id": pid, "draft_id": {"$in": source_ids}},
                {
                    "_id": 0,
                    "draft_id": 1,
                    "scene_id": 1,
                    "version_number": 1,
                    "generated_text": 1,
                },
            ).to_list(length=500)
            context["scene_plans"] = await db.scene_plans.find(
                {
                    "project_id": pid,
                    "chapter_plan_id": draft.get("chapter_plan_id"),
                }
            ).sort("order", 1).to_list(length=500)
        context["continuity_reports"] = await db.continuity_reports.find(
            {
                "project_id": pid,
                "subject_id": draft["draft_id"],
            },
            {"_id": 0},
        ).sort("created_at", -1).to_list(length=20)
        return context

    async def _arc_context(
        self, db, pid: ObjectId, arc_id: str
    ) -> Dict[str, Any]:
        arc = await db.story_arcs.find_one(
            {"project_id": pid, "arc_id": arc_id}
        )
        if not arc:
            raise ValueError("Arc not found")
        chapter_drafts = await db.chapter_drafts.find(
            {
                "project_id": pid,
                "arc_id": arc_id,
                "status": "approved",
                "active": True,
            },
            {
                "_id": 0,
                "draft_id": 1,
                "chapter_plan_id": 1,
                "version_number": 1,
                "generated_text": 1,
            },
        ).sort("created_at", 1).to_list(length=500)
        if not chapter_drafts:
            raise ValueError("Arc review requires approved chapter drafts")
        return {
            "subject_type": "arc",
            "subject_id": arc_id,
            "arc_id": arc_id,
            "arc": arc,
            "approved_chapter_drafts": chapter_drafts,
            "chapter_plans": await db.chapter_plans.find(
                {"project_id": pid, "arc_id": arc_id}
            ).sort("chapter_number", 1).to_list(length=500),
            "character_progressions": await db.character_progressions.find(
                {"project_id": pid, "arc_id": arc_id}
            ).to_list(length=500),
            "foreshadow_chains": await db.foreshadow_chains.find(
                {"project_id": pid, "arc_id": arc_id}
            ).sort("order", 1).to_list(length=500),
        }

    async def request_review(
        self,
        db,
        project_id: str,
        *,
        subject_type: str,
        subject_id: str,
        report_type: str = "editorial",
    ) -> Dict[str, Any]:
        pid, _ = await self._project(db, project_id)
        normalized_type = report_type.lower()
        if normalized_type not in {"editorial", "dialogue"}:
            raise ValueError("report_type must be editorial or dialogue")
        if subject_type == "arc":
            if normalized_type == "dialogue":
                raise ValueError("Dialogue review requires a scene or chapter draft")
            context = await self._arc_context(db, pid, subject_id)
            draft = None
        elif subject_type in {"scene", "chapter"}:
            draft = await self._draft(
                db,
                project_id,
                subject_type,
                subject_id,
                allowed_statuses={"review", "approved"},
            )
            context = await self._draft_context(db, pid, subject_type, draft)
        else:
            raise ValueError("subject_type must be scene, chapter, or arc")

        agent_name = "DialogueAgent" if normalized_type == "dialogue" else "EditorAgent"
        payload, metadata = await self._execute(
            db,
            project_id=project_id,
            agent_name=agent_name,
            editorial_context=context,
            changed_entity=f"{subject_type}:{subject_id}",
            affected_domain=(
                "dialogue_review"
                if normalized_type == "dialogue"
                else "editorial_review"
            ),
            reason=(
                f"Explicit {normalized_type} review request for approved "
                f"{subject_type} requires {agent_name}"
            ),
        )
        raw = payload.get(
            "dialogue_review" if normalized_type == "dialogue" else "editorial_review"
        ) or {}
        dimension_scores = _dimension_scores(raw.get("dimension_scores"))
        findings = []
        raw_findings = raw.get("findings") or {}
        if isinstance(raw_findings, dict):
            for category, values in raw_findings.items():
                findings.extend(_findings(values, str(category)))
        else:
            findings.extend(_findings(raw_findings, normalized_type))
        if subject_type in {"scene", "chapter"}:
            findings.extend(
                story_quality_service.analyze_text(
                    str(context.get("approved_text") or "")
                )["findings"]
            )
        elif subject_type == "arc":
            findings.extend(
                story_quality_service.compare_chapters(
                    [
                        {
                            "chapter_number": index + 1,
                            "chapter_summary": item.get("generated_text") or "",
                            "important_events": [],
                            "word_count": _text_metrics(
                                item.get("generated_text") or ""
                            )["word_count"],
                        }
                        for index, item in enumerate(
                            context.get("approved_chapter_drafts") or []
                        )
                    ]
                )
            )
        findings = _unique(findings)
        blockers = _unique(
            [
                str(item).strip()
                for item in raw.get("blockers") or []
                if str(item).strip()
            ]
            + [
                item["message"]
                for item in findings
                if item.get("severity") in {"blocker", "error", "critical"}
            ]
        )
        recommendations = _unique(
            str(item).strip()
            for item in raw.get("recommendations") or []
            if str(item).strip()
        )
        evidence = _unique(
            str(item).strip()
            for item in raw.get("evidence") or []
            if str(item).strip()
        )
        score = round(mean(dimension_scores.values())) if dimension_scores else 50
        now = datetime.utcnow()
        report = {
            "project_id": pid,
            "report_id": str(uuid4()),
            "arc_id": context.get("arc_id"),
            "chapter_id": context.get("chapter_plan_id"),
            "scene_id": context.get("scene_id"),
            "draft_id": (draft or {}).get("draft_id"),
            "version_number": int((draft or {}).get("version_number") or 0),
            "subject_type": subject_type,
            "subject_id": subject_id,
            "report_type": normalized_type,
            "score": score,
            "dimension_scores": dimension_scores,
            "findings": findings,
            "recommendations": recommendations,
            "blockers": blockers,
            "evidence": evidence,
            "text_metrics": context.get("text_metrics") or {},
            "generation_metadata": metadata,
            "generated_by": agent_name,
            "created_at": now,
        }
        inserted = await db.editorial_reports.insert_one(report)
        report["_id"] = inserted.inserted_id
        scores = await self.recalculate_scores(
            db,
            project_id,
            subject_type=subject_type,
            subject_id=subject_id,
            arc_id=str(context.get("arc_id") or ""),
            chapter_plan_id=str(context.get("chapter_plan_id") or ""),
        )
        await self._after_change(
            db,
            project_id,
            "editorial_report_created",
            {
                "report_id": report["report_id"],
                "subject_type": subject_type,
                "subject_id": subject_id,
                "report_type": normalized_type,
                "score": score,
            },
        )
        return {"report": _serialize(report), "scores": _serialize(scores)}

    async def _latest_report(
        self,
        db,
        pid: ObjectId,
        subject_type: str,
        subject_id: str,
        report_type: str,
    ) -> Dict[str, Any]:
        return await db.editorial_reports.find_one(
            {
                "project_id": pid,
                "subject_type": subject_type,
                "subject_id": subject_id,
                "report_type": report_type,
            },
            sort=[("created_at", -1)],
        ) or {}

    async def _record_score(
        self,
        db,
        *,
        pid: ObjectId,
        subject_type: str,
        subject_id: str,
        score_type: str,
        dimensions: Dict[str, int],
        evidence: list[str],
    ) -> Dict[str, Any]:
        score = round(mean(dimensions.values())) if dimensions else 0
        doc = {
            "project_id": pid,
            "score_id": str(uuid4()),
            "subject_type": subject_type,
            "subject_id": subject_id,
            "score_type": score_type,
            "score": score,
            "dimensions": dimensions,
            "evidence": _unique(evidence),
            "calculated_at": datetime.utcnow(),
        }
        result = await db.editorial_scores.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def _scene_score(
        self, db, pid: ObjectId, draft_id: str
    ) -> Dict[str, Any]:
        editorial = await self._latest_report(
            db, pid, "scene", draft_id, "editorial"
        )
        dialogue = await self._latest_report(
            db, pid, "scene", draft_id, "dialogue"
        )
        editor_dims = editorial.get("dimension_scores") or {}
        dialogue_dims = dialogue.get("dimension_scores") or {}
        dimensions = {
            "style": _clamp(editor_dims.get("style")),
            "dialogue": _clamp(
                dialogue_dims.get("dialogue")
                or dialogue_dims.get("realism")
                or dialogue.get("score")
            ),
            "pacing": _clamp(editor_dims.get("pacing")),
            "objective_fulfillment": _clamp(
                editor_dims.get("objective_fulfillment")
            ),
            "emotional_progression": _clamp(
                editor_dims.get("emotional_progression")
            ),
        }
        return await self._record_score(
            db,
            pid=pid,
            subject_type="scene",
            subject_id=draft_id,
            score_type="scene_editorial",
            dimensions=dimensions,
            evidence=[
                item
                for report in (editorial, dialogue)
                for item in report.get("evidence") or []
            ],
        )

    async def _chapter_score(
        self, db, pid: ObjectId, draft_id: str
    ) -> Dict[str, Any]:
        draft = await db.chapter_drafts.find_one(
            {"project_id": pid, "draft_id": draft_id}
        )
        if not draft:
            raise ValueError("Chapter draft not found")
        editorial = await self._latest_report(
            db, pid, "chapter", draft_id, "editorial"
        )
        editor_dims = editorial.get("dimension_scores") or {}
        scene_scores = []
        for scene_draft_id in draft.get("source_scene_draft_ids") or []:
            latest = await db.editorial_scores.find_one(
                {
                    "project_id": pid,
                    "subject_type": "scene",
                    "subject_id": scene_draft_id,
                    "score_type": "scene_editorial",
                },
                sort=[("calculated_at", -1)],
            )
            if latest:
                scene_scores.append(int(latest.get("score") or 0))
        continuity = await db.continuity_reports.find_one(
            {"project_id": pid, "subject_id": draft_id},
            sort=[("created_at", -1)],
        ) or {}
        continuity_score = {"PASS": 100, "WARNING": 70, "FAIL": 0}.get(
            str(continuity.get("result") or ""), 50
        )
        dimensions = {
            "scene_quality": round(mean(scene_scores)) if scene_scores else 50,
            "pacing": _clamp(editor_dims.get("pacing")),
            "continuity": continuity_score,
            "emotional_progression": _clamp(
                editor_dims.get("emotional_progression")
            ),
            "objective_fulfillment": _clamp(
                editor_dims.get("objective_fulfillment")
            ),
        }
        return await self._record_score(
            db,
            pid=pid,
            subject_type="chapter",
            subject_id=draft_id,
            score_type="chapter_editorial",
            dimensions=dimensions,
            evidence=list(editorial.get("evidence") or [])
            + [f"continuity={continuity.get('result') or 'unknown'}"],
        )

    async def _arc_score(
        self, db, pid: ObjectId, arc_id: str
    ) -> Dict[str, Any]:
        editorial = await self._latest_report(
            db, pid, "arc", arc_id, "editorial"
        )
        dims = editorial.get("dimension_scores") or {}
        chapter_drafts = await db.chapter_drafts.find(
            {
                "project_id": pid,
                "arc_id": arc_id,
                "status": "approved",
                "active": True,
            },
            {"draft_id": 1},
        ).to_list(length=500)
        chapter_scores = []
        for draft in chapter_drafts:
            score = await db.editorial_scores.find_one(
                {
                    "project_id": pid,
                    "subject_type": "chapter",
                    "subject_id": draft["draft_id"],
                    "score_type": "chapter_editorial",
                },
                sort=[("calculated_at", -1)],
            )
            if score:
                chapter_scores.append(int(score.get("score") or 0))
        dimensions = {
            "chapter_quality": round(mean(chapter_scores))
            if chapter_scores
            else 50,
            "progression_quality": _clamp(dims.get("progression_quality")),
            "consistency": _clamp(dims.get("consistency")),
            "pacing": _clamp(dims.get("pacing")),
            "payoff_readiness": _clamp(dims.get("payoff_readiness")),
        }
        return await self._record_score(
            db,
            pid=pid,
            subject_type="arc",
            subject_id=arc_id,
            score_type="arc_editorial",
            dimensions=dimensions,
            evidence=list(editorial.get("evidence") or []),
        )

    async def recalculate_scores(
        self,
        db,
        project_id: str,
        *,
        subject_type: str,
        subject_id: str,
        arc_id: str = "",
        chapter_plan_id: str = "",
    ) -> list[Dict[str, Any]]:
        pid, _ = await self._project(db, project_id)
        scores = []
        if subject_type == "scene":
            scores.append(await self._scene_score(db, pid, subject_id))
            if chapter_plan_id:
                chapter = await db.chapter_drafts.find_one(
                    {
                        "project_id": pid,
                        "chapter_plan_id": chapter_plan_id,
                        "status": "approved",
                        "active": True,
                    }
                )
                if chapter:
                    scores.append(
                        await self._chapter_score(db, pid, chapter["draft_id"])
                    )
        elif subject_type == "chapter":
            scores.append(await self._chapter_score(db, pid, subject_id))
        elif subject_type == "arc":
            scores.append(await self._arc_score(db, pid, subject_id))
        if arc_id and subject_type != "arc":
            existing_arc_report = await self._latest_report(
                db, pid, "arc", arc_id, "editorial"
            )
            if existing_arc_report:
                scores.append(await self._arc_score(db, pid, arc_id))
        return scores

    async def create_branch(
        self,
        db,
        project_id: str,
        *,
        source_draft_type: str,
        source_draft_id: str,
        title: str = "",
        parent_branch_id: str | None = None,
        revision_pass: str = "development",
    ) -> Dict[str, Any]:
        pid, _ = await self._project(db, project_id)
        normalized_pass = str(revision_pass or "development").strip().lower()
        if normalized_pass not in REVISION_PASSES:
            raise ValueError("Unsupported revision pass")
        source = await self._draft(
            db,
            project_id,
            source_draft_type,
            source_draft_id,
            allowed_statuses={"review", "approved"},
        )
        if parent_branch_id:
            parent = await db.revision_branches.find_one(
                {"project_id": pid, "branch_id": parent_branch_id}
            )
            if not parent:
                raise ValueError("Parent revision branch not found")
            if parent.get("source_draft_id") != source_draft_id:
                raise ValueError("Parent branch references a different source draft")
        now = datetime.utcnow()
        branch = {
            "project_id": pid,
            "branch_id": str(uuid4()),
            "source_draft_id": source_draft_id,
            "source_draft_type": source_draft_type,
            "source_version_number": int(source.get("version_number") or 0),
            "source_text_sha256": hashlib.sha256(
                str(source.get("generated_text") or "").encode("utf-8")
            ).hexdigest(),
            "source_text_snapshot": str(source.get("generated_text") or ""),
            "source_status": source.get("status"),
            "arc_id": source.get("arc_id"),
            "chapter_plan_id": source.get("chapter_plan_id"),
            "scene_id": source.get("scene_id"),
            "parent_branch_id": parent_branch_id,
            "title": title.strip() or f"Revision of {source_draft_id[:8]}",
            "revision_pass": normalized_pass,
            "status": "draft",
            "created_at": now,
            "updated_at": now,
        }
        result = await db.revision_branches.insert_one(branch)
        branch["_id"] = result.inserted_id
        await self._after_change(
            db,
            project_id,
            "revision_branch_created",
            {
                "branch_id": branch["branch_id"],
                "source_draft_id": source_draft_id,
            },
        )
        return _serialize(branch)

    async def generate_revision(
        self,
        db,
        project_id: str,
        branch_id: str,
        *,
        change_reason: str,
        report_ids: list[str] | None = None,
        revision_pass: str | None = None,
        request_id: str | None = None,
        model_preference: str = "auto",
        selected_text: str | None = None,
    ) -> Dict[str, Any]:
        if not change_reason.strip():
            raise ValueError("change_reason is required")
        pid, _ = await self._project(db, project_id)
        branch = await db.revision_branches.find_one(
            {"project_id": pid, "branch_id": branch_id}
        )
        if not branch:
            raise ValueError("Revision branch not found")
        if branch.get("status") not in {"draft", "review"}:
            raise ValueError("Only draft or review branches can generate revisions")
        normalized_pass = str(
            revision_pass or branch.get("revision_pass") or "development"
        ).strip().lower()
        if normalized_pass not in REVISION_PASSES:
            raise ValueError("Unsupported revision pass")
        normalized_request_id = str(request_id or "").strip() or None
        if normalized_request_id:
            existing = await db.revision_versions.find_one(
                {
                    "project_id": pid,
                    "branch_id": branch_id,
                    "request_id": normalized_request_id,
                }
            )
            if existing:
                result = _serialize(existing)
                result["deduplicated"] = True
                return result
        source = await self._draft(
            db,
            project_id,
            branch["source_draft_type"],
            branch["source_draft_id"],
            allowed_statuses={"review", "approved"},
        )
        source_text = str(
            branch.get("source_text_snapshot")
            or source.get("generated_text")
            or ""
        )
        before_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
        if before_hash != branch.get("source_text_sha256"):
            raise ValueError("Approved source draft changed after branch creation")
        query: Dict[str, Any] = {
            "project_id": pid,
            "subject_id": branch["source_draft_id"],
        }
        if report_ids:
            query["report_id"] = {"$in": list(report_ids)}
        reports = await db.editorial_reports.find(query, {"_id": 0}).sort(
            "created_at", -1
        ).to_list(length=100)
        if not reports:
            raise ValueError("Revision generation requires editorial reports")
        revision_context = {
            "subject_type": branch["source_draft_type"],
            "subject_id": branch["source_draft_id"],
            "arc_id": branch.get("arc_id"),
            "branch_id": branch_id,
            "source_text": source_text,
            "source_version_number": source.get("version_number"),
            "editorial_reports": reports,
            "change_reason": change_reason,
            "revision_pass": normalized_pass,
            "protected_elements": list(
                source.get("preserved_elements")
                or ["Approved planning", "Canon", "Timeline", "Required events"]
            ),
        }
        humanization_requested = normalized_pass == "style" and any(
            term in change_reason.lower()
            for term in ("human", "natural", "ai", "artificial", "polish", "rhythm")
        )
        source_word_count = len(re.findall(r"\b[\w'-]+\b", source_text))
        # Full chapters need strong editorial reasoning in Auto mode. The
        # lightweight route remains available for short excerpts, where a
        # compact polish can be validated without risking summary-like output.
        revision_routing_task = (
            "humanization"
            if humanization_requested and source_word_count < 500
            else "editorial"
        )
        payload, metadata = await self._execute(
            db,
            project_id=project_id,
            agent_name="RevisionAgent",
            editorial_context=revision_context,
            changed_entity=f"revision_branch:{branch_id}",
            affected_domain="revision",
            reason="Explicit author revision request requires RevisionAgent",
            routing_task=revision_routing_task,
            model_preference=model_preference,
        )
        proposal = payload.get("revision_proposal") or {}
        generated_text = str(proposal.get("generated_text") or "").strip()
        if not generated_text:
            raise ValueError("RevisionAgent returned empty generated_text")
        quality_issue = None
        if humanization_requested:
            quality_issue = _humanization_quality_failure(source_text, generated_text)
        if quality_issue:
            # A valid JSON response can still be unsafe as a chapter rewrite.
            # Escalate through the existing strong editorial route, without
            # persisting the weak candidate or touching the source draft.
            fallback_payload, fallback_metadata = await self._execute(
                db,
                project_id=project_id,
                agent_name="RevisionAgent",
                editorial_context=revision_context,
                changed_entity=f"revision_branch:{branch_id}",
                affected_domain="revision",
                reason=f"Lightweight humanization failed quality validation: {quality_issue}",
                routing_task="editorial",
                model_preference="auto",
            )
            fallback_proposal = fallback_payload.get("revision_proposal") or {}
            fallback_text = str(fallback_proposal.get("generated_text") or "").strip()
            fallback_issue = _humanization_quality_failure(source_text, fallback_text)
            if fallback_issue:
                raise ValueError(
                    f"Humanization quality validation failed after escalation: {fallback_issue}"
                )
            payload, metadata = fallback_payload, fallback_metadata
            metadata["quality_escalated"] = True
            metadata["quality_escalation_reason"] = quality_issue
            proposal = fallback_proposal
            generated_text = fallback_text
        if selected_text:
            # A focused edit asks the model to rewrite one passage. Models
            # usually return just that passage; the proposal must still be the
            # whole chapter, or applying it would replace the chapter with one
            # paragraph.
            generated_text = _splice_selected_revision(
                source_text, selected_text, generated_text
            )
        latest = await db.revision_versions.find_one(
            {"project_id": pid, "branch_id": branch_id},
            sort=[("version_number", -1)],
        )
        now = datetime.utcnow()
        version = {
            "project_id": pid,
            "revision_id": str(uuid4()),
            "branch_id": branch_id,
            "version_number": int((latest or {}).get("version_number") or 0) + 1,
            "parent_revision_id": (latest or {}).get("revision_id"),
            "generated_text": generated_text,
            "summary": str(proposal.get("summary") or ""),
            "applied_recommendations": list(
                proposal.get("applied_recommendations") or []
            ),
            "change_reason": change_reason,
            "revision_pass": normalized_pass,
            "changes": list(proposal.get("changes") or []),
            "reason": str(
                proposal.get("reason")
                or payload.get("reasoning")
                or change_reason
            ),
            "affected_elements": list(proposal.get("affected_elements") or []),
            "estimated_improvement": str(
                proposal.get("estimated_improvement") or "medium"
            ),
            "what_stays_unchanged": list(
                proposal.get("what_stays_unchanged")
                or ["Approved planning", "Canon", "Timeline"]
            ),
            "request_id": normalized_request_id,
            "created_by": "RevisionAgent",
            "generation_metadata": metadata,
            "created_at": now,
        }
        result = await db.revision_versions.insert_one(version)
        version["_id"] = result.inserted_id
        after_source = await self._draft(
            db,
            project_id,
            branch["source_draft_type"],
            branch["source_draft_id"],
            allowed_statuses={"review", "approved"},
        )
        after_hash = hashlib.sha256(
            str(after_source.get("generated_text") or "").encode("utf-8")
        ).hexdigest()
        if before_hash != after_hash:
            raise RuntimeError("Approved source draft was modified during revision")
        await db.revision_branches.update_one(
            {"_id": branch["_id"]},
            {
                "$set": {
                    "latest_revision_id": version["revision_id"],
                    "updated_at": now,
                }
            },
        )
        await self._after_change(
            db,
            project_id,
            "revision_version_created",
            {
                "branch_id": branch_id,
                "revision_id": version["revision_id"],
                "version_number": version["version_number"],
            },
        )
        return _serialize(version)

    async def transition_branch(
        self,
        db,
        project_id: str,
        branch_id: str,
        status: str,
        *,
        reason: str = "",
    ) -> Dict[str, Any]:
        pid, _ = await self._project(db, project_id)
        normalized = status.lower()
        if normalized not in BRANCH_STATUSES:
            raise ValueError("Unsupported revision branch status")
        branch = await db.revision_branches.find_one(
            {"project_id": pid, "branch_id": branch_id}
        )
        if not branch:
            raise ValueError("Revision branch not found")
        current = str(branch.get("status") or "draft")
        if normalized not in BRANCH_TRANSITIONS.get(current, set()):
            raise ValueError(f"Cannot transition revision branch {current} -> {normalized}")
        if normalized == "approved":
            if current != "review":
                raise ValueError("Revision branch must be reviewed before approval")
            if not await db.revision_versions.find_one(
                {"project_id": pid, "branch_id": branch_id}
            ):
                raise ValueError("Revision branch has no proposal version")
        if normalized == "rejected" and not reason.strip():
            raise ValueError("A rejection reason is required")
        now = datetime.utcnow()
        await db.revision_branches.update_one(
            {"_id": branch["_id"]},
            {
                "$set": {
                    "status": normalized,
                    "review_reason": reason.strip(),
                    "updated_at": now,
                    f"{normalized}_at": now,
                }
            },
        )
        await self._after_change(
            db,
            project_id,
            "revision_branch_changed",
            {"branch_id": branch_id, "status": normalized},
        )
        return _serialize(
            await db.revision_branches.find_one({"_id": branch["_id"]})
        )

    async def apply_revision(
        self,
        db,
        project_id: str,
        branch_id: str,
        *,
        revision_id: str | None = None,
    ) -> Dict[str, Any]:
        """Promote an approved proposal into the existing draft lineage for final review."""
        pid, _ = await self._project(db, project_id)
        branch = await db.revision_branches.find_one(
            {"project_id": pid, "branch_id": branch_id}
        )
        if not branch:
            raise ValueError("Revision branch not found")
        if branch.get("status") != "approved":
            raise ValueError("Approve the revision proposal before using it as a draft")
        query: Dict[str, Any] = {"project_id": pid, "branch_id": branch_id}
        if revision_id:
            query["revision_id"] = revision_id
        revision = await db.revision_versions.find_one(
            query,
            sort=[("version_number", -1)],
        )
        if not revision:
            raise ValueError("Revision proposal not found")
        if revision.get("promoted_draft_id"):
            existing_collection = (
                "scene_drafts"
                if branch.get("source_draft_type") == "scene"
                else "chapter_drafts"
            )
            existing = await db[existing_collection].find_one(
                {
                    "project_id": pid,
                    "draft_id": revision["promoted_draft_id"],
                }
            )
            if existing:
                result = _serialize(existing)
                result["deduplicated"] = True
                return result

        draft_type = str(branch.get("source_draft_type") or "")
        collection = "scene_drafts" if draft_type == "scene" else "chapter_drafts"
        identity = "scene_id" if draft_type == "scene" else "chapter_plan_id"
        source = await db[collection].find_one(
            {"project_id": pid, "draft_id": branch["source_draft_id"]}
        )
        if not source:
            raise ValueError("Source draft not found")
        lineage: Dict[str, Any] = {"project_id": pid, identity: source[identity]}
        if draft_type != "scene" and not source.get("chapter_plan_id"):
            # Chapters written with "Start writing now" have no chapter plan.
            # Matching on chapter_plan_id=None would touch every such chapter
            # in the project, so scope the lineage to this chapter number.
            lineage["chapter_number"] = source.get("chapter_number")
        latest = await db[collection].find_one(
            lineage,
            sort=[("version_number", -1)],
        )
        next_version = int((latest or {}).get("version_number") or 0) + 1
        now = datetime.utcnow()
        await db[collection].update_many(
            {**lineage, "active": True},
            {"$set": {"active": False, "updated_at": now}},
        )
        promoted = {
            key: value
            for key, value in source.items()
            if key not in {
                "_id",
                "draft_id",
                "version_number",
                "version_label",
                "parent_version_id",
                "status",
                "active",
                "generated_text",
                "validation_result",
                "continuity_report_id",
                "request_id",
                "writer_room_id",
                "writer_room_source_id",
                "review_reason",
                "approved_at",
                "rejected_at",
                "archived_at",
                "created_at",
                "updated_at",
            }
        }
        promoted.update(
            {
                "draft_id": str(uuid4()),
                "version_number": next_version,
                "version_label": f"Version {chr(64 + min(next_version, 26))}",
                "parent_version_id": source["draft_id"],
                "status": "review",
                "active": True,
                "generated_text": revision["generated_text"],
                "word_count": len(str(revision["generated_text"] or "").split()),
                "generated_by": "RevisionAgent",
                "operation": revision.get("revision_pass") or "revision",
                "why": revision.get("reason") or revision.get("change_reason"),
                "expected_impact": revision.get("estimated_improvement") or "medium",
                "affected_narrative_areas": list(
                    revision.get("affected_elements") or []
                ),
                "preserved_elements": list(
                    revision.get("what_stays_unchanged") or []
                ),
                "change_reason": revision.get("change_reason") or "",
                "revision_branch_id": branch_id,
                "revision_id": revision["revision_id"],
                "created_at": now,
                "updated_at": now,
            }
        )
        inserted = await db[collection].insert_one(promoted)
        promoted["_id"] = inserted.inserted_id
        if draft_type == "scene":
            report = await draft_validation_service.validate_scene_draft(
                db, project_id, promoted, stage="revision_promotion"
            )
        else:
            report = await draft_validation_service.validate_chapter_draft(
                db, project_id, promoted, stage="revision_promotion"
            )
        await db[collection].update_one(
            {"_id": inserted.inserted_id},
            {
                "$set": {
                    "validation_result": report["result"],
                    "continuity_report_id": report["report_id"],
                }
            },
        )
        await db.revision_versions.update_one(
            {"_id": revision["_id"]},
            {
                "$set": {
                    "promoted_draft_id": promoted["draft_id"],
                    "promoted_at": now,
                }
            },
        )
        await self._after_change(
            db,
            project_id,
            "revision_applied_to_draft",
            {
                "branch_id": branch_id,
                "revision_id": revision["revision_id"],
                "draft_id": promoted["draft_id"],
                "draft_type": draft_type,
            },
        )
        promoted["validation_result"] = report["result"]
        promoted["continuity_report_id"] = report["report_id"]
        return {
            "draft": _serialize(promoted),
            "continuity_report": _serialize(report),
        }

    async def lineage(
        self, db, project_id: str, branch_id: str
    ) -> Dict[str, Any]:
        pid, _ = await self._project(db, project_id)
        branch = await db.revision_branches.find_one(
            {"project_id": pid, "branch_id": branch_id}
        )
        if not branch:
            raise ValueError("Revision branch not found")
        ancestors = []
        current = branch
        seen = set()
        while current and current.get("branch_id") not in seen:
            seen.add(current.get("branch_id"))
            versions = await db.revision_versions.find(
                {"project_id": pid, "branch_id": current["branch_id"]}
            ).sort("version_number", 1).to_list(length=500)
            ancestors.append({**current, "versions": versions})
            parent_id = current.get("parent_branch_id")
            current = (
                await db.revision_branches.find_one(
                    {"project_id": pid, "branch_id": parent_id}
                )
                if parent_id
                else None
            )
        return _serialize(
            {
                "branch": branch,
                "lineage": list(reversed(ancestors)),
            }
        )

    async def compare(
        self,
        db,
        project_id: str,
        branch_id: str,
        *,
        revision_id: str | None = None,
    ) -> Dict[str, Any]:
        pid, _ = await self._project(db, project_id)
        branch = await db.revision_branches.find_one(
            {"project_id": pid, "branch_id": branch_id}
        )
        if not branch:
            raise ValueError("Revision branch not found")
        source = await self._draft(
            db,
            project_id,
            branch["source_draft_type"],
            branch["source_draft_id"],
            # Same rule as creating, generating and applying a revision; a
            # chapter in review must be comparable before the author applies it.
            allowed_statuses={"review", "approved"},
        )
        query: Dict[str, Any] = {"project_id": pid, "branch_id": branch_id}
        if revision_id:
            query["revision_id"] = revision_id
        revision = await db.revision_versions.find_one(
            query, sort=[("version_number", -1)]
        )
        if not revision:
            raise ValueError("Revision version not found")
        source_text = str(source.get("generated_text") or "")
        revision_text = str(revision.get("generated_text") or "")
        matcher = difflib.SequenceMatcher(None, source_text, revision_text)
        diff = list(
            difflib.unified_diff(
                source_text.splitlines(),
                revision_text.splitlines(),
                fromfile="source",
                tofile=f"revision-{revision['version_number']}",
                lineterm="",
            )
        )
        return _serialize(
            {
                "branch_id": branch_id,
                "source_draft_id": branch["source_draft_id"],
                "revision_id": revision["revision_id"],
                "version_number": revision["version_number"],
                "source_text": source_text,
                "revision_text": revision_text,
                "similarity": round(matcher.ratio(), 4),
                "source_word_count": len(source_text.split()),
                "revision_word_count": len(revision_text.split()),
                "diff": diff[:500],
            }
        )

    async def dashboard(self, db, project_id: str) -> Dict[str, Any]:
        pid, _ = await self._project(db, project_id)
        reports = await db.editorial_reports.find(
            {"project_id": pid}
        ).sort("created_at", -1).to_list(length=5000)
        scores = await db.editorial_scores.find(
            {"project_id": pid}
        ).sort("calculated_at", -1).to_list(length=5000)
        latest_scores: Dict[tuple[str, str, str], Dict[str, Any]] = {}
        for score in scores:
            key = (
                str(score.get("subject_type")),
                str(score.get("subject_id")),
                str(score.get("score_type")),
            )
            latest_scores.setdefault(key, score)
        branches = await db.revision_branches.find(
            {"project_id": pid}
        ).sort("updated_at", -1).to_list(length=5000)
        scene_drafts = await db.scene_drafts.find(
            {"project_id": pid, "status": "approved", "active": True}
        ).to_list(length=5000)
        chapter_drafts = await db.chapter_drafts.find(
            {"project_id": pid, "status": "approved", "active": True}
        ).to_list(length=5000)
        report_keys = {
            (
                str(report.get("subject_type")),
                str(report.get("subject_id")),
                str(report.get("report_type")),
            )
            for report in reports
        }
        editorial_queue = []
        for subject_type, drafts in (
            ("scene", scene_drafts),
            ("chapter", chapter_drafts),
        ):
            for draft in drafts:
                missing = [
                    report_type
                    for report_type in ("editorial", "dialogue")
                    if (subject_type, draft["draft_id"], report_type)
                    not in report_keys
                ]
                if missing:
                    editorial_queue.append(
                        {
                            "subject_type": subject_type,
                            "subject_id": draft["draft_id"],
                            "arc_id": draft.get("arc_id"),
                            "chapter_plan_id": draft.get("chapter_plan_id"),
                            "scene_id": draft.get("scene_id"),
                            "missing_reviews": missing,
                        }
                    )
        blockers = [
            {
                "report_id": report.get("report_id"),
                "subject_type": report.get("subject_type"),
                "subject_id": report.get("subject_id"),
                "report_type": report.get("report_type"),
                "blockers": report.get("blockers") or [],
                "score": report.get("score"),
            }
            for report in reports
            if report.get("blockers") or int(report.get("score") or 0) < 60
        ]
        return _serialize(
            {
                "project_id": pid,
                "reports": reports,
                "scores": list(latest_scores.values()),
                "score_history": scores,
                "branches": branches,
                "editorial_queue": editorial_queue,
                "revision_queue": [
                    branch
                    for branch in branches
                    if branch.get("status") in {"draft", "review"}
                ],
                "blockers": blockers,
                "generated_at": datetime.utcnow(),
            }
        )


editorial_service = EditorialService()
