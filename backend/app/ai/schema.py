from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RoadmapGenerationInput(StrictModel):
    goal_title: str
    desired_outcome: str
    current_level: str
    existing_experience: str
    relevant_constraints: str
    proof_of_completion: str


class RoadmapDraftStep(StrictModel):
    stable_key: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9-]+$")
    kind: Literal["learn", "practice", "prove"]
    title: str = Field(min_length=5, max_length=180)
    objective: str = Field(min_length=12, max_length=600)
    rationale: str = Field(min_length=12, max_length=600)
    action: str = Field(min_length=20, max_length=1600)
    completion_condition: str = Field(min_length=12, max_length=800)
    effort_label: Literal[
        "Short focused session",
        "Several focused sessions",
        "Multi-session project",
    ]
    evidence_suggestion: str = Field(min_length=3, max_length=500)
    prerequisite_step_keys: list[str] = Field(max_length=6)
    resource_queries: list[str] = Field(max_length=4)


class RoadmapDraftMilestone(StrictModel):
    title: str = Field(min_length=5, max_length=180)
    outcome: str = Field(min_length=12, max_length=800)
    rationale: str = Field(min_length=12, max_length=800)
    steps: list[RoadmapDraftStep] = Field(min_length=1, max_length=8)


class RoadmapDraft(StrictModel):
    schema_version: Literal["1.0"]
    title: str = Field(min_length=5, max_length=180)
    summary: str = Field(min_length=20, max_length=1200)
    goal_outcome: str = Field(min_length=12, max_length=1000)
    starting_state_summary: str = Field(min_length=12, max_length=1000)
    assumptions: list[str] = Field(max_length=8)
    milestones: list[RoadmapDraftMilestone] = Field(min_length=2, max_length=8)


class QualityIssue(StrictModel):
    severity: Literal["warning", "error"]
    code: str
    message: str
    path: str
    repair_instruction: str


class ProviderCritique(StrictModel):
    passed: bool
    score: int = Field(ge=0, le=100)
    summary: str
    issues: list[QualityIssue] = Field(max_length=20)


class QualityReport(StrictModel):
    passed: bool
    final_score: int = Field(ge=0, le=100)
    structural_score: int = Field(ge=0, le=100)
    critic_score: int = Field(ge=0, le=100)
    repair_attempts: int = Field(ge=0)
    issues: list[QualityIssue]
