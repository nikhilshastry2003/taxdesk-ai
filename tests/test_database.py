"""Tests for the migration runner and the schema's rules."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from database import migrate
from database.migrate import connect, initialize


@pytest.fixture
def db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """Give a test a fresh initialized database in a temp folder.

    In: pytest's tmp_path, a unique folder per test.
    Out: an open connection, closed automatically after the test.
    """
    conn = connect(tmp_path / "test.db")
    initialize(conn)
    yield conn
    conn.close()


def test_fresh_database_gets_all_tables(db: sqlite3.Connection) -> None:
    """Initialization on a new file must create every table."""
    rows = db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    names = {row[0] for row in rows}

    expected = {"CLIENTS", "SERVICES", "CLIENT_SERVICES", "PERIODS", "TASKS", "documents"}
    assert expected <= names


def test_second_initialize_keeps_existing_data(tmp_path: Path) -> None:
    """Running initialization again must be a no-op, never a reset."""
    conn = connect(tmp_path / "test.db")

    assert initialize(conn) is True
    conn.execute("INSERT INTO CLIENTS (NAME, FOLDER_PATH) VALUES ('Alpha', '/c/Alpha')")
    conn.commit()

    assert initialize(conn) is False
    count = conn.execute("SELECT COUNT(*) FROM CLIENTS").fetchone()[0]
    assert count == 1

    conn.close()


def test_new_required_service_reaches_an_existing_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A service appended to REQUIRED_SERVICES must appear on the next
    initialize call, without editing or re-running schema.sql."""
    conn = connect(tmp_path / "test.db")
    initialize(conn)

    monkeypatch.setattr(
        migrate,
        "REQUIRED_SERVICES",
        [*migrate.REQUIRED_SERVICES, "PT"],
    )

    assert initialize(conn) is False

    names = {row[0] for row in conn.execute("SELECT NAME FROM SERVICES")}
    assert "PT" in names
    assert len(names) == 5

    conn.close()


def test_foreign_keys_are_enforced(db: sqlite3.Connection) -> None:
    """connect() must switch the per connection foreign key pragma on."""
    assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO documents (client_id, filename, path)"
            " VALUES (99, 'x.pdf', '/x.pdf')"
        )


def test_schema_constraints_hold_through_the_runner(db: sqlite3.Connection) -> None:
    """The rules written in schema.sql must survive the runner path."""
    db.execute("INSERT INTO CLIENTS (NAME, FOLDER_PATH) VALUES ('Alpha', '/c/Alpha')")
    # Services come from initialization now, look one up instead of inserting.
    service = db.execute("SELECT ID FROM SERVICES WHERE NAME = 'GSTR-3B'").fetchone()[0]
    db.execute("INSERT INTO PERIODS (YEAR, MONTH) VALUES (2026, 8)")
    db.execute(
        "INSERT INTO TASKS (CLIENT_ID, SERVICE_ID, PERIOD_YEAR, PERIOD_MONTH)"
        " VALUES (1, ?, 2026, 8)",
        (service,),
    )

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO TASKS (CLIENT_ID, SERVICE_ID, PERIOD_YEAR, PERIOD_MONTH)"
            " VALUES (1, ?, 2026, 8)",
            (service,),
        )

    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE TASKS SET STATUS = 'Done' WHERE ID = 1")
