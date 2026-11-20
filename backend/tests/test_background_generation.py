"""Roadmaps are built in the background; the app polls a status endpoint for progress."""

from datetime import timedelta
from uuid import UUID

from fastapi.testclient import TestClient

from app.ai.dependencies import get_generation_service
from app.ai.providers.base import RoadmapProviderError
from app.ai.providers.fixture import FixtureRoadmapProvider
from app.ai.service import RoadmapGenerationService
from app.db.models import RoadmapGenerationAttempt
from app.main import app
from tests.test_generation_in_flight import db_session, insert_started_attempt, ready_goal


class ProgressService:
    """Reports two stages, checking each one is saved before generating."""

    def __init__(self) -> None:
        self.seen: list[tuple[str, int, int]] = []

    def generate(self, generation_input, on_progress=None):
        for stage, done, total in [
            ("Planning your roadmap", 0, 0),
            ("Writing milestone 1 of 2", 0, 2),
        ]:
            on_progress(stage, done, total)
            attempt = (
                db_session()
                .query(RoadmapGenerationAttempt)
                .order_by(RoadmapGenerationAttempt.created_at.desc())
                .first()
            )
            self.seen.append(
                (attempt.progress_stage, attempt.progress_done, attempt.progress_total)
            )
        return RoadmapGenerationService(FixtureRoadmapProvider()).generate(generation_input)


class FailingService:
    def generate(self, generation_input, on_progress=None):
        raise RoadmapProviderError("provider down", diagnostic_code="stage=outline")


def start(client: TestClient, headers: dict[str, str], goal_id: str):
    return client.post(f"/api/v1/goals/{goal_id}/roadmaps/generation", headers=headers)


def status_of(client: TestClient, headers: dict[str, str], goal_id: str) -> dict:
    return client.get(f"/api/v1/goals/{goal_id}/roadmaps/generation", headers=headers).json()


def test_generation_returns_at_once_and_the_roadmap_appears_when_ready(client: TestClient) -> None:
    service = ProgressService()
    app.dependency_overrides[get_generation_service] = lambda: service
    headers, goal_id = ready_goal(client)

    started = start(client, headers, goal_id)

    assert started.status_code == 202
    assert started.json()["state"] == "running"
    # TestClient runs the background job right after the response.
    assert service.seen == [("Planning your roadmap", 0, 0), ("Writing milestone 1 of 2", 0, 2)]
    status = status_of(client, headers, goal_id)
    assert status["state"] == "ready" and status["roadmap_status"] == "draft"
    roadmap = client.get(f"/api/v1/roadmaps/{status['roadmap_id']}", headers=headers)
    assert roadmap.status_code == 200


def test_status_shows_progress_while_running(client: TestClient) -> None:
    headers, goal_id = ready_goal(client)
    attempt_id = insert_started_attempt(goal_id, age=timedelta(seconds=5))
    db = db_session()
    attempt = db.get(RoadmapGenerationAttempt, attempt_id)
    attempt.progress_stage, attempt.progress_done, attempt.progress_total = (
        "Writing milestone 3 of 7",
        2,
        7,
    )
    db.commit()

    assert status_of(client, headers, goal_id) == {
        "state": "running",
        "stage": "Writing milestone 3 of 7",
        "done": 2,
        "total": 7,
        "roadmap_id": None,
        "roadmap_status": None,
    }
    assert start(client, headers, goal_id).status_code == 409  # no second paid run


def test_a_failed_background_run_reports_failed_and_can_be_retried(client: TestClient) -> None:
    app.dependency_overrides[get_generation_service] = lambda: FailingService()
    headers, goal_id = ready_goal(client)

    assert start(client, headers, goal_id).status_code == 202
    assert status_of(client, headers, goal_id)["state"] == "failed"
    attempt = db_session().query(RoadmapGenerationAttempt).one()
    assert attempt.outcome == "failed"

    app.dependency_overrides[get_generation_service] = lambda: ProgressService()
    assert start(client, headers, goal_id).status_code == 202
    assert status_of(client, headers, goal_id)["state"] == "ready"


def test_an_existing_draft_is_returned_without_generating_again(client: TestClient) -> None:
    app.dependency_overrides[get_generation_service] = lambda: ProgressService()
    headers, goal_id = ready_goal(client)
    start(client, headers, goal_id)
    first = status_of(client, headers, goal_id)

    app.dependency_overrides[get_generation_service] = lambda: FailingService()
    again = start(client, headers, goal_id)

    assert again.status_code == 202
    assert again.json()["state"] == "ready"
    assert again.json()["roadmap_id"] == first["roadmap_id"]


def test_status_is_private_to_the_goal_owner(client: TestClient) -> None:
    _, goal_id = ready_goal(client)
    other_headers, _ = ready_goal(client)
    response = client.get(f"/api/v1/goals/{goal_id}/roadmaps/generation", headers=other_headers)
    assert response.status_code == 404
    assert UUID(goal_id)
