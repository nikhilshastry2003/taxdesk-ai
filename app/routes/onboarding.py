"""Root folder onboarding. Dad points TaxDesk at his client root once,
the subfolders become client candidates, he confirms which are real."""

from pathlib import Path
from sqlite3 import Connection

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.db import queries
from app.deps import get_db, templates

router = APIRouter()


def folder_candidates(conn: Connection, root: str) -> list[dict[str, object]]:
    existing = {client["name"] for client in queries.list_clients(conn)}
    subfolders = sorted(
        (entry for entry in Path(root).iterdir() if entry.is_dir()),
        key=lambda entry: entry.name.lower(),
    )
    return [
        {"name": folder.name, "existing": folder.name in existing}
        for folder in subfolders
    ]


@router.get("/onboarding", response_class=HTMLResponse)
def onboarding_page(
    request: Request,
    conn: Connection = Depends(get_db),
) -> Response:
    root = queries.get_setting(conn, "root_folder")
    candidates = folder_candidates(conn, root) if root else None
    return templates.TemplateResponse(
        request,
        "onboarding.html",
        {
            "root_folder": root,
            "candidates": candidates,
            "error": None,
        },
    )


@router.post("/onboarding/root")
async def save_root(
    request: Request,
    conn: Connection = Depends(get_db),
) -> Response:
    form = await request.form()
    root = str(form.get("root_folder", "")).strip()

    if not Path(root).is_dir():
        return templates.TemplateResponse(
            request,
            "onboarding.html",
            {
                "root_folder": root,
                "candidates": None,
                "error": "That path does not exist or is not a folder.",
            },
            status_code=400,
        )

    queries.set_setting(conn, "root_folder", root)
    return RedirectResponse("/onboarding", status_code=303)


@router.post("/onboarding/confirm")
async def confirm_clients(
    request: Request,
    conn: Connection = Depends(get_db),
) -> Response:
    root = queries.get_setting(conn, "root_folder")
    if root is None:
        return RedirectResponse("/onboarding", status_code=303)

    # Only names that really are subfolders of the root may become
    # clients. Form input crosses a trust boundary, even on localhost.
    valid_names = {candidate["name"] for candidate in folder_candidates(conn, root)}

    form = await request.form()
    for name in form.getlist("folders"):
        if name in valid_names:
            queries.create_client(conn, str(name), str(Path(root) / str(name)))

    return RedirectResponse("/clients", status_code=303)
