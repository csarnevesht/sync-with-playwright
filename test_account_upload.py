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
        account_manager = AccountManager(page, debug_mode=debug_mode)
        # Verify we're on the correct account page
        if not account_manager.verify_account_page_url():
            logging.error("Please navigate to the account page first.")
            sys.exit(1)
        
        # Initialize Salesforce page objects
        accounts_page = AccountsPage(page, debug_mode=debug_mode)
        
        # Upload files for the account
        upload_success = upload_files_for_account(page, test_account, debug_mode=debug_mode, max_tries=max_tries)
        
        if not upload_success:
            print("File upload process completed with errors")
            sys.exit(1)
        
        # Close the browser
        browser.close()

if __name__ == "__main__":
    main() 