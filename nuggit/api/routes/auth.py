"""
Authentication routes for the Nuggit API.

This module provides endpoints for user registration, login, logout,
email verification, and password reset functionality.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from nuggit.api.models.auth import (
    UserRegistrationRequest, UserLoginRequest, UserLoginResponse,
    EmailVerificationRequest, PasswordResetRequest, PasswordResetConfirmRequest,
    UserProfile, AuthResponse, TokenRefreshRequest, UserListResponse
)
from nuggit.util.user_db import (
    create_user, authenticate_user, get_user_by_id, get_user_by_email,
    verify_user_email, update_user_password, create_email_verification_token,
    verify_email_verification_token, create_password_reset_token,
    verify_password_reset_token, UserAlreadyExistsError, get_users_list
)
from nuggit.util.auth import (
    create_access_token, create_refresh_token, verify_token,
    get_user_from_token, TokenExpiredError, InvalidTokenError
)
from nuggit.util.email_service import get_email_service
from nuggit.api.utils.error_handling import (
    validation_error, authentication_error, not_found_error,
    internal_server_error, create_error_response
)

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Optional[dict]: User information or None if not authenticated
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        user_info = get_user_from_token(token)
        if user_info:
            # Get full user data from database
            user = get_user_by_id(user_info['id'])
            if user and user['is_active']:
                return user
        return None
    except Exception:
        return None


async def require_auth(current_user: Optional[dict] = Depends(get_current_user)) -> dict:
    """
    Require authentication for protected endpoints.
    
    Args:
        current_user: Current user from dependency
        
    Returns:
        dict: User information
        
    Raises:
        HTTPException: If user is not authenticated
    """
    if not current_user:
        raise authentication_error("Authentication required")
    return current_user


async def require_admin(current_user: dict = Depends(require_auth)) -> dict:
    """
    Require admin privileges for admin-only endpoints.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        dict: User information
        
    Raises:
        HTTPException: If user is not an admin
    """
    if not current_user.get('is_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


@router.post("/register", response_model=AuthResponse)
async def register_user(user_data: UserRegistrationRequest):
    """
    Register a new user account.
    
    Creates a new user account and sends an email verification link.
    The user must verify their email before they can log in.
    """
    try:
        # Create user account
        user_id = create_user(
            email=user_data.email,
            username=user_data.username,
            password=user_data.password,
            first_name=user_data.first_name,
            last_name=user_data.last_name
        )
        
        # Create email verification token
        verification_token = create_email_verification_token(user_id)
        
        # Send verification email
        email_service = get_email_service()
        email_sent = await email_service.send_verification_email(
            to_email=user_data.email,
            username=user_data.username,
            verification_token=verification_token
        )
        
        if not email_sent:
            logger.warning(f"Failed to send verification email to {user_data.email}")
        
        logger.info(f"User registered successfully: {user_data.username}")
        return AuthResponse(
            success=True,
            message="Registration successful. Please check your email to verify your account."
        )
        
    except UserAlreadyExistsError:
        raise validation_error("Email or username already exists")
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise internal_server_error("Registration failed")


@router.post("/login", response_model=UserLoginResponse)
async def login_user(login_data: UserLoginRequest):
    """
    Authenticate user and return access tokens.
    
    Validates user credentials and returns JWT access and refresh tokens.
    """
    try:
        # First, check if user exists and get their verification status
        user_by_email = get_user_by_email(login_data.email_or_username)
        if not user_by_email:
            from nuggit.util.user_db import get_user_by_username
            user_by_email = get_user_by_username(login_data.email_or_username)

        # If user exists but is not verified, provide specific error
        if user_by_email and not user_by_email['is_verified']:
            # Still need to verify password to avoid user enumeration
            from nuggit.util.auth import verify_password
            if verify_password(login_data.password, user_by_email['password_hash']):
                raise authentication_error("Please verify your email address before logging in")
            else:
                raise authentication_error("Invalid email/username or password")

        # Authenticate user (will return None for unverified users)
        user = authenticate_user(login_data.email_or_username, login_data.password)
        if not user:
            raise authentication_error("Invalid email/username or password")
        
        # Create tokens with longer expiration
        from nuggit.util.auth import ACCESS_TOKEN_EXPIRE_MINUTES
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        if login_data.remember_me:
            # If remember me is checked, use even longer expiration (30 days)
            access_token_expires = timedelta(days=30)
        
        access_token = create_access_token(
            user_id=user['id'],
            email=user['email'],
            username=user['username'],
            is_admin=user['is_admin'],
            expires_delta=access_token_expires
        )
        
        refresh_token = create_refresh_token(
            user_id=user['id'],
            email=user['email'],
            username=user['username']
        )
        
        # Create user profile
        user_profile = UserProfile(
            id=user['id'],
            email=user['email'],
            username=user['username'],
            first_name=user['first_name'],
            last_name=user['last_name'],
            is_verified=user['is_verified'],
            is_active=user['is_active'],
            is_admin=user['is_admin'],
            created_at=user['created_at'],
            updated_at=user['updated_at'],
            last_login_at=user['last_login_at']
        )
        
        logger.info(f"User logged in successfully: {user['username']}")
        return UserLoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds()),
            user=user_profile
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise internal_server_error("Login failed")


@router.post("/refresh", response_model=dict)
async def refresh_token(refresh_data: TokenRefreshRequest):
    """
    Refresh access token using refresh token.
    
    Validates refresh token and returns a new access token.
    """
    try:
        # Verify refresh token
        payload = verify_token(refresh_data.refresh_token, 'refresh')
        user_id = int(payload['sub'])
        
        # Get user data
        user = get_user_by_id(user_id)
        if not user or not user['is_active']:
            raise authentication_error("Invalid refresh token")
        
        # Create new access token with proper expiration
        from nuggit.util.auth import ACCESS_TOKEN_EXPIRE_MINUTES
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        access_token = create_access_token(
            user_id=user['id'],
            email=user['email'],
            username=user['username'],
            is_admin=user['is_admin'],
            expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": int(access_token_expires.total_seconds())
        }
        
    except (TokenExpiredError, InvalidTokenError):
        raise authentication_error("Invalid or expired refresh token")
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise internal_server_error("Token refresh failed")


@router.post("/verify-email", response_model=AuthResponse)
async def verify_email(verification_data: EmailVerificationRequest):
    """
    Verify user email address using verification token.
    
    Validates the email verification token and marks the user's email as verified.
    """
    try:
        # Verify token
        user_id = verify_email_verification_token(verification_data.token)
        if not user_id:
            raise validation_error("Invalid or expired verification token")
        
        # Mark email as verified
        if verify_user_email(user_id):
            logger.info(f"Email verified for user ID: {user_id}")
            return AuthResponse(
                success=True,
                message="Email verified successfully. You can now log in."
            )
        else:
            raise not_found_error("User not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification failed: {e}")
        raise internal_server_error("Email verification failed")


@router.post("/forgot-password", response_model=AuthResponse)
async def forgot_password(reset_data: PasswordResetRequest):
    """
    Request password reset for user account.
    
    Sends a password reset email to the user if the email exists.
    """
    try:
        # Find user by email
        user = get_user_by_email(reset_data.email)
        if not user:
            # Don't reveal if email exists or not for security
            return AuthResponse(
                success=True,
                message="If the email exists, a password reset link has been sent."
            )
        
        # Create password reset token
        reset_token = create_password_reset_token(user['id'])
        
        # Send password reset email
        email_service = get_email_service()
        email_sent = await email_service.send_password_reset_email(
            to_email=user['email'],
            username=user['username'],
            reset_token=reset_token
        )
        
        if not email_sent:
            logger.warning(f"Failed to send password reset email to {user['email']}")
        
        logger.info(f"Password reset requested for user: {user['username']}")
        return AuthResponse(
            success=True,
            message="If the email exists, a password reset link has been sent."
        )
        
    except Exception as e:
        logger.error(f"Password reset request failed: {e}")
        raise internal_server_error("Password reset request failed")


@router.post("/reset-password", response_model=AuthResponse)
async def reset_password(reset_data: PasswordResetConfirmRequest):
    """
    Reset user password using reset token.
    
    Validates the reset token and updates the user's password.
    """
    try:
        # Verify reset token
        user_id = verify_password_reset_token(reset_data.token)
        if not user_id:
            raise validation_error("Invalid or expired reset token")
        
        # Update password
        if update_user_password(user_id, reset_data.new_password):
            logger.info(f"Password reset for user ID: {user_id}")
            return AuthResponse(
                success=True,
                message="Password reset successfully. You can now log in with your new password."
            )
        else:
            raise not_found_error("User not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset failed: {e}")
        raise internal_server_error("Password reset failed")


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(current_user: dict = Depends(require_auth)):
    """
    Get current user's profile information.

    Returns the authenticated user's profile data.
    """
    return UserProfile(
        id=current_user['id'],
        email=current_user['email'],
        username=current_user['username'],
        first_name=current_user['first_name'],
        last_name=current_user['last_name'],
        is_verified=current_user['is_verified'],
        is_active=current_user['is_active'],
        is_admin=current_user['is_admin'],
        created_at=current_user['created_at'],
        updated_at=current_user['updated_at'],
        last_login_at=current_user['last_login_at']
    )


@router.patch("/me", response_model=UserProfile)
async def update_current_user_profile(
    update_data: dict,
    current_user: dict = Depends(require_auth)
):
    """
    Update current user's profile information.

    Allows users to update their own profile data like first_name, last_name, etc.
    """
    try:
        from nuggit.util.db import get_connection

        # Validate update data - only allow certain fields to be updated
        allowed_fields = ['first_name', 'last_name']
        update_fields = {k: v for k, v in update_data.items() if k in allowed_fields}

        if not update_fields:
            raise validation_error("No valid fields to update")

        # Update user in database
        with get_connection() as conn:
            set_clause = ", ".join([f"{field} = ?" for field in update_fields.keys()])
            values = list(update_fields.values()) + [current_user['id']]

            conn.execute(f"""
                UPDATE users
                SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, values)
            conn.commit()

        # Get updated user data
        updated_user = get_user_by_id(current_user['id'])

        logger.info(f"User {current_user['username']} updated profile: {update_fields}")

        return UserProfile(
            id=updated_user['id'],
            email=updated_user['email'],
            username=updated_user['username'],
            first_name=updated_user['first_name'],
            last_name=updated_user['last_name'],
            is_verified=updated_user['is_verified'],
            is_active=updated_user['is_active'],
            is_admin=updated_user['is_admin'],
            created_at=updated_user['created_at'],
            updated_at=updated_user['updated_at'],
            last_login_at=updated_user['last_login_at']
        )

    except Exception as e:
        logger.error(f"Error updating profile for user {current_user['id']}: {e}")
        raise internal_server_error("Failed to update profile")


@router.post("/change-password", response_model=AuthResponse)
async def change_password(
    password_data: dict,
    current_user: dict = Depends(require_auth)
):
    """
    Change current user's password.

    Requires current password for verification and sets new password.
    """
    try:
        current_password = password_data.get('current_password')
        new_password = password_data.get('new_password')

        if not current_password or not new_password:
            raise validation_error("Current password and new password are required")

        # Verify current password
        user = authenticate_user(current_user['email'], current_password)
        if not user:
            raise authentication_error("Current password is incorrect")

        # Update password
        if update_user_password(current_user['id'], new_password):
            logger.info(f"Password changed for user: {current_user['username']}")
            return AuthResponse(
                success=True,
                message="Password changed successfully"
            )
        else:
            raise internal_server_error("Failed to update password")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change failed for user {current_user['id']}: {e}")
        raise internal_server_error("Password change failed")


# Admin routes
@router.get("/admin/users", response_model=UserListResponse)
async def get_users_list_admin(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Users per page"),
    search: Optional[str] = Query(None, description="Search by email or username"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: dict = Depends(require_admin)
):
    """
    Get paginated list of users (admin only).

    Returns a paginated list of all users with search and filtering capabilities.
    """
    try:
        result = get_users_list(
            page=page,
            per_page=per_page,
            search=search,
            is_active=is_active
        )

        users = [
            UserProfile(
                id=user['id'],
                email=user['email'],
                username=user['username'],
                first_name=user['first_name'],
                last_name=user['last_name'],
                is_verified=user['is_verified'],
                is_active=user['is_active'],
                is_admin=user['is_admin'],
                created_at=user['created_at'],
                updated_at=user['updated_at'],
                last_login_at=user['last_login_at']
            )
            for user in result['users']
        ]

        return UserListResponse(
            users=users,
            total=result['total'],
            page=result['page'],
            per_page=result['per_page']
        )

    except Exception as e:
        logger.error(f"Failed to get users list: {e}")
        raise internal_server_error("Failed to retrieve users list")


@router.get("/admin/users/{user_id}", response_model=UserProfile)
async def get_user_admin(
    user_id: int,
    current_user: dict = Depends(require_admin)
):
    """
    Get user details by ID (admin only).

    Returns detailed information about a specific user.
    """
    try:
        user = get_user_by_id(user_id)
        if not user:
            raise not_found_error(f"User with ID {user_id} not found")

        return UserProfile(
            id=user['id'],
            email=user['email'],
            username=user['username'],
            first_name=user['first_name'],
            last_name=user['last_name'],
            is_verified=user['is_verified'],
            is_active=user['is_active'],
            is_admin=user['is_admin'],
            created_at=user['created_at'],
            updated_at=user['updated_at'],
            last_login_at=user['last_login_at']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user {user_id}: {e}")
        raise internal_server_error("Failed to retrieve user details")


@router.get("/admin/stats", response_model=dict)
async def get_admin_stats(current_user: dict = Depends(require_admin)):
    """
    Get admin dashboard statistics.

    Returns system-wide statistics for the admin dashboard.
    """
    try:
        from nuggit.util.db import get_connection

        with get_connection() as conn:
            # Get user statistics
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total_users,
                    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_users,
                    SUM(CASE WHEN is_verified = 1 THEN 1 ELSE 0 END) as verified_users,
                    SUM(CASE WHEN is_admin = 1 THEN 1 ELSE 0 END) as admin_users
                FROM users
            """)
            user_stats = cursor.fetchone()

            # Get repository statistics
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total_repositories,
                    COUNT(DISTINCT user_id) as users_with_repos,
                    AVG(stars) as avg_stars,
                    SUM(stars) as total_stars
                FROM repositories
            """)
            repo_stats = cursor.fetchone()

            # Get recent activity (last 30 days)
            cursor = conn.execute("""
                SELECT COUNT(*) as recent_users
                FROM users
                WHERE created_at >= datetime('now', '-30 days')
            """)
            recent_activity = cursor.fetchone()

            return {
                "users": {
                    "total": user_stats[0] if user_stats else 0,
                    "active": user_stats[1] if user_stats else 0,
                    "verified": user_stats[2] if user_stats else 0,
                    "admin": user_stats[3] if user_stats else 0,
                    "recent": recent_activity[0] if recent_activity else 0
                },
                "repositories": {
                    "total": repo_stats[0] if repo_stats else 0,
                    "users_with_repos": repo_stats[1] if repo_stats else 0,
                    "avg_stars": round(repo_stats[2] or 0, 1),
                    "total_stars": repo_stats[3] if repo_stats else 0
                },
                "timestamp": datetime.utcnow().isoformat()
            }

    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        raise internal_server_error("Failed to retrieve admin statistics")


@router.patch("/admin/users/{user_id}", response_model=dict)
async def update_user_admin(
    user_id: int,
    update_data: dict,
    current_user: dict = Depends(require_admin)
):
    """
    Update user information (admin only).

    Allows admin to update user status, roles, and other properties.
    """
    try:
        from nuggit.util.db import get_connection

        # Validate update data
        allowed_fields = ['is_active', 'is_admin', 'is_verified']
        update_fields = {k: v for k, v in update_data.items() if k in allowed_fields}

        if not update_fields:
            raise validation_error("No valid fields to update")

        # Check if user exists
        user = get_user_by_id(user_id)
        if not user:
            raise not_found_error(f"User with ID {user_id} not found")

        # Prevent admin from deactivating themselves
        if user_id == current_user['id'] and 'is_active' in update_fields and not update_fields['is_active']:
            raise validation_error("Cannot deactivate your own account")

        # Update user in database
        with get_connection() as conn:
            set_clause = ", ".join([f"{field} = ?" for field in update_fields.keys()])
            values = list(update_fields.values()) + [user_id]

            conn.execute(f"""
                UPDATE users
                SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, values)
            conn.commit()

        logger.info(f"Admin {current_user['username']} updated user {user_id}: {update_fields}")

        return {
            "success": True,
            "message": f"User {user_id} updated successfully",
            "updated_fields": update_fields
        }

    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        raise internal_server_error("Failed to update user")
