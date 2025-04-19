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


@router.post("/", summary="Fetch and store repository metadata from GitHub", response_model=RepositoryResponse)
def add_repository(repo_input: RepositoryInput = Body(...), max_retries: int = Query(3, description="Maximum number of retries for GitHub API calls")):
    """
    Fetch and store repository metadata from GitHub.

    Args:
        repo_input (RepositoryInput): The repository information with either ID or URL.
        max_retries (int, optional): Maximum number of retries for GitHub API calls. Defaults to 3.

    Returns:
        RepositoryResponse: A message indicating the result of the operation and the repository details.

    Raises:
        HTTPException: If the repository information is invalid, the repository is not found on GitHub,
                      or there is an error saving to the database.
    """
    # Extract repository owner and name from either ID or URL
    owner = None
    name = None

    if repo_input.id:
        try:
            owner, name = repo_input.id.strip().split('/')
        except ValueError:
            raise HTTPException(status_code=400, detail="Repository ID must be in the format 'owner/name'")
    elif repo_input.url:
        result = validate_repo_url(repo_input.url)
        if not result:
            raise HTTPException(status_code=400, detail="Invalid GitHub repository URL")
        owner, name = result
    else:
        raise HTTPException(status_code=400, detail="Either repository ID or URL must be provided")

    # Check if repository already exists
    existing_repo = get_repository(f"{owner}/{name}")

    # Retry logic for GitHub API rate limits
    last_exception = None
    for attempt in range(max_retries):
        try:
            # Get repository information from GitHub
            repo_info = get_repo_info(owner, name, token=repo_input.token)
            if not repo_info:
                raise HTTPException(status_code=404, detail="Repository not found on GitHub")

            # Save to DB using centralized logic
            insert_or_update_repo(repo_info)

            # Return success response with repository details
            return {
                "message": f"Repository '{repo_info['id']}' {'updated' if existing_repo else 'added'} successfully.",
                "repository": repo_info
            }
        except GithubException as e:
            last_exception = e
            if e.status == 403 and attempt < max_retries - 1:
                # This might be a rate limit issue, wait and retry
                logging.warning(f"GitHub API rate limit hit, retrying ({attempt+1}/{max_retries}): {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
            elif e.status == 404:
                # Repository not found
                raise HTTPException(status_code=404, detail=f"Repository {owner}/{name} not found on GitHub")
            else:
                # Other GitHub exceptions
                break
        except Exception as e:
            last_exception = e
            logging.error(f"Error processing repository {owner}/{name}: {e}")
            break

    # If we get here, all retries failed or another exception occurred
    error_message = str(last_exception) if last_exception else "Unknown error"
    raise HTTPException(status_code=500, detail=f"Failed to process repository: {error_message}")

    try:
        owner, name = repo_id.strip().split('/')
    except ValueError:
        raise HTTPException(status_code=400, detail="Repository ID must be in the format 'owner/name'")


@router.delete("/{repo_id:path}", summary="Delete a repository from the database")
def delete_repository(repo_id: str):
    """
    Delete a repository from the database.

    Args:
        repo_id (str): The ID of the repository to delete.

    Returns:
        dict: A message indicating the result of the operation.

    Raises:
        HTTPException: If the repository is not found or there is an error deleting it.
    """
    # Check if repository exists
    existing_repo = get_repository(repo_id)
    if not existing_repo:
        raise HTTPException(status_code=404, detail=f"Repository {repo_id} not found")

    try:
        # Use the db function to delete the repository
        success = db_delete_repository(repo_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Repository {repo_id} not found")

        return {"message": f"Repository '{repo_id}' deleted successfully."}
    except sqlite3.Error as e:
        logging.error(f"Database error deleting repository {repo_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        logging.error(f"Error deleting repository {repo_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete repository: {str(e)}")
