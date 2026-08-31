"""Run one live roadmap through generation, critique, and repair without persistence.

The report deliberately excludes prompts, model output, user content, and API keys. It is
intended for provider debugging before an application deployment.
"""

import argparse
import json
from pathlib import Path
from time import perf_counter
from typing import Any

from app.ai.dependencies import live_service
from app.ai.providers.base import RoadmapProvider, RoadmapProviderError
from app.ai.quality import combine_quality, evaluate_structure
from app.ai.schema import QualityIssue, RoadmapGenerationInput
from app.core.config import get_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose one live roadmap without using the API or database.",
    )
    parser.add_argument(
        "--case",
        default="experienced career progression",
        help="Exact case name from evals/cases.json.",
    )
    return parser.parse_args()


def issue_summary(issue: QualityIssue) -> dict[str, str]:
    return {
        "severity": issue.severity,
        "code": issue.code,
        "path": issue.path,
        "repair_instruction": issue.repair_instruction,
    }


def provider_failure(stage: str, error: Exception) -> dict[str, object]:
    diagnostic_code = getattr(error, "diagnostic_code", type(error).__name__)
    return {
        "stage": stage,
        "status": "failed",
        "error_type": type(error).__name__,
        "diagnostic_code": diagnostic_code,
    }


def successful_provider_stage(
    stage: str,
    *,
    input_tokens: int,
    output_tokens: int,
) -> dict[str, object]:
    return {
        "stage": stage,
        "status": "passed",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def diagnose(
    provider: RoadmapProvider,
    generation_input: RoadmapGenerationInput,
    *,
    quality_threshold: int,
    max_repair_attempts: int,
) -> dict[str, Any]:
    """Exercise the production AI stages and return only bounded diagnostic metadata."""
    started = perf_counter()
    stages: list[dict[str, object]] = []
    total_input_tokens = 0
    total_output_tokens = 0

    try:
        generated = provider.generate(generation_input)
    except Exception as error:
        stages.append(provider_failure("generate", error))
        return _report(
            provider,
            passed=False,
            stages=stages,
            input_tokens=0,
            output_tokens=0,
            started=started,
        )

    total_input_tokens += generated.input_tokens
    total_output_tokens += generated.output_tokens
    stages.append(
        successful_provider_stage(
            "generate",
            input_tokens=generated.input_tokens,
            output_tokens=generated.output_tokens,
        )
    )
    draft = generated.value

    for repair_attempt in range(max_repair_attempts + 1):
        structural_score, structural_issues = evaluate_structure(draft, generation_input)
        stages.append(
            {
                "stage": "structure" if repair_attempt == 0 else "structure_after_repair",
                "status": "passed" if not structural_issues else "failed",
                "score": structural_score,
                "issues": [issue_summary(issue) for issue in structural_issues],
            }
        )

        critic_stage = "critique" if repair_attempt == 0 else "critique_after_repair"
        try:
            critiqued = provider.critique(generation_input, draft)
        except Exception as error:
            stages.append(provider_failure(critic_stage, error))
            return _report(
                provider,
                passed=False,
                stages=stages,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                started=started,
            )

        total_input_tokens += critiqued.input_tokens
        total_output_tokens += critiqued.output_tokens
        stages.append(
            {
                **successful_provider_stage(
                    critic_stage,
                    input_tokens=critiqued.input_tokens,
                    output_tokens=critiqued.output_tokens,
                ),
                "critic_passed": critiqued.value.passed,
                "score": critiqued.value.score,
                "issues": [issue_summary(issue) for issue in critiqued.value.issues],
            }
        )

        quality = combine_quality(
            structural_score=structural_score,
            structural_issues=structural_issues,
            critique=critiqued.value,
            repair_attempts=repair_attempt,
            threshold=quality_threshold,
        )
        stages.append(
            {
                "stage": "quality_gate",
                "status": "passed" if quality.passed else "failed",
                "final_score": quality.final_score,
                "structural_score": quality.structural_score,
                "critic_score": quality.critic_score,
                "repair_attempt": repair_attempt,
                "issues": [issue_summary(issue) for issue in quality.issues],
            }
        )
        if quality.passed:
            return _report(
                provider,
                passed=True,
                stages=stages,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                started=started,
            )
        if repair_attempt >= max_repair_attempts:
            return _report(
                provider,
                passed=False,
                stages=stages,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                started=started,
            )

        try:
            repaired = provider.repair(generation_input, draft, quality.issues)
        except Exception as error:
            stages.append(provider_failure("repair", error))
            return _report(
                provider,
                passed=False,
                stages=stages,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                started=started,
            )

        total_input_tokens += repaired.input_tokens
        total_output_tokens += repaired.output_tokens
        stages.append(
            successful_provider_stage(
                "repair",
                input_tokens=repaired.input_tokens,
                output_tokens=repaired.output_tokens,
            )
        )
        draft = repaired.value

    raise AssertionError("Diagnostic loop exited unexpectedly")


def _report(
    provider: RoadmapProvider,
    *,
    passed: bool,
    stages: list[dict[str, object]],
    input_tokens: int,
    output_tokens: int,
    started: float,
) -> dict[str, Any]:
    stage_models = getattr(
        provider,
        "stage_models",
        {"generate": provider.model, "critique": provider.model, "repair": provider.model},
    )
    stage_max_completion_tokens = getattr(
        provider,
        "stage_max_completion_tokens",
        None,
    )
    return {
        "passed": passed,
        "provider": provider.source,
        "model": provider.model,
        "stage_models": stage_models,
        "stage_max_completion_tokens": stage_max_completion_tokens,
        "prompt_version": provider.prompt_version,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "duration_ms": round((perf_counter() - started) * 1000),
        "stages": stages,
    }


def load_case(case_name: str) -> RoadmapGenerationInput:
    cases_path = Path(__file__).with_name("cases.json")
    cases = json.loads(cases_path.read_text())
    for case in cases:
        if case["name"] == case_name:
            return RoadmapGenerationInput.model_validate(case["input"])
    available = ", ".join(case["name"] for case in cases)
    raise SystemExit(f"Unknown case '{case_name}'. Available cases: {available}")


def main() -> int:
    args = parse_args()
    settings = get_settings()
    try:
        service = live_service(settings)
        report = diagnose(
            service.provider,
            load_case(args.case),
            quality_threshold=settings.ai_quality_threshold,
            max_repair_attempts=settings.ai_max_repair_attempts,
        )
    except RoadmapProviderError as error:
        report = {
            "passed": False,
            "provider": settings.ai_provider,
            "model": settings.ai_model,
            "stages": [provider_failure("configuration", error)],
        }
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
