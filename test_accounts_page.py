import os
import sys
from playwright.sync_api import sync_playwright
import logging
from salesforce.pages.accounts_page import AccountsPage
import pytest
from get_salesforce_page import get_salesforce_page

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_get_accounts_matching():
    """Test the get_accounts_matching method of AccountsPage with a custom filter for accounts with more than 0 files."""
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            accounts_page = AccountsPage(page, debug_mode=True)

            # Custom filter: accounts with more than 0 files
            def nonzero_files_filter(account):
                files_count = accounts_page.get_files_count_for_account(account['id'])
                return files_count is not None and files_count > 0

            accounts = accounts_page.get_accounts_matching(max_number=5, files_filter=nonzero_files_filter)

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
    test_get_accounts_matching() 