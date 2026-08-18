"""Every SQL statement the application runs, as small typed functions.

Routes call these and never write SQL themselves. Only the functions a
shipped feature genuinely needs live here, nothing speculative.
"""

from sqlite3 import Connection, Row


def get_root_folder(conn: Connection) -> str | None:
    """Read the configured root client folder.

    In: an open connection.
    Out: the stored path, or None when onboarding never saved one,
    which is the app's definition of not configured yet.
    """
    row = conn.execute("SELECT ROOT_FOLDER FROM SETTINGS WHERE ID = 1").fetchone()
    return row["ROOT_FOLDER"] if row else None


def set_root_folder(conn: Connection, root_folder: str) -> None:
    """Save or replace the root client folder, the single settings row.

    In: an open connection and a validated directory path.
    Out: nothing, the one allowed row is created or updated in place.
    """
    conn.execute(
        "INSERT INTO SETTINGS (ID, ROOT_FOLDER) VALUES (1, ?)"
        " ON CONFLICT(ID) DO UPDATE SET ROOT_FOLDER = excluded.ROOT_FOLDER",
        (root_folder,),
    )


def list_clients(conn: Connection) -> list[Row]:
    """List every client, for marking folders as already added.

    In: an open connection.
    Out: client rows with ID, NAME, FOLDER_PATH, ordered by name.
    """
    return conn.execute(
        "SELECT ID, NAME, FOLDER_PATH FROM CLIENTS ORDER BY NAME",
    ).fetchall()


def create_client(conn: Connection, name: str, folder_path: str) -> None:
    """Create a client unless its folder is already registered.

    In: an open connection, the client name, and its absolute folder
    path.
    Out: nothing. The UNIQUE rule on FOLDER_PATH is the final guard,
    OR IGNORE turns a duplicate into a quiet no-op instead of an error.
    """
    conn.execute(
        "INSERT OR IGNORE INTO CLIENTS (NAME, FOLDER_PATH) VALUES (?, ?)",
        (name, folder_path),
    )
