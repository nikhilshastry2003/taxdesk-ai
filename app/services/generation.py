"""Task generation and period logic. Pure functions over a database
connection, no HTTP anywhere, so tests can import this directly."""

from datetime import date
from sqlite3 import Connection

# Due day of month per service, in the month FOLLOWING the period.
# PLACEHOLDER, every value stays None until dad confirms the real days,
# then each fill is a one line edit. The following month assumption also
# gets confirmed with him at that point.
DUE_DAY_RULES: dict[str, int | None] = {
    "GSTR_3B": None,
    "GSTR_1": None,
    "EPF": None,
    "ESI": None,
}


def financial_year(month: int, year: int) -> str:
    """India's financial year runs April to March. July 2026 belongs to
    '2026-27', February 2026 belongs to '2025-26'."""
    start_year = year if month >= 4 else year - 1
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def due_date_for(service_type: str, month: int, year: int) -> str | None:
    day = DUE_DAY_RULES.get(service_type)
    if day is None:
        return None

    if month == 12:
        return date(year + 1, 1, day).isoformat()
    return date(year, month + 1, day).isoformat()


def generate_tasks(conn: Connection, period_id: int) -> int:
    """Create the missing tasks for a period, return how many were new.
    Safe to run any number of times, the UNIQUE constraint on
    (client_id, period_id, service_type) absorbs every rerun."""
    cursor = conn.execute(
        "INSERT OR IGNORE INTO compliance_tasks (client_id, period_id, service_type)"
        " SELECT client_id, ?, service_type FROM client_services WHERE active = 1",
        (period_id,),
    )
    created = cursor.rowcount

    period = conn.execute(
        "SELECT month, year FROM compliance_periods WHERE id = ?",
        (period_id,),
    ).fetchone()

    # Fill due dates wherever a rule exists and the task has none yet.
    # A no-op today while all rules are None, and the backfill path for
    # existing tasks once dad's answers land.
    for service_type in DUE_DAY_RULES:
        due = due_date_for(service_type, period["month"], period["year"])
        if due is not None:
            conn.execute(
                "UPDATE compliance_tasks SET due_date = ?"
                " WHERE period_id = ? AND service_type = ? AND due_date IS NULL",
                (due, period_id, service_type),
            )

    return created
