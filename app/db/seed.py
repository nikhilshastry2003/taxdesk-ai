"""Fill a development database with sample TaxDesk data.

Usage:
    python3 app/db/seed.py [path/to/database.db]

Development tool only, never run on the real office machine. That
database starts empty and fills through onboarding. Rerunning is safe,
every write is INSERT OR IGNORE or a deterministic UPDATE.
"""

import sys
from pathlib import Path
from sqlite3 import Connection

from migrate import DEFAULT_DB_PATH, connect, migrate

# Each entry is (name, folder_path, active services).
SeedClient = tuple[str, str, list[str]]

SEED_CLIENTS: list[SeedClient] = [
    ("ABC Traders", "D:/Clients/ABC Traders", ["GSTR_3B", "GSTR_1", "EPF", "ESI"]),
    ("Kumar Textiles", "D:/Clients/Kumar Textiles", ["GSTR_3B", "GSTR_1"]),
    ("Shree Enterprises", "D:/Clients/Shree Enterprises", ["GSTR_3B", "EPF"]),
    ("Patel and Sons", "D:/Clients/Patel and Sons", ["GSTR_1", "ESI"]),
    ("Lakshmi Traders", "D:/Clients/Lakshmi Traders", ["GSTR_3B"]),
    ("Nanda Services", "D:/Clients/Nanda Services", ["EPF", "ESI"]),
]

JULY_2026 = (7, 2026, "2026-27")


def seed_clients(conn: Connection) -> None:
    """Insert the sample clients and their services, skipping any that
    already exist.

    In: an open database connection.
    Out: nothing, rows are written into clients and client_services.
    """
    for name, folder_path, services in SEED_CLIENTS:
        conn.execute(
            "INSERT OR IGNORE INTO clients (name, folder_path) VALUES (?, ?)",
            (name, folder_path),
        )

        client_id = conn.execute(
            "SELECT id FROM clients WHERE name = ?",
            (name,),
        ).fetchone()[0]

        for service_type in services:
            conn.execute(
                "INSERT OR IGNORE INTO client_services (client_id, service_type)"
                " VALUES (?, ?)",
                (client_id, service_type),
            )


def seed_period(conn: Connection) -> int:
    """Create the July 2026 sample period, or reuse it when rerun.

    In: an open database connection.
    Out: the period's row id.
    """
    month, year, financial_year = JULY_2026

    conn.execute(
        "INSERT OR IGNORE INTO compliance_periods (month, year, financial_year)"
        " VALUES (?, ?, ?)",
        (month, year, financial_year),
    )

    return conn.execute(
        "SELECT id FROM compliance_periods WHERE month = ? AND year = ?",
        (month, year),
    ).fetchone()[0]


def generate_tasks(conn: Connection, period_id: int) -> None:
    """Create one pending task per client per active service.

    In: a connection and the period row id to generate for.
    Out: nothing, missing task rows are inserted, existing ones kept.
    """
    # The same query v0.4 will use in the app. OR IGNORE plus the UNIQUE
    # constraint on (client_id, period_id, service_type) makes a second
    # run insert nothing.
    conn.execute(
        "INSERT OR IGNORE INTO compliance_tasks (client_id, period_id, service_type)"
        " SELECT client_id, ?, service_type FROM client_services WHERE active = 1",
        (period_id,),
    )


def mark_sample_statuses(conn: Connection, period_id: int) -> None:
    """Flip a couple of sample tasks into interesting states.

    In: a connection and the period row id.
    Out: nothing, one task becomes done, one gets a detected proof.
    """
    # One done task and one detected proof, so every page state has data
    # to show while the UI is being built.
    conn.execute(
        "UPDATE compliance_tasks"
        " SET status = 'done',"
        "     completed_at = datetime('now'),"
        "     completed_source = 'manual'"
        " WHERE period_id = ? AND service_type = 'GSTR_3B'"
        " AND client_id = (SELECT id FROM clients WHERE name = 'ABC Traders')",
        (period_id,),
    )

    conn.execute(
        "UPDATE compliance_tasks"
        " SET proof_status = 'detected',"
        "     proof_file_path = 'D:/Clients/Kumar Textiles/2026-27/GSTR3B_July2026.pdf'"
        " WHERE period_id = ? AND service_type = 'GSTR_3B'"
        " AND client_id = (SELECT id FROM clients WHERE name = 'Kumar Textiles')",
        (period_id,),
    )


def print_dashboard(conn: Connection, period_id: int) -> None:
    """Print the pending counts per service, the seed's proof of life.

    In: a connection and the period row id.
    Out: nothing returned, prints counts to the terminal.
    """
    rows = conn.execute(
        "SELECT service_type, COUNT(*) FROM compliance_tasks"
        " WHERE period_id = ? AND status = 'pending'"
        " GROUP BY service_type ORDER BY service_type",
        (period_id,),
    ).fetchall()

    print("pending tasks for July 2026")
    for service_type, count in rows:
        print(f"  {service_type}: {count}")

    total = sum(count for _, count in rows)
    print(f"  total pending: {total}")


def main() -> None:
    """Run the whole seed, migrate first so a brand new file works.

    In: an optional database path from the command line.
    Out: nothing, the database is filled and counts are printed.
    """
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB_PATH
    conn = connect(db_path)

    try:
        # Migrations first, so seeding works on a brand new database file.
        migrate(conn)

        seed_clients(conn)
        period_id = seed_period(conn)
        generate_tasks(conn, period_id)
        mark_sample_statuses(conn, period_id)
        conn.commit()

        print_dashboard(conn, period_id)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
