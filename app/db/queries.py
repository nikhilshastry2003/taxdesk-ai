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
