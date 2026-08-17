"""Tests for the development seed and the services in initialization."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from database.migrate import connect, initialize
from database.seed import (
    mark_sample_statuses,
    seed_clients,
    seed_period_and_tasks,
)


def run_seed(conn: sqlite3.Connection) -> None:
    """Run the full seed sequence on an initialized database.

    In: an open connection after initialize().
    Out: nothing, same steps as the command line entry point.
    """
    seed_clients(conn)
    seed_period_and_tasks(conn)
    mark_sample_statuses(conn)
    conn.commit()


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


def test_initialization_provides_the_four_services(db: sqlite3.Connection) -> None:
    """A fresh database must already know the four filing types."""
    rows = db.execute("SELECT NAME FROM SERVICES ORDER BY NAME")
    names = [row[0] for row in rows]

    assert names == ["EPF", "ESI", "GSTR-1", "GSTR-3B"]


def test_seed_creates_expected_rows(db: sqlite3.Connection) -> None:
    """Five clients, twelve subscriptions, one inactive, eleven tasks."""
    run_seed(db)

    clients = db.execute("SELECT COUNT(*) FROM CLIENTS").fetchone()[0]
    subscriptions = db.execute("SELECT COUNT(*) FROM CLIENT_SERVICES").fetchone()[0]
    active = db.execute(
        "SELECT COUNT(*) FROM CLIENT_SERVICES WHERE ACTIVE = 1"
    ).fetchone()[0]
    tasks = db.execute("SELECT COUNT(*) FROM TASKS").fetchone()[0]

    assert clients == 5
    assert subscriptions == 12
    assert active == 11
    assert tasks == active


def test_generation_skips_inactive_subscriptions(db: sqlite3.Connection) -> None:
    """The switched off subscription must produce no task."""
    run_seed(db)

    row = db.execute(
        "SELECT COUNT(*) FROM TASKS t"
        " JOIN CLIENTS c ON c.ID = t.CLIENT_ID"
        " JOIN SERVICES s ON s.ID = t.SERVICE_ID"
        " WHERE c.NAME = 'Bhima Textiles' AND s.NAME = 'GSTR-1'"
    ).fetchone()

    assert row[0] == 0


def test_second_seed_run_changes_nothing(db: sqlite3.Connection) -> None:
    """Rerunning the whole seed must leave identical row counts."""
    run_seed(db)
    before = {
        table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("CLIENTS", "CLIENT_SERVICES", "PERIODS", "TASKS")
    }

    run_seed(db)
    after = {
        table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("CLIENTS", "CLIENT_SERVICES", "PERIODS", "TASKS")
    }

    assert before == after


def test_sample_statuses_present(db: sqlite3.Connection) -> None:
    """One done task with a trace, one not applicable, rest pending."""
    run_seed(db)

    done = db.execute(
        "SELECT COMPLETED_AT, COMPLETION_METHOD FROM TASKS WHERE STATUS = 'done'"
    ).fetchall()
    assert len(done) == 1
    assert done[0][0] is not None
    assert done[0][1] == "manual"

    not_applicable = db.execute(
        "SELECT COUNT(*) FROM TASKS WHERE STATUS = 'not_applicable'"
    ).fetchone()[0]
    assert not_applicable == 1

    pending = db.execute(
        "SELECT COUNT(*) FROM TASKS WHERE STATUS = 'pending'"
    ).fetchone()[0]
    assert pending == 9
