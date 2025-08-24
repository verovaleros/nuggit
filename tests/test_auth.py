"""
Unit tests for authentication functionality.

Tests user registration, login, email verification, password reset,
JWT token handling, and authentication middleware.
"""

import pytest
import tempfile
import os
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

# Import the modules we're testing
from nuggit.util.auth import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    verify_token
)
from nuggit.util.user_db import (
    create_user, authenticate_user, get_user_by_id, get_user_by_email,
    verify_user_email, update_user_password, create_email_verification_token,
    verify_email_verification_token, create_password_reset_token,
    verify_password_reset_token, UserAlreadyExistsError
)
from nuggit.api.routes.auth import get_current_user, require_auth, require_admin
from nuggit.api.main import app


class TestPasswordHashing:
    """Test password hashing and verification functions."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "test_password_123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long
        assert hashed.startswith('$2b$')  # bcrypt prefix
    
    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "test_password_123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_password_hash_consistency(self):
        """Test password hash consistency."""
        password = "test_password_123"
        hashed1 = hash_password(password)
        hashed2 = hash_password(password)

        # Different hashes should be generated (due to salt)
        assert hashed1 != hashed2

        # But both should verify correctly
        assert verify_password(password, hashed1) is True
        assert verify_password(password, hashed2) is True


class TestJWTTokens:
    """Test JWT token creation and verification."""
    
    def test_create_access_token(self):
        """Test access token creation."""
        token = create_access_token(
            user_id=1,
            email="test@example.com",
            username="testuser"
        )

        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        token = create_refresh_token(
            user_id=1,
            email="test@example.com",
            username="testuser"
        )

        assert isinstance(token, str)
        assert len(token) > 50

    def test_verify_token_valid(self):
        """Test token verification with valid token."""
        token = create_access_token(
            user_id=1,
            email="test@example.com",
            username="testuser"
        )

        decoded = verify_token(token)
        assert decoded["sub"] == "1"  # user_id is stored as 'sub' and converted to string
        assert decoded["email"] == "test@example.com"
        assert decoded["username"] == "testuser"
        assert decoded["type"] == "access"

    def test_verify_token_invalid(self):
        """Test token verification with invalid token."""
        invalid_token = "invalid.token.here"

        from nuggit.util.auth import InvalidTokenError
        with pytest.raises(InvalidTokenError):
            verify_token(invalid_token)

    def test_verify_token_expired(self):
        """Test token verification with expired token."""
        # Create token with very short expiration
        token = create_access_token(
            user_id=1,
            email="test@example.com",
            username="testuser",
            expires_delta=timedelta(seconds=-1)
        )

        from nuggit.util.auth import TokenExpiredError
        with pytest.raises(TokenExpiredError):
            verify_token(token)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Create temporary file
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)

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


class TestUserDatabase:
    """Test user database operations."""
    
    def test_create_user_success(self, temp_db):
        """Test successful user creation."""
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        user_id = create_user(**user_data)
        assert isinstance(user_id, int)
        assert user_id > 0
    
    def test_create_user_duplicate_email(self, temp_db):
        """Test user creation with duplicate email."""
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser1',
            'password': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        # Create first user
        create_user(**user_data)
        
        # Try to create second user with same email
        user_data['username'] = 'testuser2'
        with pytest.raises(UserAlreadyExistsError):
            create_user(**user_data)
    
    def test_create_user_duplicate_username(self, temp_db):
        """Test user creation with duplicate username."""
        user_data = {
            'email': 'test1@example.com',
            'username': 'testuser',
            'password': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        # Create first user
        create_user(**user_data)
        
        # Try to create second user with same username
        user_data['email'] = 'test2@example.com'
        with pytest.raises(UserAlreadyExistsError):
            create_user(**user_data)
    
    def test_get_user_by_id(self, temp_db):
        """Test retrieving user by ID."""
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        user_id = create_user(**user_data)
        user = get_user_by_id(user_id)
        
        assert user is not None
        assert user['id'] == user_id
        assert user['email'] == 'test@example.com'
        assert user['username'] == 'testuser'
        assert user['first_name'] == 'Test'
        assert user['last_name'] == 'User'
        assert user['is_verified'] == 0  # SQLite returns 0/1 for boolean
        assert user['is_active'] == 1
        assert user['is_admin'] == 0
    
    def test_get_user_by_email(self, temp_db):
        """Test retrieving user by email."""
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        user_id = create_user(**user_data)
        user = get_user_by_email('test@example.com')
        
        assert user is not None
        assert user['id'] == user_id
        assert user['email'] == 'test@example.com'
    
    def test_authenticate_user_success(self, temp_db):
        """Test successful user authentication."""
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        create_user(**user_data)
        # Verify email first
        user = get_user_by_email('test@example.com')
        verify_user_email(user['id'])
        
        # Test authentication with email
        authenticated_user = authenticate_user('test@example.com', 'TestPassword123')
        assert authenticated_user is not None
        assert authenticated_user['email'] == 'test@example.com'
        
        # Test authentication with username
        authenticated_user = authenticate_user('testuser', 'TestPassword123')
        assert authenticated_user is not None
        assert authenticated_user['username'] == 'testuser'
    
    def test_authenticate_user_wrong_password(self, temp_db):
        """Test authentication with wrong password."""
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        create_user(**user_data)
        user = get_user_by_email('test@example.com')
        verify_user_email(user['id'])
        
        authenticated_user = authenticate_user('test@example.com', 'WrongPassword')
        assert authenticated_user is None
    
    def test_authenticate_user_unverified(self, temp_db):
        """Test authentication with unverified user."""
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        create_user(**user_data)
        # Don't verify email
        
        authenticated_user = authenticate_user('test@example.com', 'TestPassword123')
        assert authenticated_user is None


class TestEmailVerification:
    """Test email verification functionality."""

    def test_create_email_verification_token(self, temp_db):
        """Test creating email verification token."""
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }

        user_id = create_user(**user_data)
        token = create_email_verification_token(user_id)

        assert isinstance(token, str)
        assert len(token) > 20  # Should be a reasonable length

    def test_verify_email_verification_token_valid(self, temp_db):
        """Test verifying valid email verification token."""
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }

        user_id = create_user(**user_data)
        token = create_email_verification_token(user_id)

        result = verify_email_verification_token(token)
        assert result == user_id  # Should return user ID

        # Now actually verify the user's email
        verify_success = verify_user_email(user_id)
        assert verify_success is True

        # Check that user is now verified
        user = get_user_by_id(user_id)
        assert user['is_verified'] == 1  # SQLite returns 0/1 for boolean

    def test_verify_email_verification_token_invalid(self, temp_db):
        """Test verifying invalid email verification token."""
        result = verify_email_verification_token('invalid_token')
        assert result is None  # Should return None for invalid token

    def test_verify_user_email_directly(self, temp_db):
        """Test directly verifying user email."""
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }

        user_id = create_user(**user_data)

        # User should not be verified initially
        user = get_user_by_id(user_id)
        assert user['is_verified'] == 0  # SQLite returns 0/1 for boolean

        # Verify user
        verify_user_email(user_id)

        # User should now be verified
        user = get_user_by_id(user_id)
        assert user['is_verified'] == 1


class TestPasswordReset:
    """Test password reset functionality."""

    def test_create_password_reset_token(self, temp_db):
        """Test creating password reset token."""
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }

        user_id = create_user(**user_data)
        token = create_password_reset_token(user_id)

        assert isinstance(token, str)
        assert len(token) > 20

    def test_verify_password_reset_token_valid(self, temp_db):
        """Test verifying valid password reset token."""
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }

        user_id = create_user(**user_data)
        token = create_password_reset_token(user_id)

        result = verify_password_reset_token(token)
        assert result == user_id

    def test_verify_password_reset_token_invalid(self, temp_db):
        """Test verifying invalid password reset token."""
        result = verify_password_reset_token('invalid_token')
        assert result is None

    def test_update_user_password(self, temp_db):
        """Test updating user password."""
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }

        user_id = create_user(**user_data)
        verify_user_email(user_id)

        # Update password
        new_password = 'NewPassword456'
        update_user_password(user_id, new_password)

        # Test authentication with new password
        authenticated_user = authenticate_user('test@example.com', new_password)
        assert authenticated_user is not None

        # Test that old password no longer works
        authenticated_user = authenticate_user('test@example.com', 'TestPassword123')
        assert authenticated_user is None


class TestAuthenticationMiddleware:
    """Test authentication middleware and dependencies."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self, temp_db):
        """Test getting current user with valid token."""
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }

        user_id = create_user(**user_data)
        verify_user_email(user_id)

        # Create token with correct signature
        token = create_access_token(
            user_id=user_id,
            email="test@example.com",
            username="testuser"
        )

        # Mock the authorization header
        from fastapi.security import HTTPAuthorizationCredentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        user = await get_current_user(credentials)
        assert user['id'] == user_id
        assert user['email'] == 'test@example.com'

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test getting current user with invalid token."""
        from fastapi.security import HTTPAuthorizationCredentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid_token")

        # Invalid token should return None, not raise exception
        user = await get_current_user(credentials)
        assert user is None

    @pytest.mark.asyncio
    async def test_require_auth_valid_user(self, temp_db):
        """Test require_auth with valid user."""
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }

        user_id = create_user(**user_data)
        verify_user_email(user_id)
        user = get_user_by_id(user_id)

        # Should not raise exception for active, verified user
        result = await require_auth(user)
        assert result == user

    @pytest.mark.asyncio
    async def test_require_auth_inactive_user(self, temp_db):
        """Test require_auth with inactive user through full auth flow."""
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }

        user_id = create_user(**user_data)
        verify_user_email(user_id)

        # Create token first
        token = create_access_token(
            user_id=user_id,
            email="test@example.com",
            username="testuser"
        )

        # Manually set user as inactive using our test database
        with sqlite3.connect(temp_db) as conn:
            conn.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
            conn.commit()

        # Test the full auth flow - get_current_user should return None for inactive user
        from fastapi.security import HTTPAuthorizationCredentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        current_user = await get_current_user(credentials)
        assert current_user is None  # Should be None for inactive user

        # require_auth should raise exception when current_user is None
        with pytest.raises(HTTPException) as exc_info:
            await require_auth(current_user)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_require_admin_admin_user(self, temp_db):
        """Test require_admin with admin user."""
        user_data = {
            'email': 'admin@example.com',
            'username': 'admin',
            'password': 'AdminPassword123',
            'first_name': 'Admin',
            'last_name': 'User'
        }

        user_id = create_user(**user_data)
        verify_user_email(user_id)

        # Manually set user as admin using our test database
        with sqlite3.connect(temp_db) as conn:
            conn.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (user_id,))
            conn.commit()

        user = get_user_by_id(user_id)

        # Should not raise exception for admin user
        result = await require_admin(user)
        assert result == user

    @pytest.mark.asyncio
    async def test_require_admin_regular_user(self, temp_db):
        """Test require_admin with regular user."""
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }

        user_id = create_user(**user_data)
        verify_user_email(user_id)
        user = get_user_by_id(user_id)

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(user)
        assert exc_info.value.status_code == 403
