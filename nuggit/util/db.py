# nuggit/util/db.py

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent.parent / "nuggit.db"

@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def initialize_database():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS repositories (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            url TEXT NOT NULL,
            topics TEXT,
            license TEXT,
            created_at TEXT,
            updated_at TEXT,
            stars INTEGER,
            forks INTEGER,
            issues INTEGER,
            contributors TEXT,
            commits INTEGER,
            last_commit TEXT,
            tags TEXT,
            notes TEXT,
            last_synced TEXT
        )
        """)

        # Create repo history table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS repository_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_id TEXT NOT NULL,
            field TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            changed_at TEXT NOT NULL,
            FOREIGN KEY (repo_id) REFERENCES repositories(id)
        )
        """)

        # Create comments table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS repository_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_id TEXT NOT NULL,
            comment TEXT NOT NULL,
            author TEXT DEFAULT 'Anonymous',
            created_at TEXT NOT NULL,
            FOREIGN KEY (repo_id) REFERENCES repositories(id)
        )
        """)

        # Create versions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS repository_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_id TEXT NOT NULL,
            version_number TEXT NOT NULL,
            release_date TEXT,
            description TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (repo_id) REFERENCES repositories(id)
        )
        """)


def add_origin_version(repo_id: str) -> int:
    """
    Add a single version to a newly added repository,
    using today's date (YYYY.MM.DD) as the version_number
    and recording when it was indexed.
    
    Args:
        repo_id (str): The ID of the repository.

    Returns:
        int: The ID of the newly added version.
    """
    today = datetime.utcnow().date()
    version_name = today.strftime("%Y.%m.%d")
    release_date = today.isoformat()
    description = f"Indexed on {release_date}"

    return add_version(
        repo_id=repo_id,
        version_number=version_name,
        release_date=release_date,
        description=description
    )


def insert_or_update_repo(repo_data: Dict[str, Any]) -> None:
    """
    Insert a new repository or update an existing one, recording any field changes in history.
    If it’s a new repo, immediately add an initial version named by today’s date.

    Args:
        repo_data (Dict[str, Any]): Repository fields; must include 'id'.
    """
    # Single UTC timestamp for history & upsert
    timestamp = datetime.utcnow().isoformat()
    repo_data.setdefault('last_synced', timestamp)

    # Columns to upsert
    upsert_cols = [
        "id", "name", "description", "url", "topics", "license",
        "created_at", "updated_at", "stars", "forks", "issues",
        "contributors", "commits", "last_commit", "tags", "notes", "last_synced"
    ]

    # SQL templates
    query_select = f"""
        SELECT {', '.join(upsert_cols)}
          FROM repositories
         WHERE id = ?
    """
    query_history = """
        INSERT INTO repository_history
            (repo_id, field, old_value, new_value, changed_at)
        VALUES (?, ?, ?, ?, ?)
    """
    query_upsert = f"""
        INSERT INTO repositories ({', '.join(upsert_cols)})
        VALUES ({', '.join(f":{c}" for c in upsert_cols)})
          ON CONFLICT(id) DO UPDATE SET
            {', '.join(f"{c}=excluded.{c}" for c in upsert_cols if c != "id")}
    """

    with get_connection() as conn:
        # Map rows to dicts
        conn.row_factory = sqlite3.Row

        # Check for existing repo
        cur = conn.execute(query_select, (repo_data['id'],))
        row = cur.fetchone()
        is_new = row is None

        # Record history for changed fields
        if row:
            existing = dict(row)
            history_params: List[tuple] = [
                (
                    repo_data['id'],
                    field,
                    str(existing[field]),
                    str(repo_data[field]),
                    timestamp
                )
                for field in repo_data
                if field in existing and str(repo_data[field]) != str(existing[field])
            ]
            if history_params:
                conn.executemany(query_history, history_params)

        # Upsert repository row
        conn.execute(query_upsert, repo_data)

    # For new repositories, add initial dated version
    if is_new:
        add_origin_version(repo_data['id'])


def tag_repository(repo_id: str, tag: str) -> bool:
    """
    Append a tag to a repository’s existing tags.

    Args:
        repo_id (str): The ID of the repository.
        tag (str): The tag to add.

    Returns:
        bool: True if the update affected a row, False otherwise.

    Raises:
        sqlite3.Error: If there is a database error.
    """
    query = """
        UPDATE repositories
           SET tags = COALESCE(tags || ',', '') || ?
         WHERE id = ?
    """

    with get_connection() as conn:
        result = conn.execute(query, (tag, repo_id))
        return result.rowcount > 0


def add_note(repo_id: str, note: str) -> bool:
    """
    Append a note to a repository’s existing notes.

    Args:
        repo_id (str): The ID of the repository.
        note (str): The note text to append.

    Returns:
        bool: True if the update affected a row, False otherwise.

    Raises:
        sqlite3.Error: If there is a database error.
    """
    query = """
        UPDATE repositories
           SET notes = COALESCE(notes || '\n', '') || ?
         WHERE id = ?
    """

    with get_connection() as conn:
        result = conn.execute(query, (note, repo_id))
        return result.rowcount > 0


def get_repository(repo_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a repository by its ID.

    Args:
        repo_id (str): The ID of the repository.

    Returns:
        Optional[Dict[str, Any]]: A dictionary of repository fields if found, else None.

    Raises:
        sqlite3.Error: If there is a database error.
    """
    query = "SELECT * FROM repositories WHERE id = ?"

    with get_connection() as conn:
        # Have rows behave like dicts (column → value)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query, (repo_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def list_all_repositories() -> list[Dict[str, Any]]:
    """
    List all repositories in the database.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing repository data.

    Raises:
        sqlite3.Error: If there is a database error.
    """
    query = "SELECT * FROM repositories"

    with get_connection() as conn:
        # Have rows behave like dicts (column → value)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query)
        return [dict(row) for row in cursor]


def get_repository_history(repo_id: str) -> list[Dict[str, Any]]:
    """
    Get all history entries for a repository, newest first.

    Args:
        repo_id (str): The ID of the repository.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing history records.

    Raises:
        sqlite3.Error: If there is a database error.
    """
    query = """
        SELECT
            field,
            old_value,
            new_value,
            changed_at
        FROM repository_history
        WHERE repo_id = ?
        ORDER BY changed_at DESC
    """

    with get_connection() as conn:
        # Have rows behave like a dict of column → value
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query, (repo_id,))
        return [dict(row) for row in cursor]


def update_repository_metadata(repo_id: str, tags: str, notes: str) -> bool:
    """
    Update the tags and notes of a repository.

    Args:
        repo_id (str): The ID of the repository.
        tags (str): Comma-separated tags.
        notes (str): Free-form notes.

    Returns:
        bool: True if the update affected a row, False otherwise.

    Raises:
        sqlite3.Error: If there is a database error.
    """
    query = """
        UPDATE repositories
           SET tags  = ?,
               notes = ?
         WHERE id    = ?
    """

    with get_connection() as conn:
        result = conn.execute(query, (tags, notes, repo_id))
        return result.rowcount > 0


def update_repository_fields(repo_id: str, fields: Dict[str, Any]) -> bool:
    """
    Update specific fields of a repository and record the changes in history.

    Args:
        repo_id (str): The ID of the repository.
        fields (Dict[str, Any]): A dictionary of fields to update.

    Returns:
        bool: True if the update was successful.
    """
    # Always record history & last_synced in UTC ISO format
    timestamp = datetime.utcnow().isoformat()

    # Select only the columns we care about
    cols = ", ".join(fields.keys())
    query_select = f"SELECT {cols} FROM repositories WHERE id = ?"

    # Prepare history insert and repository update templates
    query_history = """
        INSERT INTO repository_history
            (repo_id, field, old_value, new_value, changed_at)
        VALUES (?, ?, ?, ?, ?)
    """
    set_clauses = [f"{field} = ?" for field in fields.keys()] + ["last_synced = ?"]
    query_update = f"""
        UPDATE repositories
           SET {', '.join(set_clauses)}
         WHERE id = ?
    """

    with get_connection() as conn:
        # Fetch existing values for only the fields being updated
        conn.row_factory = sqlite3.Row
        cur = conn.execute(query_select, (repo_id,))
        row = cur.fetchone()
        if not row:
            return False

        existing = dict(row)

        # Batch up any history entries for fields that actually changed
        history_params = [
            (
                repo_id,
                field,
                str(existing.get(field)),
                str(new_val),
                timestamp
            )
            for field, new_val in fields.items()
            if str(existing.get(field)) != str(new_val)
        ]

        if history_params:
            conn.executemany(query_history, history_params)

        # Perform the repository update (always updates last_synced)
        params = list(fields.values()) + [timestamp, repo_id]
        result = conn.execute(query_update, params)
        return result.rowcount > 0


def delete_repository(repo_id: str) -> bool:
    """
    Delete a repository and its history from the database.

    Args:
        repo_id (str): The ID of the repository to delete.

    Returns:
        bool: True if the repository was deleted, False if it was not found.

    Raises:
        sqlite3.Error: If there is a database error.
    """
    delete_history_q = "DELETE FROM repository_history WHERE repo_id = ?"
    delete_comments_q = "DELETE FROM repository_comments WHERE repo_id = ?"
    delete_repo_q = "DELETE FROM repositories WHERE id = ?"

    with get_connection() as conn:
        # Clean up dependent tables
        conn.execute(delete_history_q, (repo_id,))
        conn.execute(delete_comments_q, (repo_id,))

        # Delete the repository itself and check how many rows were removed
        cursor = conn.execute(delete_repo_q, (repo_id,))
        return cursor.rowcount > 0


def add_comment(repo_id: str, comment: str, author: str = "Anonymous") -> int:
    """
    Add a comment to a repository.

    Args:
        repo_id (str): The ID of the repository.
        comment (str): The comment text.
        author (str, optional): The author of the comment. Defaults to "Anonymous".

    Returns:
        int: The ID of the newly added comment.

    Raises:
        sqlite3.Error: If there is a database error.
    """
    query = """
        INSERT INTO repository_comments
            (repo_id, comment, author, created_at)
        VALUES (?, ?, ?, ?)
    """
    # Get current timestamp in ISO format
    created_at = datetime.utcnow().isoformat()

    with get_connection() as conn:
        cursor = conn.execute(query, (repo_id, comment, author, created_at))
        return cursor.lastrowid


def get_comments(repo_id: str) -> List[Dict[str, Any]]:
    """
    Get all comments for a repository.

    Args:
        repo_id (str): The ID of the repository.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing comment information.

    Raises:
        sqlite3.Error: If there is a database error.
    """
    query = """
        SELECT
            id,
            comment,
            author,
            created_at
        FROM repository_comments
        WHERE repo_id = ?
        ORDER BY created_at DESC
    """
    with get_connection() as conn:
        # Return rows as mapping of column→value
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query, (repo_id,))
        return [dict(row) for row in cursor]


def add_version(repo_id: str, version_number: str, release_date: Optional[str] = None, description: Optional[str] = None) -> int:
    """
    Add a version to a repository.

    Args:
        repo_id (str): The ID of the repository.
        version_number (str): The version number (e.g., "1.0.0").
        release_date (Optional[str], optional): The release date in ISO format. Defaults to None.
        description (Optional[str], optional): A description of the version. Defaults to None.

    Returns:
        int: The ID of the newly added version.

    Raises:
        sqlite3.Error: If there is a database error.
    """
    # Get current timestamp in ISO format
    created_at = datetime.utcnow().isoformat()

    query = """
        INSERT INTO repository_versions
            (repo_id, version_number, release_date, description, created_at)
        VALUES (?, ?, ?, ?, ?)
    """
    with get_connection() as conn:
        # Insert the version
        cursor = conn.execute(
            query,
            (repo_id, version_number, release_date, description, created_at)
        )
        return cursor.lastrowid


def get_versions(repo_id: str) -> List[Dict[str, Any]]:
    """
    Get all versions for a repository.

    Args:
        repo_id (str): The ID of the repository.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing version information.

    Raises:
        sqlite3.Error: If there is a database error.
    """
    query = """
        SELECT
            id,
            version_number,
            release_date,
            description,
            created_at
        FROM repository_versions
        WHERE repo_id = ?
        ORDER BY created_at DESC
    """

    with get_connection() as conn:
        # Tell sqlite3 to give us rows that behave like dicts
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query, (repo_id,))

        # Now each row is a sqlite3.Row, which can be cast directly to dict
        return [dict(row) for row in cursor]
