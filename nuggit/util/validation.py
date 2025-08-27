"""
Data validation utilities for Nuggit database operations.

This module provides comprehensive validation for all data before database insertion,
using Pydantic models to ensure data integrity and consistency.
"""

import re
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from urllib.parse import urlparse
import logging

from nuggit.util.timezone import validate_datetime_string, parse_datetime, to_utc_iso

logger = logging.getLogger(__name__)

# Configuration constants
MAX_COMMA_SEPARATED_ITEMS = 50  # Maximum number of items in comma-separated lists (topics, tags)


class ValidationError(Exception):
    """Raised when data validation fails."""
    pass


class RepositoryModel(BaseModel):
    """Pydantic model for repository data validation."""
    
    id: str = Field(..., min_length=1, max_length=255, description="Repository ID in owner/repo format")
    name: str = Field(..., min_length=1, max_length=255, description="Repository name")
    description: Optional[str] = Field(None, max_length=1000, description="Repository description")
    url: str = Field(..., description="GitHub repository URL")
    topics: Optional[str] = Field(None, max_length=1000, description="Comma-separated topics")
    license: Optional[str] = Field(None, max_length=100, description="License identifier")
    created_at: Optional[str] = Field(None, description="Repository creation timestamp")
    updated_at: Optional[str] = Field(None, description="Repository last update timestamp")
    stars: Optional[int] = Field(None, ge=0, description="Number of stars")
    forks: Optional[int] = Field(None, ge=0, description="Number of forks")
    issues: Optional[int] = Field(None, ge=0, description="Number of open issues")
    contributors: Optional[Union[int, str]] = Field(None, description="Number of contributors")
    commits: Optional[int] = Field(None, ge=0, description="Total number of commits")
    last_commit: Optional[str] = Field(None, description="Last commit timestamp")
    tags: Optional[str] = Field(None, max_length=500, description="User-defined tags")
    notes: Optional[str] = Field(None, max_length=2000, description="User notes")
    last_synced: Optional[str] = Field(None, description="Last sync timestamp")
    version: Optional[int] = Field(1, ge=1, description="Version for optimistic locking")

    @field_validator('id')
    @classmethod
    def validate_repo_id(cls, v: str) -> str:
        """Validate repository ID format (owner/repo)."""
        if not re.match(r'^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$', v):
            raise ValueError('Repository ID must be in owner/repo format')
        return v

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate GitHub URL format."""
        parsed = urlparse(v)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError('Invalid URL format')
        
        if 'github.com' not in parsed.netloc.lower():
            raise ValueError('URL must be a GitHub repository URL')
        
        return v

    @field_validator('created_at', 'updated_at', 'last_commit', 'last_synced')
    @classmethod
    def validate_timestamp(cls, v: Optional[str]) -> Optional[str]:
        """Validate ISO timestamp format using timezone utilities."""
        if v is None:
            return v

        if not validate_datetime_string(v):
            raise ValueError('Timestamp must be in valid ISO format')

        # Normalize to UTC ISO format
        dt = parse_datetime(v)
        if dt is None:
            raise ValueError('Could not parse timestamp')

        return to_utc_iso(dt)

    @field_validator('topics', 'tags')
    @classmethod
    def validate_comma_separated(cls, v: Optional[str]) -> Optional[str]:
        """Validate comma-separated values."""
        if v is None:
            return v
        
        # Check for reasonable number of items
        items = [item.strip() for item in v.split(',') if item.strip()]
        if len(items) > MAX_COMMA_SEPARATED_ITEMS:  # Reasonable limit
            raise ValueError('Too many items in comma-separated list')
        
        return v

    @field_validator('contributors')
    @classmethod
    def validate_contributors(cls, v: Optional[Union[int, str]]) -> Optional[str]:
        """Validate contributors field - convert int to string for database storage."""
        if v is None:
            return v

        # If it's already a string, validate it
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return None
            # Check if it's a numeric string
            if v.isdigit():
                return v
            # Allow special values like "5000+"
            if re.match(r'^\d+\+?$', v):
                return v
            raise ValueError('Contributors must be a number or number with + suffix')

        # If it's an integer, convert to string
        if isinstance(v, int):
            if v < 0:
                raise ValueError('Contributors count cannot be negative')
            return str(v)

        raise ValueError('Contributors must be a number or string')

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate repository name."""
        if not v.strip():
            raise ValueError('Repository name cannot be empty')
        return v.strip()

    @field_validator('description', 'notes')
    @classmethod
    def validate_text_fields(cls, v: Optional[str]) -> Optional[str]:
        """Validate text fields."""
        if v is None:
            return v
        
        # Strip whitespace and check for reasonable length
        v = v.strip()
        if not v:
            return None
        
        return v


class RepositoryHistoryModel(BaseModel):
    """Pydantic model for repository history validation."""
    
    repo_id: str = Field(..., min_length=1, max_length=255)
    field: str = Field(..., min_length=1, max_length=100)
    old_value: Optional[str] = Field(None, max_length=2000)
    new_value: Optional[str] = Field(None, max_length=2000)
    changed_at: str = Field(..., description="Change timestamp")

    @field_validator('repo_id')
    @classmethod
    def validate_repo_id(cls, v: str) -> str:
        """Validate repository ID format."""
        if not re.match(r'^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$', v):
            raise ValueError('Repository ID must be in owner/repo format')
        return v

    @field_validator('changed_at')
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate timestamp format using timezone utilities."""
        if not validate_datetime_string(v):
            raise ValueError('Timestamp must be in valid ISO format')

        # Normalize to UTC ISO format
        dt = parse_datetime(v)
        if dt is None:
            raise ValueError('Could not parse timestamp')

        return to_utc_iso(dt)

    @field_validator('field')
    @classmethod
    def validate_field_name(cls, v: str) -> str:
        """Validate field name."""
        allowed_fields = {
            'name', 'description', 'url', 'topics', 'license', 'created_at',
            'updated_at', 'stars', 'forks', 'issues', 'contributors', 'commits',
            'last_commit', 'tags', 'notes', 'last_synced'
        }
        if v not in allowed_fields:
            raise ValueError(f'Invalid field name: {v}')
        return v


class RepositoryCommentModel(BaseModel):
    """Pydantic model for repository comment validation."""
    
    repo_id: str = Field(..., min_length=1, max_length=255)
    comment: str = Field(..., min_length=1, max_length=2000)
    author: str = Field('Anonymous', min_length=1, max_length=100)
    created_at: str = Field(..., description="Comment creation timestamp")

    @field_validator('repo_id')
    @classmethod
    def validate_repo_id(cls, v: str) -> str:
        """Validate repository ID format."""
        if not re.match(r'^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$', v):
            raise ValueError('Repository ID must be in owner/repo format')
        return v

    @field_validator('comment')
    @classmethod
    def validate_comment(cls, v: str) -> str:
        """Validate comment content."""
        v = v.strip()
        if not v:
            raise ValueError('Comment cannot be empty')
        return v

    @field_validator('author')
    @classmethod
    def validate_author(cls, v: str) -> str:
        """Validate author name."""
        v = v.strip()
        if not v:
            return 'Anonymous'
        return v

    @field_validator('created_at')
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate timestamp format using timezone utilities."""
        if not validate_datetime_string(v):
            raise ValueError('Timestamp must be in valid ISO format')

        # Normalize to UTC ISO format
        dt = parse_datetime(v)
        if dt is None:
            raise ValueError('Could not parse timestamp')

        return to_utc_iso(dt)


class RepositoryVersionModel(BaseModel):
    """Pydantic model for repository version validation."""
    
    repo_id: str = Field(..., min_length=1, max_length=255)
    version_number: str = Field(..., min_length=1, max_length=100)
    release_date: Optional[str] = Field(None, description="Release date")
    description: Optional[str] = Field(None, max_length=1000)
    created_at: str = Field(..., description="Version creation timestamp")

    @field_validator('repo_id')
    @classmethod
    def validate_repo_id(cls, v: str) -> str:
        """Validate repository ID format."""
        if not re.match(r'^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$', v):
            raise ValueError('Repository ID must be in owner/repo format')
        return v

    @field_validator('version_number')
    @classmethod
    def validate_version_number(cls, v: str) -> str:
        """Validate version number format."""
        v = v.strip()
        if not v:
            raise ValueError('Version number cannot be empty')
        
        # Allow various version formats: semantic versioning, dates, etc.
        if not re.match(r'^[a-zA-Z0-9._-]+$', v):
            raise ValueError('Version number contains invalid characters')
        
        return v

    @field_validator('release_date')
    @classmethod
    def validate_release_date(cls, v: Optional[str]) -> Optional[str]:
        """Validate release date format using timezone utilities."""
        if v is None:
            return v

        # Handle date-only format by adding time
        if re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            v = v + 'T00:00:00Z'

        if not validate_datetime_string(v):
            raise ValueError('Release date must be in valid ISO format')

        # Normalize to UTC ISO format
        dt = parse_datetime(v)
        if dt is None:
            raise ValueError('Could not parse release date')

        return to_utc_iso(dt)

    @field_validator('created_at')
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate timestamp format using timezone utilities."""
        if not validate_datetime_string(v):
            raise ValueError('Timestamp must be in valid ISO format')

        # Normalize to UTC ISO format
        dt = parse_datetime(v)
        if dt is None:
            raise ValueError('Could not parse timestamp')

        return to_utc_iso(dt)


def validate_repository_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate repository data using Pydantic model.
    
    Args:
        data: Raw repository data dictionary
        
    Returns:
        Validated and cleaned data dictionary
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        model = RepositoryModel(**data)
        return model.model_dump(exclude_none=True)
    except Exception as e:
        logger.error(f"Repository validation failed: {e}")
        raise ValidationError(f"Repository validation failed: {e}")


def validate_history_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate repository history data."""
    try:
        model = RepositoryHistoryModel(**data)
        return model.model_dump(exclude_none=True)
    except Exception as e:
        logger.error(f"History validation failed: {e}")
        raise ValidationError(f"History validation failed: {e}")


def validate_comment_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate repository comment data."""
    try:
        model = RepositoryCommentModel(**data)
        return model.model_dump(exclude_none=True)
    except Exception as e:
        logger.error(f"Comment validation failed: {e}")
        raise ValidationError(f"Comment validation failed: {e}")


def validate_version_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate repository version data."""
    try:
        model = RepositoryVersionModel(**data)
        return model.model_dump(exclude_none=True)
    except Exception as e:
        logger.error(f"Version validation failed: {e}")
        raise ValidationError(f"Version validation failed: {e}")


def sanitize_input(value: Any) -> Any:
    """
    Sanitize input data to prevent injection attacks.
    
    Args:
        value: Input value to sanitize
        
    Returns:
        Sanitized value
    """
    if isinstance(value, str):
        # Remove null bytes and control characters
        value = value.replace('\x00', '').strip()
        
        # Limit length to prevent DoS
        if len(value) > 10000:
            value = value[:10000]
            
    return value
