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
# Note: Order matters! More specific routes should come before general ones
# repositories.router has the root "/" route and specific routes like "/check/{repo_id:path}"
app.include_router(repositories.router, prefix="/repositories", tags=["repositories"])
# versions.router has specific routes like "/{repo_id:path}/versions"
app.include_router(versions.router,     prefix="/repositories", tags=["versions"])
# detail.router has the general "/{repo_id:path}" route and should come last
app.include_router(detail.router,       prefix="/repositories", tags=["repository detail"])
# version-comparison endpoints share the same router
app.include_router(versions.router,     prefix="/api",          tags=["version comparison"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Nuggit API"}

@app.get("/version")
def get_version():
    """Get version information for troubleshooting and display."""
    import subprocess
    import os

    # Get git commit hash from environment variable (set during Docker build) or try git command
    git_commit = os.environ.get("GIT_COMMIT", "ace0a19")

    # If not set in environment, try to get it from git (for local development)
    if git_commit == "unknown":
        try:
            # Try to get git commit from the current working directory first
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                git_commit = result.stdout.strip()
            else:
                # Try from the repository root
                result = subprocess.run(
                    ["git", "rev-parse", "--show-toplevel"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    repo_root = result.stdout.strip()
                    commit_result = subprocess.run(
                        ["git", "rev-parse", "--short", "HEAD"],
                        capture_output=True,
                        text=True,
                        cwd=repo_root
                    )
                    if commit_result.returncode == 0:
                        git_commit = commit_result.stdout.strip()
        except Exception as e:
            # Silently fail for production environments
            pass

    return {
        "api_version": "0.1.0",
        "git_commit": git_commit,
        "app_name": "Nuggit"
    }
