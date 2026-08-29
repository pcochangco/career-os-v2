import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.ai.providers.base import ProviderResult
from app.ai.providers.fixture import FixtureRoadmapProvider
from app.ai.quality import evaluate_structure
from app.ai.schema import (
    ProviderCritique,
    QualityIssue,
    RoadmapDraft,
    RoadmapGenerationInput,
)
from app.ai.service import RoadmapGenerationService, RoadmapQualityError


def eval_inputs() -> list[RoadmapGenerationInput]:
    path = Path(__file__).parents[1] / "evals" / "cases.json"
    cases = json.loads(path.read_text())
    return [RoadmapGenerationInput.model_validate(case["input"]) for case in cases]


@pytest.mark.parametrize("generation_input", eval_inputs())
def test_fixture_passes_representative_eval_cases(
    generation_input: RoadmapGenerationInput,
) -> None:
    outcome = RoadmapGenerationService(FixtureRoadmapProvider()).generate(generation_input)

    assert outcome.quality.passed is True
    assert outcome.quality.final_score >= 80
    assert outcome.draft.schema_version == "1.0"
    assert any(
        step.kind == "prove" for milestone in outcome.draft.milestones for step in milestone.steps
    )


def base_input() -> RoadmapGenerationInput:
    return RoadmapGenerationInput(
        goal_title="Learn API system design",
        desired_outcome="Design and explain a resilient production API",
        current_level="Python backend developer",
        existing_experience="FastAPI, PostgreSQL, and Docker",
        relevant_constraints="Prefer practical architecture exercises",
        proof_of_completion="A reviewed architecture document and working API",
    )


class RepairingProvider(FixtureRoadmapProvider):
    def __init__(self, repair_succeeds: bool) -> None:
        self.repair_succeeds = repair_succeeds
        self.repair_calls = 0

    def generate(self, generation_input: RoadmapGenerationInput) -> ProviderResult[RoadmapDraft]:
        valid = super().generate(generation_input).value
        broken = deepcopy(valid)
        broken.milestones[0].steps[0].prerequisite_step_keys = ["missing-step"]
        return ProviderResult(value=broken)

    def repair(
        self,
        generation_input: RoadmapGenerationInput,
        draft: RoadmapDraft,
        issues: list[QualityIssue],
    ) -> ProviderResult[RoadmapDraft]:
        del draft, issues
        self.repair_calls += 1
        if self.repair_succeeds:
            return FixtureRoadmapProvider().generate(generation_input)
        return self.generate(generation_input)


def test_generation_repairs_a_failed_quality_check_once() -> None:
    provider = RepairingProvider(repair_succeeds=True)
    outcome = RoadmapGenerationService(provider, max_repair_attempts=1).generate(base_input())

    assert outcome.quality.passed is True
    assert outcome.quality.repair_attempts == 1
    assert provider.repair_calls == 1


def test_generation_rejects_output_that_still_fails_after_repair() -> None:
    provider = RepairingProvider(repair_succeeds=False)

    with pytest.raises(RoadmapQualityError) as captured:
        RoadmapGenerationService(provider, max_repair_attempts=1).generate(base_input())

    assert captured.value.report.passed is False
    assert provider.repair_calls == 1


def test_quality_check_rejects_schedule_and_unverified_url() -> None:
    generation_input = base_input()
    draft = FixtureRoadmapProvider().generate(generation_input).value
    draft.milestones[0].steps[
        0
    ].action = (
        "Study every day before the deadline using https://example.com and write brief notes."
    )

    score, issues = evaluate_structure(draft, generation_input)
    codes = {item.code for item in issues}

    assert score < 100
    assert "required_schedule" in codes
    assert "unverified_url" in codes


def test_critic_issue_can_drive_repair() -> None:
    issue = QualityIssue(
        severity="error",
        code="missing_intermediate_skill",
        message="The roadmap jumps over a required intermediate skill.",
        path="milestones.1",
        repair_instruction="Add one focused practice step before the proof step.",
    )
    critique = ProviderCritique(
        passed=False,
        score=70,
        summary="A prerequisite gap remains.",
        issues=[issue],
    )

    assert critique.issues[0].repair_instruction.startswith("Add one")
