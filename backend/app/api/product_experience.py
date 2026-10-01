"""Cohesive product-experience projections over NovelForge's existing intelligence."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId

from app.core.database import Database
from app.services.canon_governance_service import CANON_TYPES, canon_governance_service
from app.services.application_knowledge_service import application_knowledge_service
from app.services.narrative_completeness_service import narrative_completeness_service
from app.services.narrative_critique_service import narrative_critique_service
from app.services.shared_narrative_context_service import shared_narrative_context_service
from app.services.workspace_companion_service import workspace_companion_service
from app.services.story_bible_service import rebuild_story_bible
from app.services.project_event_service import emit_project_event
from app.services.project_evolution_service import project_evolution_service
from app.services.memory_provider import memory_provider_service
from app.api.data import serialize_doc


router = APIRouter(prefix="/api/projects/{project_id}", tags=["product-experience"])


@router.get("/memory/providers/status")
async def memory_provider_status(project_id: str):
    return await memory_provider_service.status(Database.get_db())


@router.get("/memory/providers/recall")
async def memory_provider_recall(
    project_id: str,
    q: str = Query(min_length=1, max_length=4000),
    top_k: int = Query(default=8, ge=1, le=50),
    mode: str | None = Query(default=None),
):
    try:
        return await memory_provider_service.recall(
            Database.get_db(), project_id, q, top_k=top_k, mode=mode,
        )
    except (TypeError, ValueError) as exc:
        raise _conflict(exc) from exc


@router.post("/memory/providers/compare")
async def memory_provider_compare(project_id: str, payload: Dict[str, Any]):
    query = str(payload.get("query") or payload.get("q") or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    return await memory_provider_service.compare(
        Database.get_db(), project_id, query,
        top_k=int(payload.get("top_k") or 8),
    )


@router.post("/memory/providers/smoke-test")
async def memory_provider_smoke_test(project_id: str):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    return await memory_provider_service.smoke_test(Database.get_db(), project_id)


@router.get("/memory/providers/events")
async def memory_provider_events(
    project_id: str,
    limit: int = Query(default=100, ge=1, le=500),
):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    rows = await Database.get_db().memory_provider_events.find(
        {"project_id": ObjectId(project_id)}
    ).sort("created_at", -1).to_list(length=limit)
    return [serialize_doc(row) for row in rows]


@router.get("/memory/providers/comparisons")
async def memory_provider_comparisons(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=200),
):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    rows = await Database.get_db().memory_provider_comparisons.find(
        {"project_id": ObjectId(project_id)}
    ).sort("created_at", -1).to_list(length=limit)
    return [serialize_doc(row) for row in rows]


def _conflict(exc: ValueError) -> HTTPException:
    message = exc.args[0] if exc.args else str(exc)
    status = 404 if "not found" in str(message).lower() else 409
    return HTTPException(status_code=status, detail=message)


@router.get("/application-knowledge")
async def application_knowledge(project_id: str):
    try:
        await narrative_completeness_service.calculate(Database.get_db(), project_id, persist=False)
        return application_knowledge_service.catalog()
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/application-knowledge/{surface_id}")
async def application_surface(project_id: str, surface_id: str):
    try:
        await narrative_completeness_service.calculate(Database.get_db(), project_id, persist=False)
        return application_knowledge_service.surface(surface_id)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/project-timeline")
async def project_timeline(project_id: str, limit: int = Query(default=300, ge=1, le=1000)):
    try:
        return await project_evolution_service.timeline(Database.get_db(), project_id, limit)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/explainability-timeline")
async def explainability_timeline(project_id: str, limit: int = Query(default=100, ge=1, le=500)):
    try:
        return await project_evolution_service.explainability(Database.get_db(), project_id, limit)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/narrative-critique")
async def get_narrative_critique(project_id: str):
    try:
        return await narrative_critique_service.get(Database.get_db(), project_id)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/narrative-critique/refresh")
async def refresh_narrative_critique(project_id: str, payload: dict | None = None):
    try:
        return await narrative_critique_service.refresh(
            Database.get_db(), project_id,
            include_latest_agent_audit=bool((payload or {}).get("include_latest_agent_audit", True)),
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/narrative-completeness")
async def narrative_completeness(project_id: str):
    try:
        return await narrative_completeness_service.calculate(Database.get_db(), project_id)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/production-milestones")
async def production_milestones(project_id: str):
    try:
        result = await narrative_completeness_service.calculate(Database.get_db(), project_id)
        return {key: result[key] for key in ("project_id", "overall_completion", "current_milestone", "milestones", "next_actions", "calculated_at")}
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/shared-narrative-context")
async def list_shared_context(
    project_id: str,
    domain: str | None = Query(default=None),
    active: bool | None = Query(default=True),
    limit: int = Query(default=500, ge=1, le=5000),
):
    try:
        return await shared_narrative_context_service.list(Database.get_db(), project_id, domain=domain, active=active, limit=limit)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/shared-narrative-context")
async def add_shared_context(project_id: str, payload: Dict[str, Any]):
    try:
        result = await shared_narrative_context_service.ingest(
            Database.get_db(), project_id,
            content=str(payload.get("content") or payload.get("value") or ""),
            source_type=str(payload.get("source_type") or "explicit_author_input"),
            source_id=str(payload.get("source_id") or ""),
            source_excerpt=str(payload.get("source_excerpt") or "") or None,
            structured=payload,
        )
        if result.get("persisted"):
            bible = await rebuild_story_bible(Database.get_db(), project_id)
            await emit_project_event(
                Database.get_db(), project_id, "shared_narrative_context_updated",
                payload={"context_id": (result.get("entry") or {}).get("context_id"), "story_bible_version": bible.get("version")},
            )
        return result
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.put("/shared-narrative-context/{context_id}/active")
async def set_shared_context_active(project_id: str, context_id: str, payload: Dict[str, Any]):
    try:
        result = await shared_narrative_context_service.set_active(
            Database.get_db(), project_id, context_id, bool(payload.get("active")),
        )
        bible = await rebuild_story_bible(Database.get_db(), project_id)
        await emit_project_event(
            Database.get_db(), project_id, "shared_narrative_context_updated",
            payload={"context_id": context_id, "active": result.get("active"), "story_bible_version": bible.get("version")},
        )
        return result
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/canon-explorer")
async def canon_explorer(
    project_id: str,
    search: str = Query(default="", max_length=200),
    canon_type: str = Query(default=""),
    active: bool | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=10000),
):
    if canon_type and canon_type not in CANON_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported canon type")
    try:
        return await canon_governance_service.explorer(
            Database.get_db(), project_id, search=search, canon_type=canon_type, active=active, limit=limit,
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/canon-explorer/{canon_id}")
async def canon_detail(project_id: str, canon_id: str):
    try:
        return await canon_governance_service.record_detail(Database.get_db(), project_id, canon_id)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/canon-explorer/{canon_id}/propose-edit")
async def propose_canon_edit(project_id: str, canon_id: str, payload: Dict[str, Any]):
    try:
        return await canon_governance_service.propose_edit(Database.get_db(), project_id, canon_id, payload)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/canon-explorer/compare/{left_id}/{right_id}")
async def compare_canon(project_id: str, left_id: str, right_id: str):
    try:
        return await canon_governance_service.compare(Database.get_db(), project_id, left_id, right_id)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.get("/workspace-companion")
async def workspace_companion(
    project_id: str,
    active_surface: str = Query(default=""),
):
    try:
        return await workspace_companion_service.refresh(
            Database.get_db(),
            project_id,
            active_surface=active_surface,
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.put("/workspace-companion/messages/{message_id}")
async def update_companion_message(project_id: str, message_id: str, payload: Dict[str, Any]):
    try:
        return await workspace_companion_service.set_message_state(
            Database.get_db(), project_id, message_id, read=payload.get("read"),
            dismissed=payload.get("dismissed"), completed=payload.get("completed"),
            snooze_hours=payload.get("snooze_hours"),
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/workspace-companion/read")
async def mark_companion_feed_read(project_id: str):
    try:
        return await workspace_companion_service.mark_feed_read(
            Database.get_db(), project_id
        )
    except ValueError as exc:
        raise _conflict(exc) from exc


GUIDE_STEPS = [
    ("project", "Project creation", "Capture the project identity and initial story promise.", "dashboard", ["Project Assistant"]),
    ("vision", "Story vision", "Align the premise, audience, and narrative goals.", "vision", ["Story Coach"]),
    ("genre", "Genre", "Set the story conventions and reader expectations the novel will use or challenge.", "vision", ["Story Coach", "Developmental Editor"]),
    ("theme", "Theme", "Define the ideas and questions that should gain meaning across the novel.", "vision", ["Story Coach", "AI Narrative Reviewer"]),
    ("characters", "Characters", "Define the people whose wants and choices drive the novel.", "characters", ["Character Intelligence", "Character Interviewer"]),
    ("world", "Worldbuilding", "Establish locations, cultures, factions, and governing constraints.", "world", ["Worldbuilding Consultant"]),
    ("power", "Power system", "Define capabilities, costs, limits, or mark the system not applicable.", "power", ["Canon Intelligence"]),
    ("relationships", "Relationships", "Make interpersonal bonds, tensions, and evolution explicit.", "relationships", ["Character Intelligence", "Knowledge Graph"]),
    ("timeline", "Timeline", "Anchor major events and validate chronology and travel.", "timeline", ["Timeline Intelligence"]),
    ("arcs", "Arcs", "Shape goals, escalation, reversals, and intended payoffs.", "arc-development", ["Developmental Editor", "Plot Thread Intelligence"]),
    ("scene-planning", "Scene planning", "Give each scene purpose, conflict, change, and outcome.", "drafting", ["Story Coach"]),
    ("drafting", "Paragraph drafting", "Write the planned scenes while preserving approved context.", "drafting", ["Writing Assistant"]),
    ("revision", "Revision", "Use evidence-backed critique without surrendering author control.", "editorial", ["Developmental Editor", "Dialogue Coach"]),
    ("health", "Story Health", "Resolve the highest-impact structural and continuity risks.", "story-health", ["Narrative Analysis Engine"]),
    ("canon", "Canon review", "Approve, reject, compare, or deactivate official facts transparently.", "canon", ["Canon Intelligence"]),
    ("publication", "Publication readiness", "Pass explicit Revision and Publication Ready gates.", "readiness", ["AI Narrative Reviewer"]),
]


@router.get("/novel-creation-guide")
async def novel_creation_guide(project_id: str):
    try:
        completeness = await narrative_completeness_service.calculate(Database.get_db(), project_id)
    except ValueError as exc:
        raise _conflict(exc) from exc
    dimensions = completeness.get("dimensions") or {}
    story_criteria = {
        item.get("criterion_id"): item
        for item in dimensions.get("story", {}).get("criteria", [])
    }
    target_scores = {
        "vision": dimensions.get("story", {}).get("score", 0), "characters": dimensions.get("character", {}).get("score", 0),
        "genre": 100 if story_criteria.get("story.genre", {}).get("complete") else 0,
        "theme": 100 if story_criteria.get("story.themes", {}).get("complete") else 0,
        "world": dimensions.get("world", {}).get("score", 0), "power": dimensions.get("power", {}).get("score", 0),
        "relationships": dimensions.get("relationship", {}).get("score", 0), "timeline": dimensions.get("timeline", {}).get("score", 0),
        "health": min(100, round(sum(item.get("score", 0) for item in dimensions.values()) / max(1, len(dimensions)))),
        "canon": dimensions.get("canon", {}).get("score", 0), "publication": 100 if any(item.get("gate_id") == "publication_ready" and item.get("achieved") for item in completeness.get("milestones") or []) else 0,
    }
    steps = [
        {"step_id": step_id, "label": label, "why_it_matters": why, "target": target,
         "ai_systems": systems, "completion": target_scores.get(step_id, 100 if step_id == "project" else 0),
         "required_information": [item.get("label") for item in completeness.get("remaining_work") or [] if item.get("target") == target][:5],
         "optional_improvements": [item.get("suggested_improvement") for item in completeness.get("remaining_work") or [] if item.get("target") == target and not item.get("required")][:3]}
        for step_id, label, why, target, systems in GUIDE_STEPS
    ]
    return {"steps": steps, "jump_freely": True, "milestones": completeness.get("milestones"),
            "current_milestone": completeness.get("current_milestone"), "next_actions": completeness.get("next_actions")}
