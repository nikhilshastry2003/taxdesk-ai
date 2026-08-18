"""Shared pieces route modules need, the database dependency and the
template engine. Every route gets its own short lived connection
through the single sanctioned connect(), and never anything else."""

from collections.abc import Iterator
from pathlib import Path
from sqlite3 import Connection

from fastapi import Request
from fastapi.templating import Jinja2Templates

from database.migrate import connect

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


def get_db(request: Request) -> Iterator[Connection]:
    """Hand one request one database connection with honest teardown.

    In: the current request, whose app state carries the database
    path, set once in create_app.
    Out: yields an open connection for exactly this request. A route
    that finishes cleanly gets its writes committed, a route that
    raises gets them rolled back, and the connection always closes.
    """
    conn = connect(request.app.state.db_path)
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
