"""Shared pieces route modules need, today only the database
dependency. Every route gets its own short lived connection through
the single sanctioned connect(), and never anything else."""

from collections.abc import Iterator
from sqlite3 import Connection

from fastapi import Request

from database.migrate import connect


def get_db(request: Request) -> Iterator[Connection]:
    """Hand one request one database connection, then close it.

    In: the current request, whose app state carries the database
    path, set once in create_app.
    Out: yields an open connection for exactly this request, closed
    when the request ends. Commit handling arrives with the first
    write route, nothing here writes yet.
    """
    conn = connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()
