"""The health route, the skeleton's only endpoint and the template
every future route file follows, parse nothing, call through the
dependency, return a plain dict."""

from sqlite3 import Connection

from fastapi import APIRouter, Depends

from app.deps import get_db

router = APIRouter()


@router.get("/health")
def health(conn: Connection = Depends(get_db)) -> dict[str, str]:
    """Report that the whole spine is alive, server to database.

    In: nothing from the caller.
    Out: exactly {"status": "ok"}, and nothing else, no paths, no
    versions, no internals. The SELECT proves SQLite is reachable,
    its result is deliberately not exposed.
    """
    conn.execute("SELECT 1")
    return {"status": "ok"}
