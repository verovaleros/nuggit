"""
Timezone utilities for consistent datetime handling across the Nuggit application.

This module provides standardized timezone-aware datetime operations to ensure
consistent handling of timestamps throughout the application.
"""

import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Union
import logging

logger = logging.getLogger(__name__)

# Standard timezone for the application (UTC)
UTC = timezone.utc

# Common timezone patterns for parsing
TIMEZONE_PATTERNS = [
    # ISO 8601 formats
    r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})Z',  # 2023-01-01T12:00:00Z
    r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\+00:00',  # 2023-01-01T12:00:00+00:00
    r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.(\d+)Z',  # 2023-01-01T12:00:00.123Z
    r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.(\d+)\+00:00',  # 2023-01-01T12:00:00.123+00:00
    # GitHub API format
    r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.(\d+)\+(\d{2}):(\d{2})',  # 2023-01-01T12:00:00.123+05:30
    # Date only
    r'(\d{4}-\d{2}-\d{2})',  # 2023-01-01
]


def now_utc() -> datetime:
    """
    Get current UTC datetime.
    
    Returns:
        datetime: Current UTC datetime with timezone info
    """
    return datetime.now(UTC)


def to_utc_iso(dt: Optional[Union[datetime, str]]) -> Optional[str]:
    """
    Convert datetime to UTC ISO format string.
    
    Args:
        dt: Datetime object or ISO string to convert
        
    Returns:
        Optional[str]: UTC ISO format string with 'Z' suffix, or None if input is None
        
    Examples:
        >>> to_utc_iso(datetime(2023, 1, 1, 12, 0, 0))
        '2023-01-01T12:00:00Z'
    """
    if dt is None:
        return None
    
    if isinstance(dt, str):
        dt = parse_datetime(dt)
        if dt is None:
            return None
    
    # Convert to UTC if not already
    if dt.tzinfo is None:
        # Assume naive datetime is UTC
        dt = dt.replace(tzinfo=UTC)
    elif dt.tzinfo != UTC:
        dt = dt.astimezone(UTC)
    
    # Return ISO format with Z suffix
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """
    Parse datetime string into timezone-aware datetime object.
    
    Handles various datetime formats commonly used in the application:
    - ISO 8601 with Z suffix
    - ISO 8601 with timezone offset
    - GitHub API format
    - Date-only format
    
    Args:
        dt_str: Datetime string to parse
        
    Returns:
        Optional[datetime]: Timezone-aware datetime object in UTC, or None if parsing fails
        
    Examples:
        >>> parse_datetime('2023-01-01T12:00:00Z')
        datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    """
    if not dt_str:
        return None
    
    dt_str = dt_str.strip()
    
    try:
        # Try standard ISO format first
        if dt_str.endswith('Z'):
            # Remove Z and parse as UTC
            dt = datetime.fromisoformat(dt_str[:-1])
            return dt.replace(tzinfo=UTC)
        
        # Try ISO format with timezone
        if '+' in dt_str or dt_str.endswith('+00:00'):
            # Handle timezone offset
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            return dt.astimezone(UTC)
        
        # Try date-only format
        if re.match(r'^\d{4}-\d{2}-\d{2}$', dt_str):
            dt = datetime.fromisoformat(dt_str + 'T00:00:00')
            return dt.replace(tzinfo=UTC)
        
        # Try parsing as naive datetime and assume UTC
        dt = datetime.fromisoformat(dt_str)
        return dt.replace(tzinfo=UTC)
        
    except ValueError as e:
        logger.warning(f"Failed to parse datetime string '{dt_str}': {e}")
        return None


def format_datetime(
    dt: Optional[Union[datetime, str]],
    format_type: str = 'iso',
    include_timezone: bool = True
) -> Optional[str]:
    """
    Format datetime for display or storage.
    
    Args:
        dt: Datetime object or string to format
        format_type: Format type ('iso', 'human', 'date', 'relative')
        include_timezone: Whether to include timezone information
        
    Returns:
        Optional[str]: Formatted datetime string, or None if input is None
        
    Examples:
        >>> dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        >>> format_datetime(dt, 'human')
        'Jan 1, 2023 12:00 PM UTC'
        >>> format_datetime(dt, 'relative')
        '5 days ago'
    """
    if dt is None:
        return None
    
    if isinstance(dt, str):
        dt = parse_datetime(dt)
        if dt is None:
            return None
    
    # Ensure timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    
    if format_type == 'iso':
        return to_utc_iso(dt)
    
    elif format_type == 'human':
        if include_timezone:
            return dt.strftime('%b %d, %Y %I:%M %p %Z')
        else:
            return dt.strftime('%b %d, %Y %I:%M %p')
    
    elif format_type == 'date':
        return dt.strftime('%Y-%m-%d')
    
    elif format_type == 'relative':
        return format_relative_time(dt)
    
    else:
        raise ValueError(f"Unknown format_type: {format_type}")


def format_relative_time(dt: Optional[Union[datetime, str]]) -> Optional[str]:
    """
    Format datetime as relative time (e.g., "2 days ago", "in 3 hours").
    
    Args:
        dt: Datetime object or string to format
        
    Returns:
        Optional[str]: Relative time string, or None if input is None
        
    Examples:
        >>> dt = datetime.now(timezone.utc) - timedelta(days=2)
        >>> format_relative_time(dt)
        '2 days ago'
    """
    if dt is None:
        return None
    
    if isinstance(dt, str):
        dt = parse_datetime(dt)
        if dt is None:
            return None
    
    # Ensure timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    
    now = now_utc()
    diff = now - dt
    
    # Handle future dates
    if diff.total_seconds() < 0:
        diff = -diff
        suffix = "from now"
    else:
        suffix = "ago"
    
    seconds = int(diff.total_seconds())
    
    if seconds < 60:
        return f"{seconds} second{'s' if seconds != 1 else ''} {suffix}"
    
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} {suffix}"
    
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} {suffix}"
    
    days = hours // 24
    if days < 30:
        return f"{days} day{'s' if days != 1 else ''} {suffix}"
    
    months = days // 30
    if months < 12:
        return f"{months} month{'s' if months != 1 else ''} {suffix}"
    
    years = days // 365
    return f"{years} year{'s' if years != 1 else ''} {suffix}"


def validate_datetime_string(dt_str: Optional[str]) -> bool:
    """
    Validate if a string is a valid datetime format.
    
    Args:
        dt_str: Datetime string to validate
        
    Returns:
        bool: True if valid datetime string, False otherwise
    """
    if not dt_str:
        return False
    
    return parse_datetime(dt_str) is not None


def normalize_github_datetime(github_dt: Optional[str]) -> Optional[str]:
    """
    Normalize GitHub API datetime to standard UTC ISO format.
    
    GitHub API returns datetimes in various formats. This function
    normalizes them to a consistent UTC ISO format.
    
    Args:
        github_dt: GitHub datetime string
        
    Returns:
        Optional[str]: Normalized UTC ISO datetime string
        
    Examples:
        >>> normalize_github_datetime('2023-01-01T12:00:00.123+05:30')
        '2023-01-01T06:30:00Z'
    """
    if not github_dt:
        return None
    
    # Parse and convert to UTC ISO
    dt = parse_datetime(github_dt)
    return to_utc_iso(dt) if dt else None


def get_timezone_info() -> dict:
    """
    Get timezone information for the application.
    
    Returns:
        dict: Timezone information including current UTC time and offset
    """
    now = now_utc()
    
    return {
        'timezone': 'UTC',
        'current_utc_time': to_utc_iso(now),
        'current_timestamp': int(now.timestamp()),
        'iso_format': 'YYYY-MM-DDTHH:MM:SSZ',
        'description': 'All timestamps are stored and processed in UTC'
    }


def migrate_datetime_field(value: Optional[str]) -> Optional[str]:
    """
    Migrate datetime field to standardized UTC format.
    
    This function is useful for migrating existing datetime fields
    to the standardized format.
    
    Args:
        value: Existing datetime value (may be in various formats)
        
    Returns:
        Optional[str]: Standardized UTC ISO datetime string
    """
    if not value:
        return None
    
    # Try to parse and normalize
    dt = parse_datetime(value)
    if dt:
        return to_utc_iso(dt)
    
    # If parsing fails, log warning and return original value
    logger.warning(f"Could not migrate datetime field: {value}")
    return value


# Convenience functions for common operations
def utc_now_iso() -> str:
    """Get current UTC time as ISO string."""
    return to_utc_iso(now_utc())


def days_ago(days: int) -> str:
    """Get UTC ISO string for N days ago."""
    dt = now_utc() - timedelta(days=days)
    return to_utc_iso(dt)


def hours_ago(hours: int) -> str:
    """Get UTC ISO string for N hours ago."""
    dt = now_utc() - timedelta(hours=hours)
    return to_utc_iso(dt)
