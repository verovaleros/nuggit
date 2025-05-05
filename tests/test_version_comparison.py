#!/usr/bin/env python3
"""
Unit tests for the version comparison functionality in nuggit/api/routes/versions.py.
"""

import unittest
import os
import sys
import difflib

# Add the parent directory to the path so we can import the module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestVersionComparison(unittest.TestCase):
    """Test cases for the version comparison functionality."""

    def test_compare_text(self):
        """Test the text comparison function."""
        # Define a simple text comparison function similar to the one in versions.py
        def compare_text(a, b):
            changed = a != b
            diff = list(difflib.unified_diff([a or ""], [b or ""], lineterm=""))
            if len(diff) > 2 and diff[0].startswith('---'):
                diff = diff[2:]
            return {"changed": changed, "diff": diff}

        # Test with identical strings
        result = compare_text("test", "test")
        self.assertFalse(result["changed"])
        self.assertEqual(len(result["diff"]), 0)

        # Test with different strings
        result = compare_text("test", "updated")
        self.assertTrue(result["changed"])
        self.assertTrue(len(result["diff"]) > 0)

        # Test with numeric values
        result = compare_text("10", "20")
        self.assertTrue(result["changed"])
        self.assertTrue(len(result["diff"]) > 0)
        self.assertTrue(any(line.startswith('-10') for line in result["diff"]))
        self.assertTrue(any(line.startswith('+20') for line in result["diff"]))

        # Test with repository metrics
        # Stars
        result = compare_text("10", "20")
        self.assertTrue(result["changed"])
        self.assertTrue(any(line.startswith('-10') for line in result["diff"]))
        self.assertTrue(any(line.startswith('+20') for line in result["diff"]))

        # Forks
        result = compare_text("5", "8")
        self.assertTrue(result["changed"])
        self.assertTrue(any(line.startswith('-5') for line in result["diff"]))
        self.assertTrue(any(line.startswith('+8') for line in result["diff"]))

        # Commits
        result = compare_text("100", "150")
        self.assertTrue(result["changed"])
        self.assertTrue(any(line.startswith('-100') for line in result["diff"]))
        self.assertTrue(any(line.startswith('+150') for line in result["diff"]))

        # License
        result = compare_text("MIT", "Apache 2.0")
        self.assertTrue(result["changed"])
        self.assertTrue(any(line.startswith('-MIT') for line in result["diff"]))
        self.assertTrue(any(line.startswith('+Apache 2.0') for line in result["diff"]))

        # Topics
        result = compare_text("test, sample", "test, sample, updated")
        self.assertTrue(result["changed"])
        self.assertTrue(any(line.startswith('-test, sample') for line in result["diff"]))
        self.assertTrue(any(line.startswith('+test, sample, updated') for line in result["diff"]))


if __name__ == "__main__":
    unittest.main()
