"""
Account Salesforce Fuzzy Search

This command helps analyze the migration status of accounts from Dropbox to Salesforce.
It performs a smart search that handles various name formats and provides detailed matching information.

Key Features:
- Supports both single account search and batch processing from a file
- Handles complex name formats (with/without commas, ampersands, parentheses)
- Performs multiple search attempts to find the best matches
- Shows detailed search results including exact and partial matches
- Provides a clear summary of migration status for each account

Process:
1. Takes input: either a single Dropbox account name or a list from a file
2. Extracts and normalizes the last name from each folder name
3. Searches Salesforce CRM using multiple strategies:
   - First by last name
   - Then by full name
   - Finally with any additional information
4. Analyzes search results to find exact and partial matches
5. Generates a detailed report showing:
   - All search attempts and their results
   - Exact matches found (if any)
   - Partial matches with similarity details
   - Final migration status summary

Usage Examples:
    # Search for a single account
    python -m sync.cmd_migration_analyzer --dropbox-account-name="Alexander & Armelia Rolle"

    # Process multiple accounts from a file
    python -m sync.cmd_migration_analyzer --dropbox-accounts-file=accounts/fuzzy.txt

Output:
    - Detailed search results for each account
    - Summary table showing Dropbox account names and their Salesforce matches
    - Clear indication of accounts that need attention (no matches found)
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
    parser.add_argument('--dropbox-accounts-file', 
                      help='Name of the file containing Dropbox account folders (default: fuzzy.txt)',
                      default=None)
    parser.add_argument('--dropbox-account-name',
                      help='Single Dropbox account folder name to search for',
                      default=None)
    return parser.parse_args()

def accounts_fuzzy_search(accounts_file: str = None, account_name: str = None):
    """
    Account fuzzy search functionality for accounts using last names from folder names.
    
    Args:
        accounts_file: Optional name of the file containing Dropbox account folders.
                      If not provided, defaults to 'fuzzy.txt'.
        account_name: Optional single Dropbox account folder name to search for.
    """
    # Initialize account folders list
    ACCOUNT_FOLDERS = []

    # If a single account name is provided, use that
    if account_name:
        ACCOUNT_FOLDERS = [account_name]
        logging.info(f"Using provided Dropbox account name: {account_name}")
    else:
        # Otherwise, read from file
        accounts_file_path = accounts_file if accounts_file else 'accounts/fuzzy.txt'
        logging.info(f"Dropbox accounts file: {accounts_file_path}")
        logging.info(f"Default options: dropbox_accounts_file='fuzzy.txt'")

        # Read account folders from file
        ACCOUNT_FOLDERS = read_accounts_folders(accounts_file)

        # If no folders were read, use a default for testing
        if not ACCOUNT_FOLDERS:
            logging.warning("No account folders read from file, using default test folder")
            ACCOUNT_FOLDERS = ["Andrews, Kathleen"]

    # List to store results for summary
    summary_results = []

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
                
                # Get exact matches for summary
                exact_matches = [match for match in result['matches'] if match in [attempt['query'] for attempt in result['search_attempts']]]
                salesforce_name = exact_matches[0] if exact_matches else "--"
                summary_results.append({
                    'dropbox_name': folder_name,
                    'salesforce_name': salesforce_name
                })
            
            # Print results summary
            print("\n=== SALESFORCE ACCOUNT MATCHES ===")
            for folder_name, result in results.items():
                print(f"\nDropbox account folder name: {folder_name}")
                
                # Get exact matches
                exact_matches = [match for match in result['matches'] if match in [attempt['query'] for attempt in result['search_attempts']]]
                
                # Show Salesforce account name based on exact matches
                if exact_matches:
                    print(f"Salesforce account name: {exact_matches[0]}")  # Show first exact match
                else:
                    print("Salesforce account name: None")
                
                # Show search details if there are any matches
                if result['matches']:
                    print("\n📝 Search details:")
                    for attempt in result['search_attempts']:
                        if attempt['matching_accounts']:
                            print(f"\n   Search type: {attempt['type']}")
                            print(f"   Query used: '{attempt['query']}'")
                            print(f"   Found {attempt['matches']} matches:")
                            for account in sorted(attempt['matching_accounts']):
                                print(f"      - {account}")
                print("=" * 50)
            
            # Print final summary
            print("\n=== SUMMARY ===")
            for result in summary_results:
                print(f"\nDropbox account folder name: {result['dropbox_name']}")
                salesforce_name = result['salesforce_name']
                if salesforce_name == "--":
                    print(f"Salesforce account name: -- [No exact match found]")
                else:
                    print(f"Salesforce account name: {salesforce_name}")
            
        except Exception as e:
            logging.error(f"Test failed with error: {str(e)}")
        finally:
            browser.close()
            # Print accounts file and default options at the end
            logging.info(f"\n=== TEST END ===")
            if not account_name:
                logging.info(f"Dropbox accounts file: {accounts_file_path}")
                logging.info(f"Default options: dropbox_accounts_file='fuzzy.txt'")

if __name__ == "__main__":
    args = parse_args()
    accounts_fuzzy_search(args.dropbox_accounts_file, args.dropbox_account_name) 