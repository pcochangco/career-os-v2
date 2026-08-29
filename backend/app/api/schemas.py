from datetime import datetime
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
    kind: str
    title: str
    objective: str
    action: str
    completion_condition: str
    effort_label: str


class RoadmapMilestoneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    position: int
    title: str
    outcome: str
    steps: list[RoadmapStepRead]


class RoadmapRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    goal_id: UUID
    version: int
    status: str
    title: str
    summary: str
    generation_source: str
    created_at: datetime
    accepted_at: datetime | None
    milestones: list[RoadmapMilestoneRead]
