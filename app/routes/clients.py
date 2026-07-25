"""Client list, client detail, and service configuration."""

from sqlite3 import Connection

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.db import queries
from app.deps import get_db, templates

router = APIRouter()


@router.get("/")
def home(conn: Connection = Depends(get_db)) -> RedirectResponse:
    if queries.get_setting(conn, "root_folder") is None:
        return RedirectResponse("/onboarding", status_code=302)
    return RedirectResponse("/clients", status_code=302)


@router.get("/clients", response_class=HTMLResponse)
def client_list(
    request: Request,
    conn: Connection = Depends(get_db),
) -> Response:
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
    client = queries.get_client(conn, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="No such client")

    return templates.TemplateResponse(
        request,
        "client_detail.html",
        {
            "client": client,
            "service_types": queries.SERVICE_TYPES,
            "service_labels": queries.SERVICE_LABELS,
            "active": queries.active_services(conn, client_id),
        },
    )


@router.post("/clients/{client_id}/services")
async def save_services(
    request: Request,
    client_id: int,
    conn: Connection = Depends(get_db),
) -> Response:
    if queries.get_client(conn, client_id) is None:
        raise HTTPException(status_code=404, detail="No such client")

    form = await request.form()
    ticked = set(form.getlist("services"))
    for service_type in queries.SERVICE_TYPES:
        queries.set_service(conn, client_id, service_type, service_type in ticked)

    return RedirectResponse(f"/clients/{client_id}", status_code=303)
