"""
Database utilities for user management.

This module provides functions for user CRUD operations, authentication,
email verification, and password reset functionality.
"""

import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from nuggit.util.db import get_connection
from nuggit.util.timezone import utc_now_iso
from nuggit.util.auth import hash_password, verify_password, generate_secure_token

logger = logging.getLogger(__name__)


class UserNotFoundError(Exception):
    """Exception raised when a user is not found."""
    pass


class UserAlreadyExistsError(Exception):
    """Exception raised when trying to create a user that already exists."""
    pass


class InvalidCredentialsError(Exception):
    """Exception raised when login credentials are invalid."""
    pass


def create_user(
    email: str,
    username: str,
    password: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None
) -> int:
    """
    Create a new user account.
    
    Args:
        email: User email address
        username: Username
        password: Plain text password
        first_name: First name (optional)
        last_name: Last name (optional)
        
    Returns:
        int: User ID
        
    Raises:
        UserAlreadyExistsError: If email or username already exists
    """
    password_hash = hash_password(password)
    now = utc_now_iso()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Check if email or username already exists
        cursor.execute(
            "SELECT id FROM users WHERE email = ? OR username = ?",
            (email.lower(), username.lower())
        )
        if cursor.fetchone():
            raise UserAlreadyExistsError("Email or username already exists")
        
        # Insert new user
        cursor.execute("""
            INSERT INTO users (
                email, username, password_hash, first_name, last_name,
                is_verified, is_active, is_admin, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            email.lower(), username.lower(), password_hash,
            first_name, last_name, False, True, False, now, now
        ))
        
        user_id = cursor.lastrowid
        logger.info(f"Created new user: {username} (ID: {user_id})")
        return user_id


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get user by ID.
    
    Args:
        user_id: User ID
        
    Returns:
        Optional[Dict[str, Any]]: User data or None if not found
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, username, first_name, last_name,
                   is_verified, is_active, is_admin, created_at, updated_at, last_login_at
            FROM users WHERE id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Get user by email address.
    
    Args:
        email: Email address
        
    Returns:
        Optional[Dict[str, Any]]: User data or None if not found
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, username, password_hash, first_name, last_name,
                   is_verified, is_active, is_admin, created_at, updated_at, last_login_at
            FROM users WHERE email = ?
        """, (email.lower(),))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """
    Get user by username.
    
    Args:
        username: Username
        
    Returns:
        Optional[Dict[str, Any]]: User data or None if not found
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, username, password_hash, first_name, last_name,
                   is_verified, is_active, is_admin, created_at, updated_at, last_login_at
            FROM users WHERE username = ?
        """, (username.lower(),))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def authenticate_user(email_or_username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate a user with email/username and password.
    
    Args:
        email_or_username: Email address or username
        password: Plain text password
        
    Returns:
        Optional[Dict[str, Any]]: User data if authenticated, None otherwise
    """
    # Try to find user by email first, then by username
    user = get_user_by_email(email_or_username)
    if not user:
        user = get_user_by_username(email_or_username)
    
    if not user:
        return None
    
    # Verify password
    if not verify_password(password, user['password_hash']):
        return None
    
    # Check if user is active
    if not user['is_active']:
        return None

    # Check if user email is verified
    if not user['is_verified']:
        return None

    # Update last login time
    update_last_login(user['id'])
    
    # Remove password hash from returned data
    user.pop('password_hash', None)
    return user


def update_last_login(user_id: int) -> None:
    """
    Update user's last login timestamp.
    
    Args:
        user_id: User ID
    """
    now = utc_now_iso()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET last_login_at = ? WHERE id = ?",
            (now, user_id)
        )


def verify_user_email(user_id: int) -> bool:
    """
    Mark user's email as verified.
    
    Args:
        user_id: User ID
        
    Returns:
        bool: True if user was found and updated, False otherwise
    """
    now = utc_now_iso()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET is_verified = ?, updated_at = ? WHERE id = ?",
            (True, now, user_id)
        )
        
        if cursor.rowcount > 0:
            logger.info(f"Verified email for user ID: {user_id}")
            return True
        return False


def update_user_password(user_id: int, new_password: str) -> bool:
    """
    Update user's password.
    
    Args:
        user_id: User ID
        new_password: New plain text password
        
    Returns:
        bool: True if password was updated, False otherwise
    """
    password_hash = hash_password(new_password)
    now = utc_now_iso()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
            (password_hash, now, user_id)
        )
        
        if cursor.rowcount > 0:
            logger.info(f"Updated password for user ID: {user_id}")
            return True
        return False


def create_email_verification_token(user_id: int) -> str:
    """
    Create an email verification token for a user.
    
    Args:
        user_id: User ID
        
    Returns:
        str: Verification token
    """
    token = generate_secure_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    now = utc_now_iso()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Delete any existing tokens for this user
        cursor.execute(
            "DELETE FROM email_verification_tokens WHERE user_id = ?",
            (user_id,)
        )
        
        # Insert new token
        cursor.execute("""
            INSERT INTO email_verification_tokens (token, user_id, expires_at, created_at)
            VALUES (?, ?, ?, ?)
        """, (token, user_id, expires_at.isoformat(), now))
        
        logger.info(f"Created email verification token for user ID: {user_id}")
        return token


def verify_email_verification_token(token: str) -> Optional[int]:
    """
    Verify an email verification token and return user ID.
    
    Args:
        token: Verification token
        
    Returns:
        Optional[int]: User ID if token is valid, None otherwise
    """
    now = datetime.now(timezone.utc)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id FROM email_verification_tokens
            WHERE token = ? AND expires_at > ? AND used_at IS NULL
        """, (token, now.isoformat()))
        
        row = cursor.fetchone()
        if row:
            user_id = row['user_id']
            
            # Mark token as used
            cursor.execute(
                "UPDATE email_verification_tokens SET used_at = ? WHERE token = ?",
                (utc_now_iso(), token)
            )
            
            logger.info(f"Verified email verification token for user ID: {user_id}")
            return user_id
        
        return None


def create_password_reset_token(user_id: int) -> str:
    """
    Create a password reset token for a user.
    
    Args:
        user_id: User ID
        
    Returns:
        str: Reset token
    """
    token = generate_secure_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    now = utc_now_iso()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Delete any existing tokens for this user
        cursor.execute(
            "DELETE FROM password_reset_tokens WHERE user_id = ?",
            (user_id,)
        )
        
        # Insert new token
        cursor.execute("""
            INSERT INTO password_reset_tokens (token, user_id, expires_at, created_at)
            VALUES (?, ?, ?, ?)
        """, (token, user_id, expires_at.isoformat(), now))
        
        logger.info(f"Created password reset token for user ID: {user_id}")
        return token


def verify_password_reset_token(token: str) -> Optional[int]:
    """
    Verify a password reset token and return user ID.
    
    Args:
        token: Reset token
        
    Returns:
        Optional[int]: User ID if token is valid, None otherwise
    """
    now = datetime.now(timezone.utc)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id FROM password_reset_tokens
            WHERE token = ? AND expires_at > ? AND used_at IS NULL
        """, (token, now.isoformat()))
        
        row = cursor.fetchone()
        if row:
            user_id = row['user_id']
            
            # Mark token as used
            cursor.execute(
                "UPDATE password_reset_tokens SET used_at = ? WHERE token = ?",
                (utc_now_iso(), token)
            )
            
            logger.info(f"Verified password reset token for user ID: {user_id}")
            return user_id
        
        return None


def get_users_list(
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    is_active: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Get a paginated list of users (admin only).
    
    Args:
        page: Page number (1-based)
        per_page: Number of users per page
        search: Search term for email/username
        is_active: Filter by active status
        
    Returns:
        Dict[str, Any]: Users list with pagination info
    """
    offset = (page - 1) * per_page
    
    # Build WHERE clause
    where_conditions = []
    params = []
    
    if search:
        where_conditions.append("(email LIKE ? OR username LIKE ?)")
        search_term = f"%{search}%"
        params.extend([search_term, search_term])
    
    if is_active is not None:
        where_conditions.append("is_active = ?")
        params.append(is_active)
    
    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM users {where_clause}"
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]
        
        # Get users
        users_query = f"""
            SELECT id, email, username, first_name, last_name,
                   is_verified, is_active, is_admin, created_at, updated_at, last_login_at
            FROM users {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(users_query, params + [per_page, offset])
        
        users = [dict(row) for row in cursor.fetchall()]
        
        return {
            'users': users,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }
