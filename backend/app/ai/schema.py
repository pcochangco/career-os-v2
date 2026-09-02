from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RoadmapGenerationInput(StrictModel):
    goal_title: str
    desired_outcome: str
    current_level: str
    existing_experience: str
    relevant_constraints: str
    proof_of_completion: str
    discovery_context: list["DiscoveryContextAnswer"] = Field(default_factory=list, max_length=6)


class DiscoveryContextAnswer(StrictModel):
    question_key: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9-]+$")
    question: str = Field(min_length=8, max_length=400)
    answer: str = Field(min_length=1, max_length=1200)
    skipped: bool = False


class GoalIntentAssessment(StrictModel):
    is_meaningful: bool
    normalized_title: str = Field(default="", max_length=140)
    reason: Literal["meaningful", "nonsense", "not_a_goal", "too_vague"]

    @model_validator(mode="after")
    def require_a_usable_normalized_title(self) -> "GoalIntentAssessment":
        if self.is_meaningful and len(self.normalized_title.strip()) < 3:
            raise ValueError("A meaningful goal must include a usable normalized title")
        if self.is_meaningful != (self.reason == "meaningful"):
            raise ValueError("Goal meaning and reason must agree")
        if not self.is_meaningful and self.normalized_title.strip():
            raise ValueError("A rejected goal must not include a normalized title")
        return self


class DiscoveryOption(StrictModel):
    key: str = Field(min_length=1, max_length=48, pattern=r"^[a-z0-9-]+$")
    label: str = Field(min_length=2, max_length=72)


class DiscoveryQuestionDraft(StrictModel):
    is_complete: bool
    suggested_goal_title: str = Field(default="", max_length=140)
    question_key: str = Field(default="", max_length=64, pattern=r"^[a-z0-9-]*$")
    question: str = Field(default="", max_length=240)
    help_text: str = Field(default="", max_length=240)
    selection_mode: Literal["multiple"] = "multiple"
    options: list[DiscoveryOption] = Field(default_factory=list, max_length=6)
    placeholder: str = Field(default="", max_length=180)
    completion_reason: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def require_an_actionable_question(self) -> "DiscoveryQuestionDraft":
        """Make incomplete discovery turns retryable structured-output failures."""
        if self.suggested_goal_title and len(self.suggested_goal_title.strip()) < 3:
            raise ValueError("A suggested goal title must be useful when provided")
        if self.is_complete:
            return self
        if not self.question_key:
            raise ValueError("An incomplete discovery turn must include a question key")
        if len(self.question.strip()) < 8:
            raise ValueError("An incomplete discovery turn must include a useful question")
        if len(self.help_text.strip()) < 8:
            raise ValueError("An incomplete discovery turn must include helpful guidance")
        if len(self.options) < 3:
            raise ValueError("An incomplete discovery turn must include three answer options")
        return self


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
