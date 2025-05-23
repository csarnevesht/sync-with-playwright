#!/usr/bin/env python3

"""
Dropbox Connection Test Script

This script tests the Dropbox connection and configuration by:
1. Verifying the access token
2. Checking the Dropbox folder path
3. Testing directory creation
"""

import os
import dropbox
from dropbox.exceptions import ApiError
from dotenv import load_dotenv
import argparse
from dropbox_renamer.utils.path_utils import clean_dropbox_path

def ensure_directory_exists(directory):
    """Ensure the directory exists, create it if it doesn't."""
    try:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Directory exists or was created: {directory}")
        return True
    except Exception as e:
        print(f"✗ Error creating directory {directory}: {str(e)}")
        return False

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

def test_dropbox_connection(dbx, dropbox_path):
    """Test the Dropbox connection and folder access."""
    try:
        # Test account connection
        account = dbx.users_get_current_account()
        print(f"✓ Successfully connected to Dropbox as: {account.name.display_name}")
        print(f"✓ Account ID: {account.account_id}")
        print(f"✓ Email: {account.email}")
        
        # Clean and test the path
        cleaned_path = clean_dropbox_path(dropbox_path)
        print(f"\nTesting path: {cleaned_path}")
        
        # Test folder access
        try:
            metadata = dbx.files_get_metadata(cleaned_path)
            print(f"✓ Successfully accessed Dropbox folder: {cleaned_path}")
            print(f"✓ Folder type: {type(metadata).__name__}")
            return True
        except ApiError as e:
            print(f"✗ Error accessing Dropbox folder: {e}")
            # Try alternative case versions if the first attempt fails
            try:
                path_parts = [p for p in cleaned_path.split('/') if p]
                # Try lowercase
                path_lower = '/' + '/'.join(p.lower() for p in path_parts)
                metadata = dbx.files_get_metadata(path_lower)
                print(f"✓ Successfully accessed Dropbox folder with lowercase path: {path_lower}")
                print(f"✓ Folder type: {type(metadata).__name__}")
                return True
            except ApiError:
                try:
                    # Try uppercase
                    path_upper = '/' + '/'.join(p.upper() for p in path_parts)
                    metadata = dbx.files_get_metadata(path_upper)
                    print(f"✓ Successfully accessed Dropbox folder with uppercase path: {path_upper}")
                    print(f"✓ Folder type: {type(metadata).__name__}")
                    return True
                except ApiError:
                    return False
            
    except ApiError as e:
        print(f"✗ Error connecting to Dropbox: {e}")
        return False

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description='Test Dropbox connection and configuration.')
    parser.add_argument('--env-file', '-e', default='.env',
                      help='Path to .env file (default: .env)')
    
    args = parser.parse_args()
    
    try:
        print("\n=== Testing Dropbox Configuration ===")
        
        # Check if .env file exists
        if not os.path.exists(args.env_file):
            print(f"\n.env file not found at: {args.env_file}")
            print("Creating new .env file...")
            with open(args.env_file, 'w') as f:
                f.write("# Dropbox Configuration\n")
            print(f"✓ Created new .env file at: {args.env_file}")
        
        # Get access token
        print("\n1. Checking access token...")
        access_token = get_access_token(args.env_file)
        if not access_token:
            print("✗ Could not get access token")
            return
        
        # Initialize Dropbox client
        print("\n2. Initializing Dropbox client...")
        dbx = dropbox.Dropbox(access_token, timeout=30)
        
        # Get Dropbox folder
        print("\n3. Checking Dropbox folder...")
        root_folder = get_DROPBOX_FOLDER(args.env_file)
        if not root_folder:
            print("✗ Could not get Dropbox folder")
            return
        
        # Test Dropbox connection
        print("\n4. Testing Dropbox connection...")
        if not test_dropbox_connection(dbx, root_folder):
            print("✗ Dropbox connection test failed")
            return
        
        # Get and test data directory
        print("\n5. Checking data directory...")
        base_directory = get_DATA_DIRECTORY(args.env_file)
        if not base_directory:
            print("✗ Could not get data directory")
            return
        
        if not ensure_directory_exists(base_directory):
            print("✗ Could not create data directory")
            return
        
        print("\n=== All Tests Passed Successfully! ===")
        print("\nConfiguration Summary:")
        print(f"✓ Dropbox Account: {dbx.users_get_current_account().name.display_name}")
        print(f"✓ Dropbox Folder: {root_folder}")
        print(f"✓ Data Directory: {base_directory}")
        print(f"✓ Configuration File: {args.env_file}")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        if hasattr(e, 'error'):
            print(f"✗ Error details: {e.error}")

if __name__ == "__main__":
    main() 