"""
API routes for repository versions.
"""

from fastapi import APIRouter, Body, HTTPException, Query, Path
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import difflib

from nuggit.util.db import get_repository, add_version, get_versions

router = APIRouter(tags=["versions"])

# Create a separate router for the version comparison endpoint
compare_router = APIRouter(tags=["version comparison"])


class VersionCreate(BaseModel):
    """
    Model for creating a new version.
    """
    version_number: str
    release_date: Optional[str] = None
    description: Optional[str] = None


class VersionResponse(BaseModel):
    """
    Model for version response.
    """
    id: int
    version_number: str
    release_date: Optional[str] = None
    description: Optional[str] = None
    created_at: str


@router.post("/{repo_id:path}/versions", summary="Add a version to a repository", response_model=VersionResponse)
def add_repository_version(repo_id: str, version_data: VersionCreate = Body(...)):
    """
    Add a version to a repository.

    Args:
        repo_id (str): The ID of the repository.
        version_data (VersionCreate): The version data.

    Returns:
        VersionResponse: The newly created version.

    Raises:
        HTTPException: If the repository is not found or the version creation fails.
    """
    # Check if repository exists
    repo = get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        # Add the version
        version_id = add_version(
            repo_id=repo_id,
            version_number=version_data.version_number,
            release_date=version_data.release_date,
            description=version_data.description
        )

        # Get all versions to find the newly added one
        all_versions = get_versions(repo_id)
        new_version = next((v for v in all_versions if v["id"] == version_id), None)

        if not new_version:
            raise HTTPException(status_code=500, detail="Version was added but could not be retrieved")

        return new_version
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add version: {str(e)}")


@router.get("/{repo_id:path}/versions", summary="Get versions for a repository", response_model=List[VersionResponse])
def get_repository_versions(repo_id: str, limit: int = Query(20, description="Maximum number of versions to return")):
    """
    Get versions for a repository.

    Args:
        repo_id (str): The ID of the repository.
        limit (int, optional): Maximum number of versions to return. Defaults to 20.

    Returns:
        List[VersionResponse]: A list of versions.

    Raises:
        HTTPException: If the repository is not found or the versions retrieval fails.
    """
    # Check if repository exists
    repo = get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        # Get versions
        versions = get_versions(repo_id)

        # Limit the number of versions
        return versions[:limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get versions: {str(e)}")


class VersionComparisonResponse(BaseModel):
    """
    Model for version comparison response.
    """
    version1: Dict[str, Any]
    version2: Dict[str, Any]
    differences: Dict[str, Any]


@router.get("/{repo_id:path}/versions/compare", summary="Compare two versions", response_model=VersionComparisonResponse)
@router.get("/{repo_id:path}/compare", summary="Compare two versions (alternate path)", response_model=VersionComparisonResponse)
def compare_versions(
    repo_id: str,
    version1_id: int = Query(..., description="ID of the first version"),
    version2_id: int = Query(..., description="ID of the second version")
):
    # Debug logging
    import logging
    logging.info(f"Comparing versions for repo_id: {repo_id}, version1_id: {version1_id}, version2_id: {version2_id}")
    """
    Compare two versions of a repository.

    Args:
        repo_id (str): The ID of the repository.
        version1_id (int): The ID of the first version.
        version2_id (int): The ID of the second version.

    Returns:
        VersionComparisonResponse: The comparison result.

    Raises:
        HTTPException: If the repository or versions are not found, or the comparison fails.
    """
    # Check if repository exists
    import logging
    logging.info(f"Checking if repository exists: {repo_id}")

    # Handle the case where the URL path might include '/versions/compare' or '/compare'
    # This is a workaround for the routing issue
    if '/versions/compare' in repo_id:
        actual_repo_id = repo_id.split('/versions/compare')[0]
        logging.info(f"Extracted actual repo_id from path: {actual_repo_id}")
        repo = get_repository(actual_repo_id)
    elif '/compare' in repo_id:
        actual_repo_id = repo_id.split('/compare')[0]
        logging.info(f"Extracted actual repo_id from path: {actual_repo_id}")
        repo = get_repository(actual_repo_id)
    else:
        repo = get_repository(repo_id)

    if not repo:
        logging.error(f"Repository not found: {repo_id}")
        raise HTTPException(status_code=404, detail="Repository not found")

    # Use the actual repo_id for the rest of the function
    if '/versions/compare' in repo_id or '/compare' in repo_id:
        repo_id = actual_repo_id

    logging.info(f"Repository found: {repo_id}")

    try:
        # Get all versions for the repository
        all_versions = get_versions(repo_id)

        # Find the specified versions
        version1 = next((v for v in all_versions if v["id"] == version1_id), None)
        version2 = next((v for v in all_versions if v["id"] == version2_id), None)

        if not version1:
            raise HTTPException(status_code=404, detail=f"Version with ID {version1_id} not found")

        if not version2:
            raise HTTPException(status_code=404, detail=f"Version with ID {version2_id} not found")

        # Compare the versions
        differences = {
            "version_number": compare_text(version1["version_number"], version2["version_number"]),
            "release_date": compare_text(version1["release_date"], version2["release_date"]),
            "description": compare_text(version1["description"], version2["description"]),
            "created_at": compare_text(version1["created_at"], version2["created_at"])
        }

        return {
            "version1": version1,
            "version2": version2,
            "differences": differences
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare versions: {str(e)}")


# New endpoint for version comparison that doesn't use path parameters for the repository ID
@compare_router.get("/compare-versions", summary="Compare two versions (query params)", response_model=VersionComparisonResponse)
def compare_versions_query(
    repo_id: str = Query(..., description="The ID of the repository"),
    version1_id: int = Query(..., description="ID of the first version"),
    version2_id: int = Query(..., description="ID of the second version")
):
    """
    Compare two versions of a repository using query parameters.

    Args:
        repo_id (str): The ID of the repository.
        version1_id (int): The ID of the first version.
        version2_id (int): The ID of the second version.

    Returns:
        VersionComparisonResponse: The comparison result.

    Raises:
        HTTPException: If the repository or versions are not found, or the comparison fails.
    """
    # Debug logging
    import logging
    logging.info(f"Comparing versions using query params - repo_id: {repo_id}, version1_id: {version1_id}, version2_id: {version2_id}")

    # Check if repository exists
    repo = get_repository(repo_id)
    if not repo:
        logging.error(f"Repository not found: {repo_id}")
        raise HTTPException(status_code=404, detail="Repository not found")

    logging.info(f"Repository found: {repo_id}")

    try:
        # Get all versions for the repository
        all_versions = get_versions(repo_id)

        # Find the specified versions
        version1 = next((v for v in all_versions if v["id"] == version1_id), None)
        version2 = next((v for v in all_versions if v["id"] == version2_id), None)

        if not version1:
            raise HTTPException(status_code=404, detail=f"Version with ID {version1_id} not found")

        if not version2:
            raise HTTPException(status_code=404, detail=f"Version with ID {version2_id} not found")

        # Compare the versions
        differences = {
            "version_number": compare_text(version1["version_number"], version2["version_number"]),
            "release_date": compare_text(version1["release_date"], version2["release_date"]),
            "description": compare_text(version1["description"], version2["description"]),
            "created_at": compare_text(version1["created_at"], version2["created_at"])
        }

        return {
            "version1": version1,
            "version2": version2,
            "differences": differences
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare versions: {str(e)}")


def compare_text(text1, text2):
    """
    Compare two text strings and return the differences.

    Args:
        text1: The first text string (or None).
        text2: The second text string (or None).

    Returns:
        dict: A dictionary containing the comparison result.
    """
    # Handle None values
    text1 = str(text1) if text1 is not None else ""
    text2 = str(text2) if text2 is not None else ""

    # If both texts are the same, return a simple result
    if text1 == text2:
        return {
            "changed": False,
            "diff": None
        }

    # Generate a unified diff
    diff = list(difflib.unified_diff(
        text1.splitlines(),
        text2.splitlines(),
        lineterm="",
        n=0
    ))

    # Remove the headers (first two lines)
    if len(diff) > 2:
        diff = diff[2:]

    return {
        "changed": True,
        "diff": "\n".join(diff) if diff else "Content changed but no line-by-line diff available"
    }
