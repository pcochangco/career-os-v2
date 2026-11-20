"""A failing discovery AI (retired model, outage) must never block creating a goal."""

import pytest
from fastapi.testclient import TestClient

from app.ai.dependencies import get_discovery_service, get_goal_intent_service
from app.ai.providers.base import ProviderResult, RoadmapProviderError
from app.ai.providers.compatible import OpenAICompatibleRoadmapProvider
from app.ai.schema import GoalIntentAssessment
from app.core.config import Settings
from app.discovery.service import (
    AdaptiveDiscoveryService,
    FallbackDiscoveryService,
    FixtureDiscoveryProvider,
)
from app.main import app

RETIRED = (
    "stage=discovery;model=qwen/qwen3.6-27b;NotFoundError;status_code=404;code=model_not_found"
)


class RetiredModelProvider:
    source = "groq"
    model = "openai/gpt-oss-120b"

    def assess_goal(self, *, goal_title):
        raise RoadmapProviderError("model gone", diagnostic_code=RETIRED)

    def next_question(self, **kwargs):
        raise RoadmapProviderError("model gone", diagnostic_code=RETIRED)


def fallback_service() -> FallbackDiscoveryService:
    return FallbackDiscoveryService(
        AdaptiveDiscoveryService(RetiredModelProvider()),
        AdaptiveDiscoveryService(FixtureDiscoveryProvider()),
    )


def test_goal_check_and_questions_fall_back_when_the_ai_fails() -> None:
    service = fallback_service()
    assessment = service.assess_goal(goal_title="Learn conversational Spanish")
    assert assessment.value.is_meaningful
    question = service.next_question(
        goal_title="Learn conversational Spanish", answers=[], used_question_keys=[]
    )
    assert question.value.question_key == "focus-area"


def test_creating_a_goal_works_while_the_discovery_ai_is_down(client: TestClient) -> None:
    app.dependency_overrides[get_goal_intent_service] = fallback_service
    app.dependency_overrides[get_discovery_service] = fallback_service
    token = client.post("/api/v1/auth/anonymous").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post("/api/v1/goals", headers=headers, json={"title": "Run my first marathon"})

    assert created.status_code == 201
    started = client.post(
        f"/api/v1/goals/{created.json()['id']}/discovery/questions/next", headers=headers
    )
    assert started.status_code == 200
    assert started.json()["question"]["options"]


@pytest.mark.parametrize(
    ("mode", "expected"), [("auto", FallbackDiscoveryService), ("live", AdaptiveDiscoveryService)]
)
def test_only_auto_mode_falls_back(
    monkeypatch: pytest.MonkeyPatch, mode: str, expected: type
) -> None:
    settings = Settings(ai_mode=mode, ai_provider="groq", ai_api_key="server-secret")
    monkeypatch.setattr("app.ai.dependencies.get_settings", lambda: settings)
    assert type(get_discovery_service()) is expected


def test_a_retired_stage_model_is_retried_with_the_main_model() -> None:
    requests: list[dict] = []

    class ModelNotFound(ValueError):
        status_code = 404
        code = "model_not_found"

    class Message:
        refusal = None
        content = GoalIntentAssessment(
            is_meaningful=True, normalized_title="Run a marathon", reason="meaningful"
        ).model_dump_json()

    class Choice:
        finish_reason = "stop"
        message = Message()

    class Completion:
        choices = [Choice()]
        usage = None
        id = "ok"

    class Completions:
        def create(self, **kwargs):
            requests.append(kwargs)
            if kwargs["model"] == "qwen/qwen3.6-27b":
                raise ModelNotFound("The model does not exist")
            return Completion()

    class Client:
        class chat:  # noqa: N801
            completions = Completions()

    provider = OpenAICompatibleRoadmapProvider(
        provider_name="groq",
        api_key="unused",
        base_url="https://api.groq.com/openai/v1",
        model="openai/gpt-oss-120b",
        discovery_model="qwen/qwen3.6-27b",
        response_format_mode="json_object",
        client=Client(),
    )
    result = provider.assess_goal(goal_title="run a marathon")

    assert isinstance(result, ProviderResult) and result.value.is_meaningful
    assert [r["model"] for r in requests] == ["qwen/qwen3.6-27b", "openai/gpt-oss-120b"]
