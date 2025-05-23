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

from dropbox_renamer.utils.dropbox_utils import (
    get_access_token,
    list_folder_contents,
    clean_dropbox_path,
    get_DROPBOX_FOLDER
)
from dropbox_renamer.utils.file_utils import (
    read_account_folders,
    read_ignored_folders
)

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

def display_summary(counts, folders_only=False):
    """Display a summary of the analysis results."""
    print("\n=== Summary ===")
    print(f"Total folders found: {counts['total']}")
    if not folders_only:
        print(f"Total files found: {counts['files']}")
    if counts['allowed'] > 0:
        print(f"Account folders: {counts['allowed']}")
    if counts['not_allowed'] > 0:
        print(f"Non-account folders: {counts['not_allowed']}")
    if counts['ignored'] > 0:
        print(f"Ignored folders: {counts['ignored']}")

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
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description='Analyze Dropbox folder structure.')
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
    
    args = parser.parse_args()
    
    try:
        # Get access token
        access_token = get_access_token(args.env_file)
        if not access_token:
            print("Error: Could not get access token")
            return
        
        # Initialize Dropbox client with app key and secret
        app_key = os.getenv('DROPBOX_APP_KEY')
        app_secret = os.getenv('DROPBOX_APP_SECRET')
        if app_key and app_secret:
            print(f"Debug: Using app key: {app_key[:5]}...")
            dbx = dropbox.Dropbox(access_token, app_key=app_key, app_secret=app_secret, timeout=30)
        else:
            print("Debug: No app key/secret found, using token only")
            dbx = dropbox.Dropbox(access_token, timeout=30)
        
        # Get the root folder from environment
        root_folder = get_DROPBOX_FOLDER(args.env_file)
        if not root_folder:
            print("Error: Could not get DROPBOX_FOLDER from environment")
            return
            
        print(f"\n=== Analyzing Folder Structure for {root_folder} ===")
        
        # If find-folder is enabled, search recursively for the folder
        if args.find_folder:
            print(f"\nSearching for folder: {args.find_folder}")
            if args.analyze_path:
                full_path = os.path.join(root_folder, args.analyze_path.lstrip('/'))
                print(f"Starting search from: {args.analyze_path}")
                found = debug_list_folders(dbx, full_path)
            else:
                found = debug_list_folders(dbx, root_folder)
            if not found:
                print(f"\nFolder '{args.find_folder}' not found in any subfolder")
            return
        
        # If debug-list is enabled, just list all folders without filtering
        if args.debug_list:
            if args.analyze_path:
                full_path = os.path.join(root_folder, args.analyze_path.lstrip('/'))
                print(f"Debug listing subfolder: {args.analyze_path}")
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
                print(f"{idx}. {folder}")
        
        # If a specific path is provided, analyze that path relative to root_folder
        if args.analyze_path:
            full_path = os.path.join(root_folder, args.analyze_path.lstrip('/'))
            print(f"Analyzing subfolder: {args.analyze_path}")
            if args.folders_only:
                counts = list_folders_only(dbx, full_path, account_folders=account_folders, ignored_folders=ignored_folders)
            else:
                counts = analyze_folder_structure(dbx, full_path, account_folders=account_folders, ignored_folders=ignored_folders)
        else:
            # Analyze the root folder
            if args.folders_only:
                counts = list_folders_only(dbx, root_folder, account_folders=account_folders, ignored_folders=ignored_folders)
            else:
                counts = analyze_folder_structure(dbx, root_folder, account_folders=account_folders, ignored_folders=ignored_folders)
        
        # Display summary
        display_summary(counts, args.folders_only)
        
    except Exception as e:
        print(f"Error: {e}")
        if hasattr(e, 'error'):
            print(f"Error details: {e.error}")

if __name__ == "__main__":
    main() 