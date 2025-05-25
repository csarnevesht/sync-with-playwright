"""
Test suite for Salesforce sync functionality.
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from playwright.sync_api import sync_playwright, Browser, Page

# Get the absolute path to the project root directory
project_root = os.path.dirname(os.path.abspath(__file__))

# Add the project root to Python path
sys.path.insert(0, project_root)

def configure_logging(debug_mode: bool):
    """Configure logging based on debug mode."""
    # Get the root logger
    root_logger = logging.getLogger()
    
    # Set root logger level
    root_logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    
    # Create file handler
    log_file = os.path.join(project_root, 'sync.log')
    file_handler = logging.FileHandler(log_file, mode='w')
    file_handler.setLevel(logging.DEBUG)  # Always log debug to file
    
    # Create formatters
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Configure specific module loggers
    modules = [
        'sync.salesforce_client.pages.file_manager',
        'sync.salesforce_client.pages.account_manager',
        'sync.salesforce_client.utils.file_upload',
        'tests.test_accounts_create'
    ]
    
    for module in modules:
        module_logger = logging.getLogger(module)
        module_logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
        module_logger.propagate = True
    
    # Log the debug status
    root_logger.debug("Debug logging enabled" if debug_mode else "Debug logging disabled")
    
    # Return the configured logger for this module
    return logging.getLogger(__name__)

def setup_test_environment() -> tuple[Path, Path]:
    """Set up the test environment by creating necessary directories."""
    # Create test directories in the project root
    test_dir = Path(project_root) / "test"
    test_dir.mkdir(exist_ok=True)
    
    # Create a timestamped directory for this test run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = test_dir / timestamp
    run_dir.mkdir(exist_ok=True)
    
    # Create subdirectories
    (run_dir / "accounts").mkdir(exist_ok=True)
    (run_dir / "files").mkdir(exist_ok=True)
    
    return test_dir, run_dir

def run_test(test_func, browser: Browser, page: Page, logger):
    """Run a test function with the provided browser and page objects."""
    try:
        logger.info(f"Starting test: {test_func.__name__}")
        test_func(browser, page)
        logger.info(f"Test completed successfully: {test_func.__name__}")
        return True
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Run Salesforce sync tests')
    parser.add_argument('--test', choices=[
        'all',
        'account-creation',
        'account-search',
        'file-upload',
        'account-deletion',
        'account-filter',
        'account-file-retrieval',
        'account-file-deletion'
    ], default='all', help='Specify which test to run')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Configure logging first, before any imports
    logger = configure_logging(args.debug)
    
    # Import test modules after logging is configured
    from sync.config import SALESFORCE_URL
    from sync.salesforce_client import Salesforce
    from sync.salesforce_client.utils.browser import get_salesforce_page
    
    # Import test modules
    from tests.test_account_creation import test_account_creation
    from tests.test_account_search import test_search_account
    from tests.test_account_file_upload import test_account_file_upload
    from tests.test_account_deletion import test_account_deletion
    from tests.test_account_filter import test_account_filter
    from tests.test_account_file_retrieval import test_account_file_retrieval
    from tests.test_account_file_deletion import test_account_file_deletion
    
    # Set up test environment
    test_dir, run_dir = setup_test_environment()
    
    # Initialize Playwright
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            # Run selected test(s)
            if args.test == 'all':
                tests = [
                    ('Account Creation', test_account_creation),
                    ('Account Search', test_search_account),
                    ('File Upload', test_account_file_upload),
                    ('Account Deletion', test_account_deletion),
                    ('Account Filter', test_account_filter),
                    ('Account File Retrieval', test_account_file_retrieval),
                    ('Account File Deletion', test_account_file_deletion)
                ]
            else:
                test_map = {
                    'account-creation': [('Account Creation', test_account_creation)],
                    'account-search': [('Account Search', test_search_account)],
                    'file-upload': [('File Upload', test_account_file_upload)],
                    'account-deletion': [('Account Deletion', test_account_deletion)],
                    'account-filter': [('Account Filter', test_account_filter)],
                    'account-file-retrieval': [('Account File Retrieval', test_account_file_retrieval)],
                    'account-file-deletion': [('Account File Deletion', test_account_file_deletion)]
                }
                tests = test_map[args.test]
            
            # Run tests
            for test_name, test_func in tests:
                logger.info(f"\nRunning {test_name} test...")
                start_time = time.time()
                success = run_test(test_func, browser, page, logger)
                duration = time.time() - start_time
                
                if success:
                    logger.info(f"{test_name} test passed in {duration:.2f} seconds")
                else:
                    logger.error(f"{test_name} test failed after {duration:.2f} seconds")
                    sys.exit(1)
        finally:
            browser.close()

if __name__ == '__main__':
    main() 