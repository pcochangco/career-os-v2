"""Passwordless sign-in with a one-time emailed code."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings

EMAIL = "learner@example.com"


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Turn email-code sign-in on with a sender that records instead of emailing."""
    outbox: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "app.api.routes.auth.get_settings",
        lambda: Settings(email_code_login_enabled=True, email_sender="log"),
    )
    monkeypatch.setattr(
        "app.api.routes.auth.send_sign_in_code",
        lambda _settings, email, code: outbox.append((email, code)),
    )
    return outbox


def request_code(client: TestClient, email: str = EMAIL) -> int:
    return client.post("/api/v1/auth/email-code/request", json={"email": email}).status_code


def verify(client: TestClient, code: str, email: str = EMAIL):
    return client.post("/api/v1/auth/email-code/verify", json={"email": email, "code": code})


def test_switched_off_by_default(client: TestClient) -> None:
    assert client.get("/api/v1/auth/config").json()["email_code"] is False
    assert request_code(client) == 404
    assert verify(client, "123456").status_code == 404


def test_log_sender_is_never_ready_in_production() -> None:
    settings = Settings(email_code_login_enabled=True, email_sender="log", environment="production")
    assert settings.email_code_login_ready is False
    assert Settings(
        email_code_login_enabled=True,
        email_sender="resend",
        email_from="CareerOS <sign-in@careeros.example>",
        resend_api_key="re_test",
        environment="production",
    ).email_code_login_ready


def test_code_signs_in_once_and_returns_the_same_account(
    client: TestClient, sent: list[tuple[str, str]]
) -> None:
    assert client.get("/api/v1/auth/config").json()["email_code"] is True
    assert request_code(client, "  Learner@Example.com ") == 202
    [(email, code)] = sent
    assert email == EMAIL and len(code) == 6 and code.isdigit()

    signed_in = verify(client, code)
    assert signed_in.status_code == 200
    headers = {"Authorization": f"Bearer {signed_in.json()['access_token']}"}
    account = client.get("/api/v1/auth/account", headers=headers).json()
    assert account["status"] == "saved"
    assert account["email"] == EMAIL
    assert verify(client, code).status_code == 401  # single use

    request_code(client)
    again = verify(client, sent[-1][1])
    assert again.json()["user_id"] == signed_in.json()["user_id"]


def test_wrong_code_counts_attempts_and_locks_the_code(
    client: TestClient, sent: list[tuple[str, str]]
) -> None:
    request_code(client)
    code = sent[-1][1]
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        response = verify(client, wrong)
        assert response.status_code == 401
        assert "didn't work" in response.json()["detail"]
    assert verify(client, code).status_code == 401  # locked after 5 misses


def test_requesting_again_replaces_the_previous_code(
    client: TestClient, sent: list[tuple[str, str]]
) -> None:
    request_code(client)
    request_code(client)
    first, second = sent[0][1], sent[1][1]
    if first != second:
        assert verify(client, first).status_code == 401
    assert verify(client, second).status_code == 200


def test_rejects_invalid_email_and_limits_requests_per_email(
    client: TestClient, sent: list[tuple[str, str]]
) -> None:
    assert request_code(client, "not-an-email") == 422
    statuses = [request_code(client) for _ in range(6)]
    assert statuses[:5] == [202] * 5
    assert statuses[5] == 429


def test_resend_sender_posts_the_code_and_hides_failures(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import httpx

    from app.services.email import EmailDeliveryError, send_sign_in_code

    settings = Settings(
        email_sender="resend", email_from="CareerOS <a@careeros.example>", resend_api_key="re_x"
    )
    calls: list[dict] = []

    def ok(url: str, **kwargs: object) -> httpx.Response:
        calls.append({"url": url, **kwargs})
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", ok)
    send_sign_in_code(settings, EMAIL, "424242")
    [call] = calls
    assert call["url"] == "https://api.resend.com/emails"
    assert call["json"]["to"] == [EMAIL] and "424242" in call["json"]["subject"]

    def failing(url: str, **_: object) -> httpx.Response:
        return httpx.Response(500, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", failing)
    with pytest.raises(EmailDeliveryError):
        send_sign_in_code(settings, EMAIL, "424242")
    assert "424242" not in caplog.text and "re_x" not in caplog.text
