import os
import sys
import logging
from playwright.sync_api import sync_playwright
from salesforce.pages.account_manager import AccountManager
from salesforce.pages.file_manager import FileManager
from salesforce.logger import OperationLogger
from dropbox_client import DropboxClient
from mock_data import get_mock_accounts

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('automation.log')
        ]
    )

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
                file_manager.navigate_to_files()
                file_manager.upload_file(step['file_path'])
            elif step['type'] == 'file_search':
                file_manager.navigate_to_files()
                file_manager.search_file(step['file_pattern'])
                
            logger.mark_step_success(step)
            
        except Exception as e:
            logging.error(f"Error processing failed step: {str(e)}")
            logger.mark_step_failure(step, str(e))

def main():
    """Main function to run the automation."""
    setup_logging()
    
    # Get configuration
    token = os.getenv('DROPBOX_TOKEN')
    test_mode = os.getenv('TEST_MODE', 'true').lower() == 'true'
    debug_mode = os.getenv('DEBUG_MODE', 'true').lower() == 'true'
    
    if not token and not test_mode:
        logging.error("DROPBOX_TOKEN environment variable is not set")
        sys.exit(1)
        
    with sync_playwright() as p:
        try:
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
                logging.error("No Salesforce page found. Please make sure you have a Salesforce page open.")
                sys.exit(1)
                
            # Use the Salesforce page
            page = salesforce_page
            
            # Initialize page objects
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
                    if not account_manager.navigate_to_accounts():
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
                        if not account_manager._debug_prompt("Do you want to proceed with this account?"):
                            logging.info("Skipping this account as requested.")
                            continue
                            
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
                            
                    # Process files
                    for file in account['files']:
                        try:
                            # Navigate to Files
                            if not file_manager.navigate_to_files():
                                logging.error("Failed to navigate to Files tab")
                                continue
                                
                            # Check number of files
                            num_files = file_manager.get_number_of_files()
                            logging.info(f"Number of files in account: {num_files}")
                            
                            # Search for file
                            search_pattern = f"{os.path.splitext(file['name'])[0]}"
                            if file_manager.search_file(search_pattern):
                                logging.info(f"File already exists: {file['name']}")
                            else:
                                logging.info(f"File not found, will be uploaded: {file['name']}")
                                
                            # Navigate back to account page
                            account_id = account_manager.current_account_id
                            if account_id:
                                account_manager.navigate_to_account_by_id(account_id)
                                
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