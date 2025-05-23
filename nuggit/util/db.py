import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent.parent / "nuggit.db"

@contextmanager
def get_connection():
    """
    Context manager for SQLite connections with enhanced defaults:
    - 30s timeout for busy waits
    - PARSE_DECLTYPES and PARSE_COLNAMES for type detection
    - sqlite3.Row row factory for dict-like row access
    - foreign key enforcement on

    Yields:
        sqlite3.Connection: A SQLite connection with custom settings.

    Raises:
        sqlite3.Error: If connecting to the database fails.
    """
    conn = sqlite3.connect(
        DB_PATH,
        timeout=30,
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def initialize_database() -> None:
    """
    Initialize the database schema, creating tables if they do not exist.

    Tables:
        - repositories
        - repository_history
        - repository_comments
        - repository_versions

    Raises:
        sqlite3.Error: If any schema creation statement fails.
    """
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

    Raises:
        sqlite3.Error: If the database insert fails.
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
    Insert a new repository or update an existing one,
    recording any field changes in history.
    If it's a new repo, immediately add an initial version named by today's date.

    Args:
        repo_data (Dict[str, Any]): Repository fields; must include 'id'.

    Raises:
        sqlite3.Error: If any database operation fails.
    """
    timestamp = datetime.utcnow().isoformat()
    repo_data.setdefault('last_synced', timestamp)

    upsert_cols = [
        "id", "name", "description", "url", "topics", "license",
        "created_at", "updated_at", "stars", "forks", "issues",
        "contributors", "commits", "last_commit", "tags", "notes", "last_synced"
    ]

    query_select = f"SELECT {', '.join(upsert_cols)} FROM repositories WHERE id = ?"
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
        cur = conn.execute(query_select, (repo_data['id'],))
        row = cur.fetchone()
        is_new = row is None

        if row:
            existing = dict(row)
            history_params: List[tuple] = [
                (
                    repo_data['id'], field,
                    str(existing[field]), str(repo_data[field]),
                    timestamp
                )
                for field in repo_data
                if field in existing and str(repo_data[field]) != str(existing[field])
            ]
            if history_params:
                conn.executemany(query_history, history_params)

        conn.execute(query_upsert, repo_data)

    if is_new:
        add_origin_version(repo_data['id'])


def tag_repository(repo_id: str, tag: str) -> bool:
    """
    Append a tag to a repository's existing tags.

    Args:
        repo_id (str): The ID of the repository.
        tag (str): The tag to add.

    Returns:
        bool: True if the update affected a row, False otherwise.

    Raises:
        sqlite3.Error: If the database update fails.
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
    Append a note to a repository's existing notes.

    Args:
        repo_id (str): The ID of the repository.
        note (str): The note text to append.

    Returns:
        bool: True if the update affected a row, False otherwise.

    Raises:
        sqlite3.Error: If the database update fails.
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
        Optional[Dict[str, Any]]: A dict of repository fields if found, else None.

    Raises:
        sqlite3.Error: If the database query fails.
    """
    query = "SELECT * FROM repositories WHERE id = ?"
    with get_connection() as conn:
        row = conn.execute(query, (repo_id,)).fetchone()
        return dict(row) if row else None


def list_all_repositories() -> List[Dict[str, Any]]:
    """
    List all repositories.

    Returns:
        List[Dict[str, Any]]: A list of repository records.

    Raises:
        sqlite3.Error: If the database query fails.
    """
    query = "SELECT * FROM repositories"
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(query)]


def get_repository_history(repo_id: str) -> List[Dict[str, Any]]:
    """
    Get all history entries for a repository, newest first.

    Args:
        repo_id (str): The repository ID.

    Returns:
        List[Dict[str, Any]]: History records.

    Raises:
        sqlite3.Error: If the database query fails.
    """
    query = """
        SELECT field, old_value, new_value, changed_at
        FROM repository_history
        WHERE repo_id = ?
        ORDER BY changed_at DESC
    """
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(query, (repo_id,))]


def update_repository_metadata(repo_id: str, tags: str, notes: str) -> bool:
    """
    Update tags and notes of a repository.

    Args:
        repo_id (str): The ID of the repository.
        tags (str): Comma-separated tags.
        notes (str): Free-form notes.

    Returns:
        bool: True if updated successfully, False otherwise.

    Raises:
        sqlite3.Error: If the database update fails.
    """
    query = """
        UPDATE repositories
        SET tags = ?, notes = ?
        WHERE id = ?
    """
    with get_connection() as conn:
        return conn.execute(query, (tags, notes, repo_id)).rowcount > 0


def update_repository_fields(repo_id: str, fields: Dict[str, Any]) -> bool:
    """
    Update specific fields of a repository and record changes in history.

    Args:
        repo_id (str): Repository ID.
        fields (Dict[str, Any]): Fields to update.

    Returns:
        bool: True if update succeeded, False otherwise.

    Raises:
        sqlite3.Error: If any database operation fails.
    """
    timestamp = datetime.utcnow().isoformat()
    cols = ", ".join(fields.keys())
    query_select = f"SELECT {cols} FROM repositories WHERE id = ?"
    query_history = """
        INSERT INTO repository_history
            (repo_id, field, old_value, new_value, changed_at)
        VALUES (?, ?, ?, ?, ?)
    """
    set_clauses = [f"{f} = ?" for f in fields] + ["last_synced = ?"]
    query_update = f"UPDATE repositories SET {', '.join(set_clauses)} WHERE id = ?"

    with get_connection() as conn:
        row = conn.execute(query_select, (repo_id,)).fetchone()
        if not row:
            return False
        existing = dict(row)
        history_params = [
            (repo_id, f, str(existing.get(f)), str(v), timestamp)
            for f, v in fields.items()
            if str(existing.get(f)) != str(v)
        ]
        if history_params:
            conn.executemany(query_history, history_params)
        params = list(fields.values()) + [timestamp, repo_id]
        return conn.execute(query_update, params).rowcount > 0


def delete_repository(repo_id: str) -> bool:
    """
    Delete a repository and its related data.

    Args:
        repo_id (str): The ID of the repository.

    Returns:
        bool: True if deleted successfully, False otherwise.

    Raises:
        sqlite3.Error: If any database delete operation fails.
    """
    with get_connection() as conn:
        # Delete related data first (foreign key constraints)
        conn.execute("DELETE FROM repository_history WHERE repo_id = ?", (repo_id,))
        conn.execute("DELETE FROM repository_comments WHERE repo_id = ?", (repo_id,))
        conn.execute("DELETE FROM repository_versions WHERE repo_id = ?", (repo_id,))

        # Then delete the repository itself
        return conn.execute("DELETE FROM repositories WHERE id = ?", (repo_id,)).rowcount > 0


def add_comment(repo_id: str, comment: str, author: str = "Anonymous") -> int:
    """
    Add a comment to a repository.

    Args:
        repo_id (str): The ID of the repository.
        comment (str): The comment text.
        author (str): The author of the comment.

    Returns:
        int: ID of new comment.

    Raises:
        sqlite3.Error: If the database insert fails.
    """
    created_at = datetime.utcnow().isoformat()
    query = "INSERT INTO repository_comments (repo_id, comment, author, created_at) VALUES (?, ?, ?, ?)"
    with get_connection() as conn:
        return conn.execute(query, (repo_id, comment, author, created_at)).lastrowid


def get_comments(repo_id: str) -> List[Dict[str, Any]]:
    """
    Get all comments for a repository, newest first.

    Args:
        repo_id (str): The repository ID.

    Returns:
        List[Dict[str, Any]]: Comment records.

    Raises:
        sqlite3.Error: If the database query fails.
    """
    query = "SELECT id, comment, author, created_at FROM repository_comments WHERE repo_id = ? ORDER BY created_at DESC"
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(query, (repo_id,))]


def add_version(repo_id: str, version_number: str, release_date: Optional[str] = None, description: Optional[str] = None) -> int:
    """
    Add a version to a repository.

    Args:
        repo_id (str): The repository ID.
        version_number (str): Version number.
        release_date (Optional[str]): Release date in ISO format.
        description (Optional[str]): Description.

    Returns:
        int: ID of new version.

    Raises:
        sqlite3.Error: If the database insert fails.
    """
    created_at = datetime.utcnow().isoformat()
    query = "INSERT INTO repository_versions (repo_id, version_number, release_date, description, created_at) VALUES (?, ?, ?, ?, ?)"
    with get_connection() as conn:
        return conn.execute(query, (repo_id, version_number, release_date, description, created_at)).lastrowid


def get_versions(repo_id: str) -> List[Dict[str, Any]]:
    """
    Get all versions for a repository, newest first.

    Args:
        repo_id (str): The repository ID.

    Returns:
        List[Dict[str, Any]]: Version records.

    Raises:
        sqlite3.Error: If the database query fails.
    """
    query = "SELECT id, version_number, release_date, description, created_at FROM repository_versions WHERE repo_id = ? ORDER BY created_at DESC"
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(query, (repo_id,))]


def create_repository_version(repo_id: str, repo_info: Dict[str, Any]) -> int:
    """
    Create a new version when a repository is updated from GitHub.
    Uses the current date (YYYY.MM.DD) as the version number.

    Args:
        repo_id (str): The ID of the repository.
        repo_info (Dict[str, Any]): The updated repository information.

    Returns:
        int: The ID of the newly added version.

    Raises:
        sqlite3.Error: If the database insert fails.
    """
    today = datetime.utcnow().date()
    version_name = today.strftime("%Y.%m.%d")
    release_date = today.isoformat()

    # Create a description that includes what changed
    description = f"Updated from GitHub on {release_date}"

    # Check if there are existing versions with the same version number
    existing_versions = get_versions(repo_id)
    same_day_versions = [v for v in existing_versions if v["version_number"] == version_name]

    # If there are versions from the same day, append a suffix
    if same_day_versions:
        version_name = f"{version_name}.{len(same_day_versions) + 1}"

    return add_version(
        repo_id=repo_id,
        version_number=version_name,
        release_date=release_date,
        description=description
    )
