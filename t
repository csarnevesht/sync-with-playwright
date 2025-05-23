#!/usr/bin/env python3

import os
import sys
import pytest
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    # Get the directory containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Add the script directory to Python path
    sys.path.insert(0, script_dir)
    
    # Get the tests directory
    tests_dir = os.path.join(script_dir, 'tests')
    
    # Run pytest with the tests directory
    args = [
        tests_dir,
        '-v',  # verbose output
        '--capture=no',  # show print statements
    ]
    
    # Add any command line arguments passed to this script
    args.extend(sys.argv[1:])
    
    # Run the tests
    return pytest.main(args)

if __name__ == '__main__':
    sys.exit(main()) 