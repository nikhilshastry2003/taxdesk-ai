"""Client list, client detail, and service configuration."""

from sqlite3 import Connection

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.db import queries
from app.deps import get_db, templates

router = APIRouter()


@router.get("/")
def home(conn: Connection = Depends(get_db)) -> RedirectResponse:
    """Send the visitor to the right start page.

    In: nothing from the user, just the connection.
    Out: a redirect, to onboarding when no root folder is saved yet,
    otherwise to the Dashboard.
    """
    if queries.get_setting(conn, "root_folder") is None:
        return RedirectResponse("/onboarding", status_code=302)
    return RedirectResponse("/dashboard", status_code=302)


@router.get("/clients", response_class=HTMLResponse)
def client_list(
    request: Request,
    conn: Connection = Depends(get_db),
) -> Response:
    """Show the client list page.

    In: nothing from the URL.
    Out: the rendered list of all clients.
    """
    return templates.TemplateResponse(
        request,
        "clients.html",
        {"clients": queries.list_clients(conn)},
    )


@router.get("/clients/{client_id}", response_class=HTMLResponse)
def client_detail(
    request: Request,
    client_id: int,
    conn: Connection = Depends(get_db),
) -> Response:
    """Show one client, its folder, its service ticks, and its pending
    tasks for the period in context.

    In: the client id from the URL, optional ?period=<id>.
    Out: the rendered client page, or 404 when the id does not exist.
    """
    client = queries.get_client(conn, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="No such client")

    # Which period the pending section is about, ?period=<id> from a
    # Dashboard click, else the default period.
    raw_period = request.query_params.get("period")
    period = None
    if raw_period is not None:
        try:
            period = queries.get_period(conn, int(raw_period))
        except ValueError:
            period = None
    if period is None:
        period = queries.default_period(conn)

    pending = (
        queries.client_pending_tasks(conn, client_id, period["id"])
        if period is not None
        else []
    )

    return templates.TemplateResponse(
        request,
        "client_detail.html",
        {
            "client": client,
            "service_types": queries.SERVICE_TYPES,
            "service_labels": queries.SERVICE_LABELS,
            "active": queries.active_services(conn, client_id),
            "period": period,
            "pending": pending,
        },
    )


@router.post("/clients/{client_id}/services")
async def save_services(
    request: Request,
    client_id: int,
    conn: Connection = Depends(get_db),
) -> Response:
    """Save the service checkboxes for one client. Ticked services are
    switched on, everything unticked is switched off, never deleted.

    In: the client id from the URL and the submitted checkbox form.
    Out: a redirect back to the client page, or 404 for a bad id.
    """
    if queries.get_client(conn, client_id) is None:
        raise HTTPException(status_code=404, detail="No such client")

    form = await request.form()
    ticked = set(form.getlist("services"))
    for service_type in queries.SERVICE_TYPES:
        queries.set_service(conn, client_id, service_type, service_type in ticked)

    return RedirectResponse(f"/clients/{client_id}", status_code=303)
