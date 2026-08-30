import pytest

from app.ai.dependencies import create_generation_service
from app.ai.evaluation import outcome_metrics, quality_delta
from app.ai.providers.base import RoadmapProviderError
from app.ai.providers.fixture import FixtureRoadmapProvider
from app.ai.schema import RoadmapGenerationInput
from app.ai.service import FallbackRoadmapGenerationService, RoadmapGenerationService
from app.core.config import Settings


def generation_input() -> RoadmapGenerationInput:
    return RoadmapGenerationInput(
        goal_title="Build an AI automation system",
        desired_outcome="Deploy and evaluate a reliable AI automation workflow",
        current_level="Experienced Python automation engineer",
        existing_experience="Python, APIs, RAG, and LLM integrations",
        relevant_constraints="Prefer practical work and concise explanations",
        proof_of_completion="A deployed system with an evaluation report",
    )


class FailingProvider(FixtureRoadmapProvider):
    source = "openai"
    model = "failing-live-model"

    def generate(self, generation_input: RoadmapGenerationInput):
        del generation_input
        raise RoadmapProviderError("simulated provider outage")


def test_auto_mode_uses_fixture_without_a_server_key() -> None:
    service = create_generation_service(Settings(ai_provider="auto"))

    outcome = service.generate(generation_input())

    assert outcome.provider == "fixture"
    assert outcome.model == "deterministic-fixture"


def test_strict_openai_mode_rejects_a_missing_key() -> None:
    with pytest.raises(RoadmapProviderError):
        create_generation_service(Settings(ai_provider="openai"))


def test_live_failure_falls_back_to_the_quality_checked_fixture() -> None:
    service = FallbackRoadmapGenerationService(
        primary=RoadmapGenerationService(FailingProvider()),
        fallback=RoadmapGenerationService(FixtureRoadmapProvider()),
    )

    outcome = service.generate(generation_input())

    assert outcome.provider == "fixture"
    assert outcome.quality.passed is True


def test_evaluation_metrics_compare_without_exposing_roadmap_text() -> None:
    outcome = RoadmapGenerationService(FixtureRoadmapProvider()).generate(generation_input())
    metrics = outcome_metrics(outcome)

    assert metrics["provider"] == "fixture"
    assert metrics["steps"] == 6
    assert quality_delta(metrics, metrics) == 0
    assert "draft" not in metrics
