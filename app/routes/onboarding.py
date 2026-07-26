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
    """List the subfolders of the root as client candidates.

    In: a connection and the root folder path.
    Out: one dict per subfolder with its name and whether a client of
    that name already exists, sorted by name.
    """
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
    """Show the onboarding page, the root form, and once a root is
    saved, the discovered folder candidates.

    In: nothing from the URL.
    Out: the rendered onboarding page.
    """
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
    """Save the root folder path after checking it really is a folder.

    In: the submitted form with the root_folder text.
    Out: a redirect back to onboarding, or the form again with an
    error when the path is not a real folder.
    """
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
    """Create a client for each ticked folder name.

    In: the submitted form with the ticked folder names.
    Out: a redirect to the client list. Names that are not really
    subfolders of the root are silently ignored.
    """
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
