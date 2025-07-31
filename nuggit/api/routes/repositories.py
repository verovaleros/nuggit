import os
import re
import time
import logging
from typing import Optional, List, Callable, Any, Dict, Tuple

from fastapi import APIRouter, HTTPException, Body, Query, Depends
from pydantic import BaseModel, Field, model_validator, field_validator
from github import GithubException

from nuggit.util.db import (
    list_all_repositories,
    insert_or_update_repo,
    get_repository,
    delete_repository as db_delete_repository,
    update_repository_fields,
    update_repository_metadata,
    create_repository_version,
)
from nuggit.util.github import get_repo_info, validate_repo_url

router = APIRouter()

# -- Shared Helpers ---------------------------------------------------------

def retry_github(
    fn: Callable[..., Dict[str, Any]],
    owner: str,
    name: str,
    token: Optional[str],
    retries: int,
    preserve: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Call GitHub API with exponential-backoff retry, optionally preserving fields.

    Args:
        fn: GitHub API function to call (e.g., get_repo_info).
        owner: Repository owner name.
        name: Repository name.
        token: GitHub access token.
        retries: Number of retry attempts on rate limit.
        preserve: Optional dict of fields to preserve and merge into result.

    Returns:
        A dict of repository data with preserved fields if provided.

    Raises:
        HTTPException: 404 if repository not found.
        HTTPException: 500 on other GitHub errors.
    """
    last_exc: Exception = None
    for attempt in range(retries):
        try:
            data = fn(owner, name, token=token)
            if not data:
                raise HTTPException(404, f"{owner}/{name} not found on GitHub")
            if preserve:
                data.update({k: preserve.get(k) for k in preserve})
            return data
        except GithubException as e:
            last_exc = e
            if e.status == 403 and attempt < retries - 1:
                # Only wait if we have retries left
                if retries > 0:
                    wait = 0.5  # Use a minimal wait time
                    logging.warning(f"Rate limit, retrying immediately...")
                    time.sleep(wait)
                continue
            if e.status == 404:
                raise HTTPException(404, f"{owner}/{name} not found on GitHub")
            break
        except Exception as e:
            last_exc = e
            logging.error(f"GitHub call failed: {e}")
            break
    raise HTTPException(500, f"GitHub error: {last_exc}")


def parse_owner_name(id: Optional[str], url: Optional[str]) -> Tuple[str, str]:
    """
    Extract owner and repository name from an ID or URL.

    Args:
        id: Optional string in the format "owner/name".
        url: Optional GitHub repository URL.

    Returns:
        A tuple (owner, name).

    Raises:
        HTTPException: 400 if neither id nor url is provided or invalid.
    """
    if id:
        if not re.match(r'^[\w.-]+/[\w.-]+$', id):
            raise HTTPException(400, "ID must be 'owner/name'")
        return id.split('/', 1)
    if url:
        res = validate_repo_url(url)
        if not res:
            raise HTTPException(400, "Invalid GitHub URL")
        return res
    raise HTTPException(400, "Either 'id' or 'url' must be provided")


def get_token(token: Optional[str] = None) -> Optional[str]:
    """
    Retrieve the GitHub token from the request or environment.

    Args:
        token: Optional token provided in the request.

    Returns:
        The GitHub token string, or None if not set.
    """
    return token or os.getenv("GITHUB_TOKEN")

# -- Schemas ---------------------------------------------------------------

class RepositoryInput(BaseModel):
    id: Optional[str] = Field(None, description="Repository identifier in the format 'owner/name'.")
    url: Optional[str] = Field(None, description="GitHub repository URL.")
    token: Optional[str] = Field(None, description="GitHub access token to use for this request.")

    @model_validator(mode="after")
    def check_id_or_url(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure that either 'id' or 'url' is provided.

        Raises:
            ValueError: If neither field is set.
        """
        #if not (values.get('id') or values.get('url')):
        #    raise ValueError("Either 'id' or 'url' must be provided")
        #return values
        if not (values.id or values.url):
            raise ValueError("Either 'id' or 'url' must be provided")
        return values


class RepositoryResponse(BaseModel):
    message: str = Field(..., description="Status message of the operation.")
    repository: Dict[str, Any] = Field(..., description="The repository data returned.")


class BatchRepositoryInput(BaseModel):
    repositories: List[str] = Field(..., description="List of repository identifiers ('owner/name').")
    token: Optional[str] = Field(None, description="GitHub access token to use for batch operations.")
    tags: Optional[str] = Field(None, description="Comma-separated tags to apply to all repositories in the batch.")

    @field_validator('repositories')
    def non_empty(cls, v: List[str]) -> List[str]:
        """
        Ensure the repositories list is not empty.

        Raises:
            ValueError: If list is empty.
        """
        if not v:
            raise ValueError("Empty repository list")
        return v


class RepositoryFieldsUpdate(BaseModel):
    license: Optional[str] = Field(None, description="Repository license identifier.")
    stars: Optional[int] = Field(None, description="Number of stars to update.")
    topics: Optional[str] = Field(None, description="Comma-separated list of topics.")
    commits: Optional[int] = Field(None, description="Total commit count.")
    tags: Optional[str] = Field(None, description="User-defined tags for the repository.")
    notes: Optional[str] = Field(None, description="User-defined notes about the repository.")


class RepositoryMetadataUpdate(BaseModel):
    tags: str = Field(..., description="New tags for the repository.")
    notes: str = Field(..., description="New notes for the repository.")

# -- Routes ----------------------------------------------------------------

@router.get("/", summary="List all repositories")
def list_repositories():
    """
    List all repositories in the database.

    Returns:
        dict: A mapping with a 'repositories' key containing all records.

    Raises:
        HTTPException: 500 if retrieval fails.
    """
    try:
        return {"repositories": list_all_repositories()}
    except Exception as e:
        logging.error(e)
        raise HTTPException(500, "Could not list repositories")


@router.get("/check/{repo_id:path}", summary="Check if a repository exists")
def check_repository(repo_id: str):
    """
    Check if a repository exists in the database.

    Args:
        repo_id (str): Identifier in the format 'owner/name'.

    Returns:
        dict: Contains 'exists' (bool) and 'repository' data if found.

    Raises:
        HTTPException: 500 if an error occurs during lookup.
    """
    try:
        repo = get_repository(repo_id)
        return {"exists": bool(repo), "repository": repo}
    except Exception as e:
        logging.error(e)
        raise HTTPException(500, "Error checking repository")


@router.post(
    "/",
    summary="Fetch and store repository metadata from GitHub",
    response_model=RepositoryResponse,
)
def add_repository(
    payload: RepositoryInput = Body(...),
    max_retries: int = Query(3, description="Max retry attempts on rate limit."),
):
    """
    Fetch and store repository metadata from GitHub.

    Args:
        payload (RepositoryInput): Contains 'id' or 'url' and optional token.
        max_retries (int): Number of retry attempts on rate limit.

    Returns:
        RepositoryResponse: Message and repository data.

    Raises:
        HTTPException: 400 for validation errors.
        HTTPException: 404 if repository not found on GitHub.
        HTTPException: 500 on other GitHub or DB errors.
    """
    owner, name = parse_owner_name(payload.id, payload.url)
    existing = get_repository(f"{owner}/{name}")
    repo_info = retry_github(get_repo_info, owner, name, payload.token, max_retries)
    insert_or_update_repo(repo_info)
    action = "updated" if existing else "added"
    return {
        "message": f"Repository '{repo_info['id']}' {action} successfully.",
        "repository": repo_info,
    }


@router.put("/{repo_id:path}", summary="Update repository information from GitHub")
def update_repository(
    repo_id: str,
    token: Optional[str] = Depends(get_token),
    max_retries: int = Query(3, description="Max retry attempts on rate limit."),
):
    """
    Update repository information from GitHub and create a new version snapshot.

    Args:
        repo_id (str): Identifier in the format 'owner/name'.
        token (str, optional): GitHub access token.
        max_retries (int): Number of retry attempts on rate limit.

    Returns:
        dict: Message and the updated repository data.

    Raises:
        HTTPException: 404 if repository not found in DB or on GitHub.
        HTTPException: 500 on other errors.
    """
    existing = get_repository(repo_id)
    if not existing:
        raise HTTPException(404, f"{repo_id} not in DB")
    owner, name = repo_id.split('/', 1)
    repo_info = retry_github(
        get_repo_info,
        owner,
        name,
        token,
        max_retries,
        preserve={"tags": existing.get("tags"), "notes": existing.get("notes")},
    )
    insert_or_update_repo(repo_info)
    # Create a new version to track this update
    create_repository_version(repo_id, repo_info)
    return {"message": f"Repository '{repo_id}' updated and versioned successfully.", "repository": repo_info}


@router.post("/batch", summary="Import multiple repositories at once")
def batch_import(batch: BatchRepositoryInput):
    """
    Import multiple repositories from GitHub in a single request.

    Args:
        batch (BatchRepositoryInput): List of repo IDs and optional token.

    Returns:
        dict: Summary message and detailed results for each repo.
    """
    results: Dict[str, List[Any]] = {"successful": [], "failed": []}
    for repo_input in batch.repositories:
        try:
            # Check if this is a GitHub URL or username/repo format
            if repo_input.startswith('http') and 'github.com' in repo_input:
                # This is a GitHub URL
                res = validate_repo_url(repo_input)
                if not res:
                    raise ValueError("Invalid GitHub URL")
                owner, name = res
                repo_id = f"{owner}/{name}"
            elif re.match(r'^[\w.-]+/[\w.-]+$', repo_input):
                # This is a username/repo format
                owner, name = repo_input.split('/', 1)
                repo_id = repo_input
            else:
                raise ValueError("Invalid format, expected 'owner/name' or GitHub URL")

            existing = get_repository(repo_id)
            # Use 1 retry to handle transient issues
            preserve_data = None
            if existing:
                preserve_data = {"tags": existing.get("tags"), "notes": existing.get("notes")}

            # Use the global token if batch.token is None
            token_to_use = batch.token or get_token()
            logging.info(f"Processing {repo_id} with token: {'Yes' if token_to_use else 'No'}")

            try:
                repo_info = retry_github(
                    get_repo_info,
                    owner,
                    name,
                    token_to_use,
                    3,  # Use more retries for batch operations
                    preserve=preserve_data,
                )
            except HTTPException as e:
                logging.error(f"HTTPException for {repo_id}: {e.detail}")
                raise e
            except Exception as e:
                logging.error(f"Unexpected error for {repo_id}: {e}")
                raise e

            # Apply shared tags if provided
            if batch.tags:
                existing_tags = repo_info.get("tags", "")
                if existing_tags:
                    # Merge existing tags with new tags, avoiding duplicates
                    existing_tag_list = [tag.strip() for tag in existing_tags.split(",") if tag.strip()]
                    new_tag_list = [tag.strip() for tag in batch.tags.split(",") if tag.strip()]
                    combined_tags = list(dict.fromkeys(existing_tag_list + new_tag_list))  # Remove duplicates while preserving order
                    repo_info["tags"] = ",".join(combined_tags)
                else:
                    repo_info["tags"] = batch.tags

            insert_or_update_repo(repo_info)
            # If this is an update (not a new repo), create a version
            if existing:
                create_repository_version(repo_id, repo_info)
            results["successful"].append({"id": repo_id, "name": repo_info.get("name")})
        except Exception as e:
            results["failed"].append({"id": repo_input, "error": str(e)})
    return {
        "message": f"Batch import: {len(results['successful'])} succeeded, {len(results['failed'])} failed.",
        "results": results,
    }


@router.put(
    "/{repo_id:path}/metadata/",
    summary="Update repository metadata (tags and notes)"
)
def update_metadata(
    repo_id: str,
    meta: RepositoryMetadataUpdate = Body(...),
):
    """
    Update metadata (tags and notes) for a repository.

    Args:
        repo_id (str): Identifier in the format 'owner/name'.
        meta (RepositoryMetadataUpdate): Contains new tags and notes.

    Returns:
        dict: Message and updated repository data.

    Raises:
        HTTPException: 404 if repo not found.
        HTTPException: 500 if metadata update fails.
    """
    if not get_repository(repo_id):
        raise HTTPException(404, f"{repo_id} not found")
    if not update_repository_metadata(repo_id, meta.tags, meta.notes):
        raise HTTPException(500, "Metadata update failed")
    return {"message": f"Metadata for '{repo_id}' updated.", "repository": get_repository(repo_id)}


@router.patch(
    "/{repo_id:path}/fields",
    summary="Update specific repository fields"
)
def update_fields(
    repo_id: str,
    fields: RepositoryFieldsUpdate = Body(...),
):
    """
    Update specific fields of a repository.

    Args:
        repo_id (str): Identifier in the format 'owner/name'.
        fields (RepositoryFieldsUpdate): Fields to update.

    Returns:
        dict: Message and updated repository data.

    Raises:
        HTTPException: 404 if repo not found.
        HTTPException: 400 if no fields provided.
        HTTPException: 500 if update fails.
    """
    existing = get_repository(repo_id)
    if not existing:
        raise HTTPException(404, f"{repo_id} not found")
    data_to_update = {k: v for k, v in fields.dict().items() if v is not None}
    if not data_to_update:
        raise HTTPException(400, "No fields to update")
    if not update_repository_fields(repo_id, data_to_update):
        raise HTTPException(500, "Field update failed")
    return {"message": f"Fields for '{repo_id}' updated.", "repository": get_repository(repo_id)}


@router.delete("/{repo_id:path}", summary="Delete a repository from the database")
def delete_repository(repo_id: str):
    """
    Delete a repository from the database.

    Args:
        repo_id (str): Identifier in the format 'owner/name'.

    Returns:
        dict: Message indicating deletion result.

    Raises:
        HTTPException: 404 if repo not found.
        HTTPException: 500 if delete fails.
    """
    if not get_repository(repo_id):
        raise HTTPException(404, f"{repo_id} not found")
    if not db_delete_repository(repo_id):
        raise HTTPException(500, "Delete failed")
    return {"message": f"Repository '{repo_id}' deleted successfully."}