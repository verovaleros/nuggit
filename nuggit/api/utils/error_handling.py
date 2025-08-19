"""
Standardized error handling utilities for the Nuggit API.

This module provides consistent error response formats, exception handling,
and error logging across all API endpoints.
"""

import logging
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, Union
from enum import Enum

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """Standardized error codes for the API."""
    
    # Client errors (4xx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    REPOSITORY_NOT_FOUND = "REPOSITORY_NOT_FOUND"
    INVALID_REPOSITORY_ID = "INVALID_REPOSITORY_ID"
    INVALID_REQUEST_FORMAT = "INVALID_REQUEST_FORMAT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    RATE_LIMITED = "RATE_LIMITED"
    
    # Server errors (5xx)
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    GITHUB_API_ERROR = "GITHUB_API_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    
    # Business logic errors
    OPTIMISTIC_LOCK_ERROR = "OPTIMISTIC_LOCK_ERROR"
    DUPLICATE_RESOURCE = "DUPLICATE_RESOURCE"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"


class ErrorDetail(BaseModel):
    """Detailed error information."""
    
    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Human-readable error message")
    code: Optional[str] = Field(None, description="Machine-readable error code")


class StandardErrorResponse(BaseModel):
    """Standardized error response format."""
    
    error: bool = Field(True, description="Always true for error responses")
    error_code: ErrorCode = Field(..., description="Standardized error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[list[ErrorDetail]] = Field(None, description="Detailed error information")
    timestamp: str = Field(..., description="ISO timestamp when error occurred")
    request_id: Optional[str] = Field(None, description="Unique request identifier")
    path: Optional[str] = Field(None, description="API path that caused the error")


class NuggitException(Exception):
    """Base exception class for Nuggit-specific errors."""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        status_code: int = 500,
        details: Optional[list[ErrorDetail]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or []
        super().__init__(message)


class ValidationException(NuggitException):
    """Exception for validation errors."""
    
    def __init__(self, message: str, details: Optional[list[ErrorDetail]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details=details
        )


class RepositoryNotFoundException(NuggitException):
    """Exception for repository not found errors."""
    
    def __init__(self, repo_id: str):
        super().__init__(
            message=f"Repository '{repo_id}' not found",
            error_code=ErrorCode.REPOSITORY_NOT_FOUND,
            status_code=404
        )


class DatabaseException(NuggitException):
    """Exception for database-related errors."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(
            message=f"Database error: {message}",
            error_code=ErrorCode.DATABASE_ERROR,
            status_code=500
        )
        self.original_error = original_error


class GitHubAPIException(NuggitException):
    """Exception for GitHub API errors."""
    
    def __init__(self, message: str, status_code: int = 500, original_error: Optional[Exception] = None):
        error_code = ErrorCode.RATE_LIMITED if status_code == 403 else ErrorCode.GITHUB_API_ERROR
        super().__init__(
            message=f"GitHub API error: {message}",
            error_code=error_code,
            status_code=status_code
        )
        self.original_error = original_error


class OptimisticLockException(NuggitException):
    """Exception for optimistic locking conflicts."""
    
    def __init__(self, message: str = "Resource was modified by another process"):
        super().__init__(
            message=message,
            error_code=ErrorCode.OPTIMISTIC_LOCK_ERROR,
            status_code=409
        )


def create_error_response(
    error_code: ErrorCode,
    message: str,
    status_code: int = 500,
    details: Optional[list[ErrorDetail]] = None,
    request_id: Optional[str] = None,
    path: Optional[str] = None
) -> JSONResponse:
    """Create a standardized error response."""
    
    error_response = StandardErrorResponse(
        error_code=error_code,
        message=message,
        details=details,
        timestamp=datetime.utcnow().isoformat() + "Z",
        request_id=request_id,
        path=path
    )
    
    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(exclude_none=True)
    )


def handle_validation_error(validation_error: Exception) -> JSONResponse:
    """Handle Pydantic validation errors."""
    
    details = []
    if hasattr(validation_error, 'errors'):
        for error in validation_error.errors():
            field = '.'.join(str(loc) for loc in error.get('loc', []))
            details.append(ErrorDetail(
                field=field,
                message=error.get('msg', 'Validation error'),
                code=error.get('type', 'validation_error')
            ))
    
    return create_error_response(
        error_code=ErrorCode.VALIDATION_ERROR,
        message="Request validation failed",
        status_code=400,
        details=details
    )


def handle_database_error(db_error: Exception, operation: str = "database operation") -> JSONResponse:
    """Handle database-related errors."""
    
    logger.error(f"Database error during {operation}: {db_error}", exc_info=True)
    
    return create_error_response(
        error_code=ErrorCode.DATABASE_ERROR,
        message=f"Database error occurred during {operation}",
        status_code=500
    )


def handle_github_error(github_error: Exception, operation: str = "GitHub operation") -> JSONResponse:
    """Handle GitHub API errors."""
    
    status_code = 500
    error_code = ErrorCode.GITHUB_API_ERROR
    
    # Check if it's a rate limit error
    if hasattr(github_error, 'status') and github_error.status == 403:
        status_code = 429
        error_code = ErrorCode.RATE_LIMITED
    elif hasattr(github_error, 'status') and github_error.status == 404:
        status_code = 404
        error_code = ErrorCode.REPOSITORY_NOT_FOUND
    
    logger.error(f"GitHub API error during {operation}: {github_error}", exc_info=True)
    
    return create_error_response(
        error_code=error_code,
        message=f"GitHub API error occurred during {operation}",
        status_code=status_code
    )


def handle_generic_error(error: Exception, operation: str = "operation") -> JSONResponse:
    """Handle generic unexpected errors."""
    
    logger.error(f"Unexpected error during {operation}: {error}", exc_info=True)
    
    return create_error_response(
        error_code=ErrorCode.INTERNAL_SERVER_ERROR,
        message=f"An unexpected error occurred during {operation}",
        status_code=500
    )


def log_error_context(
    error: Exception,
    request: Optional[Request] = None,
    additional_context: Optional[Dict[str, Any]] = None
):
    """Log error with additional context for debugging."""
    
    context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc()
    }
    
    if request:
        context.update({
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "client": request.client.host if request.client else None
        })
    
    if additional_context:
        context.update(additional_context)
    
    logger.error("Error context", extra={"context": context})


def create_http_exception(
    error_code: ErrorCode,
    message: str,
    status_code: int = 500,
    details: Optional[list[ErrorDetail]] = None
) -> HTTPException:
    """Create an HTTPException with standardized format."""
    
    error_response = StandardErrorResponse(
        error_code=error_code,
        message=message,
        details=details,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )
    
    return HTTPException(
        status_code=status_code,
        detail=error_response.model_dump(exclude_none=True)
    )


# Convenience functions for common error scenarios
def repository_not_found(repo_id: str) -> HTTPException:
    """Create a repository not found exception."""
    return create_http_exception(
        error_code=ErrorCode.REPOSITORY_NOT_FOUND,
        message=f"Repository '{repo_id}' not found",
        status_code=404
    )


def validation_error(message: str, details: Optional[list[ErrorDetail]] = None) -> HTTPException:
    """Create a validation error exception."""
    return create_http_exception(
        error_code=ErrorCode.VALIDATION_ERROR,
        message=message,
        status_code=400,
        details=details
    )


def internal_server_error(message: str = "An internal server error occurred") -> HTTPException:
    """Create an internal server error exception."""
    return create_http_exception(
        error_code=ErrorCode.INTERNAL_SERVER_ERROR,
        message=message,
        status_code=500
    )


def github_api_error(message: str, status_code: int = 500) -> HTTPException:
    """Create a GitHub API error exception."""
    error_code = ErrorCode.RATE_LIMITED if status_code == 429 else ErrorCode.GITHUB_API_ERROR
    return create_http_exception(
        error_code=error_code,
        message=message,
        status_code=status_code
    )


def database_error(message: str = "A database error occurred") -> HTTPException:
    """Create a database error exception."""
    return create_http_exception(
        error_code=ErrorCode.DATABASE_ERROR,
        message=message,
        status_code=500
    )
