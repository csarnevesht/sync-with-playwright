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
- Analyzes file migration status with modified date prefix handling
- Supports batch processing with configurable size and start index

Process:
1. Takes input: either a single Dropbox account name or a list from a file
2. Extracts and normalizes the last name from each folder name
3. Searches Salesforce CRM using multiple strategies:
   - First by last name
   - Then by full name
   - Finally with any additional information
4. Analyzes search results to find exact and partial matches
5. If file analysis is enabled:
   - Lists Dropbox account files with modified dates
   - Lists Salesforce account files
   - Compares files between systems
   - Tracks file migration status
   - Verifies date prefix compliance
6. Generates a detailed report showing:
   - All search attempts and their results
   - Exact matches found (if any)
   - Partial matches with similarity details
   - File migration status
   - Date prefix compliance
   - Final migration status summary

Usage Examples:
    # Default behavior (lists all Dropbox accounts)
    python -m sync.cmd_analyzer

    # Search for a single account
    python -m sync.cmd_analyzer --dropbox-account-name="Alexander & Armelia Rolle"

    # Process multiple accounts from a file
    python -m sync.cmd_analyzer --dropbox-accounts-file=accounts/fuzzy.txt

    # Full analysis with file comparison
    python -m sync.cmd_analyzer --dropbox-accounts --dropbox-account-files --salesforce-accounts --salesforce-account-files

    # Batch processing with start index
    python -m sync.cmd_analyzer --dropbox-accounts --account-batch-size 5 --start-from 10

Output:
    - Detailed search results for each account
    - Summary table showing Dropbox account names and their Salesforce matches
    - File migration status with date prefix compliance
    - Clear indication of accounts and files that need attention
"""

import os
import sys
import argparse
from playwright.sync_api import sync_playwright, TimeoutError
import logging
from salesforce.pages.account_manager import AccountManager
from salesforce.utils.browser import get_salesforce_page
from dropbox_renamer.utils.account_utils import read_accounts_folders
from dropbox_renamer.utils.dropbox_utils import DropboxClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Analyze migration status of accounts from Dropbox to Salesforce')
    
    # Account Source Options (Mutually Exclusive)
    account_source = parser.add_mutually_exclusive_group()
    account_source.add_argument('--dropbox-account-name',
                      help='Single Dropbox account folder name to search for',
                      default=None)
    account_source.add_argument('--dropbox-accounts-file',
                      help='File containing list of Dropbox accounts',
                      default=None)
    
    # Analysis Scope Options
    parser.add_argument('--dropbox-accounts',
                      help='List all Dropbox accounts',
                      action='store_true')
    parser.add_argument('--dropbox-account-files',
                      help='List files for each Dropbox account',
                      action='store_true')
    parser.add_argument('--salesforce-accounts',
                      help='List all Salesforce accounts',
                      action='store_true')
    parser.add_argument('--salesforce-account-files',
                      help='List files for each Salesforce account',
                      action='store_true')
    
    # Processing Options
    parser.add_argument('--account-batch-size',
                      help='Number of accounts to process in each batch',
                      type=int,
                      default=None)
    parser.add_argument('--start-from',
                      help='Index to start processing from',
                      type=int,
                      default=0)
    parser.add_argument('--dropbox-accounts-only',
                      help='Process only Dropbox accounts',
                      action='store_true')
    
    return parser.parse_args()

def accounts_fuzzy_search(args):
    """
    Account fuzzy search functionality for accounts using last names from folder names.
    
    Args:
        args: Command line arguments containing all options
    """
    # Initialize account folders list
    ACCOUNT_FOLDERS = []

    # If a single account name is provided, use that
    if args.dropbox_account_name:
        ACCOUNT_FOLDERS = [args.dropbox_account_name]
        logging.info(f"Using provided Dropbox account name: {args.dropbox_account_name}")
    # If accounts file is provided, read from it
    elif args.dropbox_accounts_file:
        logging.info(f"Dropbox accounts file: {args.dropbox_accounts_file}")
        ACCOUNT_FOLDERS = read_accounts_folders(args.dropbox_accounts_file)
    # If --dropbox-accounts is specified or no source is provided, use default behavior
    elif args.dropbox_accounts or (not args.dropbox_account_name and not args.dropbox_accounts_file):
        # Initialize Dropbox client
        token = os.getenv('DROPBOX_TOKEN')
        if not token:
            logging.error("DROPBOX_TOKEN environment variable is not set")
            return
        dbx = DropboxClient(token, debug_mode=True)
        ACCOUNT_FOLDERS = dbx.get_account_folders()
        logging.info(f"Using all Dropbox accounts (total: {len(ACCOUNT_FOLDERS)})")

    # If no folders were found, use a default for testing
    if not ACCOUNT_FOLDERS:
        logging.warning("No account folders found, using default test folder")
        ACCOUNT_FOLDERS = ["Andrews, Kathleen"]

    # Apply batch size and start-from if specified
    if args.account_batch_size:
        start_idx = args.start_from
        end_idx = min(start_idx + args.account_batch_size, len(ACCOUNT_FOLDERS))
        ACCOUNT_FOLDERS = ACCOUNT_FOLDERS[start_idx:end_idx]
        logging.info(f"Processing batch of {len(ACCOUNT_FOLDERS)} accounts starting from index {start_idx}")

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
                
                # Get Dropbox files if requested
                dropbox_files = []
                if args.dropbox_account_files:
                    dbx = DropboxClient(os.getenv('DROPBOX_TOKEN'), debug_mode=True)
                    dropbox_files = dbx.get_account_files(folder_name)
                    logging.info(f"Found {len(dropbox_files)} files in Dropbox")
                
                # Perform fuzzy search
                result = account_manager.fuzzy_search_account(folder_name)
                results[folder_name] = result
                
                # Get exact matches for summary
                exact_matches = [match for match in result['matches'] if match in [attempt['query'] for attempt in result['search_attempts']]]
                salesforce_name = exact_matches[0] if exact_matches else "--"
                
                # Get Salesforce files if requested and account was found
                salesforce_files = []
                if args.salesforce_account_files and salesforce_name != "--":
                    salesforce_files = account_manager.get_account_files(salesforce_name)
                    logging.info(f"Found {len(salesforce_files)} files in Salesforce")
                
                # Compare files if both Dropbox and Salesforce files are available
                file_comparison = None
                if dropbox_files and salesforce_files:
                    file_comparison = compare_files(dropbox_files, salesforce_files)
                
                summary_results.append({
                    'dropbox_name': folder_name,
                    'salesforce_name': salesforce_name,
                    'dropbox_files': dropbox_files,
                    'salesforce_files': salesforce_files,
                    'file_comparison': file_comparison
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
                
                # Show file comparison if available
                if args.dropbox_account_files and args.salesforce_account_files:
                    print("\n📁 File Comparison:")
                    for result in summary_results:
                        if result['dropbox_name'] == folder_name and result['file_comparison']:
                            for file_status in result['file_comparison']:
                                print(f"   {file_status['status']} {file_status['file']}")
                                if file_status['details']:
                                    print(f"      {file_status['details']}")
                
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
                
                # Show file summary if available
                if args.dropbox_account_files and args.salesforce_account_files:
                    print("\nFile Migration Status:")
                    if result['file_comparison']:
                        migrated = sum(1 for f in result['file_comparison'] if f['status'] == '✓')
                        total = len(result['file_comparison'])
                        print(f"   {migrated}/{total} files migrated")
                        for file_status in result['file_comparison']:
                            if file_status['status'] != '✓':
                                print(f"   {file_status['status']} {file_status['file']}")
                                if file_status['details']:
                                    print(f"      {file_status['details']}")
                    else:
                        print("   No files to compare")
            
        except Exception as e:
            logging.error(f"Test failed with error: {str(e)}")
        finally:
            browser.close()
            logging.info(f"\n=== ANALYSIS COMPLETE ===")

def compare_files(dropbox_files, salesforce_files):
    """
    Compare files between Dropbox and Salesforce, checking for migration status and date prefix compliance.
    
    Args:
        dropbox_files: List of Dropbox files with metadata
        salesforce_files: List of Salesforce files
        
    Returns:
        List of file status objects with migration and prefix information
    """
    file_statuses = []
    
    for db_file in dropbox_files:
        original_name = db_file['name']
        modified_date = db_file['modified_date']
        expected_prefix = modified_date.strftime('%y%m%d')
        
        # Check for file in Salesforce with different prefix formats
        found = False
        prefix_status = None
        
        # Try original name
        if original_name in salesforce_files:
            found = True
            prefix_status = "Missing prefix"
        else:
            # Try with prefix formats
            prefixed_name_no_space = f"{expected_prefix}{original_name}"
            prefixed_name_with_space = f"{expected_prefix} {original_name}"
            
            if prefixed_name_no_space in salesforce_files:
                found = True
                prefix_status = "Correct prefix (no space)"
            elif prefixed_name_with_space in salesforce_files:
                found = True
                prefix_status = "Correct prefix (with space)"
        
        # Create status object
        status = {
            'file': original_name,
            'status': '✓' if found else '✗',
            'details': None
        }
        
        if found:
            if prefix_status != "Correct prefix (no space)":
                status['details'] = prefix_status
        else:
            status['details'] = f"Not found in Salesforce (expected prefix: {expected_prefix})"
        
        file_statuses.append(status)
    
    return file_statuses

if __name__ == "__main__":
    args = parse_args()
    accounts_fuzzy_search(args) 