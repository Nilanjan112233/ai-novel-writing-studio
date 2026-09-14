"""Read-only story auditing across deterministic records and one audit agent."""
from __future__ import annotations

from datetime import datetime
import json
from typing import Any, Dict, Iterable
from uuid import uuid4

from bson import ObjectId

from app.services.chapter_intelligence_service import chapter_intelligence_service
from app.services.narrative_studio import narrative_studio_service
from app.services.orchestration_engine import orchestration_engine
from app.services.orchestration_service_v2 import orchestration_service_v2
from app.services.project_event_service import emit_project_event
from app.services.story_bible_service import rebuild_story_bible
from app.services.story_quality_service import story_quality_service
from app.services.narrative_analysis_engine import narrative_analysis_engine


AUDIT_CONTEXT_BUDGET = 22000
_SEVERITY_ORDER = {"critical": 0, "error": 0, "high": 1, "warning": 2, "medium": 2, "low": 3, "info": 4}


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


def _unique_findings(findings: Iterable[Dict[str, Any]]) -> list[Dict[str, Any]]:
    result = []
    seen = set()
    for finding in findings:
        marker = (
            str(finding.get("category")),
            str(finding.get("subject_id")),
            str(finding.get("message")),
        )
        if marker in seen:
            continue
        seen.add(marker)
        result.append(finding)
    return result


def _clip(value: Any, limit: int = 320) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else f"{text[: limit - 1]}…"


def _compact_values(values: Iterable[Any], *, limit: int, text_limit: int = 240) -> list[Any]:
    compacted: list[Any] = []
    for value in list(values or [])[:limit]:
        if isinstance(value, dict):
            compacted.append(
                {
                    str(key): _clip(item, text_limit)
                    for key, item in list(value.items())[:6]
                    if item not in (None, "", [], {})
                }
            )
        else:
            compacted.append(_clip(value, text_limit))
    return compacted


def _compact_audit_context(
    analysis: Dict[str, Any],
    chapter_memory: Dict[str, Any],
    deterministic_findings: list[Dict[str, Any]],
    canon_conflicts: list[Dict[str, Any]],
) -> Dict[str, Any]:
    """Pack shared analysis evidence into a stable, large-novel prompt budget."""
    snapshot = analysis.get("snapshot") or {}
    ordered_findings = sorted(
        deterministic_findings,
        key=lambda item: (
            _SEVERITY_ORDER.get(str(item.get("severity") or "warning").lower(), 5),
            str(item.get("category") or ""),
            str(item.get("finding_id") or ""),
        ),
    )

    findings = [
        {
            "finding_id": item.get("finding_id"),
            "category": item.get("category"),
            "severity": item.get("severity"),
            "message": _clip(item.get("message"), 360),
            "evidence": _compact_values(item.get("evidence") or [], limit=3),
            "affected_chapters": list(item.get("affected_chapters") or [])[:12],
            "affected_scenes": list(item.get("affected_scenes") or [])[:12],
            "recommended_actions": _compact_values(
                item.get("recommended_actions") or [], limit=3
            ),
        }
        for item in ordered_findings[:80]
    ]
    recent_chapters = [
        {
            "chapter_number": item.get("chapter_number"),
            "title": _clip(item.get("title"), 120),
            "summary": _clip(item.get("chapter_summary"), 420),
            "events": _compact_values(item.get("important_events") or [], limit=4),
            "characters": _compact_values(item.get("characters_present") or [], limit=10, text_limit=80),
            "unresolved_questions": _compact_values(item.get("unresolved_questions") or [], limit=4),
            "future_obligations": _compact_values(item.get("future_obligations") or [], limit=4),
        }
        for item in list(chapter_memory.get("recent") or [])[-10:]
    ]
    obligations = [
        {
            "chapter_number": item.get("chapter_number"),
            "title": _clip(item.get("title"), 120),
            "unresolved_questions": _compact_values(item.get("unresolved_questions") or [], limit=4),
            "future_obligations": _compact_values(item.get("future_obligations") or [], limit=6),
        }
        for item in list(chapter_memory.get("long_range_obligations") or [])[:20]
    ]
    conflicts = [
        {
            "conflict_id": item.get("conflict_id") or item.get("id"),
            "type": item.get("conflict_type") or item.get("type"),
            "severity": item.get("severity"),
            "message": _clip(item.get("message") or item.get("explanation"), 360),
            "canon_ids": list(item.get("canon_ids") or [])[:8],
            "evidence": _compact_values(item.get("evidence") or [], limit=3),
        }
        for item in canon_conflicts[:30]
    ]
    context = {
        "analysis_summary": {
            "analysis_id": snapshot.get("analysis_id"),
            "graph_version": snapshot.get("graph_version"),
            "scores": snapshot.get("scores") or {},
            "finding_counts": snapshot.get("finding_counts") or {},
            "stats": snapshot.get("stats") or {},
        },
        "deterministic_findings": findings,
        "finding_coverage": {
            "included": len(findings),
            "available": len(deterministic_findings),
            "selection": "highest severity first",
        },
        "recent_chapters": recent_chapters,
        "long_range_obligations": obligations,
        "active_canon_conflicts": conflicts,
    }

    # Pathological evidence strings must never make a whole-novel review fail.
    while len(json.dumps(context, default=str, ensure_ascii=True)) > AUDIT_CONTEXT_BUDGET:
        if len(context["deterministic_findings"]) > 4:
            context["deterministic_findings"].pop()
            context["finding_coverage"]["included"] = len(context["deterministic_findings"])
        elif len(context["recent_chapters"]) > 1:
            context["recent_chapters"].pop(0)
        elif len(context["long_range_obligations"]) > 1:
            context["long_range_obligations"].pop()
        elif len(context["active_canon_conflicts"]) > 1:
            context["active_canon_conflicts"].pop()
        else:
            break
    return context


def _finding(
    category: str,
    message: str,
    *,
    severity: str = "warning",
    subject_type: str = "project",
    subject_id: str = "",
    evidence: Iterable[str] = (),
) -> Dict[str, Any]:
    return {
        "finding_id": str(uuid4()),
        "category": category,
        "severity": severity,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "message": message,
        "evidence": list(evidence),
    }


class StoryAuditorService:
    async def deterministic_findings(
        self, db, project_id: str
    ) -> list[Dict[str, Any]]:
        # Phase 6: deterministic review consumes the shared analysis graph. The
        # compatibility shape below keeps existing reports and clients stable.
        platform = await narrative_analysis_engine.analyze(db, project_id)
        return [
            {
                "finding_id": item["finding_id"],
                "category": item["category"],
                "severity": item["severity"],
                "subject_type": item["domain"],
                "subject_id": (item.get("affected_elements") or [""])[0],
                "message": item["explanation"],
                "evidence": [str(value) for value in item.get("evidence") or []],
                "affected_chapters": item.get("affected_chapters") or [],
                "affected_scenes": item.get("affected_scenes") or [],
                "recommended_actions": item.get("recommended_actions") or [],
                "confidence": item.get("confidence"),
            }
            for item in platform["findings"]
        ]

    async def _legacy_deterministic_findings(
        self, db, project_id: str
    ) -> list[Dict[str, Any]]:
        pid = ObjectId(project_id)
        chapters = await db.chapter_intelligence.find(
            {"project_id": pid, "active": True}
        ).sort("chapter_number", 1).to_list(length=10000)
        findings: list[Dict[str, Any]] = []
        latest_number = max(
            [int(item.get("chapter_number") or 0) for item in chapters] or [0]
        )

        mysteries = await db.mystery_registry.find(
            {"project_id": pid}
        ).to_list(length=5000)
        for mystery in mysteries:
            status = str(mystery.get("status") or "open").lower()
            if status not in {"resolved", "closed", "paid_off"}:
                findings.append(
                    _finding(
                        "unresolved_mystery",
                        str(mystery.get("question") or "Mystery remains unresolved"),
                        subject_type="mystery",
                        subject_id=str(
                            mystery.get("mystery_id") or mystery.get("_id")
                        ),
                        evidence=[
                            str(mystery.get("reveal_target") or "No reveal target")
                        ],
                    )
                )

        threads = await db.plot_threads.find(
            {"project_id": pid, "status": {"$nin": ["resolved", "closed"]}}
        ).to_list(length=5000)
        recent_text = " ".join(
            str(value)
            for chapter in chapters[-10:]
            for value in [
                chapter.get("chapter_summary"),
                *chapter.get("important_events", []),
                *chapter.get("future_obligations", []),
            ]
            if value
        ).lower()
        for thread in threads:
            title = str(thread.get("title") or "")
            if title and title.lower() not in recent_text:
                findings.append(
                    _finding(
                        "abandoned_plot_thread",
                        f"Open plot thread has no signal in the last ten chapters: {title}",
                        subject_type="plot_thread",
                        subject_id=str(thread.get("_id")),
                    )
                )

        artifacts = await db.artifact_registry.find(
            {
                "project_id": pid,
                "status": {"$nin": ["resolved", "destroyed", "archived"]},
            }
        ).to_list(length=5000)
        recent_artifact_ids = {
            str(item.get("artifact_id"))
            for chapter in chapters[-10:]
            for item in chapter.get("artifact_usage", [])
        }
        for artifact in artifacts:
            artifact_id = str(artifact.get("artifact_id") or artifact.get("_id"))
            if artifact_id not in recent_artifact_ids:
                findings.append(
                    _finding(
                        "abandoned_artifact",
                        f"Active artifact is absent from the last ten chapters: {artifact.get('name') or artifact.get('item') or artifact_id}",
                        subject_type="artifact",
                        subject_id=artifact_id,
                    )
                )

        foreshadow = await db.foreshadow_registry_v2.find(
            {
                "project_id": pid,
                "status": {"$nin": ["resolved", "paid_off"]},
            }
        ).to_list(length=5000)
        recent_foreshadow_ids = {
            str(item.get("entry_id"))
            for chapter in chapters[-10:]
            for key in (
                "foreshadowing_introduced",
                "foreshadowing_advanced",
                "foreshadowing_resolved",
            )
            for item in chapter.get(key, [])
        }
        for item in foreshadow:
            entry_id = str(item.get("entry_id") or item.get("_id"))
            if entry_id not in recent_foreshadow_ids:
                findings.append(
                    _finding(
                        "abandoned_foreshadowing",
                        f"Foreshadowing seed has not advanced recently: {item.get('seed') or entry_id}",
                        subject_type="foreshadowing",
                        subject_id=entry_id,
                    )
                )

        characters = await db.character_bibles.find(
            {
                "project_id": pid,
                "current_status": {"$nin": ["dead", "departed", "archived"]},
            }
        ).to_list(length=5000)
        recent_characters = {
            str(value).lower()
            for chapter in chapters[-10:]
            for value in chapter.get("characters_present", [])
        }
        for character in characters:
            name = str(character.get("name") or "")
            if name and name.lower() not in recent_characters:
                findings.append(
                    _finding(
                        "forgotten_character",
                        f"Active character is absent from the last ten chapters: {name}",
                        subject_type="character",
                        subject_id=name,
                    )
                )

        relationships = await db.relationship_graphs.find(
            {"project_id": pid}
        ).to_list(length=5000)
        recent_relationship_ids = {
            str(item.get("relationship_id"))
            for chapter in chapters[-12:]
            for item in chapter.get("relationship_changes", [])
        }
        for relationship in relationships:
            relationship_id = str(
                relationship.get("relationship_id") or relationship.get("_id")
            )
            if relationship_id not in recent_relationship_ids:
                findings.append(
                    _finding(
                        "forgotten_relationship",
                        (
                            f"Tracked relationship has no recent movement: "
                            f"{relationship.get('character_a')} / {relationship.get('character_b')}"
                        ),
                        subject_type="relationship",
                        subject_id=relationship_id,
                        severity="info",
                    )
                )

        for chapter in chapters:
            chapter_number = int(chapter.get("chapter_number") or 0)
            for obligation in chapter.get("future_obligations", []):
                resolved_later = any(
                    str(obligation).lower()
                    in " ".join(
                        str(value)
                        for key in (
                            "important_events",
                            "mysteries_resolved",
                            "foreshadowing_resolved",
                        )
                        for value in later.get(key, [])
                    ).lower()
                    for later in chapters
                    if int(later.get("chapter_number") or 0) > chapter_number
                )
                if not resolved_later and latest_number - chapter_number >= 8:
                    findings.append(
                        _finding(
                            "unresolved_promise",
                            f"Obligation from chapter {chapter_number} remains open: {obligation}",
                            subject_type="chapter",
                            subject_id=str(chapter.get("chapter_plan_id") or ""),
                            evidence=[f"origin_chapter={chapter_number}"],
                        )
                    )

        for start in range(max(0, len(chapters) - 20)):
            window = chapters[start : start + 3]
            if len(window) < 3:
                continue
            if all(
                len(item.get("important_events") or []) <= 1
                and not item.get("character_changes")
                and not item.get("knowledge_revealed")
                for item in window
            ):
                findings.append(
                    _finding(
                        "pacing_dead_zone",
                        (
                            "Three consecutive chapters contain little event, "
                            "character, or knowledge movement."
                        ),
                        subject_type="chapter_range",
                        subject_id=(
                            f"{window[0].get('chapter_number')}-"
                            f"{window[-1].get('chapter_number')}"
                        ),
                    )
                )

        findings.extend(story_quality_service.compare_chapters(chapters))
        for chapter in chapters:
            for item in chapter.get("quality_findings", []):
                findings.append(
                    {
                        **item,
                        "finding_id": str(uuid4()),
                        "subject_type": "chapter",
                        "subject_id": str(
                            chapter.get("chapter_plan_id") or ""
                        ),
                    }
                )

        conflicts = await db.canon_conflicts.find(
            {
                "project_id": pid,
                "status": {"$in": ["open", "acknowledged"]},
            }
        ).to_list(length=5000)
        for conflict in conflicts:
            findings.append(
                _finding(
                    "canon_drift",
                    str(conflict.get("message") or "Open canon conflict"),
                    severity=str(conflict.get("severity") or "high"),
                    subject_type="canon",
                    subject_id=str(conflict.get("conflict_id") or ""),
                )
            )

        continuity = await db.continuity_reports.find(
            {
                "project_id": pid,
                "result": {"$in": ["WARNING", "FAIL"]},
            }
        ).sort("created_at", -1).to_list(length=5000)
        for report in continuity:
            findings.append(
                _finding(
                    "narrative_contradiction",
                    (
                        f"{report.get('result')} continuity report remains open "
                        f"for {report.get('subject_id')}"
                    ),
                    severity=(
                        "high" if report.get("result") == "FAIL" else "warning"
                    ),
                    subject_type=str(report.get("subject_type") or "draft"),
                    subject_id=str(report.get("subject_id") or ""),
                )
            )
        return _unique_findings(findings)

    async def run(
        self,
        db,
        project_id: str,
        *,
        include_agent: bool = True,
    ) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        project = await db.projects.find_one({"_id": pid})
        if not project:
            raise ValueError("Project not found")
        deterministic = await self.deterministic_findings(db, project_id)
        agent_findings: list[Dict[str, Any]] = []
        metadata: Dict[str, Any] = {}
        if include_agent:
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
            analysis = await narrative_analysis_engine.platform(db, project_id)
            chapter_memory = await chapter_intelligence_service.memory_packet(
                db, project_id, recent_limit=10, obligation_limit=20
            )
            canon_conflicts = await db.canon_conflicts.find(
                    {
                        "project_id": pid,
                        "status": {"$in": ["open", "acknowledged"]},
                    },
                    {"_id": 0},
                ).to_list(length=500)
            state["story_audit_context"] = _compact_audit_context(
                analysis,
                chapter_memory,
                deterministic,
                canon_conflicts,
            )
            settings = await orchestration_engine.get_settings(db)
            plan = await orchestration_service_v2.create_explicit_plan(
                db,
                project_id=project_id,
                agent_name="StoryAuditorAgent",
                changed_entity="story:full-audit",
                affected_domain="story_audit",
                reason="Explicit read-only production story audit",
            )
            try:
                result = await narrative_studio_service.run(
                    db,
                    project_id=project_id,
                    state=state,
                    agent_names=["StoryAuditorAgent"],
                    plan_id=str(plan["_id"]),
                    max_agent_calls=1,
                    max_cycle_cost_usd=float(settings.max_cycle_cost_usd),
                )
                outputs = [
                    item
                    for item in state.get("cycle_outputs") or []
                    if item.get("agent_name") == "StoryAuditorAgent"
                ]
                raw = (
                    (outputs[-1].get("structured_output") or {}).get(
                        "story_audit"
                    )
                    if outputs
                    else {}
                ) or {}
                for item in raw.get("findings") or []:
                    if not isinstance(item, dict):
                        continue
                    agent_findings.append(
                        {
                            "finding_id": str(uuid4()),
                            "category": str(
                                item.get("category") or "agent_observation"
                            ),
                            "severity": str(
                                item.get("severity") or "warning"
                            ).lower(),
                            "subject_type": str(
                                item.get("subject_type") or "project"
                            ),
                            "subject_id": str(item.get("subject_id") or ""),
                            "message": str(
                                item.get("message")
                                or item.get("finding")
                                or ""
                            ),
                            "evidence": list(item.get("evidence") or []),
                            "affected_chapters": list(item.get("affected_chapters") or []),
                            "affected_scenes": list(item.get("affected_scenes") or []),
                            "affected_elements": list(item.get("affected_elements") or []),
                            "recommended_actions": list(item.get("recommended_actions") or []),
                        }
                    )
                await orchestration_service_v2.finalize_explicit_plan(
                    db,
                    plan_id=plan["_id"],
                    agent_name="StoryAuditorAgent",
                    status="completed",
                    actual_cost_usd=float(result.get("actual_cost_usd") or 0),
                )
                metadata["orchestration_plan_id"] = str(plan["_id"])
            except Exception as exc:
                await orchestration_service_v2.finalize_explicit_plan(
                    db,
                    plan_id=plan["_id"],
                    agent_name="StoryAuditorAgent",
                    status="failed",
                    error=str(exc),
                )
                raise

        findings = _unique_findings([*deterministic, *agent_findings])
        severities = [
            str(item.get("severity") or "warning").lower() for item in findings
        ]
        result = (
            "FAIL"
            if any(value in {"critical", "error", "high"} for value in severities)
            else "WARNING"
            if findings
            else "PASS"
        )
        now = datetime.utcnow()
        report = {
            "project_id": pid,
            "report_id": str(uuid4()),
            "result": result,
            "findings": findings,
            "finding_counts": {
                category: sum(
                    1
                    for item in findings
                    if item.get("category") == category
                )
                for category in sorted(
                    {str(item.get("category")) for item in findings}
                )
            },
            "deterministic_finding_count": len(deterministic),
            "agent_finding_count": len(agent_findings),
            "generated_by": (
                ["deterministic", "StoryAuditorAgent"]
                if include_agent
                else ["deterministic"]
            ),
            "generation_metadata": metadata,
            "created_at": now,
        }
        inserted = await db.story_audit_reports.insert_one(report)
        report["_id"] = inserted.inserted_id
        bible = await rebuild_story_bible(db, project_id)
        await emit_project_event(
            db,
            project_id,
            "story_audit_completed",
            cycle_number=int(bible.get("cycle_number") or 0),
            payload={
                "report_id": report["report_id"],
                "result": result,
                "finding_count": len(findings),
                "story_bible_version": bible.get("version"),
            },
        )
        return _serialize(report)


story_auditor_service = StoryAuditorService()
