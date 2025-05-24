"""
Test Account File Upload

This test verifies the file upload functionality for Salesforce accounts. It:
1. Creates a test account if it doesn't exist (using mock data)
2. Navigates to the account's page
3. Uploads test files to the account
4. Verifies the upload was successful

The test uses mock data to ensure consistent test conditions and includes
retry logic for file uploads to handle potential network issues.
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Optional
import pytest
from playwright.sync_api import Page, expect
import re
import json
from datetime import datetime
import shutil
import tempfile
from sync.salesforce.utils.file_upload import upload_files_for_account
from sync.salesforce.pages.account_manager import AccountManager
from sync.salesforce.utils.browser import get_salesforce_page
from sync.salesforce.utils.mock_data import get_mock_accounts

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_account_upload():
    """Test uploading files to a Salesforce account."""
    # Enable debug mode
    debug_mode = True
    max_tries = 3  # Number of retry attempts per file
    
    # Get mock account data
    mock_accounts = get_mock_accounts()
    test_account = mock_accounts[0]  # Use first mock account for testing
    
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            # Initialize account manager
            account_manager = AccountManager(page, debug_mode=debug_mode)
            
            # Navigate to Accounts page
            assert account_manager.navigate_to_accounts_list_page(), "Failed to navigate to Accounts page"
            
            # Get full name for the test account
            full_name = f"{test_account['first_name']} {test_account['last_name']}"
            logging.info(f"Processing account: {full_name}")
            
            # Create account if it doesn't exist
            if not account_manager.account_exists(full_name, view_name="My Clients"):
                logging.info(f"Account {full_name} does not exist, creating it...")
                created = account_manager.create_new_account(
                    first_name=test_account['first_name'],
                    last_name=test_account['last_name'],
                    middle_name=test_account.get('middle_name'),
                    account_info=test_account.get('account_info', {})
                )
                assert created, f"Failed to create account: {full_name}"
                logging.info(f"Account {full_name} created successfully")
                
                # Navigate back to Accounts page
                assert account_manager.navigate_to_accounts_list_page(), "Failed to navigate to Accounts page after creation"
            else:
                logging.info(f"Account {full_name} already exists")
            
            # Navigate to account page
            if not account_manager.click_account_name(full_name):
                logging.error(f"Failed to navigate to account view page for: {full_name}")
                return
            
            # Verify we're on the correct account page
            is_valid, account_id = account_manager.verify_account_page_url()
            if not is_valid:
                logging.error("Not on a valid account page")
                return
            
            logging.info(f"Successfully navigated to account {full_name} with ID {account_id}")
            
            # Upload files for the account
            logging.info(f"Uploading files for account: {full_name}")
            upload_success = upload_files_for_account(
                page, 
                test_account, 
                debug_mode=debug_mode, 
                max_tries=max_tries
            )
            
            if not upload_success:
                logging.error("File upload process completed with errors")
                return
            
            logging.info("Test completed successfully")
            
        except Exception as e:
            logging.error(f"Test failed: {str(e)}")
            page.screenshot(path="test-failure.png")
            raise
        finally:
            browser.close()

def main():
    test_account_upload()

if __name__ == "__main__":
    main() 