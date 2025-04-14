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
    repos = list_all_repositories()
    return {"repositories": repos}


@router.post("/", summary="Fetch and store repository metadata from GitHub")
def add_repository(repo: dict = Body(...)):
    repo_id = repo.get("id")
    if not repo_id:
        raise HTTPException(status_code=400, detail="Missing repository ID")

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
