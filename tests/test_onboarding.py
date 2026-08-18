"""Tests for onboarding, discovery, confirmation, and its trust
boundary. Everything runs on temp folders and temp databases."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from database.migrate import connect


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """Give a test a running app over a fresh temp database.

    In: pytest's tmp_path.
    Out: a TestClient with startup done, migrations applied.
    """
    application = create_app(tmp_path / "test.db")
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """Give a test a realistic root folder on disk.

    In: pytest's tmp_path.
    Out: a root containing three client folders, one hidden folder,
    and one plain file.
    """
    folder = tmp_path / "clients"
    folder.mkdir()
    (folder / "Aster Traders").mkdir()
    (folder / "Bhima Textiles").mkdir()
    (folder / "Cauvery Mills").mkdir()
    (folder / ".hidden").mkdir()
    (folder / "loose_file.txt").write_text("not a folder")
    return folder


def saved_root(client: TestClient, tmp_path: Path) -> str | None:
    """Read ROOT_FOLDER straight from the test database.

    In: the test client fixture's paired tmp_path.
    Out: the stored value, or None when no row exists.
    """
    conn = connect(tmp_path / "test.db")
    row = conn.execute("SELECT ROOT_FOLDER FROM SETTINGS WHERE ID = 1").fetchone()
    conn.close()
    return row["ROOT_FOLDER"] if row else None


def client_rows(tmp_path: Path) -> list[tuple[str, str]]:
    """Read all clients straight from the test database.

    In: the test's tmp_path.
    Out: (name, folder_path) pairs ordered by name.
    """
    conn = connect(tmp_path / "test.db")
    rows = conn.execute(
        "SELECT NAME, FOLDER_PATH FROM CLIENTS ORDER BY NAME"
    ).fetchall()
    conn.close()
    return [(row["NAME"], row["FOLDER_PATH"]) for row in rows]


def test_onboarding_without_root_asks_for_one(client: TestClient) -> None:
    """No configured root shows the form and no candidate list."""
    response = client.get("/onboarding")

    assert response.status_code == 200
    assert 'name="root_folder"' in response.text
    assert "Select the folders" not in response.text


def test_valid_root_is_saved_and_redirects_303(
    client: TestClient, root: Path, tmp_path: Path
) -> None:
    """A real directory is persisted and the POST answers 303."""
    response = client.post(
        "/onboarding/root", data={"root_folder": str(root)}, follow_redirects=False
    )

    assert response.status_code == 303
    assert saved_root(client, tmp_path) == str(root.resolve())


def test_invalid_root_rejected_and_settings_untouched(
    client: TestClient, tmp_path: Path
) -> None:
    """A nonexistent path renders an error and saves nothing."""
    response = client.post(
        "/onboarding/root",
        data={"root_folder": str(tmp_path / "nope")},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert "Nothing was saved" in response.text
    assert saved_root(client, tmp_path) is None


def test_discovery_lists_immediate_folders_only(
    client: TestClient, root: Path
) -> None:
    """Subfolders appear, files and hidden folders and nested
    directories do not."""
    (root / "Aster Traders" / "Nested").mkdir()
    client.post("/onboarding/root", data={"root_folder": str(root)})

    page = client.get("/onboarding").text

    for name in ("Aster Traders", "Bhima Textiles", "Cauvery Mills"):
        assert name in page
    assert "loose_file.txt" not in page
    assert ".hidden" not in page
    assert "Nested" not in page


def test_new_candidates_are_checked_by_default(
    client: TestClient, root: Path
) -> None:
    """Every new folder's checkbox carries the checked attribute and
    the button says how many clients it will add."""
    client.post("/onboarding/root", data={"root_folder": str(root)})

    page = client.get("/onboarding").text

    assert page.count("checked") == 3
    assert "Add 3 clients" in page


def test_confirm_creates_exactly_the_selected_clients(
    client: TestClient, root: Path, tmp_path: Path
) -> None:
    """Two ticked folders become two clients with absolute paths, the
    unticked one does not."""
    client.post("/onboarding/root", data={"root_folder": str(root)})

    response = client.post(
        "/onboarding/confirm",
        data={"folders": ["Aster Traders", "Cauvery Mills"]},
        follow_redirects=False,
    )

    assert response.status_code == 303
    rows = client_rows(tmp_path)
    assert rows == [
        ("Aster Traders", str((root / "Aster Traders").resolve())),
        ("Cauvery Mills", str((root / "Cauvery Mills").resolve())),
    ]
    assert all(Path(path).is_absolute() for _, path in rows)


def test_existing_clients_marked_and_not_duplicated(
    client: TestClient, root: Path, tmp_path: Path
) -> None:
    """After a confirmation, rerunning shows already added and a second
    confirm changes nothing."""
    client.post("/onboarding/root", data={"root_folder": str(root)})
    client.post("/onboarding/confirm", data={"folders": ["Aster Traders"]})

    page = client.get("/onboarding").text
    assert "(already added)" in page
    assert "Add 2 clients" in page

    before = client_rows(tmp_path)
    client.post(
        "/onboarding/confirm",
        data={"folders": ["Aster Traders"]},
    )
    assert client_rows(tmp_path) == before


def test_traversal_names_cannot_create_clients(
    client: TestClient, root: Path, tmp_path: Path
) -> None:
    """Crafted names die silently, only real subfolders count."""
    outside = tmp_path / "outside"
    outside.mkdir()
    client.post("/onboarding/root", data={"root_folder": str(root)})

    client.post(
        "/onboarding/confirm",
        data={"folders": ["../outside", str(outside), "no_such_folder"]},
    )

    assert client_rows(tmp_path) == []


def test_empty_root_is_handled_cleanly(
    client: TestClient, tmp_path: Path
) -> None:
    """An empty root saves fine and the page says so plainly."""
    empty = tmp_path / "empty"
    empty.mkdir()

    client.post("/onboarding/root", data={"root_folder": str(empty)})
    page = client.get("/onboarding").text

    assert "No folders found inside the root" in page


def test_changing_root_keeps_existing_client_paths(
    client: TestClient, root: Path, tmp_path: Path
) -> None:
    """A new root never rewrites paths recorded under the old one."""
    client.post("/onboarding/root", data={"root_folder": str(root)})
    client.post("/onboarding/confirm", data={"folders": ["Aster Traders"]})
    before = client_rows(tmp_path)

    other = tmp_path / "other_root"
    other.mkdir()
    (other / "Deccan Services").mkdir()
    client.post("/onboarding/root", data={"root_folder": str(other)})

    assert client_rows(tmp_path) == before
    assert saved_root(client, tmp_path) == str(other.resolve())


def test_home_redirects_to_onboarding(client: TestClient) -> None:
    """The root URL points at the only page that exists."""
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/onboarding"
