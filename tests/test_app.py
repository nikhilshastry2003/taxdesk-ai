"""Tests for the application skeleton, the health route and startup."""

from collections.abc import Iterator
from pathlib import Path
from sqlite3 import Connection

import pytest
from fastapi.testclient import TestClient

from app.deps import get_db
from app.main import create_app
from database.migrate import connect


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """Give a test a running app over a fresh temp database.

    In: pytest's tmp_path.
    Out: a TestClient whose startup has run, so migrations applied.
    """
    application = create_app(tmp_path / "test.db")
    with TestClient(application) as test_client:
        yield test_client


def test_health_returns_200(client: TestClient) -> None:
    """The route must answer with HTTP 200."""
    assert client.get("/health").status_code == 200


def test_health_body_is_exactly_status_ok(client: TestClient) -> None:
    """Key for key equality, so nothing can quietly join the response."""
    assert client.get("/health").json() == {"status": "ok"}


def test_health_uses_the_injected_database(tmp_path: Path) -> None:
    """The route must reach SQLite through the dependency, proven by
    overriding it and observing the override being consumed."""
    application = create_app(tmp_path / "main.db")
    used = False

    def override() -> Iterator[Connection]:
        nonlocal used
        used = True
        conn = connect(tmp_path / "other.db")
        try:
            yield conn
        finally:
            conn.close()

    application.dependency_overrides[get_db] = override

    with TestClient(application) as test_client:
        response = test_client.get("/health")

    assert response.status_code == 200
    assert used is True


def test_startup_initializes_a_fresh_database(tmp_path: Path) -> None:
    """Entering the app context must leave the database migrated."""
    db_path = tmp_path / "fresh.db"
    application = create_app(db_path)

    with TestClient(application):
        pass

    conn = connect(db_path)
    recorded = [
        row[0]
        for row in conn.execute("SELECT filename FROM schema_applied ORDER BY filename")
    ]
    conn.close()

    assert recorded == ["001_schema.sql", "002_settings.sql"]


def test_unknown_route_returns_plain_404(client: TestClient) -> None:
    """A miss must return FastAPI's generic 404 with no internals."""
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_health_exposes_no_internal_information(client: TestClient) -> None:
    """The response must carry no paths, versions, or database hints."""
    response = client.get("/health")
    body = response.text.lower()

    for leak in ("taxdesk", ".db", "sqlite", "path", "version", "traceback"):
        assert leak not in body
    assert set(response.json().keys()) == {"status"}
