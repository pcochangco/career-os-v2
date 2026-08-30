from fastapi.testclient import TestClient


def create_session(client: TestClient) -> str:
    response = client.post("/api/v1/auth/anonymous")
    assert response.status_code == 201
    return response.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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


def test_roadmap_generation_is_rate_limited_per_user(client: TestClient) -> None:
    token = create_session(client)
    headers = auth(token)
    goal = client.post(
        "/api/v1/goals",
        headers=headers,
        json={"title": "Learn secure API design"},
    ).json()
    discovery = {
        "desired_outcome": "Design and explain a secure production API",
        "current_level": "Python backend developer",
        "existing_experience": "FastAPI, SQLAlchemy, and PostgreSQL",
        "relevant_constraints": "Prefer practical exercises",
        "proof_of_completion": "A threat-modeled API with security tests",
    }
    response = client.put(
        f"/api/v1/goals/{goal['id']}/discovery",
        headers=headers,
        json=discovery,
    )
    assert response.status_code == 200

    for _ in range(3):
        response = client.post(f"/api/v1/goals/{goal['id']}/roadmaps", headers=headers)
        assert response.status_code == 201

    limited = client.post(f"/api/v1/goals/{goal['id']}/roadmaps", headers=headers)
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "3600"


def test_openapi_contains_sprint_1_paths(client: TestClient) -> None:
    paths = client.get("/api/openapi.json").json()["paths"]

    assert "/api/v1/auth/anonymous" in paths
    assert "/api/v1/goals" in paths
    assert "/api/v1/goals/{goal_id}/discovery" in paths
    assert "/api/v1/goals/{goal_id}/roadmaps" in paths
    assert "/api/v1/roadmaps/{roadmap_id}/accept" in paths
