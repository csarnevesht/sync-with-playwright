import os
import sys
from playwright.sync_api import sync_playwright
from dropbox_client import DropboxClient
from salesforce.pages.accounts_page import AccountsPage
from config import SALESFORCE_URL
import tempfile
import shutil
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from mock_data import get_mock_accounts

def get_dropbox_token():
    """Get Dropbox token from token.txt or prompt user."""
    if os.path.exists('token.txt'):
        with open('token.txt', 'r') as f:
            return f.read().strip()
    
    token = input("Please enter your Dropbox API token: ")
    with open('token.txt', 'w') as f:
        f.write(token)
    return token

def create_mock_files(mock_account: Dict, temp_dir: str) -> List[str]:
    """Create mock files in the temporary directory."""
    local_files = []
    for file_info in mock_account['files']:
        file_path = os.path.join(temp_dir, file_info['name'])
        with open(file_path, 'wb') as f:
            f.write(file_info['content'])
        local_files.append(file_path)
    return local_files

def main():
    # Check for test mode
    test_mode = os.getenv('TEST_MODE', '').lower() in ['true', '1', 'yes']
    debug_mode = os.getenv('DEBUG_MODE', '').lower() in ['true', '1', 'yes']
    
    if test_mode:
        logging.info("Test mode is enabled - using mock data")
        mock_accounts = get_mock_accounts()
    else:
        # Get Dropbox token
        token = get_dropbox_token()
        if not token:
            print("Error: Dropbox token is required")
            sys.exit(1)

    if debug_mode:
        logging.info("Debug mode is enabled")

    # Start Playwright
    with sync_playwright() as p:
        # Connect to existing Chrome browser
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        # Print URLs of all open pages for debugging
        for i, context in enumerate(browser.contexts):
            for j, pg in enumerate(context.pages):
                print(f"Context {i}, Page {j}, URL: {pg.url}")
        # Use the first page from the first context
        page = browser.contexts[0].pages[0]
        
        # Navigate to Salesforce
        page.goto(SALESFORCE_URL)
        
        # Initialize Salesforce page objects
        accounts_page = AccountsPage(page, debug_mode=debug_mode)

        # Process accounts
        if test_mode:
            accounts_to_process = mock_accounts
        else:
            # Initialize Dropbox client
            dbx = DropboxClient(token, debug_mode=debug_mode)
            accounts_to_process = [
                {
                    'folder_name': folder,
                    'first_name': first,
                    'last_name': last,
                    'middle_name': middle,
                    'account_info': dbx.extract_account_info(folder),
                    'files': dbx.get_account_files(folder)
                }
                for folder in dbx.get_account_folders()
                for first, last, middle in [dbx.parse_account_name(folder)]
            ]

        # Process each account
        for account in accounts_to_process:
            print(f"\nProcessing account: {account['folder_name']}")
            
            account_name = f"{account['first_name']} {account['last_name']}"
            
            # Navigate to Accounts page
            accounts_page.navigate_to_accounts()
            
            # Search for account
            if accounts_page.search_account(account_name):
                print(f"Found existing account: {account_name}")
                accounts_page.click_first_account()
            else:
                print(f"Creating new account: {account_name}")
                if account['account_info']:
                    print("Found account information")
                else:
                    print("No account information found")
                
                # Create account with extracted information
                accounts_page.create_new_account(
                    first_name=account['first_name'],
                    last_name=account['last_name'],
                    middle_name=account['middle_name'],
                    account_info=account['account_info']
                )
                accounts_page.click_first_account()
            
            # Navigate to Files
            accounts_page.navigate_to_files()
            
            # Check number of files
            num_files = accounts_page.get_number_of_files()
            print(f"Number of files in account: {num_files}")
            
            # Create temporary directory for downloads
            with tempfile.TemporaryDirectory() as temp_dir:
                if num_files == 0:
                    # Upload all files for new accounts
                    if test_mode:
                        files_to_upload = create_mock_files(account, temp_dir)
                    else:
                        files_to_upload = []
                        for file in account['files']:
                            local_path = dbx.download_file(
                                f"/{dbx.root_folder}/{account['folder_name']}/{file.name}",
                                temp_dir
                            )
                            if local_path:
                                files_to_upload.append(local_path)
                    
                    if files_to_upload:
                        print(f"Uploading {len(files_to_upload)} files to Salesforce...")
                        if not accounts_page.upload_files(files_to_upload):
                            print("Failed to upload files")
                        elif not accounts_page.verify_files_uploaded([os.path.basename(f) for f in files_to_upload]):
                            print("Not all files were verified after upload")
                        else:
                            print("All files uploaded and verified successfully")
                else:
                    # Search for each file
                    found_files = []
                    files_to_add = []
                    
                    for file in account['files']:
                        # Create search pattern
                        search_pattern = f"*{os.path.splitext(file.name)[0]}"
                        
                        if accounts_page.search_file(search_pattern):
                            found_files.append(file.name)
                        else:
                            files_to_add.append(file)
                    
                    # Upload new files
                    if files_to_add:
                        print(f"Found {len(files_to_add)} new files to upload")
                        if test_mode:
                            local_files = create_mock_files({'files': files_to_add}, temp_dir)
                        else:
                            local_files = []
                            for file in files_to_add:
                                local_path = dbx.download_file(
                                    f"/{dbx.root_folder}/{account['folder_name']}/{file.name}",
                                    temp_dir
                                )
                                if local_path:
                                    local_files.append(local_path)
                        
                        if local_files:
                            print(f"Uploading {len(local_files)} files to Salesforce...")
                            if not accounts_page.upload_files(local_files):
                                print("Failed to upload files")
                            elif not accounts_page.verify_files_uploaded([os.path.basename(f) for f in local_files]):
                                print("Not all files were verified after upload")
                            else:
                                print("All files uploaded and verified successfully")
                    else:
                        print("No new files to upload")

        # Close browser
        browser.close()

if __name__ == "__main__":
    main() 