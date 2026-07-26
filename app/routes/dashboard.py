"""Dashboard, the glance page, and Priority, the same truth as a
working list. Both read only, both built on the same query functions."""

from sqlite3 import Connection, Row

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response

from app.db import queries
from app.deps import get_db, templates

router = APIRouter()


def pick_period(request: Request, conn: Connection) -> Row | None:
    """Decide which period the page is about.

    In: the request (may carry ?period=<id> in the URL) and a connection.
    Out: the period row from the URL when it is valid, otherwise the
    default period, or None when no periods exist at all.
    """
    raw = request.query_params.get("period")
    if raw is not None:
        try:
            period = queries.get_period(conn, int(raw))
        except ValueError:
            period = None
        if period is not None:
            return period
    return queries.default_period(conn)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    conn: Connection = Depends(get_db),
) -> Response:
    """Show the Dashboard page, the pending counts per service, the
    total, and the list of clients with pending work.

    In: the request, optional ?period=<id> in the URL.
    Out: the rendered Dashboard page for that period.
    """
    period = pick_period(request, conn)

    counts: dict[str, int] = {}
    total = 0
    clients: list[Row] = []
    if period is not None:
        counts = queries.pending_counts(conn, period["id"])
        total = sum(counts.values())
        clients = queries.pending_clients(conn, period["id"])

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "period": period,
            "periods": queries.list_periods(conn),
            "counts": counts,
            "total": total,
            "pending_clients": clients,
            "service_labels": queries.SERVICE_LABELS,
        },
    )


@router.get("/priority", response_class=HTMLResponse)
def priority(
    request: Request,
    conn: Connection = Depends(get_db),
) -> Response:
    """Show the Priority page, pending tasks grouped by service, and
    when filtered to one service it doubles as that service's own page.

    In: the request, optional ?period=<id>, ?service=<type>, ?q=<text>.
    Out: the rendered Priority page, all four sections, or one section
    when a valid service filter is present.
    """
    period = pick_period(request, conn)

    service = request.query_params.get("service")
    if service not in queries.SERVICE_TYPES:
        service = None

    search = request.query_params.get("q", "").strip() or None

    sections: dict[str, list[Row]] = {}
    counts: dict[str, int] = {}
    if period is not None:
        tasks = queries.pending_tasks(conn, period["id"], service, search)
        shown_services = [service] if service else queries.SERVICE_TYPES
        sections = {
            name: [task for task in tasks if task["service_type"] == name]
            for name in shown_services
        }
        counts = queries.pending_counts(conn, period["id"])

    return templates.TemplateResponse(
        request,
        "priority.html",
        {
            "period": period,
            "periods": queries.list_periods(conn),
            "sections": sections,
            "counts": counts,
            "service": service,
            "search": search or "",
            "service_labels": queries.SERVICE_LABELS,
        },
    )
