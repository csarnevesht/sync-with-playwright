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
import logging
from dropbox_renamer.utils.dropbox_utils import get_access_token

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

def ensure_directory_exists(directory):
    """Ensure the directory exists, create it if it doesn't."""
    try:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Directory exists or was created: {directory}")
        return True
    except Exception as e:
        print(f"✗ Error creating directory {directory}: {str(e)}")
        return False

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

def test_dropbox_connection():
    """Test the Dropbox connection and token validity."""
    try:
        # Get access token
        token = get_access_token()
        logger.info(f"Token loaded successfully (length: {len(token)})")
        
        # Initialize Dropbox client
        dbx = dropbox.Dropbox(token)
        logger.info("Successfully initialized Dropbox client")
        
        # Test the connection
        account = dbx.users_get_current_account()
        logger.info(f"Successfully connected to Dropbox as: {account.name.display_name}")
        return True
        
    except ApiError as e:
        if e.error.is_expired_access_token():
            logger.error("\nError: Your Dropbox access token has expired.")
            logger.error("\nTo fix this:")
            logger.error("1. Go to https://www.dropbox.com/developers/apps")
            logger.error("2. Select your app")
            logger.error("3. Under 'OAuth 2', click 'Generated access token'")
            logger.error("4. Generate a new access token")
            logger.error("5. Update your .env file with the new token:")
            logger.error("   DROPBOX_TOKEN=your_new_token")
        else:
            logger.error(f"Error connecting to Dropbox: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
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
        if not test_dropbox_connection():
            print("✗ Could not get access token")
            return
        
        # Get Dropbox folder
        print("\n2. Checking Dropbox folder...")
        root_folder = get_DROPBOX_FOLDER(args.env_file)
        if not root_folder:
            print("✗ Could not get Dropbox folder")
            return
        
        # Get and test data directory
        print("\n3. Checking data directory...")
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