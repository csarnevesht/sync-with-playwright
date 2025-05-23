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

from .utils.dropbox_utils import (
    get_access_token,
    list_all_namespaces_and_roots,
    list_app_folder_contents,
    list_folder_contents,
    clean_dropbox_path,
    get_DROPBOX_FOLDER
)
from .utils.file_utils import (
    read_allowed_folders,
    read_ignored_folders
)

def analyze_folder_structure(dbx, path, indent=0, allowed_folders=None, ignored_folders=None):
    """Recursively analyze and print the folder structure."""
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
        
        for entry in entries:
            # Print the current entry with proper indentation
            prefix = "  " * indent
            if isinstance(entry, dropbox.files.FolderMetadata):
                folder_name = entry.name
                
                # Skip ignored folders
                if ignored_folders and folder_name in ignored_folders:
                    print(f"{prefix}📁 {folder_name} (ignored)")
                    continue
                
                # Check if folder is allowed
                if allowed_folders and folder_name not in allowed_folders:
                    print(f"{prefix}📁 {folder_name} (not allowed)")
                    continue
                
                print(f"{prefix}📁 {folder_name}")
                # Recursively analyze subfolders
                analyze_folder_structure(dbx, entry.path_display, indent + 1, allowed_folders, ignored_folders)
            else:
                print(f"{prefix}📄 {entry.name}")
                
    except ApiError as e:
        print(f"Error analyzing folder {path}: {e}")

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description='Analyze Dropbox folder structure.')
    parser.add_argument('--env-file', '-e', default='.env',
                      help='Path to .env file (default: .env)')
    parser.add_argument('--list-namespaces', action='store_true',
                      help='List all available namespaces and root folders')
    parser.add_argument('--list-app-folder', action='store_true',
                      help='List contents of the app folder')
    parser.add_argument('--analyze-path', '-p',
                      help='Analyze folder structure starting from this path (relative to DROPBOX_FOLDER)')
    parser.add_argument('--show-all', action='store_true',
                      help='Show all folders, including ignored and not allowed ones')
    
    args = parser.parse_args()
    
    try:
        # Get access token
        access_token = get_access_token(args.env_file)
        if not access_token:
            print("Error: Could not get access token")
            return
        
        # Initialize Dropbox client
        dbx = dropbox.Dropbox(access_token, timeout=30)
        
        # Handle special commands
        if args.list_namespaces:
            print("\n=== Listing Namespaces and Root Folders ===")
            list_all_namespaces_and_roots(dbx)
            return
            
        if args.list_app_folder:
            print("\n=== Listing App Folder Contents ===")
            list_app_folder_contents(dbx)
            return
        
        # Get the root folder from environment
        root_folder = get_DROPBOX_FOLDER(args.env_file)
        if not root_folder:
            print("Error: Could not get DROPBOX_FOLDER from environment")
            return
            
        print(f"\n=== Analyzing Folder Structure for {root_folder} ===")
        
        # Read allowed and ignored folders
        allowed_folders = None if args.show_all else read_allowed_folders()
        ignored_folders = None if args.show_all else read_ignored_folders()
        
        if not args.show_all:
            if allowed_folders:
                print(f"\nAllowed folders: {', '.join(allowed_folders)}")
            if ignored_folders:
                print(f"Ignored folders: {', '.join(ignored_folders)}")
        
        # If a specific path is provided, analyze that path relative to root_folder
        if args.analyze_path:
            full_path = os.path.join(root_folder, args.analyze_path.lstrip('/'))
            print(f"Analyzing subfolder: {args.analyze_path}")
            analyze_folder_structure(dbx, full_path, allowed_folders=allowed_folders, ignored_folders=ignored_folders)
        else:
            # Analyze the root folder
            analyze_folder_structure(dbx, root_folder, allowed_folders=allowed_folders, ignored_folders=ignored_folders)
        
    except Exception as e:
        print(f"Error: {e}")
        if hasattr(e, 'error'):
            print(f"Error details: {e.error}")

if __name__ == "__main__":
    main() 