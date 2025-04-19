from fastapi import APIRouter
from pydantic import BaseModel
from fastapi import Body
from fastapi import HTTPException
from github import Github
from nuggit.util.db import get_repository
from nuggit.util.db import update_repository_metadata
from nuggit.util.github import get_recent_commits

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

    # Add commits to the response
    return {**repo_data, "recent_commits": recent_commits}


class RepoMetadataUpdate(BaseModel):
    """
    Model for updating repository metadata.
    """
    tags: str
    notes: str


@router.put("/{repo_id:path}", summary="Update repository metadata (tags and notes)")
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

