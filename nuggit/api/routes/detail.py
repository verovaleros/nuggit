import os
import logging
import asyncio
from functools import lru_cache
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Body, Query, status
from pydantic import BaseModel
from github import Github, GithubException

from nuggit.util.async_db import (
    get_repository as db_get_repository,
    update_repository_metadata as db_update_repository_metadata,
    add_comment as db_add_comment,
    get_comments as db_get_comments,
    get_versions as db_get_versions,
)
from nuggit.util.github import get_recent_commits

router = APIRouter()
logger = logging.getLogger(__name__)


@lru_cache()
def get_gh_client() -> Github:
    """
    Initialize and cache a GitHub client for reuse.

    Reads GITHUB_TOKEN from the environment (if present) for authenticated requests.

    Returns:
        Github: An instance of the PyGitHub client.
    """
    token = os.getenv("GITHUB_TOKEN")
    return Github(token) if token else Github()


class CommitSchema(BaseModel):
    """
    Schema for a Git commit.
    """
    sha: str
    message: str
    author: str
    date: str  # ISO formatted string


class VersionSchema(BaseModel):
    """
    Schema for a repository version.
    """
    id: int
    version: str = ""
    version_number: Optional[str] = None
    release_date: Optional[str] = None
    description: Optional[str] = None
    created_at: str  # ISO formatted string

    def __init__(self, **data):
        # Map version_number to version if version is not provided
        if "version_number" in data and "version" not in data:
            data["version"] = data["version_number"]
        super().__init__(**data)


class CommentCreate(BaseModel):
    """
    Model for creating a new comment.
    """
    comment: str
    author: Optional[str] = "Anonymous"


class CommentResponse(BaseModel):
    """
    Model for comment response.
    """
    id: int
    comment: str
    author: str
    created_at: str


class RepoMetadataUpdate(BaseModel):
    """
    Model for updating repository metadata.
    """
    tags: str
    notes: str


class MessageResponse(BaseModel):
    """
    Generic message response.
    """
    message: str


class RepositoryDetail(BaseModel):
    """
    Detailed repository data including metadata, commits, comments, and versions.
    """
    id: str
    name: str
    description: Optional[str] = None
    url: Optional[str] = None
    topics: Optional[str] = None
    license: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    stars: Optional[int] = None
    forks: Optional[int] = None
    issues: Optional[int] = None
    contributors: Optional[str] = None
    commits: Optional[int] = None
    last_commit: Optional[str] = None
    tags: List[str] = []
    notes: Optional[str] = None
    last_synced: Optional[str] = None
    recent_commits: List[CommitSchema]
    comments: List[CommentResponse]
    versions: List[VersionSchema]


async def fetch_recent_commits(
    gh_client: Github,
    repo_id: str,
    limit: int = 10,
    max_retries: int = 2,
    offline_mode: bool = False
) -> List[CommitSchema]:
    """
    Fetch recent commits for a GitHub repository using a thread pool.
    In offline mode, returns an empty list without attempting to contact GitHub.

    Args:
        gh_client (Github): Authenticated GitHub client instance.
        repo_id (str): Repository identifier (owner/name).
        limit (int, optional): Maximum number of commits to fetch. Defaults to 10.
        max_retries (int, optional): Number of retry attempts on failure. Defaults to 2.
        offline_mode (bool, optional): If True, skip GitHub API calls. Defaults to False.

    Returns:
        List[CommitSchema]: List of commits as Pydantic models.

    Raises:
        None: All exceptions are caught and logged; returns empty list on error.
    """
    # If in offline mode, don't try to contact GitHub
    if offline_mode:
        logger.info(f"Offline mode: skipping GitHub commit fetch for {repo_id}")
        return []

    # Set a short timeout to avoid long waits
    timeout = 3  # 3 seconds timeout

    try:
        loop = asyncio.get_event_loop()
        # Use asyncio.wait_for to add a timeout
        commits = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: get_recent_commits(
                    gh_client.get_repo(repo_id),
                    limit=limit,
                    max_retries=0  # No retries to avoid delays
                )
            ),
            timeout=timeout
        )
        return [CommitSchema(**c) for c in commits]
    except asyncio.TimeoutError:
        logger.warning(f"Timeout fetching commits for {repo_id} - falling back to offline mode")
        return []
    except GithubException as e:
        logger.error(f"GitHub error fetching commits for {repo_id}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error fetching commits for {repo_id}: {e}")
    return []


@router.get(
    "/{repo_id:path}",
    response_model=RepositoryDetail,
    summary="Get a single repository by ID",
)
async def get_repository_detail(repo_id: str):
    """
    Retrieve full repository info, including recent commits, comments, and versions.

    Args:
        repo_id (str): Unique owner/repo identifier (e.g., "octocat/Hello-World").

    Returns:
        RepositoryDetail: A Pydantic model containing:
            - id: repository ID
            - name: repository name
            - tags: list of tags
            - notes: optional notes
            - recent_commits: list of latest commits (limit configurable)
            - comments: list of CommentResponse
            - versions: list of VersionSchema

    Raises:
        HTTPException (404): If repository with `repo_id` does not exist.
    """
    # URL-decode the repository ID to handle URL-encoded slashes
    import urllib.parse
    decoded_repo_id = urllib.parse.unquote(repo_id)
    logger.info(f"Looking up repository with ID: {decoded_repo_id} (original: {repo_id})")

    repo_data = await db_get_repository(decoded_repo_id)
    if not repo_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    # Check if we can connect to GitHub
    offline_mode = False
    try:
        # Try to make a quick connection to GitHub to check if we're online
        import socket
        socket.create_connection(("api.github.com", 443), timeout=1)
    except (socket.timeout, socket.error):
        # If we can't connect, assume we're offline
        logger.warning("Cannot connect to GitHub - operating in offline mode")
        offline_mode = True

    gh_client = get_gh_client()

    # Only fetch comments and versions initially, not commits
    comments_task = asyncio.create_task(db_get_comments(decoded_repo_id))
    versions_task = asyncio.create_task(db_get_versions(decoded_repo_id))

    comments, versions = await asyncio.gather(
        comments_task, versions_task, return_exceptions=True
    )

    # Initialize empty commits list - will be fetched separately when needed
    recent_commits = []

    if isinstance(comments, Exception):
        logger.error(f"Error fetching comments for {repo_id}: {comments}")
        comments = []
    if isinstance(versions, Exception):
        logger.error(f"Error fetching versions for {repo_id}: {versions}")
        versions = []

    # Convert tags from comma-separated string to list
    if "tags" in repo_data and isinstance(repo_data["tags"], str):
        repo_data["tags"] = [tag.strip() for tag in repo_data["tags"].split(",")] if repo_data["tags"] else []

    return RepositoryDetail(
        **repo_data,
        recent_commits=recent_commits,
        comments=comments,
        versions=versions,
    )


@router.put(
    "/{repo_id:path}/metadata",
    response_model=MessageResponse,
    summary="Update repository metadata (tags and notes)",
)
async def update_repo_metadata(
    repo_id: str,
    data: RepoMetadataUpdate = Body(...),
):
    """
    Update the metadata (tags and notes) of a repository.

    Args:
        repo_id (str): The ID of the repository.
        data (RepoMetadataUpdate): The new metadata to apply.

    Returns:
        MessageResponse: A message indicating the result of the update.

    Raises:
        HTTPException (404): If the repository is not found.
        HTTPException (500): If the update fails unexpectedly.
    """
    # URL-decode the repository ID to handle URL-encoded slashes
    import urllib.parse
    decoded_repo_id = urllib.parse.unquote(repo_id)
    logger.info(f"Updating metadata for repository with ID: {decoded_repo_id} (original: {repo_id})")

    try:
        success = await db_update_repository_metadata(
            decoded_repo_id, data.tags, data.notes
        )
    except Exception as e:
        logger.error(f"Error updating metadata for {decoded_repo_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update metadata"
        )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    return MessageResponse(message="Repository metadata updated")


@router.post(
    "/{repo_id:path}/comments",
    response_model=CommentResponse,
    summary="Add a comment to a repository",
)
async def add_repository_comment(
    repo_id: str,
    comment_data: CommentCreate = Body(...),
):
    """
    Add a comment to a repository.

    Args:
        repo_id (str): The ID of the repository.
        comment_data (CommentCreate): The comment payload.

    Returns:
        CommentResponse: The newly created comment.

    Raises:
        HTTPException (404): If the repository is not found.
        HTTPException (500): If the comment creation fails.
    """
    # URL-decode the repository ID to handle URL-encoded slashes
    import urllib.parse
    decoded_repo_id = urllib.parse.unquote(repo_id)
    logger.info(f"Adding comment to repository with ID: {decoded_repo_id} (original: {repo_id})")

    repo = await db_get_repository(decoded_repo_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    try:
        comment_id = await db_add_comment(
            decoded_repo_id, comment_data.comment, comment_data.author
        )
        all_comments = await db_get_comments(decoded_repo_id)
        new = next((c for c in all_comments if c["id"] == comment_id), None)
        if not new:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Comment added but not found"
            )
        return CommentResponse(**new)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding comment for {decoded_repo_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add comment"
        )


@router.get(
    "/{repo_id:path}/comments",
    response_model=List[CommentResponse],
    summary="Get comments for a repository",
)
async def get_repository_comments(
    repo_id: str,
    limit: int = Query(20, description="Maximum number of comments to return"),
):
    """
    Get comments for a repository.

    Args:
        repo_id (str): The ID of the repository.
        limit (int, optional): Maximum number of comments to return. Defaults to 20.

    Returns:
        List[CommentResponse]: A list of comments.

    Raises:
        HTTPException (404): If the repository is not found.
        HTTPException (500): If comments retrieval fails.
    """
    # URL-decode the repository ID to handle URL-encoded slashes
    import urllib.parse
    decoded_repo_id = urllib.parse.unquote(repo_id)
    logger.info(f"Looking up repository for comments with ID: {decoded_repo_id} (original: {repo_id})")

    repo = await db_get_repository(decoded_repo_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    try:
        comments = await db_get_comments(decoded_repo_id)
        return [CommentResponse(**c) for c in comments[:limit]]
    except Exception as e:
        logger.error(f"Error retrieving comments for {decoded_repo_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get comments"
        )


@router.get(
    "/{repo_id:path}/commits/",
    response_model=List[CommitSchema],
    summary="Get recent commits for a repository",
)
async def get_repository_commits(
    repo_id: str,
    limit: int = Query(10, description="Maximum number of commits to return"),
):
    """
    Get recent commits for a repository.

    Args:
        repo_id (str): The ID of the repository.
        limit (int, optional): Maximum number of commits to return. Defaults to 10.

    Returns:
        List[CommitSchema]: A list of recent commits.

    Raises:
        HTTPException (404): If the repository is not found.
        HTTPException (500): If commits retrieval fails.
    """
    # URL-decode the repository ID to handle URL-encoded slashes
    import urllib.parse
    decoded_repo_id = urllib.parse.unquote(repo_id)
    logger.info(f"Looking up repository with ID: {decoded_repo_id} (original: {repo_id})")

    repo = await db_get_repository(decoded_repo_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    # Check if we can connect to GitHub
    offline_mode = False
    try:
        # Try to make a quick connection to GitHub to check if we're online
        import socket
        socket.create_connection(("api.github.com", 443), timeout=1)
    except (socket.timeout, socket.error):
        # If we can't connect, assume we're offline
        logger.warning("Cannot connect to GitHub - operating in offline mode")
        offline_mode = True

    gh_client = get_gh_client()

    try:
        commits = await fetch_recent_commits(gh_client, decoded_repo_id, limit=limit, offline_mode=offline_mode)
        return commits
    except Exception as e:
        logger.error(f"Error retrieving commits for {decoded_repo_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get commits"
        )
