import logging
from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic, perf_counter, sleep
from typing import Protocol

from app.ai.providers.base import ProviderResult, RoadmapProvider, RoadmapProviderError
from app.ai.quality import combine_quality, evaluate_structure
from app.ai.schema import (
    MilestoneStepDetails,
    ProviderCritique,
    QualityIssue,
    QualityReport,
    RoadmapDraft,
    RoadmapDraftMilestone,
    RoadmapDraftStep,
    RoadmapGenerationInput,
    RoadmapOutline,
)


@dataclass(frozen=True)
class GenerationOutcome:
    draft: RoadmapDraft
    quality: QualityReport
    provider: str
    model: str
    prompt_version: str
    response_ids: tuple[str, ...]
    input_tokens: int
    output_tokens: int
    duration_ms: int


class RoadmapQualityError(RuntimeError):
    def __init__(self, report: QualityReport) -> None:
        super().__init__("The generated roadmap did not pass the quality contract")
        self.report = report


class RoadmapGenerationService:
    def __init__(
        self,
        provider: RoadmapProvider,
        quality_threshold: int = 80,
        max_repair_attempts: int = 1,
    ) -> None:
        self.provider = provider
        self.quality_threshold = quality_threshold
        self.max_repair_attempts = max_repair_attempts

    def generate(self, generation_input: RoadmapGenerationInput) -> GenerationOutcome:
        started = perf_counter()
        response_ids: list[str] = []
        input_tokens = 0
        output_tokens = 0

        generated = self.provider.generate(generation_input)
        input_tokens, output_tokens = self._record_usage(
            generated,
            response_ids,
            input_tokens,
            output_tokens,
        )
        draft = generated.value

        for repair_attempts in range(self.max_repair_attempts + 1):
            structural_score, structural_issues = evaluate_structure(draft, generation_input)
            critiqued = self.provider.critique(generation_input, draft)
            input_tokens, output_tokens = self._record_usage(
                critiqued,
                response_ids,
                input_tokens,
                output_tokens,
            )
            report = combine_quality(
                structural_score=structural_score,
                structural_issues=structural_issues,
                critique=critiqued.value,
                repair_attempts=repair_attempts,
                threshold=self.quality_threshold,
            )
            if report.passed:
                return GenerationOutcome(
                    draft=draft,
                    quality=report,
                    provider=self.provider.source,
                    model=self.provider.model,
                    prompt_version=self.provider.prompt_version,
                    response_ids=tuple(response_ids),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    duration_ms=round((perf_counter() - started) * 1000),
                )
            if repair_attempts >= self.max_repair_attempts:
                raise RoadmapQualityError(report)

            repaired = self.provider.repair(generation_input, draft, report.issues)
            input_tokens, output_tokens = self._record_usage(
                repaired,
                response_ids,
                input_tokens,
                output_tokens,
            )
            draft = repaired.value

        raise AssertionError("Generation loop exited unexpectedly")

    @staticmethod
    def _record_usage(
        result: ProviderResult[object],
        response_ids: list[str],
        input_tokens: int,
        output_tokens: int,
    ) -> tuple[int, int]:
        if result.response_id:
            response_ids.append(result.response_id)
        return input_tokens + result.input_tokens, output_tokens + result.output_tokens


class RetryingRoadmapGenerationService:
    """Retry only bounded, transient provider capacity failures in strict live mode."""

    def __init__(
        self,
        primary: RoadmapGenerationService,
        *,
        max_transient_retries: int,
        retry_delay_seconds: float,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        self.primary = primary
        self.max_transient_retries = max_transient_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.sleeper = sleeper

    @property
    def provider(self) -> RoadmapProvider:
        return self.primary.provider

    def generate(self, generation_input: RoadmapGenerationInput) -> GenerationOutcome:
        for attempt in range(self.max_transient_retries + 1):
            try:
                return self.primary.generate(generation_input)
            except RoadmapProviderError as error:
                if (
                    not self._is_transient_capacity_error(error)
                    or attempt >= self.max_transient_retries
                ):
                    raise
                delay = self.retry_delay_seconds * (attempt + 1)
                logger.warning(
                    "Retrying transient roadmap provider failure attempt=%s delay_seconds=%s "
                    "failure_code=%s",
                    attempt + 1,
                    round(delay, 2),
                    error.diagnostic_code,
                )
                self.sleeper(delay)
        raise AssertionError("Transient retry loop exited unexpectedly")

    @staticmethod
    def _is_transient_capacity_error(error: RoadmapProviderError) -> bool:
        diagnostic = error.diagnostic_code.casefold()
        transient_statuses = (
            "status_code=429",
            "status_code=500",
            "status_code=502",
            "status_code=503",
            "status_code=504",
        )
        transient_errors = ("apiconnectionerror", "apitimeouterror", "timeout")
        return (
            "code=rate_limit_exceeded" in diagnostic
            or any(status in diagnostic for status in transient_statuses)
            or any(error_type in diagnostic for error_type in transient_errors)
        )


logger = logging.getLogger(__name__)


class FallbackRoadmapGenerationService:
    """Run the live provider first and preserve availability with a vetted fixture."""

    def __init__(
        self,
        primary: "RoadmapGenerationService | RetryingRoadmapGenerationService | StagedRoadmapGenerationService",  # noqa: E501
        fallback: RoadmapGenerationService,
    ) -> None:
        self.primary = primary
        self.fallback = fallback

    def generate(self, generation_input: RoadmapGenerationInput) -> GenerationOutcome:
        try:
            return self.primary.generate(generation_input)
        except (RoadmapProviderError, RoadmapQualityError) as error:
            diagnostic_code = getattr(error, "diagnostic_code", type(error).__name__)
            logger.warning(
                "Live roadmap generation failed; using deterministic fallback "
                "failure_type=%s failure_code=%s",
                type(error).__name__,
                diagnostic_code,
            )
            try:
                return self.fallback.generate(generation_input)
            except Exception as fallback_error:
                # The deterministic fallback is the last line of defence. If it ever fails,
                # return the friendly "temporarily unavailable" response instead of a 500.
                logger.error(
                    "Deterministic roadmap fallback failed failure_type=%s",
                    type(fallback_error).__name__,
                )
                raise RoadmapProviderError(
                    "Deterministic fallback failed",
                    diagnostic_code=f"stage=fallback;{type(fallback_error).__name__}",
                ) from fallback_error


class StagedRoadmapProvider(Protocol):
    source: str
    model: str
    prompt_version: str
    deadline: float | None

    def generate_outline(self, generation_input: RoadmapGenerationInput) -> ProviderResult: ...

    def critique_outline(
        self, generation_input: RoadmapGenerationInput, outline: RoadmapOutline
    ) -> ProviderResult: ...

    def repair_outline(
        self,
        generation_input: RoadmapGenerationInput,
        outline: RoadmapOutline,
        issues: list[QualityIssue],
    ) -> ProviderResult: ...

    def expand_milestone(
        self,
        generation_input: RoadmapGenerationInput,
        outline: RoadmapOutline,
        milestone_index: int,
        issues: list[QualityIssue] = ...,
        step_keys: list[str] | None = ...,
    ) -> ProviderResult: ...


# Checks that only need the path's shape, so they can run on the outline before any details.
OUTLINE_CHECK_CODES = {
    "too_few_steps",
    "too_many_steps",
    "too_few_capability_phases",
    "thin_milestone",
    "duplicate_step_key",
    "duplicate_step_title",
    "missing_practice",
    "missing_prove",
    "unknown_prerequisite",
    "forward_prerequisite",
    "weak_personalization",
    "missing_curriculum_capability",
    "curriculum_prerequisite_order",
}


def outline_as_draft(outline: RoadmapOutline) -> RoadmapDraft:
    """A placeholder draft (objective stands in for every text field) for shape checks."""
    return RoadmapDraft(
        **outline.model_dump(exclude={"milestones"}),
        milestones=[
            RoadmapDraftMilestone(
                **milestone.model_dump(exclude={"steps"}),
                rationale=milestone.outcome,
                focus_areas=[milestone.title, milestone.proof_target],
                success_signal=milestone.proof_target,
                steps=[
                    RoadmapDraftStep(
                        **step.model_dump(),
                        rationale=step.objective,
                        action=f"Work toward this: {step.objective}",
                        completion_condition=step.objective,
                        effort_label="Several focused sessions",
                        evidence_suggestion=step.title,
                        resource_queries=[],
                    )
                    for step in milestone.steps
                ],
            )
            for milestone in outline.milestones
        ],
    )


def evaluate_outline(
    outline: RoadmapOutline, generation_input: RoadmapGenerationInput
) -> tuple[int, list[QualityIssue]]:
    _, issues = evaluate_structure(outline_as_draft(outline), generation_input)
    kept = [item for item in issues if item.code in OUTLINE_CHECK_CODES]
    return max(0, 100 - sum(14 if i.severity == "error" else 5 for i in kept)), kept


# The accepted outline already passed this check, and detail calls can't reorder steps. On
# full step text it misfires: an early step that merely mentions a later topic ("you'll deploy
# this later") makes that topic look like it comes before its prerequisites.
OUTLINE_ONLY_CODES = {"curriculum_prerequisite_order"}


def evaluate_detailed_draft(
    draft: RoadmapDraft, generation_input: RoadmapGenerationInput
) -> tuple[int, list[QualityIssue]]:
    _, issues = evaluate_structure(draft, generation_input)
    kept = [item for item in issues if item.code not in OUTLINE_ONLY_CODES]
    return max(0, 100 - sum(14 if i.severity == "error" else 5 for i in kept)), kept


def assemble_draft(
    outline: RoadmapOutline, details: dict[int, MilestoneStepDetails]
) -> RoadmapDraft:
    """Outline decides each step's key, kind, title and order; expansion supplies the rest."""
    milestones = []
    for index, milestone in enumerate(outline.milestones):
        by_key = {detail.stable_key: detail for detail in details[index].steps}
        milestones.append(
            RoadmapDraftMilestone(
                **milestone.model_dump(exclude={"steps"}),
                rationale=details[index].rationale,
                focus_areas=details[index].focus_areas,
                success_signal=details[index].success_signal,
                steps=[
                    RoadmapDraftStep(
                        stable_key=step.stable_key,
                        kind=step.kind,
                        title=step.title,
                        prerequisite_step_keys=step.prerequisite_step_keys,
                        **by_key[step.stable_key].model_dump(exclude={"stable_key"}),
                    )
                    for step in milestone.steps
                ],
            )
        )
    return RoadmapDraft(**outline.model_dump(exclude={"milestones"}), milestones=milestones)


def milestone_of_issue(issue: QualityIssue, outline: RoadmapOutline) -> int | None:
    """Map a step- or milestone-level issue to its milestone; None for whole-roadmap issues."""
    path = issue.path
    if path.startswith("steps."):
        key = path.split(".")[1]
        for index, milestone in enumerate(outline.milestones):
            if any(step.stable_key == key for step in milestone.steps):
                return index
    if path.startswith("milestones.") and path.split(".")[1].isdigit():
        index = int(path.split(".")[1]) - 1
        return index if 0 <= index < len(outline.milestones) else None
    return None


class StagedRoadmapGenerationService:
    """Build a roadmap in small calls so no single answer hits a free-tier output cap.

    1. Outline the whole path (milestones + step titles), check and critique it, repair once.
    2. Write full step details one milestone at a time.
    3. Check the assembled roadmap; regenerate only the milestones with problems.
    Every call shares one time budget; running out raises, and the caller falls back.
    """

    def __init__(
        self,
        provider: StagedRoadmapProvider,
        quality_threshold: int = 80,
        max_repair_attempts: int = 1,
        time_budget_seconds: float = 150.0,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.provider = provider
        self.quality_threshold = quality_threshold
        self.max_repair_attempts = max_repair_attempts
        self.time_budget_seconds = time_budget_seconds
        self.clock = clock

    def generate(self, generation_input: RoadmapGenerationInput) -> GenerationOutcome:
        started = perf_counter()
        self._response_ids: list[str] = []
        self._tokens = [0, 0]
        self.provider.deadline = self.clock() + self.time_budget_seconds
        try:
            outline, critique, repairs = self._accepted_outline(generation_input)
            draft, repairs = self._detailed_draft(generation_input, outline, critique, repairs)
        finally:
            self.provider.deadline = None
        score, issues = evaluate_detailed_draft(draft, generation_input)
        report = combine_quality(
            structural_score=score,
            structural_issues=issues,
            critique=critique,
            repair_attempts=repairs,
            threshold=self.quality_threshold,
        )
        if not report.passed:
            raise RoadmapQualityError(report)
        return GenerationOutcome(
            draft=draft,
            quality=report,
            provider=self.provider.source,
            model=self.provider.model,
            prompt_version=f"{self.provider.prompt_version}+staged",
            response_ids=tuple(self._response_ids),
            input_tokens=self._tokens[0],
            output_tokens=self._tokens[1],
            duration_ms=round((perf_counter() - started) * 1000),
        )

    def _record(self, result: ProviderResult):
        if result.response_id:
            self._response_ids.append(result.response_id)
        self._tokens[0] += result.input_tokens
        self._tokens[1] += result.output_tokens
        return result.value

    def _accepted_outline(
        self, generation_input: RoadmapGenerationInput
    ) -> tuple[RoadmapOutline, ProviderCritique, int]:
        outline = self._record(self.provider.generate_outline(generation_input))
        for attempt in range(self.max_repair_attempts + 1):
            score, issues = evaluate_outline(outline, generation_input)
            critique = self._record(self.provider.critique_outline(generation_input, outline))
            report = combine_quality(
                structural_score=score,
                structural_issues=issues,
                critique=critique,
                repair_attempts=attempt,
                threshold=self.quality_threshold,
            )
            if report.passed:
                return outline, critique, attempt
            if attempt >= self.max_repair_attempts:
                raise RoadmapQualityError(report)
            outline = self._record(
                self.provider.repair_outline(generation_input, outline, report.issues)
            )
        raise AssertionError("Outline loop exited unexpectedly")

    def _expand(
        self,
        generation_input: RoadmapGenerationInput,
        outline: RoadmapOutline,
        index: int,
        issues: list[QualityIssue],
        step_keys: list[str] | None = None,
    ) -> MilestoneStepDetails:
        expected = step_keys or [step.stable_key for step in outline.milestones[index].steps]
        for _attempt in range(2):
            details = self._record(
                self.provider.expand_milestone(
                    generation_input, outline, index, issues, step_keys=step_keys
                )
            )
            missing = [key for key in expected if key not in {d.stable_key for d in details.steps}]
            if not missing:
                return details
            issues = [
                *issues,
                QualityIssue(
                    severity="error",
                    code="missing_step_details",
                    message=f"No details were returned for: {', '.join(missing)}.",
                    path=f"milestones.{index + 1}.steps",
                    repair_instruction="Return one entry for every listed stable_key.",
                ),
            ]
        raise RoadmapProviderError(
            "The roadmap provider skipped outlined steps",
            diagnostic_code=f"stage=expand;milestone={index + 1};missing_step_details",
        )

    def _expand_fitting(
        self,
        generation_input: RoadmapGenerationInput,
        outline: RoadmapOutline,
        index: int,
        issues: list[QualityIssue],
        step_keys: list[str] | None = None,
    ) -> MilestoneStepDetails:
        """Detail a milestone; if the answer runs out of room, detail each half separately."""
        keys = step_keys or [step.stable_key for step in outline.milestones[index].steps]
        try:
            return self._expand(generation_input, outline, index, issues, step_keys)
        except RoadmapProviderError as error:
            # In JSON mode Groq reports a cut-off answer as json_validate_failed, not length.
            too_long = any(
                marker in error.diagnostic_code
                for marker in ("finish_reason=length", "json_validate_failed")
            )
            if not too_long or len(keys) < 2:
                raise
        middle = len(keys) // 2
        first = self._expand_fitting(generation_input, outline, index, issues, keys[:middle])
        second = self._expand_fitting(generation_input, outline, index, issues, keys[middle:])
        return first.model_copy(update={"steps": [*first.steps, *second.steps]})

    def _detailed_draft(
        self,
        generation_input: RoadmapGenerationInput,
        outline: RoadmapOutline,
        critique: ProviderCritique,
        repairs: int,
    ) -> tuple[RoadmapDraft, int]:
        details = {
            index: self._expand_fitting(generation_input, outline, index, [])
            for index in range(len(outline.milestones))
        }
        draft = assemble_draft(outline, details)
        _, issues = evaluate_detailed_draft(draft, generation_input)
        by_milestone: dict[int, list[QualityIssue]] = {}
        for item in issues:
            index = milestone_of_issue(item, outline)
            if item.severity == "error" and index is not None:
                by_milestone.setdefault(index, []).append(item)
        # One targeted round: only milestones with step-level errors are rewritten.
        if by_milestone and self.max_repair_attempts > 0:
            for index, milestone_issues in by_milestone.items():
                details[index] = self._expand_fitting(
                    generation_input, outline, index, milestone_issues
                )
            draft = assemble_draft(outline, details)
            repairs += 1
        return draft, repairs
