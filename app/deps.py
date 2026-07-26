"""Shared pieces every route module needs, the template engine and the
per request database connection."""

import os
from collections.abc import Iterator
from pathlib import Path
from sqlite3 import Connection

from fastapi.templating import Jinja2Templates

from app.db.migrate import DEFAULT_DB_PATH, connect

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates"),
)


def db_path() -> Path:
    """Decide which database file the app uses.

    In: nothing, reads the TAXDESK_DB environment variable if set,
    which is how tests point the app at a scratch database.
    Out: the path to the database file, default taxdesk.db at repo root.
    """
    return Path(os.environ.get("TAXDESK_DB", str(DEFAULT_DB_PATH)))


def get_db() -> Iterator[Connection]:
    """One connection per request. Commits only when the route finished
    without an exception, so a failed request writes nothing."""
    conn = connect(db_path())
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
