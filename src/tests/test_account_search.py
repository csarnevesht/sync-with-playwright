"""
Test Account Search and File Verification

This test verifies the account search functionality and file verification in Salesforce. It:
1. Searches for a specific account by name
2. Creates the account if it doesn't exist (using mock data)
3. Navigates to the account's files
4. Verifies the number of files matches the expected count
5. Ensures proper navigation between account and files pages

The test includes robust file loading with incremental scrolling to handle large file lists
and retry logic for file uploads when creating new accounts.
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Optional
import pytest
from playwright.sync_api import Page, expect, Browser, sync_playwright
import re
import json
from datetime import datetime
import shutil
import tempfile
from sync.salesforce_client.pages.account_manager import AccountManager
from sync.salesforce_client.pages.file_manager import SalesforceFileManager
from sync.salesforce_client.utils.browser import get_salesforce_page
from sync.salesforce_client.utils.file_upload import upload_account_files
from sync.salesforce_client.utils.mock_data import get_mock_accounts
from src.config import *

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Global view name for all operations
VIEW_NAME = 'FinServ__My_Clients'

def test_search_account(browser: Browser, page: Page):
    """
    Test searching for an account by name and verifying its files.
    
    Args:
        browser: Playwright browser instance
        page: Playwright page instance
    """
    try:
        # Get mock account data
        mock_accounts = get_mock_accounts()
        
        # Find a mock account with files
        account = next((a for a in mock_accounts if a.get('files')), None)
        if not account:
            logging.error("No suitable mock account found for test_search_account")
            return
            
        account_name = f"{account['first_name']} {account['last_name']}"
        expected_files = len(account['files'])
        
        # Initialize managers
        account_manager = AccountManager(page, debug_mode=True)
        file_manager = SalesforceFileManager(page, debug_mode=True)
        
        # Check if account exists and get search result
        account_exists = account_manager.account_exists(account_name, view_name=VIEW_NAME)
        
        # Ensure the account exists (create if not)
        just_created = False
        if not account_exists:
            logging.info(f"Account {account_name} does not exist, creating it...")
            # Use mock data for creation
            mock = next((a for a in mock_accounts if f"{a['first_name']} {a['last_name']}" == account_name), None)
            if not mock:
                logging.error(f"No mock data found for {account_name}")
                return
                
            created = account_manager.create_new_account(
                first_name=mock['first_name'],
                last_name=mock['last_name'],
                middle_name=mock.get('middle_name'),
                account_info=mock.get('account_info', {})
            )
            assert created, f"Failed to create account: {account_name}"
            logging.info(f"Account {account_name} created successfully")
            just_created = True
            
            # Verify account exists after creation
            account_exists = account_manager.account_exists(account_name, view_name=VIEW_NAME)
            assert account_exists, f"Account {account_name} does not exist after creation"
        else:
            logging.info(f"Account {account_name} already exists")
        
        # Navigate to account page
        if not account_manager.click_account_name(account_name):
            logging.error(f"Failed to navigate to account view page for: {account_name}")
            return
        
        # Verify we're on the correct account page
        is_valid, account_id = account_manager.verify_account_page_url()
        if not is_valid:
            logging.error("Not on a valid account page")
            return
        
        logging.info(f"Successfully navigated to account {account_name} with ID {account_id}")
        
        # If just created, upload files
        if just_created:
            mock = next((a for a in mock_accounts if f"{a['first_name']} {a['last_name']}" == account_name), None)
            if mock and mock.get('files'):
                logging.info(f"Uploading files for newly created account: {account_name}")
                upload_success = upload_account_files(page, mock, debug_mode=True)
                assert upload_success, f"Failed to upload files for account: {account_name}"
        
        # Navigate to files and get count
        logging.info(f"Navigating to files for account {account_name}")
        num_files = account_manager.navigate_to_account_files_and_get_number_of_files(account_id)
        
        if num_files == -1:
            logging.error("Failed to navigate to files page")
            return
        
        logging.info(f"Final file count: {num_files}")
        
        # Handle both integer and string (e.g., "50+") file counts
        if isinstance(num_files, str):
            assert num_files == "50+" or int(num_files.rstrip('+')) >= expected_files, \
                f"Expected at least {expected_files} files, but found {num_files}"
        else:
            assert num_files == expected_files, \
                f"Expected {expected_files} files, but found {num_files}"
        
        # Navigate back to account page
        account_manager.navigate_back_to_account_page()
        
        # Verify we're back on the account page
        is_valid, _ = account_manager.verify_account_page_url()
        assert is_valid, "Failed to navigate back to account page"
        
        logging.info("Test completed successfully")
        
    except Exception as e:
        logging.error(f"Test failed: {str(e)}")
        page.screenshot(path="test-failure.png")
        raise

def main():
    """Run the test with the first mock account that has files."""
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            test_search_account(browser, page)
        finally:
            browser.close()

if __name__ == "__main__":
    main() 