"""
Database tests for authentication functionality.

Tests user database operations, repository-user associations,
and authentication-related database functions.
"""

import pytest
import tempfile
import os
import sqlite3
from datetime import datetime, timedelta

from nuggit.util.user_db import (
    create_user, get_user_by_id, get_user_by_email, get_users_list,
    verify_user_email, update_user_password, create_email_verification_token,
    verify_email_verification_token, create_password_reset_token,
    verify_password_reset_token, UserAlreadyExistsError
)
from nuggit.util.db import insert_or_update_repo, get_repository
from nuggit.util.timezone import now_utc, UTC


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
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
    
    # Create repositories table
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

    # Create repository_history table
    conn.execute('''
        CREATE TABLE repository_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_id TEXT NOT NULL,
            field TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            changed_at TEXT NOT NULL,
            FOREIGN KEY (repo_id) REFERENCES repositories(id)
        )
    ''')

    # Create repository_comments table
    conn.execute('''
        CREATE TABLE repository_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_id TEXT NOT NULL,
            comment TEXT NOT NULL,
            author TEXT DEFAULT 'Anonymous',
            created_at TEXT NOT NULL,
            FOREIGN KEY (repo_id) REFERENCES repositories(id)
        )
    ''')

    # Create repository_versions table
    conn.execute('''
        CREATE TABLE repository_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_id TEXT NOT NULL,
            version_number TEXT NOT NULL,
            release_date TEXT,
            description TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (repo_id) REFERENCES repositories(id),
            UNIQUE(repo_id, version_number)
        )
    ''')
    
    conn.commit()
    conn.close()

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

    # Patch the get_connection function in both user_db and db modules
    from unittest.mock import patch
    with patch('nuggit.util.user_db.get_connection', test_get_connection), \
         patch('nuggit.util.db.get_connection', test_get_connection):
        yield db_path

    # Cleanup
    os.unlink(db_path)


class TestUserDatabaseOperations:
    """Test user database CRUD operations."""
    
    def test_create_multiple_users(self, temp_db):
        """Test creating multiple users."""
        users_data = [
            {
                'email': 'user1@example.com',
                'username': 'user1',
                'password': 'Password123',
                'first_name': 'User',
                'last_name': 'One'
            },
            {
                'email': 'user2@example.com',
                'username': 'user2',
                'password': 'Password123',
                'first_name': 'User',
                'last_name': 'Two'
            },
            {
                'email': 'admin@example.com',
                'username': 'admin',
                'password': 'AdminPassword123',
                'first_name': 'Admin',
                'last_name': 'User'
            }
        ]
        
        user_ids = []
        for user_data in users_data:
            user_id = create_user(**user_data)
            user_ids.append(user_id)
            assert isinstance(user_id, int)
            assert user_id > 0
        
        # Verify all users were created
        assert len(set(user_ids)) == 3  # All IDs should be unique
    
    def test_get_users_list_pagination(self, temp_db):
        """Test getting paginated list of users."""
        # Create multiple users
        for i in range(15):
            user_data = {
                'email': f'user{i}@example.com',
                'username': f'user{i}',
                'password': 'Password123',
                'first_name': f'User{i}',
                'last_name': 'Test'
            }
            create_user(**user_data)
        
        # Test first page
        result = get_users_list(page=1, per_page=10)
        assert result['total'] == 15
        assert result['page'] == 1
        assert result['per_page'] == 10
        assert len(result['users']) == 10
        
        # Test second page
        result = get_users_list(page=2, per_page=10)
        assert result['total'] == 15
        assert result['page'] == 2
        assert result['per_page'] == 10
        assert len(result['users']) == 5
    
    def test_get_users_list_search(self, temp_db):
        """Test searching users."""
        # Create test users
        users_data = [
            {
                'email': 'john.doe@example.com',
                'username': 'johndoe',
                'password': 'Password123',
                'first_name': 'John',
                'last_name': 'Doe'
            },
            {
                'email': 'jane.smith@example.com',
                'username': 'janesmith',
                'password': 'Password123',
                'first_name': 'Jane',
                'last_name': 'Smith'
            },
            {
                'email': 'admin@company.com',
                'username': 'admin',
                'password': 'Password123',
                'first_name': 'Admin',
                'last_name': 'User'
            }
        ]
        
        for user_data in users_data:
            create_user(**user_data)
        
        # Search by email
        result = get_users_list(search='john.doe')
        assert result['total'] == 1
        assert result['users'][0]['email'] == 'john.doe@example.com'
        
        # Search by username
        result = get_users_list(search='admin')
        assert result['total'] == 1
        assert result['users'][0]['username'] == 'admin'
        
        # Search with no results
        result = get_users_list(search='nonexistent')
        assert result['total'] == 0
        assert len(result['users']) == 0
    
    def test_get_users_list_filter_active(self, temp_db):
        """Test filtering users by active status."""
        # Create users
        user1_id = create_user(
            email='active@example.com',
            username='active',
            password='Password123',
            first_name='Active',
            last_name='User'
        )
        
        user2_id = create_user(
            email='inactive@example.com',
            username='inactive',
            password='Password123',
            first_name='Inactive',
            last_name='User'
        )
        
        # Deactivate one user
        from nuggit.util.user_db import get_connection
        with get_connection() as conn:
            conn.execute("UPDATE users SET is_active = FALSE WHERE id = ?", (user2_id,))
        
        # Filter for active users only
        result = get_users_list(is_active=True)
        assert result['total'] == 1
        assert result['users'][0]['email'] == 'active@example.com'
        
        # Filter for inactive users only
        result = get_users_list(is_active=False)
        assert result['total'] == 1
        assert result['users'][0]['email'] == 'inactive@example.com'
        
        # Get all users
        result = get_users_list()
        assert result['total'] == 2


class TestRepositoryUserAssociation:
    """Test repository-user associations."""
    
    def test_insert_repository_with_user_id(self, temp_db):
        """Test inserting repository with user association."""
        # Create user
        user_id = create_user(
            email='test@example.com',
            username='testuser',
            password='Password123',
            first_name='Test',
            last_name='User'
        )
        
        # Create repository data
        repo_data = {
            'id': 'test/repo',
            'name': 'repo',
            'description': 'Test repository',
            'url': 'https://github.com/test/repo',
            'stars': 100,
            'forks': 20
        }
        
        # Insert repository with user association
        insert_or_update_repo(repo_data, user_id=user_id)
        
        # Verify repository was created with user association
        repo = get_repository('test/repo')
        assert repo is not None
        assert repo['id'] == 'test/repo'
        assert repo['user_id'] == user_id
    
    def test_insert_repository_without_user_id(self, temp_db):
        """Test inserting repository without user association."""
        repo_data = {
            'id': 'test/repo',
            'name': 'repo',
            'description': 'Test repository',
            'url': 'https://github.com/test/repo',
            'stars': 100,
            'forks': 20
        }
        
        # Insert repository without user association
        insert_or_update_repo(repo_data)
        
        # Verify repository was created without user association
        repo = get_repository('test/repo')
        assert repo is not None
        assert repo['id'] == 'test/repo'
        assert repo.get('user_id') is None
    
    def test_update_repository_preserves_user_id(self, temp_db):
        """Test that updating repository preserves user association."""
        # Create user
        user_id = create_user(
            email='test@example.com',
            username='testuser',
            password='Password123',
            first_name='Test',
            last_name='User'
        )
        
        # Create repository with user association
        repo_data = {
            'id': 'test/repo',
            'name': 'repo',
            'description': 'Test repository',
            'url': 'https://github.com/test/repo',
            'stars': 100,
            'forks': 20
        }
        
        insert_or_update_repo(repo_data, user_id=user_id)
        
        # Update repository without specifying user_id
        updated_repo_data = {
            'id': 'test/repo',
            'name': 'repo',
            'description': 'Updated test repository',
            'url': 'https://github.com/test/repo',
            'stars': 150,
            'forks': 25
        }
        
        insert_or_update_repo(updated_repo_data)
        
        # Verify user association is preserved
        repo = get_repository('test/repo')
        assert repo is not None
        assert repo['description'] == 'Updated test repository'
        assert repo['stars'] == 150
        assert repo['user_id'] == user_id


class TestTokenManagement:
    """Test email verification and password reset token management."""
    
    def test_email_verification_token_expiration(self, temp_db):
        """Test email verification token expiration."""
        user_id = create_user(
            email='test@example.com',
            username='testuser',
            password='Password123',
            first_name='Test',
            last_name='User'
        )
        
        # Create token
        token = create_email_verification_token(user_id)
        
        # Manually expire the token
        from nuggit.util.user_db import get_connection
        with get_connection() as conn:
            expired_time = now_utc() - timedelta(hours=1)
            conn.execute(
                "UPDATE email_verification_tokens SET expires_at = ? WHERE token = ?",
                (expired_time.isoformat(), token)
            )
        
        # Try to verify expired token
        result = verify_email_verification_token(token)
        assert result is None
    
    def test_password_reset_token_expiration(self, temp_db):
        """Test password reset token expiration."""
        user_id = create_user(
            email='test@example.com',
            username='testuser',
            password='Password123',
            first_name='Test',
            last_name='User'
        )
        
        # Create token
        token = create_password_reset_token(user_id)
        
        # Manually expire the token
        from nuggit.util.user_db import get_connection
        with get_connection() as conn:
            expired_time = now_utc() - timedelta(hours=1)
            conn.execute(
                "UPDATE password_reset_tokens SET expires_at = ? WHERE token = ?",
                (expired_time.isoformat(), token)
            )
        
        # Try to verify expired token
        result = verify_password_reset_token(token)
        assert result is None
    
    def test_password_reset_token_single_use(self, temp_db):
        """Test that password reset tokens can only be used once."""
        user_id = create_user(
            email='test@example.com',
            username='testuser',
            password='Password123',
            first_name='Test',
            last_name='User'
        )
        
        # Create token
        token = create_password_reset_token(user_id)
        
        # Use token first time
        result1 = verify_password_reset_token(token)
        assert result1 == user_id
        
        # Try to use token second time
        result2 = verify_password_reset_token(token)
        assert result2 is None
