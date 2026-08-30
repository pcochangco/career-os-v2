from typing import TypedDict

from app.ai.service import GenerationOutcome


class OutcomeMetrics(TypedDict):
    provider: str
    model: str
    passed: bool
    quality_score: int
    milestones: int
    steps: int
    input_tokens: int
    output_tokens: int
    duration_ms: int


def outcome_metrics(outcome: GenerationOutcome) -> OutcomeMetrics:
    return {
        "provider": outcome.provider,
        "model": outcome.model,
        "passed": outcome.quality.passed,
        "quality_score": outcome.quality.final_score,
        "milestones": len(outcome.draft.milestones),
        "steps": sum(len(milestone.steps) for milestone in outcome.draft.milestones),
        "input_tokens": outcome.input_tokens,
        "output_tokens": outcome.output_tokens,
        "duration_ms": outcome.duration_ms,
    }


def quality_delta(live: OutcomeMetrics, fixture: OutcomeMetrics) -> int:
    return live["quality_score"] - fixture["quality_score"]
