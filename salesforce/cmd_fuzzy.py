"""
Test Account Fuzzy Search

This test verifies the fuzzy search functionality for accounts in Salesforce. It:
1. Takes a Dropbox account folder name as input
2. Extracts the last name from the folder name
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Test fuzzy search for Salesforce accounts')
    parser.add_argument('--dropbox-account-folder', 
                      help='Name of the Dropbox account folder to search for',
                      required=True)
    return parser.parse_args()

def accounts_fuzzy_search(dropbox_account_folder: str):
    """
    Account fuzzy search functionality for accounts using last names from folder names.
    
    Args:
        dropbox_account_folder: Name of the Dropbox account folder to search for.
    """
    # Print folder name at the start
    logging.info(f"Dropbox account folder: {dropbox_account_folder}")

    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            # Initialize account manager
            account_manager = AccountManager(page, debug_mode=True)
            
            # Navigate to accounts page
            if not account_manager.navigate_to_accounts_list_page():
                logging.error("Failed to navigate to accounts page")
                return
            
            # Process the folder name
            logging.info(f"\nProcessing folder: {dropbox_account_folder}")
            
            # Perform fuzzy search
            result = account_manager.fuzzy_search_account(dropbox_account_folder)
            
            # Print results summary
            print("\n=== SALESFORCE ACCOUNT MATCHES ===")
            print(f"\n📁 Searching for: {dropbox_account_folder}")
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
            # Print folder name at the end
            logging.info(f"\n=== TEST END ===")
            logging.info(f"Dropbox account folder: {dropbox_account_folder}")

if __name__ == "__main__":
    args = parse_args()
    accounts_fuzzy_search(args.dropbox_account_folder) 