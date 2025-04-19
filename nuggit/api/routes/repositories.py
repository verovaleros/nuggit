# nuggit/api/routes/repositories.py
import os
import sqlite3
from fastapi import APIRouter, HTTPException, Body
from nuggit.util.db import list_all_repositories
from nuggit.util.github import get_repo_info


router = APIRouter()
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "nuggit.db"))


@router.get("/", summary="List all repositories")
def get_repositories():
    """
    List all repositories in the database.

    Returns:
        dict: A dictionary containing a list of all repositories.

    Raises:
        HTTPException: If there is an error fetching the repositories.
    """
    try:
        repos = list_all_repositories()
        return {"repositories": repos}
    except Exception as e:
        logging.error(f"Error listing repositories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list repositories: {str(e)}")


@router.get("/check/{repo_id:path}", summary="Check if a repository exists")
def check_repository(repo_id: str):
    """
    Check if a repository exists in the database.

    Args:
        repo_id (str): The ID of the repository to check.

    Returns:
        dict: A dictionary indicating whether the repository exists.

    Raises:
        HTTPException: If there is an error checking the repository.
    """
    try:
        repo = get_repository(repo_id)
        return {
            "exists": repo is not None,
            "repository": repo if repo else None
        }
    except Exception as e:
        logging.error(f"Error checking repository {repo_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check repository: {str(e)}")


# Define Pydantic models for request validation
class RepositoryInput(BaseModel):
    """Model for repository input with validation."""
    id: Optional[str] = Field(None, description="Repository ID in the format 'owner/name'")
    url: Optional[str] = Field(None, description="GitHub repository URL")
    token: Optional[str] = Field(None, description="GitHub API token for authentication")

    @validator('id')
    def validate_id_format(cls, v):
        if v and not re.match(r'^[\w.-]+/[\w.-]+$', v):
            raise ValueError("Repository ID must be in the format 'owner/name'")
        return v

    @validator('url')
    def validate_url(cls, v, values):
        if not v and not values.get('id'):
            raise ValueError("Either 'id' or 'url' must be provided")
        if v and not (v.startswith('http://github.com/') or v.startswith('https://github.com/')):
            raise ValueError("URL must be a valid GitHub repository URL")
        return v

class RepositoryResponse(BaseModel):
    """Model for repository response."""
    message: str
    repository: dict

    try:
        owner, name = repo_id.strip().split('/')
    except ValueError:
        raise HTTPException(status_code=400, detail="Repository ID must be in the format 'owner/name'")

    repo_info = get_repo_info(owner, name)
    if not repo_info:
        raise HTTPException(status_code=404, detail="Repository not found on GitHub")

    # Store in SQLite
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO repositories (
                id, name, description, url, topics, license, created_at, updated_at,
                stars, forks, issues, contributors, commits, last_commit, tags, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            repo_info["id"],
            repo_info["name"],
            repo_info["description"],
            repo_info["url"],
            repo_info["topics"],
            repo_info["license"],
            repo_info["created_at"],
            repo_info["updated_at"],
            repo_info["stars"],
            repo_info["forks"],
            repo_info["issues"],
            repo_info["contributors"],
            repo_info["commits"],
            repo_info["last_commit"],
            repo_info["tags"],
            repo_info["notes"]
        ))

        conn.commit()
        conn.close()

        return {"message": f"Repository '{repo_info['id']}' added successfully."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save to database: {e}")
