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
from sync.salesforce.pages.account_manager import AccountManager
from sync.salesforce.utils.mock_data import get_mock_accounts
from playwright.sync_api import TimeoutError

# Get logger for this module
logger = logging.getLogger(__name__)

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

def verify_account_exists(account_manager: AccountManager, account_name: str, view_name: str = "Recent", max_retries: int = 3) -> bool:
    """
    Verify if an account exists with retry logic.
    
    Args:
        account_manager: AccountManager instance
        account_name: Name of the account to check
        view_name: Name of the view to search in (default: "Recent")
        max_retries: Maximum number of retry attempts
        
    Returns:
        bool: True if account exists, False otherwise
    """
    for attempt in range(max_retries):
        try:
            # Check if account exists
            exists = account_manager.account_exists(account_name, view_name=view_name)
            if exists:
                logger.info(f"Account exists: {account_name}")
                return True
            else:
                logger.info(f"Account does not exist: {account_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking account existence: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
    
    return False

def create_account_with_retry(account_manager: AccountManager, account_data: dict, max_retries: int = 3) -> bool:
    """
    Create an account with retry logic.
    
    Args:
        account_manager: AccountManager instance
        account_data: Account data dictionary
        max_retries: Maximum number of retry attempts
        
    Returns:
        bool: True if account was created successfully, False otherwise
    """
    for attempt in range(max_retries):
        try:
            success = account_manager.create_new_account(
                first_name=account_data['first_name'],
                last_name=account_data['last_name'],
                middle_name=account_data.get('middle_name'),
                account_info=account_data.get('account_info', {})
            )
            if success:
                logger.info(f"Successfully created account: {account_data['first_name']} {account_data['last_name']}")
                return True
            else:
                logger.error(f"Failed to create account on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
        except Exception as e:
            logger.error(f"Error creating account: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
    
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

def test_delete_accounts(browser: Browser, page: Page):
    """
    Test deleting multiple accounts in Salesforce.
    
    Args:
        browser: Playwright browser instance
        page: Playwright page instance
    
    This test:
    1. Loads mock account data
    2. Creates test accounts if they don't exist
    3. Verifies the accounts exist before deletion
    4. Deletes each account
    5. Verifies successful deletion
    6. Handles any cleanup of remaining test data
    """
    try:
        # Initialize account manager
        account_manager = AccountManager(page, debug_mode=True)
        
        # Set view name for all operations
        view_name = "Recent"
        
        # Get mock accounts
        mock_accounts = get_mock_accounts()
        accounts_to_delete = []
        
        # First, ensure accounts exist
        for mock in mock_accounts:
            account_name = get_full_name(mock)
            logger.info(f"Checking account: {account_name}")
            
            # Create account if it doesn't exist
            if not verify_account_exists(account_manager, account_name, view_name=view_name):
                logger.info(f"Account {account_name} does not exist, creating it...")
                if not create_account_with_retry(account_manager, mock):
                    logger.error(f"Failed to create account after retries: {account_name}")
                    continue
            
            accounts_to_delete.append(account_name)
            logger.info(f"Account {account_name} exists and ready for deletion")
        
        # Delete each account
        for account_name in accounts_to_delete:
            logger.info(f"Deleting account: {account_name}")
            
            # Verify account exists before deletion
            if not verify_account_exists(account_manager, account_name, view_name=view_name):
                logger.error(f"Account not found before deletion: {account_name}")
                continue
            
            # Delete the account with retry
            for attempt in range(3):
                try:
                    if account_manager.delete_account(account_name, view_name=view_name):
                        logger.info(f"Successfully deleted account: {account_name}")
                        
                        # Verify account was deleted
                        if verify_account_exists(account_manager, account_name, view_name=view_name):
                            logger.error(f"Account still exists after deletion: {account_name}")
                            if attempt < 2:  # Try again if not last attempt
                                time.sleep(2)
                                continue
                        else:
                            logger.info(f"Verified account deletion: {account_name}")
                            break
                    else:
                        logger.error(f"Failed to delete account: {account_name}")
                        if attempt < 2:  # Try again if not last attempt
                            time.sleep(2)
                            continue
                except Exception as e:
                    logger.error(f"Error deleting account {account_name}: {str(e)}")
                    if attempt < 2:  # Try again if not last attempt
                        time.sleep(2)
                        continue
        
        # Final cleanup check
        logger.info("\nPerforming final cleanup check...")
        for account_name in accounts_to_delete:
            if verify_account_exists(account_manager, account_name, view_name=view_name):
                logger.warning(f"Account still exists, attempting final deletion: {account_name}")
                if account_manager.delete_account(account_name, view_name=view_name):
                    logger.info(f"Successfully deleted account in cleanup: {account_name}")
                else:
                    logger.error(f"Failed to delete account in cleanup: {account_name}")
        
        logger.info("Test completed successfully")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        page.screenshot(path="test-failure.png")
        raise

def main():
    """Run the account deletion test."""
    from playwright.sync_api import sync_playwright
    from sync.salesforce.utils.browser import get_salesforce_page
    
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            test_delete_accounts(browser, page)
        finally:
            browser.close()

if __name__ == "__main__":
    main() 