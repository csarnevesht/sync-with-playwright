"""Utility functions for file operations and logging."""

import os
import datetime
from pathlib import Path

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

def log_processing_time(account_name, start_time, end_time, download_dir):
    """Log the processing time for an account."""
    duration = end_time - start_time
    seconds = duration.total_seconds()
    log_file = os.path.join(download_dir, 'processing_times.log')
    with open(log_file, 'a') as f:
        f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {account_name}: {format_duration(seconds)}\n")

def read_allowed_folders(file_path='./accounts/main.txt'):
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

def read_ignored_folders(file_path='./accounts/ignore.txt'):
    """Read the list of folders to ignore from ignore.txt."""
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

def read_account_folders(accounts_file=None):
    """Read the list of account folders from the specified file or default to accounts/main.txt."""
    if accounts_file is None:
        accounts_file = 'accounts/main.txt'
    
    try:
        with open(accounts_file, 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        print(f"Warning: Account folders file not found: {accounts_file}")
        return [] 