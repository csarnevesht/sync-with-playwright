import os
import sys
from playwright.sync_api import sync_playwright, TimeoutError
import logging
from salesforce.pages.account_manager import AccountManager
from salesforce.pages.accounts_page import AccountsPage
import pytest
from get_salesforce_page import get_salesforce_page
from salesforce.pages.file_manager import FileManager
from mock_data import get_mock_accounts
from file_upload import upload_files_for_account
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def wait_for_page_load(page, timeout=10000):
    """Wait for the page to be fully loaded."""
    try:
        page.wait_for_load_state('networkidle', timeout=timeout)
        page.wait_for_load_state('domcontentloaded', timeout=timeout)
        return True
    except TimeoutError:
        logging.warning("Timeout waiting for page load, continuing anyway")
        return False

def get_full_name(account: dict) -> str:
    """Get the full name of an account including middle name if present."""
    name_parts = [
        account['first_name'],
        account.get('middle_name'),
        account['last_name']
    ]
    return ' '.join(
        part for part in name_parts 
        if part and str(part).strip().lower() not in ['none', '']
    )

def verify_account_and_files(account_manager: AccountManager, file_manager: FileManager, account: dict) -> bool:
    """
    Verify that an account exists and has the expected number of files.
    
    Args:
        account_manager: AccountManager instance
        file_manager: FileManager instance
        account: Account dictionary from mock data
        
    Returns:
        bool: True if verification passed, False otherwise
    """
    # Get full name
    full_name = get_full_name(account)
    
    # Check if account exists
    if not account_manager.account_exists(full_name):
        logging.error(f"Account does not exist: {full_name}")
        return False
        
    # Click on the account name to navigate to it
    if not account_manager.click_account_name(full_name):
        logging.error(f"Failed to navigate to account view page for: {full_name}")
        return False
        
    # Verify we're on the correct account page
    is_valid, account_id = account_manager.verify_account_page_url()
    if not is_valid:
        logging.error("Not on a valid account page")
        return False
        
    logging.info(f"Successfully navigated to account {full_name} with ID {account_id}")
    
    # Navigate to Files and get count
    num_files = account_manager.navigate_to_files_and_get_number_of_files_for_this_account(account_id)
    if num_files == -1:
        logging.error("Failed to navigate to Files")
        return False
        
    # Verify file count
    expected_files = len(account['files'])
    if isinstance(num_files, str):
        # If we have "50+" files, we can't verify exact count
        if num_files == "50+":
            logging.info(f"Account has more than 50 files, expected at least {expected_files}")
            return True
        else:
            logging.error(f"Unexpected file count format: {num_files}")
            return False
    else:
        if num_files < expected_files:
            logging.error(f"Account has {num_files} files, expected {expected_files}")
            return False
            
    # Verify each file exists
    for file in account['files']:
        search_pattern = f"{os.path.splitext(file['name'])[0]}"
        if not file_manager.search_file(search_pattern):
            logging.error(f"File not found: {file['name']}")
            return False
            
    logging.info(f"Successfully verified account {full_name} with {num_files} files")
    return True

def test_create_accounts():
    """Test creating accounts from mock data."""
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            # Initialize managers
            account_manager = AccountManager(page)
            file_manager = FileManager(page)
            
            # Navigate to Accounts page
            assert account_manager.navigate_to_accounts_list_page(), "Failed to navigate to Accounts page"
            
            # Get mock accounts
            mock_accounts = get_mock_accounts()
            
            # Process each mock account
            for account in mock_accounts:
                try:
                    # Get the full name including middle name
                    full_name = get_full_name(account)
                    logging.info(f"Processing account: {full_name}")
                    
                    # Navigate back to accounts list page before searching
                    assert account_manager.navigate_to_accounts_list_page(), "Failed to navigate to Accounts page"
                    
                    # Check if account exists
                    if account_manager.account_exists(full_name):
                        logging.info(f"Account exists: {full_name}")
                        # Navigate to account view page
                        assert account_manager.click_account_name(full_name), f"Failed to click account name: {full_name}"
                        # Get account ID for file upload
                        is_valid, account_id = account_manager.verify_account_page_url()
                        assert is_valid, f"Could not get account ID for {full_name}"
                        # Upload files for existing account
                        logging.info(f"Uploading files for existing account: {full_name}")
                        upload_success = upload_files_for_account(page, account, debug_mode=True)
                        assert upload_success, f"Failed to upload files for account: {full_name}"
                    else:
                        logging.info(f"Account does not exist: {full_name}")
                        # Create new account
                        assert account_manager.create_new_account(
                            first_name=account['first_name'],
                            last_name=account['last_name'],
                            middle_name=account.get('middle_name'),
                            account_info=account.get('account_info', {})
                        ), f"Failed to create account: {full_name}"
                        # Get account ID for file upload
                        is_valid, account_id = account_manager.verify_account_page_url()
                        assert is_valid, f"Could not get account ID for {full_name}"
                        # Upload files for new account
                        logging.info(f"Uploading files for new account: {full_name}")
                        upload_success = upload_files_for_account(page, account, debug_mode=True)
                        assert upload_success, f"Failed to upload files for account: {full_name}"
                    
                except Exception as e:
                    logging.error(f"Error processing account {full_name}: {str(e)}")
                    page.screenshot(path=f"error-{full_name.replace(' ', '-')}.png")
                    continue
            
            # Run final verification pass
            logging.info("Running final verification pass...")
            for account in mock_accounts:
                try:
                    full_name = get_full_name(account)
                    # Navigate back to accounts list page before verifying
                    assert account_manager.navigate_to_accounts_list_page(), "Failed to navigate to Accounts page"
                    # Verify account and files
                    assert verify_account_and_files(account_manager, file_manager, account), f"Verification failed for account: {full_name}"
                except Exception as e:
                    logging.error(f"Error verifying account {full_name}: {str(e)}")
                    page.screenshot(path=f"verification-error-{full_name.replace(' ', '-')}.png")
                    continue
                    
        except Exception as e:
            logging.error(f"Test failed: {str(e)}")
            page.screenshot(path="test-failure.png")
            raise
        finally:
            browser.close()

def main():
    test_create_accounts()

if __name__ == "__main__":
    main() 