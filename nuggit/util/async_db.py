"""
Asynchronous versions of database utility functions.

This module provides asynchronous wrappers around the synchronous database
functions in db.py, allowing them to be used with FastAPI's async routes.
Enhanced with proper connection management and error handling.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from functools import wraps

logger = logging.getLogger(__name__)

from nuggit.util.db import (
    get_repository as sync_get_repository,
    update_repository_metadata as sync_update_repository_metadata,
    add_comment as sync_add_comment,
    get_comments as sync_get_comments,
    get_versions as sync_get_versions,
    add_version as sync_add_version,
    get_repository_history as sync_get_repository_history,
)


def async_db_operation(operation_name: str):
    """
    Decorator for async database operations with enhanced error handling and logging.

    Args:
        operation_name: Name of the operation for logging purposes
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                logger.debug(f"Starting async database operation: {operation_name}")
                result = await func(*args, **kwargs)
                logger.debug(f"Completed async database operation: {operation_name}")
                return result
            except Exception as e:
                logger.error(f"Async database operation failed: {operation_name} - {e}")
                raise
        return wrapper
    return decorator


@async_db_operation("get_repository")
async def get_repository(repo_id: str) -> Optional[Dict[str, Any]]:
    """
    Asynchronous version of get_repository.

    Args:
        repo_id (str): The ID of the repository.

    Returns:
        Optional[Dict[str, Any]]: A dict of repository fields if found, else None.

    Raises:
        Exception: If the database query fails.
    """
    return await asyncio.to_thread(sync_get_repository, repo_id)


async def update_repository_metadata(repo_id: str, tags: str, notes: str) -> bool:
    """
    Asynchronous version of update_repository_metadata.

    Args:
        repo_id (str): The ID of the repository.
        tags (str): Comma-separated tags.
        notes (str): Free-form notes.

    Returns:
        bool: True if updated successfully, False otherwise.

    Raises:
        Exception: If the database update fails.
    """
    return await asyncio.to_thread(sync_update_repository_metadata, repo_id, tags, notes)


async def add_comment(repo_id: str, comment: str, author: str = "Anonymous") -> int:
    """
    Asynchronous version of add_comment.

    Args:
        repo_id (str): The ID of the repository.
        comment (str): The comment text.
        author (str): The author of the comment.

    Returns:
        int: ID of new comment.

    Raises:
        Exception: If the database insert fails.
    """
    return await asyncio.to_thread(sync_add_comment, repo_id, comment, author)


async def get_comments(repo_id: str) -> List[Dict[str, Any]]:
    """
    Asynchronous version of get_comments.

    Args:
        repo_id (str): The repository ID.

    Returns:
        List[Dict[str, Any]]: Comment records.

    Raises:
        Exception: If the database query fails.
    """
    return await asyncio.to_thread(sync_get_comments, repo_id)


async def get_versions(repo_id: str) -> List[Dict[str, Any]]:
    """
    Asynchronous version of get_versions.

    Args:
        repo_id (str): The repository ID.

    Returns:
        List[Dict[str, Any]]: Version records.

    Raises:
        Exception: If the database query fails.
    """
    return await asyncio.to_thread(sync_get_versions, repo_id)


async def add_version(
    repo_id: str,
    version_number: str,
    release_date: Optional[str] = None,
    description: Optional[str] = None
) -> int:
    """
    Asynchronous version of add_version.

    Args:
        repo_id (str): The repository ID.
        version_number (str): Version number.
        release_date (Optional[str]): Release date in ISO format.
        description (Optional[str]): Description.

    Returns:
        int: ID of new version.

    Raises:
        Exception: If the database insert fails.
    """
    return await asyncio.to_thread(
        sync_add_version,
        repo_id,
        version_number,
        release_date,
        description
    )


async def get_repository_history(repo_id: str) -> List[Dict[str, Any]]:
    """
    Asynchronous version of get_repository_history.

    Args:
        repo_id (str): The repository ID.

    Returns:
        List[Dict[str, Any]]: History records.

    Raises:
        Exception: If the database query fails.
    """
    return await asyncio.to_thread(sync_get_repository_history, repo_id)
