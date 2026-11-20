"""Two overlapping "next question" requests for one goal must not produce a 500."""

from uuid import UUID

from fastapi.testclient import TestClient

from app.ai.dependencies import get_discovery_service
from app.ai.providers.base import ProviderResult
from app.ai.schema import DiscoveryOption, DiscoveryQuestionDraft
from app.db.models import GoalDiscoveryQuestion
from app.main import app
from tests.test_generation_in_flight import db_session


class RacingService:
    """While "thinking", another request saves question 1 for the same goal first."""

    def __init__(self, goal_id: str) -> None:
        self.goal_id = goal_id

    def next_question(self, **kwargs) -> ProviderResult[DiscoveryQuestionDraft]:
        db = db_session()
        db.add(
            GoalDiscoveryQuestion(
                goal_id=UUID(self.goal_id),
                revision=1,
                position=1,
                question_key="winner-question",
                question="What does success look like for you?",
                help_text="Pick what matters most.",
                selection_mode="multiple",
                options=[{"key": f"o{i}", "label": f"Option {i}"} for i in range(3)],
                placeholder="",
            )
        )
        db.commit()
        return ProviderResult(
            value=DiscoveryQuestionDraft(
                is_complete=False,
                question_key="loser-question",
                question="Which area should we focus on first?",
                help_text="Choose one to start.",
                options=[DiscoveryOption(key=f"x{i}", label=f"Choice {i}") for i in range(3)],
            )
        )


def test_the_slower_request_returns_the_question_the_faster_one_saved(client: TestClient) -> None:
    token = client.post("/api/v1/auth/anonymous").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    goal_id = client.post(
        "/api/v1/goals", headers=headers, json={"title": "Learn conversational Spanish"}
    ).json()["id"]
    app.dependency_overrides[get_discovery_service] = lambda: RacingService(goal_id)

    response = client.post(f"/api/v1/goals/{goal_id}/discovery/questions/next", headers=headers)

    assert response.status_code == 200
    assert response.json()["question"]["question_key"] == "winner-question"
    saved = db_session().query(GoalDiscoveryQuestion).filter_by(goal_id=UUID(goal_id)).all()
    assert [q.question_key for q in saved] == ["winner-question"]
