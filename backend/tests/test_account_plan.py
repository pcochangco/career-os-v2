"""The account endpoint tells the client which plan applies, so limits are explained up front."""

from fastapi.testclient import TestClient


def account(client: TestClient) -> dict:
    token = client.post("/api/v1/auth/anonymous").json()["access_token"]
    response = client.get("/api/v1/auth/account", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    return response.json()


def test_free_account_reports_its_goal_limit(client: TestClient) -> None:
    body = account(client)

    assert body["plan"] == "free"
    assert body["goal_limit"] == 2


def test_premium_account_reports_no_goal_limit(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.auth.is_premium", lambda user: True)

    body = account(client)

    assert body["plan"] == "premium"
    assert body["goal_limit"] is None
