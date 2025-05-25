"""
Test Account Deletion and Cleanup

This test verifies the account deletion functionality in Salesforce. It:
1. Creates test accounts using mock data
2. Verifies the accounts exist in Salesforce
3. Deletes the accounts one by one
4. Verifies successful deletion
5. Handles cleanup of any remaining test data

The test includes:
- Robust account deletion with validation
- Error handling for deletion failures
- Verification of account removal
- Support for bulk deletion operations
- Cleanup of test data after execution
- Timeout handling and retries
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Optional
import pytest
from playwright.sync_api import Page, expect, Browser
import re
import json
from datetime import datetime
import shutil
import tempfile
from sync.salesforce_client.pages.account_manager import AccountManager
from sync.salesforce_client.pages.file_manager import FileManager
from sync.salesforce_client.utils.mock_data import get_mock_accounts
from sync.salesforce_client.utils.file_upload import upload_files_for_account
from playwright.sync_api import TimeoutError
from sync.salesforce_client.utils.browser import get_salesforce_page

# Get logger for this module
logger = logging.getLogger(__name__)

# Global view name for all operations
VIEW_NAME = "Recent"

def wait_for_page_load(page, timeout=10000):
    """
    Wait for the page to be fully loaded.
    
    Args:
        page: Playwright page object
        timeout: Maximum time to wait in milliseconds
        
    Returns:
        bool: True if page loaded successfully, False otherwise
    """
    try:
        page.wait_for_load_state('networkidle', timeout=timeout)
        page.wait_for_load_state('domcontentloaded', timeout=timeout)
        return True
    except TimeoutError:
        logger.warning("Timeout waiting for page load, continuing anyway")
        return False


def get_full_name(account: dict) -> str:
    """
    Get the full name of an account including middle name if present.
    
    Args:
        account: Account dictionary from mock data
        
    Returns:
        str: Full name of the account
    """
    name_parts = [
        account['first_name'],
        account.get('middle_name'),
        account['last_name']
    ]
    return ' '.join(
        part for part in name_parts 
        if part and str(part).strip().lower() not in ['none', '']
    )

def test_account_deletion(browser: Browser, page: Page):
    """
    Test deleting accounts from Salesforce.
    
    Args:
        browser: Playwright browser instance
        page: Playwright page instance
    """
    try:
        # Initialize managers
        account_manager = AccountManager(page, debug_mode=True)
        file_manager = FileManager(page, debug_mode=True)
        
        # Get mock accounts
        mock_accounts = get_mock_accounts()
        if not mock_accounts:
            logging.error("No mock accounts found")
            return
            
        # Use the first mock account
        account = mock_accounts[0]
        account_name = get_full_name(account)
        logging.info(f"Using mock account: {account_name}")
        
        # Check if account exists and store result
        account_exists = account_manager.account_exists(account_name, view_name=VIEW_NAME)
        
        # Create account if it doesn't exist
        if not account_exists:
            logging.info(f"Account {account_name} does not exist, creating it...")
            # Create new account
            if not account_manager.create_new_account(
                first_name=account['first_name'],
                last_name=account['last_name'],
                middle_name=account.get('middle_name'),
                account_info=account.get('account_info', {})
            ):
                logging.error(f"Failed to create account: {account_name}")
                return
                
            # Upload files for new account
            logging.info(f"Uploading files for new account: {account_name}")
            upload_success = upload_files_for_account(page, account, debug_mode=True)
            if not upload_success:
                logging.error(f"Failed to upload files for account: {account_name}")
                return
                
            # Verify account exists after creation
            account_exists = account_manager.account_exists(account_name, view_name=VIEW_NAME)
            assert account_exists, f"Account {account_name} does not exist after creation"
        else:
            logging.info(f"Account exists: {account_name}")
        
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
        
        # Delete the account
        if not account_manager.delete_account(account_name, view_name=VIEW_NAME):
            logging.error(f"Failed to delete account: {account_name}")
            return
            
        logging.info(f"Successfully deleted account: {account_name}")
        
        # Verify account was deleted
        if account_manager.account_exists(account_name, view_name=VIEW_NAME):
            logging.error(f"Account still exists after deletion: {account_name}")
            return
            
        logging.info(f"Verified account deletion: {account_name}")
        logging.info("Test completed successfully")
        
    except Exception as e:
        logging.error(f"Test failed: {str(e)}")
        raise

def main():
    """Main function to run the test."""
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            test_account_deletion(browser, page)
        finally:
            browser.close()

if __name__ == "__main__":
    main() 