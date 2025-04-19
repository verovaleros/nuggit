#!/usr/bin/env python3
"""
Unit tests for the nuggit/api/routes/versions.py module.
"""

import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path so we can import the module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the modules to test
from nuggit.api.routes.versions import get_repository_at_version, compare_text
from nuggit.util.db import get_repository, get_repository_history


class TestVersions(unittest.TestCase):
    """Test cases for the versions module."""

    def setUp(self):
        """Set up test data."""
        # Sample repository data
        self.repo_id = "test/repo"
        self.version_timestamp = "2023-01-01T00:00:00"

        # Sample repository history
        self.sample_history = [
            {
                "field": "license",
                "old_value": "MIT",
                "new_value": "Apache 2.0",
                "changed_at": "2023-01-02T00:00:00"
            },
            {
                "field": "stars",
                "old_value": "10",
                "new_value": "20",
                "changed_at": "2023-01-02T00:00:00"
            },
            {
                "field": "topics",
                "old_value": "test, sample",
                "new_value": "test, sample, updated",
                "changed_at": "2023-01-02T00:00:00"
            },
            {
                "field": "commits",
                "old_value": "100",
                "new_value": "150",
                "changed_at": "2023-01-02T00:00:00"
            }
        ]

        # Sample repository data
        self.current_repo = {
            "id": self.repo_id,
            "name": "Test Repository",
            "description": "A test repository",
            "license": "Apache 2.0",
            "stars": 20,
            "topics": "test, sample, updated",
            "commits": 150
        }

    @patch('nuggit.api.routes.versions.get_repository')
    @patch('nuggit.api.routes.versions.get_repository_history')
    def test_get_repository_at_version(self, mock_get_history, mock_get_repo):
        """Test getting repository data at a specific version."""
        # Mock the get_repository function
        mock_get_repo.return_value = self.current_repo

        # Mock the get_repository_history function
        mock_get_history.return_value = self.sample_history

        # Call the function
        repo_at_version = get_repository_at_version(self.repo_id, self.version_timestamp)

        # Verify the repository data was retrieved correctly
        self.assertEqual(repo_at_version["id"], self.repo_id)
        self.assertEqual(repo_at_version["name"], "Test Repository")

        # Verify the fields were reverted to their old values
        self.assertEqual(repo_at_version["license"], "MIT")
        self.assertEqual(repo_at_version["stars"], "10")
        self.assertEqual(repo_at_version["topics"], "test, sample")
        self.assertEqual(repo_at_version["commits"], "100")

        # Test with a non-existent repository
        mock_get_repo.return_value = None
        repo_at_version = get_repository_at_version("nonexistent/repo", self.version_timestamp)
        self.assertEqual(repo_at_version, {})

        # Test with a timestamp after all changes
        mock_get_repo.return_value = self.current_repo
        repo_at_version = get_repository_at_version(self.repo_id, "2023-01-03T00:00:00")
        self.assertEqual(repo_at_version["license"], "Apache 2.0")
        self.assertEqual(repo_at_version["stars"], 20)

    def test_compare_text(self):
        """Test comparing text strings."""
        # Test with identical strings
        result = compare_text("test", "test")
        self.assertFalse(result["changed"])
        self.assertIsNone(result["diff"])

        # Test with different strings
        result = compare_text("test", "test updated")
        self.assertTrue(result["changed"])
        self.assertIsNotNone(result["diff"])

        # Test with None values
        result = compare_text(None, "test")
        self.assertTrue(result["changed"])
        self.assertIsNotNone(result["diff"])

        result = compare_text("test", None)
        self.assertTrue(result["changed"])
        self.assertIsNotNone(result["diff"])

        result = compare_text(None, None)
        self.assertFalse(result["changed"])
        self.assertIsNone(result["diff"])

        # Test with numeric values
        result = compare_text(10, 20)
        self.assertTrue(result["changed"])
        self.assertIsNotNone(result["diff"])

        # Test with multiline strings
        text1 = "line1\nline2\nline3"
        text2 = "line1\nline2 updated\nline3"
        result = compare_text(text1, text2)
        self.assertTrue(result["changed"])
        self.assertIsNotNone(result["diff"])


if __name__ == "__main__":
    unittest.main()
