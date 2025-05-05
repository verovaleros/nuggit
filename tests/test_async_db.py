#!/usr/bin/env python3
"""
Unit tests for the nuggit/util/async_db.py module.
"""

import unittest
import os
import sys
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add the parent directory to the path so we can import the module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the modules to test
from nuggit.util.async_db import (
    get_repository,
    update_repository_metadata,
    add_comment,
    get_comments,
    get_versions,
)


class TestAsyncDB(unittest.TestCase):
    """Test cases for the async_db module."""

    def setUp(self):
        """Set up test fixtures."""
        # Sample repository data for testing
        self.repo_id = "test/repo"
        self.sample_repo = {
            "id": self.repo_id,
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
        
        # Sample comments for testing
        self.sample_comments = [
            {
                "id": 1,
                "comment": "Test comment 1",
                "author": "Test Author 1",
                "created_at": "2023-01-01T00:00:00"
            },
            {
                "id": 2,
                "comment": "Test comment 2",
                "author": "Test Author 2",
                "created_at": "2023-01-02T00:00:00"
            }
        ]
        
        # Sample versions for testing
        self.sample_versions = [
            {
                "id": 1,
                "version_number": "1.0.0",
                "release_date": "2023-01-01",
                "description": "Test version 1",
                "created_at": "2023-01-01T00:00:00"
            },
            {
                "id": 2,
                "version_number": "2.0.0",
                "release_date": "2023-02-01",
                "description": "Test version 2",
                "created_at": "2023-02-01T00:00:00"
            }
        ]

    @patch('nuggit.util.async_db.sync_get_repository')
    def test_get_repository(self, mock_sync_get_repository):
        """Test the async get_repository function."""
        # Set up the mock
        mock_sync_get_repository.return_value = self.sample_repo
        
        # Run the async function
        result = asyncio.run(get_repository(self.repo_id))
        
        # Verify the result
        self.assertEqual(result, self.sample_repo)
        mock_sync_get_repository.assert_called_once_with(self.repo_id)

    @patch('nuggit.util.async_db.sync_update_repository_metadata')
    def test_update_repository_metadata(self, mock_sync_update_repository_metadata):
        """Test the async update_repository_metadata function."""
        # Set up the mock
        mock_sync_update_repository_metadata.return_value = True
        
        # Run the async function
        tags = "test, sample"
        notes = "Test notes"
        result = asyncio.run(update_repository_metadata(self.repo_id, tags, notes))
        
        # Verify the result
        self.assertTrue(result)
        mock_sync_update_repository_metadata.assert_called_once_with(self.repo_id, tags, notes)

    @patch('nuggit.util.async_db.sync_add_comment')
    def test_add_comment(self, mock_sync_add_comment):
        """Test the async add_comment function."""
        # Set up the mock
        mock_sync_add_comment.return_value = 1
        
        # Run the async function
        comment = "Test comment"
        author = "Test Author"
        result = asyncio.run(add_comment(self.repo_id, comment, author))
        
        # Verify the result
        self.assertEqual(result, 1)
        mock_sync_add_comment.assert_called_once_with(self.repo_id, comment, author)

    @patch('nuggit.util.async_db.sync_get_comments')
    def test_get_comments(self, mock_sync_get_comments):
        """Test the async get_comments function."""
        # Set up the mock
        mock_sync_get_comments.return_value = self.sample_comments
        
        # Run the async function
        result = asyncio.run(get_comments(self.repo_id))
        
        # Verify the result
        self.assertEqual(result, self.sample_comments)
        mock_sync_get_comments.assert_called_once_with(self.repo_id)

    @patch('nuggit.util.async_db.sync_get_versions')
    def test_get_versions(self, mock_sync_get_versions):
        """Test the async get_versions function."""
        # Set up the mock
        mock_sync_get_versions.return_value = self.sample_versions
        
        # Run the async function
        result = asyncio.run(get_versions(self.repo_id))
        
        # Verify the result
        self.assertEqual(result, self.sample_versions)
        mock_sync_get_versions.assert_called_once_with(self.repo_id)


if __name__ == '__main__':
    unittest.main()
