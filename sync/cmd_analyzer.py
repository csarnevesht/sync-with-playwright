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
from sync.salesforce.pages.account_manager import AccountManager
from sync.salesforce.pages.file_manager import FileManager
from sync.salesforce.utils.browser import get_salesforce_page
from sync.dropbox.utils.account_utils import read_accounts_folders, read_ignored_folders
from sync.dropbox.utils.dropbox_utils import (
    DropboxClient,
    get_access_token,
    get_DROPBOX_FOLDER,
    clean_dropbox_path,
    list_folder_contents
)
from sync.dropbox.utils.date_utils import has_date_prefix
from dropbox.exceptions import ApiError
import dropbox
from typing import List, Union

# ANSI color codes
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Custom formatter to add colors to specific log messages
class ColoredFormatter(logging.Formatter):
    def format(self, record):
        if "Processing Dropbox account folder" in record.msg:
            record.msg = f"{Colors.BLUE}{Colors.BOLD}{record.msg}{Colors.ENDC}"
        return super().format(record)

# Apply the colored formatter
for handler in logger.handlers:
    handler.setFormatter(ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s'))

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Analyze migration status of accounts from Dropbox to Salesforce')
    
    # Environment file option
    parser.add_argument('--env-file', '-e', default='.env',
                      help='Path to .env file (default: .env)')
    
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

def initialize_dropbox_client():
    """
    Initialize Dropbox client with proper token handling and logging.
    
    Returns:
        DropboxClient: Initialized client or None if initialization fails
    """
    try:
        # Get access token with detailed logging
        logger.info("Attempting to get Dropbox access token...")
        token = get_access_token()
        
        if not token:
            logger.error("Failed to get Dropbox access token: No token found")
            return None
            
        # Log token details (first 10 chars for security)
        token_preview = token[:10] + "..." if len(token) > 10 else token
        logger.info(f"Successfully retrieved Dropbox token (starts with: {token_preview})")
        
        # Initialize client with debug mode
        logger.info("Initializing Dropbox client...")
        dbx = DropboxClient(token, debug_mode=True)
        
        # Test connection
        try:
            account = dbx.dbx.users_get_current_account()
            logger.info(f"Successfully connected to Dropbox as: {account.name.display_name}")
            logger.info(f"Account ID: {account.account_id}")
            logger.info(f"Email: {account.email}")
            return dbx
        except ApiError as e:
            if e.error.is_expired_access_token():
                logger.error("Dropbox access token has expired")
                logger.error("Please generate a new token and update your environment")
            else:
                logger.error(f"Failed to connect to Dropbox: {str(e)}")
            return None
            
    except Exception as e:
        logger.error(f"Unexpected error initializing Dropbox client: {str(e)}")
        return None

def accounts_fuzzy_search(args):
    """
    Account fuzzy search functionality for accounts using last names from folder names.
    
    Args:
        args: Command line arguments containing all options
    """
    # Initialize account folders list
    ACCOUNT_FOLDERS = []

    # Always read ignored folders
    try:
        ignored_folders = read_ignored_folders()
        if not ignored_folders:
            logger.warning("No ignored folders found or ignore file is empty")
    except Exception as e:
        logger.error(f"Error reading ignored folders: {str(e)}")
        ignored_folders = set()

    # If a single account name is provided, use that
    if args.dropbox_account_name:
        if args.dropbox_account_name in ignored_folders:
            logger.warning(f"Account {args.dropbox_account_name} is in the ignore list. Skipping...")
            return
        ACCOUNT_FOLDERS = [args.dropbox_account_name]
        logger.info(f"Using provided Dropbox account name: {args.dropbox_account_name}")
    # If accounts file is provided, read from it
    elif args.dropbox_accounts_file:
        logger.info(f"Dropbox accounts file: {args.dropbox_accounts_file}")
        ACCOUNT_FOLDERS = read_accounts_folders(args.dropbox_accounts_file)
        # Filter out ignored folders
        original_count = len(ACCOUNT_FOLDERS)
        ACCOUNT_FOLDERS = [folder for folder in ACCOUNT_FOLDERS if folder not in ignored_folders]
        ignored_count = original_count - len(ACCOUNT_FOLDERS)
        if ignored_count > 0:
            logger.info(f"Filtered out {ignored_count} ignored folders from the list")
        logger.info(f"Found {len(ACCOUNT_FOLDERS)} valid account folders after filtering ignored folders")
    
    # If --dropbox-accounts is specified or no source is provided, use default behavior
    elif args.dropbox_accounts or (not args.dropbox_account_name and not args.dropbox_accounts_file):
        # Initialize Dropbox client with enhanced logging
        dbx = initialize_dropbox_client()
        if not dbx:
            logger.error("Failed to initialize Dropbox client. Exiting...")
            return
            
        logger.info("Retrieving all Dropbox account folders...")
        try:
            # Get the root folder from environment
            root_folder = get_DROPBOX_FOLDER(args.env_file)
            if not root_folder:
                logger.error("Could not get DROPBOX_FOLDER from environment")
                return
                
            logger.info(f"Raw root folder from environment: {root_folder}")
            
            # Clean and validate the path
            try:
                clean_path = clean_dropbox_path(root_folder)
                logger.info(f"Cleaned Dropbox path: {clean_path}")
            except ValueError as e:
                logger.error(f"Invalid path format: {str(e)}")
                return
                
            if not clean_path:
                logger.error(f"Invalid path: {root_folder}")
                return
                
            # Try to get metadata first to check if path exists
            try:
                logger.info(f"Checking if path exists: {clean_path}")
                metadata = dbx.dbx.files_get_metadata(clean_path)
                logger.info(f"Path exists, type: {type(metadata).__name__}")
            except ApiError as e:
                if e.error.is_path() and e.error.get_path().is_not_found():
                    logger.error(f"Path not found: {clean_path}")
                    logger.error("Please check:")
                    logger.error("1. The path exists in your Dropbox")
                    logger.error("2. You have permission to access this path")
                    logger.error("3. The path is correctly formatted")
                    return
                raise
                
            # List all folders in the path
            logger.info(f"Listing contents of: {clean_path}")
            entries = list_folder_contents(dbx.dbx, clean_path)
            all_folders = [entry.name for entry in entries if isinstance(entry, dropbox.files.FolderMetadata)]
            
            # Filter out ignored folders
            original_count = len(all_folders)
            ACCOUNT_FOLDERS = [folder for folder in all_folders if folder not in ignored_folders]
            ignored_count = original_count - len(ACCOUNT_FOLDERS)
            
            if ignored_count > 0:
                logger.info(f"Filtered out {ignored_count} ignored folders from the list")
                logger.info("Ignored folders:")
                for folder in sorted(set(all_folders) - set(ACCOUNT_FOLDERS)):
                    logger.info(f"  - {folder}")
            
            if not ACCOUNT_FOLDERS:
                logger.warning(f"No valid folders found in path: {clean_path}")
                logger.info("Please check your Dropbox folder path and permissions")
                return
                
            logger.info(f"Successfully retrieved {len(ACCOUNT_FOLDERS)} folders from Dropbox (after filtering {ignored_count} ignored folders)")
            logger.info(f"Dropbox path used: {clean_path}")
            
        except ApiError as e:
            logger.error(f"Error listing folders: {str(e)}")
            logger.error("This could be due to:")
            logger.error("1. Invalid path format")
            logger.error("2. Insufficient permissions")
            logger.error("3. Network connectivity issues")
            return
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return

    # Apply batch size and start-from if specified
    if args.account_batch_size:
        start_idx = args.start_from
        end_idx = min(start_idx + args.account_batch_size, len(ACCOUNT_FOLDERS))
        ACCOUNT_FOLDERS = ACCOUNT_FOLDERS[start_idx:end_idx]
        logger.info(f"Processing batch of {len(ACCOUNT_FOLDERS)} accounts starting from index {start_idx}")

    if args.dropbox_accounts_only:
        total_folders = len(ACCOUNT_FOLDERS)
        print(f"Dropbox account folder names:")
        for index, folder_name in enumerate(ACCOUNT_FOLDERS, 1):
            print(f"    {index}. {folder_name}")
        return

    # List to store results for summary
    summary_results = []

    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            # Initialize account manager and file manager
            account_manager = AccountManager(page, debug_mode=True)
            file_manager = FileManager(page, debug_mode=True)
            
            # Dictionary to store results for each folder
            results = {}
            total_folders = len(ACCOUNT_FOLDERS)
            
            logger.info(f"\nStarting to process {total_folders} folders...")
            
            # Process each folder name
            for index, folder_name in enumerate(ACCOUNT_FOLDERS, 1):
                logger.info(f"\n[{index}/{total_folders}] Processing Dropbox account folder: {folder_name}")
                
                # Navigate to accounts page
                if not account_manager.navigate_to_accounts_list_page():
                    logger.error("Failed to navigate to accounts page")
                    continue
                
                # Get Dropbox files if requested
                dropbox_files = []
                if args.dropbox_account_files:
                    logger.info(f"Retrieving files for Dropbox account: {folder_name}")
                    dbx = initialize_dropbox_client()
                    if not dbx:
                        logger.error(f"Failed to initialize Dropbox client for folder {folder_name}. Skipping...")
                        continue
                        
                    try:
                        dropbox_files = dbx.get_account_files(folder_name)
                        logger.info(f"Successfully retrieved {len(dropbox_files)} files from Dropbox")
                    except ApiError as e:
                        logger.error(f"Failed to get files for folder {folder_name}: {str(e)}")
                        continue
                
                if not args.salesforce_accounts:
                    continue

                # Perform fuzzy search
                result = account_manager.fuzzy_search_account(folder_name)
                results[folder_name] = result
                
                # Get exact matches for summary
                if result['status'] == 'Exact Match' and result['matches']:
                    salesforce_name = result['matches'][0]
                else:
                    salesforce_name = "--"
                
                # Get Salesforce files if requested and account was found
                salesforce_files = []
                if args.salesforce_account_files and salesforce_name != "--":
                    # Navigate to the account and get its ID
                    if account_manager.click_account_name(salesforce_name):
                        is_valid, account_id = account_manager.verify_account_page_url()
                        if is_valid and account_id:
                            # Navigate to files section
                            logger.info("Navigating to files section")
                            logger.info(f"account_id: {account_id}")
                            num_files = account_manager.navigate_to_files_and_get_number_of_files_for_this_account(account_id)
                            if num_files == -1:
                                logging.error("Failed to navigate to Files")
                                return []
                            
                            salesforce_files = file_manager.get_all_file_names()
                            logger.info(f"Found {len(salesforce_files)} files in Salesforce")
                        else:
                            logger.error(f"Could not verify account page or get account ID for: {salesforce_name}")
                    else:
                        logger.error(f"Could not navigate to Salesforce account: {salesforce_name}")
                
                # Compare files if both Dropbox and Salesforce files are available
                file_comparison = None
                if dropbox_files and salesforce_files:
                    file_comparison = file_manager.compare_files(dropbox_files, salesforce_files)
                
                summary_results.append({
                    'dropbox_name': folder_name,
                    'salesforce_name': salesforce_name,
                    'dropbox_files': dropbox_files,
                    'salesforce_files': salesforce_files,
                    'file_comparison': file_comparison
                })
            
            # Print results summary
            if args.salesforce_accounts:
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
                
                if args.dropbox_account_files:
                    # Show Dropbox files
                    print("\n📁 Dropbox account files:")
                    for summary in summary_results:
                        if summary['dropbox_name'] == folder_name and summary['dropbox_files']:
                            sorted_files = sorted(summary['dropbox_files'], key=lambda x: x.name)
                            for i, file in enumerate(sorted_files, 1):
                                print(f"   + {i}. {file.name}")
                # Show file comparison if available
                if args.dropbox_account_files and args.salesforce_account_files:
                    # Show Salesforce files
                    print("\n📁 Salesforce account files:")
                    for summary in summary_results:
                        if summary['dropbox_name'] == folder_name and summary['salesforce_files']:
                            sorted_files = sorted(summary['salesforce_files'], 
                                key=lambda x: int(x.split('.')[0]) if x.split('.')[0].isdigit() else float('inf'))
                            for file in sorted_files:
                                print(f"   + {file}")
                    # Show comparison results
                    print("\n📁 File Comparison:")
                    for summary in summary_results:
                        if summary['dropbox_name'] == folder_name and summary['file_comparison']:
                            file_details = summary['file_comparison'].get('file_details', {})
                            for file_name, detail in file_details.items():
                                status = detail.get('status', '')
                                sf_file = detail.get('salesforce_file', '')
                                match_type = detail.get('match_type', '')
                                reason = detail.get('reason', '')
                                print(f"   {status} {file_name}")
                                if sf_file:
                                    print(f"      Matched Salesforce file: {sf_file} ({match_type})")
                                if reason:
                                    print(f"      {reason}")
                                potential_matches = detail.get('potential_matches', [])
                                if potential_matches:
                                    print(f"      Potential matches: {potential_matches}")
                
                print("=" * 50)
            
            # Print final summary
            print("\n=== SUMMARY ===")
            for result in summary_results:
                print(f"\nDropbox account folder name: {result['dropbox_name']}")
                salesforce_name = result['salesforce_name']
                if salesforce_name == "--":
                    print(f"Salesforce account name: -- [No exact match found]")
                else:
                    print(f"Salesforce account name: {salesforce_name} [Exact Match]")
                # Show file summary if available
                if args.dropbox_account_files and args.salesforce_account_files:
                    print("\nFile Migration Status:")
                    file_comparison = result.get('file_comparison')
                    if file_comparison:
                        matched = file_comparison.get('matched_files', 0)
                        total = file_comparison.get('total_files', 0)
                        print(f"   {matched}/{total} files matched")
                        missing_files = file_comparison.get('missing_files', [])
                        extra_files = file_comparison.get('extra_files', [])
                        if missing_files:
                            print("   Missing files in Salesforce:")
                            for f in missing_files:
                                print(f"      - {f}")
                        if extra_files:
                            print("   Extra files in Salesforce:")
                            for f in extra_files:
                                print(f"      - {f}")
                    else:
                        print("   No files to compare")
            
        except Exception as e:
            logger.error(f"Test failed with error: {str(e)}")
        finally:
            browser.close()
            logger.info(f"\n=== ANALYSIS COMPLETE ===")

if __name__ == "__main__":
    args = parse_args()
    accounts_fuzzy_search(args) 