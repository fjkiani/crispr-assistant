#!/usr/bin/env python3
"""
Test runner for the AI Research Assistant streamlit application.
Run this script to verify that the application is working correctly.
"""

import os
import sys
import unittest
import subprocess
import argparse

def run_tests(test_type="all", verbose=False):
    """Run the specified tests and return True if all tests pass"""
    print("Running tests for AI Research Assistant")
    print("======================================")
    
    # Create tests directory if it doesn't exist
    os.makedirs('tests', exist_ok=True)
    
    # Create __init__.py if it doesn't exist
    init_file = os.path.join('tests', '__init__.py')
    if not os.path.exists(init_file):
        with open(init_file, 'w') as f:
            f.write("# Tests package\n")
    
    # Discover tests
    test_suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    
    if test_type in ["all", "unit"]:
        print("Discovering unit tests...")
        unit_tests = loader.discover('tests', pattern='test_*.py', top_level_dir='.')
        test_suite.addTests(unit_tests)
    
    if test_type in ["all", "integration"]:
        print("Discovering integration tests...")
        integration_tests = loader.discover('tests', pattern='test_integration.py', top_level_dir='.')
        test_suite.addTests(integration_tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(test_suite)
    
    # Check if Streamlit app can start
    if test_type in ["all", "app"]:
        print("\nTesting Streamlit app imports...")
        app_success = True
        try:
            # Just verify the imports work and basic init functions
            import streamlit_app
            print("Successfully imported streamlit_app.py")
        except Exception as e:
            print(f"Error importing Streamlit app: {str(e)}")
            app_success = False
            
    # Print summary
    print("\nTest Summary:")
    print(f"Ran {result.testsRun} tests")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    # Return success only if both unittest and app test (if run) succeeded
    success = len(result.failures) == 0 and len(result.errors) == 0
    if test_type in ["all", "app"]:
        success = success and app_success
        
    return success

def main():
    """Main function to parse arguments and run tests"""
    parser = argparse.ArgumentParser(description="Run tests for AI Research Assistant")
    parser.add_argument('--test-type', choices=['all', 'unit', 'integration', 'app'], 
                      default='all', help='Type of tests to run')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    success = run_tests(args.test_type, args.verbose)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 