from time import perf_counter

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.ai.providers.base import ProviderResult
from app.ai.schema import GoalIntentAssessment
from app.core.config import Settings
from app.db.base import Base
from app.db.models import AIUsageEvent, User
from app.services.ai_usage import GOAL_INTENT_OPERATION, finish_ai_usage_event, start_ai_usage_event


def test_live_operation_quota_falls_back_and_records_usage() -> None:
    engine = create_engine("sqlite+pysqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            user = User()
            db.add(user)
            db.commit()
            settings = Settings(
                ai_mode="auto",
                ai_api_key="test-key",
                ai_goal_intent_limit_per_hour=1,
                ai_global_goal_intent_limit_per_hour=1,
            )

            first, first_fallback = start_ai_usage_event(
                db,
                user=user,
                operation=GOAL_INTENT_OPERATION,
                goal_id=None,
                settings=settings,
            )
            second, second_fallback = start_ai_usage_event(
                db,
                user=user,
                operation=GOAL_INTENT_OPERATION,
                goal_id=None,
                settings=settings,
            )

            assert first_fallback is False
            assert first.requested_provider == settings.ai_provider
            assert second_fallback is True
            assert second.requested_provider == "fixture"

            started = perf_counter()
            finish_ai_usage_event(
                db,
                first,
                outcome="succeeded",
                result=ProviderResult(
                    value=GoalIntentAssessment(
                        is_meaningful=True,
                        normalized_title="Build a portfolio",
                        reason="meaningful",
                    ),
                    response_id="safe-response-id",
                    input_tokens=123,
                    output_tokens=45,
                ),
                provider_source="test-provider",
                provider_model="test-model",
                duration_started_at=started,
            )

            recorded = db.scalar(select(AIUsageEvent).where(AIUsageEvent.id == first.id))
            assert recorded is not None
            assert recorded.input_tokens == 123
            assert recorded.output_tokens == 45
            assert recorded.response_count == 1
            assert recorded.completed_at is not None
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
