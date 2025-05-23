"""
Test Account Fuzzy Search

This test verifies the fuzzy search functionality for accounts in Salesforce. It:
1. Takes a list of account folder names from a file in the accounts directory
2. Extracts the last name from each folder name
3. Searches for accounts in Salesforce CRM using the last name
4. Verifies the search results
"""

import os
import sys
import argparse
from playwright.sync_api import sync_playwright, TimeoutError
import logging
from salesforce.pages.account_manager import AccountManager
from salesforce.utils.browser import get_salesforce_page
from dropbox_renamer.utils.account_utils import read_accounts_folders

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Test fuzzy search for Salesforce accounts')
    parser.add_argument('--accounts-file', 
                      help='Name of the file in the accounts directory to read from (default: fuzzy.txt)',
                      default=None)
    return parser.parse_args()

def accounts_fuzzy_search(accounts_file: str = None):
    """
    Account fuzzy search functionality for accounts using last names from folder names.
    
    Args:
        accounts_file: Optional name of the file in the accounts directory to read from.
                      If not provided, defaults to 'fuzzy.txt'.
    """
    # Print accounts file and default options at the start
    accounts_file_path = accounts_file if accounts_file else 'accounts/fuzzy.txt'
    logging.info(f"Accounts file: {accounts_file_path}")
    logging.info(f"Default options: accounts_file='fuzzy.txt'")

    # Read account folders from file
    ACCOUNT_FOLDERS = read_accounts_folders(accounts_file)

    # If no folders were read, use a default for testing
    if not ACCOUNT_FOLDERS:
        logging.warning("No account folders read from file, using default test folder")
        ACCOUNT_FOLDERS = ["Andrews, Kathleen"]

    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            # Initialize account manager
            account_manager = AccountManager(page, debug_mode=True)
            
            # Navigate to accounts page
            if not account_manager.navigate_to_accounts_list_page():
                logging.error("Failed to navigate to accounts page")
                return
            
            # Dictionary to store results for each folder
            results = {}
            total_folders = len(ACCOUNT_FOLDERS)
            
            logging.info(f"\nStarting to process {total_folders} folders...")
            
            # Process each folder name
            for index, folder_name in enumerate(ACCOUNT_FOLDERS, 1):
                logging.info(f"\n[{index}/{total_folders}] Processing folder: {folder_name}")
                
                # Perform fuzzy search
                result = account_manager.fuzzy_search_account(folder_name)
                results[folder_name] = result
            
            # Print results summary
            print("\n=== SALESFORCE ACCOUNT MATCHES ===")
            for folder_name, result in results.items():
                print(f"\n📁 Searching for: {folder_name}")
                print(f"📊 Status: {result['status']}")
                
                # Show exact matches
                print("\n🔍 Exact Matches:")
                exact_matches = [match for match in result['matches'] if match in [attempt['query'] for attempt in result['search_attempts']]]
                if exact_matches:
                    for match in sorted(exact_matches):
                        print(f"   • {match}")
                else:
                    print("   • None found")
                
                # Show partial matches
                print("\n🔍 Partial Matches:")
                partial_matches = [match for match in result['matches'] if match not in exact_matches]
                if partial_matches:
                    for match in sorted(partial_matches):
                        print(f"   • {match}")
                else:
                    print("   • None found")
                
                print("\n📝 Search details:")
                for attempt in result['search_attempts']:
                    if attempt['matching_accounts']:
                        print(f"\n   Search type: {attempt['type']}")
                        print(f"   Query used: '{attempt['query']}'")
                        print(f"   Found {attempt['matches']} matches:")
                        for account in sorted(attempt['matching_accounts']):
                            print(f"      - {account}")
                print("=" * 50)
            
        except Exception as e:
            logging.error(f"Test failed with error: {str(e)}")
        finally:
            browser.close()
            # Print accounts file and default options at the end
            logging.info(f"\n=== TEST END ===")
            logging.info(f"Accounts file: {accounts_file_path}")
            logging.info(f"Default options: accounts_file='fuzzy.txt'")

if __name__ == "__main__":
    args = parse_args()
    accounts_fuzzy_search(args.accounts_file) 