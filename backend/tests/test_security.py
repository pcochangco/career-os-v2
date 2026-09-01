from fastapi.testclient import TestClient

from app.core.rate_limit import SlidingWindowRateLimiter


def test_api_responses_include_request_reference_and_security_headers(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/health",
        headers={"X-Request-ID": "mobile-check-42"},
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "mobile-check-42"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["cross-origin-opener-policy"] == "same-origin-allow-popups"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"


def test_invalid_request_reference_is_replaced(client: TestClient) -> None:
    response = client.get(
        "/api/v1/health",
        headers={"X-Request-ID": "unsafe request id with spaces"},
    )

    request_id = response.headers["x-request-id"]
    assert request_id != "unsafe request id with spaces"
    assert len(request_id) == 32
    assert request_id.isalnum()


def test_auth_rate_limiter_uses_a_sliding_window() -> None:
    now = [100.0]
    limiter = SlidingWindowRateLimiter(clock=lambda: now[0])

    assert limiter.check("anonymous:hashed", limit=2, window_seconds=60).allowed
    assert limiter.check("anonymous:hashed", limit=2, window_seconds=60).allowed
    blocked = limiter.check("anonymous:hashed", limit=2, window_seconds=60)
    assert blocked.allowed is False
    assert blocked.retry_after_seconds == 60

    now[0] = 161.0
    assert limiter.check("anonymous:hashed", limit=2, window_seconds=60).allowed
