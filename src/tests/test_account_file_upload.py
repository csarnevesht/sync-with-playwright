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
from playwright.sync_api import Page, expect, sync_playwright
import re
import json
from datetime import datetime
import shutil
import tempfile
from src.sync.salesforce_client.utils.file_upload import upload_account_file_with_retries, upload_account_files, upload_account_file
from src.sync.salesforce_client.pages.account_manager import AccountManager
from src.sync.salesforce_client.utils.browser import get_salesforce_page
from src.sync.salesforce_client.utils.mock_data import get_mock_accounts
from src.sync.salesforce_client.pages.file_manager import SalesforceFileManager
from src.config import *

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Global view name for all operations
VIEW_NAME = "FinServ__My_Clients"

def test_account_file_upload(browser, page):
    """
    Test uploading files to an account.
    
    Args:
        browser: Playwright browser instance
        page: Playwright page instance
    """
    try:
        # Initialize managers
        account_manager = AccountManager(page, debug_mode=True)
        file_manager = SalesforceFileManager(page, debug_mode=True)
        
        # Search for account
        account_name = "John Smith"
        
        # Check if account exists and store result
        if not account_manager.account_exists(account_name, view_name=VIEW_NAME):
            logging.info(f"Account {account_name} does not exist, creating it...")
            account_manager.create_new_account(
                first_name=account_name.split(' ')[0],
                last_name=account_name.split(' ')[1],
                middle_name=None,
                account_info={}
            )
        
        # Click on account name to navigate to it
        if not account_manager.click_account_name(account_name):
            logging.error(f"Failed to navigate to account view page for: {account_name}")
            return
        
        # Verify we're on the correct account page and get account ID
        is_valid, account_id = account_manager.verify_account_page_url()
        if not is_valid or not account_id:
            logging.error("Not on a valid account page or could not get account ID")
            return
        
        logging.info(f"Successfully navigated to account {account_name} with ID {account_id}")
        
        # Navigate to files section
        logging.info("Navigating to files section")
        num_files = file_manager.navigate_to_account_files_click_on_files_card_to_facilitate_file_operation()
        if num_files == -1:
            logging.error("Failed to navigate to Files")
            return
        
        # Upload test file
        test_file_path = "test_files/abc.pdf"
        if not os.path.exists(test_file_path):
            os.makedirs("test_files", exist_ok=True)
            with open(test_file_path, "w") as f:
                f.write("Test file content")
        
        logging.info(f"Uploading file: {test_file_path}")
        upload_success = upload_account_file_with_retries(page, test_file_path, expected_items=num_files+1)
        
        if not upload_success:
            logging.error("Failed to upload file")
            raise Exception("Failed to upload file")
        
        logging.info("File upload successful")
        
    except Exception as e:
        logging.error(f"Test failed: {str(e)}")
        raise

def main():
    """Main function to run the test."""
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            test_account_file_upload(browser, page)
        finally:
            browser.close()

if __name__ == "__main__":
    main() 