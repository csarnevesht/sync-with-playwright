import os
import sys
import tempfile
import re
import time
from playwright.sync_api import Page
from ..pages.accounts_page import AccountsPage
import logging
from ..pages.file_manager import SalesforceFileManager
from ..pages.account_manager import AccountManager
from typing import Optional



def upload_account_file(page: Page, file_to_upload: str, expected_items: int = 1) -> bool:
    """
    Upload a single file and verify the upload.
    
    Args:
        page: Playwright page object
        file_to_upload: Path to the file to upload
        expected_items: Number of items expected to be in the Files list after upload
    
    Returns:
        bool: True if the file was uploaded successfully, False otherwise
    """
    logging.info("\nStarting file upload...upload_account_file")
    file_name = os.path.basename(file_to_upload)
    
    logging.info(f"\nUploading file: {file_name}")
    logging.info(f"Expected number of items after upload: {expected_items}")
    
    try:
        # Click Add Files button for each file
        add_files_button = page.wait_for_selector('div[title="Add Files"]', timeout=3000)
        if add_files_button and add_files_button.is_visible():
            logging.info("Found 'Add Files' button")
            add_files_button.click()
            logging.info("Clicked 'Add Files' button")
        
        # Wait for the upload dialog
        logging.info("Waiting for upload dialog...")
        page.wait_for_selector('div.modal-container', timeout=3000)
        
        # Set single file to upload
        logging.info(f"\nSetting file to upload: {file_name}")
        page.set_input_files('input[type="file"]', [file_to_upload])
        logging.info("File set for upload")
        logging.info("Waiting for upload to complete indicator (text and icon)...")
        # Wait for the upload-complete text
        page.wait_for_selector("span.slds-text-body--small.header", timeout=30000)
        # Wait for the green checkmark icon
        page.wait_for_selector("svg.slds-icon-text-success", timeout=30000)
        logging.info("Upload indicator detected.")
        
        # Wait for upload to complete
        logging.info("\nWaiting for upload to complete...")
        page.wait_for_selector('div.progress-indicator', timeout=3000, state='hidden')
        logging.info("File upload completed")
        
        # Refresh the page to ensure we're in a clean state
        logging.info("Refreshing page...")
        page.reload()
        logging.info("Page refreshed")
        # logging.info("Waiting load state...")
        # page.wait_for_load_state('networkidle')
        
        # Verify files are visible in the list
        logging.info("\nVerifying uploaded files...")
        
        # First verify we're on the correct URL pattern
        logging.info("Verifying URL pattern...")
        current_url = page.url
        pattern = r'Account/([^/]+)/related/AttachedContentDocuments/view'
        match = re.search(pattern, current_url)
        if not match:
            logging.info(f"Error: Not on the correct Files page URL pattern. Current URL: {current_url}")
            return False
        account_id = match.group(1)
        logging.info(f"Verified correct URL pattern with account ID: {account_id}")
        
        # Now check the number of items
        logging.info("Checking number of items...")
        files = page.wait_for_selector('h1[title="Files"].slds-page-header__title', timeout=6000)
        if files:
            logging.info("Files page is visible")
            # Wait a moment for the files to appear
           
            # Check for the number of items
            items_text = page.locator('span[aria-live="polite"].countSortedByFilteredBy').first.text_content()
            logging.info(f"Items text: {items_text}")
            
            # Extract the number of items from the text
            items_match = re.search(r'(\d+)\s+items?\s+•', items_text)
            if items_match:
                num_items = int(items_match.group(1))
                logging.info(f"Found {num_items} items, expected {expected_items} items")
                
                if num_items < expected_items:
                    logging.info(f"Warning: Number of items ({num_items}) is less than expected ({expected_items})")
                    return False
                elif num_items > expected_items:
                    logging.info(f"Warning: Number of items ({num_items}) is more than expected ({expected_items})")
                    return False
                else:
                    logging.info("Success: Number of items matches expected count")
                    return True
            else:
                logging.info("Could not determine number of items from text")
                return False
        else:
            logging.info("Error: Files list not visible")
            return False
                
    except Exception as e:
        logging.info(f"Error during file upload: {str(e)}")
        return False

def upload_account_files(page: Page, account: dict, debug_mode: bool = True, max_tries: int = 10) -> bool:
    """
    Upload files for a specific account, handling the entire process from setup to verification.
    account['files'] is a list of dictionaries, each containing:
    {
        'name': 'file_name.pdf',
    }   
    account['folder_name'] is the name of the folder to upload the files to
    
    Args:
        page: Playwright page object
        account: Dictionary containing account information including files to upload
        debug_mode: Whether to enable debug mode (default: True)
        max_tries: Maximum number of retry attempts per file (default: 10)
    
    Returns:
        bool: True if all files were uploaded successfully, False otherwise
    """
    logging.info(f"Starting file upload process for account: {account['folder_name']}")
    
    
    try:
        account_manager = AccountManager(page, debug_mode=debug_mode)
        # Verify we're on the correct account page
        logging.info(f"Verifying account page URL")
        is_valid, account_id = account_manager.verify_account_page_url()
        if not is_valid:
            return False
        
        # Create temporary directory for test files
        logging.info(f"Creating temporary directory for test files")
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            files_to_upload = []
            logging.info(f"account['files']: {account['files']}")
            for file_info in account['files']:
                file_path = os.path.join(temp_dir, file_info['name'])
                with open(file_path, 'wb') as f:
                    f.write(file_info['content'])
                files_to_upload.append(file_path)
                logging.info(f"Created test file: {file_path}")
            
            # Show files to be uploaded
            logging.info("\nFiles to be uploaded:")
            for file in files_to_upload:
                logging.info(f"  + {os.path.basename(file)}")
            
            # Initialize Salesforce page objects
            file_manager = SalesforceFileManager(page, debug_mode=debug_mode)
            account_manager = AccountManager(page, debug_mode=debug_mode)
            account_manager.current_account_id = account_id

            # Upload files
            upload_success = True
            expected_items = 0  # Start with 0 files
            for file_path in files_to_upload:
                try:
                    logging.info(f"Processing file: {os.path.basename(file_path)}")
                    
                    # Check if file exists in the account
                    logging.info(f"Checking if file {os.path.basename(file_path)} already exists in the account")
                    num_files = account_manager.navigate_to_files_and_get_number_of_account_files(account_id)
                    if isinstance(num_files, str) or num_files > 0:
                        file_name_of_file_to_upload = f"{os.path.splitext(os.path.basename(file_path))[0]}"
                        logging.info(f"file_name_of_file_to_upload: {file_name_of_file_to_upload}")
                        if file_manager.search_salesforce_file(file_name_of_file_to_upload):
                            logging.info(f"File {file_name_of_file_to_upload} already exists, skipping upload for file: {file_path}")
                            account_manager.navigate_back_to_account_page()
                            continue
                    
                    account_manager.navigate_back_to_account_page()
                    
                    # Try uploading the file with retries
                    logging.info(f"**** Try uploading the file with retries, file: {file_path}")
                    current_try = 1
                    file_success = False
                    while current_try <= max_tries and not file_success:
                        try:
                            logging.info(f"Attempt {current_try} of {max_tries}")

                            # Navigate to Files page before each upload
                            logging.info("Navigating to Files page...")
                            num_files = file_manager.navigate_to_files_click_on_files_card_to_facilitate_upload()
                            logging.info(f"***Number of files in account: {num_files}")
                            
                            # Update expected items count
                            if isinstance(num_files, str):
                                # If we have a string like "50+", use 50 as the base count
                                base_count = 50
                            else:
                                base_count = num_files
                            expected_items = base_count + 1 if current_try == 1 else base_count
                            logging.info(f"***Number of files: {num_files}")
                            logging.info(f"***Expected number of items: {expected_items}")

                            logging.info(f"**** Uploading single file")
                            if upload_account_file(page, file_path, expected_items):
                                file_success = True
                                logging.info(f"**** Single file uploaded successfully")
                                break
                            
                            current_try += 1
                            if current_try <= max_tries:
                                logging.info(f"Retrying in 2 seconds...")
                                time.sleep(2)
                                
                        except Exception as e:
                            logging.error(f"Error during upload attempt {current_try}: {str(e)}")
                            page.screenshot(path=f"upload-error-attempt-{current_try}-{os.path.basename(file_path)}.png")
                            current_try += 1
                            if current_try <= max_tries:
                                logging.info(f"Retrying...")
                                # time.sleep(2)
                                account_manager.navigate_back_to_account_page()

                    
                    if not file_success:
                        logging.error(f"Failed to upload file after {max_tries} attempts: {file_path}")
                        upload_success = False
                        break
                        
                except Exception as e:
                    logging.error(f"Error processing file {os.path.basename(file_path)}: {str(e)}")
                    page.screenshot(path=f"upload-error-{os.path.basename(file_path)}.png")
                    upload_success = False
                    break
                    
            return upload_success
            
    except Exception as e:
        logging.error(f"Error in upload_files_for_account: {str(e)}")
        page.screenshot(path="upload-error-main.png")
        return False 

def upload_account_file_with_retries(page: Page, file_path: str, expected_items: int = 1, max_retries: int = 10, retry_delay: float = 1.0) -> bool:
    """Upload a file to Salesforce account with retry logic.
    
    Args:
        page: Playwright page object
        file_path: Path to the file to upload
        max_retries: Maximum number of retry attempts (default: 10)
        retry_delay: Delay between retries in seconds (default: 1.0)
        
    Returns:
        bool: True if upload succeeded, False otherwise
    """
    logger = logging.getLogger(__name__)
    logger.info(f"upload_account_file_with_retries")
    
    # Extract account ID from current URL
    current_url = page.url
    pattern = r'Account/([^/]+)/'
    match = re.search(pattern, current_url)
    if not match:
        logger.error("Could not extract account ID from URL")
        return False
    
    account_id = match.group(1)
    logger.info(f"Extracted account ID: {account_id}")
    
    account_manager = AccountManager(page, debug_mode=True)
    account_manager.current_account_id = account_id
    file_manager = SalesforceFileManager(page, debug_mode=True)
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Upload attempt {attempt + 1}/{max_retries} for file: {file_path}")
        
            
            if upload_account_file(page, file_path, expected_items):
                logger.info(f"Successfully uploaded file on attempt {attempt + 1}: {file_path}")
                return True
            
            logger.warning(f"Upload failed on attempt {attempt + 1}/{max_retries}")
            
            # Navigate back to account page before retry
            logger.info("Navigating back to account page before retry...")
            account_manager.navigate_back_to_account_page()

            # Navigate to Files section before each attempt
            logger.info("Navigating to Files section...")
            num_files = file_manager.navigate_to_files_click_on_files_card_to_facilitate_upload()
            logger.info(f"Number of files in account: {num_files}")
            
            if attempt < max_retries - 1:
                logger.info(f"Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
                
        except Exception as e:
            logger.error(f"Error during upload attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                
                logger.info(f"Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
    
    logger.error(f"Failed to upload file after {max_retries} attempts: {file_path}")
    return False 