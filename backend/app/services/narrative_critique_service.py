"""Actionable critique projection over Story Health and shared narrative evidence."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any, Dict, Iterable

from bson import ObjectId

from app.services.narrative_analysis_engine import narrative_analysis_engine
from app.services.story_health_service import story_health_service
from app.services.story_quality_service import analyze_text


ROUTING = {
    "canon": "canon_intelligence",
    "timeline": "timeline_intelligence",
    "character": "character_intelligence",
    "dialogue": "dialogue_coach",
    "pacing": "story_health",
    "continuity": "story_health",
    "plot": "plot_thread_intelligence",
    "world": "worldbuilding_consultant",
    "balance": "developmental_editor",
}

CATEGORY_DOMAINS = {
    "weak_motivation": "character",
    "missing_emotional_payoff": "character",
    "inconsistent_dialogue": "dialogue",
    "redundant_exposition": "dialogue",
    "weak_foreshadowing": "plot",
    "repetitive_scene": "pacing",
    "weak_chapter_hook": "pacing",
    "weak_chapter_ending": "pacing",
    "repetitive_chapter_opening": "pacing",
    "generic_prose_pattern": "dialogue",
    "repetitive_prose_pattern": "pacing",
    "missing_conflict_escalation": "pacing",
    "worldbuilding_inconsistency": "world",
    "structural_weakness": "balance",
}


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


def _tokens(value: Any) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9']+", str(value or "").lower()) if len(token) > 3}


def _similarity(left: Any, right: Any) -> float:
    a, b = _tokens(left), _tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, min(len(a), len(b)))


def _draft_text(document: Dict[str, Any]) -> str:
    return str(
        document.get("generated_text")
        or document.get("content")
        or document.get("prose")
        or document.get("text")
        or ""
    ).strip()


class NarrativeCritiqueService:
    async def _project(self, db, project_id: str) -> ObjectId:
        if not ObjectId.is_valid(project_id):
            raise ValueError("Invalid project ID")
        pid = ObjectId(project_id)
        if not await db.projects.find_one({"_id": pid}):
            raise ValueError("Project not found")
        return pid

    def _finding(
        self,
        category: str,
        severity: str,
        explanation: str,
        *,
        evidence: Iterable[Any],
        improvement: str,
        chapters: Iterable[int] = (),
        scenes: Iterable[str] = (),
        elements: Iterable[str] = (),
        confidence: float = .75,
        source_finding_id: str = "",
    ) -> Dict[str, Any]:
        domain = CATEGORY_DOMAINS.get(category, "balance")
        chapter_list = sorted({int(value) for value in chapters if value is not None})
        scene_list = sorted({str(value) for value in scenes if value})
        element_list = sorted({str(value) for value in elements if value})
        basis = "|".join([category, explanation, str(chapter_list), str(scene_list), str(element_list)])
        return {
            "finding_id": hashlib.sha256(basis.encode("utf-8")).hexdigest()[:32],
            "finding_type": "critique",
            "domain": domain,
            "category": category,
            "severity": severity,
            "explanation": explanation,
            "affected_chapters": chapter_list,
            "affected_scenes": scene_list,
            "affected_elements": element_list,
            "evidence": _serialize(list(evidence)),
            "recommended_actions": [improvement],
            "suggested_improvement": improvement,
            "responsible_subsystem": ROUTING[domain],
            "confidence": round(float(confidence), 3),
            "source_service": "narrative_critique_service",
            "source_finding_id": source_finding_id,
        }

    async def _qualitative_findings(self, db, pid: ObjectId) -> list[Dict[str, Any]]:
        findings: list[Dict[str, Any]] = []
        chapters = await db.chapter_intelligence.find({"project_id": pid, "active": True}).sort("chapter_number", 1).to_list(length=10000)
        characters = await db.character_bibles.find({"project_id": pid}).to_list(length=5000)
        for character in characters:
            name = str(character.get("name") or "").strip()
            if not name or str(character.get("current_status") or "active").lower() in {"archived", "dead", "departed"}:
                continue
            motivations = list(character.get("motivations") or character.get("goals") or [])
            appearances = [
                item for item in chapters
                if name.lower() in {str(value).lower() for value in item.get("characters_present") or []}
            ]
            motivation_text = " ".join(map(str, motivations))
            chapter_text = " ".join(str(item.get("chapter_summary") or item.get("character_changes") or "") for item in appearances)
            if not motivations or (len(appearances) >= 3 and _similarity(motivation_text, chapter_text) < .15):
                findings.append(self._finding(
                    "weak_motivation", "medium",
                    f"{name}'s recorded actions are not clearly connected to an established motivation.",
                    evidence=[{"motivations": motivations, "appearance_chapters": [item.get("chapter_number") for item in appearances]}],
                    improvement="Clarify the want, fear, or belief driving the cited actions, or revise the actions to express the established motivation.",
                    chapters=[item.get("chapter_number") for item in appearances], elements=[name], confidence=.74,
                ))

        arcs = await db.story_arcs.find({"project_id": pid, "development_status": {"$in": ["completed", "archived"]}}).to_list(length=1000)
        progressions = await db.character_progressions.find({"project_id": pid}).to_list(length=5000)
        for arc in arcs:
            related = [item for item in progressions if item.get("arc_id") == arc.get("arc_id")]
            for item in related:
                if not item.get("emotional_growth") and not item.get("arc_end_state"):
                    findings.append(self._finding(
                        "missing_emotional_payoff", "high",
                        f"Completed arc {arc.get('title') or arc.get('arc_id')} has no recorded emotional payoff for {item.get('character')}.",
                        evidence=[{"arc_id": arc.get("arc_id"), "progression_id": item.get("progression_id")}],
                        improvement="Add an observable emotional consequence that resolves or deliberately complicates the character's established internal movement.",
                        elements=[str(arc.get("arc_id")), str(item.get("character"))], confidence=.9,
                    ))

        dialogue_reports = await db.editorial_reports.find({
            "project_id": pid, "review_type": "dialogue",
        }).sort("created_at", -1).to_list(length=5000)
        for report in dialogue_reports:
            dimensions = report.get("dimension_scores") or {}
            weakest = min([
                float(dimensions.get(key, 100)) for key in ("distinctiveness", "speaker_differentiation", "conversation_flow")
            ] or [100])
            if weakest < 70:
                findings.append(self._finding(
                    "inconsistent_dialogue", "high" if weakest < 55 else "medium",
                    f"Dialogue review found weak voice differentiation or conversation consistency for {report.get('subject_type')} {report.get('subject_id')}.",
                    evidence=[{"dimension_scores": dimensions, "report_id": report.get("report_id"), "findings": report.get("findings")}],
                    improvement="Revise through a proposal so each speaker's vocabulary, rhythm, knowledge, and emotional objective remain distinct.",
                    scenes=[str(report.get("subject_id"))] if report.get("subject_type") == "scene" else [],
                    elements=[str(report.get("report_id"))], confidence=.93,
                ))

        foreshadow = await db.foreshadow_registry_v2.find({
            "project_id": pid, "status": {"$nin": ["paid_off", "resolved", "abandoned"]},
        }).to_list(length=5000)
        for item in foreshadow:
            if not item.get("payoff_target") or not (item.get("payoff_arc_id") or item.get("chapter_payoff")):
                findings.append(self._finding(
                    "weak_foreshadowing", "medium",
                    f"Foreshadowing seed has no concrete payoff location: {item.get('seed') or item.get('entry_id')}.",
                    evidence=[{"entry_id": item.get("entry_id"), "payoff_target": item.get("payoff_target"), "status": item.get("status")}],
                    improvement="Define the intended payoff and link it to a later arc, chapter, or timeline event before adding more references.",
                    chapters=[item.get("chapter_planted")] if item.get("chapter_planted") else [],
                    elements=[str(item.get("entry_id") or item.get("_id"))], confidence=.92,
                ))

        scenes = await db.scene_plans.find({"project_id": pid}).to_list(length=10000)
        chapter_order = {
            str(item.get("chapter_plan_id")): int(item.get("chapter_number") or 0)
            for item in await db.chapter_plans.find(
                {"project_id": pid}, {"chapter_plan_id": 1, "chapter_number": 1}
            ).to_list(length=5000)
        }
        scenes.sort(key=lambda item: (
            chapter_order.get(str(item.get("chapter_plan_id")), 10**9),
            int(item.get("order") or 0),
        ))
        for index, left in enumerate(scenes):
            for right in scenes[index + 1:index + 6]:
                if left.get("scene_id") == right.get("scene_id"):
                    continue
                similarity = _similarity(left.get("purpose") or left.get("outcome"), right.get("purpose") or right.get("outcome"))
                if similarity >= .82:
                    findings.append(self._finding(
                        "repetitive_scene", "medium",
                        f"Scenes {left.get('title') or left.get('scene_id')} and {right.get('title') or right.get('scene_id')} appear to perform the same narrative work.",
                        evidence=[{"similarity": round(similarity, 2), "left_purpose": left.get("purpose"), "right_purpose": right.get("purpose")}],
                        improvement="Differentiate the conflict, revelation, emotional turn, or outcome; otherwise consider combining the scenes.",
                        scenes=[str(left.get("scene_id")), str(right.get("scene_id"))], confidence=.78,
                    ))

        scene_drafts = await db.scene_drafts.find({"project_id": pid, "active": True}).to_list(length=5000)
        for draft in scene_drafts:
            text = str(draft.get("content") or draft.get("prose") or draft.get("text") or "")
            for item in analyze_text(text).get("findings") or []:
                if item.get("category") in {"excessive_exposition", "emotional_over_explanation"}:
                    findings.append(self._finding(
                        "redundant_exposition", "medium",
                        str(item.get("message")), evidence=item.get("evidence") or [],
                        improvement="Remove repeated explanation and let action, dialogue, or concrete consequence carry the cited information.",
                        scenes=[str(draft.get("scene_id") or draft.get("draft_id"))], confidence=.82,
                    ))

        chapter_drafts = await db.chapter_drafts.find({"project_id": pid, "active": True}).sort("chapter_number", 1).to_list(length=5000)
        chapter_openings: list[tuple[int, str]] = []
        for draft in chapter_drafts:
            text = _draft_text(draft)
            if text:
                chapter_number = int(draft.get("chapter_number") or 0)
                first_words = " ".join(re.findall(r"[a-z0-9']+", text[:700].lower()))
                if chapter_number:
                    chapter_openings.append((chapter_number, first_words[:180]))
                quality = analyze_text(text)
                for quality_finding in quality.get("findings") or []:
                    category = str(quality_finding.get("category") or "prose_quality")
                    if category == "ai_writing_fingerprint":
                        category = "generic_prose_pattern"
                    elif category.startswith("repetitive_"):
                        category = "repetitive_prose_pattern"
                    findings.append(self._finding(
                        category,
                        "medium" if category in {"generic_prose_pattern", "excessive_exposition"} else "low",
                        f"Chapter {draft.get('chapter_number') or 'draft'}: {quality_finding.get('message')}",
                        evidence=quality_finding.get("evidence") or [],
                        improvement=(
                            "Replace familiar phrasing with specific images, choices, and consequences belonging to this story."
                            if category == "generic_prose_pattern"
                            else "Vary the sentence, paragraph, or dialogue pattern while preserving the author's voice."
                            if category == "repetitive_prose_pattern"
                            else "Let action, sensory detail, and subtext carry more of the meaning instead of explaining it."
                        ),
                        chapters=[draft.get("chapter_number")] if draft.get("chapter_number") else [],
                        elements=[str(draft.get("draft_id") or draft.get("_id") or "")],
                        confidence=.82,
                    ))
            words = text.split()
            if len(words) < 350:
                continue
            opening = " ".join(words[:140]).lower()
            ending = " ".join(words[-140:]).lower()
            chapter_number = draft.get("chapter_number")
            if not re.search(r"[?!]|\b(?:but|until|suddenly|refused|discovered|threat|danger|wanted|must)\b", opening):
                findings.append(self._finding(
                    "weak_chapter_hook", "low",
                    f"Chapter {chapter_number or draft.get('draft_id')} opens without a detected question, disruption, desire, or immediate tension marker.",
                    evidence=[" ".join(words[:45])],
                    improvement="Strengthen the opening with a concrete desire, disruption, unanswered question, or consequence already grounded in the chapter plan.",
                    chapters=[chapter_number] if chapter_number else [], confidence=.58,
                ))
            if not re.search(r"[?!]|\b(?:but|however|until|then|realized|decided|discovered|promised|refused|arrived)\b", ending):
                findings.append(self._finding(
                    "weak_chapter_ending", "low",
                    f"Chapter {chapter_number or draft.get('draft_id')} ends without a detected turn, decision, revelation, consequence, or forward question.",
                    evidence=[" ".join(words[-45:])],
                    improvement="End on a changed condition, costly decision, revelation, consequence, or unresolved pressure supported by the chapter's existing events.",
                    chapters=[chapter_number] if chapter_number else [], confidence=.58,
                ))

        opening_groups: Dict[str, list[int]] = {}
        for chapter_number, opening in chapter_openings:
            if opening:
                opening_groups.setdefault(opening, []).append(chapter_number)
        for opening, chapters_for_opening in opening_groups.items():
            if len(chapters_for_opening) >= 2:
                findings.append(self._finding(
                    "repetitive_chapter_opening",
                    "low",
                    "Multiple chapters begin with nearly the same sentence shape or phrase.",
                    evidence=[f"Chapters {', '.join(map(str, chapters_for_opening))}: {opening}"],
                    improvement="Vary the entry point, immediate sensory focus, or character action unless the repeated opening is an intentional motif.",
                    chapters=chapters_for_opening,
                    confidence=.86,
                ))

        chapter_plans = await db.chapter_plans.find({"project_id": pid}).sort("chapter_number", 1).to_list(length=5000)
        for start in range(max(0, len(chapter_plans) - 2)):
            window = chapter_plans[start:start + 3]
            if len(window) == 3 and all(not str(item.get("conflict") or "").strip() for item in window):
                findings.append(self._finding(
                    "missing_conflict_escalation", "high",
                    f"Chapters {window[0].get('chapter_number')}–{window[-1].get('chapter_number')} have no planned conflict escalation.",
                    evidence=[{"chapter_number": item.get("chapter_number"), "purpose": item.get("purpose")} for item in window],
                    improvement="Define how opposition, cost, urgency, or irreversible consequence increases across this chapter sequence.",
                    chapters=[item.get("chapter_number") for item in window], confidence=.94,
                ))
        return findings

    async def refresh(self, db, project_id: str, *, include_latest_agent_audit: bool = True) -> Dict[str, Any]:
        pid = await self._project(db, project_id)
        health_before = await story_health_service.calculate(db, project_id)
        platform = await narrative_analysis_engine.platform(db, project_id)
        qualitative = await self._qualitative_findings(db, pid)
        if include_latest_agent_audit:
            audit = await db.story_audit_reports.find_one({"project_id": pid}, sort=[("created_at", -1)])
            for item in (audit or {}).get("findings") or []:
                if not item.get("message"):
                    continue
                subject_type = str(item.get("subject_type") or "balance")
                category = str(item.get("category") or "structural_weakness")
                if category not in CATEGORY_DOMAINS:
                    CATEGORY_DOMAINS[category] = subject_type if subject_type in ROUTING else "balance"
                qualitative.append(self._finding(
                    category,
                    str(item.get("severity") or "medium").replace("warning", "medium"),
                    str(item.get("message")),
                    evidence=item.get("evidence") or [],
                    improvement=str((item.get("recommended_actions") or ["Review the cited evidence and choose an author-approved structural improvement."])[0]),
                    chapters=item.get("affected_chapters") or [], scenes=item.get("affected_scenes") or [],
                    elements=item.get("affected_elements") or [], confidence=float(item.get("confidence") or .72),
                    source_finding_id=str(item.get("finding_id") or ""),
                ))

        now = datetime.utcnow()
        active_ids = {item["finding_id"] for item in qualitative}
        stale_query: Dict[str, Any] = {
            "project_id": pid, "finding_type": "critique", "status": {"$in": ["open", "acknowledged"]},
        }
        if active_ids:
            stale_query["finding_id"] = {"$nin": list(active_ids)}
        await db.narrative_findings.update_many(stale_query, {"$set": {"status": "resolved", "resolved_at": now}})
        for finding in qualitative:
            await db.narrative_findings.update_one(
                {"project_id": pid, "finding_id": finding["finding_id"]},
                {"$set": {**finding, "project_id": pid, "last_seen_at": now},
                 "$setOnInsert": {"first_seen_at": now, "status": "open"}},
                upsert=True,
            )
        await narrative_analysis_engine.refresh_scores(db, project_id)
        health_after = await story_health_service.calculate(db, project_id)
        current = await db.narrative_findings.find({
            "project_id": pid, "status": {"$in": ["open", "acknowledged"]},
        }).sort([("severity", -1), ("first_seen_at", 1)]).to_list(length=20000)
        normalized = []
        for item in current:
            domain = str(item.get("domain") or "balance")
            normalized.append({
                **item,
                "responsible_subsystem": item.get("responsible_subsystem") or ROUTING.get(domain, "story_health"),
                "suggested_improvement": item.get("suggested_improvement") or ((item.get("recommended_actions") or ["Review the evidence and choose an author-approved improvement."])[0]),
            })
        return _serialize({
            "story_health_before": health_before.get("story_health_score"),
            "story_health_after": health_after.get("story_health_score"),
            "analysis_id": platform["snapshot"].get("analysis_id"),
            "findings": normalized,
            "critique_finding_count": sum(1 for item in normalized if item.get("finding_type") == "critique"),
            "generated_at": now,
            "author_control": "Improvements are proposals only and are never applied automatically.",
        })

    async def get(self, db, project_id: str) -> Dict[str, Any]:
        pid = await self._project(db, project_id)
        platform = await narrative_analysis_engine.platform(db, project_id)
        findings = await db.narrative_findings.find({
            "project_id": pid, "status": {"$in": ["open", "acknowledged"]},
        }).to_list(length=20000)
        if not any(item.get("finding_type") == "critique" for item in findings):
            return await self.refresh(db, project_id)
        health = await story_health_service.calculate(db, project_id)
        return _serialize({
            "story_health_before": health.get("story_health_score"),
            "story_health_after": health.get("story_health_score"),
            "analysis_id": platform["snapshot"].get("analysis_id"),
            "findings": findings,
            "critique_finding_count": sum(1 for item in findings if item.get("finding_type") == "critique"),
            "generated_at": datetime.utcnow(),
            "author_control": "Improvements are proposals only and are never applied automatically.",
        })


narrative_critique_service = NarrativeCritiqueService()
