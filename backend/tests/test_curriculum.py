import pytest

from app.ai.curriculum import APPLIED_AI, DATA_ENGINEERING, PYTHON_BACKEND, select_curriculum
from app.ai.providers.fixture import FixtureRoadmapProvider
from app.ai.quality import evaluate_structure
from app.ai.schema import (
    CurriculumBackbone,
    CurriculumCapability,
    CurriculumPhase,
    RoadmapGenerationInput,
)
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
    assert sum(len(milestone.steps) for milestone in outcome.draft.milestones) == (
        curriculum.capability_count * 2
    )
    assert [len(milestone.steps) for milestone in outcome.draft.milestones] == [
        len(phase.capabilities) * 2 for phase in curriculum.phases
    ]
    roadmap_text = " ".join(
        step.title for milestone in outcome.draft.milestones for step in milestone.steps
    ).casefold()
    for phase in curriculum.phases:
        for capability in phase.capabilities:
            assert capability.label.casefold() in roadmap_text
            assert f"apply {capability.label}".casefold() in roadmap_text
            assert f"validate {capability.label}".casefold() in roadmap_text


def test_fixture_roadmap_uses_capability_prerequisite_edges() -> None:
    generation_input = learner_input("Become an AI automation engineer", APPLIED_AI)
    outcome = RoadmapGenerationService(FixtureRoadmapProvider()).generate(generation_input)
    steps = {
        step.stable_key: step
        for milestone in outcome.draft.milestones
        for step in milestone.steps
    }

    for phase in APPLIED_AI.phases:
        for capability in phase.capabilities:
            if not capability.prerequisite_capability_keys:
                continue
            assert steps[f"{capability.key}-apply"].prerequisite_step_keys == [
                f"{prerequisite}-evidence"
                for prerequisite in capability.prerequisite_capability_keys
            ]


def test_curriculum_rejects_a_forward_capability_prerequisite() -> None:
    curriculum_data = PYTHON_BACKEND.model_dump()
    curriculum_data["phases"][0]["capabilities"][0]["prerequisite_capability_keys"] = [
        "web-api"
    ]

    with pytest.raises(ValueError, match="occur earlier"):
        CurriculumBackbone.model_validate(curriculum_data)


def test_fixture_preserves_a_backbone_with_a_different_phase_and_capability_shape() -> None:
    curriculum = APPLIED_AI.model_copy(deep=True)
    curriculum.phases.append(
        CurriculumPhase(
            key="integrated-delivery",
            title="Integrated delivery",
            outcome="Combine the system into one reviewable, production-minded delivery.",
            capabilities=[
                CurriculumCapability(
                    key="system-integration",
                    label="System integration",
                    topics=["interfaces", "failure handling"],
                    proof=(
                        "An integrated demonstration with documented interfaces and failure paths."
                    ),
                    coverage_terms=["integration", "interfaces"],
                )
            ],
        )
    )
    generation_input = learner_input("Become an AI automation engineer", curriculum)
    outcome = RoadmapGenerationService(FixtureRoadmapProvider()).generate(generation_input)

    assert outcome.quality.passed is True
    assert len(outcome.draft.milestones) == 5
    assert [len(milestone.steps) for milestone in outcome.draft.milestones] == [4, 4, 4, 4, 2]
    assert sum(len(milestone.steps) for milestone in outcome.draft.milestones) == 18
    assert outcome.draft.milestones[-1].title == "Integrated delivery"
    assert "system integration" in outcome.draft.milestones[-1].steps[0].title.casefold()


def test_quality_rejects_a_missing_curriculum_capability() -> None:
    curriculum = APPLIED_AI.model_copy(deep=True)
    curriculum.phases[0].capabilities[0].coverage_terms = ["missing-curriculum-token"]
    generation_input = learner_input("Become an AI automation engineer", curriculum)
    draft = FixtureRoadmapProvider().generate(generation_input).value

    score, issues = evaluate_structure(draft, generation_input)

    assert score < 100
    assert "missing_curriculum_capability" in {item.code for item in issues}
