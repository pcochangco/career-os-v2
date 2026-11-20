import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.ai.dependencies import get_discovery_service
from app.ai.providers.base import ProviderResult
from app.ai.providers.fixture import read_answers
from app.ai.schema import DiscoveryContextAnswer, DiscoveryQuestionDraft
from app.discovery.service import (
    FALLBACK_OPTIONS,
    FALLBACK_QUESTIONS,
    AdaptiveDiscoveryService,
    DiscoveryValidationError,
    FixtureDiscoveryProvider,
    deduplicate_context,
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
    assert started.json()["answered_questions"] == 0
    assert started.json()["minimum_questions"] == 3
    assert started.json()["maximum_questions"] == 6

    reloaded = client.get(f"/api/v1/goals/{goal['id']}/discovery", headers=headers)
    assert reloaded.status_code == 200
    assert reloaded.json()["question"]["id"] == first_question["id"]

    second = client.post(
        f"/api/v1/goals/{goal['id']}/discovery/questions/{first_question['id']}/answer",
        headers=headers,
        json={
            "selected_option_keys": ["build-a-practical-project", "prepare-for-a-career-move"],
            "custom_answer": "I want to focus on agent reliability.",
        },
    )
    assert second.status_code == 200
    second_question = second.json()["question"]
    assert second_question["question_key"] == "starting-point"
    assert second.json()["answered_questions"] == 1

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
        json={"selected_option_keys": ["creating-strong-proof-of-my-skills"]},
    )
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    assert ready.json()["answered_questions"] == 3
    assert len(ready.json()["context_summary"]) == 3
    assert "Skipped" in ready.json()["context_summary"][1]
    assert ready.json()["context"][1]["skipped"] is True
    assert len(ready.json()["context"]) == 3

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
        json={"selected_option_keys": ["build-a-practical-project"]},
    ).json()["question"]
    third_question = client.post(
        f"/api/v1/goals/{goal['id']}/discovery/questions/{second_question['id']}/answer",
        headers=headers,
        json={"selected_option_keys": ["used-it-at-work"]},
    ).json()["question"]
    assert third_question["selection_mode"] == "multiple"

    multiple = client.post(
        f"/api/v1/goals/{goal['id']}/discovery/questions/{third_question['id']}/answer",
        headers=headers,
        json={
            "selected_option_keys": [
                "creating-strong-proof-of-my-skills",
                "confidence-explaining-my-work",
            ]
        },
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

    response = client.post(f"/api/v1/goals/{goal['id']}/discovery/questions/next", headers=headers)
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


def test_discovery_stops_after_six_answers_even_if_provider_wants_more() -> None:
    class NeverFinishedProvider:
        def next_question(self, **kwargs):
            position = len(kwargs["answers"]) + 1
            return ProviderResult(
                value=DiscoveryQuestionDraft(
                    is_complete=False,
                    question_key=f"question-{position}",
                    question="Which direction would help you make meaningful progress?",
                    help_text="Choose the options that best describe what you need.",
                    options=[
                        {"key": "practice", "label": "More practice"},
                        {"key": "guidance", "label": "Clear guidance"},
                        {"key": "evidence", "label": "Stronger evidence"},
                    ],
                )
            )

    answers = [
        DiscoveryContextAnswer(
            question_key=f"question-{position}",
            question="Which direction would help you make meaningful progress?",
            answer="More practice",
        )
        for position in range(1, 7)
    ]
    result = AdaptiveDiscoveryService(NeverFinishedProvider()).next_question(
        goal_title="Build a portfolio",
        answers=answers,
        used_question_keys=[answer.question_key for answer in answers],
    )

    assert result.value.is_complete is True


def test_discovery_stops_on_a_semantic_repeat_and_keeps_the_useful_answer() -> None:
    class RepeatingProvider:
        def next_question(self, **kwargs):
            del kwargs
            return ProviderResult(
                value=DiscoveryQuestionDraft(
                    is_complete=False,
                    question_key="field-again",
                    question=(
                        "Which academic field or discipline do you plan to pursue for the "
                        "scholarship?"
                    ),
                    help_text="Choose the field that best matches your intended course.",
                    options=[
                        {"key": "stem", "label": "STEM"},
                        {"key": "business", "label": "Business"},
                        {"key": "arts", "label": "Arts and humanities"},
                    ],
                )
            )

    answers = [
        DiscoveryContextAnswer(
            question_key="scholarship-type",
            question="What type of scholarship are you targeting?",
            answer="Graduate",
        ),
        DiscoveryContextAnswer(
            question_key="academic-field",
            question=(
                "Which academic field or discipline are you planning to pursue for the scholarship?"
            ),
            answer="Skipped",
            skipped=True,
        ),
        DiscoveryContextAnswer(
            question_key="experience",
            question="What research or project experience do you already have?",
            answer="No experience",
        ),
    ]

    result = AdaptiveDiscoveryService(RepeatingProvider()).next_question(
        goal_title="University scholarship in Europe",
        answers=answers,
        used_question_keys=[answer.question_key for answer in answers],
    )
    assert result.value.is_complete is True

    context = deduplicate_context(
        [
            *answers,
            DiscoveryContextAnswer(
                question_key="field-again",
                question=(
                    "Which academic field or discipline do you plan to pursue for the scholarship?"
                ),
                answer="STEM",
            ),
        ]
    )
    assert len(context) == 3
    assert context[1].answer == "STEM"
    assert context[1].skipped is False


def test_incomplete_discovery_turn_requires_an_actionable_question() -> None:
    try:
        DiscoveryQuestionDraft(is_complete=False)
    except ValidationError:
        pass
    else:
        raise AssertionError("An incomplete discovery response must not omit its question fields")


def test_skipping_every_question_is_explained_honestly(client: TestClient) -> None:
    headers = auth(create_session(client))
    goal = client.post(
        "/api/v1/goals", headers=headers, json={"title": "Learn conversational Spanish"}
    ).json()
    state = client.post(
        f"/api/v1/goals/{goal['id']}/discovery/questions/next", headers=headers
    ).json()
    while state["status"] != "ready":
        state = client.post(
            f"/api/v1/goals/{goal['id']}/discovery/questions/{state['question']['id']}/answer",
            headers=headers,
            json={"skipped": True},
        ).json()

    assert all(item["skipped"] for item in state["context"])
    assert "skipped the questions" in state["completion_reason"]


@pytest.mark.parametrize(
    ("goal_title", "expected", "unexpected"),
    [
        ("Run my first marathon", "Finish an event or race", "career"),
        ("Speak conversational Spanish", "Hold everyday conversations", "career"),
        ("Learn watercolour painting", "Find my own style", "career"),
        ("Open a coffee shop", "Win my first customers", "career"),
        ("Learn to cook", "Learn the basics properly", "career"),
        ("Become a Python developer", "Prepare for a career move", "race"),
    ],
)
def test_fallback_questions_match_the_goal_topic(
    goal_title: str, expected: str, unexpected: str
) -> None:
    fixture = FixtureDiscoveryProvider()
    answers: list[DiscoveryContextAnswer] = []
    labels: list[str] = []
    while not (
        question := fixture.next_question(
            goal_title=goal_title, answers=answers, used_question_keys=[]
        ).value
    ).is_complete:
        AdaptiveDiscoveryService._validate_question(question, [a.question_key for a in answers])
        labels += [option.label for option in question.options]
        answers.append(
            DiscoveryContextAnswer(
                question_key=question.question_key,
                question=question.question,
                answer=question.options[0].label,
            )
        )
    assert len(answers) == 3
    assert expected in labels
    assert not any(unexpected in label.casefold() for label in labels)


@pytest.mark.parametrize("domain", sorted(FALLBACK_OPTIONS))
def test_fallback_starting_point_options_reveal_the_level(domain: str) -> None:
    question = FALLBACK_QUESTIONS[1][1]
    levels = {
        read_answers(
            [DiscoveryContextAnswer(question_key="starting-point", question=question, answer=label)]
        )["level"]
        for label in FALLBACK_OPTIONS[domain]["starting-point"]
    }
    assert {"beginner", "experienced"} <= levels
