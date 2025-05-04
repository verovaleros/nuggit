from fastapi import APIRouter, Body, HTTPException, Query, Path, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
import urllib.parse
import difflib
import logging

from nuggit.util.async_db import (
    get_repository,
    add_version,
    get_versions,
    get_repository_history
)

logger = logging.getLogger(__name__)

# Single router for version endpoints and comparison
router = APIRouter()

# Alias for backward compatibility
compare_router = router


class VersionCreate(BaseModel):
    """
    Payload for creating a new repository version.
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
    release_date: Optional[str]
    description: Optional[str]
    created_at: str


class VersionComparisonResponse(BaseModel):
    """
    Model for version comparison response.
    """
    version1: Dict[str, Any]
    version2: Dict[str, Any]
    differences: Dict[str, Any]


async def repo_or_404(
    repo_id: str = Path(..., description="Repository identifier (may be URL-encoded)")
) -> Dict[str, Any]:
    """
    Dependency: resolve repository ID, raising 404 if not found.

    Args:
        repo_id (str): The ID of the repository.

    Returns:
        dict: A dictionary containing the repository details.

    Raises:
        HTTPException: If the repository is not found.
    """
    actual = urllib.parse.unquote(repo_id)
    repo = await get_repository(actual)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


def _compare_text(a: str, b: str) -> Dict[str, Any]:
    """
    Compare two text fields, returning whether they differ and a unified diff.

    Args:
        a (str): The first text to compare.
        b (str): The second text to compare.

    Returns:
        dict: A dictionary containing the comparison results.
    """
    changed = a != b
    diff = list(difflib.unified_diff([a or ""], [b or ""], lineterm=""))
    if len(diff) > 2 and diff[0].startswith('---'):
        diff = diff[2:]
    return {"changed": changed, "diff": diff}


@router.post(
    "/{repo_id:path}/versions",
    summary="Add a version to a repository",
    response_model=VersionResponse
)
async def add_repository_version(
    repo: Dict[str, Any] = Depends(repo_or_404),
    version_data: VersionCreate = Body(...)
) -> VersionResponse:
    """
    Add a version to a repository.

    Args:
        repo: Resolved repository record.
        version_data: Version payload.

    Returns:
        VersionResponse: The newly created version.

    Raises:
        HTTPException: If creation fails.
    """
    version_id = await add_version(
        repo_id=repo["id"],
        version_number=version_data.version_number,
        release_date=version_data.release_date,
        description=version_data.description
    )
    # Efficient retrieval of the created version
    versions = await get_versions(repo["id"])
    version = next(
        (v for v in versions if v["id"] == version_id),
        None
    )
    if not version:
        raise HTTPException(status_code=500, detail="Created version not found")
    return VersionResponse(**version)


@router.get(
    "/{repo_id:path}/versions",
    summary="Get versions for a repository",
    response_model=List[VersionResponse]
)
async def list_versions(
    repo: Dict[str, Any] = Depends(repo_or_404),
    limit: int = Query(20, description="Maximum number of versions to return")
) -> List[VersionResponse]:
    """
    Get versions for a repository.

    Args:
        repo: Resolved repository record.
        limit: Maximum number of versions.

    Returns:
        List[VersionResponse]: List of versions.

    Raises:
        HTTPException: If retrieval fails.
    """
    versions = await get_versions(repo["id"])
    return [VersionResponse(**v) for v in versions[:limit]]


@router.get(
    "/{repo_id:path}/versions/compare",
    summary="Compare two versions",
    response_model=VersionComparisonResponse
)
@router.get(
    "/{repo_id:path}/compare",
    summary="Compare two versions (alternate path)",
    response_model=VersionComparisonResponse
)
async def compare_versions(
    repo: Dict[str, Any] = Depends(repo_or_404),
    version1_id: int = Query(..., description="ID of the first version"),
    version2_id: int = Query(..., description="ID of the second version")
) -> VersionComparisonResponse:
    """
    Compare two versions of a repository.

    Args:
        repo: Resolved repository record.
        version1_id: ID of the first version.
        version2_id: ID of the second version.

    Returns:
        VersionComparisonResponse: The comparison result.

    Raises:
        HTTPException: If versions not found or comparison fails.
    """
    versions = await get_versions(repo["id"])
    version_map = {v["id"]: v for v in versions}
    if version1_id not in version_map:
        raise HTTPException(status_code=404, detail=f"Version {version1_id} not found")
    if version2_id not in version_map:
        raise HTTPException(status_code=404, detail=f"Version {version2_id} not found")
    v1, v2 = version_map[version1_id], version_map[version2_id]
    differences = {
        "version_number": _compare_text(v1["version_number"], v2["version_number"]),
        "release_date": _compare_text(v1.get("release_date", ""), v2.get("release_date", "")),
        "description": _compare_text(v1.get("description", ""), v2.get("description", ""))
    }
    return VersionComparisonResponse(version1=v1, version2=v2, differences=differences)


@router.get(
    "/get-versions",
    summary="Get versions (query params)",
    response_model=List[VersionResponse]
)
async def list_versions_query(
    repo_id: str = Query(..., description="The repository ID"),
    limit: int = Query(20, description="Maximum number of versions to return")
) -> List[VersionResponse]:
    """
    Query-parameter-based endpoint for listing versions.

    Args:
        repo_id: Repository ID.
        limit: Maximum number of versions.

    Returns:
        List[VersionResponse]: List of versions.

    Raises:
        HTTPException: If the repository is not found.
    """
    repo = await repo_or_404(repo_id)
    return await list_versions(repo, limit)


@router.get(
    "/compare-versions",
    summary="Compare versions (query params)",
    response_model=VersionComparisonResponse
)
async def compare_versions_query(
    repo_id: str = Query(..., description="Repository ID"),
    version1_id: int = Query(..., description="ID of the first version"),
    version2_id: int = Query(..., description="ID of the second version")
) -> VersionComparisonResponse:
    """
    Query-parameter-based endpoint for comparing versions.

    Args:
        repo_id: Repository ID.
        version1_id: First version ID.
        version2_id: Second version ID.

    Returns:
        VersionComparisonResponse: The comparison result.

    Raises:
        HTTPException: If not found or comparison fails.
    """
    repo = await repo_or_404(repo_id)
    return await compare_versions(repo, version1_id, version2_id)


async def get_repository_at_version(
    repo_id: str,
    version_timestamp: str
) -> Dict[str, Any]:
    """
    Get repository data as it was at the time of a specific version.

    Args:
        repo_id: ID of the repository.
        version_timestamp: ISO timestamp of the target version.

    Returns:
        Dict[str, Any]: Repository fields at that version.

    Raises:
        HTTPException: If repository not found or timestamp invalid.
    """
    repo = await get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    state = repo.copy()
    history = await get_repository_history(repo_id)
    for change in sorted(history, key=lambda x: x["changed_at"], reverse=True):
        if change["changed_at"] <= version_timestamp:
            break
        state[change["field"]] = change["old_value"]
    return state
