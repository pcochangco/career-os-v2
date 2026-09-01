import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
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


def provider_token(subject: str) -> str:
    return subject.ljust(40, "-")


def sign_in_identity(client: TestClient, provider: str, subject: str):
    return client.post(
        f"/api/v1/auth/sign-in/{provider}",
        json={"identity_token": provider_token(subject)},
    )


def link_identity(client: TestClient, token: str, provider: str, subject: str):
    return client.post(
        f"/api/v1/auth/link/{provider}",
        headers=auth(token),
        json={"identity_token": provider_token(subject)},
    )


def test_provider_config_is_public(client: TestClient) -> None:
    response = client.get("/api/v1/auth/config")

    assert response.status_code == 200
    assert response.json()["apple"] is False
    assert response.json()["google"] is False


def test_provider_sign_in_creates_saved_account(client: TestClient) -> None:
    app.dependency_overrides[get_identity_token_verifier] = override_identity_verifier

    signed_in = sign_in_identity(client, "google", "google-user-1")

    assert signed_in.status_code == 200
    account = client.get(
        "/api/v1/auth/account",
        headers=auth(signed_in.json()["access_token"]),
    )
    assert account.status_code == 200
    assert account.json()["status"] == "saved"
    assert account.json()["providers"] == ["google"]


def test_returning_sign_in_never_merges_guest_data(client: TestClient) -> None:
    app.dependency_overrides[get_identity_token_verifier] = override_identity_verifier
    original = sign_in_identity(client, "google", "returning-user").json()
    saved_goal = client.post(
        "/api/v1/goals",
        headers=auth(original["access_token"]),
        json={"title": "Learn product design"},
    ).json()

    guest = create_session(client)
    guest_goal = client.post(
        "/api/v1/goals",
        headers=auth(guest["access_token"]),
        json={"title": "Ship an Android app"},
    ).json()

    returned = sign_in_identity(client, "google", "returning-user")
    assert returned.status_code == 200
    returned_session = returned.json()
    assert returned_session["user_id"] == original["user_id"]

    saved_goals = client.get(
        "/api/v1/goals",
        headers=auth(returned_session["access_token"]),
    )
    assert [item["id"] for item in saved_goals.json()] == [saved_goal["id"]]

    guest_goals = client.get(
        "/api/v1/goals",
        headers=auth(guest["access_token"]),
    )
    assert [item["id"] for item in guest_goals.json()] == [guest_goal["id"]]


def test_guest_cannot_link_or_merge_an_identity(client: TestClient) -> None:
    app.dependency_overrides[get_identity_token_verifier] = override_identity_verifier
    guest = create_session(client)

    linked = link_identity(client, guest["access_token"], "google", "google-user")

    assert linked.status_code == 403
    assert linked.json()["detail"] == "Sign in before linking another provider"
    assert (
        client.get("/api/v1/auth/account", headers=auth(guest["access_token"])).status_code == 200
    )


def test_saved_user_can_link_both_providers(client: TestClient) -> None:
    app.dependency_overrides[get_identity_token_verifier] = override_identity_verifier
    google = sign_in_identity(client, "google", "google-user").json()
    apple = link_identity(client, google["access_token"], "apple", "apple-user")
    assert apple.status_code == 200

    account = client.get(
        "/api/v1/auth/account",
        headers=auth(apple.json()["access_token"]),
    ).json()
    assert account["providers"] == ["apple", "google"]


def test_sign_in_rejects_invalid_identity_token(client: TestClient) -> None:
    app.dependency_overrides[get_identity_token_verifier] = override_identity_verifier

    response = sign_in_identity(client, "google", "invalid")

    assert response.status_code == 401


def test_guest_access_can_be_disabled(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.api.routes.auth.get_settings",
        lambda: Settings(allow_guest_access=False),
    )

    response = client.post("/api/v1/auth/anonymous")

    assert response.status_code == 404
    assert response.json()["detail"] == "Guest access is not available"


def test_logout_revokes_session(client: TestClient) -> None:
    app.dependency_overrides[get_identity_token_verifier] = override_identity_verifier
    session = sign_in_identity(client, "google", "logout-user").json()

    response = client.post(
        "/api/v1/auth/logout",
        headers=auth(session["access_token"]),
    )

    assert response.status_code == 204
    assert (
        client.get("/api/v1/auth/account", headers=auth(session["access_token"])).status_code == 401
    )


def test_account_deletion_removes_access(client: TestClient) -> None:
    app.dependency_overrides[get_identity_token_verifier] = override_identity_verifier
    session = sign_in_identity(client, "google", "delete-user").json()

    response = client.delete(
        "/api/v1/auth/account",
        headers=auth(session["access_token"]),
    )

    assert response.status_code == 204
    assert (
        client.get("/api/v1/auth/account", headers=auth(session["access_token"])).status_code == 401
    )
