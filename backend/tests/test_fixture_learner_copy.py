"""The deterministic fallback must never show model instructions to learners."""

import pytest

from app.ai.providers.fixture import FixtureRoadmapProvider
from app.ai.schema import (
    ADAPTIVE_INSTRUCTION_PREFIX,
    DiscoveryContextAnswer,
    RoadmapGenerationInput,
)


def adaptive_input(
    goal_title: str, answers: list[DiscoveryContextAnswer]
) -> RoadmapGenerationInput:
    return RoadmapGenerationInput(
        goal_title=goal_title,
        desired_outcome=f"Achieve the goal: {goal_title}",
        current_level=f"{ADAPTIVE_INSTRUCTION_PREFIX} to establish their starting point.",
        existing_experience=f"{ADAPTIVE_INSTRUCTION_PREFIX} to identify existing experience.",
        relevant_constraints=(
            f"{ADAPTIVE_INSTRUCTION_PREFIX} to identify preferences and constraints."
        ),
        proof_of_completion=(
            f"{ADAPTIVE_INSTRUCTION_PREFIX} to define convincing proof of completion."
        ),
        discovery_context=answers,
    )


SKIPPED = [
    DiscoveryContextAnswer(
        question_key="starting-point",
        question="What is your starting point right now?",
        answer="Skipped",
        skipped=True,
    )
]
ANSWERED = [
    DiscoveryContextAnswer(
        question_key="starting-point",
        question="What is your starting point right now?",
        answer="I sketch interfaces as a hobby",
    ),
    DiscoveryContextAnswer(
        question_key="constraint",
        question="What could get in the way?",
        answer="Only weekends are free",
    ),
]


def all_learner_text(generation_input: RoadmapGenerationInput) -> str:
    return FixtureRoadmapProvider().generate(generation_input).value.model_dump_json()


@pytest.mark.parametrize(
    "goal_title",
    ["Become a product designer", "Learn conversational Spanish", "Start a bakery", "Learn Python"],
)
@pytest.mark.parametrize("answers", [SKIPPED, ANSWERED], ids=["skipped", "answered"])
def test_adaptive_fallback_hides_model_instructions(goal_title, answers):
    text = all_learner_text(adaptive_input(goal_title, answers))

    assert ADAPTIVE_INSTRUCTION_PREFIX not in text
    assert "Achieve the goal:" not in text


def test_adaptive_fallback_uses_the_learners_own_answers():
    draft = FixtureRoadmapProvider().generate(
        adaptive_input("Become a product designer", ANSWERED)
    ).value

    assert "I sketch interfaces as a hobby" in draft.starting_state_summary
    assert draft.goal_outcome == "Become a product designer"


def test_adaptive_fallback_explains_skipped_discovery():
    draft = FixtureRoadmapProvider().generate(
        adaptive_input("Become a product designer", SKIPPED)
    ).value

    assert "skipped the starting questions" in draft.starting_state_summary
