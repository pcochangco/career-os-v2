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
    service = create_generation_service(Settings(ai_mode="auto", ai_provider="groq"))

    outcome = service.generate(generation_input())

    assert outcome.provider == "fixture"
    assert outcome.model == "deterministic-fixture"


def test_strict_live_mode_rejects_a_missing_key() -> None:
    with pytest.raises(RoadmapProviderError):
        create_generation_service(Settings(ai_mode="live", ai_provider="groq"))


def test_provider_endpoint_and_model_are_configuration_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_config: dict[str, object] = {}

    class FakeOpenAIClient:
        def __init__(self, **kwargs: object) -> None:
            client_config.update(kwargs)

    monkeypatch.setattr("app.ai.providers.compatible.OpenAI", FakeOpenAIClient)
    settings = Settings(
        ai_mode="auto",
        ai_provider="groq",
        ai_base_url="https://api.groq.com/openai/v1/",
        ai_model="openai/gpt-oss-20b",
        ai_reasoning_effort="",
        ai_api_key="server-secret",
    )

    assert settings.ai_provider == "groq"
    assert settings.ai_base_url == "https://api.groq.com/openai/v1"
    assert settings.ai_model == "openai/gpt-oss-20b"
    assert settings.ai_reasoning_effort is None
    assert settings.ai_configured is True
    assert settings.ai_generation_mode == "live_ai"

    service = create_generation_service(settings)

    assert isinstance(service, FallbackRoadmapGenerationService)
    provider = service.primary.provider
    assert provider.source == "groq"
    assert provider.model == "openai/gpt-oss-20b"
    assert provider.reasoning_effort is None
    assert client_config["base_url"] == "https://api.groq.com/openai/v1"


@pytest.mark.parametrize(
    "base_url",
    [
        "http://api.example.com/v1",
        "https://user:password@api.example.com/v1",
        "https://api.example.com/v1?key=secret",
    ],
)
def test_live_provider_endpoint_must_be_credential_free_https(base_url: str) -> None:
    with pytest.raises(ValueError):
        Settings(ai_base_url=base_url)


def test_generic_ai_key_remains_redacted_in_settings() -> None:
    settings = Settings(ai_api_key="server-secret")

    assert "server-secret" not in repr(settings)


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
