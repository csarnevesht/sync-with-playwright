#!/usr/bin/env python3

"""
Dropbox Analyzer

This script connects to Dropbox and lists all app folders and their contents.
It helps in analyzing the Dropbox account structure and available folders.
"""

import argparse
import dropbox
from dropbox.exceptions import ApiError
from dotenv import load_dotenv
import os
import logging

from sync.dropbox_client.utils.dropbox_utils import (
    get_access_token,
    list_dropbox_folder_contents,
    clean_dropbox_folder_name,
    get_DROPBOX_FOLDER,
    get_folder_structure,
    display_summary
)
from src.sync.dropbox_client.utils.file_utils import (
    read_account_folders,
    read_ignored_folders
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

def list_folders_only(dbx, path, account_folders=None, ignored_folders=None, debug=False):
    """List only folders in the given path, without their contents."""
    try:
        clean_path = clean_dropbox_folder_name(path)
        if not clean_path:
            print(f"Invalid path: {path}")
            return {'total': 0, 'allowed': 0, 'ignored': 0, 'not_allowed': 0, 'found_ignored': set(), 'allowed_folders': set()}

        try:
            dbx.files_get_metadata(clean_path)
        except ApiError as e:
            if e.error.is_path() and e.error.get_path().is_not_found():
                print(f"Path not found: {clean_path}")
                return {'total': 0, 'allowed': 0, 'ignored': 0, 'not_allowed': 0, 'found_ignored': set(), 'allowed_folders': set()}
            raise

        entries = list_dropbox_folder_contents(dbx, clean_path)
        counts = {
            'total': 0,
            'allowed': 0,
            'ignored': 0,
            'not_allowed': 0,
            'found_ignored': set(),
            'allowed_folders': set()  # Track allowed folders
        }
        
        if debug:
            print("\nAll folders found in Dropbox:")
            for entry in entries:
                if isinstance(entry, dropbox.files.FolderMetadata):
                    print(f"  - {entry.name}")
            print("\nProcessing folders:")
            
        for entry in entries:
            if isinstance(entry, dropbox.files.FolderMetadata):
                folder_name = entry.name
                counts['total'] += 1
                
                # Check if folder should be ignored (case-insensitive)
                if ignored_folders and any(folder_name.lower() == ignored.lower() for ignored in ignored_folders):
                    counts['ignored'] += 1
                    counts['found_ignored'].add(folder_name)
                    if debug:
                        print(f"  - {folder_name} (ignored - matches ignore list)")
                    continue
                    
                if account_folders:
                    normalized_folder_name = folder_name.strip()
                    normalized_account_folders = [acct.strip() for acct in account_folders]
                    if normalized_folder_name in normalized_account_folders:
                        if debug:
                            print(f"  + {folder_name} (allowed - exact match in account list)")
                        counts['allowed'] += 1
                        counts['allowed_folders'].add(folder_name)
                    else:
                        normalized_folder_name_lower = normalized_folder_name.lower()
                        normalized_account_folders_lower = [acct.lower() for acct in normalized_account_folders]
                        if normalized_folder_name_lower in normalized_account_folders_lower:
                            if debug:
                                print(f"  + {folder_name} (allowed - case-insensitive match in account list)")
                            counts['allowed'] += 1
                            counts['allowed_folders'].add(folder_name)
                        else:
                            if debug:
                                print(f"  - {folder_name} (not allowed - not in account list)")
                            counts['not_allowed'] += 1
                else:
                    if debug:
                        print(f"  + {folder_name} (allowed - no account list specified)")
                    counts['allowed'] += 1
                    counts['allowed_folders'].add(folder_name)
        return counts
    except ApiError as e:
        print(f"Error listing folders for {path}: {e}")
        return {'total': 0, 'allowed': 0, 'ignored': 0, 'not_allowed': 0, 'found_ignored': set(), 'allowed_folders': set()}

def analyze_folder_structure(dbx, path, indent=0, account_folders=None, ignored_folders=None):
    """Recursively analyze and print the folder structure, only including files in account folders."""
    try:
        clean_path = clean_dropbox_folder_name(path)
        if not clean_path:
            print(f"Invalid path: {path}")
            return {'total': 0, 'allowed': 0, 'ignored': 0, 'not_allowed': 0, 'files': 0}
        try:
            dbx.files_get_metadata(clean_path)
        except ApiError as e:
            if e.error.is_path() and e.error.get_path().is_not_found():
                print(f"Path not found: {clean_path}")
                return {'total': 0, 'allowed': 0, 'ignored': 0, 'not_allowed': 0, 'files': 0}
            raise
        entries = list_dropbox_folder_contents(dbx, clean_path)
        counts = {
            'total': 0,
            'allowed': 0,
            'ignored': 0,
            'not_allowed': 0,
            'files': 0
        }
        for entry in entries:
            prefix = "  " * indent
            if isinstance(entry, dropbox.files.FolderMetadata):
                folder_name = entry.name
                counts['total'] += 1
                if ignored_folders and folder_name in ignored_folders:
                    counts['ignored'] += 1
                    continue
                if account_folders:
                    normalized_folder_name = folder_name.strip()
                    normalized_account_folders = [acct.strip() for acct in account_folders]
                    if normalized_folder_name in normalized_account_folders:
                        print(f"{prefix}📁 {folder_name}")
                        counts['allowed'] += 1
                        # Only recurse and print files for account folders
                        sub_counts = analyze_folder_structure(dbx, entry.path_display, indent + 1, account_folders, ignored_folders)
                        for key in counts:
                            counts[key] += sub_counts[key]
                    else:
                        counts['not_allowed'] += 1
                else:
                    print(f"{prefix}📁 {folder_name}")
                    counts['allowed'] += 1
                    sub_counts = analyze_folder_structure(dbx, entry.path_display, indent + 1, account_folders, ignored_folders)
                    for key in counts:
                        counts[key] += sub_counts[key]
            else:
                # Only print files if we are inside an account folder (indent > 0 and parent is allowed)
                if indent > 0:
                    print(f"{prefix}📄 {entry.name}")
                    counts['files'] += 1
        return counts
    except ApiError as e:
        print(f"Error analyzing folder {path}: {e}")
        return {'total': 0, 'allowed': 0, 'ignored': 0, 'not_allowed': 0, 'files': 0}

def debug_list_folders(dbx, path):
    """List all folders in the given Dropbox folder with no filtering or recursion."""
    try:
        # Clean and validate the path
        clean_path = clean_dropbox_folder_name(path)
        if not clean_path:
            print(f"Invalid path: {path}")
            return

        # Try to get metadata first to check if path exists
        try:
            dbx.files_get_metadata(clean_path)
        except ApiError as e:
            if e.error.is_path() and e.error.get_path().is_not_found():
                print(f"Path not found: {clean_path}")
                return
            raise

        entries = list_dropbox_folder_contents(dbx, clean_path)

        print(f"\nFolders in: {clean_path}")
        for entry in entries:
            if isinstance(entry, dropbox.files.FolderMetadata):
                print(entry.name)
        print(f"\n[Dropbox folder used: {clean_path}]")
    except ApiError as e:
        print(f"Error listing folders for {path}: {e}")
        return

def display_summary(counts, folders_only=False, ignored_folders=None, account_folders=None, show_all=False, debug=False, analyze_path=None, accounts_file=None):
    """
    Display a summary of the analysis results.
    
    Args:
        counts (dict): Dictionary containing folder and file counts
        folders_only (bool): Whether only folders were analyzed
        ignored_folders (list): List of ignored folders
        account_folders (list): List of account folders
        show_all (bool): Whether --show-all flag was used
        debug (bool): Whether --debug flag was used
        analyze_path (str): Path to analyze (if specified)
        accounts_file (str): Path to accounts file (if specified)
    """
    print("\n=== Summary ===")
    print("Flags used:")
    print(f"  - --folders-only: {folders_only}")
    print(f"  - --show-all: {show_all}")
    print(f"  - --debug: {debug}")
    print(f"  - --analyze-path: {analyze_path if analyze_path else '(default: root folder)'}")
    if not show_all:
        print(f"  - --accounts-file: {accounts_file if accounts_file else '(default: accounts/main.txt)'}")
    print()
    
    if not folders_only:
        print(f"Total Dropbox account files: {counts['files']}")
    print(f"Dropbox account folders: {counts['allowed']}")
    
    # Always show the list of allowed folders
    if 'allowed_folders' in counts:
        print("\nDropbox account folders list:")
        for idx, folder in enumerate(sorted(counts['allowed_folders']), 1):
            print(f"{idx}. {folder}")
    
    print(f"\nIgnored Dropbox account folders: {counts['ignored']}")
    if counts['ignored'] > 0 and 'found_ignored' in counts:
        print("Ignored Dropbox account folders list:")
        for folder in sorted(counts['found_ignored']):
            print(f"  - {folder}")

def main():
    """Main function to analyze Dropbox folder structure."""
    parser = argparse.ArgumentParser(description='Analyze Dropbox folder structure')
    parser.add_argument('--env-file', '-e', default='.env',
                      help='Path to .env file (default: .env)')
    parser.add_argument('--analyze-path', '-p',
                      help='Analyze folder structure starting from this path (relative to DROPBOX_FOLDER)')
    parser.add_argument('--show-all', action='store_true',
                      help='Show all folders except ignored ones (ignores account folders list)')
    parser.add_argument('--folders-only', action='store_true',
                      help='List only folders without their contents')
    parser.add_argument('--accounts-file', '-a',
                      help='Path to file containing list of account folders (default: accounts/main.txt)')
    parser.add_argument('--debug-list', action='store_true',
                      help='Debug: List all folders from Dropbox without any filtering')
    parser.add_argument('--find-folder',
                      help='Debug: Search for a specific folder recursively')
    parser.add_argument('--debug', action='store_true',
                      help='Show detailed folder processing information')
    args = parser.parse_args()
    
    # Get absolute path of .env file
    env_file_abs_path = os.path.abspath(args.env_file)
    logger.info(f"Using .env file at: {env_file_abs_path}")
    
    # Get access token
    try:
        token = get_access_token()
        logger.info(f"Token loaded successfully (length: {len(token)})")
    except ValueError as e:
        logger.error(f"Failed to get access token: {str(e)}")
        return
    
    # Initialize Dropbox client
    try:
        dbx = dropbox.Dropbox(token)
        logger.info("Successfully initialized Dropbox client")
    except Exception as e:
        logger.error(f"Failed to initialize Dropbox client: {str(e)}")
        return
    
    # Get the root folder from environment
    root_folder = get_DROPBOX_FOLDER(args.env_file)
    if not root_folder:
        logger.error("Could not get DROPBOX_FOLDER from environment")
        return
        
    logger.info(f"=== Analyzing Folder Structure for {root_folder} ===")
    
    # If find-folder is enabled, search recursively for the folder
    if args.find_folder:
        logger.info(f"Searching for folder: {args.find_folder}")
        if args.analyze_path:
            full_path = os.path.join(root_folder, args.analyze_path.lstrip('/'))
            logger.info(f"Starting search from: {args.analyze_path}")
            found = debug_list_folders(dbx, full_path)
        else:
            found = debug_list_folders(dbx, root_folder)
        if not found:
            logger.info(f"Folder '{args.find_folder}' not found in any subfolder")
        return
    
    # If debug-list is enabled, just list all folders without filtering
    if args.debug_list:
        if args.analyze_path:
            full_path = os.path.join(root_folder, args.analyze_path.lstrip('/'))
            logger.info(f"Debug listing subfolder: {args.analyze_path}")
            debug_list_folders(dbx, full_path)
        else:
            debug_list_folders(dbx, root_folder)
        return
    
    # Always read ignored folders
    ignored_folders = read_ignored_folders()
    
    # Read account folders based on options
    account_folders = None if args.show_all else read_account_folders(args.accounts_file)
    
    # Display account folders list when not using --show-all
    if account_folders and not args.show_all:
        print("\nDropbox Account folders:")
        for idx, folder in enumerate(account_folders, 1):
            ignored_mark = " (ignored)" if ignored_folders and folder in ignored_folders else ""
            print(f"{idx}. {folder}{ignored_mark}")
    
    # If a specific path is provided, analyze that path relative to root_folder
    if args.analyze_path:
        full_path = os.path.join(root_folder, args.analyze_path.lstrip('/'))
        logger.info(f"Analyzing subfolder: {args.analyze_path}")
        if args.folders_only:
            counts = list_folders_only(dbx, full_path, account_folders=account_folders, ignored_folders=ignored_folders, debug=args.debug)
        else:
            counts = analyze_folder_structure(dbx, full_path, account_folders=account_folders, ignored_folders=ignored_folders)
    else:
        # Analyze the root folder
        if args.folders_only:
            counts = list_folders_only(dbx, root_folder, account_folders=account_folders, ignored_folders=ignored_folders, debug=args.debug)
        else:
            counts = analyze_folder_structure(dbx, root_folder, account_folders=account_folders, ignored_folders=ignored_folders)
    
    # Display summary
    display_summary(counts, args.folders_only, ignored_folders, account_folders, args.show_all, args.debug, args.analyze_path, args.accounts_file)

if __name__ == "__main__":
    main() 