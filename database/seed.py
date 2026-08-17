"""Fill a development database with sample TaxDesk data.

Usage:
    python3 -m database.seed [path/to/database.db]

Development tool only, never run on a real office machine. Rerunning
is safe, every write is INSERT OR IGNORE or a deterministic UPDATE,
so a second run changes nothing.
"""

import sqlite3
import sys
from pathlib import Path

from database.migrate import DEFAULT_DB_PATH, connect, initialize

# Each entry is (name, folder_path, subscribed service names).
SEED_CLIENTS: list[tuple[str, str, list[str]]] = [
    ("Aster Traders", "D:/Clients/Aster Traders", ["GSTR-3B", "GSTR-1", "EPF", "ESI"]),
    ("Bhima Textiles", "D:/Clients/Bhima Textiles", ["GSTR-3B", "GSTR-1"]),
    ("Cauvery Mills", "D:/Clients/Cauvery Mills", ["GSTR-3B", "EPF"]),
    ("Deccan Services", "D:/Clients/Deccan Services", ["ESI"]),
    ("Everest Agencies", "D:/Clients/Everest Agencies", ["GSTR-1", "EPF", "ESI"]),
]

SEED_PERIOD = (2026, 8)


def service_id(conn: sqlite3.Connection, name: str) -> int:
    """Look up a service's id by its name.

    In: an open connection and a service name like 'GSTR-3B'.
    Out: the service's row id. Raises if the name does not exist,
    which would mean initialization never ran.
    """
    row = conn.execute(
        "SELECT ID FROM SERVICES WHERE NAME = ?",
        (name,),
    ).fetchone()
    return row[0]


def seed_clients(conn: sqlite3.Connection) -> None:
    """Insert the sample clients and their service subscriptions.

    In: an open connection on an initialized database.
    Out: nothing, existing rows are left untouched on rerun.
    """
    for name, folder_path, services in SEED_CLIENTS:
        conn.execute(
            "INSERT OR IGNORE INTO CLIENTS (NAME, FOLDER_PATH) VALUES (?, ?)",
            (name, folder_path),
        )

        client_id = conn.execute(
            "SELECT ID FROM CLIENTS WHERE FOLDER_PATH = ?",
            (folder_path,),
        ).fetchone()[0]

        for service_name in services:
            conn.execute(
                "INSERT OR IGNORE INTO CLIENT_SERVICES (CLIENT_ID, SERVICE_ID)"
                " VALUES (?, ?)",
                (client_id, service_id(conn, service_name)),
            )

    # One switched off subscription, so pages can show that state and
    # generation can prove it skips inactive rows.
    conn.execute(
        "UPDATE CLIENT_SERVICES SET ACTIVE = 0"
        " WHERE CLIENT_ID = (SELECT ID FROM CLIENTS WHERE NAME = 'Bhima Textiles')"
        " AND SERVICE_ID = (SELECT ID FROM SERVICES WHERE NAME = 'GSTR-1')",
    )


def seed_period_and_tasks(conn: sqlite3.Connection) -> None:
    """Create the sample month and generate its tasks.

    In: an open connection with clients and subscriptions present.
    Out: nothing. One task per active subscription, the UNIQUE rule
    on TASKS absorbs reruns, generating twice adds nothing.
    """
    year, month = SEED_PERIOD
    conn.execute(
        "INSERT OR IGNORE INTO PERIODS (YEAR, MONTH) VALUES (?, ?)",
        (year, month),
    )

    conn.execute(
        "INSERT OR IGNORE INTO TASKS (CLIENT_ID, SERVICE_ID, PERIOD_YEAR, PERIOD_MONTH)"
        " SELECT CLIENT_ID, SERVICE_ID, ?, ? FROM CLIENT_SERVICES WHERE ACTIVE = 1",
        (year, month),
    )


def mark_sample_statuses(conn: sqlite3.Connection) -> None:
    """Flip two tasks into interesting states for future pages.

    In: an open connection with generated tasks.
    Out: nothing, one task done with a completion trace, one not
    applicable. Reruns set the same rows to the same values.
    """
    conn.execute(
        "UPDATE TASKS SET STATUS = 'done',"
        " COMPLETED_AT = datetime('now'), COMPLETION_METHOD = 'manual'"
        " WHERE CLIENT_ID = (SELECT ID FROM CLIENTS WHERE NAME = 'Aster Traders')"
        " AND SERVICE_ID = (SELECT ID FROM SERVICES WHERE NAME = 'GSTR-3B')",
    )
    conn.execute(
        "UPDATE TASKS SET STATUS = 'not_applicable'"
        " WHERE CLIENT_ID = (SELECT ID FROM CLIENTS WHERE NAME = 'Deccan Services')"
        " AND SERVICE_ID = (SELECT ID FROM SERVICES WHERE NAME = 'ESI')",
    )


def print_summary(conn: sqlite3.Connection) -> None:
    """Print pending counts per service, the seed's proof of life.

    In: an open connection after seeding.
    Out: nothing returned, prints to the terminal.
    """
    year, month = SEED_PERIOD
    rows = conn.execute(
        "SELECT s.NAME, COUNT(*) FROM TASKS t"
        " JOIN SERVICES s ON s.ID = t.SERVICE_ID"
        " WHERE t.PERIOD_YEAR = ? AND t.PERIOD_MONTH = ? AND t.STATUS = 'pending'"
        " GROUP BY s.NAME ORDER BY s.NAME",
        (year, month),
    ).fetchall()

    print(f"pending tasks for {month} / {year}")
    total = 0
    for name, count in rows:
        print(f"  {name}: {count}")
        total += count
    print(f"  total pending: {total}")


def main() -> None:
    """Run the whole seed, initializing first so a new file works.

    In: an optional database path from the command line.
    Out: nothing, the database is filled and a summary printed.
    """
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB_PATH
    conn = connect(db_path)

    try:
        initialize(conn)

        seed_clients(conn)
        seed_period_and_tasks(conn)
        mark_sample_statuses(conn)
        conn.commit()

        print_summary(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
