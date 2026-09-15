"""Run bounded live-model evaluations without printing prompts or roadmap text."""

import argparse
import json
from pathlib import Path

from app.ai.curriculum import apply_matching_curriculum
from app.ai.evaluation import outcome_metrics, quality_delta
from app.ai.providers.compatible import OpenAICompatibleRoadmapProvider
from app.ai.providers.fixture import FixtureRoadmapProvider
from app.ai.schema import RoadmapGenerationInput
from app.ai.service import RoadmapGenerationService
from app.core.config import get_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument(
        "--confirm-live",
        action="store_true",
        help="Required because each case can make bounded paid-provider calls.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = get_settings()
    if not args.confirm_live:
        raise SystemExit("Pass --confirm-live to spend provider capacity on live evaluation.")
    if args.limit < 1 or args.limit > settings.ai_live_evaluation_case_limit:
        raise SystemExit(
            "--limit must be between 1 and "
            f"{settings.ai_live_evaluation_case_limit} (CAREEROS_AI_LIVE_EVALUATION_CASE_LIMIT)."
        )
    api_key = settings.ai_api_key
    if api_key is None or not api_key.get_secret_value().strip():
        raise SystemExit("CAREEROS_AI_API_KEY must be configured outside source control")

    provider = OpenAICompatibleRoadmapProvider(
        provider_name=settings.ai_provider,
        api_key=api_key.get_secret_value(),
        base_url=settings.ai_base_url,
        model=settings.ai_model,
        critic_model=settings.resolved_ai_critic_model,
        repair_model=settings.resolved_ai_repair_model,
        response_format_mode=settings.ai_response_format,
        reasoning_effort=settings.ai_reasoning_effort,
        timeout_seconds=settings.ai_request_timeout_seconds,
        max_completion_tokens=settings.ai_max_completion_tokens,
        critic_max_completion_tokens=settings.ai_critic_max_completion_tokens,
        repair_max_completion_tokens=settings.ai_repair_max_completion_tokens,
    )
    live_service = RoadmapGenerationService(
        provider,
        quality_threshold=settings.ai_quality_threshold,
        max_repair_attempts=settings.ai_max_repair_attempts,
    )
    fixture_service = RoadmapGenerationService(FixtureRoadmapProvider())
    cases_path = Path(__file__).with_name("cases.json")
    cases = json.loads(cases_path.read_text())[: args.limit]
    results: list[dict[str, object]] = []

    for case in cases:
        generation_input = apply_matching_curriculum(
            RoadmapGenerationInput.model_validate(case["input"])
        )
        fixture = outcome_metrics(fixture_service.generate(generation_input))
        try:
            live = outcome_metrics(live_service.generate(generation_input))
            results.append(
                {
                    "name": case["name"],
                    "tags": case.get("tags", []),
                    "status": "passed",
                    "live": live,
                    "fixture": fixture,
                    "quality_delta": quality_delta(live, fixture),
                }
            )
        except Exception as error:
            results.append(
                {
                    "name": case["name"],
                    "tags": case.get("tags", []),
                    "status": "failed",
                    "error_type": type(error).__name__,
                    "fixture": fixture,
                }
            )

    report = {
        "model": settings.ai_model,
        "cases": results,
        "passed": sum(result["status"] == "passed" for result in results),
        "failed": sum(result["status"] == "failed" for result in results),
        "total_input_tokens": sum(
            result.get("live", {}).get("input_tokens", 0) for result in results
        ),
        "total_output_tokens": sum(
            result.get("live", {}).get("output_tokens", 0) for result in results
        ),
    }
    print(json.dumps(report, indent=2))
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
