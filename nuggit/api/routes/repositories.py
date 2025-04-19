import os
import re
import time
import logging
import sqlite3
from os import getenv
from typing import Optional, Union
from pydantic import BaseModel, Field, validator
from fastapi import APIRouter, HTTPException, Body, Query, Depends
from nuggit.util.db import list_all_repositories, insert_or_update_repo, get_repository, delete_repository as db_delete_repository, update_repository_fields
from nuggit.util.github import get_repo_info, validate_repo_url
from github.GithubException import GithubException


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


@router.put("/{repo_id:path}", summary="Update repository information from GitHub")
def update_repository(repo_id: str, token: Optional[str] = None, max_retries: int = Query(3, description="Maximum number of retries for GitHub API calls")):
    # Use token from environment if not provided
    if token is None:
        token = getenv("GITHUB_TOKEN")
        if token:
            logging.info(f"Using GitHub token from environment: {token[:4]}...")
        else:
            logging.warning("No GitHub token found in environment")
    """
    Update repository information from GitHub.

    Args:
        repo_id (str): The ID of the repository to update.
        token (str, optional): GitHub API token for authentication. Defaults to None.
        max_retries (int, optional): Maximum number of retries for GitHub API calls. Defaults to 3.

    Returns:
        dict: A message indicating the result of the operation and the updated repository details.

    Raises:
        HTTPException: If the repository is not found in the database, not found on GitHub,
                      or there is an error updating the repository.
    """
    # Check if repository exists in the database
    existing_repo = get_repository(repo_id)
    if not existing_repo:
        raise HTTPException(status_code=404, detail=f"Repository {repo_id} not found in the database")

    try:
        owner, name = repo_id.strip().split('/')
    except ValueError:
        raise HTTPException(status_code=400, detail="Repository ID must be in the format 'owner/name'")

    # Retry logic for GitHub API rate limits
    last_exception = None
    for attempt in range(max_retries):
        try:
            # Get updated repository information from GitHub
            repo_info = get_repo_info(owner, name, token=token)
            if not repo_info:
                raise HTTPException(status_code=404, detail=f"Repository {repo_id} not found on GitHub")

            # Save to DB using centralized logic
            insert_or_update_repo(repo_info)

            # Return success response with repository details
            return {
                "message": f"Repository '{repo_info['id']}' updated successfully.",
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
                raise HTTPException(status_code=404, detail=f"Repository {repo_id} not found on GitHub")
            else:
                # Other GitHub exceptions
                break
        except Exception as e:
            last_exception = e
            logging.error(f"Error updating repository {repo_id}: {e}")
            break

    # If we get here, all retries failed or another exception occurred
    error_message = str(last_exception) if last_exception else "Unknown error"
    raise HTTPException(status_code=500, detail=f"Failed to update repository: {error_message}")


class BatchRepositoryInput(BaseModel):
    """Model for batch repository import."""
    repositories: list[str] = Field(..., description="List of repository IDs in the format 'owner/name'")
    token: Optional[str] = Field(None, description="GitHub API token for authentication")


class RepositoryFieldsUpdate(BaseModel):
    """Model for updating repository fields."""
    license: Optional[str] = Field(None, description="Repository license")
    stars: Optional[int] = Field(None, description="Number of stars")
    topics: Optional[str] = Field(None, description="Repository topics")
    commits: Optional[int] = Field(None, description="Total number of commits")


@router.post("/batch", summary="Import multiple repositories at once")
def batch_import_repositories(batch_input: BatchRepositoryInput = Body(...)):
    """
    Import multiple repositories at once.

    Args:
        batch_input (BatchRepositoryInput): The batch import request with a list of repository IDs.

    Returns:
        dict: A summary of the import operation.

    Raises:
        HTTPException: If there is an error with the batch import.
    """
    if not batch_input.repositories:
        raise HTTPException(status_code=400, detail="No repositories provided for import")

    results = {
        "successful": [],
        "failed": []
    }

    for repo_id in batch_input.repositories:
        try:
            # Validate repository ID format
            if not re.match(r'^[\w.-]+/[\w.-]+$', repo_id):
                results["failed"].append({
                    "id": repo_id,
                    "error": "Invalid repository ID format"
                })
                continue

            owner, name = repo_id.strip().split('/')

            # Get repository information from GitHub
            repo_info = get_repo_info(owner, name, token=batch_input.token)
            if not repo_info:
                results["failed"].append({
                    "id": repo_id,
                    "error": "Repository not found on GitHub"
                })
                continue

            # Save to DB
            insert_or_update_repo(repo_info)

            # Add to successful list
            results["successful"].append({
                "id": repo_id,
                "name": repo_info["name"]
            })

        except Exception as e:
            logging.error(f"Error importing repository {repo_id}: {e}")
            results["failed"].append({
                "id": repo_id,
                "error": str(e)
            })

    # Return summary
    return {
        "message": f"Batch import completed. {len(results['successful'])} succeeded, {len(results['failed'])} failed.",
        "results": results
    }


@router.patch("/{repo_id:path}/fields", summary="Update specific repository fields")
def update_repository_field_values(repo_id: str, fields: RepositoryFieldsUpdate = Body(...)):
    """
    Update specific fields of a repository.

    Args:
        repo_id (str): The ID of the repository.
        fields (RepositoryFieldsUpdate): The fields to update.

    Returns:
        dict: A message indicating the result of the operation and the updated repository details.

    Raises:
        HTTPException: If the repository is not found or there is an error updating the fields.
    """
    # Check if repository exists
    existing_repo = get_repository(repo_id)
    if not existing_repo:
        raise HTTPException(status_code=404, detail=f"Repository {repo_id} not found in the database")

    try:
        # Convert the fields model to a dictionary, excluding None values
        fields_dict = {k: v for k, v in fields.dict().items() if v is not None}

        if not fields_dict:
            raise HTTPException(status_code=400, detail="No fields provided for update")

        # Update the fields
        success = update_repository_fields(repo_id, fields_dict)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update repository fields")

        # Get the updated repository
        updated_repo = get_repository(repo_id)

        return {
            "message": f"Repository '{repo_id}' fields updated successfully.",
            "repository": updated_repo
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error updating repository fields for {repo_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update repository fields: {str(e)}")


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
