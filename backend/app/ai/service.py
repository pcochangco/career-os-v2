import logging
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter, sleep

from app.ai.providers.base import ProviderResult, RoadmapProvider, RoadmapProviderError
from app.ai.quality import combine_quality, evaluate_structure
from app.ai.schema import QualityReport, RoadmapDraft, RoadmapGenerationInput


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
        diagnostic = error.diagnostic_code
        return "code=rate_limit_exceeded" in diagnostic or "status_code=429" in diagnostic


logger = logging.getLogger(__name__)


class FallbackRoadmapGenerationService:
    """Run the live provider first and preserve availability with a vetted fixture."""

    def __init__(
        self,
        primary: RoadmapGenerationService | RetryingRoadmapGenerationService,
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
            return self.fallback.generate(generation_input)
