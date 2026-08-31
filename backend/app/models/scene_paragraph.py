from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field


class ParagraphDependencies(BaseModel):
    canon_facts: List[str] = Field(default_factory=list)
    characters: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    relationships: List[str] = Field(default_factory=list)
    mysteries: List[str] = Field(default_factory=list)
    callbacks: List[str] = Field(default_factory=list)


class PipelineStageMetadata(BaseModel):
    status: str = "planned"  # planned, generating, expanded, approved, etc.
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    provider: Optional[str] = None
    model: Optional[str] = None
    token_usage: int = 0
    estimated_cost: float = 0.0
    retry_count: int = 0
    notes: List[str] = Field(default_factory=list)


class ValidationDomainResult(BaseModel):
    valid: bool = True
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validated_at: datetime = Field(default_factory=datetime.utcnow)


class ParagraphSkeleton(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    project_id: str  # Hex string for ObjectId
    scene_id: str
    paragraph_id: str = Field(default_factory=lambda: str(uuid4()))
    order: int
    purpose: str
    narrative_goal: str
    scene_goal: str
    emotion: str
    tension_level: str  # String representation e.g. "5", "High", etc.
    pov: str
    location: str
    prose: str = ""
    dialogue_goal: str = ""
    exposition_goal: str = ""
    target_word_count: int = 250
    is_locked: bool = False
    approval_state: str = "pending"  # pending, approved, rejected
    version: int = 1
    regeneration_count: int = 0
    dependencies: ParagraphDependencies = Field(default_factory=ParagraphDependencies)
    processing_pipeline: Dict[str, PipelineStageMetadata] = Field(default_factory=dict)
    validation_domains: Dict[str, ValidationDomainResult] = Field(default_factory=dict)
    comments: List[Dict[str, Any]] = Field(default_factory=list)
    revision_notes: List[Dict[str, Any]] = Field(default_factory=list)
    branch_id: Optional[str] = None
    parent_version_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ParagraphVersion(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    version_id: str = Field(default_factory=lambda: str(uuid4()))
    paragraph_id: str
    version_number: int
    snapshot: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = "system"
    generation_metadata: Optional[Dict[str, Any]] = None
    change_reason: str = ""

class ParagraphSuggestion(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    suggestion_id: str = Field(default_factory=lambda: str(uuid4()))
    paragraph_id: str
    suggestion_type: str  # rewrite, expand, tone, shorten, etc.
    provider: str
    model: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "pending"  # pending, accepted, rejected
    proposed_prose: str
    generation_metadata: Optional[Dict[str, Any]] = None

