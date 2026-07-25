"""Periods and their compliance tasks. Create a month, generate tasks,
mark them, close the month when done."""

from sqlite3 import Connection

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.db import queries
from app.deps import get_db, templates
from app.services.generation import financial_year, generate_tasks

ALLOWED_STATUSES = {"pending", "done", "not_applicable"}

router = APIRouter()


@router.get("/periods", response_class=HTMLResponse)
def period_list(
    request: Request,
    conn: Connection = Depends(get_db),
) -> Response:
    return templates.TemplateResponse(
        request,
        "periods.html",
        {
            "periods": queries.list_periods(conn),
            "error": request.query_params.get("error"),
        },
    )


@router.post("/periods")
async def create_period(
    request: Request,
    conn: Connection = Depends(get_db),
) -> Response:
    form = await request.form()
    try:
        month = int(str(form.get("month", "")))
        year = int(str(form.get("year", "")))
    except ValueError:
        return RedirectResponse("/periods?error=bad-input", status_code=303)

    if not (1 <= month <= 12 and 2000 <= year <= 2100):
        return RedirectResponse("/periods?error=bad-input", status_code=303)

    period_id = queries.create_period(conn, month, year, financial_year(month, year))
    return RedirectResponse(f"/periods/{period_id}", status_code=303)


@router.get("/periods/{period_id}", response_class=HTMLResponse)
def period_detail(
    request: Request,
    period_id: int,
    conn: Connection = Depends(get_db),
) -> Response:
    period = queries.get_period(conn, period_id)
    if period is None:
        raise HTTPException(status_code=404, detail="No such period")

    tasks = queries.tasks_for_period(conn, period_id)

    # Group for the template, one section per service in fixed order.
    grouped = {
        service: [task for task in tasks if task["service_type"] == service]
        for service in queries.SERVICE_TYPES
    }

    return templates.TemplateResponse(
        request,
        "period_detail.html",
        {
            "period": period,
            "grouped": grouped,
            "service_labels": queries.SERVICE_LABELS,
            "task_count": len(tasks),
            "error": request.query_params.get("error"),
        },
    )


@router.post("/periods/{period_id}/generate")
def generate(
    period_id: int,
    conn: Connection = Depends(get_db),
) -> Response:
    period = queries.get_period(conn, period_id)
    if period is None:
        raise HTTPException(status_code=404, detail="No such period")

    if period["status"] == "closed":
        return RedirectResponse(f"/periods/{period_id}?error=closed", status_code=303)

    generate_tasks(conn, period_id)
    return RedirectResponse(f"/periods/{period_id}", status_code=303)


@router.post("/periods/{period_id}/toggle-close")
def toggle_close(
    period_id: int,
    conn: Connection = Depends(get_db),
) -> Response:
    period = queries.get_period(conn, period_id)
    if period is None:
        raise HTTPException(status_code=404, detail="No such period")

    new_status = "closed" if period["status"] == "open" else "open"
    queries.set_period_status(conn, period_id, new_status)
    return RedirectResponse(f"/periods/{period_id}", status_code=303)


@router.post("/tasks/{task_id}/status")
async def set_task_status(
    request: Request,
    task_id: int,
    conn: Connection = Depends(get_db),
) -> Response:
    task = queries.get_task(conn, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="No such task")

    period = queries.get_period(conn, task["period_id"])
    if period is not None and period["status"] == "closed":
        return RedirectResponse(
            f"/periods/{task['period_id']}?error=closed",
            status_code=303,
        )

    form = await request.form()
    status = str(form.get("status", ""))
    if status not in ALLOWED_STATUSES:
        return RedirectResponse(
            f"/periods/{task['period_id']}?error=bad-status",
            status_code=303,
        )

    queries.set_task_status(conn, task_id, status)
    return RedirectResponse(f"/periods/{task['period_id']}", status_code=303)
