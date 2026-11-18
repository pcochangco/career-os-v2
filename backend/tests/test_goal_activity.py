"""The goals list says where each roadmap stands, so returning users can pick up in one tap."""

from datetime import datetime

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


def goal_listing(client: TestClient, headers: dict[str, str]) -> dict:
    [goal] = client.get("/api/v1/goals", headers=headers).json()
    return goal


def test_goal_without_a_roadmap_has_no_activity(client: TestClient) -> None:
    headers = signed_in(client)
    client.post("/api/v1/goals", headers=headers, json={"title": "Learn conversational Spanish"})

    goal = goal_listing(client, headers)
    assert goal["current_step_title"] == ""
    assert goal["last_activity_at"] is None


def test_listing_shows_current_step_and_latest_activity(client: TestClient) -> None:
    headers = signed_in(client)
    goal = client.post(
        "/api/v1/goals", headers=headers, json={"title": "Learn conversational Spanish"}
    ).json()
    client.put(f"/api/v1/goals/{goal['id']}/discovery", headers=headers, json=DISCOVERY)
    roadmap = client.post(f"/api/v1/goals/{goal['id']}/roadmaps", headers=headers).json()
    roadmap = client.post(f"/api/v1/roadmaps/{roadmap['id']}/accept", headers=headers).json()
    steps = [step for milestone in roadmap["milestones"] for step in milestone["steps"]]
    first = next(step for step in steps if step["id"] == roadmap["current_step_id"])

    accepted = goal_listing(client, headers)
    assert accepted["current_step_title"] == first["title"]
    started_at = datetime.fromisoformat(accepted["last_activity_at"])

    roadmap = client.put(
        f"/api/v1/roadmap-steps/{first['id']}/progress",
        headers=headers,
        json={"completed": True, "completion_confirmed": True},
    ).json()
    second = next(step for step in steps if step["id"] == roadmap["current_step_id"])

    progressed = goal_listing(client, headers)
    assert progressed["current_step_title"] == second["title"]
    assert datetime.fromisoformat(progressed["last_activity_at"]) >= started_at
