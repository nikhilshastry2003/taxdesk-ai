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
    """Read one app level setting, like the root folder path.

    In: a connection and the setting's key, for example 'root_folder'.
    Out: the stored value, or None when the key was never saved.
    """
    row = conn.execute(
        "SELECT value FROM settings WHERE key = ?",
        (key,),
    ).fetchone()
    return row["value"] if row else None


def set_setting(conn: Connection, key: str, value: str) -> None:
    """Save one app level setting, overwriting any previous value.

    In: a connection, the key, and the new value.
    Out: nothing, the row is inserted or updated in place.
    """
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)"
        " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


def list_clients(conn: Connection) -> list[Row]:
    """List every client for the Clients page.

    In: a database connection.
    Out: all client rows with id, name, folder path, ordered by name.
    """
    return conn.execute(
        "SELECT id, name, folder_path FROM clients ORDER BY name",
    ).fetchall()


def get_client(conn: Connection, client_id: int) -> Row | None:
    """Fetch one client by id.

    In: a connection and the client row id.
    Out: the client row, or None when the id does not exist.
    """
    return conn.execute(
        "SELECT id, name, folder_path, phone, email, notes FROM clients WHERE id = ?",
        (client_id,),
    ).fetchone()


def create_client(conn: Connection, name: str, folder_path: str) -> None:
    """Create a client unless one with the same name already exists.

    In: a connection, the client name, and its folder path on disk.
    Out: nothing, an existing name is left untouched (no duplicates).
    """
    conn.execute(
        "INSERT OR IGNORE INTO clients (name, folder_path) VALUES (?, ?)",
        (name, folder_path),
    )


def active_services(conn: Connection, client_id: int) -> set[str]:
    """Find which services are currently switched on for one client.

    In: a connection and the client row id.
    Out: a set of service type names, for example {'GSTR_3B', 'EPF'}.
    """
    rows = conn.execute(
        "SELECT service_type FROM client_services WHERE client_id = ? AND active = 1",
        (client_id,),
    ).fetchall()
    return {row["service_type"] for row in rows}


def list_periods(conn: Connection) -> list[Row]:
    """List every tracked month, newest first.

    In: a database connection.
    Out: period rows with id, month, year, financial year, status.
    """
    return conn.execute(
        "SELECT id, month, year, financial_year, status FROM compliance_periods"
        " ORDER BY year DESC, month DESC",
    ).fetchall()


def get_period(conn: Connection, period_id: int) -> Row | None:
    """Fetch one period by id.

    In: a connection and the period row id.
    Out: the period row, or None when the id does not exist.
    """
    return conn.execute(
        "SELECT id, month, year, financial_year, status FROM compliance_periods WHERE id = ?",
        (period_id,),
    ).fetchone()


def create_period(conn: Connection, month: int, year: int, financial_year: str) -> int:
    """Create a month for tracking, or return the existing one, since a
    month can only exist once.

    In: a connection, month 1 to 12, a four digit year, and the already
    computed financial year text.
    Out: the period row id, new or existing.
    """
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
    """Open or close a period.

    In: a connection, the period row id, and 'open' or 'closed'.
    Out: nothing, the period row is updated.
    """
    conn.execute(
        "UPDATE compliance_periods SET status = ? WHERE id = ?",
        (status, period_id),
    )


def tasks_for_period(conn: Connection, period_id: int) -> list[Row]:
    """List every task of one period, all statuses, with client names,
    for the period page table.

    In: a connection and the period row id.
    Out: task rows ordered by service then client name.
    """
    return conn.execute(
        "SELECT t.id, t.service_type, t.status, t.due_date, t.proof_status, c.name AS client_name"
        " FROM compliance_tasks t JOIN clients c ON c.id = t.client_id"
        " WHERE t.period_id = ?"
        " ORDER BY t.service_type, c.name",
        (period_id,),
    ).fetchall()


def default_period(conn: Connection) -> Row | None:
    """Pick which period the pages show when the user has not chosen one.
    The newest open period wins, a newer but closed one does not.

    In: a database connection.
    Out: the chosen period row, or None when no periods exist yet.
    """
    return conn.execute(
        "SELECT id, month, year, financial_year, status FROM compliance_periods"
        " ORDER BY (status = 'open') DESC, year DESC, month DESC LIMIT 1",
    ).fetchone()


def pending_counts(conn: Connection, period_id: int) -> dict[str, int]:
    """Count how many tasks are still pending in one period, split by
    service type. These are the numbers the Dashboard shows.

    In: a database connection and the period row id.
    Out: a dict with every service present, zero included, for example
    {'GSTR_3B': 3, 'GSTR_1': 0, 'EPF': 1, 'ESI': 0}.
    """
    counts = {service: 0 for service in SERVICE_TYPES}
    rows = conn.execute(
        "SELECT service_type, COUNT(*) AS n FROM compliance_tasks"
        " WHERE period_id = ? AND status = 'pending'"
        " GROUP BY service_type",
        (period_id,),
    )
    for row in rows:
        counts[row["service_type"]] = row["n"]
    return counts


def pending_tasks(
    conn: Connection,
    period_id: int,
    service_type: str | None = None,
    search: str | None = None,
) -> list[Row]:
    """List the pending tasks of one period, each with its client name.
    The Dashboard counts use the same conditions, so the numbers there
    and the rows here always agree.

    In: a connection, the period row id, and two optional filters,
    a single service type and a client name search text.
    Out: task rows joined with client names, ordered by service then
    client name.
    """
    sql = (
        "SELECT t.id, t.service_type, t.due_date, t.proof_status,"
        " c.id AS client_id, c.name AS client_name"
        " FROM compliance_tasks t JOIN clients c ON c.id = t.client_id"
        " WHERE t.period_id = ? AND t.status = 'pending'"
    )
    params: list[object] = [period_id]

    if service_type is not None:
        sql += " AND t.service_type = ?"
        params.append(service_type)
    if search:
        sql += " AND c.name LIKE ? COLLATE NOCASE"
        params.append(f"%{search}%")

    sql += " ORDER BY t.service_type, c.name"
    return conn.execute(sql, params).fetchall()


def pending_clients(conn: Connection, period_id: int) -> list[Row]:
    """List the clients that still have pending work in one period.

    In: a database connection and the period row id.
    Out: one row per client with id, name, and how many of its tasks
    are still pending, ordered by name.
    """
    return conn.execute(
        "SELECT c.id, c.name, COUNT(*) AS pending"
        " FROM compliance_tasks t JOIN clients c ON c.id = t.client_id"
        " WHERE t.period_id = ? AND t.status = 'pending'"
        " GROUP BY c.id ORDER BY c.name",
        (period_id,),
    ).fetchall()


def client_pending_tasks(conn: Connection, client_id: int, period_id: int) -> list[Row]:
    """List one client's pending tasks for one period, shown on the
    client page when opened from Dashboard or Priority.

    In: a connection, the client row id, and the period row id.
    Out: that client's pending task rows, ordered by service.
    """
    return conn.execute(
        "SELECT id, service_type, due_date, proof_status FROM compliance_tasks"
        " WHERE client_id = ? AND period_id = ? AND status = 'pending'"
        " ORDER BY service_type",
        (client_id, period_id),
    ).fetchall()


def get_task(conn: Connection, task_id: int) -> Row | None:
    """Fetch one task by id.

    In: a connection and the task row id.
    Out: the task row, or None when the id does not exist.
    """
    return conn.execute(
        "SELECT id, client_id, period_id, service_type, status FROM compliance_tasks WHERE id = ?",
        (task_id,),
    ).fetchone()


def set_task_status(conn: Connection, task_id: int, status: str) -> None:
    """Change a task's status, keeping the completion trace honest.

    In: a connection, the task row id, and one of 'pending', 'done',
    'not_applicable'.
    Out: nothing, the task row is updated.
    """
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
    """Switch one service on or off for one client.

    In: a connection, the client row id, the service type, and True
    for on, False for off.
    Out: nothing, the row is created if needed and its flag updated.
    """
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
