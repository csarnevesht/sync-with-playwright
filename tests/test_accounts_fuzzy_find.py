"""
Test Account Fuzzy Search

This test verifies the fuzzy search functionality for accounts in Salesforce. It:
1. Takes a list of account folder names from a file
2. Extracts the last name from each folder name
3. Searches for accounts in Salesforce CRM using the last name
4. Verifies the search results
"""

import os
import sys
from playwright.sync_api import sync_playwright, TimeoutError
import logging
from salesforce.pages.account_manager import AccountManager
from get_salesforce_page import get_salesforce_page

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def read_account_folders(file_path: str) -> list:
    """
    Read account folders from a file.
    
    Args:
        file_path: Path to the file containing account folders
        
    Returns:
        list: List of account folder names
    """
    try:
        with open(file_path, 'r') as f:
            # Read lines and strip whitespace, skip empty lines
            folders = [line.strip() for line in f if line.strip()]
        logging.info(f"Read {len(folders)} account folders from {file_path}")
        return folders
    except Exception as e:
        logging.error(f"Error reading account folders file: {str(e)}")
        return []

# Get the root directory (parent of tests directory)
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Construct path to account_folders.txt in root directory
account_folders_file = os.path.join(root_dir, 'account_folders.txt')

# Read account folders from file
ACCOUNT_FOLDERS = read_account_folders(account_folders_file)

# If no folders were read, use a default for testing
if not ACCOUNT_FOLDERS:
    logging.warning("No account folders read from file, using default test folder")
    ACCOUNT_FOLDERS = ["Andrews, Kathleen"]

def test_accounts_fuzzy_find():
    """
    Test fuzzy search functionality for accounts using last names from folder names.
    """
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
            logging.info("\n=== SALESFORCE ACCOUNT MATCHES ===")
            for folder_name, result in results.items():
                logging.info(f"\n📁 Searching for: {folder_name}")
                logging.info(f"📊 Status: {result['status']}")
                
                # Show all unique matches found across all search attempts
                all_matches = set()
                for attempt in result['search_attempts']:
                    if attempt['matching_accounts']:
                        all_matches.update(attempt['matching_accounts'])
                # Also include matches from the main matches list
                all_matches.update(result['matches'])
                
                if all_matches:
                    logging.info("\n✅ All matching accounts found in Salesforce:")
                    for match in sorted(all_matches):
                        logging.info(f"   • {match}")
                else:
                    logging.info("\n❌ No matching accounts found in Salesforce")
                
                logging.info("\n🔍 Search details:")
                for attempt in result['search_attempts']:
                    if attempt['matching_accounts']:
                        logging.info(f"\n   Search type: {attempt['type']}")
                        logging.info(f"   Query used: '{attempt['query']}'")
                        logging.info(f"   Found {attempt['matches']} matches:")
                        for account in sorted(attempt['matching_accounts']):
                            logging.info(f"      - {account}")
                logging.info("=" * 50)
            
        except Exception as e:
            logging.error(f"Test failed with error: {str(e)}")
        finally:
            browser.close()

if __name__ == "__main__":
    test_accounts_fuzzy_find() 