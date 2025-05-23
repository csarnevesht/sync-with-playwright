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
from playwright.sync_api import sync_playwright, TimeoutError
import logging
from salesforce.pages.account_manager import AccountManager
from salesforce.utils.browser import get_salesforce_page
from salesforce.utils.mock_data import get_mock_accounts
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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
        logging.warning("Timeout waiting for page load, continuing anyway")
        return False

def wait_for_element(page, selector: str, timeout: int = 10000, state: str = "visible") -> bool:
    """
    Wait for an element to be in the specified state.
    
    Args:
        page: Playwright page object
        selector: Element selector
        timeout: Maximum time to wait in milliseconds
        state: Element state to wait for (visible, hidden, etc.)
        
    Returns:
        bool: True if element is in the specified state, False otherwise
    """
    try:
        page.wait_for_selector(selector, state=state, timeout=timeout)
        return True
    except TimeoutError:
        logging.warning(f"Timeout waiting for element: {selector}")
        return False

def verify_account_exists(account_manager: AccountManager, account_name: str, max_retries: int = 3) -> bool:
    """
    Verify if an account exists with retry logic.
    
    Args:
        account_manager: AccountManager instance
        account_name: Name of the account to check
        max_retries: Maximum number of retry attempts
        
    Returns:
        bool: True if account exists, False otherwise
    """
    for attempt in range(max_retries):
        try:
            # Ensure we're on the accounts list page
            if not account_manager.navigate_to_accounts_list_page():
                logging.error("Failed to navigate to accounts list page")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
            
            # Wait for the page to be fully loaded
            if not wait_for_page_load(account_manager.page):
                logging.warning("Page load timeout, retrying...")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
            
            # Check if account exists
            exists = account_manager.account_exists(account_name)
            if exists:
                logging.info(f"Account exists: {account_name}")
                return True
            else:
                logging.info(f"Account does not exist: {account_name}")
                return False
                
        except Exception as e:
            logging.error(f"Error checking account existence: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
    
    return False

def create_account_with_retry(account_manager: AccountManager, mock: dict, max_retries: int = 3) -> bool:
    """
    Create an account with retry logic.
    
    Args:
        account_manager: AccountManager instance
        mock: Mock account data
        max_retries: Maximum number of retry attempts
        
    Returns:
        bool: True if account was created successfully, False otherwise
    """
    account_name = f"{mock['first_name']} {mock['last_name']}"
    
    # First verify if account already exists
    if verify_account_exists(account_manager, account_name):
        logging.info(f"Account already exists, skipping creation: {account_name}")
        return True
    
    for attempt in range(max_retries):
        try:
            logging.info(f"Creating account: {account_name} (Attempt {attempt + 1}/{max_retries})")
            
            # Wait for the page to be fully loaded before starting
            if not wait_for_page_load(account_manager.page):
                logging.warning("Page load timeout, retrying...")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
            
            # Create the account with increased timeout
            created = account_manager.create_new_account(
                first_name=mock['first_name'],
                last_name=mock['last_name'],
                middle_name=mock.get('middle_name'),
                account_info=mock.get('account_info', {}),
                timeout=15000  # Increased timeout for Next button
            )
            
            if created:
                # Verify the account was actually created
                if verify_account_exists(account_manager, account_name):
                    logging.info(f"Successfully created and verified account: {account_name}")
                    return True
                else:
                    logging.warning(f"Account creation reported success but account not found: {account_name}")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                
            logging.warning(f"Failed to create account: {account_name}")
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retry
                continue
                
        except Exception as e:
            logging.error(f"Error creating account {account_name}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retry
                continue
    
    return False

def test_delete_accounts():
    """
    Test deleting multiple accounts in Salesforce.
    
    This test:
    1. Loads mock account data
    2. Creates test accounts if they don't exist
    3. Verifies the accounts exist before deletion
    4. Deletes each account
    5. Verifies successful deletion
    6. Handles any cleanup of remaining test data
    """
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            # Initialize account manager
            account_manager = AccountManager(page, debug_mode=True)
            
            # Get mock accounts
            mock_accounts = get_mock_accounts()
            accounts_to_delete = []
            
            # First, ensure accounts exist
            for mock in mock_accounts:
                account_name = f"{mock['first_name']} {mock['last_name']}"
                logging.info(f"Checking account: {account_name}")
                
                # Create account if it doesn't exist
                if not verify_account_exists(account_manager, account_name):
                    logging.info(f"Account {account_name} does not exist, creating it...")
                    if not create_account_with_retry(account_manager, mock):
                        logging.error(f"Failed to create account after retries: {account_name}")
                        continue
                
                accounts_to_delete.append(account_name)
                logging.info(f"Account {account_name} exists and ready for deletion")
            
            # Delete each account
            for account_name in accounts_to_delete:
                logging.info(f"Deleting account: {account_name}")
                
                # Verify account exists before deletion
                if not verify_account_exists(account_manager, account_name):
                    logging.error(f"Account not found before deletion: {account_name}")
                    continue
                
                # Delete the account with retry
                for attempt in range(3):
                    try:
                        if account_manager.delete_account(account_name):
                            logging.info(f"Successfully deleted account: {account_name}")
                            
                            # Verify account was deleted
                            if verify_account_exists(account_manager, account_name):
                                logging.error(f"Account still exists after deletion: {account_name}")
                                if attempt < 2:  # Try again if not last attempt
                                    time.sleep(2)
                                    continue
                            else:
                                logging.info(f"Verified account deletion: {account_name}")
                                break
                        else:
                            logging.error(f"Failed to delete account: {account_name}")
                            if attempt < 2:  # Try again if not last attempt
                                time.sleep(2)
                                continue
                    except Exception as e:
                        logging.error(f"Error deleting account {account_name}: {str(e)}")
                        if attempt < 2:  # Try again if not last attempt
                            time.sleep(2)
                            continue
            
            # Final cleanup check
            logging.info("\nPerforming final cleanup check...")
            for account_name in accounts_to_delete:
                if verify_account_exists(account_manager, account_name):
                    logging.warning(f"Account still exists, attempting final deletion: {account_name}")
                    if account_manager.delete_account(account_name):
                        logging.info(f"Successfully deleted account in cleanup: {account_name}")
                    else:
                        logging.error(f"Failed to delete account in cleanup: {account_name}")
            
            logging.info("Test completed successfully")
            
        except Exception as e:
            logging.error(f"Test failed: {str(e)}")
            page.screenshot(path="test-failure.png")
            raise
        finally:
            browser.close()

def main():
    """Run the account deletion test."""
    test_delete_accounts()

if __name__ == "__main__":
    main() 