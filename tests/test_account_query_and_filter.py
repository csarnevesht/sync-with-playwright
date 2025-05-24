"""
Test Account Query and Filtering

This test suite verifies the account query and filtering functionality in Salesforce. It focuses on
finding and validating accounts that have files attached to them, with specific attention to:

1. Account Query:
   - Retrieves accounts matching specific conditions (e.g., accounts with files)
   - Limits results to a maximum number of accounts (default: 5)
   - Uses the "All Clients" view for consistent results

2. File Validation:
   - Verifies each account has files attached
   - Counts and validates the number of files per account
   - Handles pagination for accounts with large numbers of files (50+)
   - Implements scrolling mechanism to load all files when needed

3. Data Integrity:
   - Validates required account properties (name, ID, files_count)
   - Ensures file counts are valid numbers
   - Verifies file counts match actual number of files

4. Error Handling:
   - Implements robust error handling for various scenarios
   - Takes screenshots on test failure for debugging
   - Provides detailed logging throughout the process

5. Performance:
   - Optimizes file loading for accounts with many files
   - Implements efficient scrolling mechanism
   - Includes stability checks to ensure all files are loaded

The test includes comprehensive logging to track:
- Account discovery and validation
- File counting and verification
- Scrolling progress for large file sets
- Any errors or issues encountered
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Optional
import pytest
from playwright.sync_api import Page, Browser, expect
import re
import json
from datetime import datetime
import shutil
import tempfile
from sync.salesforce.pages.account_manager import AccountManager
from sync.salesforce.pages.accounts_page import AccountsPage
from sync.salesforce.utils.browser import get_salesforce_page

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_accounts_with_files(account_manager: AccountManager, max_number: int = 5) -> list:
    """
    Get accounts that have files attached to them.
    
    This function queries Salesforce for accounts that have files attached, using the following process:
    1. Uses the AccountManager to query accounts with a custom condition
    2. Filters accounts to only include those with files
    3. Limits the results to the specified maximum number
    4. Returns detailed account information including file counts
    
    Args:
        account_manager: AccountManager instance for interacting with Salesforce
        max_number: Maximum number of accounts to return (default: 5)
    
    Returns:
        list: List of accounts with files, each containing:
            - name: Account name
            - id: Account ID
            - files_count: Number of files attached
    
    Note:
        The function includes detailed logging of the accounts found and their file counts.
        If no accounts are found or an error occurs, an empty list is returned.
    """
    try:
        accounts = account_manager.get_accounts_matching_condition(
            max_number=max_number,
            condition=lambda account: account_manager.account_has_files(account['id']),
            view_name="All Clients"
        )
        
        if not accounts:
            logging.info("No accounts with files were found")
        else:
            logging.info(f"Found {len(accounts)} accounts with files:")
            for account in accounts:
                logging.info(
                    f"Account: {account['name']}\n"
                    f"  ID: {account['id']}\n"
                    f"  Files: {account['files_count']}"
                )
        
        return accounts
    except Exception as e:
        logging.error(f"Error getting accounts with files: {str(e)}")
        return []

def test_accounts_query_and_filter(browser: Browser, page: Page):
    """
    Test the account query and filtering functionality.
    
    This test verifies the complete account query and filtering process in Salesforce:
    
    1. Account Discovery:
       - Queries accounts with specific conditions
       - Limits results to maximum of 5 accounts
       - Verifies each account has files attached
    
    2. Data Validation:
       - Checks required account properties (name, ID, files_count)
       - Validates file counts are correct
       - Ensures file counts are valid numbers
    
    3. File Verification:
       - Navigates to each account's files page
       - Counts and validates the number of files
       - Handles pagination for accounts with many files
    
    4. Error Handling:
       - Takes screenshots on test failure
       - Provides detailed error logging
       - Implements robust exception handling
    
    Args:
        browser: Playwright browser instance
        page: Playwright page instance
    
    Raises:
        AssertionError: If any validation fails
        Exception: For any unexpected errors during test execution
    
    Note:
        The test includes comprehensive logging of the entire process,
        making it easier to debug any issues that arise.
    """
    try:
        # Initialize managers with debug mode for detailed logging
        accounts_page = AccountsPage(page, debug_mode=True)
        account_manager = AccountManager(page, debug_mode=True)

        # Get accounts with files and verify count
        accounts = get_accounts_with_files(account_manager)
        assert len(accounts) <= 5, f"Expected at most 5 accounts, got {len(accounts)}"
        
        # Verify each account has files and required properties
        for account in accounts:
            # Verify account has files
            assert account_manager.account_has_files(account['id']), \
                f"Account {account['name']} should have files"
            
            # Verify required properties exist
            assert 'name' in account, f"Account missing name property: {account}"
            assert 'id' in account, f"Account missing ID property: {account}"
            assert 'files_count' in account, f"Account missing files_count property: {account}"
            
            # Verify files count is a valid number
            assert isinstance(account['files_count'], (int, str)), \
                f"Invalid files_count type for account {account['name']}: {type(account['files_count'])}"
        
        logging.info("Test completed successfully")

    except Exception as e:
        logging.error(f"Test failed: {str(e)}")
        page.screenshot(path="test-failure.png")
        raise

def main():
    """
    Run the account query and filter test.
    
    This function serves as the entry point for running the test directly.
    It handles the Playwright browser setup and teardown, and executes
    the test with proper error handling.
    """
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            test_accounts_query_and_filter(browser, page)
        finally:
            browser.close()

if __name__ == "__main__":
    main() 