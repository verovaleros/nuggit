import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from nuggit.util.timezone import utc_now_iso, normalize_github_datetime

# Import logging utilities
try:
    from nuggit.util.logging_config import LogTimer, get_performance_logger, get_audit_logger
    PERFORMANCE_LOGGING_AVAILABLE = True
    audit_logger = get_audit_logger()
except ImportError:
    PERFORMANCE_LOGGING_AVAILABLE = False
    audit_logger = None

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "nuggit.db"

# Import connection pool for enhanced connection management
try:
    from nuggit.util.connection_pool import get_pooled_connection
    USE_CONNECTION_POOL = True
except ImportError:
    USE_CONNECTION_POOL = False
    logger.warning("Connection pool not available, falling back to simple connections")


@contextmanager
def get_connection():
    """
    Context manager for SQLite connections with enhanced connection management.

    Uses connection pooling when available for better performance and leak prevention.
    Falls back to simple connections if pooling is not available.

    Yields:
        sqlite3.Connection: A SQLite connection with custom settings.

    Raises:
        sqlite3.Error: If connecting to the database fails.
    """
    if USE_CONNECTION_POOL:
        # Use connection pool for better connection management
        with get_pooled_connection(DB_PATH) as conn:
            yield conn
    else:
        # Fallback to simple connection management
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
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def initialize_database() -> None:
    """
    Initialize the database schema using the migration system.

    This function now uses the migration system to ensure proper
    schema versioning and data integrity.

    Raises:
        sqlite3.Error: If any schema creation statement fails.
        MigrationError: If migration system fails.
    """
    from nuggit.util.migrations import MigrationManager

    try:
        # Use migration system for proper schema management
        migration_manager = MigrationManager(DB_PATH)

        # Check if we need to run migrations
        status = migration_manager.get_status()

        if status['pending_count'] > 0:
            logger.info(f"Running {status['pending_count']} pending migrations...")
            applied = migration_manager.migrate()
            logger.info(f"Successfully applied migrations: {', '.join(applied)}")
        else:
            logger.info("Database schema is up to date")

        # Validate migration integrity
        issues = migration_manager.validate_migrations()
        if issues:
            logger.warning(f"Migration validation issues: {issues}")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        # Fallback to legacy initialization for backward compatibility
        logger.info("Falling back to legacy database initialization...")
        _legacy_initialize_database()


def _legacy_initialize_database() -> None:
    """
    Legacy database initialization for backward compatibility.
    This should only be used as a fallback.
    """
    logger.warning("Using legacy database initialization - consider running migrations")

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
    from nuggit.util.timezone import now_utc
    today = now_utc().date()
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
    Insert a new repository or update an existing one with validation,
    recording any field changes in history.
    If it's a new repo, immediately add an initial version named by today's date.

    Args:
        repo_data (Dict[str, Any]): Repository fields; must include 'id'.

    Raises:
        sqlite3.Error: If any database operation fails.
        ValidationError: If data validation fails.
    """
    operation_name = f"insert_or_update_repo_{repo_data.get('id', 'unknown')}"

    if PERFORMANCE_LOGGING_AVAILABLE:
        with LogTimer(operation_name, repo_id=repo_data.get('id')):
            _insert_or_update_repo_impl(repo_data)
    else:
        _insert_or_update_repo_impl(repo_data)


def _insert_or_update_repo_impl(repo_data: Dict[str, Any]) -> None:
    """Implementation of insert_or_update_repo with performance logging."""
    from nuggit.util.validation import validate_repository_data, ValidationError

    # Validate input data
    try:
        validated_data = validate_repository_data(repo_data)
    except ValidationError as e:
        logger.error(f"Repository data validation failed: {e}")
        raise

    timestamp = utc_now_iso()
    validated_data.setdefault('last_synced', timestamp)

    # Ensure version is set for new repositories
    validated_data.setdefault('version', 1)

    # Only use columns that are actually present in the validated data
    available_cols = [
        "id", "name", "description", "url", "topics", "license",
        "created_at", "updated_at", "stars", "forks", "issues",
        "contributors", "commits", "last_commit", "tags", "notes", "last_synced", "version"
    ]
    upsert_cols = [col for col in available_cols if col in validated_data]

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
        {', '.join(f"{c}=excluded.{c}" for c in upsert_cols if c not in ["id", "version"])},
        version = version + 1
    """

    with get_connection() as conn:
        cur = conn.execute(query_select, (validated_data['id'],))
        row = cur.fetchone()
        is_new = row is None

        if row:
            existing = dict(row)
            # Validate and record history changes
            history_params: List[tuple] = []
            for field in validated_data:
                if field in existing and str(validated_data[field]) != str(existing[field]):
                    history_data = {
                        'repo_id': validated_data['id'],
                        'field': field,
                        'old_value': str(existing[field]),
                        'new_value': str(validated_data[field]),
                        'changed_at': timestamp
                    }
                    try:
                        from nuggit.util.validation import validate_history_data
                        validated_history = validate_history_data(history_data)
                        history_params.append((
                            validated_history['repo_id'],
                            validated_history['field'],
                            validated_history['old_value'],
                            validated_history['new_value'],
                            validated_history['changed_at']
                        ))
                    except Exception as e:
                        logger.warning(f"History validation failed for {field}: {e}")

            if history_params:
                conn.executemany(query_history, history_params)

        conn.execute(query_upsert, validated_data)

    if is_new:
        add_origin_version(validated_data['id'])

        # Audit log for new repository
        if audit_logger:
            audit_logger.log_data_change(
                user="system",
                table="repositories",
                operation="INSERT",
                record_id=validated_data['id'],
                repo_name=validated_data.get('name', 'unknown')
            )
    else:
        # Audit log for repository update
        if audit_logger:
            audit_logger.log_data_change(
                user="system",
                table="repositories",
                operation="UPDATE",
                record_id=validated_data['id'],
                repo_name=validated_data.get('name', 'unknown')
            )


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


class OptimisticLockError(Exception):
    """Raised when an optimistic lock conflict occurs."""
    pass


def update_repository_fields(repo_id: str, fields: Dict[str, Any], expected_version: Optional[int] = None) -> bool:
    """
    Update specific fields of a repository with optimistic locking and record changes in history.

    Args:
        repo_id (str): Repository ID.
        fields (Dict[str, Any]): Fields to update.
        expected_version (Optional[int]): Expected version for optimistic locking.

    Returns:
        bool: True if update succeeded, False otherwise.

    Raises:
        sqlite3.Error: If any database operation fails.
        OptimisticLockError: If version conflict occurs.
    """
    timestamp = utc_now_iso()

    # Include version in the select query if optimistic locking is used
    select_cols = list(fields.keys())
    if expected_version is not None:
        select_cols.append('version')

    cols = ", ".join(select_cols)
    query_select = f"SELECT {cols} FROM repositories WHERE id = ?"
    query_history = """
        INSERT INTO repository_history
            (repo_id, field, old_value, new_value, changed_at)
        VALUES (?, ?, ?, ?, ?)
    """

    # Build update query with version increment if using optimistic locking
    set_clauses = [f"{f} = ?" for f in fields] + ["last_synced = ?"]
    where_clause = "WHERE id = ?"

    if expected_version is not None:
        set_clauses.append("version = version + 1")
        where_clause += " AND version = ?"

    query_update = f"UPDATE repositories SET {', '.join(set_clauses)} {where_clause}"

    with get_connection() as conn:
        row = conn.execute(query_select, (repo_id,)).fetchone()
        if not row:
            return False

        existing = dict(row)

        # Check version for optimistic locking
        if expected_version is not None:
            current_version = existing.get('version', 1)
            if current_version != expected_version:
                raise OptimisticLockError(
                    f"Version conflict: expected {expected_version}, got {current_version}"
                )

        # Record history for changed fields
        history_params = [
            (repo_id, f, str(existing.get(f)), str(v), timestamp)
            for f, v in fields.items()
            if str(existing.get(f)) != str(v)
        ]
        if history_params:
            conn.executemany(query_history, history_params)

        # Execute update
        params = list(fields.values()) + [timestamp, repo_id]
        if expected_version is not None:
            params.append(expected_version)

        result = conn.execute(query_update, params)

        # Check if update was successful (handles optimistic locking)
        if result.rowcount == 0 and expected_version is not None:
            raise OptimisticLockError("Update failed due to version conflict")

        return result.rowcount > 0


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
    Add a comment to a repository with validation.

    Args:
        repo_id (str): The ID of the repository.
        comment (str): The comment text.
        author (str): The author of the comment.

    Returns:
        int: ID of new comment.

    Raises:
        sqlite3.Error: If the database insert fails.
        ValidationError: If data validation fails.
    """
    from nuggit.util.validation import validate_comment_data, ValidationError

    created_at = utc_now_iso()

    # Validate comment data
    comment_data = {
        'repo_id': repo_id,
        'comment': comment,
        'author': author,
        'created_at': created_at
    }

    try:
        validated_data = validate_comment_data(comment_data)
    except ValidationError as e:
        logger.error(f"Comment data validation failed: {e}")
        raise

    query = "INSERT INTO repository_comments (repo_id, comment, author, created_at) VALUES (?, ?, ?, ?)"
    with get_connection() as conn:
        return conn.execute(query, (
            validated_data['repo_id'],
            validated_data['comment'],
            validated_data['author'],
            validated_data['created_at']
        )).lastrowid


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
    Add a version to a repository with validation.

    Args:
        repo_id (str): The repository ID.
        version_number (str): Version number.
        release_date (Optional[str]): Release date in ISO format.
        description (Optional[str]): Description.

    Returns:
        int: ID of new version.

    Raises:
        sqlite3.Error: If the database insert fails.
        ValidationError: If data validation fails.
    """
    from nuggit.util.validation import validate_version_data, ValidationError

    created_at = utc_now_iso()

    # Validate version data
    version_data = {
        'repo_id': repo_id,
        'version_number': version_number,
        'release_date': release_date,
        'description': description,
        'created_at': created_at
    }

    try:
        validated_data = validate_version_data(version_data)
    except ValidationError as e:
        logger.error(f"Version data validation failed: {e}")
        raise

    query = "INSERT INTO repository_versions (repo_id, version_number, release_date, description, created_at) VALUES (?, ?, ?, ?, ?)"
    with get_connection() as conn:
        return conn.execute(query, (
            validated_data['repo_id'],
            validated_data['version_number'],
            validated_data.get('release_date'),
            validated_data.get('description'),
            validated_data['created_at']
        )).lastrowid


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
    from nuggit.util.timezone import now_utc
    today = now_utc().date()
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
