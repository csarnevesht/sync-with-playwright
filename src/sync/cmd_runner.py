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
    python -m sync.cmd_runner

    # Search for a single account
    python -m sync.cmd_runner --dropbox-account-name="Alexander & Armelia Rolle"

    # Process multiple accounts from a file
    python -m sync.cmd_runner --dropbox-accounts-file=accounts/fuzzy.txt

    # Full analysis with file comparison
    python -m sync.cmd_runner --dropbox-accounts --dropbox-account-files --salesforce-accounts --salesforce-account-files

    # Batch processing with start index
    python -m sync.cmd_runner --dropbox-accounts --account-batch-size 5 --start-from 10

Output:
    - Detailed search results for each account
    - Summary table showing Dropbox account names and their Salesforce matches
    - File migration status with date prefix compliance
    - Clear indication of accounts and files that need attention

RESULTS DICTIONARY STRUCTURE:
----------------------------
The 'results' dictionary maps each Dropbox folder name (str) to a dictionary containing the Salesforce search results for that account. Example structure:

results = {
    'Montesino, Maria': {
        'matches': [<list of matched Salesforce account names>],
        'match_info': {
            'match_status': 'Exact Match' | 'No Match' | ...,
            ...
        },
        'view': <Salesforce view name>,
        'status': <status string>,
        'search_info': {
            'account_data': {
                'name': <Dropbox account name>,
                'first_name': <first name>,
                'last_name': <last name>,
                ... (other fields from Dropbox account info)
            },
            ...
        },
        ... (other keys, e.g., 'expected_salesforce_matches', 'file_comparison', etc.)
    },
    ...
}

Each value is a dictionary (the Salesforce search result) with at least:
- 'matches': list of Salesforce account names matched
- 'match_info': dict with at least 'match_status' (e.g., 'Exact Match', 'No Match')
- 'view': Salesforce view name (e.g., 'All Clients')
- 'status': status string for the search
- 'search_info': dict with Dropbox account info, including 'account_data' (fields like name, first_name, last_name, etc.)
- (other keys may be present depending on the run options)
"""

import os
import sys
import argparse
import time
import re

from sync import salesforce_client
from sync.utils.name_utils import extract_name_parts
from src.sync.utils.duration import format_duration
from playwright.sync_api import sync_playwright, TimeoutError
import logging
from datetime import datetime
from pathlib import Path
from src.sync.salesforce_client.pages.account_manager import AccountManager
from src.sync.salesforce_client.pages.file_manager import SalesforceFileManager
from src.sync.salesforce_client.utils.browser import get_salesforce_page
from src.sync.dropbox_client.utils.account_utils import (
    read_accounts_folders,
    read_ignored_folders
)
from src.sync.dropbox_client.utils.dropbox_utils import (
    DropboxClient,
    get_access_token,
    get_folder_metadata,
    get_dropbox_root_folder,
    get_folder_creation_date
)
from src.sync.dropbox_client.utils.date_utils import has_date_prefix
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
    CYAN = '\033[96m'  # Add cyan color for better visibility

# Custom formatter to add colors to specific log messages
class ColoredFormatter(logging.Formatter):
    def format(self, record):
        if "Processing Dropbox account folder" in record.msg:
            # Make the message bold and cyan for better visibility
            record.msg = f"{Colors.CYAN}{Colors.BOLD}{record.msg}{Colors.ENDC}"
        return super().format(record)

# Custom formatter for report logging (no timestamp or level)
class ReportFormatter(logging.Formatter):
    def format(self, record):
        return record.getMessage()

def format_args_for_logging(args):
    """Format command line arguments for logging.
    
    Args:
        args: The parsed command line arguments
        
    Returns:
        str: Formatted string of arguments
    """
    # Get all non-None arguments
    arg_dict = {k: v for k, v in vars(args).items() if v is not None}
    
    # Format the arguments
    formatted_args = []
    for key, value in arg_dict.items():
        if isinstance(value, bool):
            if value:  # Only include True boolean flags
                formatted_args.append(f"--{key}")
        else:
            formatted_args.append(f"--{key}={value}")
    
    return " ".join(formatted_args)

def setup_logging(args):
    """Configure logging to write to both file and console with colored output.
    
    Args:
        args: The parsed command line arguments
    """
    # Create logs directory with date and time-based subfolder
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_dir = Path('logs') / timestamp
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create log files directly in the timestamped folder
    log_file = log_dir / 'analyzer.log'
    report_file = log_dir / 'report.log'
    
    # Create formatters
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_formatter = ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s')
    report_formatter = ReportFormatter()
    
    # Create file handler for main log
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Create file handler for report log
    report_handler = logging.FileHandler(report_file)
    report_handler.setFormatter(report_formatter)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.DEBUG)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Configure account_manager logger
    account_manager_logger = logging.getLogger('account_manager')
    account_manager_logger.setLevel(logging.INFO)
    account_manager_logger.addHandler(file_handler)
    
    # Create a separate logger for reports
    report_logger = logging.getLogger('report')
    report_logger.setLevel(logging.INFO)
    report_logger.addHandler(report_handler)
    
    # Log the command and arguments
    command = f"python -m sync.cmd_runner {format_args_for_logging(args)}"
    root_logger.info(f"Command: {command}")
    report_logger.info(f"Command: {command}")
    
    # Log the log file locations
    root_logger.info(f"Main log file: {log_file}")
    report_logger.info(f"Report log file: {report_file}")
    
    return root_logger, report_logger

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Analyze migration status of accounts from Dropbox to Salesforce')
    
    # Environment file option
    parser.add_argument('--env-file', '-e', default='.env',
                      help='Path to .env file (default: .env)')
    
    # Add commands arguments
    parser.add_argument('--commands',
                      help='Comma-separated list of commands to execute')
    parser.add_argument('--commands-file',
                      help='Path to file containing commands to execute (one per line)')
    parser.add_argument('--continue-on-error',
                      action='store_true',
                      help='Continue executing remaining commands even if one fails')
    
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
    parser.add_argument('--dropbox-accounts-and-name-parts',
                      help='List all Dropbox accounts with their parsed name parts',
                      action='store_true')
    parser.add_argument('--dropbox-account-files',
                      help='List files for each Dropbox account',
                      action='store_true')
    parser.add_argument('--dropbox-account-info',
                      help='Extract info for each Dropbox account',
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
    
    
      

def run_command(args):
    """
    Run command
    
    Args:
        args: Command line arguments containing all options
    """

    start_time = time.time()

    # Initialize account folders list
    ACCOUNT_FOLDERS = []

    dropbox_root_folder = get_dropbox_root_folder(args.env_file, report_logger)
    logger.info(f"Dropbox root path: {dropbox_root_folder}")
    
    logger.info("step: Read Ignored Folders")
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
        logger.info('step: Get Account Folders')
        if args.dropbox_account_name in ignored_folders:
            logger.warning(f"Account {args.dropbox_account_name} is in the ignore list. Skipping...")
            report_logger.info(f"\nAccount {args.dropbox_account_name} is in the ignore list. Skipping...")
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
        logger.info("step: Get Dropbox Account Folders")
        # Initialize Dropbox client with enhanced logging
        dropbox_client = initialize_dropbox_client()
        if not dropbox_client:
            logger.error("Failed to initialize Dropbox client. Exiting...")
            report_logger.info("\nFailed to initialize Dropbox client. Exiting...")
            return
            
        logger.info("Retrieving all Dropbox account folders...")
        try:
                
            # Try to get metadata first to check if path exists
            try:
                logger.info(f"Checking if path exists: {dropbox_root_folder}")
                metadata = dropbox_client.dbx.files_get_metadata(dropbox_root_folder)
                logger.info(f"Path exists, type: {type(metadata).__name__}")
            except ApiError as e:
                if e.error.is_path() and e.error.get_path().is_not_found():
                    logger.error(f"Path not found: {dropbox_root_folder}")
                    logger.error("Please check:")
                    logger.error("1. The path exists in your Dropbox")
                    logger.error("2. You have permission to access this path")
                    logger.error("3. The path is correctly formatted")
                    report_logger.info(f"\nPath not found: {dropbox_root_folder}")
                    report_logger.info("Please check:")
                    report_logger.info("1. The path exists in your Dropbox")
                    report_logger.info("2. You have permission to access this path")
                    report_logger.info("3. The path is correctly formatted")
                    return
                raise
                
            # List all folders in the path
            logger.info(f"Getting all account folders from: {dropbox_client.root_folder}")
            all_account_folders = dropbox_client.get_dropbox_account_names()
            
            # Filter out ignored folders
            original_count = len(all_account_folders)
            ACCOUNT_FOLDERS = [folder for folder in all_account_folders if folder not in ignored_folders]
            ignored_count = original_count - len(ACCOUNT_FOLDERS)
            
            if ignored_count > 0:
                logger.info(f"Filtered out {ignored_count} ignored folders from the list")
                logger.info("Ignored folders:")
                for folder in sorted(set(all_account_folders) - set(ACCOUNT_FOLDERS)):
                    logger.info(f"  - {folder}")
            
            if not ACCOUNT_FOLDERS:
                logger.warning(f"No valid folders found in path: {dropbox_root_folder}")
                logger.info("Please check your Dropbox folder path and permissions")
                report_logger.info(f"\nNo valid folders found in path: {dropbox_root_folder}")
                report_logger.info("Please check your Dropbox folder path and permissions")
                return
                
            logger.info(f"Successfully retrieved {len(ACCOUNT_FOLDERS)} folders from Dropbox (after filtering {ignored_count} ignored folders)")
            logger.info(f"Dropbox folder used: {dropbox_root_folder}")
            
        except ApiError as e:
            logger.error(f"Error listing folders: {str(e)}")
            logger.error("This could be due to:")
            logger.error("1. Invalid path format")
            logger.error("2. Insufficient permissions")
            logger.error("3. Network connectivity issues")
            report_logger.info(f"\nError listing folders: {str(e)}")
            report_logger.info("This could be due to:")
            report_logger.info("1. Invalid path format")
            report_logger.info("2. Insufficient permissions")
            report_logger.info("3. Network connectivity issues")
            return
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            report_logger.info(f"\nUnexpected error: {str(e)}")
            return

    # Apply batch size and start-from if specified
    if args.account_batch_size:
        start_idx = args.start_from
        end_idx = min(start_idx + args.account_batch_size, len(ACCOUNT_FOLDERS))
        ACCOUNT_FOLDERS = ACCOUNT_FOLDERS[start_idx:end_idx]
        logger.info(f"Processing batch of {len(ACCOUNT_FOLDERS)} accounts starting from index {start_idx}")

    if args.dropbox_accounts_only:
        total_folders = len(ACCOUNT_FOLDERS)
        logger.info(f"Dropbox account folder names:")
        report_logger.info("\n=== DROPBOX ACCOUNT FOLDERS ===")
        for index, dropbox_account_folder_name in enumerate(ACCOUNT_FOLDERS, 1):
            logger.info(f"    {index}. {dropbox_account_folder_name}")
            report_logger.info(f"{index}. {dropbox_account_folder_name}")
        return

    if args.dropbox_accounts_and_name_parts:
        total_folders = len(ACCOUNT_FOLDERS)
        logger.info(f"Dropbox account folder names with parsed parts:")
        report_logger.info("\n=== DROPBOX ACCOUNT FOLDERS WITH PARSED PARTS ===")
        for index, dropbox_account_folder_name in enumerate(ACCOUNT_FOLDERS, 1):
            name_parts = extract_name_parts(dropbox_account_folder_name)
            logger.info(f"\n{index}. {dropbox_account_folder_name}")
            logger.info(f"   First Name: {name_parts['first_name']}")
            logger.info(f"   Last Name: {name_parts['last_name']}")
            logger.info(f"   Middle Name: {name_parts['middle_name']}")
            logger.info(f"   Additional Info: {name_parts['additional_info']}")
            logger.info(f"   Full Name: {name_parts['full_name']}")
            logger.info(f"   Normalized Names: {name_parts['normalized_names']}")
            logger.info(f"   Swapped Names: {name_parts['swapped_names']}")
            logger.info(f"   Expected Dropbox Matches: {name_parts.get('expected_dropbox_matches', [])}")
            logger.info(f"   Expected Salesforce Matches: {name_parts.get('expected_salesforce_matches', [])}")

            report_logger.info(f"\n{index}. {dropbox_account_folder_name}")
            report_logger.info(f"   First Name: {name_parts['first_name']}")
            report_logger.info(f"   Last Name: {name_parts['last_name']}")
            report_logger.info(f"   Middle Name: {name_parts['middle_name']}")
            report_logger.info(f"   Additional Info: {name_parts['additional_info']}")
            report_logger.info(f"   Full Name: {name_parts['full_name']}")
            report_logger.info(f"   Normalized Names: {name_parts['normalized_names']}")
            report_logger.info(f"   Swapped Names: {name_parts['swapped_names']}")
            report_logger.info(f"   Expected Dropbox Matches: {name_parts.get('expected_dropbox_matches', [])}")
            report_logger.info(f"   Expected Salesforce Matches: {name_parts.get('expected_salesforce_matches', [])}")
        return

    # List to store results for summary
    summary_results = []

    logger.info('step: Process Dropbox Account folders')
    
    # Initialize Dropbox client once before Playwright context
    dropbox_client = initialize_dropbox_client()
    if not dropbox_client:
        logger.error("Failed to initialize Dropbox client. Exiting...")
        report_logger.info("Failed to initialize Dropbox client. Exiting...")
        return

    with sync_playwright() as p:
        try:
            # Only initialize Salesforce components if Salesforce flags are set
            browser = None
            page = None
            account_manager = None
            file_manager = None
            view_name="All Clients"
            
            if args.salesforce_accounts or args.salesforce_account_files:
                browser, page = get_salesforce_page(p)
                # Initialize account manager and file manager
                account_manager = AccountManager(page, debug_mode=True)
                account_manager.logger.report_logger = report_logger  # Add report logger
                file_manager = SalesforceFileManager(page, debug_mode=True)
            
            command_runner = None
            
            # Initialize command runner if commands are specified
            if args.commands or args.commands_file:
                from src.sync.command_runner import CommandRunner
                command_runner = CommandRunner(args)
                command_runner.set_context('salesforce_client', salesforce_client)
                command_runner.set_context('dropbox_client', dropbox_client)
                command_runner.set_context('dropbox_root_folder', dropbox_root_folder)
                if browser and page:
                    command_runner.set_context('browser', browser)
                    command_runner.set_context('page', page)
                    command_runner.set_context('account_manager', account_manager)
                    command_runner.set_context('file_manager', file_manager)
                
            # Dictionary to store results for each folder
            results = {}
            total_folders = len(ACCOUNT_FOLDERS)
            
            if total_folders == 0:
                logger.warning("No Dropbox accounts to process")
                report_logger.info("\nNo Dropbox accounts to process")
                return
            
            logger.info(f"Starting to process {total_folders} folders...")
            report_logger.info(f"\nStarting to process {total_folders} folders...")

            excel_file = None
            if args.dropbox_account_info:
                holiday_file, temp_path, excel_file, sheets = dropbox_client._process_holiday_file()
                if not all([holiday_file, temp_path, excel_file, sheets]):
                    logger.error("Failed to process holiday file")
                    report_logger.info("Failed to process holiday file")
                    return
            
            # Process each folder name
            for index, dropbox_account_folder_name in enumerate(ACCOUNT_FOLDERS, 1):
                logger.info(f"[{index}/{total_folders}] Processing Dropbox account folder: {dropbox_account_folder_name}")
                report_logger.info(f"\n[{index}/{total_folders}] Processing Dropbox account folder: {dropbox_account_folder_name}")
                                
                if command_runner:
                    command_runner.set_data('dropbox_account_name', dropbox_account_folder_name)
                
                logger.info('step: Extract name parts')
                # # Always extract name parts
                dropbox_account_name_parts = extract_name_parts(dropbox_account_folder_name, log=True)

            
                
                # Navigate to Salesforce base URL
                if args.salesforce_accounts and account_manager:    
                    logger.info(f"Navigating to Salesforce")
                    if not account_manager.navigate_to_salesforce():
                        logger.error("Failed to navigate to Salesforce base URL")
                        report_logger.info("Failed to navigate to Salesforce base URL")
                        return
                    logger.info("Refreshing page")
                    account_manager.refresh_page()

                if args.dropbox_account_info:
                    # DROPBOX ACCOUNT INFO
                    logger.info('step: Search for Dropbox Account Info')
                    # Always get account info since it's needed for commands
                    logger.info(f"Getting info for Dropbox account: {dropbox_account_folder_name}")
                    try:
                        dropbox_account_search_result = dropbox_client.dropbox_search_account(dropbox_account_folder_name, dropbox_account_name_parts, excel_file)
                        logger.info(f'dropbox_account_search_result: {dropbox_account_search_result}')
                        logger.info(f"Successfully retrieved info for Dropbox account: {dropbox_account_folder_name}")
                        
                        if command_runner:
                            command_runner.set_data('dropbox_account_info', dropbox_account_search_result)
                    except ApiError as e:
                        logger.error(f"Failed to get info for folder {dropbox_account_folder_name}: {str(e)}")
                        report_logger.info(f"Failed to get info for folder {dropbox_account_folder_name}: {str(e)}")
                        continue

                # Navigate to accounts page
                if args.salesforce_accounts and account_manager:
                    logger.info('Navigating to accounts page')
                    if not account_manager.navigate_to_accounts_list_page():
                        logger.error("Failed to navigate to accounts page")
                        report_logger.info("Failed to navigate to accounts page")
                        continue

                # Get Dropbox files if requested
                dropbox_account_file_names = []
                if args.dropbox_account_files:
                    logger.info(f"step: Retrieving files for Dropbox account: {dropbox_account_folder_name}")
                    try:
                        # DROPBOX ACCOUNT FILES
                        dropbox_account_file_names = dropbox_client.get_dropbox_account_files(dropbox_account_folder_name)
                        logger.info(f"Successfully retrieved {len(dropbox_account_file_names)} files from Dropbox")
                        report_logger.info(f"\n📁 Dropbox account files: [account: {dropbox_account_folder_name}] [files: {len(dropbox_account_file_names)}]")
                        sorted_files = sorted(dropbox_account_file_names, key=lambda x: x.name)
                        for i, file in enumerate(sorted_files, 1):
                            report_logger.info(f"   + {i}. {file.name}")

                        if command_runner:
                            command_runner.set_data('dropbox_account_file_names', dropbox_account_file_names)
                            command_runner.set_data('dropbox_account_folder_name', dropbox_account_folder_name)
                            
                    except ApiError as e:
                        logger.error(f"Failed to get files for folder {dropbox_account_folder_name}: {str(e)}")
                        report_logger.info(f"Failed to get files for folder {dropbox_account_folder_name}: {str(e)}")
                        continue
                
                if args.salesforce_accounts and account_manager:
                    logger.info('step: Salesforce Search Account')
                    # Perform fuzzy search
                    salesforce_account_search_result = account_manager.salesforce_search_account(dropbox_account_folder_name, view_name, dropbox_account_name_parts=dropbox_account_name_parts)
                    results[dropbox_account_folder_name] = {
                        'salesforce_account_search_result': salesforce_account_search_result,
                        'dropbox_account_search_result': dropbox_account_search_result
                    }

                    logger.debug(f"*** salesforce search result: {salesforce_account_search_result}")

                    # --- START: New grouped logging for report.log and analyzer.log ---
                    dropbox_folder_name = dropbox_account_folder_name
                    salesforce_matches = salesforce_account_search_result.get('matches', [])
                    salesforce_account_name = salesforce_matches[0] if salesforce_matches else '--'
                    salesforce_match = salesforce_account_search_result['match_info']['match_status'] if 'match_info' in salesforce_account_search_result else 'No match found'
                    salesforce_view = salesforce_account_search_result.get('view', '--')

                log_block = f"""
📁 **Dropbox Folder**
   - Name: {dropbox_account_folder_name}
   
📄 **Dropbox Account Search** 
"""
                if args.dropbox_account_info:
                    dropbox_account_data = dropbox_account_search_result.get('account_data', {})
                    for key, value in dropbox_account_data.items():
                        log_block += f"   + {key}: {value}\n"
                    log_block += "\n"
                if args.salesforce_accounts:
                    log_block = f"""
   
👤 **Salesforce Account Search**
   - Name found: {salesforce_account_name}
   - Match: {salesforce_match}
   - View: {salesforce_view}
"""                 
                print('*********log_block*********', log_block)
                report_logger.info(log_block)
                # --- END: New grouped logging ---
                # CAROLINA HERE

                build_and_log_summary_line({
                    'dropbox_name': dropbox_account_folder_name,
                    'salesforce_account_search_result': salesforce_account_search_result if args.salesforce_accounts else {},
                    'dropbox_account_search_result': dropbox_account_search_result
                }, report_logger, args)

                # Get Salesforce files if requested and account was found
                salesforce_account_file_names = []
                if args.salesforce_account_files and salesforce_matches and len(salesforce_matches) > 0 and salesforce_matches  != "--":
                    salesforce_matches  = salesforce_account_search_result['matches']
                    logger.info(f"*** salesforce_matches: {salesforce_matches}")
                    logger.info(f"step: Get Salesforce Account Files")
                    # For multiple matches, we'll check files for the first match
                    logger.info("for multiple matches, we'll check files for the first match")
                    account_to_check = salesforce_matches[0] if isinstance(salesforce_matches, list) else salesforce_matches 
                    logger.info(f"accounts_to_check: {account_to_check}")
                    # Navigate to the account and get its ID
                    logger.info(f"click_account_name: {account_to_check}")
                    if account_manager.click_account_name(account_to_check):
                        logger.info("verify_account_page_url")
                        is_valid, salesforce_account_id = account_manager.verify_account_page_url()
                        if is_valid and salesforce_account_id:
                            logger.info(f"salesforce_account_id: {salesforce_account_id}")
                            if command_runner:  
                                command_runner.set_data('salesforce_account_id', salesforce_account_id)
                            logger.info(f"salesforce_account_id: {salesforce_account_id}")

                            logger.info(f"get salesforce account file names")
                            salesforce_account_file_names = account_manager.get_salesforce_account_file_names(salesforce_account_id)
                            logger.info(f"Found {len(salesforce_account_file_names)} files in Salesforce")

                            if command_runner:
                                command_runner.set_data('dropbox_account_folder_name', dropbox_account_folder_name)
                                command_runner.set_data('salesforce_account_file_names', salesforce_account_file_names)

                        else:
                            logger.error(f"Could not verify account page or get account ID for: {account_to_check}")
                            report_logger.info(f"Could not verify account page or get account ID for: {account_to_check}")
                    else:
                        logger.error(f"Could not navigate to Salesforce account: {account_to_check}")
                        report_logger.info(f"Could not navigate to Salesforce account: {account_to_check}")

                if command_runner:  
                    command_runner.set_data('dropbox_account_folder_name', dropbox_account_folder_name)
                    command_runner.set_data('dropbox_account_file_names', dropbox_account_file_names)
                    command_runner.set_data('salesforce_account_file_names', salesforce_account_file_names)
                    command_runner.set_data('salesforce_matches', salesforce_matches)
                    command_runner.set_data('result', salesforce_account_search_result)
                    command_runner.execute_commands()
                
                # Compare files if both Dropbox and Salesforce files are available
                file_comparison = None
                if dropbox_account_file_names and salesforce_account_file_names and file_manager:
                    logger.info(f'comparing files for account: {dropbox_account_folder_name}')
                    file_comparison = file_manager.compare_salesforce_files(dropbox_account_file_names, salesforce_account_file_names)
                
                summary = {
                    'dropbox_name': dropbox_account_folder_name,
                    'dropbox_account_file_names': dropbox_account_file_names,
                    'salesforce_account_file_names': salesforce_account_file_names if args.salesforce_account_files else [],
                    'file_comparison': file_comparison,
                    'salesforce_account_search_result': salesforce_account_search_result if args.salesforce_accounts else {},
                    'dropbox_account_search_result': dropbox_account_search_result if args.dropbox_account_info else {}
                }
                # CAROLINA HERE
                summary_results.append(summary)
                if args.salesforce_accounts:
                    salesforce_account_search_result['summary'] = summary
            
            # Print results summary
            if args.salesforce_accounts and account_manager:
                report_logger.info("\n=== SALESFORCE ACCOUNT MATCHES ===")
            for dropbox_account_folder_name, result_dict in results.items():
                salesforce_account_search_result = result_dict['salesforce_account_search_result']
                logger.info(f"*** folder_name: {dropbox_account_folder_name}")
                logger.debug(f"*** salesforce search result: {salesforce_account_search_result}")
                                
                report_logger.info(f"\nDropbox account folder name: {dropbox_account_folder_name} match:[{salesforce_account_search_result['match_info']['match_status']}] view:[{salesforce_account_search_result['view']}]")
                for match in salesforce_account_search_result['matches']:
                    report_logger.info(f"  Salesforce account name: {match}")

                if args.dropbox_account_files:
                    # Show Dropbox files
                    report_logger.info("\n📁 Dropbox account files:")
                    logger.debug(f'summary_results: {summary_results}')
                    for summary in summary_results:
                        logger.info(f'folder_name: {dropbox_account_folder_name}')
                        # logger.info(f'summary: {summary}')
                        if summary['dropbox_name'] == dropbox_account_folder_name and summary['dropbox_account_file_names']:
                            sorted_files = sorted(summary['dropbox_account_file_names'], key=lambda x: x.name)
                            for i, file in enumerate(sorted_files, 1):
                                report_logger.info(f"   + {i}. {file.name}")
                # Show file comparison if available
                if args.dropbox_account_files and args.salesforce_account_files:
                    # Show Salesforce files
                    report_logger.info("\n📁 Salesforce account files:")
                    for summary in summary_results:
                        if summary['dropbox_name'] == dropbox_account_folder_name and summary['salesforce_account_file_names']:
                            sorted_files = sorted(summary['salesforce_account_file_names'], 
                                key=lambda x: int(x.split('.')[0]) if x.split('.')[0].isdigit() else float('inf'))
                            for file in sorted_files:
                                report_logger.info(f"   + {file}")
                    # Show comparison results
                    report_logger.info("\n📁 File Comparison:")
                    for summary in summary_results:
                        if summary['dropbox_name'] == dropbox_account_folder_name and summary['file_comparison']:
                            file_details = summary['file_comparison'].get('file_details', {})
                            for file_name, detail in file_details.items():
                                status = detail.get('status', '')
                                sf_file = detail.get('salesforce_file', '')
                                match_type = detail.get('match_type', '')
                                reason = detail.get('reason', '')
                                report_logger.info(f"   {status} {file_name}")
                                if sf_file:
                                    report_logger.info(f"      Matched Salesforce file: {sf_file} ({match_type})")
                                if reason:
                                    report_logger.info(f"      {reason}")
                                potential_matches = detail.get('potential_matches', [])
                                if potential_matches:
                                    report_logger.info(f"      Potential matches: {potential_matches}")
                
                report_logger.info("=" * 50)

            
            # Print final summary
            report_logger.info("\n=== SUMMARY ===")
            
            # Initialize counters for match types
            total_exact_matches = 0
            total_partial_matches = 0
            total_no_matches = 0
            
            for result_dict in summary_results:
                build_and_log_summary_line(result_dict, report_logger, args)

                # Show file summary if available
                if args.dropbox_account_files and args.salesforce_account_files:
                    report_logger.info("\nFile Migration Status:")
                    file_comparison = result_dict.get('file_comparison')
                    if file_comparison:
                        matched = file_comparison.get('matched_files', 0)
                        total = file_comparison.get('total_files', 0)
                        report_logger.info(f"   {matched}/{total} files matched")
                        missing_files = file_comparison.get('missing_files', [])
                        extra_files = file_comparison.get('extra_files', [])
                        if missing_files:
                            report_logger.info("   Missing files in Salesforce:")
                            for f in missing_files:
                                report_logger.info(f"      - {f}")
                        if extra_files:
                            report_logger.info("   Extra files in Salesforce:")
                            for f in extra_files:
                                report_logger.info(f"      - {f}")
                    else:
                        report_logger.info("   No files to compare")
            
            # Print match statistics
            report_logger.info("\n=== MATCH STATISTICS ===")
            report_logger.info(f"Total Exact Matches: {total_exact_matches}")
            report_logger.info(f"Total Partial Matches: {total_partial_matches}")
            report_logger.info(f"Total No Matches: {total_no_matches}")
            report_logger.info(f"Total Accounts Processed: {len(summary_results)}")

             

            
        except Exception as e:
            import traceback
            logger.error(f"Command analyzer failed with error: {str(e)}")
            logger.error("Stack trace:")
            logger.error(traceback.format_exc())
            report_logger.info(f"\nCommand analyzer with error: {str(e)}")
            report_logger.info("\nStack trace:")
            report_logger.info(traceback.format_exc())
        finally:
            report_logger.info(f"\n=== ANALYSIS COMPLETE ===")

    # Calculate and log total duration
    total_duration = time.time() - start_time
    duration_message = f"Total duration: {format_duration(total_duration)}"
    logging.info(duration_message)
    report_logger.info(duration_message)   

def format_summary_line(dropbox_folder_name, salesforce_info, dropbox_info, args=None):
    """
    Returns a formatted summary line for the report log.
    dropbox_folder_name: str
    salesforce_info: dict with keys 'account_name', 'match', 'view'
    dropbox_info: dict with keys 'account_name', 'match'
    args: argparse.Namespace (optional, to check for salesforce_accounts flag)
    """
    print('[[[*******dropbox_info*********', dropbox_info)
    dropbox_account_search_name = dropbox_info.get('account_name', '--')
    dropbox_account_match = dropbox_info.get('match', '--')
    dropbox_icon = '📄' if dropbox_account_match == 'Match found' else '🔴'
    summary = f"📁 **Dropbox Folder** Name: {dropbox_folder_name}, {dropbox_icon} Dropbox Name: {dropbox_account_search_name}, Dropbox Match: {dropbox_account_match}"
    if args and getattr(args, 'salesforce_accounts', False):
        salesforce_account_name = salesforce_info.get('account_name', '--')
        salesforce_match = salesforce_info.get('match', '--')
        salesforce_view = salesforce_info.get('view', '--')
        salesforce_icon = '👤' if salesforce_match == 'Exact Match' else '🔴'
        summary += f", {salesforce_icon} Salesforce Account: {salesforce_account_name}, Salesforce Match: {salesforce_match}, Salesforce View: {salesforce_view}"
    return summary

def build_and_log_summary_line(result, report_logger, args):
    dropbox_folder_name = result.get('dropbox_name', '--')
    salesforce_result = result.get('salesforce_account_search_result', {})
    dropbox_result = result.get('dropbox_account_search_result', {})
    if args.dropbox_account_info:
        account_data = dropbox_result.get('search_info', {}).get('account_data', {})
        if account_data:
            dropbox_account_search_name = account_data.get('name') or (
                (account_data.get('first_name', '').strip() + ' ' + account_data.get('last_name', '').strip()).strip()
            ) or dropbox_folder_name or '--'
        else:
            dropbox_account_search_name = dropbox_folder_name or '--'
        dropbox_search_info = dropbox_result.get('search_info', {})
        print('*********dropbox_search_info*********', dropbox_search_info)
        dropbox_match_info = dropbox_search_info.get('match_info', {})
        dropbox_account_match = dropbox_match_info.get('match_status', 'No match found')
        print('*********dropbox_result*********', dropbox_result)
        dropbox_info = {'account_name': dropbox_account_search_name, 'match': dropbox_account_match}
        print('*********dropbox_info*********', dropbox_info)
        salesforce_info = {'account_name': '--', 'match': '--', 'view': '--'}
        if args.salesforce_accounts:
            salesforce_matches = salesforce_result.get('matches', [])
            salesforce_account_name = salesforce_matches[0] if salesforce_matches else '--'
            salesforce_match = salesforce_result.get('match_info', {}).get('match_status', 'No match found')
            salesforce_view = salesforce_result.get('view', '--')
            salesforce_info = {'account_name': salesforce_account_name, 'match': salesforce_match, 'view': salesforce_view}
        summary_line = format_summary_line(dropbox_folder_name, salesforce_info, dropbox_info, args=args)
        report_logger.info(summary_line)
    else:
        # Only Dropbox info in summary
        dropbox_info = {'account_name': '--', 'match': '--'}
        salesforce_info = {'account_name': '--', 'match': '--', 'view': '--'}
        summary_line = format_summary_line(dropbox_folder_name, salesforce_info, dropbox_info, args=args)
        report_logger.info(summary_line)

if __name__ == "__main__":
    args = parse_args()
    logger, report_logger = setup_logging(args)
    run_command(args) 