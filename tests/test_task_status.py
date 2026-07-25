from sqlite3 import Connection

from app.db import queries
from app.services import generation


def make_period_with_tasks(conn: Connection) -> int:
    period_id = queries.create_period(conn, 7, 2026, generation.financial_year(7, 2026))
    generation.generate_tasks(conn, period_id)
    return period_id


def test_done_records_when_and_how(sample_clients: Connection) -> None:
    conn = sample_clients
    make_period_with_tasks(conn)

    queries.set_task_status(conn, 1, "done")

    row = conn.execute(
        "SELECT status, completed_at, completed_source FROM compliance_tasks WHERE id = 1",
    ).fetchone()
    assert row["status"] == "done"
    assert row["completed_at"] is not None
    assert row["completed_source"] == "manual"


def test_back_to_pending_clears_completion_trace(sample_clients: Connection) -> None:
    conn = sample_clients
    make_period_with_tasks(conn)

    queries.set_task_status(conn, 1, "done")
    queries.set_task_status(conn, 1, "pending")

    row = conn.execute(
        "SELECT status, completed_at, completed_source FROM compliance_tasks WHERE id = 1",
    ).fetchone()
    assert row["status"] == "pending"
    assert row["completed_at"] is None
    assert row["completed_source"] is None


def test_pending_counts_shrink_as_tasks_complete(sample_clients: Connection) -> None:
    conn = sample_clients
    period_id = make_period_with_tasks(conn)

    queries.set_task_status(conn, 1, "done")
    queries.set_task_status(conn, 2, "not_applicable")

    row = conn.execute(
        "SELECT COUNT(*) AS n FROM compliance_tasks WHERE period_id = ? AND status = 'pending'",
        (period_id,),
    ).fetchone()
    assert row["n"] == 1
