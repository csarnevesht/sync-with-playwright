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

def test_get_all_accounts():
    """Test the get_all_accounts method of AccountsPage."""
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            # Initialize AccountsPage
            accounts_page = AccountsPage(page, debug_mode=True)
            
            # Test get_all_accounts
            accounts = accounts_page.get_all_accounts()
            assert accounts, "No accounts were returned"
            
            # Verify we're on the accounts page
            current_url = page.url
            assert "/lightning/o/Account/list" in current_url, f"Not on accounts list page. Current URL: {current_url}"
            
            # Verify we have account data
            assert len(accounts) > 0, "No accounts found in the list"
            
            # Log the first few accounts for verification
            logging.info(f"Found {len(accounts)} accounts")
            for i, account in enumerate(accounts[:5]):  # Log first 5 accounts
                logging.info(f"Account {i+1}: {account['name']} (ID: {account['id']})")
            
            # Verify account data structure
            for account in accounts:
                assert 'name' in account, "Account missing name"
                assert 'id' in account, "Account missing ID"
                assert account['name'], "Account name is empty"
                assert account['id'], "Account ID is empty"
            
            logging.info("Test passed successfully")
            
        except Exception as e:
            logging.error(f"Test failed: {str(e)}")
            page.screenshot(path="test-failure.png")
            raise
        finally:
            browser.close()

if __name__ == "__main__":
    test_get_all_accounts() 