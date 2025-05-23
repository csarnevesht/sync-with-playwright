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

from dropbox_renamer.utils.dropbox_utils import (
    get_access_token,
    list_folder_contents,
    clean_dropbox_path,
    get_DROPBOX_FOLDER,
    get_folder_structure,
    display_summary
)
from dropbox_renamer.utils.file_utils import (
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

def list_folders_only(dbx, path, account_folders=None, ignored_folders=None):
    """List only folders in the given path, without their contents."""
    try:
        clean_path = clean_dropbox_path(path)
        if not clean_path:
            print(f"Invalid path: {path}")
            return {'total': 0, 'allowed': 0, 'ignored': 0, 'not_allowed': 0}

        try:
            dbx.files_get_metadata(clean_path)
        except ApiError as e:
            if e.error.is_path() and e.error.get_path().is_not_found():
                print(f"Path not found: {clean_path}")
                return {'total': 0, 'allowed': 0, 'ignored': 0, 'not_allowed': 0}
            raise

        entries = list_folder_contents(dbx, clean_path)
        counts = {
            'total': 0,
            'allowed': 0,
            'ignored': 0,
            'not_allowed': 0
        }
        print("\nAll folders found in Dropbox:")
        for entry in entries:
            if isinstance(entry, dropbox.files.FolderMetadata):
                print(f"  - {entry.name}")
        print("\nFiltering folders:")
        for entry in entries:
            if isinstance(entry, dropbox.files.FolderMetadata):
                folder_name = entry.name
                counts['total'] += 1
                if ignored_folders and folder_name in ignored_folders:
                    counts['ignored'] += 1
                    print(f"  - {folder_name} (ignored)")
                    continue
                if account_folders:
                    normalized_folder_name = folder_name.strip()
                    normalized_account_folders = [acct.strip() for acct in account_folders]
                    if normalized_folder_name in normalized_account_folders:
                        print(f"  + {folder_name} (matched)")
                        counts['allowed'] += 1
                    else:
                        normalized_folder_name_lower = normalized_folder_name.lower()
                        normalized_account_folders_lower = [acct.lower() for acct in normalized_account_folders]
                        if normalized_folder_name_lower in normalized_account_folders_lower:
                            print(f"  + {folder_name} (matched case-insensitive)")
                            counts['allowed'] += 1
                        else:
                            print(f"  - {folder_name} (not in account_folders)")
                            counts['not_allowed'] += 1
                else:
                    print(f"  + {folder_name}")
                    counts['allowed'] += 1
        return counts
    except ApiError as e:
        print(f"Error listing folders for {path}: {e}")
        return {'total': 0, 'allowed': 0, 'ignored': 0, 'not_allowed': 0}

def analyze_folder_structure(dbx, path, indent=0, account_folders=None, ignored_folders=None):
    """Recursively analyze and print the folder structure, only including files in account folders."""
    try:
        clean_path = clean_dropbox_path(path)
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
        entries = list_folder_contents(dbx, clean_path)
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
    """List all folders in the given Dropbox path with no filtering or recursion."""
    try:
        # Clean and validate the path
        clean_path = clean_dropbox_path(path)
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

        entries = list_folder_contents(dbx, clean_path)

        print(f"\nFolders in: {clean_path}")
        for entry in entries:
            if isinstance(entry, dropbox.files.FolderMetadata):
                print(entry.name)
        print(f"\n[Dropbox path used: {clean_path}]")
    except ApiError as e:
        print(f"Error listing folders for {path}: {e}")
        return

def main():
    """Main function to analyze Dropbox folder structure."""
    parser = argparse.ArgumentParser(description='Analyze Dropbox folder structure')
    parser.add_argument('--env-file', default='.env', help='Path to .env file')
    parser.add_argument('--accounts-file', '-a',
                      help='Path to file containing list of account folders (default: accounts/main.txt)')
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
    
    # Get folder structure
    try:
        folder_structure = get_folder_structure(dbx)
        logger.info("Successfully retrieved folder structure")
    except Exception as e:
        logger.error(f"Failed to get folder structure: {str(e)}")
        return
    
    # Display results
    display_summary(folder_structure)

if __name__ == "__main__":
    main() 