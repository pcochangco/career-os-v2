import re
from datetime import datetime
from typing import Any, Literal
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

GOAL_SIGNAL_WORDS = {
    "abroad",
    "achieve",
    "advance",
    "apply",
    "application",
    "app",
    "automate",
    "be",
    "become",
    "build",
    "business",
    "buy",
    "cafe",
    "career",
    "certification",
    "change",
    "complete",
    "course",
    "create",
    "debt",
    "degree",
    "design",
    "develop",
    "developer",
    "engineer",
    "earn",
    "engineering",
    "exam",
    "exercise",
    "fitness",
    "fit",
    "fluency",
    "gain",
    "graduate",
    "get",
    "goal",
    "grow",
    "growth",
    "health",
    "healthy",
    "home",
    "house",
    "improve",
    "increase",
    "income",
    "interview",
    "invest",
    "investment",
    "job",
    "launch",
    "language",
    "lead",
    "learn",
    "license",
    "lose",
    "loss",
    "manager",
    "make",
    "marathon",
    "master",
    "mastery",
    "migrate",
    "move",
    "open",
    "own",
    "pass",
    "pay",
    "portfolio",
    "practice",
    "prepare",
    "product",
    "project",
    "promotion",
    "publish",
    "quit",
    "race",
    "read",
    "reach",
    "reduce",
    "relocate",
    "relocation",
    "research",
    "run",
    "save",
    "salary",
    "savings",
    "scholarship",
    "secure",
    "skill",
    "speak",
    "start",
    "stop",
    "study",
    "system",
    "train",
    "travel",
    "visa",
    "website",
    "weight",
    "work",
    "write",
}

ALLOWED_SINGLE_WORD_GOALS = {
    "fitness",
    "health",
    "leadership",
    "meditation",
    "networking",
    "programming",
    "promotion",
    "retirement",
    "running",
    "scholarship",
    "writing",
}


class AnonymousSessionRead(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID


class IdentityLinkWrite(BaseModel):
    identity_token: str = Field(min_length=40, max_length=8192)


class AuthProviderConfigRead(BaseModel):
    apple: bool = False
    google: bool = False
    google_web_client_id: str = ""
    google_ios_client_id: str = ""
    google_android_client_id: str = ""


class AccountRead(BaseModel):
    user_id: UUID
    status: Literal["guest", "saved"]
    providers: list[Literal["apple", "google"]] = Field(default_factory=list)
    email: str = ""
    provider_config: AuthProviderConfigRead


class GoalCreate(BaseModel):
    title: str = Field(min_length=3, max_length=140)

    @field_validator("title")
    @classmethod
    def require_meaningful_title(cls, value: str) -> str:
        title = " ".join(value.split())
        lower_title = title.lower()
        words = re.findall(r"[a-z]+", lower_title)
        letters_only = "".join(words)
        keyboard_patterns = ("qwerty", "asdf", "zxcv", "poiuy", "lkjh")
        is_repeated_character = bool(re.fullmatch(r"(.)\1{2,}", title))
        has_goal_signal = any(word in GOAL_SIGNAL_WORDS for word in words)
        is_allowed_single_word = len(words) == 1 and words[0] in ALLOWED_SINGLE_WORD_GOALS
        is_short_acronym = bool(re.fullmatch(r"[A-Z]{2,8}", title))
        has_proficiency_target = bool(re.search(r"\b[ABC][12]\b", title.upper()))

        if (
            len(title) < 3
            or not letters_only
            or is_repeated_character
            or any(pattern in letters_only for pattern in keyboard_patterns)
            or not (
                has_goal_signal
                or is_allowed_single_word
                or is_short_acronym
                or has_proficiency_target
            )
        ):
            raise ValueError(
                "Write a clear goal with an action or outcome, such as “Learn Spanish” "
                "or “Run a 5K”"
            )
        return title


class DiscoveryWrite(BaseModel):
    desired_outcome: str = Field(min_length=3, max_length=1000)
    current_level: str = Field(min_length=1, max_length=500)
    existing_experience: str = Field(min_length=1, max_length=1000)
    relevant_constraints: str = Field(min_length=1, max_length=1000)
    proof_of_completion: str = Field(min_length=3, max_length=1000)


class DiscoveryOptionRead(BaseModel):
    key: str
    label: str


class DiscoveryQuestionRead(BaseModel):
    id: UUID
    position: int
    question_key: str
    question: str
    help_text: str
    selection_mode: Literal["multiple"]
    options: list[DiscoveryOptionRead]
    placeholder: str


class DiscoveryStateRead(BaseModel):
    status: Literal["unstarted", "question", "ready"]
    goal_title: str = ""
    question: DiscoveryQuestionRead | None = None
    context_summary: list[str] = Field(default_factory=list)
    completion_reason: str = ""
    answered_questions: int = 0
    minimum_questions: int = 3
    maximum_questions: int = 4


class DiscoveryAnswerWrite(BaseModel):
    selected_option_keys: list[str] = Field(default_factory=list, max_length=6)
    custom_answer: str = Field(default="", max_length=1000)
    skipped: bool = False

    @field_validator("selected_option_keys", "custom_answer")
    @classmethod
    def trim_discovery_answer(cls, value: list[str] | str) -> list[str] | str:
        if isinstance(value, list):
            return [item.strip() for item in value if item.strip()]
        return value.strip()

    @model_validator(mode="after")
    def require_discovery_response(self) -> "DiscoveryAnswerWrite":
        if not self.skipped and not self.selected_option_keys and not self.custom_answer:
            raise ValueError("Choose an answer, write your own, or skip this question")
        if self.skipped and (self.selected_option_keys or self.custom_answer):
            raise ValueError("A skipped question cannot include an answer")
        return self


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
