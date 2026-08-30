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
        json={"completed": True, "completion_confirmed": True},
    )
    assert blocked.status_code == 409

    completed = client.put(
        f"/api/v1/roadmap-steps/{steps[0]['id']}/progress",
        headers=headers,
        json={"completed": True, "completion_confirmed": True},
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
        json={"completed": True, "completion_confirmed": True},
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
            json={"completed": True, "completion_confirmed": True},
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
        json={"completed": True, "completion_confirmed": True},
    )

    assert response.status_code == 404


def test_completion_requires_explicit_condition_confirmation(client: TestClient) -> None:
    token = create_session(client)
    _, roadmap = create_accepted_roadmap(client, token)
    first_step = steps_in(roadmap)[0]

    unconfirmed = client.put(
        f"/api/v1/roadmap-steps/{first_step['id']}/progress",
        headers=auth(token),
        json={"completed": True},
    )

    assert unconfirmed.status_code == 422
    unchanged = client.get(f"/api/v1/roadmaps/{roadmap['id']}", headers=auth(token)).json()
    assert unchanged["completed_steps"] == 0


def test_step_work_is_saved_trimmed_and_preserved_across_progress(client: TestClient) -> None:
    token = create_session(client)
    headers = auth(token)
    _, roadmap = create_accepted_roadmap(client, token)
    first_step = steps_in(roadmap)[0]

    saved = client.put(
        f"/api/v1/roadmap-steps/{first_step['id']}/work",
        headers=headers,
        json={
            "notes": "  Closures keep the wrapped function state.  ",
            "evidence_summary": "  Wrote and tested a timing decorator.  ",
            "evidence_url": "  https://example.com/timing-decorator  ",
        },
    )
    assert saved.status_code == 200
    saved_step = steps_in(saved.json())[0]
    assert saved_step["notes"] == "Closures keep the wrapped function state."
    assert saved_step["evidence_summary"] == "Wrote and tested a timing decorator."
    assert saved_step["evidence_url"] == "https://example.com/timing-decorator"
    assert saved_step["work_updated_at"] is not None

    completed = client.put(
        f"/api/v1/roadmap-steps/{first_step['id']}/progress",
        headers=headers,
        json={"completed": True, "completion_confirmed": True},
    )
    assert completed.status_code == 200
    completed_step = steps_in(completed.json())[0]
    assert completed_step["progress_status"] == "completed"
    assert completed_step["notes"] == saved_step["notes"]
    assert completed_step["evidence_summary"] == saved_step["evidence_summary"]
    assert completed_step["evidence_url"] == saved_step["evidence_url"]

    reopened = client.put(
        f"/api/v1/roadmap-steps/{first_step['id']}/progress",
        headers=headers,
        json={"completed": False},
    )
    assert reopened.status_code == 200
    reopened_step = steps_in(reopened.json())[0]
    assert reopened_step["progress_status"] == "current"
    assert reopened_step["notes"] == saved_step["notes"]
    assert reopened_step["evidence_summary"] == saved_step["evidence_summary"]
    assert reopened_step["evidence_url"] == saved_step["evidence_url"]


def test_step_work_rejects_invalid_links_and_other_users(client: TestClient) -> None:
    owner_token = create_session(client)
    other_token = create_session(client)
    _, roadmap = create_accepted_roadmap(client, owner_token)
    first_step = steps_in(roadmap)[0]

    invalid_link = client.put(
        f"/api/v1/roadmap-steps/{first_step['id']}/work",
        headers=auth(owner_token),
        json={"evidence_url": "ftp://example.com/file"},
    )
    assert invalid_link.status_code == 422

    not_owned = client.put(
        f"/api/v1/roadmap-steps/{first_step['id']}/work",
        headers=auth(other_token),
        json={"notes": "This must not be written."},
    )
    assert not_owned.status_code == 404
