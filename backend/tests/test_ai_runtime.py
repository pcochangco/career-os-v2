import pytest

from app.ai.dependencies import create_generation_service
from app.ai.evaluation import outcome_metrics, quality_delta
from app.ai.providers.base import RoadmapProviderError
from app.ai.providers.compatible import (
    CRITIC_PROMPT,
    SYSTEM_PROMPT,
    OpenAICompatibleRoadmapProvider,
    portable_strict_schema,
    safe_provider_diagnostic,
    safe_validation_diagnostic,
    strict_response_format,
)
from app.ai.providers.fixture import FixtureRoadmapProvider
from app.ai.schema import (
    DiscoveryQuestionDraft,
    ProviderCritique,
    QualityIssue,
    RoadmapDraft,
    RoadmapGenerationInput,
)
from app.ai.service import (
    FallbackRoadmapGenerationService,
    RetryingRoadmapGenerationService,
    RoadmapGenerationService,
)
from app.core.config import Settings
from evals.diagnose_live import diagnose


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
        ai_model="openai/gpt-oss-120b",
        ai_critic_model="openai/gpt-oss-20b",
        ai_repair_model="qwen/qwen3.8-27b",
        ai_discovery_model="qwen/qwen3.6-27b",
        ai_response_format="json_object",
        ai_reasoning_effort="low",
        ai_max_completion_tokens=5000,
        ai_critic_max_completion_tokens=1600,
        ai_repair_max_completion_tokens=4800,
        ai_discovery_max_completion_tokens=700,
        ai_api_key="server-secret",
    )

    assert settings.ai_provider == "groq"
    assert settings.ai_base_url == "https://api.groq.com/openai/v1"
    assert settings.ai_model == "openai/gpt-oss-120b"
    assert settings.resolved_ai_critic_model == "openai/gpt-oss-20b"
    assert settings.resolved_ai_repair_model == "qwen/qwen3.8-27b"
    assert settings.resolved_ai_discovery_model == "qwen/qwen3.6-27b"
    assert settings.ai_response_format == "json_object"
    assert settings.ai_reasoning_effort == "low"
    assert settings.ai_max_completion_tokens == 5000
    assert settings.ai_critic_max_completion_tokens == 1600
    assert settings.ai_repair_max_completion_tokens == 4800
    assert settings.ai_discovery_max_completion_tokens == 700
    assert settings.ai_configured is True
    assert settings.ai_generation_mode == "live_ai"

    service = create_generation_service(settings)

    assert isinstance(service, FallbackRoadmapGenerationService)
    provider = service.primary.provider
    assert provider.source == "groq"
    assert provider.model == "openai/gpt-oss-120b"
    assert provider.stage_models == {
        "generate": "openai/gpt-oss-120b",
        "critique": "openai/gpt-oss-20b",
        "repair": "qwen/qwen3.8-27b",
        "discovery": "qwen/qwen3.6-27b",
    }
    assert provider.stage_max_completion_tokens == {
        "generate": 5000,
        "critique": 1600,
        "repair": 4800,
        "discovery": 700,
    }
    assert provider.response_format_mode == "json_object"
    assert provider.reasoning_effort == "low"
    assert provider.max_completion_tokens == 5000
    assert client_config["base_url"] == "https://api.groq.com/openai/v1"


def test_discovery_provider_uses_its_own_model_and_token_cap() -> None:
    request: dict[str, object] = {}

    class Message:
        refusal = None
        content = (
            '{"is_complete":false,"question_key":"focus-area",'
            '"question":"Which specialization matters most to you?",'
            '"help_text":"Choose the direction your roadmap should emphasize.",'
            '"selection_mode":"multiple",'
            '"options":[{"key":"agents","label":"AI agents"},'
            '{"key":"testing","label":"Testing automation"},'
            '{"key":"workflows","label":"Business workflows"}],'
            '"placeholder":"Describe your direction",'
            '"completion_reason":""}'
        )

    class Completion:
        id = "discovery-response"
        choices = [type("Choice", (), {"message": Message(), "finish_reason": "stop"})()]
        usage = type("Usage", (), {"prompt_tokens": 12, "completion_tokens": 34})()

    class Completions:
        def create(self, **kwargs: object) -> Completion:
            request.update(kwargs)
            return Completion()

    client = type("Client", (), {"chat": type("Chat", (), {"completions": Completions()})()})()
    provider = OpenAICompatibleRoadmapProvider(
        provider_name="groq",
        api_key="test-key",
        base_url="https://api.groq.com/openai/v1",
        model="openai/gpt-oss-120b",
        discovery_model="qwen/qwen3.8-27b",
        discovery_max_completion_tokens=700,
        client=client,
    )

    result = provider.next_question(
        goal_title="Become an AI automation engineer",
        answers=[],
        used_question_keys=[],
    )

    assert result.value.question_key == "focus-area"
    assert result.input_tokens == 12
    assert request["model"] == "qwen/qwen3.8-27b"
    assert request["max_completion_tokens"] == 700


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
        "ProviderFailure;status_code=429;code=rate_limit_exceeded;type=tokens;param=response_format"
    )
    assert "raw provider detail" not in safe_provider_diagnostic(error)


def test_prompts_encode_schedule_free_effort_and_exact_critic_contract() -> None:
    assert "Never use minutes, hours, days, weeks" in SYSTEM_PROMPT
    assert 'exactly one of "Short focused session"' in SYSTEM_PROMPT
    assert "Do not request URLs" in CRITIC_PROMPT
    assert "exactly four top-level keys: passed, score, summary, and issues" in CRITIC_PROMPT
    assert "exactly severity, code, message, path, and repair_instruction" in CRITIC_PROMPT
    assert "Do not use overall_pass, category, description, suggestion" in CRITIC_PROMPT
    assert "thoughtful expert mentor, not a syllabus generator" in SYSTEM_PROMPT
    assert "Never reteach a" in SYSTEM_PROMPT
    assert "demonstrated skill as a beginner topic" in SYSTEM_PROMPT
    assert "chains tutorials without" in CRITIC_PROMPT
    assert "independent practice" in CRITIC_PROMPT
    assert "merely because it is" in CRITIC_PROMPT
    assert "structurally valid" in CRITIC_PROMPT


def test_validation_diagnostic_excludes_generated_values() -> None:
    generated_value = "private model output that must not be logged"
    with pytest.raises(ValueError) as captured:
        RoadmapDraft.model_validate({"title": generated_value})

    diagnostic = safe_validation_diagnostic(captured.value)

    assert diagnostic.startswith("validation_error;count=")
    assert "schema_version:missing" in diagnostic
    assert generated_value not in diagnostic


def test_roadmap_schema_rejects_calendar_effort_labels() -> None:
    draft = FixtureRoadmapProvider().generate(generation_input()).value
    payload = draft.model_dump()
    payload["milestones"][0]["steps"][0]["effort_label"] = "2-3 days"

    with pytest.raises(ValueError) as captured:
        RoadmapDraft.model_validate(payload)

    assert "milestones.0.steps.0.effort_label" in safe_validation_diagnostic(captured.value)


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
    assert request["max_completion_tokens"] == 5000
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


def test_compatible_provider_routes_each_stage_to_its_configured_budget() -> None:
    fixture = FixtureRoadmapProvider().generate(generation_input()).value
    repair_issue = QualityIssue(
        severity="error",
        code="test_repair",
        message="Repair the test roadmap.",
        path="roadmap",
        repair_instruction="Return the corrected complete roadmap.",
    )
    critique = ProviderCritique(
        passed=False,
        score=70,
        summary="The roadmap needs one repair.",
        issues=[repair_issue],
    )
    requests: list[dict[str, object]] = []

    class Message:
        refusal = None

        def __init__(self, content: str) -> None:
            self.content = content

    class Choice:
        finish_reason = "stop"

        def __init__(self, content: str) -> None:
            self.message = Message(content)

    class Completion:
        usage = None
        id = "stage-response"

        def __init__(self, content: str) -> None:
            self.choices = [Choice(content)]

    class Completions:
        def create(self, **kwargs: object) -> Completion:
            requests.append(kwargs)
            if kwargs["model"] == "openai/gpt-oss-20b":
                return Completion(critique.model_dump_json())
            return Completion(fixture.model_dump_json())

    class Chat:
        completions = Completions()

    class Client:
        chat = Chat()

    provider = OpenAICompatibleRoadmapProvider(
        provider_name="groq",
        api_key="unused-test-key",
        base_url="https://api.groq.com/openai/v1",
        model="openai/gpt-oss-120b",
        critic_model="openai/gpt-oss-20b",
        repair_model="qwen/qwen3.8-27b",
        response_format_mode="json_object",
        max_completion_tokens=5000,
        critic_max_completion_tokens=1600,
        repair_max_completion_tokens=4800,
        client=Client(),
    )

    generated = provider.generate(generation_input())
    critiqued = provider.critique(generation_input(), generated.value)
    provider.repair(generation_input(), generated.value, critiqued.value.issues)

    assert [(request["model"], request["max_completion_tokens"]) for request in requests] == [
        ("openai/gpt-oss-120b", 5000),
        ("openai/gpt-oss-20b", 1600),
        ("qwen/qwen3.8-27b", 4800),
    ]
    repair_payload = str(requests[-1]["messages"][-1]["content"])
    assert '"input"' not in repair_payload
    assert '"roadmap"' in repair_payload


def test_compatible_provider_retries_a_token_capacity_rejection_with_a_smaller_budget() -> None:
    fixture = FixtureRoadmapProvider().generate(generation_input()).value
    limits: list[int] = []

    class TokenCapacityError(ValueError):
        status_code = 413
        code = "rate_limit_exceeded"
        type = "tokens"

    class Message:
        refusal = None
        content = fixture.model_dump_json()

    class Choice:
        finish_reason = "stop"
        message = Message()

    class Completion:
        choices = [Choice()]
        usage = None
        id = "smaller-budget-response"

    class Completions:
        def create(self, **kwargs: object) -> Completion:
            limits.append(int(kwargs["max_completion_tokens"]))
            if len(limits) == 1:
                raise TokenCapacityError("provider token reservation was too large")
            return Completion()

    class Chat:
        completions = Completions()

    class Client:
        chat = Chat()

    provider = OpenAICompatibleRoadmapProvider(
        provider_name="groq",
        api_key="unused-test-key",
        base_url="https://api.groq.com/openai/v1",
        model="openai/gpt-oss-120b",
        response_format_mode="json_object",
        max_completion_tokens=5000,
        client=Client(),
    )

    result = provider.generate(generation_input())

    assert result.value == fixture
    assert limits == [5000, 3250]


def test_completion_length_limit_is_reported_before_parsing_truncated_json() -> None:
    class Message:
        refusal = None
        content = '{"schema_version":"1.0","title":"truncated'

    class Choice:
        finish_reason = "length"
        message = Message()

    class Completion:
        choices = [Choice()]
        usage = None
        id = "truncated-response"

    class Completions:
        calls = 0

        def create(self, **kwargs: object) -> Completion:
            self.calls += 1
            assert kwargs["max_completion_tokens"] == 5000
            return Completion()

    class Chat:
        completions = Completions()

    class Client:
        chat = Chat()

    provider = OpenAICompatibleRoadmapProvider(
        provider_name="groq",
        api_key="unused-test-key",
        base_url="https://api.groq.com/openai/v1",
        model="openai/gpt-oss-120b",
        response_format_mode="json_object",
        max_completion_tokens=5000,
        client=Client(),
    )

    with pytest.raises(RoadmapProviderError) as captured:
        provider.generate(generation_input())

    assert captured.value.diagnostic_code == "stage=generate;finish_reason=length"
    assert provider.client.chat.completions.calls == 1


def test_discovery_retries_an_incomplete_question_missing_options() -> None:
    invalid = (
        '{"is_complete":false,"question_key":"specialty","question":"Which specialty "'
        '"will you focus on?","help_text":"Choose the direction that best fits your goal.",'
        '"selection_mode":"multiple","options":[],"placeholder":""}'
    )
    valid = DiscoveryQuestionDraft.model_validate(
        {
            "is_complete": False,
            "question_key": "specialty",
            "question": "Which specialty will you focus on?",
            "help_text": "Choose the direction that best fits your goal.",
            "selection_mode": "multiple",
            "options": [
                {"key": "agents", "label": "AI agents"},
                {"key": "workflows", "label": "Business workflows"},
                {"key": "testing", "label": "AI testing"},
            ],
            "placeholder": "Describe another direction…",
        }
    ).model_dump_json()

    class Message:
        refusal = None

        def __init__(self, content: str) -> None:
            self.content = content

    class Choice:
        finish_reason = "stop"

        def __init__(self, content: str) -> None:
            self.message = Message(content)

    class Completion:
        usage = None
        id = "discovery-response"

        def __init__(self, content: str) -> None:
            self.choices = [Choice(content)]

    class Completions:
        calls = 0

        def create(self, **kwargs: object) -> Completion:
            assert kwargs["model"] == "qwen/qwen3.8-27b"
            self.calls += 1
            return Completion(invalid if self.calls == 1 else valid)

    class Chat:
        completions = Completions()

    class Client:
        chat = Chat()

    provider = OpenAICompatibleRoadmapProvider(
        provider_name="groq",
        api_key="unused-test-key",
        base_url="https://api.groq.com/openai/v1",
        model="openai/gpt-oss-120b",
        discovery_model="qwen/qwen3.8-27b",
        response_format_mode="json_object",
        discovery_max_completion_tokens=700,
        client=Client(),
    )

    question = provider.next_question(
        goal_title="Become an AI automation engineer",
        answers=[],
        used_question_keys=[],
    )

    assert question.value.question_key == "specialty"
    assert provider.client.chat.completions.calls == 2


def test_persistent_provider_failure_reports_only_the_generation_stage() -> None:
    class JsonValidationFailure(ValueError):
        code = "json_validate_failed"

    class Completions:
        def create(self, **kwargs: object) -> object:
            del kwargs
            raise JsonValidationFailure("private generated response")

    class Chat:
        completions = Completions()

    class Client:
        chat = Chat()

    provider = OpenAICompatibleRoadmapProvider(
        provider_name="groq",
        api_key="unused-test-key",
        base_url="https://api.groq.com/openai/v1",
        model="openai/gpt-oss-120b",
        response_format_mode="json_object",
        client=Client(),
    )

    with pytest.raises(RoadmapProviderError) as captured:
        provider.generate(generation_input())

    assert captured.value.diagnostic_code == (
        "stage=generate;model=openai/gpt-oss-120b;max_tokens=5000;"
        "JsonValidationFailure;code=json_validate_failed"
    )
    assert "private generated response" not in captured.value.diagnostic_code


def test_live_failure_falls_back_to_the_quality_checked_fixture() -> None:
    service = FallbackRoadmapGenerationService(
        primary=RoadmapGenerationService(FailingProvider()),
        fallback=RoadmapGenerationService(FixtureRoadmapProvider()),
    )

    outcome = service.generate(generation_input())

    assert outcome.provider == "fixture"
    assert outcome.quality.passed is True


def test_live_generation_retries_one_transient_capacity_failure() -> None:
    class RateLimitedOnceProvider(FixtureRoadmapProvider):
        calls = 0

        def generate(self, generation_input: RoadmapGenerationInput):
            self.calls += 1
            if self.calls == 1:
                raise RoadmapProviderError(
                    "simulated transient limit",
                    diagnostic_code=(
                        "stage=repair;APIStatusError;status_code=413;"
                        "code=rate_limit_exceeded;type=tokens"
                    ),
                )
            return super().generate(generation_input)

    waits: list[float] = []
    provider = RateLimitedOnceProvider()
    service = RetryingRoadmapGenerationService(
        RoadmapGenerationService(provider),
        max_transient_retries=1,
        retry_delay_seconds=15,
        sleeper=waits.append,
    )

    outcome = service.generate(generation_input())

    assert outcome.quality.passed is True
    assert provider.calls == 2
    assert waits == [15]


def test_live_generation_does_not_retry_non_transient_provider_failures() -> None:
    provider = FailingProvider()
    service = RetryingRoadmapGenerationService(
        RoadmapGenerationService(provider),
        max_transient_retries=1,
        retry_delay_seconds=15,
        sleeper=lambda _: (_ for _ in ()).throw(AssertionError("must not sleep")),
    )

    with pytest.raises(RoadmapProviderError):
        service.generate(generation_input())


def test_evaluation_metrics_compare_without_exposing_roadmap_text() -> None:
    outcome = RoadmapGenerationService(FixtureRoadmapProvider()).generate(generation_input())
    metrics = outcome_metrics(outcome)

    assert metrics["provider"] == "fixture"
    assert metrics["steps"] == 6
    assert quality_delta(metrics, metrics) == 0
    assert "draft" not in metrics


def test_live_diagnostic_runs_stages_without_exposing_roadmap_content() -> None:
    report = diagnose(
        FixtureRoadmapProvider(),
        generation_input(),
        quality_threshold=80,
        max_repair_attempts=1,
    )

    assert report["passed"] is True
    assert [stage["stage"] for stage in report["stages"]] == [
        "generate",
        "structure",
        "critique",
        "quality_gate",
    ]
    serialized = str(report)
    assert "draft" not in serialized
    assert generation_input().existing_experience not in serialized


def test_live_diagnostic_reports_safe_provider_stage_failure() -> None:
    report = diagnose(
        FailingProvider(),
        generation_input(),
        quality_threshold=80,
        max_repair_attempts=1,
    )

    assert report["passed"] is False
    assert report["stages"] == [
        {
            "stage": "generate",
            "status": "failed",
            "error_type": "RoadmapProviderError",
            "diagnostic_code": "provider_error",
        }
    ]
    assert "simulated provider outage" not in str(report)
