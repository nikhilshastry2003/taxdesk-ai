"""Apply pending SQL migrations, in filename order, exactly once each.

Usage:
    python3 app/db/migrate.py [path/to/database.db]

Defaults to taxdesk.db at the repo root. Applied migrations are recorded
in schema_migrations, so re-running is always safe (a no-op).
"""

import sqlite3
import sys
from pathlib import Path

# Where migration .sql files live (app/db/migrations/, next to this file)
# and where the real database sits (repo root). resolve() gives an absolute
# path so this works no matter which directory the script is run from.
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "taxdesk.db"


def connect(db_path=DEFAULT_DB_PATH):
    """Open a connection with foreign keys ON. All modules must use this,
    never sqlite3.connect directly: SQLite leaves FK enforcement off per
    connection unless this PRAGMA is set."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def applied_migrations(conn):
    """Return the set of migration filenames already applied to this DB.

    schema_migrations is the runner's own bookkeeping table: one row per
    applied migration. CREATE TABLE IF NOT EXISTS makes this safe on a
    brand-new database (first run) and a no-op on every later run.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " filename   TEXT PRIMARY KEY,"
        " applied_at TEXT NOT NULL DEFAULT (datetime('now'))"
        ")"
    )
    rows = conn.execute("SELECT filename FROM schema_migrations")
    return {row[0] for row in rows}


def migrate(conn):
    # Step 1: figure out what is pending = (all .sql files, sorted by name)
    # minus (already recorded in schema_migrations). Sorting is why the
    # files are numbered: 001_, 002_, ... guarantees apply order.
    already_applied = applied_migrations(conn)
    all_migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))
    pending = [p for p in all_migrations if p.name not in already_applied]

    # Step 2: apply each pending file, then immediately record it, then
    # commit - so a migration is never applied twice and never applied
    # without being recorded.
    for path in pending:
        conn.executescript(path.read_text())
        conn.execute(
            "INSERT INTO schema_migrations (filename) VALUES (?)", (path.name,)
        )
        conn.commit()
        print(f"applied {path.name}")

    if not pending:
        print(f"nothing to apply ({len(already_applied)} migration(s) already applied)")


if __name__ == "__main__":
    # Optional CLI argument overrides the default DB path - used by tests
    # to run against a scratch database instead of the real one.
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB_PATH
    conn = connect(db_path)
    try:
        migrate(conn)
    finally:
        conn.close()
