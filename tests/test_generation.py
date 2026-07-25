from sqlite3 import Connection

from app.db import queries
from app.services import generation


def task_count(conn: Connection, period_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM compliance_tasks WHERE period_id = ?",
        (period_id,),
    ).fetchone()
    return row["n"]


def test_generation_creates_one_task_per_active_service(sample_clients: Connection) -> None:
    conn = sample_clients
    period_id = queries.create_period(conn, 7, 2026, generation.financial_year(7, 2026))

    created = generation.generate_tasks(conn, period_id)

    assert created == 3
    assert task_count(conn, period_id) == 3


def test_second_generation_run_creates_nothing(sample_clients: Connection) -> None:
    conn = sample_clients
    period_id = queries.create_period(conn, 7, 2026, generation.financial_year(7, 2026))

    generation.generate_tasks(conn, period_id)
    created_again = generation.generate_tasks(conn, period_id)

    assert created_again == 0
    assert task_count(conn, period_id) == 3


def test_deactivated_service_generates_nothing_but_task_survives(sample_clients: Connection) -> None:
    conn = sample_clients
    period_id = queries.create_period(conn, 7, 2026, generation.financial_year(7, 2026))
    generation.generate_tasks(conn, period_id)

    queries.set_service(conn, 1, "EPF", False)
    generation.generate_tasks(conn, period_id)

    assert task_count(conn, period_id) == 3
    survivor = conn.execute(
        "SELECT status FROM compliance_tasks WHERE client_id = 1 AND service_type = 'EPF'",
    ).fetchone()
    assert survivor is not None


def test_new_client_midmonth_gets_only_its_tasks(sample_clients: Connection) -> None:
    conn = sample_clients
    period_id = queries.create_period(conn, 7, 2026, generation.financial_year(7, 2026))
    generation.generate_tasks(conn, period_id)

    conn.execute("INSERT INTO clients (name) VALUES ('Gamma')")
    conn.execute(
        "INSERT INTO client_services (client_id, service_type) VALUES (3, 'GSTR_1')",
    )

    created = generation.generate_tasks(conn, period_id)

    assert created == 1
    assert task_count(conn, period_id) == 4


def test_financial_year_boundaries() -> None:
    assert generation.financial_year(4, 2026) == "2026-27"
    assert generation.financial_year(3, 2026) == "2025-26"
    assert generation.financial_year(1, 2026) == "2025-26"
    assert generation.financial_year(12, 2026) == "2026-27"


def test_due_dates_null_while_rules_are_placeholder(sample_clients: Connection) -> None:
    conn = sample_clients
    period_id = queries.create_period(conn, 7, 2026, generation.financial_year(7, 2026))
    generation.generate_tasks(conn, period_id)

    row = conn.execute(
        "SELECT COUNT(*) AS n FROM compliance_tasks WHERE period_id = ? AND due_date IS NOT NULL",
        (period_id,),
    ).fetchone()
    assert row["n"] == 0


def test_due_dates_fill_once_a_rule_lands(sample_clients: Connection, monkeypatch) -> None:
    conn = sample_clients
    period_id = queries.create_period(conn, 7, 2026, generation.financial_year(7, 2026))
    generation.generate_tasks(conn, period_id)

    # Simulate dad's answer arriving later, GSTR_3B due on the 20th of
    # the following month. Regenerating backfills only that service.
    monkeypatch.setitem(generation.DUE_DAY_RULES, "GSTR_3B", 20)
    generation.generate_tasks(conn, period_id)

    rows = conn.execute(
        "SELECT service_type, due_date FROM compliance_tasks WHERE period_id = ? ORDER BY service_type, client_id",
        (period_id,),
    ).fetchall()
    dates = {(row["service_type"], row["due_date"]) for row in rows}
    assert ("GSTR_3B", "2026-08-20") in dates
    assert ("EPF", None) in dates


def test_december_rolls_due_date_into_january() -> None:
    assert generation.due_date_for("GSTR_3B", 12, 2026) is None
    # Direct check of the rollover arithmetic with a temporary rule.
    original = generation.DUE_DAY_RULES["GSTR_3B"]
    generation.DUE_DAY_RULES["GSTR_3B"] = 20
    try:
        assert generation.due_date_for("GSTR_3B", 12, 2026) == "2027-01-20"
    finally:
        generation.DUE_DAY_RULES["GSTR_3B"] = original
