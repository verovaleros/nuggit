from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from nuggit.api.routes import repositories
from nuggit.api.routes import detail
import nuggit.api.routes.versions as versions

app = FastAPI(
    title="Nuggit API",
    description="API for managing and reviewing GitHub repositories",
    version="0.1.0"
)

# Optional: allow frontend apps to talk to API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(repositories.router, prefix="/repositories", tags=["repositories"])
app.include_router(detail.router,       prefix="/repositories", tags=["repository detail"])
app.include_router(versions.router,     prefix="/repositories", tags=["versions"])
# version-comparison endpoints share the same router
app.include_router(versions.router,     prefix="/api",          tags=["version comparison"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Nuggit API"}

@app.get("/version")
def get_version():
    """Get version information for troubleshooting."""
    import subprocess
    import os

    # Get git commit hash from environment variable (set during Docker build) or try git command
    git_commit = os.environ.get("GIT_COMMIT", "unknown")

    # If not set in environment, try to get it from git (for local development)
    if git_commit == "unknown":
        try:
            # Find the git repository root by going up from the current file
            # Current file is at: nuggit/api/main.py
            # We need to go up: api -> nuggit -> root
            current_dir = os.path.dirname(os.path.abspath(__file__))  # nuggit/api
            nuggit_dir = os.path.dirname(current_dir)  # nuggit
            repo_root = os.path.dirname(nuggit_dir)  # root

            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                cwd=repo_root
            )
            if result.returncode == 0:
                git_commit = result.stdout.strip()
        except Exception as e:
            # For debugging, you can uncomment the next line
            # print(f"Git command failed: {e}")
            pass

    return {
        "api_version": "0.1.0",
        "git_commit": git_commit,
        "app_name": "Nuggit"
    }
