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

def add_origin_version(repo_id: str):
    """
    Add an 'Origin' version to a newly added repository.

    Args:
        repo_id (str): The ID of the repository.

    Returns:
        int: The ID of the newly added version.
    """
    import logging
    import time

    # Get today's date in ISO format (YYYY-MM-DD)
    today = datetime.now().date().isoformat()

    # Add the Origin version with retry mechanism
    max_retries = 3
    retry_delay = 1  # seconds
    last_error = None

    for attempt in range(max_retries):
        try:
            version_id = add_version(
                repo_id=repo_id,
                version_number="Origin",
                release_date=today,
                description="Repository indexed in Nuggit for the first time"
            )
            logging.info(f"Successfully added 'Origin' version for repository {repo_id}")
            return version_id
        except Exception as e:
            last_error = e
            if 'database is locked' in str(e) and attempt < max_retries - 1:
                # Database is locked, wait and retry
                logging.warning(f"Database locked when adding 'Origin' version for {repo_id}, retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                # Other error or final attempt failed
                break

    # If we get here, all retries failed
    logging.error(f"Failed to add 'Origin' version after {max_retries} attempts: {last_error}")
    raise last_error


def insert_or_update_repo(repo_data: Dict[str, Any]):
    repo_data.setdefault('last_synced', datetime.utcnow().isoformat())

    with get_connection() as conn:
        cursor = conn.cursor()

        # Fetch existing repo data for comparison
        cursor.execute("SELECT * FROM repositories WHERE id = ?", (repo_data['id'],))
        existing = cursor.fetchone()
        columns = [desc[0] for desc in cursor.description]

        # Flag to track if this is a new repository
        is_new_repo = existing is None

        if existing:
            existing_data = dict(zip(columns, existing))
            for field in repo_data:
                if field in existing_data and str(repo_data[field]) != str(existing_data[field]):
                    cursor.execute("""
                        INSERT INTO repository_history (repo_id, field, old_value, new_value, changed_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        repo_data['id'],
                        field,
                        str(existing_data[field]),
                        str(repo_data[field]),
                        repo_data['last_synced']
                    ))


        cursor.execute("""
        INSERT INTO repositories (
            id, name, description, url, topics, license, created_at, updated_at,
            stars, forks, issues, contributors, commits, last_commit, tags, notes, last_synced
        ) VALUES (
            :id, :name, :description, :url, :topics, :license, :created_at, :updated_at,
            :stars, :forks, :issues, :contributors, :commits, :last_commit, :tags, :notes, :last_synced
        )
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            description = excluded.description,
            url = excluded.url,
            topics = excluded.topics,
            license = excluded.license,
            created_at = excluded.created_at,
            updated_at = excluded.updated_at,
            stars = excluded.stars,
            forks = excluded.forks,
            issues = excluded.issues,
            contributors = excluded.contributors,
            commits = excluded.commits,
            last_commit = excluded.last_commit,
            tags = excluded.tags,
            notes = excluded.notes,
            last_synced = excluded.last_synced
        """, repo_data)

        # If this is a new repository, schedule the Origin version to be added asynchronously
        if is_new_repo:
            import threading
            import logging

            def add_origin_version_async(repo_id):
                import time
                max_retries = 3
                retry_delay = 1  # seconds

                # Wait a bit to let the main transaction complete
                time.sleep(1)

                for attempt in range(max_retries):
                    try:
                        add_origin_version(repo_id)
                        logging.info(f"Added 'Origin' version for new repository: {repo_id}")
                        break  # Success, exit the retry loop
                    except Exception as e:
                        if 'database is locked' in str(e) and attempt < max_retries - 1:
                            # Database is locked, wait and retry
                            logging.warning(f"Database locked when adding 'Origin' version for {repo_id}, retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                        else:
                            # Other error or final attempt failed
                            logging.error(f"Failed to add 'Origin' version for repository {repo_id}: {e}")

            # Start a background thread to add the Origin version
            thread = threading.Thread(target=add_origin_version_async, args=(repo_data['id'],))
            thread.daemon = True  # Make the thread a daemon so it doesn't block program exit
            thread.start()
            logging.info(f"Scheduled 'Origin' version creation for repository {repo_data['id']} in background")


def tag_repository(repo_id: str, tag: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE repositories
        SET tags = COALESCE(tags || ',', '') || ?
        WHERE id = ?
        """, (tag, repo_id))

def add_note(repo_id: str, note: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE repositories
        SET notes = COALESCE(notes || '\n', '') || ?
        WHERE id = ?
        """, (note, repo_id))

def get_repository(repo_id: str) -> Optional[Dict[str, Any]]:
    # Debug logging
    import logging
    logging.info(f"Getting repository with ID: {repo_id}")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,))
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            result = dict(zip(columns, row))
            logging.info(f"Found repository: {result['name']}")
            return result

        logging.warning(f"Repository not found with ID: {repo_id}")
        return None

def list_all_repositories() -> list[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM repositories")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

def get_repository_history(repo_id: str) -> list[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT field, old_value, new_value, changed_at
        FROM repository_history
        WHERE repo_id = ?
        ORDER BY changed_at DESC
        """, (repo_id,))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

def update_repository_metadata(repo_id: str, tags: str, notes: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE repositories SET tags = ?, notes = ? WHERE id = ?", (tags, notes, repo_id))
        success = cursor.rowcount > 0
        return success


def update_repository_fields(repo_id: str, fields: Dict[str, Any]) -> bool:
    """
    Update specific fields of a repository and record the changes in history.

    Args:
        repo_id (str): The ID of the repository.
        fields (Dict[str, Any]): A dictionary of fields to update.

    Returns:
        bool: True if the update was successful.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # Get current repository data
        cursor.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,))
        existing = cursor.fetchone()

        if not existing:
            return False

        columns = [desc[0] for desc in cursor.description]
        existing_data = dict(zip(columns, existing))

        # Current timestamp
        timestamp = datetime.utcnow().isoformat()

        # Record changes in history
        for field, value in fields.items():
            if field in existing_data and str(value) != str(existing_data[field]):
                cursor.execute("""
                    INSERT INTO repository_history (repo_id, field, old_value, new_value, changed_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    repo_id,
                    field,
                    str(existing_data[field]),
                    str(value),
                    timestamp
                ))

        # Build the update query
        set_clauses = [f"{field} = ?" for field in fields.keys()]
        query = f"UPDATE repositories SET {', '.join(set_clauses)}, last_synced = ? WHERE id = ?"

        # Execute the update
        params = list(fields.values()) + [timestamp, repo_id]
        cursor.execute(query, params)

        return cursor.rowcount > 0


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
    with get_connection() as conn:
        cursor = conn.cursor()

        # Delete repository history first (foreign key constraint)
        cursor.execute("DELETE FROM repository_history WHERE repo_id = ?", (repo_id,))

        # Delete repository comments
        cursor.execute("DELETE FROM repository_comments WHERE repo_id = ?", (repo_id,))

        # Delete the repository
        cursor.execute("DELETE FROM repositories WHERE id = ?", (repo_id,))

        # Return True if at least one row was affected
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
