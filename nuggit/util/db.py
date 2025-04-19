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

def insert_or_update_repo(repo_data: Dict[str, Any]):
    repo_data.setdefault('last_synced', datetime.utcnow().isoformat())

    with get_connection() as conn:
        cursor = conn.cursor()

        # Fetch existing repo data for comparison
        cursor.execute("SELECT * FROM repositories WHERE id = ?", (repo_data['id'],))
        existing = cursor.fetchone()
        columns = [desc[0] for desc in cursor.description]

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
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,))
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
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
    with get_connection() as conn:
        cursor = conn.cursor()

        # Get current timestamp in ISO format
        created_at = datetime.utcnow().isoformat()

        # Insert the comment
        cursor.execute(
            "INSERT INTO repository_comments (repo_id, comment, author, created_at) VALUES (?, ?, ?, ?)",
            (repo_id, comment, author, created_at)
        )

        # Get the ID of the newly inserted comment
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
    with get_connection() as conn:
        cursor = conn.cursor()

        # Get all comments for the repository, ordered by creation time (newest first)
        cursor.execute(
            "SELECT id, comment, author, created_at FROM repository_comments WHERE repo_id = ? ORDER BY created_at DESC",
            (repo_id,)
        )

        # Convert the results to a list of dictionaries
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
