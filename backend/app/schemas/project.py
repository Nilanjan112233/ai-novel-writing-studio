from pydantic import BaseModel, ConfigDict, Field, model_validator
from datetime import datetime
from typing import Optional, List


class ProjectCreate(BaseModel):
    title: str = ""
    project_name: Optional[str] = None
    story_title: Optional[str] = None
    premise: str = ""
    idea_dump: str = ""
    genre: str = ""
    tone: str = ""
    themes: List[str] = Field(default_factory=list)
    inspirations: List[str] = Field(default_factory=list)
    character_notes: Optional[str] = None
    world_notes: Optional[str] = None
    plot_notes: Optional[str] = None
    notes: Optional[str] = None
    target_length: Optional[str] = None
    audience: Optional[str] = None
    narrative_goals: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_identity(self) -> "ProjectCreate":
        self.project_name = (self.project_name or self.title or "Untitled project").strip()
        self.title = self.project_name
        self.story_title = (self.story_title or "").strip() or None
        return self


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    project_name: Optional[str] = None
    story_title: Optional[str] = None
    premise: Optional[str] = None
    idea_dump: Optional[str] = None
    genre: Optional[str] = None
    tone: Optional[str] = None
    themes: Optional[List[str]] = None
    inspirations: Optional[List[str]] = None
    character_notes: Optional[str] = None
    world_notes: Optional[str] = None
    plot_notes: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    target_length: Optional[str] = None
    audience: Optional[str] = None
    narrative_goals: Optional[List[str]] = None


class ProjectResponse(BaseModel):
    id: str
    title: str
    project_name: str = "Untitled project"
    story_title: Optional[str] = None
    premise: str
    idea_dump: str
    genre: str
    tone: str
    themes: List[str]
    inspirations: List[str]
    character_notes: Optional[str]
    world_notes: Optional[str]
    plot_notes: Optional[str]
    notes: Optional[str]
    status: str
    target_length: Optional[str] = None
    audience: Optional[str] = None
    narrative_goals: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None
    trashed_at: Optional[datetime] = None
    duplicated_from_project_id: Optional[str] = None
    app_version: Optional[str] = None
    schema_version: Optional[int] = None
    restored_from_backup_id: Optional[str] = None
    restored_from_project_id: Optional[str] = None
    planning_reconsideration: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    status: str
    current_agent: str
    started_at: datetime
    finished_at: Optional[datetime]
    cycle_number: int = 0
    metadata: dict = Field(default_factory=dict)
    error: Optional[str] = None
    error_code: Optional[str] = None

class AgentOutputResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    run_id: str
    agent_name: str
    content: str
    metadata: dict
    created_at: datetime

class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    text: str
    choices: List[str]
    answered: bool
    answer: Optional[str]
    cycle_number: int = 0
    default_recommendation: Optional[str] = None
    story_area: Optional[str] = None
    blocking: bool = False
    created_at: datetime

class AnswerSubmit(BaseModel):
    question_id: str
    answer: str


class OutlineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    premise: str
    themes: List[str]
    acts: List[dict]
    chapters: List[dict]
    created_at: datetime
    updated_at: datetime

class CharacterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    name: str
    role: str
    description: str
    traits: List[str]
    created_at: datetime

class WorldBibleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    setting: str
    rules: List[str]
    lore: List[str]
    created_at: datetime
    updated_at: datetime

class TimelineMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    cycle_number: int
    role: str
    agent_name: Optional[str] = None
    message_type: str
    content: str
    created_at: datetime
    
class CycleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    cycle_number: int
    trigger_message_ids: List[str]
    agents_run: List[str]
    started_at: datetime
    finished_at: Optional[datetime]
    status: str
    
class MessageCreateRequest(BaseModel):
    content: str


class DeleteProjectResponse(BaseModel):
    message: str
    recoverable: bool = True
    deleted_counts: dict = Field(default_factory=dict)


class ProjectPurgeRequest(BaseModel):
    confirmation_title: str = Field(min_length=1)
