"""Utility functions for Dropbox operations."""

import os
import dropbox
from dropbox.exceptions import ApiError
from dotenv import load_dotenv
from .date_utils import has_date_prefix, get_folder_creation_date
from .path_utils import clean_dropbox_path

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
    """List contents of a Dropbox folder."""
    try:
        result = dbx.files_list_folder(path)
        return result.entries
    except ApiError as e:
        print(f"Error listing folder contents for {path}: {e}")
        return []

def count_account_folders(dbx, dropbox_path, allowed_folders=None, ignored_folders=None):
    """Count the number of account folders in the Dropbox path."""
    try:
        # List contents of the root folder
        entries = list_folder_contents(dbx, dropbox_path)
        
        # Count folders that match the criteria
        count = 0
        for entry in entries:
            if isinstance(entry, dropbox.files.FolderMetadata):
                folder_name = entry.name
                
                # Skip ignored folders
                if ignored_folders and folder_name in ignored_folders:
                    continue
                    
                # Check if folder is allowed
                if allowed_folders:
                    if folder_name in allowed_folders:
                        count += 1
                else:
                    count += 1
                    
        return count
    except Exception as e:
        print(f"Error counting account folders: {e}")
        return 0

def find_folder_path(dbx, target_folder):
    """Find the full path of a folder in Dropbox."""
    try:
        # Start from root
        result = dbx.files_list_folder('')
        
        # Search through all entries
        for entry in result.entries:
            if isinstance(entry, dropbox.files.FolderMetadata):
                if entry.name.lower() == target_folder.lower():
                    return entry.path_display
                
                # Recursively search subfolders
                sub_path = find_folder_path(dbx, target_folder)
                if sub_path:
                    return sub_path
                    
        return None
    except ApiError as e:
        print(f"Error finding folder path for {target_folder}: {e}")
        return None

def list_all_namespaces_and_roots(dbx):
    """List all namespaces and root folders in Dropbox."""
    try:
        # Get all namespaces
        namespaces = dbx.team_namespaces_list()
        
        print("\nAvailable Namespaces:")
        for namespace in namespaces.namespaces:
            print(f"- {namespace.name} (ID: {namespace.namespace_id})")
            
        # Get root folders
        root_folders = dbx.files_list_folder('')
        
        print("\nRoot Folders:")
        for entry in root_folders.entries:
            if isinstance(entry, dropbox.files.FolderMetadata):
                print(f"- {entry.name} (Path: {entry.path_display})")
                
    except ApiError as e:
        print(f"Error listing namespaces and roots: {e}")

def list_app_folder_contents(dbx):
    """List contents of the app folder in Dropbox."""
    try:
        result = dbx.files_list_folder('')
        
        print("\nApp Folder Contents:")
        for entry in result.entries:
            if isinstance(entry, dropbox.files.FolderMetadata):
                print(f"📁 {entry.name}")
            else:
                print(f"📄 {entry.name}")
                
    except ApiError as e:
        print(f"Error listing app folder contents: {e}")

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