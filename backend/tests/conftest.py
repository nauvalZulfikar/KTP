from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app import models  # noqa: F401 — register tables


@pytest.fixture
def test_engine() -> Iterator[Engine]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(test_engine: Engine) -> Iterator[Session]:
    with Session(test_engine) as s:
        yield s


@pytest.fixture
def client(test_engine: Engine, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    import app.db

    monkeypatch.setattr(app.db, "engine", test_engine)

    def override_session() -> Iterator[Session]:
        with Session(test_engine) as s:
            yield s

    from app.db import get_session
    from app.main import app as fastapi_app

    fastapi_app.dependency_overrides[get_session] = override_session
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.clear()
