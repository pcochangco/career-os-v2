from fastapi.testclient import TestClient

from app.main import app
from app.services.identity import (
    IdentityTokenError,
    VerifiedIdentity,
    get_identity_token_verifier,
)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_session(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/auth/anonymous")
    assert response.status_code == 201
    return response.json()


class FakeIdentityVerifier:
    def verify(self, provider: str, identity_token: str) -> VerifiedIdentity:
        if identity_token.startswith("invalid"):
            raise IdentityTokenError("invalid token")
        return VerifiedIdentity(
            provider=provider,
            subject=identity_token,
            email=f"{identity_token}@example.com",
            display_name="CareerOS User",
        )


def override_identity_verifier() -> FakeIdentityVerifier:
    return FakeIdentityVerifier()


def link_identity(
    client: TestClient,
    token: str,
    provider: str,
    subject: str,
):
    return client.post(
        f"/api/v1/auth/link/{provider}",
        headers=auth(token),
        json={"identity_token": subject.ljust(40, "-")},
    )


def test_guest_can_link_identity_without_losing_goals(client: TestClient) -> None:
    app.dependency_overrides[get_identity_token_verifier] = override_identity_verifier
    session = create_session(client)
    token = session["access_token"]
    goal = client.post(
        "/api/v1/goals",
        headers=auth(token),
        json={"title": "Build a useful mobile app"},
    ).json()

    guest_account = client.get("/api/v1/auth/account", headers=auth(token))
    assert guest_account.status_code == 200
    assert guest_account.json()["status"] == "guest"

    linked = link_identity(client, token, "google", "google-user-1")
    assert linked.status_code == 200
    replacement = linked.json()
    assert replacement["user_id"] == session["user_id"]
    assert replacement["access_token"] != token

    assert client.get("/api/v1/auth/account", headers=auth(token)).status_code == 401
    account = client.get(
        "/api/v1/auth/account",
        headers=auth(replacement["access_token"]),
    )
    assert account.status_code == 200
    assert account.json()["status"] == "saved"
    assert account.json()["providers"] == ["google"]

    goals = client.get("/api/v1/goals", headers=auth(replacement["access_token"]))
    assert [item["id"] for item in goals.json()] == [goal["id"]]


def test_returning_identity_merges_current_guest_data(client: TestClient) -> None:
    app.dependency_overrides[get_identity_token_verifier] = override_identity_verifier
    original = create_session(client)
    linked = link_identity(
        client,
        original["access_token"],
        "google",
        "returning-user",
    ).json()
    first_goal = client.post(
        "/api/v1/goals",
        headers=auth(linked["access_token"]),
        json={"title": "Learn product design"},
    ).json()

    guest = create_session(client)
    second_goal = client.post(
        "/api/v1/goals",
        headers=auth(guest["access_token"]),
        json={"title": "Ship an Android app"},
    ).json()

    returned = link_identity(
        client,
        guest["access_token"],
        "google",
        "returning-user",
    )
    assert returned.status_code == 200
    returned_session = returned.json()
    assert returned_session["user_id"] == original["user_id"]
    assert (
        client.get("/api/v1/auth/account", headers=auth(guest["access_token"])).status_code == 401
    )

    goals = client.get("/api/v1/goals", headers=auth(returned_session["access_token"]))
    assert {item["id"] for item in goals.json()} == {first_goal["id"], second_goal["id"]}


def test_saved_user_can_link_both_providers(client: TestClient) -> None:
    app.dependency_overrides[get_identity_token_verifier] = override_identity_verifier
    session = create_session(client)
    google = link_identity(
        client,
        session["access_token"],
        "google",
        "google-user",
    ).json()
    apple = link_identity(
        client,
        google["access_token"],
        "apple",
        "apple-user",
    )
    assert apple.status_code == 200

    account = client.get(
        "/api/v1/auth/account",
        headers=auth(apple.json()["access_token"]),
    ).json()
    assert account["providers"] == ["apple", "google"]


def test_link_rejects_invalid_identity_token(client: TestClient) -> None:
    app.dependency_overrides[get_identity_token_verifier] = override_identity_verifier
    session = create_session(client)

    response = link_identity(
        client,
        session["access_token"],
        "google",
        "invalid",
    )

    assert response.status_code == 401
    assert (
        client.get("/api/v1/auth/account", headers=auth(session["access_token"])).status_code == 200
    )


def test_logout_revokes_session(client: TestClient) -> None:
    session = create_session(client)

    response = client.post(
        "/api/v1/auth/logout",
        headers=auth(session["access_token"]),
    )

    assert response.status_code == 204
    assert (
        client.get("/api/v1/auth/account", headers=auth(session["access_token"])).status_code == 401
    )


def test_account_deletion_removes_access(client: TestClient) -> None:
    session = create_session(client)

    response = client.delete(
        "/api/v1/auth/account",
        headers=auth(session["access_token"]),
    )

    assert response.status_code == 204
    assert (
        client.get("/api/v1/auth/account", headers=auth(session["access_token"])).status_code == 401
    )
