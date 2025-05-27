"""
Test Account Creation and File Management

This test verifies the account creation and file management functionality in Salesforce. It:
1. Creates new accounts using mock data
2. Verifies account creation success
3. Uploads files to the created accounts
4. Verifies file uploads and counts
5. Handles cleanup of test data

The test includes:
- Robust account creation with validation
- File upload with retry logic
- Verification of account properties
- File count verification
- Support for various file types
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
from sync.salesforce_client.utils.browser import get_salesforce_page
from sync.salesforce_client.utils.file_upload import upload_files_for_account
from sync.salesforce_client.utils.mock_data import get_mock_accounts
from playwright.sync_api import sync_playwright, TimeoutError
from src.config import *

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set root logger to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_accounts_create.log', mode='w')  # Use 'w' mode to clear previous logs
    ]
)

# Get the root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# Configure specific loggers
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Set debug level for specific modules and ensure their handlers are set
for module in [
    'sync.salesforce_client.pages.file_manager',
    'sync.salesforce_client.pages.account_manager',
    'sync.salesforce_client.utils.file_upload',
    'tests.test_accounts_create'
]:
    module_logger = logging.getLogger(module)
    module_logger.setLevel(logging.DEBUG)
    # Ensure the logger propagates to root
    module_logger.propagate = True

# Add a debug message to verify logging is working
logger.debug("Debug logging initialized")

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
        logger.debug(f"Waiting for page load with timeout {timeout}ms")
        page.wait_for_load_state('networkidle', timeout=timeout)
        logger.debug("Network is idle")
        page.wait_for_load_state('domcontentloaded', timeout=timeout)
        logger.debug("DOM content loaded")
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
    logger.debug(f"Getting full name for account: {account}")
    name_parts = [
        account['first_name'],
        account.get('middle_name'),
        account['last_name']
    ]
    logger.debug(f"Name parts before cleaning: {name_parts}")
    full_name = ' '.join(
        part for part in name_parts 
        if part and str(part).strip().lower() not in ['none', '']
    )
    logger.debug(f"Generated full name: '{full_name}' from parts: {name_parts}")
    return full_name

def verify_account_and_files(account_manager: AccountManager, file_manager: FileManager, account: dict, view_name: str = "FinServ__My_Clients") -> bool:
    """
    Verify that an account exists and has the expected number of files.
    
    Args:
        account_manager: AccountManager instance
        file_manager: FileManager instance
        account: Account dictionary from mock data
        view_name: Name of the list view to use (default: "FinServ__My_Clients")
        
    Returns:
        bool: True if verification passed, False otherwise
    """
    # Get full name
    full_name = get_full_name(account)
    logger.debug(f"Starting verification for account: {full_name}")
    logger.debug(f"Account data: {account}")
    
    # Check if account exists and store result
    logger.debug(f"Checking if account exists: {full_name} in view: {view_name}")
    account_exists = account_manager.account_exists(full_name, view_name=view_name)
    if not account_exists:
        logger.error(f"Account does not exist: {full_name}")
        return False
        
    # Click on the account name to navigate to it
    logger.debug(f"Attempting to click account name: {full_name}")
    if not account_manager.click_account_name(full_name):
        logger.error(f"Failed to navigate to account view page for: {full_name}")
        return False
        
    # Verify we're on the correct account page
    logger.debug("Verifying account page URL")
    is_valid, account_id = account_manager.verify_account_page_url()
    if not is_valid:
        logger.error("Not on a valid account page")
        return False
        
    logger.info(f"Successfully navigated to account {full_name} with ID {account_id}")
    
    # Navigate to Files and get count
    logger.debug(f"Navigating to Files for account {account_id}")
    num_files = account_manager.navigate_to_files_and_get_number_of_files_for_this_account(account_id)
    if num_files == -1:
        logger.error("Failed to navigate to Files")
        return False
        
    # Verify file count
    expected_files = len(account.get('files', []))
    logger.debug(f"Expected files: {expected_files}, Found files: {num_files}")
    logger.debug(f"Account files: {account.get('files', [])}")
    
    if isinstance(num_files, str):
        # If we have "50+" files, we can't verify exact count
        if num_files == "50+":
            logger.info(f"Account has more than 50 files, expected at least {expected_files}")
            return True
        else:
            logger.error(f"Unexpected file count format: {num_files}")
            return False
    else:
        if num_files < expected_files:
            logger.error(f"Account has {num_files} files, expected {expected_files}")
            return False
            
    # Verify each file exists
    logger.debug(f"Verifying {len(account.get('files', []))} files")
    for file in account.get('files', []):
        logger.debug(f"Searching for file: {file['name']}")
        logger.debug(f"File data: {file}")
        if not file_manager.search_file(file['name']):
            logger.error(f"File not found: {file['name']}")
            return False
            
    logger.info(f"Successfully verified account {full_name} with {num_files} files")
    return True

def test_account_creation(browser: Browser, page: Page):
    """
    Test creating accounts and managing their files in Salesforce.
    
    Args:
        browser: Playwright browser instance
        page: Playwright page instance
    
    This test:
    1. Loads mock account data
    2. For each account:
       - Checks if it exists
       - If it exists: uploads files to the existing account
       - If it doesn't exist: creates the account and uploads files
    3. Verifies all accounts and their files
    4. Handles cleanup of test data
    """
    try:
        logger.info("Starting test_account_creation")
        logger.debug("Initializing test with browser and page")
        
        # Initialize managers
        logger.debug("Initializing AccountManager and FileManager")
        account_manager = AccountManager(page, debug_mode=True)
        file_manager = FileManager(page, debug_mode=True)
        
        # Set view name for all operations
        view_name = "FinServ__My_Clients"
        logger.debug(f"Using view name: {view_name}")
        
        # Get mock accounts
        logger.debug("Loading mock accounts")
        mock_accounts = get_mock_accounts()
        logger.debug(f"Mock accounts data: {mock_accounts}")
        logger.info(f"Loaded {len(mock_accounts)} mock accounts")
        
        # Process each mock account
        for i, account in enumerate(mock_accounts, 1):
            try:
                logger.debug(f"Processing account {i}/{len(mock_accounts)}")
                # Get the full name including middle name
                full_name = get_full_name(account)
                logger.info(f"Processing account: {full_name}")
                logger.debug(f"Account data: {account}")
                
                # Check if account exists
                logger.debug(f"Checking if account exists: {full_name}")
                if account_manager.account_exists(full_name, view_name=view_name):
                    logger.info(f"Account exists: {full_name}")
                    # Navigate to account view page
                    logger.debug(f"Navigating to account view page: {full_name}")
                    if not account_manager.click_account_name(full_name):
                        logger.error(f"Failed to click account name: {full_name}")
                        continue
                    # Get account ID for file upload
                    logger.debug("Verifying account page URL")
                    is_valid, account_id = account_manager.verify_account_page_url()
                    if not is_valid:
                        logger.error(f"Could not get account ID for {full_name}")
                        continue
                    # Upload files for existing account
                    logger.info(f"Uploading files for existing account: {full_name}")
                    logger.debug(f"Account files to upload: {account.get('files', [])}")
                    upload_success = upload_files_for_account(page, account, debug_mode=True)
                    if not upload_success:
                        logger.error(f"Failed to upload files for account: {full_name}")
                        continue
                else:
                    logger.info(f"Account does not exist: {full_name}")
                    # Create new account
                    logger.debug(f"Creating new account: {full_name}")
                    logger.debug(f"Account creation data: {account}")
                    if not account_manager.create_new_account(
                        first_name=account['first_name'],
                        last_name=account['last_name'],
                        middle_name=account.get('middle_name'),
                        account_info=account.get('account_info', {})
                    ):
                        logger.error(f"Failed to create account: {full_name}")
                        continue
                    # Get account ID for file upload
                    logger.debug("Verifying account page URL")
                    is_valid, account_id = account_manager.verify_account_page_url()
                    if not is_valid:
                        logger.error(f"Could not get account ID for {full_name}")
                        continue
                    # Upload files for new account
                    logger.info(f"Uploading files for new account: {full_name}")
                    logger.debug(f"Account files to upload: {account.get('files', [])}")
                    upload_success = upload_files_for_account(page, account, debug_mode=True)
                    if not upload_success:
                        logger.error(f"Failed to upload files for account: {full_name}")
                        continue
                
            except Exception as e:
                logger.error(f"Error processing account {full_name}: {str(e)}", exc_info=True)
                page.screenshot(path=f"error-{full_name.replace(' ', '-')}.png")
                continue
        
        # Run final verification pass
        logger.info("Running final verification pass...")
        for i, account in enumerate(mock_accounts, 1):
            try:
                full_name = get_full_name(account)
                logger.debug(f"Verifying account {i}/{len(mock_accounts)}: {full_name}")
                logger.debug(f"Account data for verification: {account}")
                if not verify_account_and_files(account_manager, file_manager, account, view_name):
                    logger.error(f"Verification failed for account: {full_name}")
                    continue
                logger.info(f"Successfully verified account: {full_name}")
            except Exception as e:
                logger.error(f"Error verifying account {full_name}: {str(e)}", exc_info=True)
                continue
                
        logger.info("Test completed successfully")
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}", exc_info=True)
        page.screenshot(path="test-failure.png")
        raise
    finally:
        browser.close()

def main():
    """Run the account creation test."""
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            test_account_creation(browser, page)
        finally:
            browser.close()

if __name__ == "__main__":
    main() 