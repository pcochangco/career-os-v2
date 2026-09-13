import pytest

from app.ai.curriculum import APPLIED_AI, DATA_ENGINEERING, PYTHON_BACKEND, select_curriculum
from app.ai.providers.fixture import FixtureRoadmapProvider
from app.ai.quality import evaluate_structure
from app.ai.schema import RoadmapGenerationInput
from app.ai.service import RoadmapGenerationService


def learner_input(goal_title: str, curriculum) -> RoadmapGenerationInput:
    return RoadmapGenerationInput(
        goal_title=goal_title,
        desired_outcome=f"Become effective at {goal_title}",
        current_level="An experienced engineer with relevant programming foundations",
        existing_experience="Python, APIs, tests, and production support",
        relevant_constraints="Prefer practical work that leads to a reviewable portfolio artifact",
        proof_of_completion=(
            "A deployed project, evaluation evidence, and an engineering case study"
        ),
        curriculum=curriculum,
    )


@pytest.mark.parametrize(
    ("goal_title", "expected"),
    [
        ("Become an AI automation engineer", APPLIED_AI.key),
        ("Move into data engineering", DATA_ENGINEERING.key),
        ("Become a Python backend engineer", PYTHON_BACKEND.key),
        ("Reach conversational Spanish", None),
    ],
)
def test_curriculum_matching_only_activates_for_supported_tracks(
    goal_title: str, expected: str | None
) -> None:
    selected = select_curriculum(goal_title)

    assert (selected.key if selected else None) == expected


@pytest.mark.parametrize(
    ("goal_title", "curriculum"),
    [
        ("Become an AI automation engineer", APPLIED_AI),
        ("Move into data engineering", DATA_ENGINEERING),
        ("Become a Python backend engineer", PYTHON_BACKEND),
    ],
)
def test_fixture_roadmap_covers_the_selected_curriculum(goal_title: str, curriculum) -> None:
    generation_input = learner_input(goal_title, curriculum)
    outcome = RoadmapGenerationService(FixtureRoadmapProvider()).generate(generation_input)

    assert outcome.quality.passed is True
    assert [milestone.title for milestone in outcome.draft.milestones] == [
        phase.title for phase in curriculum.phases
    ]
    roadmap_text = " ".join(
        step.title for milestone in outcome.draft.milestones for step in milestone.steps
    ).casefold()
    for phase in curriculum.phases:
        for capability in phase.capabilities:
            assert capability.label.casefold() in roadmap_text


def test_quality_rejects_a_missing_curriculum_capability() -> None:
    curriculum = APPLIED_AI.model_copy(deep=True)
    curriculum.phases[0].capabilities[0].coverage_terms = ["missing-curriculum-token"]
    generation_input = learner_input("Become an AI automation engineer", curriculum)
    draft = FixtureRoadmapProvider().generate(generation_input).value

    score, issues = evaluate_structure(draft, generation_input)

    assert score < 100
    assert "missing_curriculum_capability" in {item.code for item in issues}
