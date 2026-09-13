"""Onboarding, the practitioner's folders become clients, with an
explicit confirmation between discovery and creation. The filesystem
is read only here, this module never writes to disk."""

from pathlib import Path
from sqlite3 import Connection

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.deps import get_db, templates
from database import queries

router = APIRouter()


def candidate_folders(root_folder: str) -> list[Path]:
    """List the immediate subfolders of the root, nothing deeper.

    In: the configured root folder path as a string.
    Out: the immediate child directories, hidden dot folders and
    plain files excluded, sorted by name. Empty when the root has
    stopped existing or cannot be read, a directory can stat as real
    while a permission or a removable drive still blocks listing it.
    """
    root = Path(root_folder)
    if not root.is_dir():
        return []

    try:
        children = list(root.iterdir())
    except OSError:
        return []

    return sorted(
        (child for child in children
         if child.is_dir() and not child.name.startswith(".")),
        key=lambda child: child.name.lower(),
    )


def discovery_context(conn: Connection, root_folder: str | None) -> dict:
    """Build the candidate list and the button label for a root.

    In: an open connection and the currently configured root, or None.
    Out: candidates is None when no root is configured, otherwise one
    entry per immediate subfolder, existing clients marked so they
    render disabled and already ticked out of the count.
    """
    if root_folder is None:
        return {"candidates": None, "new_count": 0, "submit_label": "Add 0 clients"}

    existing_paths = {client["FOLDER_PATH"] for client in queries.list_clients(conn)}
    candidates = [
        {
            "name": folder.name,
            "existing": str(folder.resolve()) in existing_paths,
        }
        for folder in candidate_folders(root_folder)
    ]
    new_count = sum(1 for candidate in candidates if not candidate["existing"])

    return {
        "candidates": candidates,
        "new_count": new_count,
        "submit_label": f"Add {new_count} client{'' if new_count == 1 else 's'}",
    }


@router.get("/")
def home() -> RedirectResponse:
    """Send the visitor to the only page that exists so far.

    In: nothing.
    Out: a redirect to onboarding.
    """
    return RedirectResponse("/onboarding", status_code=302)


@router.get("/onboarding", response_class=HTMLResponse)
def onboarding_page(
    request: Request,
    conn: Connection = Depends(get_db),
) -> Response:
    """Show the root form, and discovery once a root is saved.

    In: nothing from the URL.
    Out: the rendered page, its candidate list marking folders that
    are already clients, new folders ticked by default.
    """
    root_folder = queries.get_root_folder(conn)

    return templates.TemplateResponse(
        request,
        "onboarding.html",
        {
            "root_folder": root_folder,
            "configured_root": root_folder,
            "error": request.query_params.get("error"),
            **discovery_context(conn, root_folder),
        },
    )


@router.post("/onboarding/root")
async def save_root(
    request: Request,
    conn: Connection = Depends(get_db),
) -> Response:
    """Validate and save the root folder, the single settings row.

    In: the submitted form with the root_folder text.
    Out: 303 back to onboarding on success. An invalid path renders
    the form again with an error and SETTINGS stays untouched.
    """
    form = await request.form()
    submitted = str(form.get("root_folder", "")).strip()

    if not submitted or not Path(submitted).is_dir():
        # Echo back exactly what was typed, so a typo can be corrected
        # in place, and keep showing the still valid saved root's own
        # discovery panel, a rejected new path never touched SETTINGS.
        configured_root = queries.get_root_folder(conn)
        return templates.TemplateResponse(
            request,
            "onboarding.html",
            {
                "root_folder": submitted,
                "configured_root": configured_root,
                "error": "That path does not exist or is not a folder. Nothing was saved.",
                **discovery_context(conn, configured_root),
            },
            status_code=400,
        )

    queries.set_root_folder(conn, str(Path(submitted).resolve()))
    return RedirectResponse("/onboarding", status_code=303)


@router.post("/onboarding/confirm")
async def confirm_clients(
    request: Request,
    conn: Connection = Depends(get_db),
) -> Response:
    """Create a client for each confirmed folder, and only for those.

    In: the submitted form with ticked folder names, untrusted.
    Out: 303 back to onboarding. The accepted set is derived from a
    fresh scan of the real root, so crafted names like ../evil or
    absolute paths never match and die silently. Existing clients are
    never touched, the UNIQUE rule absorbs any duplicate.
    """
    root_folder = queries.get_root_folder(conn)
    if root_folder is None:
        return RedirectResponse("/onboarding", status_code=303)

    actual_folders = {
        folder.name: folder for folder in candidate_folders(root_folder)
    }

    form = await request.form()
    for name in form.getlist("folders"):
        folder = actual_folders.get(str(name))
        if folder is None:
            continue

        queries.create_client(
            conn,
            name=folder.name,
            folder_path=str(folder.resolve()),
        )

    return RedirectResponse("/onboarding", status_code=303)
