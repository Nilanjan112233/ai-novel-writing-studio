"""Shared contracts for the conversational Story Studio and discovery writing.

These contracts deliberately separate an author's conversation from mutations to
authoritative story state.  A response may describe a proposed change, but only
an owning governed service may apply it.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StoryIntent(StrEnum):
    ANSWER = "answer"
    BRAINSTORM = "brainstorm"
    RETRIEVE_EXPLAIN = "retrieve_explain"
    DEVELOP = "develop"
    MODIFY = "modify"
    RECONSIDER = "reconsider"
    REVIEW = "review"
    WRITE = "write"
    NAVIGATE = "navigate"
    AUTHOR_DECISION_REQUIRED = "author_decision_required"


class MutationClass(StrEnum):
    NONE = "none"
    PROPOSAL = "proposal"
    EXPLICIT_MUTATION = "explicit_mutation"
    AMBIGUOUS = "ambiguous"


class StoryStudioRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    query: str = Field(min_length=1, max_length=8000)
    mode: str = Field(default="story_coach", max_length=100)
    active_surface: str = Field(default="story-studio", max_length=100)
    target: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = Field(default=None, max_length=200)
    allow_mutations: bool = False
    # Author-facing preference for the primary Story Studio response only.
    # Utility work such as extraction, validation, and routing remains task-aware.
    model_preference: str = Field(default="auto", max_length=300)
    model_scope: Literal["message", "conversation"] = "message"


class StoryStudioIntent(BaseModel):
    intent: StoryIntent
    mutation_class: MutationClass = MutationClass.NONE
    confidence: float = Field(default=1.0, ge=0, le=1)
    target: Optional[Dict[str, Any]] = None
    requires_author_decision: bool = False
    explanation: str = ""


class StoryStudioJobEvent(BaseModel):
    stage: str
    status: Literal["queued", "running", "completed", "failed", "waiting"]
    summary: str
    created_at: Optional[str] = None


class DiscoveryWritingMetadata(BaseModel):
    workflow_mode: Literal["structured", "discovery"] = "discovery"
    instruction: str = Field(min_length=1, max_length=12000)
    chapter_number: Optional[int] = Field(default=None, ge=1, le=100000)
    target_word_min: Optional[int] = Field(default=None, ge=1, le=200000)
    target_word_count: Optional[int] = Field(default=None, ge=1, le=200000)
    target_word_max: Optional[int] = Field(default=None, ge=1, le=200000)
    pov_character: Optional[str] = Field(default=None, max_length=200)
    pov_person: Optional[Literal["first person", "third person", "omniscient"]] = None
    intentional_pov_change: bool = False

    @model_validator(mode="after")
    def validate_range(self) -> "DiscoveryWritingMetadata":
        values = [value for value in (self.target_word_min, self.target_word_count, self.target_word_max) if value is not None]
        if self.target_word_min is not None and self.target_word_max is not None and self.target_word_min > self.target_word_max:
            raise ValueError("target_word_min cannot exceed target_word_max")
        if self.target_word_count is not None:
            if self.target_word_min is not None and self.target_word_count < self.target_word_min:
                raise ValueError("target_word_count cannot be below target_word_min")
            if self.target_word_max is not None and self.target_word_count > self.target_word_max:
                raise ValueError("target_word_count cannot exceed target_word_max")
        if values and max(values) > 200000:
            raise ValueError("chapter word range is too large")
        return self


class ExtractionCandidate(BaseModel):
    candidate_type: str
    subject: str
    value: Any = None
    confidence: float = Field(default=0.5, ge=0, le=1)
    evidence: List[str] = Field(default_factory=list, max_length=20)
    status: Literal["candidate", "proposed", "approved", "rejected"] = "candidate"
    provenance: Dict[str, Any] = Field(default_factory=dict)


class StoryStudioResult(BaseModel):
    understood: str
    intent: StoryStudioIntent
    answer: str
    mutation_applied: bool = False
    author_decision_required: bool = False
    navigation_actions: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    job_id: str
    change_receipt: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None
    planning_capture: Optional[Dict[str, Any]] = None
    writing_actions: List[str] = Field(default_factory=list)
    draft: Optional[Dict[str, Any]] = None
    creative_review: Optional[Dict[str, Any]] = None
    clarification: Optional[Dict[str, Any]] = None
    continued_from_job_id: Optional[str] = None
    generation_metadata: Dict[str, Any] = Field(default_factory=dict)
    development: Optional[Dict[str, Any]] = None
