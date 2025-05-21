import os
import sys
from playwright.sync_api import sync_playwright
from dropbox_client import DropboxClient
from salesforce.pages.accounts_page import AccountsPage
from file_upload import upload_files_for_account
from config import SALESFORCE_URL
import tempfile
import shutil
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from mock_data import get_mock_accounts
import time

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
        
        # Find the Salesforce page
        salesforce_page = None
        for context in browser.contexts:
            for pg in context.pages:
                if "lightning.force.com" in pg.url:
                    salesforce_page = pg
                    break
            if salesforce_page:
                break
        
        if not salesforce_page:
            print("Error: No Salesforce page found. Please make sure you have a Salesforce page open.")
            sys.exit(1)
            
        # Use the Salesforce page
        page = salesforce_page
        
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
            name_parts = [
                account['first_name'],
                account.get('middle_name'),
                account['last_name']
            ]
            full_name = ' '.join(
                part for part in name_parts 
                if part and str(part).strip().lower() not in ['none', '']
            )
            item_count = accounts_page.search_account(full_name)
            if item_count > 0:
                print(f"\nFound {item_count} existing account(s) matching '{full_name}'")
                if not accounts_page._debug_prompt("Do you want to proceed with these accounts?"):
                    print("Skipping this account as requested.")
                    continue
                accounts_page.click_first_account()
            else:
                print(f"Creating new account: {full_name}")
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
                
                # Wait a moment for the account to be available in the system
                print("Waiting for account to be available in the system...")
                time.sleep(5)
                
                # Navigate back to Accounts page
                print("Navigating back to Accounts page...")
                accounts_page.navigate_to_accounts()
                
                # Search for the newly created account
                print(f"\nSearching for newly created account: {full_name}")
                num_items = accounts_page.search_account(full_name)
                
                if num_items == 0:
                    print(f"Error: Could not find newly created account: {full_name}")
                    print("Stopping further processing due to account verification failure.")
                    sys.exit(1)  # Exit with error code
                
                # Click on the account name
                print(f"Clicking on account name: {full_name}")
                if not accounts_page.click_account_name(full_name):
                    print(f"Error: Could not click on account name: {full_name}")
                    print("Stopping further processing due to account navigation failure.")
                    sys.exit(1)  # Exit with error code
            
            # Navigate to Files
            accounts_page.navigate_to_files()
            
            # Check number of files
            num_files = accounts_page.get_number_of_files()
            print(f"Number of files in account: {num_files}")


            # Navigate back to the original account page
            print("\nNavigating back to account page...")
            account_id = accounts_page.get_account_id()
            accounts_page.navigate_to_account_by_id(account_id)
            print("Back on account page")
            
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
                        # Create a temporary account dictionary for upload_files_for_account
                        temp_account = {
                            'name': account_name,
                            'files': [{'name': os.path.basename(f), 'content': open(f, 'rb').read()} for f in files_to_upload]
                        }
                        if not upload_files_for_account(page, temp_account, debug_mode=debug_mode, max_tries=3):
                            print("Failed to upload files")
                            if not input("Do you want to continue with the next account? (y/n): ").lower().startswith('y'):
                                print("Stopping further processing as requested.")
                                sys.exit(0)
                        else:
                            print("All files uploaded successfully")
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
                            # Create a temporary account dictionary for upload_files_for_account
                            temp_account = {
                                'name': account_name,
                                'files': [{'name': os.path.basename(f), 'content': open(f, 'rb').read()} for f in local_files]
                            }
                            if not upload_files_for_account(page, temp_account, debug_mode=debug_mode, max_tries=3):
                                print("Failed to upload files")
                                if not input("Do you want to continue with the next account? (y/n): ").lower().startswith('y'):
                                    print("Stopping further processing as requested.")
                                    sys.exit(0)
                            else:
                                print("All files uploaded successfully")
                    else:
                        print("No new files to upload")

        # Close browser
        browser.close()

if __name__ == "__main__":
    main() 