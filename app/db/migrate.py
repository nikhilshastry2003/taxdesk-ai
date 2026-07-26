"""Apply pending SQL migrations, in filename order, exactly once each.

Usage:
    python3 app/db/migrate.py [path/to/database.db]

Defaults to taxdesk.db at the repo root. Applied migrations are recorded
in schema_migrations, so re-running is always safe (a no-op).
"""

import sqlite3
import sys
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "taxdesk.db"


def connect(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """The only sanctioned way to open the database. SQLite leaves foreign
    key enforcement off on every new connection, so all code must come
    through here to get PRAGMA foreign_keys = ON. Rows come back as
    sqlite3.Row, readable by column name."""
    # check_same_thread off because FastAPI may open a connection on one
    # thread and use it on another within the same request. Safe as long
    # as a connection stays inside one request or one script run.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def applied_migrations(conn: sqlite3.Connection) -> set[str]:
    """Read the logbook of migrations this database has already run.
    Creates the logbook table itself on a brand new database.

    In: an open database connection.
    Out: the set of already applied filenames, empty on a fresh db.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " filename   TEXT PRIMARY KEY,"
        " applied_at TEXT NOT NULL DEFAULT (datetime('now'))"
        ")"
    )
    rows = conn.execute("SELECT filename FROM schema_migrations")
    return {row[0] for row in rows}


def migrate(conn: sqlite3.Connection) -> None:
    """Apply every migration file this database has not run yet, in
    filename order, and record each one. Running it again is a no-op.

    In: an open database connection.
    Out: nothing returned, prints what was applied or that nothing was.
    """
    already_applied = applied_migrations(conn)
    all_migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))
    pending = [
        migration
        for migration in all_migrations
        if migration.name not in already_applied
    ]

    if not pending:
        print(f"nothing to apply ({len(already_applied)} migration(s) already applied)")
        return

    for migration in pending:
        # Record and commit immediately after executing, so a migration can
        # never run twice and never run unrecorded.
        conn.executescript(migration.read_text())
        conn.execute(
            "INSERT INTO schema_migrations (filename) VALUES (?)",
            (migration.name,),
        )
        conn.commit()
        print(f"applied {migration.name}")


if __name__ == "__main__":
    # An argument targets a scratch database, keeping tests off the real one.
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB_PATH
    conn = connect(db_path)
    try:
        migrate(conn)
    finally:
        conn.close()
