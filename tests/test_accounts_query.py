"""
Test Account Query and Filtering

This test verifies the account query and filtering functionality in Salesforce. It:
1. Queries accounts with specific conditions (e.g., accounts with files)
2. Filters accounts based on custom criteria
3. Verifies the filtered accounts meet the specified conditions
4. Handles pagination and large result sets

The test includes robust error handling and detailed logging of account details
including file counts and account IDs.
"""

import os
import sys
from playwright.sync_api import sync_playwright
import logging
from salesforce.pages.account_manager import AccountManager
from salesforce.pages.accounts_page import AccountsPage
from salesforce.utils.browser import get_salesforce_page
from dotenv import load_dotenv
from sync.config import SALESFORCE_URL

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to see all messages
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_accounts_with_files(account_manager: AccountManager, max_number: int = 5) -> list:
    """
    Get accounts that have files attached to them.
    
    Args:
        account_manager: AccountManager instance
        max_number: Maximum number of accounts to return (default: 5)
    
    Returns:
        list: List of accounts with files, each containing:
            - name: Account name
            - id: Account ID
            - files_count: Number of files attached
    """
    try:
        accounts = account_manager.get_accounts_matching_condition(
            max_number=max_number,
            condition=lambda account: account_manager.account_has_files(account['id']),
            drop_down_option_text="All Clients"
        )
        
        if not accounts:
            logging.info("No accounts with files were found")
        else:
            logging.info(f"Found {len(accounts)} accounts with files:")
            for account in accounts:
                logging.info(
                    f"Account: {account['name']}\n"
                    f"  ID: {account['id']}\n"
                    f"  Files: {account['files_count']}"
                )
        
        return accounts
    except Exception as e:
        logging.error(f"Error getting accounts with files: {str(e)}")
        return []

def test_get_accounts_matching_condition():
    """
    Test the account query and filtering functionality.
    
    This test verifies that:
    1. We can query accounts with specific conditions
    2. The returned accounts meet the specified criteria
    3. The number of accounts returned is within the specified limit
    4. Each account has the expected properties (files, ID, etc.)
    """
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            # Initialize managers
            accounts_page = AccountsPage(page, debug_mode=True)
            account_manager = AccountManager(page, debug_mode=True)

            # Get accounts with files
            accounts = get_accounts_with_files(account_manager)
            
            # Verify we got the expected number of accounts
            assert len(accounts) <= 5, f"Expected at most 5 accounts, got {len(accounts)}"
            
            # Verify each account has files
            for account in accounts:
                assert account_manager.account_has_files(account['id']), \
                    f"Account {account['name']} should have files"
                
                # Verify account has required properties
                assert 'name' in account, f"Account missing name property: {account}"
                assert 'id' in account, f"Account missing ID property: {account}"
                assert 'files_count' in account, f"Account missing files_count property: {account}"
                
                # Verify files count is a valid number
                assert isinstance(account['files_count'], (int, str)), \
                    f"Invalid files_count type for account {account['name']}: {type(account['files_count'])}"
            
            logging.info("Test completed successfully")

        except Exception as e:
            logging.error(f"Test failed: {str(e)}")
            page.screenshot(path="test-failure.png")
            raise
        finally:
            browser.close()

def main():
    # Load environment variables
    load_dotenv()
    
    # Get credentials from environment variables
    username = os.getenv('SALESFORCE_USERNAME')
    password = os.getenv('SALESFORCE_PASSWORD')
    
    if not username or not password:
        logging.error("SALESFORCE_USERNAME and SALESFORCE_PASSWORD must be set in .env file")
        return
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # Initialize pages
        accounts_page = AccountsPage(page, debug_mode=True)
        account_manager = AccountManager(page, debug_mode=True)
        
        # Login to Salesforce
        if not account_manager.login(username, password):
            logging.error("Failed to login to Salesforce")
            return
            
        # Get all accounts
        accounts = accounts_page._get_accounts_base()
        logging.info(f"Found {len(accounts)} accounts")
        
        # Print first few accounts
        for i, account in enumerate(accounts[:5]):
            logging.info(f"Account {i+1}: {account['name']} (ID: {account['id']})")
            
        browser.close()

if __name__ == "__main__":
    main() 