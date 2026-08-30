from datetime import datetime
from typing import Any, Literal
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AnonymousSessionRead(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID


class GoalCreate(BaseModel):
    title: str = Field(min_length=3, max_length=140)


class DiscoveryWrite(BaseModel):
    desired_outcome: str = Field(min_length=3, max_length=1000)
    current_level: str = Field(min_length=1, max_length=500)
    existing_experience: str = Field(min_length=1, max_length=1000)
    relevant_constraints: str = Field(min_length=1, max_length=1000)
    proof_of_completion: str = Field(min_length=3, max_length=1000)


class GoalRead(BaseModel):
    id: UUID
    title: str
    status: str
    created_at: datetime
    active_roadmap_id: UUID | None = None
    latest_draft_roadmap_id: UUID | None = None
    completed_steps: int = 0
    total_steps: int = 0
    progress_percent: int = 0


class StepProgressWrite(BaseModel):
    completed: bool
    completion_confirmed: bool = False

    @model_validator(mode="after")
    def require_completion_confirmation(self) -> "StepProgressWrite":
        if self.completed and not self.completion_confirmed:
            raise ValueError("Confirm that the completion condition was met")
        return self


class StepWorkWrite(BaseModel):
    notes: str = Field(default="", max_length=4000)
    evidence_summary: str = Field(default="", max_length=1000)
    evidence_url: str = Field(default="", max_length=2048)

    @field_validator("notes", "evidence_summary", "evidence_url")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("evidence_url")
    @classmethod
    def require_public_web_url(cls, value: str) -> str:
        if not value:
            return value
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Evidence link must be a valid http:// or https:// URL")
        return value


class LearningResourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resource_type: Literal["article", "video"]
    title: str
    url: str
    source_name: str
    description: str
    why_relevant: str
    thumbnail_url: str
    verified_at: datetime


class StepResourcesRead(BaseModel):
    step_id: UUID
    resources: list[LearningResourceRead]
    available: bool
    cached: bool
    message: str = ""


class RoadmapStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    position: int
    stable_key: str
    kind: str
    title: str
    objective: str
    rationale: str
    action: str
    completion_condition: str
    effort_label: str
    evidence_suggestion: str
    prerequisite_step_keys: list[str]
    resource_queries: list[str]
    progress_status: Literal["completed", "current", "upcoming", "blocked"] = "upcoming"
    completed_at: datetime | None = None
    notes: str = ""
    evidence_summary: str = ""
    evidence_url: str = ""
    work_updated_at: datetime | None = None


class RoadmapMilestoneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    position: int
    title: str
    outcome: str
    rationale: str
    steps: list[RoadmapStepRead]


class RoadmapRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    goal_id: UUID
    version: int
    status: str
    title: str
    summary: str
    goal_outcome: str
    starting_state_summary: str
    assumptions: list[str]
    schema_version: str
    generation_source: str
    provider_model: str
    prompt_version: str
    quality_report: dict[str, Any]
    quality_score: int
    input_tokens: int
    output_tokens: int
    generation_duration_ms: int
    created_at: datetime
    accepted_at: datetime | None
    completed_steps: int = 0
    total_steps: int = 0
    progress_percent: int = 0
    current_step_id: UUID | None = None
    milestones: list[RoadmapMilestoneRead]
