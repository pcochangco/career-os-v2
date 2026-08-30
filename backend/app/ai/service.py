import logging
from dataclasses import dataclass
from time import perf_counter

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


logger = logging.getLogger(__name__)


class FallbackRoadmapGenerationService:
    """Run the live provider first and preserve availability with a vetted fixture."""

    def __init__(
        self,
        primary: RoadmapGenerationService,
        fallback: RoadmapGenerationService,
    ) -> None:
        self.primary = primary
        self.fallback = fallback

    def generate(self, generation_input: RoadmapGenerationInput) -> GenerationOutcome:
        try:
            return self.primary.generate(generation_input)
        except (RoadmapProviderError, RoadmapQualityError) as error:
            logger.warning(
                "Live roadmap generation failed; using deterministic fallback",
                extra={"failure_type": type(error).__name__},
            )
            return self.fallback.generate(generation_input)
