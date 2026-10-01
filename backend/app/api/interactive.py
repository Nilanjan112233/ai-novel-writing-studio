"""Phase 7 Interactive Narrative Studio APIs."""
from __future__ import annotations

from typing import Any, Dict, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.database import Database
from app.services.narrative_interaction_service import (
    ASSISTANT_MODES,
    narrative_interaction_service,
)
from app.schemas.story_studio import StoryStudioRequest
from app.services.story_studio_service import story_studio_service


router = APIRouter(prefix="/api/projects/{project_id}", tags=["interactive-narrative"])


class AssistantRequest(BaseModel):
    query: str = Field(min_length=1, max_length=5000)
    mode: str = "story_coach"
    active_surface: str = Field(default="dashboard", max_length=100)
    intent: Literal["narrative_creation"] | None = None
    request_id: str | None = Field(default=None, max_length=200)


class CharacterConversationRequest(BaseModel):
    character_name: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=5000)
    chapter_number: int | None = Field(default=None, ge=0, le=100000)
    conversation_id: str | None = Field(default=None, max_length=100)


class CanonProposalRequest(BaseModel):
    canon_type: str = "world"
    subject: str = Field(min_length=1, max_length=300)
    field: str = Field(min_length=1, max_length=300)
    value: Any
    confidence: float = Field(default=0.5, ge=0, le=1)
    evidence: list[Any] = Field(default_factory=list, max_length=50)
    affected_chapters: list[int] = Field(default_factory=list, max_length=500)
    affected_scenes: list[str] = Field(default_factory=list, max_length=1000)


class ProposalDecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str = Field(default="", max_length=2000)
    confirm_high_impact: bool = False


class WorkspaceIntelligenceRequest(BaseModel):
    surface: str = Field(min_length=1, max_length=100)
    chapter_number: int | None = Field(default=None, ge=0, le=100000)
    scene_id: str | None = Field(default=None, max_length=300)
    character_name: str | None = Field(default=None, max_length=300)


def _error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=409, detail=str(exc))


@router.get("/interactive/modes")
async def assistant_modes(project_id: str):
    db = Database.get_db()
    try:
        await narrative_interaction_service._project(db, project_id)
        return [
            {"id": mode, "label": mode.replace("_", " ").title(), "description": description}
            for mode, description in ASSISTANT_MODES.items()
        ]
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/assistant")
async def ask_project_assistant(project_id: str, payload: AssistantRequest):
    db = Database.get_db()
    try:
        return await narrative_interaction_service.assistant(
            db,
            project_id,
            query=payload.query,
            mode=payload.mode,
            active_surface=payload.active_surface,
            intent=payload.intent,
            request_id=payload.request_id,
        )
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/story-studio")
async def story_studio_request(project_id: str, payload: StoryStudioRequest):
    db = Database.get_db()
    try:
        return await story_studio_service.request(db, project_id, payload)
    except ValueError as exc:
        raise _error(exc) from exc


@router.get("/story-studio/jobs")
async def story_studio_jobs(project_id: str, limit: int = Query(default=50, ge=1, le=200)):
    db = Database.get_db()
    try:
        await narrative_interaction_service._project(db, project_id)
        return await story_studio_service.jobs(db, project_id, limit)
    except ValueError as exc:
        raise _error(exc) from exc


@router.get("/assistant/history")
async def project_assistant_history(
    project_id: str, limit: int = Query(default=50, ge=1, le=200)
):
    db = Database.get_db()
    try:
        return await narrative_interaction_service.assistant_history(db, project_id, limit)
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/character-conversations")
async def converse_with_character(
    project_id: str, payload: CharacterConversationRequest
):
    db = Database.get_db()
    try:
        return await narrative_interaction_service.character_conversation(
            db,
            project_id,
            character_name=payload.character_name,
            message=payload.message,
            chapter_number=payload.chapter_number,
            conversation_id=payload.conversation_id,
        )
    except ValueError as exc:
        raise _error(exc) from exc


@router.get("/character-conversations/{character_name}")
async def character_conversation_history(
    project_id: str,
    character_name: str,
    limit: int = Query(default=100, ge=1, le=500),
):
    db = Database.get_db()
    try:
        return await narrative_interaction_service.character_history(
            db, project_id, character_name, limit
        )
    except ValueError as exc:
        raise _error(exc) from exc


@router.get("/knowledge-graph")
async def knowledge_graph(
    project_id: str,
    kind: list[str] | None = Query(default=None),
    search: str = Query(default="", max_length=300),
    limit: int = Query(default=1200, ge=1, le=5000),
):
    db = Database.get_db()
    try:
        return await narrative_interaction_service.knowledge_graph(
            db, project_id, kinds=kind, search=search, limit=limit
        )
    except ValueError as exc:
        raise _error(exc) from exc


@router.get("/knowledge-graph/nodes/{node_id}")
async def knowledge_graph_node(project_id: str, node_id: str):
    db = Database.get_db()
    try:
        return await narrative_interaction_service.graph_node(db, project_id, node_id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.get("/narrative-findings/{finding_id}/explanation")
async def explain_narrative_finding(project_id: str, finding_id: str):
    db = Database.get_db()
    try:
        return await narrative_interaction_service.explain_finding(
            db, project_id, finding_id
        )
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/workspace-intelligence")
async def workspace_intelligence(
    project_id: str, payload: WorkspaceIntelligenceRequest
):
    db = Database.get_db()
    try:
        return await narrative_interaction_service.workspace_intelligence(
            db,
            project_id,
            surface=payload.surface,
            chapter_number=payload.chapter_number,
            scene_id=payload.scene_id,
            character_name=payload.character_name,
        )
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/canon/proposals")
async def create_canon_proposal(project_id: str, payload: CanonProposalRequest):
    db = Database.get_db()
    try:
        return await narrative_interaction_service.create_canon_proposal(
            db,
            project_id,
            payload.model_dump(),
            source_type="manual",
            source_id="author",
        )
    except ValueError as exc:
        raise _error(exc) from exc


@router.get("/canon/proposals")
async def canon_proposal_queue(
    project_id: str,
    status: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
):
    db = Database.get_db()
    try:
        return await narrative_interaction_service.canon_proposals(
            db, project_id, status, limit
        )
    except ValueError as exc:
        raise _error(exc) from exc


@router.put("/canon/proposals/{proposal_id}")
async def review_canon_proposal(
    project_id: str, proposal_id: str, payload: ProposalDecisionRequest
):
    db = Database.get_db()
    try:
        return await narrative_interaction_service.review_canon_proposal(
            db,
            project_id,
            proposal_id,
            decision=payload.decision,
            note=payload.note,
            confirm_high_impact=payload.confirm_high_impact,
        )
    except ValueError as exc:
        raise _error(exc) from exc
