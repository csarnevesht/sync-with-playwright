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