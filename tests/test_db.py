#!/usr/bin/env python3
"""
Unit tests for the nuggit/util/db.py module.
"""

import unittest
import sqlite3
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path so we can import the module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module to test
from nuggit.util import db


class TestDatabase(unittest.TestCase):
    """Test cases for the database utility functions."""

    def setUp(self):
        """Set up a temporary database for testing."""
        # Create a temporary file for the test database
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp()

        # Patch the DB_PATH to use our temporary database
        self.db_path_patcher = patch('nuggit.util.db.DB_PATH', Path(self.temp_db_path))
        self.mock_db_path = self.db_path_patcher.start()

        # Initialize the test database
        db.initialize_database()

        # Sample repository data for testing
        self.sample_repo = {
            "id": "test/repo",
            "name": "Test Repository",
            "description": "A test repository",
            "url": "https://github.com/test/repo",
            "topics": "test, sample",
            "license": "MIT",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-02T00:00:00",
            "stars": 10,
            "forks": 5,
            "issues": 2,
            "contributors": "3",
            "commits": 100,
            "last_commit": "2023-01-03T00:00:00",
            "tags": "test",
            "notes": "Test notes",
            "last_synced": datetime.utcnow().isoformat()
        }

        # Updated repository data for testing
        self.updated_repo = self.sample_repo.copy()
        self.updated_repo.update({
            "stars": 15,
            "forks": 7,
            "issues": 3,
            "commits": 120,
            "last_commit": "2023-01-04T00:00:00",
            "tags": "test, updated",
            "notes": "Updated notes",
            "last_synced": datetime.utcnow().isoformat()
        })

    def tearDown(self):
        """Clean up after tests."""
        # Stop the patcher
        self.db_path_patcher.stop()

        # Close and remove the temporary database
        os.close(self.temp_db_fd)
        os.unlink(self.temp_db_path)

    def test_initialize_database(self):
        """Test that the database is initialized correctly."""
        # Connect to the database directly to check the schema
        conn = sqlite3.connect(self.temp_db_path)
        cursor = conn.cursor()

        # Check if the repositories table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='repositories'")
        self.assertIsNotNone(cursor.fetchone())

        # Check if the repository_history table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='repository_history'")
        self.assertIsNotNone(cursor.fetchone())

        # Check the schema of the repositories table
        cursor.execute("PRAGMA table_info(repositories)")
        columns = [row[1] for row in cursor.fetchall()]
        expected_columns = [
            'id', 'name', 'description', 'url', 'topics', 'license', 'created_at',
            'updated_at', 'stars', 'forks', 'issues', 'contributors', 'commits',
            'last_commit', 'tags', 'notes', 'last_synced'
        ]
        for column in expected_columns:
            self.assertIn(column, columns)

        conn.close()

    def test_insert_repo(self):
        """Test inserting a new repository."""
        # Insert a repository
        db.insert_or_update_repo(self.sample_repo)

        # Verify it was inserted correctly
        repo = db.get_repository(self.sample_repo["id"])
        self.assertIsNotNone(repo)
        self.assertEqual(repo["name"], self.sample_repo["name"])
        self.assertEqual(repo["description"], self.sample_repo["description"])
        self.assertEqual(int(repo["stars"]), self.sample_repo["stars"])

    def test_update_repo(self):
        """Test updating an existing repository."""
        # Insert a repository
        db.insert_or_update_repo(self.sample_repo)

        # Update the repository
        db.insert_or_update_repo(self.updated_repo)

        # Verify it was updated correctly
        repo = db.get_repository(self.sample_repo["id"])
        self.assertIsNotNone(repo)
        self.assertEqual(int(repo["stars"]), self.updated_repo["stars"])
        self.assertEqual(int(repo["forks"]), self.updated_repo["forks"])
        self.assertEqual(repo["tags"], self.updated_repo["tags"])
        self.assertEqual(repo["notes"], self.updated_repo["notes"])

    def test_repository_history(self):
        """Test that repository history is recorded correctly."""
        # Insert a repository
        db.insert_or_update_repo(self.sample_repo)

        # Update the repository
        db.insert_or_update_repo(self.updated_repo)

        # Get the history
        history = db.get_repository_history(self.sample_repo["id"])

        # Verify history was recorded
        self.assertGreater(len(history), 0)

        # Check that the stars change was recorded
        stars_history = [h for h in history if h["field"] == "stars"]
        self.assertGreater(len(stars_history), 0)
        self.assertEqual(stars_history[0]["old_value"], str(self.sample_repo["stars"]))
        self.assertEqual(stars_history[0]["new_value"], str(self.updated_repo["stars"]))

    def test_tag_repository(self):
        """Test adding a tag to a repository."""
        # Insert a repository
        db.insert_or_update_repo(self.sample_repo)

        # Add a tag
        new_tag = "new-tag"
        db.tag_repository(self.sample_repo["id"], new_tag)

        # Verify the tag was added
        repo = db.get_repository(self.sample_repo["id"])
        self.assertIn(new_tag, repo["tags"])

        # The original tag should still be there
        self.assertIn("test", repo["tags"])

    def test_add_note(self):
        """Test adding a note to a repository."""
        # Insert a repository
        db.insert_or_update_repo(self.sample_repo)

        # Add a note
        new_note = "New test note"
        db.add_note(self.sample_repo["id"], new_note)

        # Verify the note was added
        repo = db.get_repository(self.sample_repo["id"])
        self.assertIn(new_note, repo["notes"])

        # The original note should still be there
        self.assertIn("Test notes", repo["notes"])

    def test_get_repository(self):
        """Test getting a repository by ID."""
        # Insert a repository
        db.insert_or_update_repo(self.sample_repo)

        # Get the repository
        repo = db.get_repository(self.sample_repo["id"])

        # Verify the repository was retrieved correctly
        self.assertIsNotNone(repo)
        self.assertEqual(repo["id"], self.sample_repo["id"])
        self.assertEqual(repo["name"], self.sample_repo["name"])

        # Test getting a non-existent repository
        repo = db.get_repository("nonexistent/repo")
        self.assertIsNone(repo)

    def test_list_all_repositories(self):
        """Test listing all repositories."""
        # Insert two repositories
        db.insert_or_update_repo(self.sample_repo)

        second_repo = self.sample_repo.copy()
        second_repo["id"] = "test/repo2"
        second_repo["name"] = "Test Repository 2"
        db.insert_or_update_repo(second_repo)

        # List all repositories
        repos = db.list_all_repositories()

        # Verify both repositories are in the list
        self.assertEqual(len(repos), 2)
        repo_ids = [repo["id"] for repo in repos]
        self.assertIn(self.sample_repo["id"], repo_ids)
        self.assertIn(second_repo["id"], repo_ids)

    def test_update_repository_metadata(self):
        """Test updating repository metadata (tags and notes)."""
        # Insert a repository
        db.insert_or_update_repo(self.sample_repo)

        # Update metadata
        new_tags = "tag1, tag2, tag3"
        new_notes = "Updated notes for testing"
        success = db.update_repository_metadata(self.sample_repo["id"], new_tags, new_notes)

        # Verify the update was successful
        self.assertTrue(success)

        # Verify the metadata was updated
        repo = db.get_repository(self.sample_repo["id"])
        self.assertEqual(repo["tags"], new_tags)
        self.assertEqual(repo["notes"], new_notes)

        # Test updating a non-existent repository
        success = db.update_repository_metadata("nonexistent/repo", new_tags, new_notes)
        self.assertFalse(success)

    def test_delete_repository(self):
        """Test deleting a repository."""
        # Insert a repository
        db.insert_or_update_repo(self.sample_repo)

        # Add some history
        db.insert_or_update_repo(self.updated_repo)

        # Delete the repository
        success = db.delete_repository(self.sample_repo["id"])

        # Verify the deletion was successful
        self.assertTrue(success)

        # Verify the repository is gone
        repo = db.get_repository(self.sample_repo["id"])
        self.assertIsNone(repo)

        # Verify the history is gone
        history = db.get_repository_history(self.sample_repo["id"])
        self.assertEqual(len(history), 0)

        # Test deleting a non-existent repository
        success = db.delete_repository("nonexistent/repo")
        self.assertFalse(success)

    def test_get_connection_context_manager(self):
        """Test that the get_connection context manager works correctly."""
        # Use the context manager
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            self.assertEqual(result[0], 1)

        # The connection should be closed after the context manager exits
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")


class TestDatabaseWithMocks(unittest.TestCase):
    """Test cases using mocks to avoid actual database operations."""

    def setUp(self):
        """Set up mocks for testing."""
        # Mock the get_connection function
        self.conn_patcher = patch('nuggit.util.db.get_connection')
        self.mock_get_connection = self.conn_patcher.start()

        # Create mock connection and cursor
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.__enter__.return_value = self.mock_conn
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.mock_get_connection.return_value = self.mock_conn

        # Sample repository data for testing
        self.sample_repo = {
            "id": "test/repo",
            "name": "Test Repository",
            "description": "A test repository",
            "url": "https://github.com/test/repo",
            "topics": "test, sample",
            "license": "MIT",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-02T00:00:00",
            "stars": 10,
            "forks": 5,
            "issues": 2,
            "contributors": "3",
            "commits": 100,
            "last_commit": "2023-01-03T00:00:00",
            "tags": "test",
            "notes": "Test notes",
            "last_synced": datetime.utcnow().isoformat()
        }

    def tearDown(self):
        """Clean up after tests."""
        self.conn_patcher.stop()

    def test_initialize_database_with_mock(self):
        """Test initialize_database with mocks."""
        db.initialize_database()

        # Verify the cursor.execute was called with the correct SQL
        self.assertEqual(self.mock_cursor.execute.call_count, 2)
        create_repositories_call = self.mock_cursor.execute.call_args_list[0][0][0]
        create_history_call = self.mock_cursor.execute.call_args_list[1][0][0]

        self.assertIn("CREATE TABLE IF NOT EXISTS repositories", create_repositories_call)
        self.assertIn("CREATE TABLE IF NOT EXISTS repository_history", create_history_call)

    def test_insert_or_update_repo_with_mock(self):
        """Test insert_or_update_repo with mocks."""
        # Mock cursor.fetchone to return None (no existing repo)
        self.mock_cursor.fetchone.return_value = None

        # Call the function
        db.insert_or_update_repo(self.sample_repo)

        # Verify the cursor.execute was called with the correct SQL
        self.assertGreaterEqual(self.mock_cursor.execute.call_count, 2)

        # Check the SELECT query
        select_call = self.mock_cursor.execute.call_args_list[0][0]
        self.assertIn("SELECT * FROM repositories WHERE id = ?", select_call[0])
        self.assertEqual(select_call[1], (self.sample_repo["id"],))

        # Check the INSERT query
        insert_call = self.mock_cursor.execute.call_args_list[1][0]
        self.assertIn("INSERT INTO repositories", insert_call[0])
        self.assertIn("ON CONFLICT(id) DO UPDATE SET", insert_call[0])

    def test_delete_repository_with_mock(self):
        """Test delete_repository with mocks."""
        # Mock cursor.rowcount to return 1 (one row affected)
        self.mock_cursor.rowcount = 1

        # Call the function
        result = db.delete_repository(self.sample_repo["id"])

        # Verify the result
        self.assertTrue(result)

        # Verify the cursor.execute was called with the correct SQL
        self.assertEqual(self.mock_cursor.execute.call_count, 2)

        # Check the DELETE from history query
        delete_history_call = self.mock_cursor.execute.call_args_list[0][0]
        self.assertIn("DELETE FROM repository_history WHERE repo_id = ?", delete_history_call[0])
        self.assertEqual(delete_history_call[1], (self.sample_repo["id"],))

        # Check the DELETE from repositories query
        delete_repo_call = self.mock_cursor.execute.call_args_list[1][0]
        self.assertIn("DELETE FROM repositories WHERE id = ?", delete_repo_call[0])
        self.assertEqual(delete_repo_call[1], (self.sample_repo["id"],))

        # Test when no rows are affected
        self.mock_cursor.rowcount = 0
        result = db.delete_repository("nonexistent/repo")
        self.assertFalse(result)

    def test_update_repository_metadata_with_mock(self):
        """Test update_repository_metadata with mocks."""
        # Mock cursor.rowcount to return 1 (one row affected)
        self.mock_cursor.rowcount = 1

        # Call the function
        new_tags = "tag1, tag2, tag3"
        new_notes = "Updated notes for testing"
        result = db.update_repository_metadata(self.sample_repo["id"], new_tags, new_notes)

        # Verify the result
        self.assertTrue(result)

        # Verify the cursor.execute was called with the correct SQL
        self.assertEqual(self.mock_cursor.execute.call_count, 1)

        # Check the UPDATE query
        update_call = self.mock_cursor.execute.call_args[0]
        self.assertIn("UPDATE repositories SET tags = ?, notes = ? WHERE id = ?", update_call[0])
        self.assertEqual(update_call[1], (new_tags, new_notes, self.sample_repo["id"]))

        # Test when no rows are affected
        self.mock_cursor.rowcount = 0
        result = db.update_repository_metadata("nonexistent/repo", new_tags, new_notes)
        self.assertFalse(result)

    def test_tag_repository_with_mock(self):
        """Test tag_repository with mocks."""
        # Call the function
        new_tag = "new-tag"
        db.tag_repository(self.sample_repo["id"], new_tag)

        # Verify the cursor.execute was called with the correct SQL
        self.assertEqual(self.mock_cursor.execute.call_count, 1)

        # Check the UPDATE query
        update_call = self.mock_cursor.execute.call_args[0]
        self.assertIn("UPDATE repositories", update_call[0])
        self.assertIn("SET tags = COALESCE(tags || ',', '') || ?", update_call[0])
        self.assertIn("WHERE id = ?", update_call[0])
        self.assertEqual(update_call[1], (new_tag, self.sample_repo["id"]))

    def test_add_note_with_mock(self):
        """Test add_note with mocks."""
        # Call the function
        new_note = "New test note"
        db.add_note(self.sample_repo["id"], new_note)

        # Verify the cursor.execute was called with the correct SQL
        self.assertEqual(self.mock_cursor.execute.call_count, 1)

        # Check the UPDATE query
        update_call = self.mock_cursor.execute.call_args[0]
        self.assertIn("UPDATE repositories", update_call[0])
        self.assertIn("SET notes = COALESCE(notes || '\n', '') || ?", update_call[0])
        self.assertIn("WHERE id = ?", update_call[0])
        self.assertEqual(update_call[1], (new_note, self.sample_repo["id"]))

    def test_get_repository_with_mock(self):
        """Test get_repository with mocks."""
        # Mock cursor.fetchone to return a row
        mock_row = ("test/repo", "Test Repository", "A test repository")
        self.mock_cursor.fetchone.return_value = mock_row

        # Mock cursor.description to return column descriptions
        mock_description = [("id",), ("name",), ("description",)]
        self.mock_cursor.description = mock_description

        # Call the function
        repo = db.get_repository(self.sample_repo["id"])

        # Verify the cursor.execute was called with the correct SQL
        self.assertEqual(self.mock_cursor.execute.call_count, 1)

        # Check the SELECT query
        select_call = self.mock_cursor.execute.call_args[0]
        self.assertIn("SELECT * FROM repositories WHERE id = ?", select_call[0])
        self.assertEqual(select_call[1], (self.sample_repo["id"],))

        # Verify the result
        self.assertIsNotNone(repo)
        self.assertEqual(repo["id"], "test/repo")
        self.assertEqual(repo["name"], "Test Repository")
        self.assertEqual(repo["description"], "A test repository")

        # Test when no row is found
        self.mock_cursor.fetchone.return_value = None
        repo = db.get_repository("nonexistent/repo")
        self.assertIsNone(repo)

    def test_list_all_repositories_with_mock(self):
        """Test list_all_repositories with mocks."""
        # Mock cursor.fetchall to return rows
        mock_rows = [
            ("test/repo1", "Test Repository 1", "A test repository 1"),
            ("test/repo2", "Test Repository 2", "A test repository 2")
        ]
        self.mock_cursor.fetchall.return_value = mock_rows

        # Mock cursor.description to return column descriptions
        mock_description = [("id",), ("name",), ("description",)]
        self.mock_cursor.description = mock_description

        # Call the function
        repos = db.list_all_repositories()

        # Verify the cursor.execute was called with the correct SQL
        self.assertEqual(self.mock_cursor.execute.call_count, 1)

        # Check the SELECT query
        select_call = self.mock_cursor.execute.call_args[0]
        self.assertIn("SELECT * FROM repositories", select_call[0])

        # Verify the result
        self.assertEqual(len(repos), 2)
        self.assertEqual(repos[0]["id"], "test/repo1")
        self.assertEqual(repos[0]["name"], "Test Repository 1")
        self.assertEqual(repos[1]["id"], "test/repo2")
        self.assertEqual(repos[1]["name"], "Test Repository 2")

    def test_get_repository_history_with_mock(self):
        """Test get_repository_history with mocks."""
        # Mock cursor.fetchall to return rows
        mock_rows = [
            ("stars", "10", "15", "2023-01-04T00:00:00"),
            ("forks", "5", "7", "2023-01-04T00:00:00")
        ]
        self.mock_cursor.fetchall.return_value = mock_rows

        # Mock cursor.description to return column descriptions
        mock_description = [("field",), ("old_value",), ("new_value",), ("changed_at",)]
        self.mock_cursor.description = mock_description

        # Call the function
        history = db.get_repository_history(self.sample_repo["id"])

        # Verify the cursor.execute was called with the correct SQL
        self.assertEqual(self.mock_cursor.execute.call_count, 1)

        # Check the SELECT query
        select_call = self.mock_cursor.execute.call_args[0]
        self.assertIn("SELECT field, old_value, new_value, changed_at", select_call[0])
        self.assertIn("FROM repository_history", select_call[0])
        self.assertIn("WHERE repo_id = ?", select_call[0])
        self.assertIn("ORDER BY changed_at DESC", select_call[0])
        self.assertEqual(select_call[1], (self.sample_repo["id"],))

        # Verify the result
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["field"], "stars")
        self.assertEqual(history[0]["old_value"], "10")
        self.assertEqual(history[0]["new_value"], "15")
        self.assertEqual(history[1]["field"], "forks")
        self.assertEqual(history[1]["old_value"], "5")
        self.assertEqual(history[1]["new_value"], "7")


if __name__ == "__main__":
    unittest.main()
