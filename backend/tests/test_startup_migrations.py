from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

from app.cli import migrate

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


@pytest.fixture
def config() -> Config:
    return Config(str(ALEMBIC_INI))


def database_at(tmp_path: Path, revision: str | None) -> str:
    url = f"sqlite+pysqlite:///{tmp_path / 'db.sqlite'}"
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        if revision:
            connection.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:rev)"), {"rev": revision}
            )
    engine.dispose()
    return url


def test_database_ahead_of_code_skips_upgrade_and_starts(
    tmp_path: Path, config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    upgrades: list[str] = []
    monkeypatch.setattr(migrate.command, "upgrade", lambda _cfg, rev: upgrades.append(rev))
    url = database_at(tmp_path, "29990101_9999")

    assert migrate.run(config, url) == "skipped_database_ahead"
    assert upgrades == []


@pytest.mark.parametrize("at_head", [True, False])
def test_known_or_empty_database_upgrades_to_head(
    tmp_path: Path, config: Config, monkeypatch: pytest.MonkeyPatch, at_head: bool
) -> None:
    upgrades: list[str] = []
    monkeypatch.setattr(migrate.command, "upgrade", lambda _cfg, rev: upgrades.append(rev))
    head = ScriptDirectory.from_config(config).get_current_head()
    url = database_at(tmp_path, head if at_head else None)

    assert migrate.run(config, url) == "upgraded"
    assert upgrades == ["head"]


def test_upgrade_errors_still_fail_startup(
    tmp_path: Path, config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(_cfg: Config, _rev: str) -> None:
        raise RuntimeError("database unreachable")

    monkeypatch.setattr(migrate.command, "upgrade", broken)
    with pytest.raises(RuntimeError):
        migrate.run(config, database_at(tmp_path, None))


def test_container_starts_through_the_safe_migrator() -> None:
    dockerfile = (Path(__file__).resolve().parents[2] / "Dockerfile").read_text()
    assert "python -m app.cli.migrate && exec uvicorn" in dockerfile
    assert "alembic upgrade head &&" not in dockerfile
