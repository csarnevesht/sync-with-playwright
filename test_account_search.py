import os
import sys
from playwright.sync_api import sync_playwright
import logging
from salesforce.pages.account_manager import AccountManager
from salesforce.pages.accounts_page import AccountsPage
import pytest
from get_salesforce_page import get_salesforce_page
from salesforce.pages.file_manager import FileManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_search_account(account_name: str):
    """Test searching for an account by name."""
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            account_manager = AccountManager(page, debug_mode=True)
            
            # Navigate to accounts page
            if not account_manager.navigate_to_accounts_list_page():
                logging.error("Failed to navigate to accounts page")
                return
                
            # Search for the account
            if not account_manager.account_exists(account_name):
                logging.error(f"Account {account_name} does not exist")
                return
                
            # Click on the account name
            if not account_manager.click_account_name(account_name):
                logging.error(f"Failed to navigate to account view page for: {account_name}")
                return
                
            # Verify we're on the correct account page
            is_valid, account_id = account_manager.verify_account_page_url()
            if not is_valid:
                logging.error("Not on a valid account page")
                return
                
            logging.info(f"Successfully navigated to account {account_name} with ID {account_id}")
            
        except Exception as e:
            logging.error(f"Test failed: {str(e)}")
            page.screenshot(path="test-failure.png")
            raise
        finally:
            browser.close()

if __name__ == "__main__":
    test_search_account("John Smith") 
    # test_search_account("Beth Albert") 