from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from bson import ObjectId


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


class Project(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    # ``title`` remains the legacy API alias for the internal project name.
    title: str = "Untitled project"
    project_name: Optional[str] = None
    story_title: Optional[str] = None
    premise: str = ""
    idea_dump: str = ""
    genre: str = ""
    tone: str = ""
    themes: List[str] = []
    inspirations: List[str] = []
    character_notes: Optional[str] = None
    world_notes: Optional[str] = None
    plot_notes: Optional[str] = None
    notes: Optional[str] = None
    target_length: Optional[str] = None
    audience: Optional[str] = None
    narrative_goals: List[str] = []
    status: str = "draft"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Run(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    project_id: PyObjectId
    status: str = "running"
    current_agent: str = ""
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class AgentOutput(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    run_id: PyObjectId
    agent_name: str
    content: str
    metadata: dict = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Question(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    project_id: PyObjectId
    text: str
    choices: List[str] = []
    answered: bool = False
    answer: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Outline(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    project_id: PyObjectId
    premise: str = ""
    themes: List[str] = []
    acts: List[dict] = []
    chapters: List[dict] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Character(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    project_id: PyObjectId
    name: str
    role: str = ""
    description: str = ""
    traits: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class WorldBible(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    project_id: PyObjectId
    setting: str = ""
    rules: List[str] = []
    lore: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class TimelineMessage(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    project_id: PyObjectId
    cycle_number: int = 1
    role: str  # "user" | "agent" | "system"
    agent_name: Optional[str] = None
    message_type: str = "idea"  # "idea" | "critique" | "question" | "summary"
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Cycle(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    project_id: PyObjectId
    cycle_number: int
    trigger_message_ids: List[PyObjectId] = []
    agents_run: List[str] = []
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    status: str = "running"  # "running" | "completed" | "failed"

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class CharacterBible(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    project_id: PyObjectId
    name: str
    aliases: List[str] = []
    role: Optional[str] = None
    goals: List[str] = []
    fears: List[str] = []
    flaws: List[str] = []
    personality_traits: List[str] = []
    arc_start: Optional[str] = None
    arc_end: Optional[str] = None
    current_arc_state: Optional[str] = None
    secrets: List[str] = []
    contradictions: List[str] = []
    relationships: List[dict] = []
    notes: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class PlotThread(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    project_id: PyObjectId
    title: str
    description: str
    introduced_in_cycle: int
    status: str
    related_characters: List[str] = []
    possible_resolutions: List[str] = []
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ContinuityReport(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    project_id: PyObjectId
    cycle_number: int
    issues: List[dict] = []
    severity: str
    recommendations: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ForeshadowEntry(BaseModel):
    setup: str
    expected_payoff: str
    resolved: bool = False


class SceneEntry(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    project_id: PyObjectId
    title: str
    summary: str
    characters_present: List[str] = []
    emotional_shift: str = ""
    purpose: str = ""
    foreshadowing: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
