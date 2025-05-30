#!/usr/bin/env python3

"""
Dropbox File Renamer

This script downloads files from Dropbox and renames both files and folders
with their modification dates as prefixes.
"""

import os
import datetime
import argparse
from pathlib import Path
import dropbox
from dropbox.exceptions import ApiError
import tempfile
import shutil
from dotenv import load_dotenv
import sys

from .utils.file_utils import (
    create_timestamped_directory,
    ensure_directory_exists,
    log_processed_folder,
    log_renamed_file,
    log_processing_time,
    read_allowed_folders,
    read_ignored_folders
)
from .utils.dropbox_utils import (
    get_renamed_path,
    download_and_rename_file,
    list_dropbox_folder_contents,
    find_folder_path,
    get_access_token,
    get_DROPBOX_FOLDER,
    count_account_folders,
    get_DATA_DIRECTORY
)
from .utils.path_utils import clean_dropbox_folder_name
from .utils.date_utils import format_duration

def get_DATA_DIRECTORY(env_file):
    """Get the data directory from environment or prompt user."""
    # Load environment variables
    load_dotenv(env_file)
    
    # Try to get directory from environment
    directory = os.getenv('DATA_DIRECTORY')
    
    # If no directory found, prompt user
    if not directory:
        print("\nDATA_DIRECTORY not found in .env file.")
        print("Please enter the base directory to save files (default: ./data):")
        directory = input().strip()
        
        if not directory:
            directory = './data'
            print(f"Using default directory: {directory}")
        
        # Update .env file with the new directory
        update_env_file(env_file, directory=directory)
    
    return directory

def update_env_file(env_file, token=None, root_folder=None, directory=None):
    """Update the .env file with the new token, root folder, and/or directory."""
    try:
        # Read existing content
        existing_content = {}
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        existing_content[key] = value
        
        # Update values
        if token:
            existing_content['DROPBOX_TOKEN'] = token
        if root_folder:
            existing_content['DROPBOX_FOLDER'] = root_folder
        if directory:
            existing_content['DATA_DIRECTORY'] = directory
        
        # Write back to file
        with open(env_file, 'w') as f:
            for key, value in existing_content.items():
                f.write(f"{key}={value}\n")
        
        if token:
            print(f"✓ Access token saved to {env_file}")
        if root_folder:
            print(f"✓ Root folder saved to {env_file}")
        if directory:
            print(f"✓ Directory saved to {env_file}")
    except Exception as e:
        print(f"✗ Error saving to {env_file}: {e}")
        raise

def collect_folder_stats(download_dir):
    """Collect statistics about the downloaded folders."""
    stats = {
        'total_folders': 0,
        'total_files': 0,
        'total_size': 0,
        'processed_folders': set(),
        'renamed_files': set()
    }
    
    # Read processed folders log
    folders_log = os.path.join(download_dir, 'processed_folders.log')
    if os.path.exists(folders_log):
        with open(folders_log, 'r') as f:
            for line in f:
                if ' - ' in line:
                    folder = line.split(' - ')[1].strip()
                    stats['processed_folders'].add(folder)
                    stats['total_folders'] += 1
    
    # Read renamed files log
    files_log = os.path.join(download_dir, 'renamed_files.log')
    if os.path.exists(files_log):
        with open(files_log, 'r') as f:
            for line in f:
                if ' - ' in line:
                    file_info = line.split(' - ')[1].strip()
                    original_path = file_info.split(' -> ')[0]
                    stats['renamed_files'].add(original_path)
                    stats['total_files'] += 1
    
    return stats

def display_summary(stats, total_time):
    """Display a summary of the processing results."""
    print("\n=== Processing Summary ===")
    print(f"Total Folders Processed: {stats['total_folders']}")
    print(f"Total Files Renamed: {stats['total_files']}")
    print(f"Total Processing Time: {format_duration(total_time)}")
    print("\nProcessed Folders:")
    for folder in sorted(stats['processed_folders']):
        print(f"- {folder}")
    print("\nRenamed Files:")
    for file in sorted(stats['renamed_files']):
        print(f"- {file}")

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description='Download and rename files from Dropbox with date prefixes.')
    parser.add_argument('--env-file', '-e', default='.env',
                      help='Path to .env file (default: .env)')
    parser.add_argument('--all', action='store_true',
                      help='Process all folders except ignored ones (ignores allowed_folders list)')
    parser.add_argument('--batch-size', type=int, default=0,
                      help='Process folders in batches of specified size (0 for all at once)')
    parser.add_argument('--start-from', type=int, default=0,
                      help='Start processing from this folder index (0-based)')
    
    args = parser.parse_args()
    
    try:
        # Get access token
        access_token = get_access_token(args.env_file)
        if not access_token:
            print("Error: Could not get access token")
            return
        
        # Initialize Dropbox client
        dbx = dropbox.Dropbox(access_token, timeout=30)
        
        # Get Dropbox folder
        dropbox_path = get_DROPBOX_FOLDER(args.env_file)
        if not dropbox_path:
            print("Error: Could not get Dropbox folder")
            return
            
        # Clean and validate the path
        clean_path = clean_dropbox_folder_name(dropbox_path)
        if not clean_path:
            print(f"Invalid path: {dropbox_path}")
            return
            
        # Try to get metadata first to check if path exists
        try:
            dbx.files_get_metadata(clean_path)
        except ApiError as e:
            if e.error.is_path() and e.error.get_path().is_not_found():
                print(f"Path not found: {clean_path}")
                return
            raise
        
        # Get data directory
        base_directory = get_DATA_DIRECTORY(args.env_file)
        if not base_directory:
            print("Error: Could not get data directory")
            return
        
        # Create timestamped directory
        download_dir = create_timestamped_directory(base_directory)
        
        # Read allowed and ignored folders
        allowed_folders = None if args.all else read_allowed_folders()
        ignored_folders = read_ignored_folders()
        
        # Count account folders
        num_folders = count_account_folders(dbx, clean_path, allowed_folders, ignored_folders)
        print(f"\nFound {num_folders} account folders to process")
        
        # Process each folder
        start_time = datetime.datetime.now()
        entries = list_dropbox_folder_contents(dbx, clean_path)
        
        # Filter and sort folders
        folders = [entry for entry in entries if isinstance(entry, dropbox.files.FolderMetadata)]
        folders.sort(key=lambda x: x.name)
        
        # Apply start-from index
        if args.start_from > 0:
            if args.start_from >= len(folders):
                print(f"Error: start-from index {args.start_from} is out of range (0-{len(folders)-1})")
                return
            folders = folders[args.start_from:]
            print(f"Starting from folder {args.start_from}: {folders[0].name}")
        
        # Process in batches if specified
        if args.batch_size > 0:
            total_batches = (len(folders) + args.batch_size - 1) // args.batch_size
            for batch_num, i in enumerate(range(0, len(folders), args.batch_size), 1):
                batch = folders[i:i + args.batch_size]
                print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} folders)")
                
                for entry in batch:
                    folder_name = entry.name
                    
                    # Skip ignored folders
                    if ignored_folders and folder_name in ignored_folders:
                        print(f"Skipping ignored folder: {folder_name}")
                        continue
                    
                    # Check if folder is allowed (only if not using --all)
                    if not args.all and allowed_folders and folder_name not in allowed_folders:
                        print(f"Skipping non-allowed folder: {folder_name}")
                        continue
                    
                    # Create local folder
                    local_folder = os.path.join(download_dir, folder_name)
                    ensure_directory_exists(local_folder)
                    
                    # Log processed folder
                    log_processed_folder(entry.path_display, download_dir)
                    
                    # Process folder contents
                    folder_entries = list_dropbox_folder_contents(dbx, entry.path_display)
                    for file_entry in folder_entries:
                        if isinstance(file_entry, dropbox.files.FileMetadata):
                            download_and_rename_file(dbx, file_entry.path_display, local_folder)
                
                # Display intermediate summary
                if batch_num < total_batches:
                    stats = collect_folder_stats(download_dir)
                    current_time = (datetime.datetime.now() - start_time).total_seconds()
                    print(f"\nBatch {batch_num} Summary:")
                    print(f"Folders processed in this batch: {len(batch)}")
                    print(f"Total folders processed so far: {stats['total_folders']}")
                    print(f"Total files renamed so far: {stats['total_files']}")
                    print(f"Time elapsed: {format_duration(current_time)}")
                    
                    # Ask for confirmation to continue
                    if batch_num < total_batches:
                        response = input("\nContinue with next batch? (y/n): ").lower()
                        if response != 'y':
                            print("Stopping after current batch.")
                            break
        else:
            # Process all folders at once
            for entry in folders:
                folder_name = entry.name
                
                # Skip ignored folders
                if ignored_folders and folder_name in ignored_folders:
                    print(f"Skipping ignored folder: {folder_name}")
                    continue
                
                # Check if folder is allowed (only if not using --all)
                if not args.all and allowed_folders and folder_name not in allowed_folders:
                    print(f"Skipping non-allowed folder: {folder_name}")
                    continue
                
                # Create local folder
                local_folder = os.path.join(download_dir, folder_name)
                ensure_directory_exists(local_folder)
                
                # Log processed folder
                log_processed_folder(entry.path_display, download_dir)
                
                # Process folder contents
                folder_entries = list_dropbox_folder_contents(dbx, entry.path_display)
                for file_entry in folder_entries:
                    if isinstance(file_entry, dropbox.files.FileMetadata):
                        download_and_rename_file(dbx, file_entry.path_display, local_folder)
        
        # Calculate total time
        end_time = datetime.datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        # Collect and display statistics
        stats = collect_folder_stats(download_dir)
        display_summary(stats, total_time)
        
    except Exception as e:
        print(f"Error: {e}")
        if hasattr(e, 'error'):
            print(f"Error details: {e.error}")

if __name__ == "__main__":
    main() 