from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logging
import os

# Initialize comprehensive logging
from nuggit.util.logging_config import init_logging_from_env, RequestLoggingMiddleware, LogTimer

# Initialize logging system
logging_setup = init_logging_from_env()
logger = logging.getLogger(__name__)

from nuggit.api.routes import repositories
from nuggit.api.routes import detail
from nuggit.api.routes import health
import nuggit.api.routes.versions as versions
from nuggit.api.utils.error_handling import (
    NuggitException, handle_validation_error, handle_generic_error,
    create_error_response, ErrorCode, log_error_context
)

app = FastAPI(
    title="Nuggit API",
    description="API for managing and reviewing GitHub repositories",
    version="0.1.0"
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Optional: allow frontend apps to talk to API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("Nuggit API starting up", extra={
    "event_type": "startup",
    "api_version": "0.1.0",
    "logging_config": logging_setup["config"].__dict__
})


# Global exception handlers
@app.exception_handler(NuggitException)
async def nuggit_exception_handler(request: Request, exc: NuggitException):
    """Handle custom Nuggit exceptions."""
    log_error_context(exc, request)

    return create_error_response(
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        path=str(request.url.path)
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI request validation errors."""
    log_error_context(exc, request)
    return handle_validation_error(exc)


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    log_error_context(exc, request)
    return handle_validation_error(exc)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTPException with standardized format."""
    log_error_context(exc, request)

    # If detail is already a dict (standardized format), return as-is
    if isinstance(exc.detail, dict) and 'error_code' in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )

    # Otherwise, standardize the response
    error_code = ErrorCode.REPOSITORY_NOT_FOUND if exc.status_code == 404 else ErrorCode.INTERNAL_SERVER_ERROR

    return create_error_response(
        error_code=error_code,
        message=str(exc.detail),
        status_code=exc.status_code,
        path=str(request.url.path)
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all other unexpected exceptions."""
    log_error_context(exc, request)
    return handle_generic_error(exc, "request processing")

# Include routers
# Note: Order matters! More specific routes should come before general ones
# Health and monitoring routes
app.include_router(health.router, prefix="/health", tags=["health"])
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
