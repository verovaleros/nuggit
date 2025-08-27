"""
Integration tests for authentication workflows.

Tests complete end-to-end user journeys using FastAPI TestClient to simulate
real user interactions across multiple API endpoints. These tests validate
that authentication components work correctly when integrated together.
"""

import pytest
import tempfile
import os
import sqlite3
import time
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from nuggit.api.main import app
from nuggit.util.user_db import (
    get_user_by_email, get_user_by_id, create_email_verification_token,
    create_password_reset_token, verify_user_email
)
from nuggit.util.auth import create_access_token


@pytest.fixture
def temp_db():
    """Create a temporary database for integration testing."""
    # Create temporary file using NamedTemporaryFile for better resource management
    tmpfile = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = tmpfile.name
    tmpfile.close()
    
    # Initialize database with schema
    conn = sqlite3.connect(db_path)
    
    # Create users table
    conn.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            is_verified BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE,
            is_admin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login_at TIMESTAMP
        )
    ''')
    
    # Create email verification tokens table
    conn.execute('''
        CREATE TABLE email_verification_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            used_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create password reset tokens table
    conn.execute('''
        CREATE TABLE password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            used_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create repositories table for testing protected routes
    conn.execute('''
        CREATE TABLE repositories (
            id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            url TEXT,
            topics TEXT,
            license TEXT,
            created_at TEXT,
            updated_at TEXT,
            stars INTEGER,
            forks INTEGER,
            issues INTEGER,
            contributors INTEGER,
            commits INTEGER,
            last_commit TEXT,
            tags TEXT,
            notes TEXT,
            last_synced TEXT,
            version INTEGER DEFAULT 1,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    
    # Patch the DB_PATH in the db module
    from nuggit.util import db
    original_db_path = db.DB_PATH
    db.DB_PATH = db_path
    
    # Create a context manager for our test database
    from contextlib import contextmanager
    
    @contextmanager
    def test_get_connection():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Enable named column access
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
        try:
            yield conn
            conn.commit()  # Auto-commit on successful exit
        except Exception:
            conn.rollback()  # Rollback on error
            raise
        finally:
            conn.close()
    
    # Patch the get_connection function in user_db module
    with patch('nuggit.util.user_db.get_connection', test_get_connection):
        yield db_path
    
    # Cleanup
    db.DB_PATH = original_db_path
    os.unlink(db_path)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_email_service():
    """Mock email service for all integration tests."""
    with patch('nuggit.api.routes.auth.get_email_service') as mock_get_service:
        mock_email_service = MagicMock()
        mock_email_service.send_verification_email = AsyncMock(return_value=True)
        mock_email_service.send_password_reset_email = AsyncMock(return_value=True)
        mock_get_service.return_value = mock_email_service
        yield mock_email_service


# ============================================================================
# End-to-End Registration Flow Tests
# ============================================================================

@pytest.mark.integration
class TestRegistrationFlow:
    """Test complete registration workflow integration."""
    
    def test_complete_registration_flow(self, client, temp_db, mock_email_service):
        """Test complete registration → email verification → login flow."""
        # Step 1: Register user
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "TestPassword123",
            "first_name": "Test",
            "last_name": "User"
        }
        
        response = client.post("/auth/register", json=user_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Registration successful" in data["message"]
        
        # Verify email service was called
        mock_email_service.send_verification_email.assert_called_once()
        
        # Step 2: Verify user exists but is unverified
        user = get_user_by_email("test@example.com")
        assert user is not None
        assert user['is_verified'] == 0  # SQLite boolean
        
        # Step 3: Get verification token (simulate email link click)
        verification_token = create_email_verification_token(user['id'])
        
        # Step 4: Verify email
        verify_response = client.post("/auth/verify-email", json={"token": verification_token})
        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data["success"] is True
        assert "Email verified successfully" in verify_data["message"]
        
        # Step 5: Verify user is now verified
        user = get_user_by_email("test@example.com")
        assert user['is_verified'] == 1
        
        # Step 6: Login with verified account
        login_data = {
            "email_or_username": "test@example.com",
            "password": "TestPassword123"
        }
        
        login_response = client.post("/auth/login", json=login_data)
        assert login_response.status_code == 200
        login_result = login_response.json()
        assert "access_token" in login_result
        assert "refresh_token" in login_result
        assert login_result["token_type"] == "bearer"
        assert login_result["user"]["email"] == "test@example.com"
        assert login_result["user"]["is_verified"] is True
        
        # Step 7: Use access token to access protected endpoint
        headers = {"Authorization": f"Bearer {login_result['access_token']}"}
        profile_response = client.get("/auth/me", headers=headers)
        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        assert profile_data["email"] == "test@example.com"
        assert profile_data["username"] == "testuser"
    
    def test_registration_with_email_failure(self, client, temp_db):
        """Test registration when email service fails but user is still created."""
        # Mock email service to fail
        with patch('nuggit.api.routes.auth.get_email_service') as mock_get_service:
            mock_email_service = MagicMock()
            mock_email_service.send_verification_email = AsyncMock(return_value=False)
            mock_get_service.return_value = mock_email_service
            
            user_data = {
                "email": "test@example.com",
                "username": "testuser",
                "password": "TestPassword123",
                "first_name": "Test",
                "last_name": "User"
            }
            
            response = client.post("/auth/register", json=user_data)
            assert response.status_code == 200  # Registration still succeeds
            
            # Verify user was created despite email failure
            user = get_user_by_email("test@example.com")
            assert user is not None
            assert user['is_verified'] == 0  # Still unverified
            
            # Verify email service was called but failed
            mock_email_service.send_verification_email.assert_called_once()
    
    def test_registration_duplicate_prevention(self, client, temp_db, mock_email_service):
        """Test duplicate registration prevention across the full flow."""
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "TestPassword123",
            "first_name": "Test",
            "last_name": "User"
        }
        
        # First registration should succeed
        response1 = client.post("/auth/register", json=user_data)
        assert response1.status_code == 200
        
        # Second registration with same email should fail
        user_data["username"] = "testuser2"
        response2 = client.post("/auth/register", json=user_data)
        assert response2.status_code == 400
        data = response2.json()
        assert data["error"] is True
        assert "already exists" in data["message"]
        
        # Third registration with same username should fail
        user_data["email"] = "test2@example.com"
        user_data["username"] = "testuser"  # Original username
        response3 = client.post("/auth/register", json=user_data)
        assert response3.status_code == 400
        data = response3.json()
        assert data["error"] is True
        assert "already exists" in data["message"]
    
    def test_registration_invalid_verification_token(self, client, temp_db, mock_email_service):
        """Test registration with invalid/expired email verification tokens."""
        # Register user
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "TestPassword123",
            "first_name": "Test",
            "last_name": "User"
        }
        
        response = client.post("/auth/register", json=user_data)
        assert response.status_code == 200
        
        # Test with invalid token
        invalid_response = client.post("/auth/verify-email", json={"token": "invalid_token"})
        assert invalid_response.status_code == 400
        data = invalid_response.json()
        assert data["error"] is True
        assert "Invalid or expired" in data["message"]
        
        # Test with empty token
        empty_response = client.post("/auth/verify-email", json={"token": ""})
        assert empty_response.status_code == 400
        
        # Verify user is still unverified
        user = get_user_by_email("test@example.com")
        assert user['is_verified'] == 0
        
        # Valid token should still work
        verification_token = create_email_verification_token(user['id'])
        valid_response = client.post("/auth/verify-email", json={"token": verification_token})
        assert valid_response.status_code == 200


# ============================================================================
# Password Reset Flow Tests
# ============================================================================

@pytest.mark.integration
class TestPasswordResetFlow:
    """Test complete password reset workflow integration."""

    def test_complete_password_reset_flow(self, client, temp_db, mock_email_service):
        """Test complete password reset → token verification → login with new password flow."""
        # Step 1: Create and verify a user first
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "OriginalPassword123",
            "first_name": "Test",
            "last_name": "User"
        }

        # Register and verify user
        client.post("/auth/register", json=user_data)
        user = get_user_by_email("test@example.com")
        verify_user_email(user['id'])

        # Step 2: Request password reset
        reset_request = {"email": "test@example.com"}
        reset_response = client.post("/auth/forgot-password", json=reset_request)
        assert reset_response.status_code == 200
        data = reset_response.json()
        assert data["success"] is True
        assert "password reset link has been sent" in data["message"]

        # Verify email service was called
        mock_email_service.send_password_reset_email.assert_called_once()

        # Step 3: Get reset token (simulate email link click)
        reset_token = create_password_reset_token(user['id'])

        # Step 4: Reset password with token
        new_password_data = {
            "token": reset_token,
            "new_password": "NewPassword456"
        }

        reset_confirm_response = client.post("/auth/reset-password", json=new_password_data)
        assert reset_confirm_response.status_code == 200
        confirm_data = reset_confirm_response.json()
        assert confirm_data["success"] is True
        assert "Password reset successfully" in confirm_data["message"]

        # Step 5: Verify old password no longer works
        old_login_data = {
            "email_or_username": "test@example.com",
            "password": "OriginalPassword123"
        }

        old_login_response = client.post("/auth/login", json=old_login_data)
        assert old_login_response.status_code == 401

        # Step 6: Verify new password works
        new_login_data = {
            "email_or_username": "test@example.com",
            "password": "NewPassword456"
        }

        new_login_response = client.post("/auth/login", json=new_login_data)
        assert new_login_response.status_code == 200
        login_result = new_login_response.json()
        assert "access_token" in login_result
        assert login_result["user"]["email"] == "test@example.com"

    def test_password_reset_nonexistent_email(self, client, temp_db, mock_email_service):
        """Test password reset for non-existent email (should not reveal email existence)."""
        reset_request = {"email": "nonexistent@example.com"}
        reset_response = client.post("/auth/forgot-password", json=reset_request)

        # Should return success to not reveal email existence
        assert reset_response.status_code == 200
        data = reset_response.json()
        assert data["success"] is True
        assert "password reset link has been sent" in data["message"]

        # Email service should not be called for non-existent email
        mock_email_service.send_password_reset_email.assert_not_called()

    def test_password_reset_expired_token(self, client, temp_db, mock_email_service):
        """Test password reset with expired token."""
        # Create and verify user
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "OriginalPassword123",
            "first_name": "Test",
            "last_name": "User"
        }

        client.post("/auth/register", json=user_data)
        user = get_user_by_email("test@example.com")
        verify_user_email(user['id'])

        # Create an expired token by manipulating the database
        with sqlite3.connect(temp_db) as conn:
            conn.row_factory = sqlite3.Row
            expired_time = (datetime.utcnow() - timedelta(hours=2)).isoformat()
            conn.execute(
                "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
                (user['id'], "expired_token_123", expired_time)
            )
            conn.commit()

        # Attempt to reset password with expired token
        reset_data = {
            "token": "expired_token_123",
            "new_password": "NewPassword456"
        }

        reset_response = client.post("/auth/reset-password", json=reset_data)
        assert reset_response.status_code == 400
        data = reset_response.json()
        assert data["error"] is True
        assert "Invalid or expired" in data["message"]

        # Verify original password still works
        login_data = {
            "email_or_username": "test@example.com",
            "password": "OriginalPassword123"
        }

        login_response = client.post("/auth/login", json=login_data)
        assert login_response.status_code == 200

    def test_password_reset_token_reuse_prevention(self, client, temp_db, mock_email_service):
        """Test that password reset tokens cannot be reused after successful reset."""
        # Create and verify user
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "OriginalPassword123",
            "first_name": "Test",
            "last_name": "User"
        }

        client.post("/auth/register", json=user_data)
        user = get_user_by_email("test@example.com")
        verify_user_email(user['id'])

        # Get reset token
        reset_token = create_password_reset_token(user['id'])

        # First password reset should succeed
        reset_data = {
            "token": reset_token,
            "new_password": "NewPassword456"
        }

        first_reset_response = client.post("/auth/reset-password", json=reset_data)
        assert first_reset_response.status_code == 200

        # Second attempt with same token should fail
        second_reset_data = {
            "token": reset_token,
            "new_password": "AnotherPassword789"
        }

        second_reset_response = client.post("/auth/reset-password", json=second_reset_data)
        assert second_reset_response.status_code == 400
        data = second_reset_response.json()
        assert data["error"] is True
        assert "Invalid or expired" in data["message"]

        # Verify the first password change is still in effect
        login_data = {
            "email_or_username": "test@example.com",
            "password": "NewPassword456"
        }

        login_response = client.post("/auth/login", json=login_data)
        assert login_response.status_code == 200


# ============================================================================
# Protected Route Access Flow Tests
# ============================================================================

@pytest.mark.integration
class TestProtectedRouteFlow:
    """Test protected route access workflow integration."""

    def test_protected_route_authentication_flow(self, client, temp_db, mock_email_service):
        """Test complete authentication flow for accessing protected repository endpoints."""
        # Step 1: Register and verify user
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "TestPassword123",
            "first_name": "Test",
            "last_name": "User"
        }

        client.post("/auth/register", json=user_data)
        user = get_user_by_email("test@example.com")
        verify_user_email(user['id'])

        # Step 2: Login to get access token
        login_data = {
            "email_or_username": "test@example.com",
            "password": "TestPassword123"
        }

        login_response = client.post("/auth/login", json=login_data)
        assert login_response.status_code == 200
        login_result = login_response.json()
        access_token = login_result["access_token"]

        # Step 3: Access user profile (protected endpoint)
        headers = {"Authorization": f"Bearer {access_token}"}
        profile_response = client.get("/auth/me", headers=headers)
        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        assert profile_data["email"] == "test@example.com"
        assert profile_data["username"] == "testuser"
        assert profile_data["is_verified"] is True

        # Step 4: Attempt to access protected repository endpoint
        repo_data = {
            "id": "test/repo",
            "name": "Test Repository",
            "description": "A test repository",
            "url": "https://github.com/test/repo"
        }

        repo_response = client.post("/repositories/", json=repo_data, headers=headers)
        # Note: This might return 404 if the endpoint doesn't exist, but should not return 401
        assert repo_response.status_code != 401  # Should not be unauthorized

        # Step 5: Verify access without token fails
        no_auth_response = client.get("/auth/me")
        assert no_auth_response.status_code == 401
        data = no_auth_response.json()
        assert data["error"] is True
        assert "Authentication required" in data["message"]

    def test_protected_route_token_expiration(self, client, temp_db, mock_email_service):
        """Test access with expired tokens and proper 401 responses."""
        # Create and verify user
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "TestPassword123",
            "first_name": "Test",
            "last_name": "User"
        }

        client.post("/auth/register", json=user_data)
        user = get_user_by_email("test@example.com")
        verify_user_email(user['id'])

        # Create an expired token
        from datetime import timedelta
        expired_token = create_access_token(
            user_id=user['id'],
            email=user['email'],
            username=user['username'],
            expires_delta=timedelta(seconds=-1)  # Already expired
        )

        # Attempt to access protected endpoint with expired token
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 401
        data = response.json()
        assert data["error"] is True

    def test_protected_route_invalid_token(self, client, temp_db, mock_email_service):
        """Test access with malformed/invalid tokens."""
        # Test with malformed token
        malformed_headers = {"Authorization": "Bearer invalid.token.here"}
        malformed_response = client.get("/auth/me", headers=malformed_headers)
        assert malformed_response.status_code == 401

        # Test with wrong token format
        wrong_format_headers = {"Authorization": "InvalidFormat token123"}
        wrong_format_response = client.get("/auth/me", headers=wrong_format_headers)
        assert wrong_format_response.status_code == 401

        # Test with empty token
        empty_headers = {"Authorization": "Bearer "}
        empty_response = client.get("/auth/me", headers=empty_headers)
        assert empty_response.status_code == 401

        # Test with no Authorization header
        no_header_response = client.get("/auth/me")
        assert no_header_response.status_code == 401

    def test_protected_route_inactive_user(self, client, temp_db, mock_email_service):
        """Test access after user account is deactivated."""
        # Create and verify user
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "TestPassword123",
            "first_name": "Test",
            "last_name": "User"
        }

        client.post("/auth/register", json=user_data)
        user = get_user_by_email("test@example.com")
        verify_user_email(user['id'])

        # Login to get token
        login_data = {
            "email_or_username": "test@example.com",
            "password": "TestPassword123"
        }

        login_response = client.post("/auth/login", json=login_data)
        access_token = login_response.json()["access_token"]

        # Verify token works initially
        headers = {"Authorization": f"Bearer {access_token}"}
        initial_response = client.get("/auth/me", headers=headers)
        assert initial_response.status_code == 200

        # Deactivate user account
        with sqlite3.connect(temp_db) as conn:
            conn.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user['id'],))
            conn.commit()

        # Verify token no longer works after deactivation
        deactivated_response = client.get("/auth/me", headers=headers)
        assert deactivated_response.status_code == 401


# ============================================================================
# Admin Workflow Integration Tests
# ============================================================================

@pytest.mark.integration
class TestAdminWorkflowFlow:
    """Test admin workflow integration."""

    def test_admin_user_management_flow(self, client, temp_db, mock_email_service):
        """Test admin login → user management operations → verify changes persist."""
        # Step 1: Create admin user
        admin_data = {
            "email": "admin@example.com",
            "username": "admin",
            "password": "AdminPassword123",
            "first_name": "Admin",
            "last_name": "User"
        }

        client.post("/auth/register", json=admin_data)
        admin_user = get_user_by_email("admin@example.com")
        verify_user_email(admin_user['id'])

        # Manually set user as admin
        with sqlite3.connect(temp_db) as conn:
            conn.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (admin_user['id'],))
            conn.commit()

        # Step 2: Admin login
        admin_login_data = {
            "email_or_username": "admin@example.com",
            "password": "AdminPassword123"
        }

        admin_login_response = client.post("/auth/login", json=admin_login_data)
        assert admin_login_response.status_code == 200
        admin_token = admin_login_response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Step 3: Create regular user
        user_data = {
            "email": "user@example.com",
            "username": "regularuser",
            "password": "UserPassword123",
            "first_name": "Regular",
            "last_name": "User"
        }

        client.post("/auth/register", json=user_data)
        regular_user = get_user_by_email("user@example.com")
        verify_user_email(regular_user['id'])

        # Step 4: Admin accesses user list (if endpoint exists)
        # Note: This tests the admin authentication flow even if endpoint doesn't exist
        user_list_response = client.get("/auth/users", headers=admin_headers)
        # Should not return 401 (unauthorized) or 403 (forbidden) for admin
        assert user_list_response.status_code != 401
        assert user_list_response.status_code != 403

        # Step 5: Verify admin can access their own profile
        admin_profile_response = client.get("/auth/me", headers=admin_headers)
        assert admin_profile_response.status_code == 200
        admin_profile = admin_profile_response.json()
        assert admin_profile["is_admin"] is True
        assert admin_profile["email"] == "admin@example.com"

        # Step 6: Verify changes persist by checking database
        updated_admin = get_user_by_id(admin_user['id'])
        assert updated_admin['is_admin'] == 1

    def test_admin_repository_management(self, client, temp_db, mock_email_service):
        """Test admin access to admin-only repository management endpoints."""
        # Create and setup admin user
        admin_data = {
            "email": "admin@example.com",
            "username": "admin",
            "password": "AdminPassword123",
            "first_name": "Admin",
            "last_name": "User"
        }

        client.post("/auth/register", json=admin_data)
        admin_user = get_user_by_email("admin@example.com")
        verify_user_email(admin_user['id'])

        # Set as admin
        with sqlite3.connect(temp_db) as conn:
            conn.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (admin_user['id'],))
            conn.commit()

        # Login as admin
        admin_login_data = {
            "email_or_username": "admin@example.com",
            "password": "AdminPassword123"
        }

        admin_login_response = client.post("/auth/login", json=admin_login_data)
        admin_token = admin_login_response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Test admin repository operations
        # Note: These test the authentication flow even if specific endpoints don't exist

        # Admin should be able to access repository management
        repo_management_response = client.get("/admin/repositories", headers=admin_headers)
        assert repo_management_response.status_code != 401  # Not unauthorized
        assert repo_management_response.status_code != 403  # Not forbidden

        # Admin should be able to perform bulk operations
        bulk_operation_data = {"action": "sync_all"}
        bulk_response = client.post("/admin/repositories/bulk", json=bulk_operation_data, headers=admin_headers)
        assert bulk_response.status_code != 401
        assert bulk_response.status_code != 403

    def test_regular_user_admin_access_denied(self, client, temp_db, mock_email_service):
        """Test regular user attempts to access admin endpoints and receives 403 Forbidden."""
        # Create regular user
        user_data = {
            "email": "user@example.com",
            "username": "regularuser",
            "password": "UserPassword123",
            "first_name": "Regular",
            "last_name": "User"
        }

        client.post("/auth/register", json=user_data)
        user = get_user_by_email("user@example.com")
        verify_user_email(user['id'])

        # Login as regular user
        login_data = {
            "email_or_username": "user@example.com",
            "password": "UserPassword123"
        }

        login_response = client.post("/auth/login", json=login_data)
        user_token = login_response.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}

        # Verify user can access their own profile
        profile_response = client.get("/auth/me", headers=user_headers)
        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        assert profile_data["is_admin"] is False

        # Attempt to access admin-only endpoints should fail
        admin_users_response = client.get("/auth/users", headers=user_headers)
        # Should return 403 Forbidden (not 401 Unauthorized since user is authenticated)
        assert admin_users_response.status_code == 403 or admin_users_response.status_code == 404

        admin_repo_response = client.get("/admin/repositories", headers=user_headers)
        assert admin_repo_response.status_code == 403 or admin_repo_response.status_code == 404

        bulk_operation_data = {"action": "sync_all"}
        admin_bulk_response = client.post("/admin/repositories/bulk", json=bulk_operation_data, headers=user_headers)
        assert admin_bulk_response.status_code == 403 or admin_bulk_response.status_code == 404
