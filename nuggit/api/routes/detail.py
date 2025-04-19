from fastapi import APIRouter
from pydantic import BaseModel
from fastapi import Body, Query
from fastapi import HTTPException
from github import Github
from nuggit.util.db import get_repository
from nuggit.util.db import update_repository_metadata
from nuggit.util.db import add_comment, get_comments
from nuggit.util.github import get_recent_commits
from typing import List, Optional

router = APIRouter()

@router.get("/{repo_id:path}", summary="Get a single repository by ID")
def get_repository_detail(repo_id: str):
    """
    Get detailed information about a single repository by its ID.
    Args:
        repo_id (str): The ID of the repository.
    Returns:
        dict: A dictionary containing repository details and recent commits.
    Raises:
        HTTPException: If the repository is not found.
    """
    repo_data = get_repository(repo_id)
    if not repo_data:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Fetch recent commits from GitHub
    try:
        from os import getenv
        # Use token from environment if available for better rate limits
        token = getenv("GITHUB_TOKEN")
        gh = Github(token) if token else Github()
        repo = gh.get_repo(repo_id)

        # Use the improved get_recent_commits function with more commits and retry logic
        recent_commits = get_recent_commits(repo, limit=10, max_retries=2)
    except Exception as e:
        recent_commits = []
        import logging
        logging.error(f"Could not fetch commits for {repo_id}: {e}")

    # Get comments for the repository
    try:
        comments = get_comments(repo_id)
    except Exception as e:
        import logging
        logging.error(f"Could not fetch comments for {repo_id}: {e}")
        comments = []

    # Add commits and comments to the response
    return {**repo_data, "recent_commits": recent_commits, "comments": comments}


class RepoMetadataUpdate(BaseModel):
    """
    Model for updating repository metadata.
    """
    tags: str
    notes: str


@router.put("/{repo_id:path}/metadata", summary="Update repository metadata (tags and notes)")
def update_repo_metadata(repo_id: str, data: RepoMetadataUpdate = Body(...)):
    """
    Update the metadata (tags and notes) of a repository.
    Args:
        repo_id (str): The ID of the repository.
        data (RepoMetadataUpdate): The new metadata to update.
    Returns:
        dict: A message indicating the result of the update.
    Raises:
        HTTPException: If the repository is not found or the update fails.
    """
    success = update_repository_metadata(repo_id, data.tags, data.notes)
    if not success:
        raise HTTPException(status_code=404, detail="Repository not found")
    return {"message": "Repository metadata updated"}


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


@router.post("/{repo_id:path}/comments", summary="Add a comment to a repository", response_model=CommentResponse)
def add_repository_comment(repo_id: str, comment_data: CommentCreate = Body(...)):
    """
    Add a comment to a repository.

    Args:
        repo_id (str): The ID of the repository.
        comment_data (CommentCreate): The comment data.

    Returns:
        CommentResponse: The newly created comment.

    Raises:
        HTTPException: If the repository is not found or the comment creation fails.
    """
    # Check if repository exists
    repo = get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        # Add the comment
        comment_id = add_comment(repo_id, comment_data.comment, comment_data.author)

        # Get all comments to find the newly added one
        all_comments = get_comments(repo_id)
        new_comment = next((c for c in all_comments if c["id"] == comment_id), None)

        if not new_comment:
            raise HTTPException(status_code=500, detail="Comment was added but could not be retrieved")

        return new_comment
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add comment: {str(e)}")


@router.get("/{repo_id:path}/comments", summary="Get comments for a repository", response_model=List[CommentResponse])
def get_repository_comments(repo_id: str, limit: int = Query(20, description="Maximum number of comments to return")):
    """
    Get comments for a repository.

    Args:
        repo_id (str): The ID of the repository.
        limit (int, optional): Maximum number of comments to return. Defaults to 20.

    Returns:
        List[CommentResponse]: A list of comments.

    Raises:
        HTTPException: If the repository is not found or the comments retrieval fails.
    """
    # Check if repository exists
    repo = get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        # Get comments
        comments = get_comments(repo_id)

        # Limit the number of comments
        return comments[:limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get comments: {str(e)}")

