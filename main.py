import json
import os
from pprint import pprint
import sys
import logging
from playwright.sync_api import sync_playwright
from salesforce.pages.account_manager import AccountManager
from salesforce.pages.file_manager import FileManager
from salesforce.logger import OperationLogger
from sync.dropbox_client import DropboxClient
from salesforce.utils.mock_data import get_mock_accounts
from salesforce.file_upload import upload_files_for_account
from salesforce.browser import get_salesforce_page


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("operations.log"),
        logging.StreamHandler()
    ]
)

# def setup_logging():
#     """Set up logging configuration."""
#     logging.basicConfig(
#         level=logging.INFO,
#         format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#         handlers=[
#             logging.StreamHandler(),
#             logging.FileHandler('operations.log')
#         ]
#     )

def process_failed_steps(account_manager: AccountManager, file_manager: FileManager, page):
    """Process any failed steps from previous runs."""
    logger = OperationLogger()
    failed_steps = logger.get_failed_steps()
    
    if not failed_steps:
        logging.info("No failed steps to process")
        return
        
    logging.info(f"Processing {len(failed_steps)} failed steps")
    
    for step in failed_steps:
        try:
            if step['type'] == 'account_creation':
                account_manager.create_new_account(
                    step['first_name'],
                    step['last_name'],
                    step.get('middle_name'),
                    step.get('account_info')
                )
            elif step['type'] == 'file_upload':
                file_manager.navigate_to_files_click_on_files_card_to_facilitate_upload()
                file_manager.upload_file(step['file_path'])
            elif step['type'] == 'file_search':
                file_manager.navigate_to_files_click_on_files_card_to_facilitate_upload()
                file_manager.search_file(step['file_pattern'])
                
            logger.mark_step_success(step)
            
        except Exception as e:
            logging.error(f"Error processing failed step: {str(e)}")
            logger.mark_step_failure(step, str(e))

def main():
    """Main function to run the automation."""
    # setup_logging()
    
    # Get configuration
    token = os.getenv('DROPBOX_TOKEN')
    test_mode = os.getenv('TEST_MODE', 'true').lower() == 'true'
    debug_mode = os.getenv('DEBUG_MODE', 'true').lower() == 'true'
    
    if not token and not test_mode:
        logging.error("DROPBOX_TOKEN environment variable is not set")
        sys.exit(1)
        
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            # Initialize page objects
            logging.info(f"****Initializing page objects")
            account_manager = AccountManager(page, debug_mode)
            file_manager = FileManager(page, debug_mode)
            
            # Process failed steps from previous runs
            process_failed_steps(account_manager, file_manager, page)
            
            # Get accounts to process
            if test_mode:
                accounts_to_process = get_mock_accounts()
            else:
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
                logging.info(f"\nProcessing account: {account['folder_name']}")
                
                try:
                    # Navigate to Accounts page
                    if not account_manager.navigate_to_accounts_list_page():
                        logging.error("Failed to navigate to Accounts page")
                        continue
                        
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
                    
                    # Check if account exists
                    if account_manager.account_exists(full_name):
                        logging.info(f"Account already exists: {full_name}")
            
                            
                        if not account_manager.click_account_name(full_name):
                            logging.error(f"Failed to navigate to account view page for: {full_name}")
                            continue
                    else:
                        # Create new account
                        logging.info(f"Creating new account: {full_name}")
                        if not account_manager.create_new_account(
                            account['first_name'],
                            account['last_name'],
                            account.get('middle_name'),
                            account.get('account_info')
                        ):
                            logging.error(f"Failed to create account for: {full_name}")
                            continue

                    current_url = page.url
                    logging.info(f"\nCurrent page URL: {current_url}")

                    is_valid, account_id = account_manager.verify_account_page_url()
                    if not is_valid:
                        logging.error(f"Failed to verify account page URL for: {full_name}")
                        continue
                    if not account_id:
                        logging.error(f"Failed to get account id for: {full_name}")
                        continue

                    # Process files
                    logging.info(f"****Processing files for account: {full_name}")
                    logging.info(f"****Files: {account['files']}")
                    for file in account['files']:
                        try:
                            # Navigate to Files
                            logging.info(f"****Navigating to Files")
                            num_files = account_manager.navigate_to_files_and_get_number_of_files_for_this_account(account_id)
                            if num_files == -1:
                                logging.error("Failed to navigate to Files")
                                account_manager.navigate_back_to_account_page()
                                continue
                                
                            # Check number of files
                            logging.info(f"Number of files in account: {num_files}")
                            
                            if isinstance(num_files, str) or num_files == 0:
                                logging.info(f"No files exist or count is {num_files}, will upload: {file['name']}")

                                account_manager.navigate_back_to_account_page()

                                # Upload files for the account
                                logging.info(f"****Uploading files for account: {full_name}")
                                upload_success = upload_files_for_account(page, account, debug_mode=debug_mode, max_tries=1)
                                if not upload_success:
                                    logging.error("File upload process completed with errors")
                                    sys.exit(1)
                            else:
                                # Search for file only if there are existing files
                                search_pattern = f"{os.path.splitext(file['name'])[0]}"
                                if file_manager.search_file(search_pattern):
                                    logging.info(f"File already exists: {file['name']}")
                                else:
                                    logging.info(f"File not found, will be uploaded: {file['name']}")
                                    #  CAROLINA HERE
                                    account_manager.navigate_back_to_account_page()
                                    # Upload single file for the account
                                    logging.info(f"****Uploading file: {file['name']} for account: {full_name}")
                                    files = account['files']
                                    file = [f for f in files if f['name'] == file['name']]
                                    if not file:
                                        logging.error(f"Could not find file {file['name']} in files list")
                                        continue
                                    account_copy = account.copy()
                                    if 'files' in account_copy:
                                        account_copy['files'] = [file[0]]  # Get the first (and only) matching file
                                    upload_success = upload_files_for_account(page, account_copy, debug_mode=debug_mode, max_tries=1)
                                    if not upload_success:
                                        logging.error("File upload process completed with errors")
                                        sys.exit(1)

                            account_manager.navigate_back_to_account_page()
  
                        except Exception as e:
                            logging.error(f"Error processing file {file['name']}: {str(e)}")
                            continue
                            
                except Exception as e:
                    logging.error(f"Error processing account {account['folder_name']}: {str(e)}")
                    continue
                    
        except Exception as e:
            logging.error(f"Error in main execution: {str(e)}")
            if 'page' in locals():
                page.screenshot(path="main-error.png")
            
        finally:
            if 'browser' in locals():
                browser.close()

                                
if __name__ == "__main__":
    main() 