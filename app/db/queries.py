"""Every SQL statement the web app runs lives here, as small typed
functions. Routes call these and never write SQL themselves."""

from sqlite3 import Connection, Row

SERVICE_TYPES = ["GSTR_3B", "GSTR_1", "EPF", "ESI"]

# Display names are derived in code, never stored (design note 001).
SERVICE_LABELS = {
    "GSTR_3B": "GSTR-3B",
    "GSTR_1": "GSTR-1",
    "EPF": "EPF / ECR",
    "ESI": "ESI Challan / Claims",
}


def get_setting(conn: Connection, key: str) -> str | None:
    row = conn.execute(
        "SELECT value FROM settings WHERE key = ?",
        (key,),
    ).fetchone()
    return row["value"] if row else None


def set_setting(conn: Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)"
        " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


def list_clients(conn: Connection) -> list[Row]:
    return conn.execute(
        "SELECT id, name, folder_path FROM clients ORDER BY name",
    ).fetchall()


def get_client(conn: Connection, client_id: int) -> Row | None:
    return conn.execute(
        "SELECT id, name, folder_path, phone, email, notes FROM clients WHERE id = ?",
        (client_id,),
    ).fetchone()


def create_client(conn: Connection, name: str, folder_path: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO clients (name, folder_path) VALUES (?, ?)",
        (name, folder_path),
    )


def active_services(conn: Connection, client_id: int) -> set[str]:
    rows = conn.execute(
        "SELECT service_type FROM client_services WHERE client_id = ? AND active = 1",
        (client_id,),
    ).fetchall()
    return {row["service_type"] for row in rows}


def list_periods(conn: Connection) -> list[Row]:
    return conn.execute(
        "SELECT id, month, year, financial_year, status FROM compliance_periods"
        " ORDER BY year DESC, month DESC",
    ).fetchall()


def get_period(conn: Connection, period_id: int) -> Row | None:
    return conn.execute(
        "SELECT id, month, year, financial_year, status FROM compliance_periods WHERE id = ?",
        (period_id,),
    ).fetchone()


def create_period(conn: Connection, month: int, year: int, financial_year: str) -> int:
    conn.execute(
        "INSERT OR IGNORE INTO compliance_periods (month, year, financial_year)"
        " VALUES (?, ?, ?)",
        (month, year, financial_year),
    )
    row = conn.execute(
        "SELECT id FROM compliance_periods WHERE month = ? AND year = ?",
        (month, year),
    ).fetchone()
    return row["id"]


def set_period_status(conn: Connection, period_id: int, status: str) -> None:
    conn.execute(
        "UPDATE compliance_periods SET status = ? WHERE id = ?",
        (status, period_id),
    )


def tasks_for_period(conn: Connection, period_id: int) -> list[Row]:
    return conn.execute(
        "SELECT t.id, t.service_type, t.status, t.due_date, t.proof_status, c.name AS client_name"
        " FROM compliance_tasks t JOIN clients c ON c.id = t.client_id"
        " WHERE t.period_id = ?"
        " ORDER BY t.service_type, c.name",
        (period_id,),
    ).fetchall()


def get_task(conn: Connection, task_id: int) -> Row | None:
    return conn.execute(
        "SELECT id, client_id, period_id, service_type, status FROM compliance_tasks WHERE id = ?",
        (task_id,),
    ).fetchone()


def set_task_status(conn: Connection, task_id: int, status: str) -> None:
    # Done records when and how. Anything else clears both, so a task
    # moved back to pending carries no stale completion trace.
    if status == "done":
        conn.execute(
            "UPDATE compliance_tasks SET status = 'done',"
            " completed_at = datetime('now'), completed_source = 'manual'"
            " WHERE id = ?",
            (task_id,),
        )
        return

    conn.execute(
        "UPDATE compliance_tasks SET status = ?,"
        " completed_at = NULL, completed_source = NULL"
        " WHERE id = ?",
        (status, task_id),
    )


def set_service(conn: Connection, client_id: int, service_type: str, active: bool) -> None:
    # Unticking deactivates instead of deleting, so history survives
    # (design note 001, deactivation is not deletion).
    conn.execute(
        "INSERT OR IGNORE INTO client_services (client_id, service_type, active)"
        " VALUES (?, ?, 0)",
        (client_id, service_type),
    )
    conn.execute(
        "UPDATE client_services SET active = ? WHERE client_id = ? AND service_type = ?",
        (1 if active else 0, client_id, service_type),
    )
