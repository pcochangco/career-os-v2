from fastapi.testclient import TestClient


def create_session(client: TestClient) -> str:
    response = client.post("/api/v1/auth/anonymous")
    assert response.status_code == 201
    return response.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_issue_report_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/api/v1/issue-reports",
        json={"category": "technical", "message": "The save button did not respond."},
    )

    assert response.status_code == 401


def test_signed_in_user_can_submit_issue_report(client: TestClient) -> None:
    token = create_session(client)

    response = client.post(
        "/api/v1/issue-reports",
        headers=auth(token),
        json={
            "category": "roadmap",
            "message": "  The second milestone repeats the first milestone.  ",
            "request_reference": "  req-beta-123  ",
            "platform": "web",
            "app_version": "  0.1.0  ",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["category"] == "roadmap"
    assert payload["reference"].startswith("CAR-")
    assert len(payload["reference"]) == 12


def test_issue_report_validates_category_and_details(client: TestClient) -> None:
    token = create_session(client)

    invalid_category = client.post(
        "/api/v1/issue-reports",
        headers=auth(token),
        json={"category": "billing", "message": "This message is long enough."},
    )
    short_message = client.post(
        "/api/v1/issue-reports",
        headers=auth(token),
        json={"category": "other", "message": "Too short"},
    )
    whitespace_message = client.post(
        "/api/v1/issue-reports",
        headers=auth(token),
        json={"category": "other", "message": "            "},
    )

    assert invalid_category.status_code == 422
    assert short_message.status_code == 422
    assert whitespace_message.status_code == 422
