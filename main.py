import os
import sys
from playwright.sync_api import sync_playwright
from dropbox_client import DropboxClient
from salesforce.pages.accounts_page import AccountsPage
from salesforce.logger import OperationLogger
from file_upload import upload_files_for_account
from config import SALESFORCE_URL
import tempfile
import shutil
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from mock_data import get_mock_accounts
import time

# Initialize logger
logger = OperationLogger()

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

def process_failed_steps(accounts_page: AccountsPage, page):
    """Process any failed steps from previous runs."""
    failed_steps = logger.get_failed_steps()
    if not failed_steps:
        return
    
    print(f"\nProcessing {len(failed_steps)} failed steps from previous run...")
    
    for step in failed_steps:
        print(f"\nProcessing failed step: {step['step_type']}")
        try:
            if step['step_type'] == 'account_creation':
                # Retry account creation
                details = step['details']
                accounts_page.create_new_account(
                    first_name=details['first_name'],
                    last_name=details['last_name'],
                    middle_name=details.get('middle_name'),
                    account_info=details.get('account_info')
                )
                # Log success
                logger.log_account_creation(
                    account_name=details['full_name'],
                    account_id=accounts_page.get_account_id(),
                    files=details.get('files', [])
                )
            
            elif step['step_type'] == 'file_upload':
                # Retry file upload
                details = step['details']
                if upload_files_for_account(page, details['account'], debug_mode=True, max_tries=3):
                    logger.log_file_upload(
                        account_name=details['account_name'],
                        file_name=details['file_name'],
                        status='success'
                    )
                else:
                    # Log failure again
                    logger.log_failed_step('file_upload', details)
            
            # Remove the processed step from failed steps
            logger.operations['failed_steps'].remove(step)
            logger._save_operations()
            
        except Exception as e:
            print(f"Error processing failed step: {str(e)}")
            # Keep the step in failed steps
            continue

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

        # Process any failed steps from previous runs
        process_failed_steps(accounts_page, page)

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
            
            try:
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
                    try:
                        # Create account with extracted information
                        accounts_page.create_new_account(
                            first_name=account['first_name'],
                            last_name=account['last_name'],
                            middle_name=account['middle_name'],
                            account_info=account['account_info']
                        )
                        
                        # Log successful account creation
                        account_id = accounts_page.get_account_id()
                        logger.log_account_creation(
                            account_name=full_name,
                            account_id=account_id,
                            files=[f.name for f in account['files']]
                        )
                        
                    except Exception as e:
                        print(f"Error creating account: {str(e)}")
                        # Log failed account creation
                        logger.log_failed_step('account_creation', {
                            'first_name': account['first_name'],
                            'last_name': account['last_name'],
                            'middle_name': account['middle_name'],
                            'account_info': account['account_info'],
                            'full_name': full_name,
                            'files': [f.name for f in account['files']],
                            'error': str(e)
                        })
                        continue
                
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
                            try:
                                if upload_files_for_account(page, temp_account, debug_mode=debug_mode, max_tries=3):
                                    print("All files uploaded successfully")
                                    # Log successful file uploads
                                    for file in files_to_upload:
                                        logger.log_file_upload(
                                            account_name=full_name,
                                            file_name=os.path.basename(file),
                                            status='success'
                                        )
                                else:
                                    print("Failed to upload files")
                                    # Log failed file upload
                                    logger.log_failed_step('file_upload', {
                                        'account_name': full_name,
                                        'file_name': os.path.basename(files_to_upload[0]),
                                        'account': temp_account,
                                        'error': 'Upload failed'
                                    })
                                    if not input("Do you want to continue with the next account? (y/n): ").lower().startswith('y'):
                                        print("Stopping further processing as requested.")
                                        sys.exit(0)
                            except Exception as e:
                                print(f"Error uploading files: {str(e)}")
                                # Log failed file upload
                                logger.log_failed_step('file_upload', {
                                    'account_name': full_name,
                                    'file_name': os.path.basename(files_to_upload[0]),
                                    'account': temp_account,
                                    'error': str(e)
                                })
                                if not input("Do you want to continue with the next account? (y/n): ").lower().startswith('y'):
                                    print("Stopping further processing as requested.")
                                    sys.exit(0)
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
                                try:
                                    if upload_files_for_account(page, temp_account, debug_mode=debug_mode, max_tries=3):
                                        print("All files uploaded successfully")
                                        # Log successful file uploads
                                        for file in local_files:
                                            logger.log_file_upload(
                                                account_name=full_name,
                                                file_name=os.path.basename(file),
                                                status='success'
                                            )
                                    else:
                                        print("Failed to upload files")
                                        # Log failed file upload
                                        logger.log_failed_step('file_upload', {
                                            'account_name': full_name,
                                            'file_name': os.path.basename(local_files[0]),
                                            'account': temp_account,
                                            'error': 'Upload failed'
                                        })
                                        if not input("Do you want to continue with the next account? (y/n): ").lower().startswith('y'):
                                            print("Stopping further processing as requested.")
                                            sys.exit(0)
                                except Exception as e:
                                    print(f"Error uploading files: {str(e)}")
                                    # Log failed file upload
                                    logger.log_failed_step('file_upload', {
                                        'account_name': full_name,
                                        'file_name': os.path.basename(local_files[0]),
                                        'account': temp_account,
                                        'error': str(e)
                                    })
                                    if not input("Do you want to continue with the next account? (y/n): ").lower().startswith('y'):
                                        print("Stopping further processing as requested.")
                                        sys.exit(0)
                        else:
                            print("No new files to upload")
            
            except Exception as e:
                print(f"Error processing account {full_name}: {str(e)}")
                # Log failed account processing
                logger.log_failed_step('account_processing', {
                    'account_name': full_name,
                    'error': str(e)
                })
                continue

        # After all accounts are created and files are loaded successfully
        account_names = ["John Smith", "Jane Marie Doe"]
        accounts_page.iterate_through_accounts(account_names)

        # Close browser
        browser.close()

if __name__ == "__main__":
    main() 