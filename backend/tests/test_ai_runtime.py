import pytest

from app.ai.dependencies import create_generation_service
from app.ai.evaluation import outcome_metrics, quality_delta
from app.ai.providers.base import RoadmapProviderError
from app.ai.providers.compatible import (
    OpenAICompatibleRoadmapProvider,
    portable_strict_schema,
    safe_provider_diagnostic,
    safe_validation_diagnostic,
    strict_response_format,
)
from app.ai.providers.fixture import FixtureRoadmapProvider
from app.ai.schema import RoadmapDraft, RoadmapGenerationInput
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
        ai_response_format="json_object",
        ai_reasoning_effort="",
        ai_api_key="server-secret",
    )

    assert settings.ai_provider == "groq"
    assert settings.ai_base_url == "https://api.groq.com/openai/v1"
    assert settings.ai_model == "openai/gpt-oss-20b"
    assert settings.ai_response_format == "json_object"
    assert settings.ai_reasoning_effort is None
    assert settings.ai_configured is True
    assert settings.ai_generation_mode == "live_ai"

    service = create_generation_service(settings)

    assert isinstance(service, FallbackRoadmapGenerationService)
    provider = service.primary.provider
    assert provider.source == "groq"
    assert provider.model == "openai/gpt-oss-20b"
    assert provider.response_format_mode == "json_object"
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


def test_provider_diagnostic_contains_only_bounded_metadata() -> None:
    class ProviderFailure(Exception):
        status_code = 429
        code = "rate_limit_exceeded"
        type = "tokens"
        param = "response_format"

    error = ProviderFailure("raw provider detail that must never be logged")

    assert safe_provider_diagnostic(error) == (
        "ProviderFailure;status_code=429;code=rate_limit_exceeded;"
        "type=tokens;param=response_format"
    )
    assert "raw provider detail" not in safe_provider_diagnostic(error)


def test_validation_diagnostic_excludes_generated_values() -> None:
    generated_value = "private model output that must not be logged"
    with pytest.raises(ValueError) as captured:
        RoadmapDraft.model_validate({"title": generated_value})

    diagnostic = safe_validation_diagnostic(captured.value)

    assert diagnostic.startswith("validation_error;count=")
    assert "schema_version:missing" in diagnostic
    assert generated_value not in diagnostic


def test_portable_schema_keeps_shape_and_defers_field_constraints_to_pydantic() -> None:
    response_format = strict_response_format(RoadmapDraft)
    json_schema = response_format["json_schema"]
    schema = json_schema["schema"]

    assert json_schema["strict"] is True
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == set(schema["required"])
    assert schema["properties"]["schema_version"]["enum"] == ["1.0"]

    def schema_keywords(value: object) -> set[str]:
        if isinstance(value, list):
            return set().union(*(schema_keywords(item) for item in value), set())
        if not isinstance(value, dict):
            return set()
        keys = set(value)
        for key, item in value.items():
            if key in {"$defs", "properties"} and isinstance(item, dict):
                keys.update(
                    set().union(
                        *(schema_keywords(definition) for definition in item.values()),
                        set(),
                    )
                )
            else:
                keys.update(schema_keywords(item))
        return keys

    keywords = schema_keywords(schema)
    for unsupported_keyword in (
        "const",
        "maxItems",
        "maxLength",
        "minItems",
        "minLength",
        "pattern",
        "title",
    ):
        assert unsupported_keyword not in keywords

    full_schema = RoadmapDraft.model_json_schema()
    assert "minLength" in str(full_schema)
    assert portable_strict_schema(full_schema) == schema


@pytest.mark.parametrize(
    ("response_format_mode", "first_failure"),
    [
        ("json_schema", "none"),
        ("json_object", "provider"),
        ("json_object", "local_validation"),
    ],
)
def test_compatible_provider_parses_with_portable_strict_schema(
    response_format_mode: str,
    first_failure: str,
) -> None:
    fixture = FixtureRoadmapProvider().generate(generation_input()).value
    request: dict[str, object] = {}

    class Message:
        refusal = None

        def __init__(self, content: str) -> None:
            self.content = content

    class Choice:
        def __init__(self, content: str) -> None:
            self.message = Message(content)

    class Usage:
        prompt_tokens = 12
        completion_tokens = 34

    class Completion:
        usage = Usage()
        id = "groq-test-response"

        def __init__(self, content: str) -> None:
            self.choices = [Choice(content)]

    class JsonValidationFailure(ValueError):
        code = "json_validate_failed"

    class Completions:
        calls = 0

        def create(self, **kwargs: object) -> Completion:
            self.calls += 1
            request.update(kwargs)
            if first_failure == "provider" and self.calls == 1:
                raise JsonValidationFailure("provider response content must not be logged")
            content = (
                "{}"
                if first_failure == "local_validation" and self.calls == 1
                else fixture.model_dump_json()
            )
            return Completion(content)

    class Chat:
        completions = Completions()

    class Client:
        chat = Chat()

    provider = OpenAICompatibleRoadmapProvider(
        provider_name="groq",
        api_key="unused-test-key",
        base_url="https://api.groq.com/openai/v1",
        model="openai/gpt-oss-20b",
        response_format_mode=response_format_mode,
        client=Client(),
    )

    result = provider.generate(generation_input())

    assert result.value == fixture
    assert result.response_id == "groq-test-response"
    assert result.input_tokens == 12
    assert result.output_tokens == 34
    assert request["response_format"]["type"] == response_format_mode
    if response_format_mode == "json_schema":
        assert request["response_format"]["json_schema"]["strict"] is True
    else:
        assert "matching this JSON Schema" in request["messages"][1]["content"]
        assert "maxItems" in request["messages"][1]["content"]
        assert request["temperature"] == 0
        assert provider.client.chat.completions.calls == 2
        if first_failure == "local_validation":
            assert "validation_error" in request["messages"][-1]["content"]


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
