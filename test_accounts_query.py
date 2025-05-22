import os
import sys
from playwright.sync_api import sync_playwright
import logging
from salesforce.pages.account_manager import AccountManager
from salesforce.pages.accounts_page import AccountsPage
import pytest
from get_salesforce_page import get_salesforce_page

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_get_accounts_matching_condition():
    """Test the get_accounts_matching_condition method of AccountsPage with a custom filter for accounts with more than 0 files."""
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            accounts_page = AccountsPage(page, debug_mode=True)
            account_manager = AccountManager(page, debug_mode=True)

            accounts = account_manager.get_accounts_matching_condition(max_number=5, condition=accounts_page.account_has_files(account['id']))

            if not accounts:
                logging.info("No accounts matching the filter were found.")
            else:
                logging.info(f"Found {len(accounts)} accounts matching the filter:")
                for account in accounts:
                    logging.info(f"Name: {account['name']}, ID: {account['id']}, Files: {account['files_count']}")

            logging.info("Test completed successfully")

        except Exception as e:
            logging.error(f"Test failed: {str(e)}")
            page.screenshot(path="test-failure.png")
            raise
        finally:
            browser.close()

if __name__ == "__main__":
    test_get_accounts_matching_condition() 