from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
    milestones: list[RoadmapMilestoneRead]
