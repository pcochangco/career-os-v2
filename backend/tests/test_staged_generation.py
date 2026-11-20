"""Staged roadmap generation: outline first, then one small call per milestone."""

import json

import pytest

from app.ai.dependencies import create_generation_service
from app.ai.providers.base import ProviderResult, RoadmapProviderError
from app.ai.providers.compatible import OpenAICompatibleRoadmapProvider
from app.ai.providers.fixture import FixtureRoadmapProvider
from app.ai.schema import (
    MilestoneStepDetails,
    ProviderCritique,
    RoadmapDraft,
    RoadmapGenerationInput,
    RoadmapOutline,
    RoadmapOutlineMilestone,
    RoadmapOutlineStep,
    RoadmapStepDetail,
)
from app.ai.service import (
    FallbackRoadmapGenerationService,
    RetryingRoadmapGenerationService,
    RoadmapQualityError,
    StagedRoadmapGenerationService,
)
from app.core.config import Settings

DETAIL_FIELDS = set(RoadmapStepDetail.model_fields)


def learner_input() -> RoadmapGenerationInput:
    return RoadmapGenerationInput(
        goal_title="Build an AI automation system",
        desired_outcome="Deploy and evaluate a reliable AI automation workflow",
        current_level="Experienced Python automation engineer",
        existing_experience="Python, APIs, RAG, and LLM integrations",
        relevant_constraints="Prefer practical work and concise explanations",
        proof_of_completion="A deployed system with an evaluation report",
    )


def split(draft: RoadmapDraft) -> tuple[RoadmapOutline, list[MilestoneStepDetails]]:
    outline = RoadmapOutline(
        **draft.model_dump(exclude={"milestones"}),
        milestones=[
            RoadmapOutlineMilestone(
                **milestone.model_dump(exclude={"steps"}),
                steps=[
                    RoadmapOutlineStep(
                        stable_key=step.stable_key,
                        kind=step.kind,
                        title=step.title,
                        objective=step.objective[:400],
                        prerequisite_step_keys=step.prerequisite_step_keys,
                    )
                    for step in milestone.steps
                ],
            )
            for milestone in draft.milestones
        ],
    )
    details = [
        MilestoneStepDetails(
            steps=[RoadmapStepDetail(**step.model_dump(include=DETAIL_FIELDS)) for step in m.steps]
        )
        for m in draft.milestones
    ]
    return outline, details


def critique(passed: bool = True) -> ProviderCritique:
    return ProviderCritique(passed=passed, score=92 if passed else 60, summary="ok", issues=[])


class FakeStagedProvider:
    source = "groq"
    model = "openai/gpt-oss-120b"
    prompt_version = "roadmap-schema-1.0-compatible-11+roadmap-mentor@test"

    def __init__(self) -> None:
        self.draft = FixtureRoadmapProvider().generate(learner_input()).value
        self.outline, self.details = split(self.draft)
        self.deadline: float | None = None
        self.calls: list[str] = []
        self.critiques = [critique()]
        self.expansions: dict[int, list[MilestoneStepDetails]] = {}
        self.expand_issues: dict[int, list[list[str]]] = {}

    def _result(self, value):
        assert self.deadline is not None  # every call runs inside the time budget
        return ProviderResult(value=value, response_id="r", input_tokens=10, output_tokens=5)

    def generate_outline(self, generation_input):
        self.calls.append("outline")
        return self._result(self.outline)

    def critique_outline(self, generation_input, outline):
        self.calls.append("critique_outline")
        return self._result(self.critiques.pop(0) if len(self.critiques) > 1 else self.critiques[0])

    def repair_outline(self, generation_input, outline, issues):
        self.calls.append("repair_outline")
        return self._result(self.outline)

    def expand_milestone(self, generation_input, outline, milestone_index, issues=()):
        self.calls.append(f"expand{milestone_index}")
        self.expand_issues.setdefault(milestone_index, []).append([i.code for i in issues])
        queued = self.expansions.get(milestone_index)
        value = queued.pop(0) if queued else self.details[milestone_index]
        return self._result(value)


def staged(provider: FakeStagedProvider) -> StagedRoadmapGenerationService:
    return StagedRoadmapGenerationService(provider, quality_threshold=80, max_repair_attempts=1)


def test_outline_then_one_call_per_milestone_assembles_the_full_roadmap() -> None:
    provider = FakeStagedProvider()
    outcome = staged(provider).generate(learner_input())

    milestones = len(provider.outline.milestones)
    expands = [f"expand{index}" for index in range(milestones)]
    assert provider.calls == ["outline", "critique_outline", *expands]
    assert outcome.draft == provider.draft
    assert outcome.quality.passed
    assert outcome.prompt_version.endswith("+staged")
    assert outcome.input_tokens == 10 * len(provider.calls)
    assert provider.deadline is None  # the budget is cleared after the run


def test_a_failed_outline_review_is_repaired_once_before_any_details() -> None:
    provider = FakeStagedProvider()
    provider.critiques = [critique(passed=False), critique()]
    staged(provider).generate(learner_input())
    assert provider.calls[:4] == [
        "outline",
        "critique_outline",
        "repair_outline",
        "critique_outline",
    ]


def test_an_outline_that_still_fails_stops_before_spending_on_details() -> None:
    provider = FakeStagedProvider()
    provider.critiques = [critique(passed=False)]
    with pytest.raises(RoadmapQualityError):
        staged(provider).generate(learner_input())
    assert not any(call.startswith("expand") for call in provider.calls)


def test_a_milestone_that_skips_a_step_is_asked_again_for_it() -> None:
    provider = FakeStagedProvider()
    complete = provider.details[0]
    provider.expansions[0] = [MilestoneStepDetails(steps=complete.steps[:-1]), complete]

    outcome = staged(provider).generate(learner_input())

    assert provider.calls.count("expand0") == 2
    assert provider.expand_issues[0][1] == ["missing_step_details"]
    assert outcome.draft == provider.draft


def test_a_step_problem_rewrites_only_its_own_milestone() -> None:
    provider = FakeStagedProvider()
    good = provider.details[1]
    bad_step = good.steps[0].model_copy(
        update={"action": f"{good.steps[0].action} See https://example.com/guide."}
    )
    provider.expansions[1] = [MilestoneStepDetails(steps=[bad_step, *good.steps[1:]]), good]

    outcome = staged(provider).generate(learner_input())

    assert provider.calls.count("expand1") == 2
    assert provider.expand_issues[1][1] == ["unverified_url"]
    assert all(provider.calls.count(f"expand{i}") == 1 for i in (0, 2))
    assert outcome.quality.passed and outcome.quality.repair_attempts == 1


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
    id = "response"

    def __init__(self, content: str) -> None:
        self.choices = [Choice(content)]


class RateLimited(ValueError):
    status_code = 429

    class response:  # noqa: N801 - mirrors the SDK error's .response.headers
        headers = {"retry-after": "2"}


def client_returning(content: str, requests: list[dict], fail_first_with_429: bool = False):
    class Completions:
        def create(self, **kwargs: object) -> Completion:
            requests.append(kwargs)
            if fail_first_with_429 and len(requests) == 1:
                raise RateLimited("tokens per minute")
            return Completion(content)

    class Chat:
        completions = Completions()

    class Client:
        chat = Chat()

    return Client()


def provider_with(client, **kwargs) -> OpenAICompatibleRoadmapProvider:
    return OpenAICompatibleRoadmapProvider(
        provider_name="groq",
        api_key="unused-test-key",
        base_url="https://api.groq.com/openai/v1",
        model="openai/gpt-oss-120b",
        critic_model="openai/gpt-oss-20b",
        repair_model="qwen/qwen3.8-27b",
        response_format_mode="json_object",
        expand_max_completion_tokens=2500,
        client=client,
        **kwargs,
    )


def test_milestones_alternate_models_with_a_small_output_cap() -> None:
    fake = FakeStagedProvider()
    requests: list[dict] = []
    provider = provider_with(client_returning(fake.details[0].model_dump_json(), requests))

    provider.expand_milestone(learner_input(), fake.outline, 0)
    provider.expand_milestone(learner_input(), fake.outline, 1)

    assert [(r["model"], r["max_completion_tokens"]) for r in requests] == [
        ("openai/gpt-oss-120b", 2500),
        ("qwen/qwen3.8-27b", 2500),
    ]
    payload = json.loads(requests[0]["messages"][-1]["content"].split("\n", 5)[-1])
    assert payload["milestone_to_detail"]["title"] == fake.outline.milestones[0].title
    assert "objective" not in json.dumps(payload["roadmap_outline"])  # other milestones in brief


def test_rate_limits_are_waited_out_only_inside_a_time_budget() -> None:
    fake = FakeStagedProvider()
    waits: list[float] = []
    requests: list[dict] = []
    provider = provider_with(
        client_returning(fake.outline.model_dump_json(), requests, fail_first_with_429=True),
        sleeper=waits.append,
        clock=lambda: 0.0,
    )
    provider.deadline = 100.0
    assert provider.generate_outline(learner_input()).value == fake.outline
    assert waits == [2.0]

    single_mode = provider_with(
        client_returning(fake.outline.model_dump_json(), [], fail_first_with_429=True),
        sleeper=waits.append,
    )
    with pytest.raises(RoadmapProviderError):  # no budget: fail fast as before
        single_mode.generate_outline(learner_input())


def test_a_spent_time_budget_stops_the_next_call() -> None:
    provider = provider_with(client_returning("{}", []), clock=lambda: 200.0)
    provider.deadline = 150.0
    with pytest.raises(RoadmapProviderError) as error:
        provider.generate_outline(learner_input())
    assert "time_budget_exceeded" in error.value.diagnostic_code


def live_settings(**overrides: object) -> Settings:
    return Settings(ai_mode="auto", ai_provider="groq", ai_api_key="server-secret", **overrides)


def test_staged_is_the_default_and_single_stays_available() -> None:
    staged_service = create_generation_service(live_settings())
    assert isinstance(staged_service, FallbackRoadmapGenerationService)
    assert isinstance(staged_service.primary, StagedRoadmapGenerationService)

    single = create_generation_service(live_settings(ai_generation_strategy="single"))
    assert isinstance(single.primary, RetryingRoadmapGenerationService)
