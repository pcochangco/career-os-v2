from dataclasses import dataclass
from typing import Protocol

from app.ai.schema import (
    ProviderCritique,
    QualityIssue,
    RoadmapDraft,
    RoadmapGenerationInput,
)


@dataclass(frozen=True)
class ProviderResult[T]:
    value: T
    response_id: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0


class RoadmapProvider(Protocol):
    source: str
    model: str
    prompt_version: str

    def generate(
        self,
        generation_input: RoadmapGenerationInput,
    ) -> ProviderResult[RoadmapDraft]: ...

    def critique(
        self,
        generation_input: RoadmapGenerationInput,
        draft: RoadmapDraft,
    ) -> ProviderResult[ProviderCritique]: ...

    def repair(
        self,
        generation_input: RoadmapGenerationInput,
        draft: RoadmapDraft,
        issues: list[QualityIssue],
    ) -> ProviderResult[RoadmapDraft]: ...


class RoadmapProviderError(RuntimeError):
    """A provider could not return a usable structured response."""

    def __init__(self, message: str, *, diagnostic_code: str = "provider_error") -> None:
        super().__init__(message)
        self.diagnostic_code = diagnostic_code
