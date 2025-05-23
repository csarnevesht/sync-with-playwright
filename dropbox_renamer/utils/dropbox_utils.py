"""Utility functions for Dropbox operations."""

import os
import dropbox
from dropbox.exceptions import ApiError
from dotenv import load_dotenv
from .date_utils import has_date_prefix, get_folder_creation_date
from .path_utils import clean_dropbox_path
from .file_utils import log_renamed_file

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

def list_folder_contents(dbx, path):
    """List the contents of a Dropbox folder."""
    try:
        result = dbx.files_list_folder(path)
        return result.entries
    except ApiError as e:
        print(f"Error listing folder {path}: {e}")
        return []

def find_folder_path(dbx, target_folder):
    """Find the full path of a folder in Dropbox."""
    try:
        # Start from root
        result = dbx.files_list_folder('')
        
        # Check each entry
        for entry in result.entries:
            if isinstance(entry, dropbox.files.FolderMetadata):
                if entry.name == target_folder:
                    return entry.path_display
                
                # Recursively check subfolders
                sub_path = find_folder_path(dbx, target_folder)
                if sub_path:
                    return sub_path
    except ApiError as e:
        print(f"Error finding folder {target_folder}: {e}")
    
    return None

def get_access_token(env_file):
    """Get the Dropbox access token from environment or prompt user."""
    # Load environment variables
    load_dotenv(env_file)
    
    # Try to get token from environment
    token = os.getenv('DROPBOX_TOKEN')
    
    # If no token found, prompt user
    if not token:
        print("\nDROPBOX_TOKEN not found in .env file.")
        print("Please enter your Dropbox access token:")
        token = input().strip()
        
        if not token:
            print("Error: No token provided")
            return None
        
        # Update .env file with the new token
        update_env_file(env_file, token=token)
    
    return token

def get_DROPBOX_FOLDER(env_file):
    """Get the Dropbox root folder from environment or prompt user."""
    # Load environment variables
    load_dotenv(env_file)
    
    # Try to get folder from environment
    folder = os.getenv('DROPBOX_FOLDER')
    
    # If no folder found, prompt user
    if not folder:
        print("\nDROPBOX_FOLDER not found in .env file.")
        print("Please enter the root folder path in Dropbox:")
        folder = input().strip()
        
        if not folder:
            print("Error: No folder path provided")
            return None
        
        # Update .env file with the new folder
        update_env_file(env_file, root_folder=folder)
    
    return folder

def count_account_folders(dbx, path, allowed_folders=None, ignored_folders=None):
    """Count the number of account folders in the given path."""
    try:
        entries = list_folder_contents(dbx, path)
        count = 0
        
        for entry in entries:
            if isinstance(entry, dropbox.files.FolderMetadata):
                # Skip ignored folders
                if ignored_folders and entry.name in ignored_folders:
                    continue
                
                # Check if folder is allowed
                if allowed_folders and entry.name not in allowed_folders:
                    continue
                
                count += 1
        
        return count
    except ApiError as e:
        print(f"Error counting folders in {path}: {e}")
        return 0

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