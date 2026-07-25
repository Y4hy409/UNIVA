"""
CLARIUS Backend - Central Test Runner

This script discovers and executes all automated backend test suites (P0.3).
Returns exit code 0 on success, or 1 on failure.
"""

import sys
import unittest
from pathlib import Path

def main():
    print("============================================================")
    print("CLARIUS AUTOMATED TEST INFRASTRUCTURE RUNNER")
    print("============================================================")
    
    # Define search start directory
    start_dir = str(Path(__file__).parent)
    
    # Discover all tests matching pattern test_*.py
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir, pattern="test_*.py")
    
    # Execute test suite
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n============================================================")
    print("TEST EXECUTION SUMMARY")
    print(f"Tests run: {result.testsRun}")
    print(f"Errors: {len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print("============================================================")
    
    if not result.wasSuccessful():
        print("FAIL: Some tests failed!")
        sys.exit(1)
    else:
        print("SUCCESS: All tests completed successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()
