"""Bring the database schema up to date at container start: python -m app.cli.migrate

Same as ``alembic upgrade head`` with one difference. When the database is already at a
revision this build doesn't know, the database is *ahead* of the code. That happens when a
newer deploy migrated and then the platform restarted an older image. Failing there takes the
whole site down (the old image can never boot), so this logs a warning and lets the app start.
Our migrations are additive, so older code keeps working against a newer schema.

Every other migration error still fails startup, as before.
"""

import logging
import sys
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from alembic import command
from app.core.config import get_settings

logger = logging.getLogger("careeros.migrate")
ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def unknown_database_revisions(config: Config, database_url: str) -> set[str]:
    """Revisions recorded in the database that this build's migration scripts don't contain."""
    script = ScriptDirectory.from_config(config)
    known = {revision.revision for revision in script.walk_revisions()}
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            current = set(MigrationContext.configure(connection).get_current_heads())
    finally:
        engine.dispose()
    return current - known


def run(config: Config | None = None, database_url: str | None = None) -> str:
    """Upgrade to head. Returns "upgraded" or "skipped_database_ahead"."""
    config = config or Config(str(ALEMBIC_INI))
    database_url = database_url or get_settings().database_url
    unknown = unknown_database_revisions(config, database_url)
    if unknown:
        logger.warning(
            "Database is at revision %s, which this build doesn't include: the schema is "
            "newer than this code. Skipping migrations and starting anyway.",
            ", ".join(sorted(unknown)),
        )
        return "skipped_database_ahead"
    command.upgrade(config, "head")
    return "upgraded"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-5.5s [%(name)s] %(message)s")
    run()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Database migration failed")
        sys.exit(1)
