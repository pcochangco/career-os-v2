from fastapi.testclient import TestClient


def test_health_returns_service_metadata(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "CareerOS API",
        "version": "0.1.0",
    }


def test_openapi_uses_versioned_health_path(client: TestClient) -> None:
    response = client.get("/api/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/health" in response.json()["paths"]
