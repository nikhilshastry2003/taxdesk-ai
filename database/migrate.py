"""Initialize the TaxDesk database from database/schema.sql.

Usage:
    python3 database/migrate.py [path/to/database.db]

Safe to run any number of times. An existing database is never
recreated or deleted, the runner records what it has applied and
skips it on every later run.
"""

import sqlite3
import sys
from pathlib import Path

DATABASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = DATABASE_DIR / "schema.sql"
DEFAULT_DB_PATH = DATABASE_DIR / "taxdesk.db"

# Required reference data, not structure and not fake seed data. The
# product is meaningless without these filing types. Ensured on every
# initialize call, so adding a name here reaches databases that were
# initialized before it existed, without touching schema.sql.
REQUIRED_SERVICES = ["GSTR-3B", "GSTR-1", "EPF", "ESI"]


def connect(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open the database, creating the file when it does not exist.

    In: the database file path, defaults to database/taxdesk.db.
    Out: an open connection with foreign key enforcement on.

    SQLite keeps foreign keys off per connection unless asked, so this
    function is the only sanctioned way to open the database. Code
    that calls sqlite3.connect directly loses that enforcement.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize(conn: sqlite3.Connection) -> bool:
    """Apply schema.sql exactly once, then ensure required services.

    In: an open connection from connect().
    Out: True when the schema was applied by this call, False when a
    previous run already had. Existing data is never touched, and the
    required services are ensured on every call, so new entries in
    REQUIRED_SERVICES reach already initialized databases too.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_applied ("
        " filename   TEXT PRIMARY KEY,"
        " applied_at TEXT NOT NULL DEFAULT (datetime('now'))"
        ")"
    )

    already_applied = conn.execute(
        "SELECT 1 FROM schema_applied WHERE filename = ?",
        (SCHEMA_PATH.name,),
    ).fetchone()

    applied = False
    if not already_applied:
        # Apply then record inside one commit, so a crash between the
        # two can never leave the database lying about itself.
        conn.executescript(SCHEMA_PATH.read_text())
        conn.execute(
            "INSERT INTO schema_applied (filename) VALUES (?)",
            (SCHEMA_PATH.name,),
        )
        applied = True

    for name in REQUIRED_SERVICES:
        conn.execute(
            "INSERT OR IGNORE INTO SERVICES (NAME) VALUES (?)",
            (name,),
        )
    conn.commit()

    return applied


if __name__ == "__main__":
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB_PATH
    conn = connect(db_path)
    try:
        applied = initialize(conn)
        print("schema applied" if applied else "already initialized, nothing to do")
    finally:
        conn.close()
