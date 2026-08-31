from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.ai.dependencies import get_discovery_service
from app.ai.providers.base import ProviderResult
from app.ai.schema import DiscoveryContextAnswer, DiscoveryQuestionDraft
from app.discovery.service import (
    AdaptiveDiscoveryService,
    DiscoveryValidationError,
    FixtureDiscoveryProvider,
)
from app.main import app


def create_session(client: TestClient) -> str:
    response = client.post("/api/v1/auth/anonymous")
    assert response.status_code == 201
    return response.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_adaptive_discovery_persists_answers_skips_and_generates_roadmap(
    client: TestClient,
) -> None:
    token = create_session(client)
    headers = auth(token)
    goal = client.post(
        "/api/v1/goals",
        headers=headers,
        json={"title": "Become an AI automation engineer"},
    ).json()

    started = client.post(
        f"/api/v1/goals/{goal['id']}/discovery/questions/next",
        headers=headers,
    )
    assert started.status_code == 200
    first_question = started.json()["question"]
    assert first_question["question_key"] == "focus-area"
    assert first_question["selection_mode"] == "multiple"
    assert len(first_question["options"]) >= 3

    reloaded = client.get(f"/api/v1/goals/{goal['id']}/discovery", headers=headers)
    assert reloaded.status_code == 200
    assert reloaded.json()["question"]["id"] == first_question["id"]

    second = client.post(
        f"/api/v1/goals/{goal['id']}/discovery/questions/{first_question['id']}/answer",
        headers=headers,
        json={
            "selected_option_keys": ["practical-project", "career-change"],
            "custom_answer": "I want to focus on agent reliability.",
        },
    )
    assert second.status_code == 200
    second_question = second.json()["question"]
    assert second_question["question_key"] == "starting-point"

    third = client.post(
        f"/api/v1/goals/{goal['id']}/discovery/questions/{second_question['id']}/answer",
        headers=headers,
        json={"skipped": True},
    )
    assert third.status_code == 200
    third_question = third.json()["question"]
    assert third_question["question_key"] == "biggest-gap"

    ready = client.post(
        f"/api/v1/goals/{goal['id']}/discovery/questions/{third_question['id']}/answer",
        headers=headers,
        json={"selected_option_keys": ["proof"]},
    )
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    assert len(ready.json()["context_summary"]) == 3
    assert "Skipped" in ready.json()["context_summary"][1]

    generated = client.post(f"/api/v1/goals/{goal['id']}/roadmaps", headers=headers)
    assert generated.status_code == 201
    assert generated.json()["quality_report"]["passed"] is True


def test_adaptive_discovery_validates_answer_options_and_allows_multiple_choices(
    client: TestClient,
) -> None:
    token = create_session(client)
    headers = auth(token)
    goal = client.post(
        "/api/v1/goals",
        headers=headers,
        json={"title": "Learn production API design"},
    ).json()
    first_question = client.post(
        f"/api/v1/goals/{goal['id']}/discovery/questions/next", headers=headers
    ).json()["question"]

    unknown = client.post(
        f"/api/v1/goals/{goal['id']}/discovery/questions/{first_question['id']}/answer",
        headers=headers,
        json={"selected_option_keys": ["not-an-option"]},
    )
    assert unknown.status_code == 422

    second_question = client.post(
        f"/api/v1/goals/{goal['id']}/discovery/questions/{first_question['id']}/answer",
        headers=headers,
        json={"selected_option_keys": ["practical-project"]},
    ).json()["question"]
    third_question = client.post(
        f"/api/v1/goals/{goal['id']}/discovery/questions/{second_question['id']}/answer",
        headers=headers,
        json={"selected_option_keys": ["work-experience"]},
    ).json()["question"]
    assert third_question["selection_mode"] == "multiple"

    multiple = client.post(
        f"/api/v1/goals/{goal['id']}/discovery/questions/{third_question['id']}/answer",
        headers=headers,
        json={"selected_option_keys": ["proof", "confidence"]},
    )
    assert multiple.status_code == 200
    assert multiple.json()["status"] == "ready"


def test_first_discovery_turn_applies_the_suggested_goal_title(client: TestClient) -> None:
    class TitleProvider:
        def next_question(self, **kwargs):
            del kwargs
            return ProviderResult(
                value=DiscoveryQuestionDraft(
                    is_complete=False,
                    suggested_goal_title="Become an AI Automation Engineer",
                    question_key="focus-area",
                    question="Which part of this goal matters most to you right now?",
                    help_text="Choose every direction that would make the roadmap useful.",
                    options=[
                        {"key": "projects", "label": "Practical projects"},
                        {"key": "roles", "label": "Career roles"},
                        {"key": "skills", "label": "Technical skills"},
                    ],
                )
            )

    app.dependency_overrides[get_discovery_service] = lambda: AdaptiveDiscoveryService(
        TitleProvider()
    )
    token = create_session(client)
    headers = auth(token)
    goal = client.post(
        "/api/v1/goals", headers=headers, json={"title": "become ai automation engineer"}
    ).json()

    response = client.post(
        f"/api/v1/goals/{goal['id']}/discovery/questions/next", headers=headers
    )
    assert response.status_code == 200
    assert response.json()["goal_title"] == "Become an AI Automation Engineer"
    assert client.get(f"/api/v1/goals/{goal['id']}", headers=headers).json()["title"] == (
        "Become an AI Automation Engineer"
    )


def test_discovery_service_rejects_early_or_repeated_provider_questions() -> None:
    class EarlyProvider:
        def next_question(self, **kwargs):
            del kwargs
            from app.ai.providers.base import ProviderResult
            from app.ai.schema import DiscoveryQuestionDraft

            return ProviderResult(value=DiscoveryQuestionDraft(is_complete=True))

    service = AdaptiveDiscoveryService(EarlyProvider())
    try:
        service.next_question(goal_title="Learn something", answers=[], used_question_keys=[])
    except DiscoveryValidationError:
        pass
    else:
        raise AssertionError("An early completion must be rejected")

    fixture = AdaptiveDiscoveryService(FixtureDiscoveryProvider())
    first = fixture.next_question(
        goal_title="Learn something", answers=[], used_question_keys=[]
    ).value
    assert first.question_key == "focus-area"
    answer = DiscoveryContextAnswer(
        question_key="focus-area",
        question=first.question,
        answer="Build a practical project",
    )
    second = fixture.next_question(
        goal_title="Learn something", answers=[answer], used_question_keys=[first.question_key]
    ).value
    assert second.question_key == "starting-point"


def test_incomplete_discovery_turn_requires_an_actionable_question() -> None:
    try:
        DiscoveryQuestionDraft(is_complete=False)
    except ValidationError:
        pass
    else:
        raise AssertionError("An incomplete discovery response must not omit its question fields")
