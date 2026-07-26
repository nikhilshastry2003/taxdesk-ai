"""Shared test fixtures. Every test gets a fresh migrated database in a
temp folder, the real taxdesk.db is never touched."""

from collections.abc import Iterator
from pathlib import Path
from sqlite3 import Connection

import pytest

from app.db.migrate import connect, migrate


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[Connection]:
    """Give a test a fresh, fully migrated database in a temp folder.

    In: pytest's tmp_path, a unique temp folder per test.
    Out: an open connection the test uses, closed automatically after.
    """
    connection = connect(tmp_path / "test.db")
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def sample_clients(conn: Connection) -> Connection:
    """Two clients, three active services and one inactive, enough shape
    to exercise generation without the full seed."""
    conn.execute("INSERT INTO clients (name) VALUES ('Alpha')")
    conn.execute("INSERT INTO clients (name) VALUES ('Beta')")
    conn.executemany(
        "INSERT INTO client_services (client_id, service_type, active) VALUES (?, ?, ?)",
        [
            (1, "GSTR_3B", 1),
            (1, "EPF", 1),
            (2, "GSTR_3B", 1),
            (2, "ESI", 0),
        ],
    )
    conn.commit()
    return conn
