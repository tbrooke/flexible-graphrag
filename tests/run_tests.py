#!/usr/bin/env python3
"""
Test runner for Flexible-GraphRAG
"""

import sys
import subprocess
import os
from pathlib import Path

def run_tests():
    """Run all tests in the tests directory"""
    
    # Get the tests directory
    tests_dir = Path(__file__).parent
    
    print("Running Flexible-GraphRAG tests...")
    print(f"Tests directory: {tests_dir}")
    
    # Run pytest with verbose output
    cmd = [
        sys.executable, "-m", "pytest",
        str(tests_dir),
        "-v",
        "--tb=short"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

def run_bm25_tests():
    """Run only BM25 related tests"""
    
    tests_dir = Path(__file__).parent
    
    print("Running BM25 tests...")
    
    cmd = [
        sys.executable, "-m", "pytest",
        str(tests_dir),
        "-m", "bm25",
        "-v",
        "--tb=short"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode
    except Exception as e:
        print(f"Error running BM25 tests: {e}")
        return 1

def run_integration_tests():
    """Run only integration tests"""
    
    tests_dir = Path(__file__).parent
    
    print("Running integration tests...")
    
    cmd = [
        sys.executable, "-m", "pytest",
        str(tests_dir),
        "-m", "integration",
        "-v",
        "--tb=short"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode
    except Exception as e:
        print(f"Error running integration tests: {e}")
        return 1

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Flexible-GraphRAG tests")
    parser.add_argument("--bm25-only", action="store_true", help="Run only BM25 tests")
    parser.add_argument("--integration-only", action="store_true", help="Run only integration tests")
    
    args = parser.parse_args()
    
    if args.bm25_only:
        exit_code = run_bm25_tests()
    elif args.integration_only:
        exit_code = run_integration_tests()
    else:
        exit_code = run_tests()
    
    sys.exit(exit_code) 