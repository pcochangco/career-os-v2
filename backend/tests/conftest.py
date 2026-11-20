# Tests must never read a developer's backend/.env: it may hold a live AI key, and settings
# loaded from it would send test traffic to the real provider. This runs before app imports.
from app.core.config import Settings

Settings.model_config["env_file"] = None

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.rate_limit import get_auth_rate_limiter
from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    get_auth_rate_limiter().clear()
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    def override_get_db() -> Iterator[Session]:
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    get_auth_rate_limiter().clear()
    Base.metadata.drop_all(engine)
    engine.dispose()
