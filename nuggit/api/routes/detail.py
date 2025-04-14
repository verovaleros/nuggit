# nuggit/api/routes/detail.py

from fastapi import APIRouter
from pydantic import BaseModel
from fastapi import Body
from fastapi import HTTPException
from github import Github
from nuggit.util.db import get_repository
from nuggit.util.db import update_repository_metadata  # make sure this exists!
from nuggit.util.github import get_recent_commits  # ✅ make sure this is imported

router = APIRouter()

@router.get("/{repo_id:path}", summary="Get a single repository by ID")
def get_repository_detail(repo_id: str):
    repo_data = get_repository(repo_id)
    if not repo_data:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Fetch recent commits from GitHub
    try:
        gh = Github()  # You can pass a token here if needed
        repo = gh.get_repo(repo_id)
        recent_commits = get_recent_commits(repo)
    except Exception as e:
        recent_commits = []
        print(f"Could not fetch commits for {repo_id}: {e}")

    # Add commits to the response
    return {**repo_data, "recent_commits": recent_commits}


class RepoMetadataUpdate(BaseModel):
    tags: str
    notes: str


@router.put("/{repo_id:path}", summary="Update repository metadata (tags and notes)")
def update_repo_metadata(repo_id: str, data: RepoMetadataUpdate = Body(...)):
    success = update_repository_metadata(repo_id, data.tags, data.notes)
    if not success:
        raise HTTPException(status_code=404, detail="Repository not found")
    return {"message": "Repository metadata updated"}

