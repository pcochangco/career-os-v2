import logging
from dataclasses import replace

from fastapi.testclient import TestClient

from app.ai.dependencies import fixture_service, get_generation_service
from app.ai.providers.base import RoadmapProviderError
from app.core.config import Settings
from app.main import app


def create_session(client: TestClient) -> str:
    response = client.post("/api/v1/auth/anonymous")
    assert response.status_code == 201
    return response.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class SuccessfulLiveService:
    def generate(self, generation_input):
        preview = fixture_service(Settings()).generate(generation_input)
        return replace(preview, provider="test-live", model="test-live-model")


def test_goal_to_accepted_roadmap_vertical_slice(client: TestClient) -> None:
    token = create_session(client)
    headers = auth(token)

    created_goal = client.post(
        "/api/v1/goals",
        headers=headers,
        json={"title": "Become an AI automation engineer"},
    )
    assert created_goal.status_code == 201
    goal = created_goal.json()
    assert goal["status"] == "discovery"

    discovery = client.put(
        f"/api/v1/goals/{goal['id']}/discovery",
        headers=headers,
        json={
            "desired_outcome": "Build and explain production-ready AI automation systems",
            "current_level": "Experienced Python automation engineer",
            "existing_experience": "Python, APIs, Selenium, Flask, and early LLM integrations",
            "relevant_constraints": "Prefer practical projects and concise learning material",
            "proof_of_completion": "A deployed AI automation portfolio project",
        },
    )
    assert discovery.status_code == 200
    assert discovery.json()["status"] == "ready_to_generate"

    generated = client.post(f"/api/v1/goals/{goal['id']}/roadmaps", headers=headers)
    assert generated.status_code == 201
    roadmap = generated.json()
    assert roadmap["status"] == "draft"
    assert roadmap["generation_source"] == "fixture"
    assert roadmap["provider_model"] == "deterministic-fixture"
    assert roadmap["schema_version"] == "1.0"
    assert roadmap["quality_score"] >= 80
    assert roadmap["quality_report"]["passed"] is True
    assert roadmap["assumptions"]
    assert len(roadmap["milestones"]) == 3
    assert sum(len(milestone["steps"]) for milestone in roadmap["milestones"]) == 6
    assert all(
        step["completion_condition"]
        for milestone in roadmap["milestones"]
        for step in milestone["steps"]
    )
    assert all(
        step["stable_key"] for milestone in roadmap["milestones"] for step in milestone["steps"]
    )

    accepted = client.post(f"/api/v1/roadmaps/{roadmap['id']}/accept", headers=headers)
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"

    goals = client.get("/api/v1/goals", headers=headers)
    assert goals.status_code == 200
    assert goals.json()[0]["active_roadmap_id"] == roadmap["id"]
    assert goals.json()[0]["status"] == "active"


def test_user_cannot_read_another_users_goal_or_roadmap(client: TestClient) -> None:
    owner_token = create_session(client)
    other_token = create_session(client)
    created = client.post(
        "/api/v1/goals",
        headers=auth(owner_token),
        json={"title": "Learn system design"},
    ).json()

    goal_response = client.get(
        f"/api/v1/goals/{created['id']}", headers=auth(other_token)
    )
    assert goal_response.status_code == 404


def test_goal_endpoints_require_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/goals")

    assert response.status_code == 401


def test_roadmap_generation_uses_preview_after_per_user_limit(
    client: TestClient,
    monkeypatch,
) -> None:
    settings = Settings(ai_mode="auto", ai_api_key="test-key")
    monkeypatch.setattr("app.api.routes.goals.get_settings", lambda: settings)
    app.dependency_overrides[get_generation_service] = SuccessfulLiveService
    token = create_session(client)
    headers = auth(token)
    discovery = {
        "desired_outcome": "Design and explain a secure production API",
        "current_level": "Python backend developer",
        "existing_experience": "FastAPI, SQLAlchemy, and PostgreSQL",
        "relevant_constraints": "Prefer practical exercises",
        "proof_of_completion": "A threat-modeled API with security tests",
    }
    generated_sources: list[str] = []
    for attempt_number in range(4):
        goal = client.post(
            "/api/v1/goals",
            headers=headers,
            json={"title": f"Learn secure API design {attempt_number}"},
        ).json()
        assert client.put(
            f"/api/v1/goals/{goal['id']}/discovery",
            headers=headers,
            json=discovery,
        ).status_code == 200
        generated = client.post(
            f"/api/v1/goals/{goal['id']}/roadmaps",
            headers=headers,
        )
        assert generated.status_code == 201
        generated_sources.append(generated.json()["generation_source"])

    assert generated_sources == ["test-live", "test-live", "test-live", "fixture"]


def test_repeated_generation_returns_the_existing_draft(client: TestClient) -> None:
    token = create_session(client)
    headers = auth(token)
    goal = client.post(
        "/api/v1/goals",
        headers=headers,
        json={"title": "Build a reliable Python service"},
    ).json()
    discovery = {
        "desired_outcome": "Build and explain a reliable production service",
        "current_level": "Python backend developer",
        "existing_experience": "FastAPI and PostgreSQL",
        "relevant_constraints": "Prefer practical exercises",
        "proof_of_completion": "A deployed service with tests",
    }
    assert client.put(
        f"/api/v1/goals/{goal['id']}/discovery",
        headers=headers,
        json=discovery,
    ).status_code == 200

    first = client.post(f"/api/v1/goals/{goal['id']}/roadmaps", headers=headers)
    repeated = client.post(f"/api/v1/goals/{goal['id']}/roadmaps", headers=headers)

    assert first.status_code == 201
    assert repeated.status_code == 201
    assert repeated.json()["id"] == first.json()["id"]
    assert repeated.json()["version"] == 1


def test_generation_does_not_replace_an_active_roadmap(client: TestClient) -> None:
    token = create_session(client)
    headers = auth(token)
    goal = client.post(
        "/api/v1/goals",
        headers=headers,
        json={"title": "Learn production API design"},
    ).json()
    discovery = {
        "desired_outcome": "Design and explain a secure production API",
        "current_level": "Python backend developer",
        "existing_experience": "FastAPI and PostgreSQL",
        "relevant_constraints": "Prefer practical exercises",
        "proof_of_completion": "A threat-modeled API with tests",
    }
    assert client.put(
        f"/api/v1/goals/{goal['id']}/discovery",
        headers=headers,
        json=discovery,
    ).status_code == 200
    roadmap = client.post(
        f"/api/v1/goals/{goal['id']}/roadmaps",
        headers=headers,
    ).json()
    assert client.post(
        f"/api/v1/roadmaps/{roadmap['id']}/accept",
        headers=headers,
    ).status_code == 200

    repeated = client.post(f"/api/v1/goals/{goal['id']}/roadmaps", headers=headers)

    assert repeated.status_code == 409
    assert repeated.json()["detail"] == "This goal already has an active roadmap."


def test_global_generation_capacity_applies_across_anonymous_sessions(
    client: TestClient,
    monkeypatch,
) -> None:
    settings = Settings(
        ai_mode="auto",
        ai_api_key="test-key",
        ai_global_generation_limit_per_hour=2,
    )
    monkeypatch.setattr("app.api.routes.goals.get_settings", lambda: settings)

    app.dependency_overrides[get_generation_service] = SuccessfulLiveService
    discovery = {
        "desired_outcome": "Build and explain a reliable production service",
        "current_level": "Python backend developer",
        "existing_experience": "FastAPI, SQLAlchemy, and PostgreSQL",
        "relevant_constraints": "Prefer practical exercises",
        "proof_of_completion": "A deployed service with tests",
    }

    for attempt_number in range(3):
        token = create_session(client)
        headers = auth(token)
        goal = client.post(
            "/api/v1/goals",
            headers=headers,
            json={"title": f"Build production service {attempt_number}"},
        ).json()
        response = client.put(
            f"/api/v1/goals/{goal['id']}/discovery",
            headers=headers,
            json=discovery,
        )
        assert response.status_code == 200
        generated = client.post(
            f"/api/v1/goals/{goal['id']}/roadmaps",
            headers=headers,
        )
        assert generated.status_code == 201
        if attempt_number < 2:
            assert generated.json()["generation_source"] != "fixture"
        else:
            assert generated.json()["generation_source"] == "fixture"
            assert generated.json()["provider_model"] == "deterministic-fixture"


def test_live_provider_failure_logs_only_the_safe_diagnostic(
    client: TestClient,
    caplog,
) -> None:
    private_detail = "private generated response must not be logged"

    class FailingService:
        def generate(self, generation_input):
            del generation_input
            raise RoadmapProviderError(
                private_detail,
                diagnostic_code="stage=generate;finish_reason=length",
            )

    app.dependency_overrides[get_generation_service] = lambda: FailingService()
    token = create_session(client)
    headers = auth(token)
    goal = client.post(
        "/api/v1/goals",
        headers=headers,
        json={"title": "Build a production AI workflow"},
    ).json()
    discovery = {
        "desired_outcome": "Build and explain a reliable production AI workflow",
        "current_level": "Python automation developer",
        "existing_experience": "Python, APIs, and basic LLM integrations",
        "relevant_constraints": "Prefer a concise project-focused roadmap",
        "proof_of_completion": "A deployed workflow with an evaluation report",
    }
    assert client.put(
        f"/api/v1/goals/{goal['id']}/discovery",
        headers=headers,
        json=discovery,
    ).status_code == 200

    with caplog.at_level(logging.WARNING, logger="app.main"):
        response = client.post(f"/api/v1/goals/{goal['id']}/roadmaps", headers=headers)

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Roadmap generation is temporarily unavailable. Please try again."
    }
    assert "failure_code=stage=generate;finish_reason=length" in caplog.text
    assert private_detail not in caplog.text


def test_openapi_contains_sprint_1_paths(client: TestClient) -> None:
    paths = client.get("/api/openapi.json").json()["paths"]

    assert "/api/v1/auth/anonymous" in paths
    assert "/api/v1/goals" in paths
    assert "/api/v1/goals/{goal_id}/discovery" in paths
    assert "/api/v1/goals/{goal_id}/roadmaps" in paths
    assert "/api/v1/roadmaps/{roadmap_id}/accept" in paths
    assert "/api/v1/roadmap-steps/{step_id}/progress" in paths
