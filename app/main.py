"""TaxDesk application entry point.

Run locally, and only locally:

    venv/bin/uvicorn app.main:app

uvicorn binds 127.0.0.1 by default, never pass a host flag. The
security boundary of this local first app is that it listens on
localhost only.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.routes.health import router as health_router
from app.routes.onboarding import router as onboarding_router
from database.migrate import DEFAULT_DB_PATH, connect, initialize


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Run migrations once before the first request is served.

    In: the FastAPI app, whose state carries the database path.
    Out: yields while the app serves. The startup connection is
    closed immediately, requests always get their own.
    """
    conn = connect(application.state.db_path)
    try:
        initialize(conn)
    finally:
        conn.close()
    yield


def create_app(db_path: Path = DEFAULT_DB_PATH) -> FastAPI:
    """Build the application around one database path.

    In: the database file path, tests pass a temp path, production
    uses the default.
    Out: a FastAPI app with migrations wired into startup and the
    routes plugged in.
    """
    application = FastAPI(lifespan=lifespan)
    application.state.db_path = db_path
    application.include_router(health_router)
    application.include_router(onboarding_router)
    return application


app = create_app()
