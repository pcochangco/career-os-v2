import pytest
from fastapi.testclient import TestClient


def test_health_returns_service_metadata(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "CareerOS API",
        "version": "0.1.0",
        "roadmap_generation": "deterministic_preview",
        "ai_provider": None,
        "ai_model": None,
        "generation_strategy": None,
        "roadmap_skill": None,
        "fallback_enabled": False,
    }


def test_health_shows_live_generation_settings(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.config import Settings

    live = Settings(ai_mode="auto", ai_provider="groq", ai_api_key="server-secret")
    monkeypatch.setattr("app.api.routes.health.get_settings", lambda: live)
    body = client.get("/api/v1/health").json()

    assert body["generation_strategy"] == "staged"
    assert body["roadmap_skill"] == "roadmap-mentor"
    assert "server-secret" not in str(body)


def test_openapi_uses_versioned_health_path(client: TestClient) -> None:
    response = client.get("/api/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/health" in response.json()["paths"]
