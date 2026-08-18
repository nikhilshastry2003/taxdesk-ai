"""Initialize the TaxDesk database from database/migrations/*.sql.

Usage:
    python3 database/migrate.py [path/to/database.db]

Migrations are numbered files applied in filename order, each exactly
once per database. Safe to run any number of times. An existing
database is never recreated or deleted, the runner records what it
has applied and skips it on every later run. Applied files are
frozen, a schema change is always a new file.
"""

import re
import sqlite3
import sys
from pathlib import Path

DATABASE_DIR = Path(__file__).resolve().parent
MIGRATIONS_DIR = DATABASE_DIR / "migrations"
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

    Invariant: connections are short lived and scoped to one request
    or one script run, never shared between requests. check_same_thread
    is off because FastAPI may create and use a request's connection on
    different thread pool threads, which is safe exactly because of
    that invariant, one connection never serves two requests at once.
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def apply_one(conn: sqlite3.Connection, migration: Path) -> None:
    """Apply a single migration file and record it, atomically.

    In: an open connection and the path of one .sql migration file.
    Out: nothing. Either the migration AND its logbook record are both
    committed, or neither is.

    executescript() commits on its own, proven by test, so driver level
    commit handling cannot make the pair atomic. Instead the script
    itself carries BEGIN and COMMIT, one real SQLite transaction wraps
    the migration and its record together. Migration files must not
    manage transactions themselves.
    """
    # The filename is spliced into the script because placeholders do
    # not exist inside executescript. Names come from our own repo
    # directory, the allowlist check is defense in depth.
    if not re.fullmatch(r"[A-Za-z0-9._-]+", migration.name):
        raise ValueError(f"unsafe migration filename: {migration.name}")

    body = migration.read_text().strip()
    if not body.endswith(";"):
        body += ";"

    script = (
        "BEGIN;\n"
        f"{body}\n"
        f"INSERT INTO schema_applied (filename) VALUES ('{migration.name}');\n"
        "COMMIT;"
    )

    try:
        conn.executescript(script)
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise


def initialize(conn: sqlite3.Connection) -> bool:
    """Apply pending migrations in order, then ensure required services.

    In: an open connection from connect().
    Out: True when at least one migration was applied by this call,
    False when the database was already current. Existing data is
    never touched, and the required services are ensured on every
    call, so new entries in REQUIRED_SERVICES reach already
    initialized databases too.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_applied ("
        " filename   TEXT PRIMARY KEY,"
        " applied_at TEXT NOT NULL DEFAULT (datetime('now'))"
        ")"
    )

    already_applied = {
        row[0]
        for row in conn.execute("SELECT filename FROM schema_applied")
    }

    applied = False
    for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if migration.name in already_applied:
            continue

        apply_one(conn, migration)
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
