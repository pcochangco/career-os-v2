"""Run bounded live-model evaluations without printing prompts or roadmap text."""

import argparse
import json
from pathlib import Path

from app.ai.evaluation import outcome_metrics, quality_delta
from app.ai.providers.compatible import OpenAICompatibleRoadmapProvider
from app.ai.providers.fixture import FixtureRoadmapProvider
from app.ai.schema import RoadmapGenerationInput
from app.ai.service import RoadmapGenerationService
from app.core.config import get_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=6)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = get_settings()
    api_key = settings.ai_api_key
    if api_key is None or not api_key.get_secret_value().strip():
        raise SystemExit("CAREEROS_AI_API_KEY must be configured outside source control")

    provider = OpenAICompatibleRoadmapProvider(
        provider_name=settings.ai_provider,
        api_key=api_key.get_secret_value(),
        base_url=settings.ai_base_url,
        model=settings.ai_model,
        reasoning_effort=settings.ai_reasoning_effort,
        timeout_seconds=settings.ai_request_timeout_seconds,
    )
    live_service = RoadmapGenerationService(
        provider,
        quality_threshold=settings.ai_quality_threshold,
        max_repair_attempts=settings.ai_max_repair_attempts,
    )
    fixture_service = RoadmapGenerationService(FixtureRoadmapProvider())
    cases_path = Path(__file__).with_name("cases.json")
    cases = json.loads(cases_path.read_text())[: max(1, args.limit)]
    results: list[dict[str, object]] = []

    for case in cases:
        generation_input = RoadmapGenerationInput.model_validate(case["input"])
        fixture = outcome_metrics(fixture_service.generate(generation_input))
        try:
            live = outcome_metrics(live_service.generate(generation_input))
            results.append(
                {
                    "name": case["name"],
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
    }
    print(json.dumps(report, indent=2))
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
