#!/usr/bin/env python3
"""
Script to run the database tests.
"""

import os
import sys
import unittest

# Add the parent directory to the path so we can import the tests
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_db import TestDatabase, TestDatabaseWithMocks

if __name__ == "__main__":
    # Create a test suite
    suite = unittest.TestSuite()
    
    # Add the test cases
    suite.addTest(unittest.makeSuite(TestDatabase))
    suite.addTest(unittest.makeSuite(TestDatabaseWithMocks))
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with non-zero status if there were failures
    sys.exit(not result.wasSuccessful())
