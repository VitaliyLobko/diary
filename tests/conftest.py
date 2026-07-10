import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from main import app
from src.database.db import get_db
from src.database.models import Base


@pytest.fixture(autouse=True)
def _disable_rate_limit():
    # The limiter is per-process global state; keep it off across the suite so
    # repeated auth calls in tests aren't throttled. The dedicated rate-limit
    # test re-enables it locally.
    app.state.limiter.enabled = False
    yield


@pytest.fixture(scope="session")
def engine():
    # Spin up a throwaway PostgreSQL instance for the whole test session, so
    # tests run against the same engine as production instead of SQLite.
    with PostgresContainer("postgres:16-alpine") as postgres:
        eng = create_engine(postgres.get_connection_url())
        try:
            yield eng
        finally:
            eng.dispose()


@pytest.fixture(autouse=True)
def _bind_session_local(engine, monkeypatch):
    # The session middleware resolves a user's role outside the dependency graph,
    # so it builds its own SessionLocal rather than the overridden get_db. Point
    # that factory at the throwaway container too.
    monkeypatch.setattr(
        "src.database.db.SessionLocal",
        sessionmaker(autocommit=False, autoflush=False, bind=engine),
    )


@pytest.fixture(scope="module")
def session(engine):
    # Fresh schema per test module.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def client(session):
    # Dependency override

    def override_get_db():
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)


@pytest.fixture(scope="module")
def user():
    return {
        "username": "testuser@test.com",
        "email": "testuser@test.com",
        "password": "12345678",
    }
