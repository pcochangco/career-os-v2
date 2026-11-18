"""People can download everything they created, and only their own data."""

from fastapi.testclient import TestClient

DISCOVERY = {
    "desired_outcome": "Hold a 10 minute conversation in Spanish",
    "current_level": "Beginner with some vocabulary",
    "existing_experience": "Duolingo for three months",
    "relevant_constraints": "Thirty minutes on weekdays",
    "proof_of_completion": "A recorded conversation with a tutor",
}


def signed_in(client: TestClient) -> dict[str, str]:
    token = client.post("/api/v1/auth/anonymous").json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def goal_with_progress(client: TestClient, headers: dict[str, str]) -> dict:
    goal = client.post(
        "/api/v1/goals", headers=headers, json={"title": "Learn conversational Spanish"}
    ).json()
    client.put(f"/api/v1/goals/{goal['id']}/discovery", headers=headers, json=DISCOVERY)
    roadmap = client.post(f"/api/v1/goals/{goal['id']}/roadmaps", headers=headers).json()
    roadmap = client.post(f"/api/v1/roadmaps/{roadmap['id']}/accept", headers=headers).json()
    step_id = roadmap["current_step_id"]
    client.put(
        f"/api/v1/roadmap-steps/{step_id}/work",
        headers=headers,
        json={"notes": "Practised greetings", "evidence_url": "https://example.com/recording"},
    )
    response = client.put(
        f"/api/v1/roadmap-steps/{step_id}/progress",
        headers=headers,
        json={"completed": True, "completion_confirmed": True},
    )
    assert response.status_code == 200
    return goal


def test_export_contains_goals_roadmaps_progress_and_work(client: TestClient) -> None:
    headers = signed_in(client)
    goal_with_progress(client, headers)

    response = client.get("/api/v1/auth/account/export", headers=headers)

    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["format"] == "careeros-account-export"
    assert body["account"]["plan"] == "free"
    [goal] = body["goals"]
    assert goal["title"] == "Learn conversational Spanish"
    [roadmap] = goal["roadmaps"]
    assert roadmap["status"] == "accepted"
    steps = [step for milestone in roadmap["milestones"] for step in milestone["steps"]]
    completed = [step for step in steps if step["completed_at"]]
    assert len(completed) == 1
    assert completed[0]["learning_record"] == "Practised greetings"
    assert completed[0]["evidence_link"] == "https://example.com/recording"


def test_export_leaves_out_internal_ai_metadata(client: TestClient) -> None:
    headers = signed_in(client)
    goal_with_progress(client, headers)

    text = client.get("/api/v1/auth/account/export", headers=headers).text

    for internal in ("provider_model", "prompt_version", "input_snapshot", "quality_report"):
        assert internal not in text


def test_export_never_includes_another_users_data(client: TestClient) -> None:
    owner = signed_in(client)
    goal_with_progress(client, owner)
    other = signed_in(client)

    body = client.get("/api/v1/auth/account/export", headers=other).json()

    assert body["goals"] == []


def test_export_requires_sign_in(client: TestClient) -> None:
    assert client.get("/api/v1/auth/account/export").status_code == 401
