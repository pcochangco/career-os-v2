"""Only one roadmap generation may run per goal at a time."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.ai.dependencies import get_generation_service
from app.ai.providers.base import RoadmapProviderError
from app.api.routes.goals import GENERATION_IN_FLIGHT_TTL, GENERATION_IN_PROGRESS_DETAIL
from app.db.models import Goal, RoadmapGenerationAttempt
from app.db.session import get_db
from app.main import app

DISCOVERY = {
    "desired_outcome": "Build and explain a reliable production service",
    "current_level": "Python backend developer",
    "existing_experience": "FastAPI and PostgreSQL",
    "relevant_constraints": "Prefer practical exercises",
    "proof_of_completion": "A deployed service with tests",
}


def ready_goal(client: TestClient) -> tuple[dict[str, str], str]:
    token = client.post("/api/v1/auth/anonymous").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    goal = client.post(
        "/api/v1/goals", headers=headers, json={"title": "Build a reliable Python service"}
    ).json()
    response = client.put(f"/api/v1/goals/{goal['id']}/discovery", headers=headers, json=DISCOVERY)
    assert response.status_code == 200
    return headers, goal["id"]


def db_session():
    return next(app.dependency_overrides[get_db]())


def insert_started_attempt(goal_id: str, *, age: timedelta) -> UUID:
    db = db_session()
    goal = db.get(Goal, UUID(goal_id))
    attempt = RoadmapGenerationAttempt(
        user_id=goal.user_id,
        goal_id=goal.id,
        requested_provider="test-live",
        created_at=datetime.now(UTC) - age,
    )
    db.add(attempt)
    db.commit()
    return attempt.id


class RecordingService:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, generation_input):
        self.calls += 1
        raise AssertionError("generation must not start while another is in flight")


def test_second_request_waits_for_the_in_flight_generation(client: TestClient) -> None:
    headers, goal_id = ready_goal(client)
    insert_started_attempt(goal_id, age=timedelta(seconds=5))
    service = RecordingService()
    app.dependency_overrides[get_generation_service] = lambda: service

    response = client.post(f"/api/v1/goals/{goal_id}/roadmaps", headers=headers)
    goal = client.get(f"/api/v1/goals/{goal_id}", headers=headers).json()

    assert response.status_code == 409
    assert response.json()["detail"] == GENERATION_IN_PROGRESS_DETAIL
    assert service.calls == 0
    assert goal["roadmap_generation_in_progress"] is True


def test_abandoned_generation_does_not_block_the_goal(client: TestClient) -> None:
    headers, goal_id = ready_goal(client)
    stale_id = insert_started_attempt(goal_id, age=GENERATION_IN_FLIGHT_TTL + timedelta(minutes=1))

    goal_before = client.get(f"/api/v1/goals/{goal_id}", headers=headers).json()
    response = client.post(f"/api/v1/goals/{goal_id}/roadmaps", headers=headers)

    assert goal_before["roadmap_generation_in_progress"] is False
    assert response.status_code == 201
    stale = db_session().get(RoadmapGenerationAttempt, stale_id)
    assert stale.outcome == "abandoned"


def test_failed_generation_releases_the_goal_for_a_retry(client: TestClient) -> None:
    class FailingService:
        calls = 0

        def generate(self, generation_input):
            FailingService.calls += 1
            raise RoadmapProviderError("provider down", diagnostic_code="stage=generate")

    app.dependency_overrides[get_generation_service] = lambda: FailingService()
    headers, goal_id = ready_goal(client)

    first = client.post(f"/api/v1/goals/{goal_id}/roadmaps", headers=headers)
    retry = client.post(f"/api/v1/goals/{goal_id}/roadmaps", headers=headers)

    assert first.status_code == 503
    assert retry.status_code == 503
    assert FailingService.calls == 2


def test_completed_generation_clears_the_in_flight_state(client: TestClient) -> None:
    headers, goal_id = ready_goal(client)

    created = client.post(f"/api/v1/goals/{goal_id}/roadmaps", headers=headers)
    goal = client.get(f"/api/v1/goals/{goal_id}", headers=headers).json()

    assert created.status_code == 201
    assert goal["roadmap_generation_in_progress"] is False
    assert goal["latest_draft_roadmap_id"] == created.json()["id"]
    outcomes = db_session().scalars(
        select(RoadmapGenerationAttempt.outcome).where(
            RoadmapGenerationAttempt.goal_id == UUID(goal_id)
        )
    ).all()
    assert outcomes and "started" not in outcomes


def test_database_rejects_two_in_flight_attempts_for_one_goal(client: TestClient) -> None:
    _, goal_id = ready_goal(client)
    insert_started_attempt(goal_id, age=timedelta(seconds=1))

    try:
        insert_started_attempt(goal_id, age=timedelta(seconds=0))
    except Exception as error:  # IntegrityError from the partial unique index
        assert "UNIQUE" in str(error).upper()
    else:
        raise AssertionError("a second in-flight attempt for the same goal was accepted")
