"""
API endpoint tests for authentication functionality.

Tests authentication API endpoints including registration, login,
email verification, password reset, and protected routes.
"""

import pytest
import tempfile
import os
import sqlite3
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from nuggit.api.main import app
from nuggit.util.user_db import create_user, verify_user_email, get_user_by_email
from nuggit.util.auth import create_access_token


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


class TestRegistrationAPI:
    """Test user registration API endpoints."""
    
    @patch('nuggit.api.routes.auth.get_email_service')
    def test_register_success(self, mock_get_email_service, client, temp_db):
        """Test successful user registration."""
        # Mock the email service and its send_verification_email method
        mock_email_service = MagicMock()
        mock_email_service.send_verification_email = AsyncMock(return_value=True)
        mock_get_email_service.return_value = mock_email_service
        
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
        
        # Verify email sending was called
        mock_email_service.send_verification_email.assert_called_once()
    
    def test_register_duplicate_email(self, client, temp_db):
        """Test registration with duplicate email."""
        # Create first user
        user_data = {
            "email": "test@example.com",
            "username": "testuser1",
            "password": "TestPassword123",
            "first_name": "Test",
            "last_name": "User"
        }
        
        with patch('nuggit.api.routes.auth.get_email_service') as mock_get_service:
            mock_email_service = MagicMock()
            mock_email_service.send_verification_email = AsyncMock(return_value=True)
            mock_get_service.return_value = mock_email_service
            response1 = client.post("/auth/register", json=user_data)
            assert response1.status_code == 200
        
        # Try to create second user with same email
        user_data["username"] = "testuser2"
        response2 = client.post("/auth/register", json=user_data)
        
        assert response2.status_code == 400
        data = response2.json()
        assert data["error"] is True
        assert "already exists" in data["message"]
    
    def test_register_invalid_email(self, client, temp_db):
        """Test registration with invalid email."""
        user_data = {
            "email": "invalid-email",
            "username": "testuser",
            "password": "TestPassword123",
            "first_name": "Test",
            "last_name": "User"
        }
        
        response = client.post("/auth/register", json=user_data)
        
        assert response.status_code == 400  # Validation error
    
    def test_register_weak_password(self, client, temp_db):
        """Test registration with weak password."""
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "weak",
            "first_name": "Test",
            "last_name": "User"
        }
        
        response = client.post("/auth/register", json=user_data)
        
        assert response.status_code == 400  # Validation error


class TestLoginAPI:
    """Test user login API endpoints."""
    
    def test_login_success(self, client, temp_db):
        """Test successful login."""
        # Create and verify user
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        user_id = create_user(**user_data)
        verify_user_email(user_id)
        
        # Login with email
        login_data = {
            "email_or_username": "test@example.com",
            "password": "TestPassword123"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "test@example.com"
    
    def test_login_with_username(self, client, temp_db):
        """Test login with username."""
        # Create and verify user
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        user_id = create_user(**user_data)
        verify_user_email(user_id)
        
        # Login with username
        login_data = {
            "email_or_username": "testuser",
            "password": "TestPassword123"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["username"] == "testuser"
    
    def test_login_wrong_password(self, client, temp_db):
        """Test login with wrong password."""
        # Create and verify user
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        user_id = create_user(**user_data)
        verify_user_email(user_id)
        
        # Login with wrong password
        login_data = {
            "email_or_username": "test@example.com",
            "password": "WrongPassword"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"] is True
        assert "Invalid email/username or password" in data["message"]
    
    def test_login_unverified_user(self, client, temp_db):
        """Test login with unverified user."""
        # Create user but don't verify
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        create_user(**user_data)
        
        # Try to login
        login_data = {
            "email_or_username": "test@example.com",
            "password": "TestPassword123"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"] is True
        assert "Invalid email/username or password" in data["message"]
    
    def test_login_nonexistent_user(self, client, temp_db):
        """Test login with nonexistent user."""
        login_data = {
            "email_or_username": "nonexistent@example.com",
            "password": "TestPassword123"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"] is True
        assert "Invalid email/username or password" in data["message"]


class TestProtectedRoutes:
    """Test protected API routes."""
    
    def test_protected_route_without_auth(self, client, temp_db):
        """Test accessing protected route without authentication."""
        repo_data = {
            "id": "test/repo"
        }
        
        response = client.post("/repositories/", json=repo_data)
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"] is True
        assert "Authentication required" in data["message"]
    
    def test_protected_route_with_invalid_token(self, client, temp_db):
        """Test accessing protected route with invalid token."""
        repo_data = {
            "id": "test/repo"
        }
        
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.post("/repositories/", json=repo_data, headers=headers)
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"] is True
    
    def test_get_current_user_profile(self, client, temp_db):
        """Test getting current user profile."""
        # Create and verify user
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        user_id = create_user(**user_data)
        verify_user_email(user_id)
        
        # Create token
        token = create_access_token(
            user_id=user_id,
            email="test@example.com",
            username="testuser"
        )
        
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/auth/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["username"] == "testuser"
        assert data["first_name"] == "Test"
        assert data["last_name"] == "User"
        assert data["is_verified"] is True
