from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class BeginnerStepUpdateRequest(BaseModel):
    action: Literal["save", "skip", "reopen"]
    title: str = ""
    details: str = ""
    source_mode: Literal["manual", "ai", "import"] = "manual"


class BeginnerStepResponse(BaseModel):
    step_id: str
    order: int
    label: str
    description: str
    target: str
    status: Literal["not_started", "in_progress", "completed", "skipped"]
    title: str = ""
    details: str = ""
    can_skip: bool = True
    can_edit: bool = True
    ai_prompt: str
    completed_at: Optional[datetime] = None


class BeginnerFlowResponse(BaseModel):
    project_id: str
    current_step: str
    completed_steps: int
    total_steps: int
    completion: int
    first_scene_ready: bool
    steps: List[BeginnerStepResponse]
    next_action: Dict[str, Any]


class WorkspaceEntryRequest(BaseModel):
    area: Literal[
        "character",
        "world",
        "timeline",
        "power",
        "relationship",
        "theme",
        "plot_thread",
        "arc",
        "mystery",
        "faction",
        "scene",
    ]
    title: str = Field(min_length=1, max_length=160)
    details: str = Field(default="", max_length=12000)
    source_mode: Literal["manual", "ai", "import"] = "manual"


class WorkspaceEntryResponse(BaseModel):
    area: str
    record_id: str
    target: str
    story_bible_version: int
    message: str


class DecisionChangeRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=12000)
    reason: str = Field(default="", max_length=1000)


class DecisionActionRequest(BaseModel):
    reason: str = Field(default="", max_length=1000)


class DecisionHistoryItem(BaseModel):
    version: int
    answer: str
    action: str
    reason: str = ""
    created_at: datetime


class DecisionResponse(BaseModel):
    question_id: str
    question: str
    answered: bool
    current_answer: Optional[str] = None
    version: int
    history: List[DecisionHistoryItem]
    impact_preview: Dict[str, Any]
    can_change: bool = True
    can_undo: bool = False
    can_reopen: bool = True


class DecisionHistoryResponse(BaseModel):
    project_id: str
    decisions: List[DecisionResponse]


class ProjectLibraryItem(BaseModel):
    id: str
    title: str
    project_name: str = "Untitled project"
    story_title: Optional[str] = None
    status: str
    genre: str = ""
    tone: str = ""
    favorite: bool = False
    created_at: datetime
    updated_at: datetime
    last_opened_at: Optional[datetime] = None
    story_consistency: Optional[int] = None
    completeness: Optional[int] = None
    milestone: str = "Getting Started"


class ProjectLibraryResponse(BaseModel):
    items: List[ProjectLibraryItem]
    page: int
    page_size: int
    total: int
    pages: int
    has_next: bool
    counts: Dict[str, int]


class FavoriteProjectRequest(BaseModel):
    favorite: bool


class WorkspaceBootstrapResponse(BaseModel):
    project_id: str
    project: Dict[str, Any]
    story_bible: Dict[str, Any]
    story_health: Dict[str, Any]
    completeness: Dict[str, Any]
    companion: Dict[str, Any]
    version: str
    generated_at: datetime
    readiness: Dict[str, str] = Field(default_factory=dict)
    performance: Dict[str, int] = Field(default_factory=dict)
    cache: Dict[str, Any] = Field(default_factory=dict)
