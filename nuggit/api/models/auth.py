"""
Authentication models for the Nuggit API.

This module contains Pydantic models for user authentication, registration,
password management, and user profile operations.
"""

import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from enum import Enum


class UserRole(str, Enum):
    """User role enumeration."""
    USER = "user"
    ADMIN = "admin"


class UserRegistrationRequest(BaseModel):
    """Model for user registration request."""
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, max_length=128, description="Password")
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v.lower()

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_names(cls, v: Optional[str]) -> Optional[str]:
        """Validate name fields."""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
            if not re.match(r'^[a-zA-Z\s\'-]+$', v):
                raise ValueError('Name can only contain letters, spaces, apostrophes, and hyphens')
        return v


class UserLoginRequest(BaseModel):
    """Model for user login request."""
    email_or_username: str = Field(..., description="Email address or username")
    password: str = Field(..., description="Password")
    remember_me: bool = Field(False, description="Remember login for extended period")


class UserLoginResponse(BaseModel):
    """Model for user login response."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: "UserProfile" = Field(..., description="User profile information")


class TokenRefreshRequest(BaseModel):
    """Model for token refresh request."""
    refresh_token: str = Field(..., description="Refresh token")


class EmailVerificationRequest(BaseModel):
    """Model for email verification request."""
    token: str = Field(..., description="Email verification token")


class PasswordResetRequest(BaseModel):
    """Model for password reset request."""
    email: EmailStr = Field(..., description="Email address")


class PasswordResetConfirmRequest(BaseModel):
    """Model for password reset confirmation."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v


class PasswordChangeRequest(BaseModel):
    """Model for password change request (authenticated user)."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserProfile(BaseModel):
    """Model for user profile information."""
    id: int = Field(..., description="User ID")
    email: str = Field(..., description="Email address")
    username: str = Field(..., description="Username")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    is_verified: bool = Field(..., description="Email verification status")
    is_active: bool = Field(..., description="Account active status")
    is_admin: bool = Field(..., description="Admin status")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")

    @property
    def full_name(self) -> Optional[str]:
        """Get full name if both first and last names are available."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name

    @property
    def display_name(self) -> str:
        """Get display name (full name or username)."""
        return self.full_name or self.username


class UserProfileUpdateRequest(BaseModel):
    """Model for user profile update request."""
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_names(cls, v: Optional[str]) -> Optional[str]:
        """Validate name fields."""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
            if not re.match(r'^[a-zA-Z\s\'-]+$', v):
                raise ValueError('Name can only contain letters, spaces, apostrophes, and hyphens')
        return v


class UserListResponse(BaseModel):
    """Model for user list response (admin only)."""
    users: list[UserProfile] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of users per page")


class AuthResponse(BaseModel):
    """Generic authentication response."""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")


class TokenPayload(BaseModel):
    """JWT token payload model."""
    sub: str = Field(..., description="Subject (user ID)")
    email: str = Field(..., description="User email")
    username: str = Field(..., description="Username")
    is_admin: bool = Field(False, description="Admin status")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    type: str = Field("access", description="Token type (access or refresh)")


# Update forward references
UserLoginResponse.model_rebuild()
