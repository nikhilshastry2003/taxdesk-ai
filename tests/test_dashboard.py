from sqlite3 import Connection

from app.db import queries
from app.services import generation


def build_period(conn: Connection) -> int:
    """Create July 2026 and generate its tasks from the sample clients.

    In: the sample_clients connection from conftest.
    Out: the new period's row id, with 3 tasks generated.
    """
    period_id = queries.create_period(conn, 7, 2026, generation.financial_year(7, 2026))
    generation.generate_tasks(conn, period_id)
    return period_id


def test_pending_counts_match_fixture(sample_clients: Connection) -> None:
    """Counts per service equal what the fixture promises."""
    conn = sample_clients
    period_id = build_period(conn)

    counts = queries.pending_counts(conn, period_id)

    assert counts == {"GSTR_3B": 2, "GSTR_1": 0, "EPF": 1, "ESI": 0}


def test_dashboard_and_priority_always_agree(sample_clients: Connection) -> None:
    """The mirror guarantee. For every service, the Dashboard count
    equals the number of rows Priority would list."""
    conn = sample_clients
    period_id = build_period(conn)
    queries.set_task_status(conn, 1, "done")

    counts = queries.pending_counts(conn, period_id)

    for service in queries.SERVICE_TYPES:
        rows = queries.pending_tasks(conn, period_id, service_type=service)
        assert counts[service] == len(rows)


def test_done_and_not_applicable_leave_the_lists(sample_clients: Connection) -> None:
    """Completed and not applicable tasks vanish from counts and rows."""
    conn = sample_clients
    period_id = build_period(conn)

    queries.set_task_status(conn, 1, "done")
    queries.set_task_status(conn, 2, "not_applicable")

    counts = queries.pending_counts(conn, period_id)
    assert sum(counts.values()) == 1
    assert len(queries.pending_tasks(conn, period_id)) == 1


def test_search_filters_by_name_fragment(sample_clients: Connection) -> None:
    """Search matches part of a client name, ignoring case."""
    conn = sample_clients
    period_id = build_period(conn)

    rows = queries.pending_tasks(conn, period_id, search="alph")

    assert rows
    assert all(row["client_name"] == "Alpha" for row in rows)
    assert queries.pending_tasks(conn, period_id, search="zzz") == []


def test_default_period_prefers_open(sample_clients: Connection) -> None:
    """A newer but closed period loses to an older open one."""
    conn = sample_clients
    july = queries.create_period(conn, 7, 2026, generation.financial_year(7, 2026))
    august = queries.create_period(conn, 8, 2026, generation.financial_year(8, 2026))
    queries.set_period_status(conn, august, "closed")

    assert queries.default_period(conn)["id"] == july

    queries.set_period_status(conn, august, "open")
    assert queries.default_period(conn)["id"] == august


def test_pending_clients_lists_only_those_with_work(sample_clients: Connection) -> None:
    """Clients whose tasks are all handled drop off the Dashboard list."""
    conn = sample_clients
    period_id = build_period(conn)

    # Beta has one task (id 3). Mark it done, only Alpha remains.
    queries.set_task_status(conn, 3, "done")

    rows = queries.pending_clients(conn, period_id)
    assert [row["name"] for row in rows] == ["Alpha"]
    assert rows[0]["pending"] == 2


def test_client_pending_view_is_scoped(sample_clients: Connection) -> None:
    """The client page section shows only that client's pending tasks."""
    conn = sample_clients
    period_id = build_period(conn)

    rows = queries.client_pending_tasks(conn, 2, period_id)

    assert len(rows) == 1
    assert rows[0]["service_type"] == "GSTR_3B"
