import os
import sys
import tempfile
import re
import time
from playwright.sync_api import Page
from salesforce.pages.accounts_page import AccountsPage
import logging
from salesforce.pages.file_manager import FileManager
from salesforce.pages.account_manager import AccountManager

def verify_account_page_url(page: Page, account_id=None) -> tuple[bool, str]:
    """
    Verify we're on the correct account page URL pattern.
    
    Args:
        page: Playwright page object
        account_id: Optional specific account ID to verify against. If None, any valid account ID is accepted.
    
    Returns:
        tuple[bool, str]: (is_valid_url, account_id)
    """
    logging.info(f"verify_account_page_url")
    current_url = page.url
    logging.info(f"\nCurrent URL: {current_url}")
    
    # Get Salesforce URL from environment variable
    salesforce_url = os.getenv('SALESFORCE_URL')
    if not salesforce_url:
        logging.error("Error: SALESFORCE_URL environment variable is not set")
        return False, None
    
    # Pattern: SALESFORCE_URL/Account/SOME_ID/view
    expected_pattern = f"{re.escape(salesforce_url)}.*/Account/([^/]+)/view"
    logging.info(f"***Expected pattern: {expected_pattern}")
    logging.info(f"Current URL: {current_url}")
    match = re.match(expected_pattern, current_url)
    
    if not match:
        logging.error("Error: Not on the correct account page URL pattern")
        logging.info(f"Current URL: {current_url}")
        logging.info(f"Expected pattern: {expected_pattern}")
        return False, None
    
    found_account_id = match.group(1)
    
    if account_id and found_account_id != account_id:
        logging.error(f"Error: Account ID mismatch. Found: {found_account_id}, Expected: {account_id}")
        return False, None
    
    logging.info(f"Verified correct URL pattern with account ID: {found_account_id}")
    return True, found_account_id

def upload_single_file(page: Page, file_to_upload: str, expected_items: int = 1) -> bool:
    """
    Upload a single file and verify the upload.
    
    Args:
        page: Playwright page object
        file_to_upload: Path to the file to upload
        expected_items: Number of items expected to be in the Files list after upload
    
    Returns:
        bool: True if the file was uploaded successfully, False otherwise
    """
    logging.info("\nStarting file upload...")
    file_name = os.path.basename(file_to_upload)
    
    logging.info(f"\nUploading file: {file_name}")
    logging.info(f"Expected number of items after upload: {expected_items}")
    
    try:
        # Click Add Files button for each file
        add_files_button = page.wait_for_selector('div[title="Add Files"]', timeout=4000)
        if add_files_button and add_files_button.is_visible():
            logging.info("Found 'Add Files' button")
            add_files_button.click()
            logging.info("Clicked 'Add Files' button")
        
        # Wait for the upload dialog
        logging.info("Waiting for upload dialog...")
        page.wait_for_selector('div.modal-container', timeout=2000)
        
        # Set single file to upload
        logging.info(f"\nSetting file to upload: {file_name}")
        page.set_input_files('input[type="file"]', [file_to_upload])
        logging.info("File set for upload")
        
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
        files = page.wait_for_selector('h1[title="Files"].slds-page-header__title', timeout=4000)
        if files:
            logging.info("Files page is visible")
            # Wait a moment for the files to appear
            time.sleep(1)
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

def upload_files_for_account(page: Page, account: dict, debug_mode: bool = True, max_tries: int = 10) -> bool:
    """
    Upload files for a specific account, handling the entire process from setup to verification.
    
    Args:
        page: Playwright page object
        account: Dictionary containing account information including files to upload
        debug_mode: Whether to enable debug mode (default: True)
        max_tries: Maximum number of retry attempts per file (default: 10)
    
    Returns:
        bool: True if all files were uploaded successfully, False otherwise
    """
    logging.info(f"Starting file upload process for account: {account['folder_name']}")
    
    # Verify we're on the correct account page
    logging.info(f"Verifying account page URL")
    is_valid, account_id = verify_account_page_url(page)
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
        accounts_page = AccountsPage(page, debug_mode=debug_mode)
        file_manager = FileManager(page, debug_mode=debug_mode)
        account_manager = AccountManager(page, debug_mode=debug_mode)
        account_manager.current_account_id = account_id

        # Upload files
        upload_success = True
        expected_items = 0  # Start with 0 files
        for file_path in files_to_upload:
            
            logging.info(f"Processing file: {os.path.basename(file_path)}")
            
            # Check if file exists in the account
            logging.info(f"Checking if file {os.path.basename(file_path)} already exists in the account")
            num_files = file_manager.navigate_to_files()
            if num_files > 0:
                search_pattern = f"{os.path.splitext(os.path.basename(file_path))[0]}"
                logging.info(f"search_pattern: {search_pattern}")
                if file_manager.search_file(search_pattern):
                    logging.info(f"File {os.path.basename(file_path)} already exists, skipping upload")
                    logging.info(f"Skipping file: {file_path}")
                    account_manager.navigate_back_to_account_page()
                    continue
            
            account_manager.navigate_back_to_account_page()
            
            # Try uploading the file with retries
            logging.info(f"**** Try uploading the file with retries, file: {file_path}")
            current_try = 1
            file_success = False
            while current_try <= max_tries and not file_success:
                logging.info(f"Attempt {current_try} of {max_tries}")

                # Navigate to Files page before each upload
                logging.info("Navigating to Files page...")
                num_files = file_manager.navigate_to_files()
                logging.info(f"***Number of files in account: {num_files}")
                
                # Update expected items count
                expected_items = num_files + 1 if current_try == 1 else num_files
                logging.info(f"***Number of files: {num_files}")
                logging.info(f"***Expected number of items: {expected_items}")

                logging.info(f"**** Uploading single file")
                if upload_single_file(page, file_path, expected_items):
                    file_success = True
                    logging.info(f"**** Single file uploaded successfully")

                logging.info(f"**** Navigating back to the original account page")  
                # Navigate back to the original account page
                account_manager.navigate_back_to_account_page()
            

                if not file_success:
                    logging.warning(f"File upload failed. Retrying... (Attempt {current_try + 1} of {max_tries})")
                    if current_try < max_tries:
                        current_try += 1
                        continue
                    # else:
                    #     logging.error("Maximum retry attempts reached. Upload may be incomplete.")
                    #     upload_success = False
                    #     if not input("Do you want to try again? (y/n): ").lower().startswith('y'):
                    #         logging.info("Stopping as requested.")
                    #         sys.exit(0)
        
        logging.info("File upload process completed successfully")
        return upload_success 