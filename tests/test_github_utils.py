import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add the parent directory to the path so we can import the module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nuggit.util.github import get_recent_commits


class TestGithubUtils(unittest.TestCase):
    
    def test_get_recent_commits_with_none_repo(self):
        """Test that get_recent_commits handles None repo gracefully"""
        result = get_recent_commits(None)
        self.assertEqual(result, [])
    
    def test_get_recent_commits_with_invalid_limit(self):
        """Test that get_recent_commits handles invalid limit values"""
        mock_repo = MagicMock()
        mock_repo.get_commits.return_value = []
        
        # Test with negative limit
        result = get_recent_commits(mock_repo, limit=-5)
        self.assertEqual(result, [])
        
        # Test with zero limit
        result = get_recent_commits(mock_repo, limit=0)
        self.assertEqual(result, [])
        
        # Test with non-integer limit
        result = get_recent_commits(mock_repo, limit="invalid")
        self.assertEqual(result, [])
    
    @patch('nuggit.util.github.logging')
    def test_get_recent_commits_with_github_exception(self, mock_logging):
        """Test that get_recent_commits handles GitHub exceptions"""
        from github.GithubException import GithubException
        
        mock_repo = MagicMock()
        mock_repo.get_commits.side_effect = GithubException(404, "Not Found")
        
        result = get_recent_commits(mock_repo)
        self.assertEqual(result, [])
        mock_logging.error.assert_called()
    
    def test_get_recent_commits_with_branch(self):
        """Test that get_recent_commits handles branch parameter"""
        mock_repo = MagicMock()
        mock_commits = MagicMock()
        mock_repo.get_commits.return_value = mock_commits
        
        # Create a mock commit
        mock_commit = MagicMock()
        mock_commit.sha = "abcdef1234567890"
        mock_commit.commit.author.name = "Test Author"
        mock_commit.commit.author.date.isoformat.return_value = "2023-01-01T00:00:00"
        mock_commit.commit.message = "Test commit message\nWith multiple lines"
        
        # Make the mock_commits iterable and return our mock_commit
        mock_commits.__iter__.return_value = [mock_commit]
        
        result = get_recent_commits(mock_repo, branch="main")
        
        # Verify the branch parameter was passed correctly
        mock_repo.get_commits.assert_called_with(sha="main")
        
        # Verify the result contains the expected data
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["sha"], "abcdef1")
        self.assertEqual(result[0]["author"], "Test Author")
        self.assertEqual(result[0]["message"], "Test commit message")
    
    def test_get_recent_commits_handles_missing_data(self):
        """Test that get_recent_commits handles missing data in commits"""
        mock_repo = MagicMock()
        mock_commits = MagicMock()
        mock_repo.get_commits.return_value = mock_commits
        
        # Create a mock commit with missing data
        mock_commit = MagicMock()
        mock_commit.sha = "abcdef1234567890"
        
        # Set commit.author to None to test fallbacks
        mock_commit.commit.author = None
        mock_commit.commit.message = None
        
        # Make the mock_commits iterable and return our mock_commit
        mock_commits.__iter__.return_value = [mock_commit]
        
        result = get_recent_commits(mock_repo)
        
        # Verify the result contains the expected fallback values
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["sha"], "abcdef1")
        self.assertEqual(result[0]["author"], "Unknown")
        self.assertEqual(result[0]["date"], "")
        self.assertEqual(result[0]["message"], "")


if __name__ == "__main__":
    unittest.main()
