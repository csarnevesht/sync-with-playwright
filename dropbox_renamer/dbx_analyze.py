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
    read_allowed_folders,
    read_ignored_folders
)

def list_folders_only(dbx, path, allowed_folders=None, ignored_folders=None):
    """List only folders in the given path, without their contents."""
    try:
        # Clean and validate the path
        clean_path = clean_dropbox_path(path)
        if not clean_path:
            print(f"Invalid path: {path}")
            return {'total': 0, 'allowed': 0, 'ignored': 0, 'not_allowed': 0}

        # Try to get metadata first to check if path exists
        try:
            dbx.files_get_metadata(clean_path)
        except ApiError as e:
            if e.error.is_path() and e.error.get_path().is_not_found():
                print(f"Path not found: {clean_path}")
                return {'total': 0, 'allowed': 0, 'ignored': 0, 'not_allowed': 0}
            raise

        entries = list_folder_contents(dbx, clean_path)
        
        # Initialize counters
        counts = {
            'total': 0,
            'allowed': 0,
            'ignored': 0,
            'not_allowed': 0
        }
        
        # Filter and print only folders
        for entry in entries:
            if isinstance(entry, dropbox.files.FolderMetadata):
                folder_name = entry.name
                counts['total'] += 1
                
                # Skip ignored folders
                if ignored_folders and folder_name in ignored_folders:
                    counts['ignored'] += 1
                    continue
                
                # Check if folder is allowed
                if allowed_folders and folder_name not in allowed_folders:
                    print(f"📁 {folder_name} (not allowed)")
                    counts['not_allowed'] += 1
                    continue
                
                print(f"📁 {folder_name}")
                counts['allowed'] += 1
                
        return counts
                
    except ApiError as e:
        print(f"Error listing folders for {path}: {e}")
        return {'total': 0, 'allowed': 0, 'ignored': 0, 'not_allowed': 0}

def analyze_folder_structure(dbx, path, indent=0, allowed_folders=None, ignored_folders=None):
    """Recursively analyze and print the folder structure."""
    try:
        # Clean and validate the path
        clean_path = clean_dropbox_path(path)
        if not clean_path:
            print(f"Invalid path: {path}")
            return {'total': 0, 'allowed': 0, 'ignored': 0, 'not_allowed': 0, 'files': 0}

        # Try to get metadata first to check if path exists
        try:
            dbx.files_get_metadata(clean_path)
        except ApiError as e:
            if e.error.is_path() and e.error.get_path().is_not_found():
                print(f"Path not found: {clean_path}")
                return {'total': 0, 'allowed': 0, 'ignored': 0, 'not_allowed': 0, 'files': 0}
            raise

        entries = list_folder_contents(dbx, clean_path)
        
        # Initialize counters
        counts = {
            'total': 0,
            'allowed': 0,
            'ignored': 0,
            'not_allowed': 0,
            'files': 0
        }
        
        for entry in entries:
            # Print the current entry with proper indentation
            prefix = "  " * indent
            if isinstance(entry, dropbox.files.FolderMetadata):
                folder_name = entry.name
                counts['total'] += 1
                
                # Skip ignored folders
                if ignored_folders and folder_name in ignored_folders:
                    counts['ignored'] += 1
                    continue
                
                # Check if folder is allowed
                if allowed_folders and folder_name not in allowed_folders:
                    print(f"{prefix}📁 {folder_name} (not allowed)")
                    counts['not_allowed'] += 1
                    continue
                
                print(f"{prefix}📁 {folder_name}")
                counts['allowed'] += 1
                # Recursively analyze subfolders
                sub_counts = analyze_folder_structure(dbx, entry.path_display, indent + 1, allowed_folders, ignored_folders)
                # Add subfolder counts
                for key in counts:
                    counts[key] += sub_counts[key]
            else:
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
        print(f"Allowed folders: {counts['allowed']}")
    if counts['not_allowed'] > 0:
        print(f"Not allowed folders: {counts['not_allowed']}")
    if counts['ignored'] > 0:
        print(f"Ignored folders: {counts['ignored']}")

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description='Analyze Dropbox folder structure.')
    parser.add_argument('--env-file', '-e', default='.env',
                      help='Path to .env file (default: .env)')
    parser.add_argument('--analyze-path', '-p',
                      help='Analyze folder structure starting from this path (relative to DROPBOX_FOLDER)')
    parser.add_argument('--show-all', action='store_true',
                      help='Show all folders except ignored ones (ignores allowed_folders list)')
    parser.add_argument('--folders-only', action='store_true',
                      help='List only folders without their contents')
    
    args = parser.parse_args()
    
    try:
        # Get access token
        access_token = get_access_token(args.env_file)
        if not access_token:
            print("Error: Could not get access token")
            return
        
        # Initialize Dropbox client
        dbx = dropbox.Dropbox(access_token, timeout=30)
        
        # Get the root folder from environment
        root_folder = get_DROPBOX_FOLDER(args.env_file)
        if not root_folder:
            print("Error: Could not get DROPBOX_FOLDER from environment")
            return
            
        print(f"\n=== Analyzing Folder Structure for {root_folder} ===")
        
        # Always read ignored folders
        ignored_folders = read_ignored_folders()
        
        # Read allowed folders only if not showing all
        allowed_folders = None if args.show_all else read_allowed_folders()
        
        # Display allowed folders list when not using --show-all
        if allowed_folders and not args.show_all:
            print(f"\nAllowed folders: {', '.join(allowed_folders)}")
        
        # If a specific path is provided, analyze that path relative to root_folder
        if args.analyze_path:
            full_path = os.path.join(root_folder, args.analyze_path.lstrip('/'))
            print(f"Analyzing subfolder: {args.analyze_path}")
            if args.folders_only:
                counts = list_folders_only(dbx, full_path, allowed_folders=allowed_folders, ignored_folders=ignored_folders)
            else:
                counts = analyze_folder_structure(dbx, full_path, allowed_folders=allowed_folders, ignored_folders=ignored_folders)
        else:
            # Analyze the root folder
            if args.folders_only:
                counts = list_folders_only(dbx, root_folder, allowed_folders=allowed_folders, ignored_folders=ignored_folders)
            else:
                counts = analyze_folder_structure(dbx, root_folder, allowed_folders=allowed_folders, ignored_folders=ignored_folders)
        
        # Display summary
        display_summary(counts, args.folders_only)
        
    except Exception as e:
        print(f"Error: {e}")
        if hasattr(e, 'error'):
            print(f"Error details: {e.error}")

if __name__ == "__main__":
    main() 