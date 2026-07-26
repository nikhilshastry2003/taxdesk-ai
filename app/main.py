"""TaxDesk web app.

Run from the repo root:
    venv/bin/uvicorn app.main:app --reload
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.migrate import connect, migrate
from app.deps import db_path
from app.routes.clients import router as clients_router
from app.routes.dashboard import router as dashboard_router
from app.routes.onboarding import router as onboarding_router
from app.routes.periods import router as periods_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run once around the app's life, migrations before it serves.

    In: the FastAPI app being started.
    Out: yields control while the app runs, nothing to clean up after.
    """
    # Migrations run at startup, so installing and opening the app is
    # all a user ever does. The runner is idempotent, a normal start
    # with nothing pending applies nothing.
    conn = connect(db_path())
    try:
        migrate(conn)
    finally:
        conn.close()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(onboarding_router)
app.include_router(clients_router)
app.include_router(periods_router)
app.include_router(dashboard_router)
