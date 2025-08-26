"""
Tests for user-specific repository filtering functionality.

This module tests that:
1. Users can only see their own repositories
2. Admin users can see all repositories
3. Repository operations are properly restricted by ownership
4. Access control is enforced across all endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from nuggit.api.main import app
from nuggit.util.auth import create_access_token
from nuggit.util.db import list_user_repositories, list_all_repositories


class TestUserRepositoryFiltering:
    """Test user-specific repository filtering."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def regular_user_token(self):
        """Create access token for regular user."""
        return create_access_token(
            user_id=1,
            email="user@example.com",
            username="testuser",
            is_admin=False
        )

    @pytest.fixture
    def admin_user_token(self):
        """Create access token for admin user."""
        return create_access_token(
            user_id=2,
            email="admin@example.com",
            username="admin",
            is_admin=True
        )

    @pytest.fixture
    def other_user_token(self):
        """Create access token for another regular user."""
        return create_access_token(
            user_id=3,
            email="other@example.com",
            username="otheruser",
            is_admin=False
        )

    @pytest.fixture
    def mock_repositories(self):
        """Mock repository data."""
        return [
            {
                "id": "user1/repo1",
                "name": "repo1",
                "user_id": 1,
                "description": "User 1's repository 1"
            },
            {
                "id": "user1/repo2",
                "name": "repo2",
                "user_id": 1,
                "description": "User 1's repository 2"
            },
            {
                "id": "user3/repo1",
                "name": "repo1",
                "user_id": 3,
                "description": "User 3's repository 1"
            },
            {
                "id": "admin/repo1",
                "name": "repo1",
                "user_id": 2,
                "description": "Admin's repository"
            }
        ]

    def test_list_repositories_regular_user_sees_own_only(self, client, regular_user_token, mock_repositories):
        """Test that regular users only see their own repositories."""
        with patch('nuggit.api.routes.repositories.list_user_repositories') as mock_list_user, \
             patch('nuggit.api.routes.repositories.list_all_repositories') as mock_list_all, \
             patch('nuggit.api.routes.repositories.get_current_user') as mock_get_user:

            # Mock the current user
            mock_get_user.return_value = {
                "id": 1,
                "email": "user@example.com",
                "username": "testuser",
                "is_admin": False
            }

            # Mock user repositories (only user 1's repos)
            user_repos = [repo for repo in mock_repositories if repo["user_id"] == 1]
            mock_list_user.return_value = user_repos
            mock_list_all.return_value = mock_repositories

            response = client.get(
                "/repositories/",
                headers={"Authorization": f"Bearer {regular_user_token}"}
            )

            assert response.status_code == 200
            data = response.json()

            # Should only see own repositories
            assert len(data["repositories"]) == 2
            assert all(repo["user_id"] == 1 for repo in data["repositories"])

            # Should call list_user_repositories, not list_all_repositories
            mock_list_user.assert_called_once_with(1)
            mock_list_all.assert_not_called()

    def test_list_repositories_admin_sees_all(self, client, admin_user_token, mock_repositories):
        """Test that admin users see all repositories."""
        with patch('nuggit.api.routes.repositories.list_user_repositories') as mock_list_user, \
             patch('nuggit.api.routes.repositories.list_all_repositories') as mock_list_all, \
             patch('nuggit.api.routes.repositories.get_current_user') as mock_get_user:

            # Mock the current admin user
            mock_get_user.return_value = {
                "id": 2,
                "email": "admin@example.com",
                "username": "admin",
                "is_admin": True
            }

            mock_list_all.return_value = mock_repositories

            response = client.get(
                "/repositories/",
                headers={"Authorization": f"Bearer {admin_user_token}"}
            )

            assert response.status_code == 200
            data = response.json()

            # Should see all repositories
            assert len(data["repositories"]) == 4

            # Should call list_all_repositories, not list_user_repositories
            mock_list_all.assert_called_once()
            mock_list_user.assert_not_called()

    def test_list_repositories_requires_authentication(self, client):
        """Test that listing repositories requires authentication."""
        with patch('nuggit.api.routes.repositories.get_current_user') as mock_get_user:
            # Mock authentication failure
            from fastapi import HTTPException
            mock_get_user.side_effect = HTTPException(status_code=401, detail="Not authenticated")

            response = client.get("/repositories/")
            assert response.status_code == 401

    def test_get_repository_detail_access_control(self, client, regular_user_token, other_user_token, mock_repositories):
        """Test that users can only access their own repository details."""
        user_repo = mock_repositories[0]  # user1/repo1 (user_id: 1)
        other_repo = mock_repositories[2]  # user3/repo1 (user_id: 3)

        with patch('nuggit.api.routes.detail.db_get_repository') as mock_get_repo, \
             patch('nuggit.api.routes.detail.get_current_user') as mock_get_user:

            # Mock the current user
            mock_get_user.return_value = {
                "id": 1,
                "email": "user@example.com",
                "username": "testuser",
                "is_admin": False
            }

            # Test accessing own repository - should succeed
            mock_get_repo.return_value = user_repo

            response = client.get(
                f"/repositories/{user_repo['id']}",
                headers={"Authorization": f"Bearer {regular_user_token}"}
            )

            assert response.status_code == 200

            # Test accessing other user's repository - should fail
            mock_get_repo.return_value = other_repo

            response = client.get(
                f"/repositories/{other_repo['id']}",
                headers={"Authorization": f"Bearer {regular_user_token}"}
            )

            assert response.status_code == 403
            # Check that the response contains an access error message
            response_data = response.json()
            assert "access" in response_data.get("message", "").lower() or "access" in str(response_data).lower()

    def test_admin_can_access_any_repository(self, client, admin_user_token, mock_repositories):
        """Test that admin users can access any repository."""
        user_repo = mock_repositories[0]  # user1/repo1 (user_id: 1)

        with patch('nuggit.api.routes.detail.db_get_repository') as mock_get_repo, \
             patch('nuggit.api.routes.detail.get_current_user') as mock_get_user:

            # Mock the current admin user
            mock_get_user.return_value = {
                "id": 2,
                "email": "admin@example.com",
                "username": "admin",
                "is_admin": True
            }

            mock_get_repo.return_value = user_repo

            response = client.get(
                f"/repositories/{user_repo['id']}",
                headers={"Authorization": f"Bearer {admin_user_token}"}
            )

            assert response.status_code == 200

    def test_repository_operations_access_control(self, client, regular_user_token, other_user_token, mock_repositories):
        """Test that repository operations respect access control."""
        user_repo = mock_repositories[0]  # user1/repo1 (user_id: 1)
        other_repo = mock_repositories[2]  # user3/repo1 (user_id: 3)

        # Test metadata update on own repository - should succeed
        with patch('nuggit.api.routes.repositories.get_repository') as mock_get_repo, \
             patch('nuggit.api.routes.repositories.update_repository_fields') as mock_update, \
             patch('nuggit.api.routes.repositories.get_current_user') as mock_get_user:

            # Mock the current user
            mock_get_user.return_value = {
                "id": 1,
                "email": "user@example.com",
                "username": "testuser",
                "is_admin": False
            }

            mock_get_repo.return_value = user_repo
            mock_update.return_value = True

            response = client.patch(
                f"/repositories/{user_repo['id']}/fields",
                headers={"Authorization": f"Bearer {regular_user_token}"},
                json={"tags": "test", "notes": "test notes"}
            )

            assert response.status_code == 200

            # Test metadata update on other user's repository - should fail
            mock_get_repo.return_value = other_repo

            response = client.patch(
                f"/repositories/{other_repo['id']}/fields",
                headers={"Authorization": f"Bearer {regular_user_token}"},
                json={"tags": "test", "notes": "test notes"}
            )

            assert response.status_code == 403

    def test_repository_deletion_access_control(self, client, regular_user_token, other_user_token, mock_repositories):
        """Test that repository deletion respects access control."""
        user_repo = mock_repositories[0]  # user1/repo1 (user_id: 1)
        other_repo = mock_repositories[2]  # user3/repo1 (user_id: 3)

        # Test deleting own repository - should succeed
        with patch('nuggit.api.routes.repositories.get_repository') as mock_get_repo, \
             patch('nuggit.api.routes.repositories.db_delete_repository') as mock_delete, \
             patch('nuggit.api.routes.repositories.get_current_user') as mock_get_user:

            # Mock the current user
            mock_get_user.return_value = {
                "id": 1,
                "email": "user@example.com",
                "username": "testuser",
                "is_admin": False
            }

            mock_get_repo.return_value = user_repo
            mock_delete.return_value = True

            response = client.delete(
                f"/repositories/{user_repo['id']}",
                headers={"Authorization": f"Bearer {regular_user_token}"}
            )

            assert response.status_code == 200

            # Test deleting other user's repository - should fail
            mock_get_repo.return_value = other_repo

            response = client.delete(
                f"/repositories/{other_repo['id']}",
                headers={"Authorization": f"Bearer {regular_user_token}"}
            )

            assert response.status_code == 403

    def test_check_repository_access_control(self, client, regular_user_token, mock_repositories):
        """Test that repository existence check respects access control."""
        user_repo = mock_repositories[0]  # user1/repo1 (user_id: 1)
        other_repo = mock_repositories[2]  # user3/repo1 (user_id: 3)

        with patch('nuggit.api.routes.repositories.get_repository') as mock_get_repo, \
             patch('nuggit.api.routes.repositories.get_current_user') as mock_get_user:

            # Mock the current user
            mock_get_user.return_value = {
                "id": 1,
                "email": "user@example.com",
                "username": "testuser",
                "is_admin": False
            }

            # Test checking own repository - should return true
            mock_get_repo.return_value = user_repo

            response = client.get(
                f"/repositories/check/{user_repo['id']}",
                headers={"Authorization": f"Bearer {regular_user_token}"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["exists"] is True
            assert data["repository"] is not None

            # Test checking other user's repository - should return false
            mock_get_repo.return_value = other_repo

            response = client.get(
                f"/repositories/check/{other_repo['id']}",
                headers={"Authorization": f"Bearer {regular_user_token}"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["exists"] is False
            assert data["repository"] is None


class TestDatabaseUserFiltering:
    """Test database-level user filtering functions."""

    def test_list_user_repositories_function(self):
        """Test the list_user_repositories database function."""
        with patch('nuggit.util.db.get_connection') as mock_get_conn:
            mock_conn = MagicMock()
            mock_get_conn.return_value.__enter__.return_value = mock_conn
            
            # Mock query results
            mock_results = [
                {"id": "user1/repo1", "user_id": 1, "name": "repo1"},
                {"id": "user1/repo2", "user_id": 1, "name": "repo2"}
            ]
            mock_conn.execute.return_value = mock_results

            result = list_user_repositories(1)

            # Verify correct query was executed
            mock_conn.execute.assert_called_once_with(
                "SELECT * FROM repositories WHERE user_id = ?",
                (1,)
            )

            # Verify results
            assert len(result) == 2
            assert all(repo["user_id"] == 1 for repo in result)
