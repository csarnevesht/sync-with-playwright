import os
import sys
import logging
from playwright.sync_api import sync_playwright
from salesforce.pages.account_manager import AccountManager
from get_salesforce_page import get_salesforce_page
from mock_data import get_mock_accounts

def main():
    # Enable debug mode
    debug_mode = True
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
            
            # Get full name
            full_name = f"{test_account['first_name']} {test_account['last_name']}"
            logging.info(f"Searching for account: {full_name}")
            
            # Delete the account using AccountManager method
            if account_manager.delete_account(full_name):
                logging.info("Test completed successfully")
            else:
                logging.error("Failed to delete account")
                sys.exit(1)
                
        except Exception as e:
            logging.error(f"Test failed: {str(e)}")
            page.screenshot(path="test-failure.png")
            raise
        finally:
            browser.close()

if __name__ == "__main__":
    main() 