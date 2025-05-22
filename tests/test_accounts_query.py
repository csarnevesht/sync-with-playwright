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

def get_accounts_with_files(account_manager: AccountManager, max_number: int = 5) -> list:
    """
    Get accounts that have files attached to them.
    
    Args:
        account_manager: AccountManager instance
        max_number: Maximum number of accounts to return (default: 5)
    
    Returns:
        list: List of accounts with files
    """
    try:
        accounts = account_manager.get_accounts_matching_condition(
            max_number=max_number,
            condition=lambda account: account_manager.account_has_files(account['id'])
        )
        
        if not accounts:
            logging.info("No accounts with files were found.")
        else:
            logging.info(f"Found {len(accounts)} accounts with files:")
            for account in accounts:
                logging.info(f"Name: {account['name']}, ID: {account['id']}, Files: {account['files_count']}")
        
        return accounts
    except Exception as e:
        logging.error(f"Error getting accounts with files: {str(e)}")
        return []

def test_get_accounts_matching_condition():
    """Test the get_accounts_matching_condition method of AccountsPage with a custom filter for accounts with more than 0 files."""
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            accounts_page = AccountsPage(page, debug_mode=True)
            account_manager = AccountManager(page, debug_mode=True)

            # Get accounts with files
            accounts = get_accounts_with_files(account_manager)
            
            # Verify we got the expected number of accounts
            assert len(accounts) <= 5, f"Expected at most 5 accounts, got {len(accounts)}"
            
            # Verify each account has files
            for account in accounts:
                assert account_manager.account_has_files(account['id']), f"Account {account['name']} should have files"
            
            logging.info("Test completed successfully")

        except Exception as e:
            logging.error(f"Test failed: {str(e)}")
            page.screenshot(path="test-failure.png")
            raise
        finally:
            browser.close()

def main():
    test_get_accounts_matching_condition()

if __name__ == "__main__":
    main() 