from fastapi.testclient import TestClient


def create_session(client: TestClient) -> str:
    response = client.post("/api/v1/auth/anonymous")
    assert response.status_code == 201
    return response.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_accepted_roadmap(client: TestClient, token: str) -> tuple[dict, dict]:
    headers = auth(token)
    goal = client.post(
        "/api/v1/goals",
        headers=headers,
        json={"title": "Learn reliable AI agent engineering"},
    ).json()
    discovery = client.put(
        f"/api/v1/goals/{goal['id']}/discovery",
        headers=headers,
        json={
            "desired_outcome": "Build and explain a reliable AI agent system",
            "current_level": "Experienced Python automation engineer",
            "existing_experience": "Python, APIs, automation, and early LLM integrations",
            "relevant_constraints": "Prefer practical work and concise free material",
            "proof_of_completion": "A deployed agent project with an evaluation report",
        },
    )
    assert discovery.status_code == 200
    generated = client.post(f"/api/v1/goals/{goal['id']}/roadmaps", headers=headers)
    assert generated.status_code == 201
    accepted = client.post(
        f"/api/v1/roadmaps/{generated.json()['id']}/accept",
        headers=headers,
    )
    assert accepted.status_code == 200
    return goal, accepted.json()


def steps_in(roadmap: dict) -> list[dict]:
    return [step for milestone in roadmap["milestones"] for step in milestone["steps"]]


def test_completion_advances_current_step_and_goal_progress(client: TestClient) -> None:
    token = create_session(client)
    headers = auth(token)
    goal, roadmap = create_accepted_roadmap(client, token)
    steps = steps_in(roadmap)

    assert roadmap["completed_steps"] == 0
    assert roadmap["total_steps"] == 6
    assert roadmap["progress_percent"] == 0
    assert roadmap["current_step_id"] == steps[0]["id"]
    assert steps[0]["progress_status"] == "current"
    assert steps[1]["progress_status"] == "blocked"

    blocked = client.put(
        f"/api/v1/roadmap-steps/{steps[1]['id']}/progress",
        headers=headers,
        json={"completed": True},
    )
    assert blocked.status_code == 409

    completed = client.put(
        f"/api/v1/roadmap-steps/{steps[0]['id']}/progress",
        headers=headers,
        json={"completed": True},
    )
    assert completed.status_code == 200
    updated = completed.json()
    updated_steps = steps_in(updated)
    assert updated["completed_steps"] == 1
    assert updated["progress_percent"] == 16
    assert updated["current_step_id"] == updated_steps[1]["id"]
    assert updated_steps[0]["progress_status"] == "completed"
    assert updated_steps[0]["completed_at"] is not None
    assert updated_steps[1]["progress_status"] == "current"

    repeated = client.put(
        f"/api/v1/roadmap-steps/{steps[0]['id']}/progress",
        headers=headers,
        json={"completed": True},
    )
    assert repeated.status_code == 200
    assert repeated.json()["completed_steps"] == 1

    goals = client.get("/api/v1/goals", headers=headers).json()
    assert goals[0]["id"] == goal["id"]
    assert goals[0]["completed_steps"] == 1
    assert goals[0]["total_steps"] == 6
    assert goals[0]["progress_percent"] == 16


def test_completing_and_reopening_final_step_updates_goal_status(client: TestClient) -> None:
    token = create_session(client)
    headers = auth(token)
    goal, roadmap = create_accepted_roadmap(client, token)

    while roadmap["current_step_id"] is not None:
        response = client.put(
            f"/api/v1/roadmap-steps/{roadmap['current_step_id']}/progress",
            headers=headers,
            json={"completed": True},
        )
        assert response.status_code == 200
        roadmap = response.json()

    assert roadmap["completed_steps"] == roadmap["total_steps"] == 6
    assert roadmap["progress_percent"] == 100
    assert all(step["progress_status"] == "completed" for step in steps_in(roadmap))
    completed_goal = client.get(f"/api/v1/goals/{goal['id']}", headers=headers).json()
    assert completed_goal["status"] == "completed"

    final_step = steps_in(roadmap)[-1]
    reopened = client.put(
        f"/api/v1/roadmap-steps/{final_step['id']}/progress",
        headers=headers,
        json={"completed": False},
    )
    assert reopened.status_code == 200
    assert reopened.json()["current_step_id"] == final_step["id"]
    assert reopened.json()["progress_percent"] == 83
    active_goal = client.get(f"/api/v1/goals/{goal['id']}", headers=headers).json()
    assert active_goal["status"] == "active"


def test_progress_is_private_to_the_roadmap_owner(client: TestClient) -> None:
    owner_token = create_session(client)
    other_token = create_session(client)
    _, roadmap = create_accepted_roadmap(client, owner_token)
    first_step = steps_in(roadmap)[0]

    response = client.put(
        f"/api/v1/roadmap-steps/{first_step['id']}/progress",
        headers=auth(other_token),
        json={"completed": True},
    )

    assert response.status_code == 404
