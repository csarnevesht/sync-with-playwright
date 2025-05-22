import os
import sys
from playwright.sync_api import sync_playwright
from file_upload import upload_files_for_account
from salesforce.pages import account_manager, file_manager
from salesforce.pages.accounts_page import AccountsPage
import tempfile
import logging
from mock_data import get_mock_accounts
import re
import time
from get_salesforce_page import get_salesforce_page
from salesforce.pages.account_manager import AccountManager

def verify_account_page_url(page, account_id=None) -> tuple[bool, str]:
    """
    Verify we're on the correct account page URL pattern.
    
    Args:
        page: Playwright page object
        account_id: Optional specific account ID to verify against. If None, any valid account ID is accepted.
    
    Returns:
        tuple[bool, str]: (is_valid_url, account_id)
    """
    current_url = page.url
    print(f"\nCurrent URL: {current_url}")
    
    # Get Salesforce URL from environment variable
    salesforce_url = os.getenv('SALESFORCE_URL')
    if not salesforce_url:
        print("Error: SALESFORCE_URL environment variable is not set")
        return False, None
    
    # Pattern: SALESFORCE_URL/Account/SOME_ID/view
    pattern = f"{re.escape(salesforce_url)}.*/Account/([^/]+)/view"
    match = re.match(pattern, current_url)
    
    if not match:
        print("Error: Not on the correct account page URL pattern")
        print(f"Expected pattern: {salesforce_url}/Account/{{account_id}}/view")
        return False, None
    
    found_account_id = match.group(1)
    
    if account_id and found_account_id != account_id:
        print(f"Error: Account ID mismatch. Found: {found_account_id}, Expected: {account_id}")
        return False, None
    
    print(f"Verified correct URL pattern with account ID: {found_account_id}")
    return True, found_account_id


def main():
    # Enable debug mode
    debug_mode = True
    max_tries = 3  # Number of retry attempts per file
    logging.basicConfig(level=logging.INFO)
    
    # Get mock account data
    mock_accounts = get_mock_accounts()
    test_account = mock_accounts[0]  # Use John Smith's account for testing
    
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            # Initialize managers
            account_manager = AccountManager(page, debug_mode=debug_mode)
            
            # Navigate to Accounts page
            assert account_manager.navigate_to_accounts_list_page(), "Failed to navigate to Accounts page"
            
            # Search for John Smith's account
            full_name = f"{test_account['first_name']} {test_account['last_name']}"
            logging.info(f"Ensuring account exists: {full_name}")
            
            # If account does not exist, create it
            if not account_manager.account_exists(full_name):
                logging.info(f"Account {full_name} does not exist, creating it...")
                created = account_manager.create_new_account(
                    first_name=test_account['first_name'],
                    last_name=test_account['last_name'],
                    middle_name=test_account.get('middle_name'),
                    account_info=test_account.get('account_info', {})
                )
                assert created, f"Failed to create account: {full_name}"
                logging.info(f"Account {full_name} created.")
                # Navigate back to Accounts page and wait for search input
                assert account_manager.navigate_to_accounts_list_page(), "Failed to navigate to Accounts page after creation"
            else:
                logging.info(f"Account {full_name} already exists.")
            
            # Click on the account name to navigate to it
            if not account_manager.click_account_name(full_name):
                logging.error(f"Failed to navigate to account view page for: {full_name}")
                sys.exit(1)
            
            # Verify we're on the correct account page
            is_valid, account_id = account_manager.verify_account_page_url()
            if not is_valid:
                logging.error("Not on a valid account page")
                sys.exit(1)
            logging.info(f"Successfully navigated to account {full_name} with ID {account_id}")
            
            # Upload files for the account
            logging.info(f"Uploading files for account: {full_name}")
            upload_success = upload_files_for_account(page, test_account, debug_mode=debug_mode, max_tries=max_tries)
            
            if not upload_success:
                logging.error("File upload process completed with errors")
                sys.exit(1)
            
            logging.info("Test completed successfully")
            
        except Exception as e:
            logging.error(f"Test failed: {str(e)}")
            page.screenshot(path="test-failure.png")
            raise
        finally:
            browser.close()

if __name__ == "__main__":
    main() 