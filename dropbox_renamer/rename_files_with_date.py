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
import re

def create_timestamped_directory(base_dir):
    """Create a new directory with current timestamp."""
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    dir_name = f"dropbox_download_{timestamp}"
    full_path = os.path.join(base_dir, dir_name)
    os.makedirs(full_path, exist_ok=True)
    
    # Create log files in the download directory
    folders_log = os.path.join(full_path, 'processed_folders.log')
    files_log = os.path.join(full_path, 'renamed_files.log')
    timing_log = os.path.join(full_path, 'processing_times.log')
    
    # Initialize log files with headers
    with open(folders_log, 'w') as f:
        f.write(f"Dropbox Download Log - {timestamp}\n")
        f.write("Processed Folders:\n")
        f.write("-" * 80 + "\n")
    
    with open(files_log, 'w') as f:
        f.write(f"Dropbox Download Log - {timestamp}\n")
        f.write("Renamed Files:\n")
        f.write("-" * 80 + "\n")
    
    with open(timing_log, 'w') as f:
        f.write(f"Dropbox Download Log - {timestamp}\n")
        f.write("Processing Times:\n")
        f.write("-" * 80 + "\n")
    
    return full_path

def ensure_directory_exists(directory):
    """Ensure the directory exists, create it if it doesn't."""
    try:
        os.makedirs(directory, exist_ok=True)
        print(f"Ensuring directory exists: {directory}")
        return True
    except Exception as e:
        print(f"Error creating directory {directory}: {str(e)}")
        return False

def has_date_prefix(name):
    """Check if the filename already has a date prefix (YYYYMMDD or YYMMDD)."""
    # Regular expression to match various date formats at the beginning of the filename:
    # - YYYYMMDD (e.g., 20240101)
    # - YYYYMMDD with space and time (e.g., 20240101 123456)
    # - YYYYMMDD with underscore and time (e.g., 20240101_123456)
    # - YYMMDD (e.g., 210928)
    pattern = r'^(?:(?:19|20)\d{6}(?:\s+\d{6}|_\d{6}|\s+|$)|(?:[0-9]{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])))'
    return bool(re.match(pattern, name))

def get_folder_creation_date(dbx, path):
    """Get the creation date of a folder by looking at its contents."""
    try:
        # List the folder contents
        result = dbx.files_list_folder(path)
        
        # If folder has contents, find the oldest file
        if result.entries:
            oldest_date = None
            for entry in result.entries:
                if isinstance(entry, dropbox.files.FileMetadata):
                    if oldest_date is None or entry.server_modified < oldest_date:
                        oldest_date = entry.server_modified
            
            # If we found files, use the oldest file's date
            if oldest_date:
                return oldest_date
        
        # If no files found or empty folder, try looking at the folder info
        folder_info = dbx.files_get_metadata(path)
        
        # Some Dropbox API versions might include a 'client_modified' field
        if hasattr(folder_info, 'client_modified'):
            return folder_info.client_modified
            
        # Try getting the shared folder info which might have creation date
        try:
            shared_info = dbx.sharing_get_folder_metadata(path)
            if hasattr(shared_info, 'time_created'):
                return shared_info.time_created
        except:
            pass
        
        # If all else fails, use the current date
        return datetime.datetime.now()
        
    except Exception as e:
        print(f"Error getting folder creation date for {path}: {e}")
        return datetime.datetime.now()

def get_renamed_path(metadata, path, is_folder=False, dbx=None):
    """Get the renamed path with date prefix."""
    try:
        # Get the original name
        original_name = os.path.basename(path)
        
        # If the name already has a date prefix, don't modify it
        if has_date_prefix(original_name):
            print(f"File/folder already has date prefix: {original_name}")
            return original_name
        
        # Get date for prefix
        if is_folder:
            # For folders, try to get creation date
            if dbx:
                date_obj = get_folder_creation_date(dbx, path)
                date_prefix = date_obj.strftime("%y%m%d")
                print(f"Using folder creation date for {path}: {date_prefix}")
            else:
                # Fallback to current date if dbx not provided
                date_prefix = datetime.datetime.now().strftime("%y%m%d")
        else:
            # For files, use modification date from metadata
            date_prefix = metadata.server_modified.strftime("%y%m%d")
        
        # Create new name with date prefix
        new_name = f"{date_prefix} {original_name}"
        
        # If it's a folder, ensure it ends with a slash
        if is_folder and not new_name.endswith('/'):
            new_name += '/'
            
        return new_name
    except Exception as e:
        print(f"Error generating renamed path for {path}: {e}")
        return os.path.basename(path)

def log_processed_folder(folder_path, download_dir):
    """Log a processed folder to the log file."""
    log_file = os.path.join(download_dir, 'processed_folders.log')
    with open(log_file, 'a') as f:
        f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {folder_path}\n")

def log_renamed_file(original_path, new_name, download_dir):
    """Log a renamed file to the log file."""
    log_file = os.path.join(download_dir, 'renamed_files.log')
    with open(log_file, 'a') as f:
        f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {original_path} -> {new_name}\n")

def download_and_rename_file(dbx, dropbox_path, local_dir):
    """Download a file from Dropbox and rename it with its modification date if it doesn't already have a date prefix."""
    try:
        # Get file metadata
        metadata = dbx.files_get_metadata(dropbox_path)
        
        # Get the original name
        original_name = os.path.basename(dropbox_path)
        
        # Check if file already has a date prefix
        if has_date_prefix(original_name):
            print(f"File already has date prefix, downloading with original name: {original_name}")
            local_path = os.path.join(local_dir, original_name)
        else:
            # Generate new filename with date prefix
            new_name = get_renamed_path(metadata, dropbox_path)
            local_path = os.path.join(local_dir, new_name)
            # Log the renamed file
            log_renamed_file(dropbox_path, new_name, os.path.dirname(local_dir))
        
        # Download the file
        print(f"Downloading: {dropbox_path} -> {local_path}")
        dbx.files_download_to_file(local_path, dropbox_path)
        
    except Exception as e:
        print(f"Error processing file {dropbox_path}: {e}")

def read_allowed_folders(file_path='./dropbox_renamer/dropbox_files.txt'):
    """Read the list of allowed folder names from dropbox_files.txt."""
    try:
        if not os.path.exists(file_path):
            print(f"Warning: {file_path} not found. Will process all folders.")
            return None
            
        with open(file_path, 'r') as f:
            # Read lines and strip whitespace, skip empty lines
            folders = [line.strip() for line in f.readlines() if line.strip()]
            
        if not folders:
            print(f"Warning: {file_path} is empty. Will process all folders.")
            return None
            
        print(f"Found {len(folders)} allowed folders in {file_path}")
        return folders
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def read_ignored_folders(file_path='./dropbox_ignore.txt'):
    """Read the list of folders to ignore from dropbox_ignore.txt."""
    try:
        if not os.path.exists(file_path):
            print(f"Warning: {file_path} not found. No folders will be ignored.")
            return set()
            
        with open(file_path, 'r') as f:
            # Read lines and strip whitespace, skip empty lines
            folders = {line.strip() for line in f.readlines() if line.strip()}
            
        if not folders:
            print(f"Warning: {file_path} is empty. No folders will be ignored.")
            return set()
            
        print(f"Found {len(folders)} folders to ignore in {file_path}")
        return folders
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return set()

def format_duration(seconds):
    """Format duration in seconds to a human-readable string with hours, minutes, and seconds."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds:.1f}s"
    elif minutes > 0:
        return f"{minutes}m {seconds:.1f}s"
    else:
        return f"{seconds:.1f}s"

def log_processing_time(account_name, start_time, end_time, download_dir):
    """Log the processing time for an account."""
    duration = end_time - start_time
    seconds = duration.total_seconds()
    log_file = os.path.join(download_dir, 'processing_times.log')
    with open(log_file, 'a') as f:
        f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {account_name}: {format_duration(seconds)}\n")

def process_dropbox_folder(dbx, dropbox_path, local_dir, allowed_folders=None, ignored_folders=None, account_start_time=None, total_accounts=None, processed_accounts=None):
    """Process a Dropbox folder recursively."""
    try:
        # Log the processed folder
        log_processed_folder(dropbox_path, local_dir)
        
        # List all entries in the folder
        result = dbx.files_list_folder(dropbox_path)
        
        # Process all entries
        for entry in result.entries:
            entry_path = entry.path_display
            
            if isinstance(entry, dropbox.files.FileMetadata):
                # Get the last folder name from the path
                path_parts = entry_path.strip('/').split('/')
                if len(path_parts) > 1:  # Make sure we have at least a folder and a file
                    account_folder = path_parts[-2]  # Get the last folder name (second to last part)
                    account_dir = os.path.join(local_dir, account_folder)
                    ensure_directory_exists(account_dir)
                    download_and_rename_file(dbx, entry_path, account_dir)
                else:
                    # If path is not deep enough, download to current directory
                    download_and_rename_file(dbx, entry_path, local_dir)
            elif isinstance(entry, dropbox.files.FolderMetadata):
                # Skip folders that are in the ignore list
                folder_name = os.path.basename(entry_path)
                if ignored_folders and folder_name in ignored_folders:
                    print(f"Skipping ignored folder: {entry_path}")
                    continue
                
                # If we have a list of allowed folders, check if this folder should be processed
                if allowed_folders is not None:
                    # Get the full path components
                    path_parts = entry_path.strip('/').split('/')
                    # Check if any part of the path matches an allowed folder
                    if not any(folder in path_parts for folder in allowed_folders):
                        print(f"Skipping folder not in allowed list: {entry_path}")
                        continue
                
                # If this is an account folder (direct child of Principal Protection), log its processing time
                if len(entry_path.strip('/').split('/')) == 5:  # All files/A Work Documents/A WORK Documents/Principal Protection/Account Name
                    account_start = datetime.datetime.now()
                    if processed_accounts is not None:
                        processed_accounts[0] += 1
                        progress = (processed_accounts[0] / total_accounts[0]) * 100
                        print(f"\nProcessing account {processed_accounts[0]}/{total_accounts[0]} ({progress:.1f}%): {folder_name}")
                    process_dropbox_folder(dbx, entry_path, local_dir, allowed_folders, ignored_folders, account_start, total_accounts, processed_accounts)
                    account_end = datetime.datetime.now()
                    duration = account_end - account_start
                    print(f"Completed {folder_name} in {format_duration(duration.total_seconds())}")
                    log_processing_time(folder_name, account_start, account_end, local_dir)
                else:
                    # Process the folder with the same local directory
                    process_dropbox_folder(dbx, entry_path, local_dir, allowed_folders, ignored_folders, account_start_time, total_accounts, processed_accounts)
        
        # Handle pagination if there are more entries
        while result.has_more:
            result = dbx.files_list_folder_continue(result.cursor)
            for entry in result.entries:
                entry_path = entry.path_display
                
                if isinstance(entry, dropbox.files.FileMetadata):
                    # Get the last folder name from the path
                    path_parts = entry_path.strip('/').split('/')
                    if len(path_parts) > 1:  # Make sure we have at least a folder and a file
                        account_folder = path_parts[-2]  # Get the last folder name (second to last part)
                        account_dir = os.path.join(local_dir, account_folder)
                        ensure_directory_exists(account_dir)
                        download_and_rename_file(dbx, entry_path, account_dir)
                    else:
                        # If path is not deep enough, download to current directory
                        download_and_rename_file(dbx, entry_path, local_dir)
                elif isinstance(entry, dropbox.files.FolderMetadata):
                    # Skip folders that are in the ignore list
                    folder_name = os.path.basename(entry_path)
                    if ignored_folders and folder_name in ignored_folders:
                        print(f"Skipping ignored folder: {entry_path}")
                        continue
                    
                    # If we have a list of allowed folders, check if this folder should be processed
                    if allowed_folders is not None:
                        # Get the full path components
                        path_parts = entry_path.strip('/').split('/')
                        # Check if any part of the path matches an allowed folder
                        if not any(folder in path_parts for folder in allowed_folders):
                            print(f"Skipping folder not in allowed list: {entry_path}")
                            continue
                    
                    # If this is an account folder (direct child of Principal Protection), log its processing time
                    if len(entry_path.strip('/').split('/')) == 5:  # All files/A Work Documents/A WORK Documents/Principal Protection/Account Name
                        account_start = datetime.datetime.now()
                        if processed_accounts is not None:
                            processed_accounts[0] += 1
                            progress = (processed_accounts[0] / total_accounts[0]) * 100
                            print(f"\nProcessing account {processed_accounts[0]}/{total_accounts[0]} ({progress:.1f}%): {folder_name}")
                        process_dropbox_folder(dbx, entry_path, local_dir, allowed_folders, ignored_folders, account_start_time, total_accounts, processed_accounts)
                        account_end = datetime.datetime.now()
                        duration = account_end - account_start
                        print(f"Completed {folder_name} in {format_duration(duration.total_seconds())}")
                        log_processing_time(folder_name, account_start, account_end, local_dir)
                    else:
                        # Process the folder with the same local directory
                        process_dropbox_folder(dbx, entry_path, local_dir, allowed_folders, ignored_folders, account_start_time, total_accounts, processed_accounts)
                    
    except Exception as e:
        print(f"Error processing folder {dropbox_path}: {e}")

def count_account_folders(dbx, dropbox_path, allowed_folders=None, ignored_folders=None):
    """Count the number of account folders that will be processed."""
    try:
        count = 0
        result = dbx.files_list_folder(dropbox_path)
        
        for entry in result.entries:
            if isinstance(entry, dropbox.files.FolderMetadata):
                entry_path = entry.path_display
                folder_name = os.path.basename(entry_path)
                
                # Skip ignored folders
                if ignored_folders and folder_name in ignored_folders:
                    continue
                
                # Check if folder is in allowed list
                if allowed_folders is not None:
                    path_parts = entry_path.strip('/').split('/')
                    if not any(folder in path_parts for folder in allowed_folders):
                        continue
                
                # If this is an account folder, increment count
                if len(entry_path.strip('/').split('/')) == 5:
                    count += 1
                
                # Recursively count in subfolders
                count += count_account_folders(dbx, entry_path, allowed_folders, ignored_folders)
        
        # Handle pagination
        while result.has_more:
            result = dbx.files_list_folder_continue(result.cursor)
            for entry in result.entries:
                if isinstance(entry, dropbox.files.FolderMetadata):
                    entry_path = entry.path_display
                    folder_name = os.path.basename(entry_path)
                    
                    # Skip ignored folders
                    if ignored_folders and folder_name in ignored_folders:
                        continue
                    
                    # Check if folder is in allowed list
                    if allowed_folders is not None:
                        path_parts = entry_path.strip('/').split('/')
                        if not any(folder in path_parts for folder in allowed_folders):
                            continue
                    
                    # If this is an account folder, increment count
                    if len(entry_path.strip('/').split('/')) == 5:
                        count += 1
                    
                    # Recursively count in subfolders
                    count += count_account_folders(dbx, entry_path, allowed_folders, ignored_folders)
        
        return count
    except Exception as e:
        print(f"Error counting account folders: {e}")
        return 0

def get_DATA_DIRECTORY(env_file):
    """Get the renamer directory from environment or prompt user."""
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
            print(f"Access token saved to {env_file}")
        if root_folder:
            print(f"Root folder saved to {env_file}")
        if directory:
            print(f"Directory saved to {env_file}")
    except Exception as e:
        print(f"Error saving to {env_file}: {e}")
        raise

def get_access_token(env_file):
    """Get the access token from environment or prompt user."""
    # Load environment variables
    load_dotenv(env_file)
    
    # Try to get token from environment
    access_token = os.getenv('DROPBOX_TOKEN')
    
    # If no token found, prompt user
    if not access_token:
        print("\nDropbox Access Token not found in .env file.")
        print("Please follow these steps:")
        print("1. Create a file named 'token.txt' in the current directory")
        print("2. Paste your Dropbox access token into this file")
        print("3. Save the file")
        print("4. Press Enter to continue...")
        
        # Wait for user to create the file
        input()
        
        try:
            # Read token from file
            if os.path.exists('token.txt'):
                with open('token.txt', 'r') as f:
                    access_token = f.read().strip()
                
                # Delete the token file for security
                os.remove('token.txt')
                
                if not access_token:
                    print("Error: Token file is empty")
                    return get_access_token(env_file)
                
                print(f"Token length: {len(access_token)}")
                
                # Update .env file with the new token
                update_env_file(env_file, token=access_token)
            else:
                print("Error: token.txt file not found")
                return get_access_token(env_file)
                
        except Exception as e:
            print(f"Error reading token: {e}")
            return get_access_token(env_file)
    
    return access_token

def get_DROPBOX_FOLDER(env_file):
    """Get the Dropbox root folder from environment or prompt user."""
    # Load environment variables
    load_dotenv(env_file)
    
    # Try to get root folder from environment
    root_folder = os.getenv('DROPBOX_FOLDER')
    
    # If no root folder found, prompt user
    if not root_folder:
        print("\nDropbox Root Folder not found in .env file.")
        print("Please enter the Dropbox folder path to process (e.g., /Customers or full Dropbox URL):")
        root_folder = input().strip()
        
        if not root_folder:
            print("Error: No folder path provided")
            return get_DROPBOX_FOLDER(env_file)
        
        # Update .env file with the new root folder
        update_env_file(env_file, root_folder=root_folder)
    
    return root_folder

def clean_dropbox_path(path):
    """Clean and format the Dropbox path from URL or user input."""
    print(f"\nOriginal path: {path}")
    
    # Remove URL parts if present
    if 'dropbox.com/home' in path:
        path = path.split('dropbox.com/home')[-1]
        print(f"After removing URL: {path}")
    
    # Remove any URL encoding
    path = path.replace('%20', ' ')
    print(f"After URL decoding: {path}")
    
    # Remove any trailing slashes
    path = path.rstrip('/')
    
    # Ensure path starts with a single forward slash
    if not path.startswith('/'):
        path = '/' + path
    
    # Remove any "All files" prefix if present
    if path.startswith('/All files'):
        path = path[10:]  # Remove '/All files' prefix
    
    # Try to normalize the path
    path_parts = [p for p in path.split('/') if p]
    
    # Handle case sensitivity issues by trying different case combinations
    if len(path_parts) > 0:
        # Try with original case first
        path = '/' + '/'.join(path_parts)
        print(f"Trying path with original case: {path}")
        
        # If that fails, try with lowercase
        path_lower = '/' + '/'.join(p.lower() for p in path_parts)
        print(f"Trying path with lowercase: {path_lower}")
        
        # If that fails, try with uppercase
        path_upper = '/' + '/'.join(p.upper() for p in path_parts)
        print(f"Trying path with uppercase: {path_upper}")
    
    print(f"Final cleaned path: {path}")
    return path

def list_folder_contents(dbx, path):
    """List the contents of a Dropbox folder for debugging."""
    try:
        print(f"\nAttempting to list contents of: {path}")
        
        # Try to get metadata first
        try:
            metadata = dbx.files_get_metadata(path)
            print(f"Folder metadata: {metadata}")
        except Exception as e:
            print(f"Error getting metadata: {e}")
        
        # Then try to list contents
        result = dbx.files_list_folder(path)
        print(f"\nContents of {path}:")
        for entry in result.entries:
            print(f"- {entry.path_display} ({type(entry).__name__})")
        return result.entries
    except Exception as e:
        print(f"Error listing folder {path}: {e}")
        if hasattr(e, 'error'):
            print(f"Error details: {e.error}")
        return []

def find_folder_path(dbx, target_folder):
    """Try to find the correct path to a folder by searching from root."""
    print("\nSearching for folder path...")
    
    # First try the exact path
    try:
        metadata = dbx.files_get_metadata(target_folder)
        if isinstance(metadata, dropbox.files.FolderMetadata):
            return target_folder
    except:
        pass
    
    # Try different case variations
    path_parts = [p for p in target_folder.split('/') if p]
    variations = [
        '/' + '/'.join(path_parts),  # Original case
        '/' + '/'.join(p.lower() for p in path_parts),  # Lowercase
        '/' + '/'.join(p.upper() for p in path_parts),  # Uppercase
    ]
    
    for variation in variations:
        try:
            metadata = dbx.files_get_metadata(variation)
            if isinstance(metadata, dropbox.files.FolderMetadata):
                print(f"Found matching folder: {variation}")
                return variation
        except:
            continue
    
    # If exact match fails, try searching from root
    try:
        result = dbx.files_list_folder('')
        for entry in result.entries:
            if isinstance(entry, dropbox.files.FolderMetadata):
                print(f"\nChecking folder: {entry.path_display}")
                try:
                    if target_folder.lower() in entry.path_display.lower():
                        return entry.path_display
                except Exception as e:
                    print(f"Error checking folder: {e}")
    except Exception as e:
        print(f"Error searching from root: {e}")
    
    return None

def list_all_namespaces_and_roots(dbx):
    """List all available namespaces (personal, team, shared) and their root contents."""
    print("\nEnumerating all Dropbox namespaces (personal, team, shared)...")
    try:
        # Print current user's root namespace
        try:
            account = dbx.users_get_current_account()
            print(f"Current account: {account.name.display_name} (ID: {account.account_id})")
        except Exception as e:
            print(f"Could not get current account info: {e}")
        
        # List all shared folders
        try:
            shared_folders = dbx.sharing_list_folders().entries
            print("\nShared folders:")
            for folder in shared_folders:
                print(f"- {folder.name} (shared_folder_id: {folder.shared_folder_id})")
                # Try to get the folder metadata and path
                try:
                    metadata = dbx.sharing_get_folder_metadata(folder.shared_folder_id)
                    print(f"  Path: {getattr(metadata, 'path_lower', None)}")
                except Exception as e:
                    print(f"  Could not get metadata for shared folder {folder.name}: {e}")
        except Exception as e:
            print(f"Could not list shared folders: {e}")
        
        # Fallback: List root and mounted folders as before
        print("\nRoot contents:")
        try:
            result = dbx.files_list_folder('')
            for entry in result.entries:
                print(f"- {entry.name} ({entry.path_display}) [{type(entry).__name__}]")
        except Exception as e:
            print(f"Could not list root contents: {e}")
        print("\nMounted folders:")
        try:
            mounted = dbx.files_list_folder('', include_mounted_folders=True)
            for entry in mounted.entries:
                if isinstance(entry, dropbox.files.FolderMetadata):
                    print(f"- [MOUNTED] {entry.name} -- API path: {entry.path_display}")
        except Exception as e:
            print(f"Could not list mounted folders: {e}")
    except Exception as e:
        print(f"Error enumerating namespaces: {e}")

def list_app_folder_contents(dbx):
    """List contents of the app folder."""
    print("\nListing app folder contents:")
    try:
        # Get app info
        app_info = dbx.check_app()
        print(f"App folder name: {app_info.name}")
        
        # List app folder contents
        result = dbx.files_list_folder('')
        print("\nApp folder contents:")
        for entry in result.entries:
            print(f"- {entry.name} ({entry.path_display}) [{type(entry).__name__}]")
            if isinstance(entry, dropbox.files.FolderMetadata):
                try:
                    subentries = dbx.files_list_folder(entry.path_display)
                    print(f"  Contents of {entry.path_display}:")
                    for subentry in subentries.entries:
                        print(f"    - {subentry.name} ({subentry.path_display}) [{type(subentry).__name__}]")
                except Exception as e:
                    print(f"  Could not list contents of {entry.path_display}: {e}")
    except Exception as e:
        print(f"Error listing app folder contents: {e}")

def collect_folder_stats(download_dir):
    """Collect statistics about processed folders and files."""
    stats = {}
    timing_log = os.path.join(download_dir, 'processing_times.log')
    
    # Read the timing log to get processing times
    with open(timing_log, 'r') as f:
        for line in f:
            if ' - ' in line and ':' in line:
                # Parse timing entries
                timestamp, rest = line.split(' - ', 1)
                if ':' in rest:
                    account, duration = rest.split(': ', 1)
                    stats[account] = {'time': duration.strip()}
    
    # Count files in each account folder
    for item in os.listdir(download_dir):
        item_path = os.path.join(download_dir, item)
        if os.path.isdir(item_path) and item != '__pycache__':
            file_count = sum(1 for f in os.listdir(item_path) if os.path.isfile(os.path.join(item_path, f)))
            if item in stats:
                stats[item]['files'] = file_count
            else:
                stats[item] = {'files': file_count, 'time': 'N/A'}
    
    return stats

def display_summary(stats, total_time):
    """Display a summary of the processing results."""
    print("\n" + "=" * 80)
    print("PROCESSING SUMMARY")
    print("=" * 80)
    print(f"Total accounts processed: {len(stats)}")
    print(f"Total processing time: {total_time}")
    print("\nAccount Details:")
    print("-" * 80)
    print(f"{'Account Name':<40} {'Files':<10} {'Processing Time':<20}")
    print("-" * 80)
    
    total_files = 0
    for account, data in sorted(stats.items()):
        files = data.get('files', 0)
        time = data.get('time', 'N/A')
        print(f"{account:<40} {files:<10} {time:<20}")
        total_files += files
    
    print("-" * 80)
    print(f"Total files processed: {total_files}")
    print("=" * 80)

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description='Download and rename Dropbox files with their modification dates.')
    parser.add_argument('--dropbox-folder', '-f',
                      help='Dropbox folder path to process (e.g., /Customers or full Dropbox URL)')
    parser.add_argument('--directory', '-d',
                      help='Base directory to save files (overrides DATA_DIRECTORY from .env)')
    parser.add_argument('--env-file', '-e', default='.env',
                      help='Path to .env file (default: .env)')
    parser.add_argument('--debug', action='store_true',
                      help='List folder contents for debugging')
    
    args = parser.parse_args()
    
    try:
        # Start timing the total process
        total_start_time = datetime.datetime.now()
        
        # Get access token
        access_token = get_access_token(args.env_file)
        if not access_token:
            print("Error: Could not get access token")
            return
        
        # Get Dropbox root folder
        root_folder = get_DROPBOX_FOLDER(args.env_file)
        if not root_folder:
            print("Error: Could not get Dropbox root folder")
            return
        
        # Get base directory (--directory takes precedence over DATA_DIRECTORY)
        base_directory = args.directory if args.directory else get_DATA_DIRECTORY(args.env_file)
        if not base_directory:
            print("Error: Could not get base directory")
            return
        
        print(f"\nUsing base directory: {base_directory}")
        
        # If no specific folder provided, use the root folder
        if not args.dropbox_folder:
            args.dropbox_folder = root_folder
        
        # Read allowed folders from dropbox_files.txt
        allowed_folders = read_allowed_folders()
        
        # Read ignored folders from dropbox_ignore.txt
        ignored_folders = read_ignored_folders()
        
        # Clean and format the Dropbox path
        dropbox_path = clean_dropbox_path(args.dropbox_folder)
        
        # Create base directory if it doesn't exist
        ensure_directory_exists(base_directory)
        
        # Create timestamped directory for this download
        download_dir = create_timestamped_directory(base_directory)
        print(f"\nCreated download directory: {download_dir}")
        
        # Initialize Dropbox client with a longer timeout
        dbx = dropbox.Dropbox(access_token, timeout=30)
        
        # Verify the token works and get account info
        try:
            account = dbx.users_get_current_account()
            print(f"Successfully connected to Dropbox as: {account.name.display_name}")
            print(f"Account ID: {account.account_id}")
            print(f"Email: {account.email}")
        except ApiError as e:
            print(f"Error connecting to Dropbox: {e}")
            print("Please check your access token and try again.")
            return
        
        # Debug: List app folder contents
        if args.debug:
            print("\nListing app folder contents:")
            list_app_folder_contents(dbx)
        
        # Debug: List all namespaces and their root contents
        if args.debug:
            print("\nListing all namespaces and their root contents:")
            list_all_namespaces_and_roots(dbx)
        
        # Try to find the correct folder path
        found_path = find_folder_path(dbx, dropbox_path)
        if found_path:
            print(f"\nFound matching folder path: {found_path}")
            dropbox_path = found_path
        else:
            print(f"\nCould not find exact folder path. Will try with original path: {dropbox_path}")
        
        # Count total number of account folders to process
        print("\nCounting account folders to process...")
        total_accounts = [count_account_folders(dbx, dropbox_path, allowed_folders, ignored_folders)]
        processed_accounts = [0]
        print(f"Found {total_accounts[0]} account folders to process")
        
        # Process the Dropbox folder
        print(f"\nProcessing Dropbox folder: {dropbox_path}")
        process_dropbox_folder(dbx, dropbox_path, download_dir, allowed_folders, ignored_folders, None, total_accounts, processed_accounts)
        
        # Log total processing time
        total_end_time = datetime.datetime.now()
        total_duration = total_end_time - total_start_time
        total_seconds = total_duration.total_seconds()
        total_time_str = format_duration(total_seconds)
        
        with open(os.path.join(download_dir, 'processing_times.log'), 'a') as f:
            f.write("\n" + "-" * 80 + "\n")
            f.write(f"Total processing time: {total_time_str}\n")
        
        # Collect and display summary statistics
        stats = collect_folder_stats(download_dir)
        display_summary(stats, total_time_str)
        
        print(f"\nDownload complete! Total time: {total_time_str}")
        
    except Exception as e:
        print(f"Error: {e}")
        if hasattr(e, 'error'):
            print(f"Error details: {e.error}")

if __name__ == "__main__":
    main() 