"""
Authentication utilities for JWT tokens, password hashing, and security.

This module provides functions for creating and validating JWT tokens,
hashing and verifying passwords, and generating secure tokens.
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
import bcrypt
from jwt.exceptions import InvalidTokenError

# JWT Configuration
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', secrets.token_urlsafe(32))
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', '7'))


class AuthError(Exception):
    """Base exception for authentication errors."""
    pass


class TokenExpiredError(AuthError):
    """Exception raised when a token has expired."""
    pass


class InvalidTokenError(AuthError):
    """Exception raised when a token is invalid."""
    pass


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        bool: True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Token length in bytes
        
    Returns:
        str: URL-safe token
    """
    return secrets.token_urlsafe(length)


def create_access_token(
    user_id: int,
    email: str,
    username: str,
    is_admin: bool = False,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: User ID
        email: User email
        username: Username
        is_admin: Whether user is admin
        expires_delta: Custom expiration time
        
    Returns:
        str: JWT token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        'sub': str(user_id),
        'email': email,
        'username': username,
        'is_admin': is_admin,
        'exp': expire,
        'iat': datetime.now(timezone.utc),
        'type': 'access'
    }
    
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(
    user_id: int,
    email: str,
    username: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        user_id: User ID
        email: User email
        username: Username
        expires_delta: Custom expiration time
        
    Returns:
        str: JWT refresh token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    payload = {
        'sub': str(user_id),
        'email': email,
        'username': username,
        'exp': expire,
        'iat': datetime.now(timezone.utc),
        'type': 'refresh'
    }
    
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_token(token: str, token_type: str = 'access') -> Dict[str, Any]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token
        token_type: Expected token type ('access' or 'refresh')
        
    Returns:
        Dict[str, Any]: Token payload
        
    Raises:
        TokenExpiredError: If token has expired
        InvalidTokenError: If token is invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # Check token type
        if payload.get('type') != token_type:
            raise InvalidTokenError(f"Invalid token type. Expected {token_type}")
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise InvalidTokenError(f"Invalid token: {str(e)}")


def get_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Extract user information from a valid token.
    
    Args:
        token: JWT token
        
    Returns:
        Optional[Dict[str, Any]]: User information or None if invalid
    """
    try:
        payload = verify_token(token, 'access')
        return {
            'id': int(payload['sub']),
            'email': payload['email'],
            'username': payload['username'],
            'is_admin': payload.get('is_admin', False)
        }
    except (TokenExpiredError, InvalidTokenError):
        return None


def create_email_verification_token(user_id: int, email: str) -> str:
    """
    Create a token for email verification.
    
    Args:
        user_id: User ID
        email: User email
        
    Returns:
        str: Verification token
    """
    # Create a hash-based token for email verification
    timestamp = str(int(datetime.now(timezone.utc).timestamp()))
    data = f"{user_id}:{email}:{timestamp}:{JWT_SECRET_KEY}"
    token_hash = hashlib.sha256(data.encode()).hexdigest()
    return f"{user_id}:{timestamp}:{token_hash}"


def verify_email_verification_token(token: str, max_age_hours: int = 24) -> Optional[int]:
    """
    Verify an email verification token.
    
    Args:
        token: Verification token
        max_age_hours: Maximum age in hours
        
    Returns:
        Optional[int]: User ID if valid, None otherwise
    """
    try:
        parts = token.split(':')
        if len(parts) != 3:
            return None
        
        user_id, timestamp, token_hash = parts
        user_id = int(user_id)
        timestamp = int(timestamp)
        
        # Check if token is expired
        token_age = datetime.now(timezone.utc).timestamp() - timestamp
        if token_age > max_age_hours * 3600:
            return None
        
        # Verify token hash
        data = f"{user_id}:email:{timestamp}:{JWT_SECRET_KEY}"
        expected_hash = hashlib.sha256(data.encode()).hexdigest()
        
        if secrets.compare_digest(token_hash, expected_hash):
            return user_id
        
        return None
        
    except (ValueError, IndexError):
        return None


def create_password_reset_token(user_id: int, email: str) -> str:
    """
    Create a token for password reset.
    
    Args:
        user_id: User ID
        email: User email
        
    Returns:
        str: Reset token
    """
    # Create a hash-based token for password reset
    timestamp = str(int(datetime.now(timezone.utc).timestamp()))
    data = f"{user_id}:{email}:{timestamp}:{JWT_SECRET_KEY}"
    token_hash = hashlib.sha256(data.encode()).hexdigest()
    return f"{user_id}:{timestamp}:{token_hash}"


def verify_password_reset_token(token: str, max_age_hours: int = 1) -> Optional[int]:
    """
    Verify a password reset token.
    
    Args:
        token: Reset token
        max_age_hours: Maximum age in hours
        
    Returns:
        Optional[int]: User ID if valid, None otherwise
    """
    try:
        parts = token.split(':')
        if len(parts) != 3:
            return None
        
        user_id, timestamp, token_hash = parts
        user_id = int(user_id)
        timestamp = int(timestamp)
        
        # Check if token is expired
        token_age = datetime.now(timezone.utc).timestamp() - timestamp
        if token_age > max_age_hours * 3600:
            return None
        
        # Verify token hash
        data = f"{user_id}:reset:{timestamp}:{JWT_SECRET_KEY}"
        expected_hash = hashlib.sha256(data.encode()).hexdigest()
        
        if secrets.compare_digest(token_hash, expected_hash):
            return user_id
        
        return None
        
    except (ValueError, IndexError):
        return None
