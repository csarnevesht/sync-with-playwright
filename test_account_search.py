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
    """Test searching for an account by name and checking its files."""
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            account_manager = AccountManager(page, debug_mode=True)
            file_manager = FileManager(page, debug_mode=True)
            
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
            
            # Navigate to files and get count
            logging.info(f"Navigating to files for account {account_name}")
            num_files = account_manager.navigate_to_files_and_get_number_of_files_for_this_account(account_id)
            
            if num_files == -1:
                logging.error("Failed to navigate to files page")
                return
                
            # Log the number of files found
            if isinstance(num_files, str):
                logging.info(f"Account has {num_files} files")
            else:
                logging.info(f"Account has {num_files} files")
                
            # Navigate back to account page
            account_manager.navigate_back_to_account_page()
            
            # Verify we're back on the account page
            is_valid, _ = account_manager.verify_account_page_url()
            assert is_valid, "Failed to navigate back to account page"
            
            logging.info("Test completed successfully")
            
        except Exception as e:
            logging.error(f"Test failed: {str(e)}")
            page.screenshot(path="test-failure.png")
            raise
        finally:
            browser.close()

if __name__ == "__main__":
    test_search_account("Beth Albert") 