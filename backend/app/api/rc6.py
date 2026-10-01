"""RC6 commercial experience endpoints over stable NovelForge services."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query

from app.core.database import Database
from app.schemas.rc6 import (
    BeginnerFlowResponse,
    BeginnerStepUpdateRequest,
    DecisionActionRequest,
    DecisionChangeRequest,
    DecisionHistoryResponse,
    DecisionResponse,
    FavoriteProjectRequest,
    ProjectLibraryResponse,
    WorkspaceBootstrapResponse,
    WorkspaceEntryRequest,
    WorkspaceEntryResponse,
)
from app.services.beginner_experience_service import beginner_experience_service
from app.services.decision_history_service import decision_history_service
from app.services.project_library_service import project_library_service
from app.services.workspace_bootstrap_service import workspace_bootstrap_service
from app.services.workspace_entry_service import workspace_entry_service


router = APIRouter(prefix="/api/projects/{project_id}", tags=["rc6-experience"])
library_router = APIRouter(prefix="/api/project-library", tags=["rc6-project-library"])


def _error(exc: ValueError) -> HTTPException:
    message = str(exc.args[0] if exc.args else exc)
    if "not found" in message.lower():
        return HTTPException(status_code=404, detail=message)
    return HTTPException(status_code=409, detail=message)


@router.get("/beginner-flow", response_model=BeginnerFlowResponse)
async def beginner_flow(project_id: str):
    try:
        return await beginner_experience_service.get(Database.get_db(), project_id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.put("/beginner-flow/{step_id}", response_model=BeginnerFlowResponse)
async def update_beginner_step(
    project_id: str,
    step_id: str,
    payload: BeginnerStepUpdateRequest,
):
    try:
        return await beginner_experience_service.update(
            Database.get_db(),
            project_id,
            step_id,
            action=payload.action,
            title=payload.title,
            details=payload.details,
            source_mode=payload.source_mode,
        )
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/workspace-entries", response_model=WorkspaceEntryResponse)
async def create_workspace_entry(project_id: str, payload: WorkspaceEntryRequest):
    try:
        return await workspace_entry_service.create(
            Database.get_db(),
            project_id,
            area=payload.area,
            title=payload.title.strip(),
            details=payload.details.strip(),
            source_mode=payload.source_mode,
        )
    except ValueError as exc:
        raise _error(exc) from exc


@router.get("/decisions", response_model=DecisionHistoryResponse)
async def decision_history(project_id: str):
    try:
        return await decision_history_service.list(Database.get_db(), project_id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.get("/decisions/{question_id}/impact", response_model=DecisionResponse)
async def decision_impact(project_id: str, question_id: str):
    try:
        return await decision_history_service.preview(Database.get_db(), project_id, question_id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.put("/decisions/{question_id}", response_model=DecisionResponse)
async def change_decision(project_id: str, question_id: str, payload: DecisionChangeRequest):
    try:
        return await decision_history_service.change(
            Database.get_db(),
            project_id,
            question_id,
            answer=payload.answer,
            reason=payload.reason,
        )
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/decisions/{question_id}/undo", response_model=DecisionResponse)
async def undo_decision(project_id: str, question_id: str, payload: DecisionActionRequest):
    try:
        return await decision_history_service.undo(
            Database.get_db(), project_id, question_id, reason=payload.reason
        )
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/decisions/{question_id}/reopen", response_model=DecisionResponse)
async def reopen_decision(project_id: str, question_id: str, payload: DecisionActionRequest):
    try:
        return await decision_history_service.reopen(
            Database.get_db(), project_id, question_id, reason=payload.reason
        )
    except ValueError as exc:
        raise _error(exc) from exc


@router.get("/workspace-bootstrap", response_model=WorkspaceBootstrapResponse)
async def workspace_bootstrap(project_id: str):
    try:
        return await workspace_bootstrap_service.get(Database.get_db(), project_id)
    except ValueError as exc:
        raise _error(exc) from exc


@library_router.get("", response_model=ProjectLibraryResponse)
async def project_library(
    status: str = Query(default="active", pattern="^(active|archived|trashed|all)$"),
    search: str = Query(default="", max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=6, le=100),
    favorites_only: bool = Query(default=False),
):
    return await project_library_service.page(
        Database.get_db(),
        status=status,
        search=search,
        page=page,
        page_size=page_size,
        favorites_only=favorites_only,
    )


@library_router.put("/{project_id}/favorite", response_model=Dict[str, Any])
async def favorite_project(project_id: str, payload: FavoriteProjectRequest):
    try:
        return await project_library_service.set_favorite(
            Database.get_db(), project_id, payload.favorite
        )
    except ValueError as exc:
        raise _error(exc) from exc


@library_router.post("/{project_id}/touch", response_model=Dict[str, Any])
async def touch_project(project_id: str):
    try:
        return await project_library_service.touch(Database.get_db(), project_id)
    except ValueError as exc:
        raise _error(exc) from exc
