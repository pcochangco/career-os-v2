from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.web import mount_frontend


def test_render_postgres_url_uses_installed_psycopg_driver() -> None:
    settings = Settings(database_url="postgresql://user:password@database.example/careeros")

    assert settings.database_url == (
        "postgresql+psycopg://user:password@database.example/careeros"
    )


def test_explicit_database_driver_is_preserved() -> None:
    database_url = "postgresql+psycopg://user:password@database.example/careeros"

    assert Settings(database_url=database_url).database_url == database_url


def test_exported_frontend_serves_routes_without_masking_api_404s(
    tmp_path: Path,
) -> None:
    (tmp_path / "index.html").write_text("<html><title>CareerOS</title></html>")
    (tmp_path / "asset.txt").write_text("deployed")
    application = FastAPI()

    @application.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    mount_frontend(application, str(tmp_path))

    with TestClient(application) as client:
        assert client.get("/").status_code == 200
        assert "CareerOS" in client.get("/goals/example/roadmap").text
        assert client.get("/asset.txt").text == "deployed"
        assert client.get("/api/v1/health").json() == {"status": "ok"}
        assert client.get("/api/v1/missing").status_code == 404
