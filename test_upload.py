import os
import sys
from playwright.sync_api import sync_playwright
from salesforce.pages.accounts_page import AccountsPage
import tempfile
import logging
from mock_data import get_mock_accounts
import re
import time

def verify_account_page_url(page, account_id=None) -> tuple[bool, str]:
    """
    Verify we're on the correct account page URL pattern.
    
    Args:
        page: Playwright page object
        account_id: Optional specific account ID to verify against. If None, any valid account ID is accepted.
    
    Returns:
        tuple[bool, str]: (is_valid_url, account_id)
    """
    current_url = page.url
    print(f"\nCurrent URL: {current_url}")
    
    # Get Salesforce URL from environment variable
    salesforce_url = os.getenv('SALESFORCE_URL')
    if not salesforce_url:
        print("Error: SALESFORCE_URL environment variable is not set")
        return False, None
    
    # Pattern: SALESFORCE_URL/Account/SOME_ID/view
    pattern = f"{re.escape(salesforce_url)}.*/Account/([^/]+)/view"
    match = re.match(pattern, current_url)
    
    if not match:
        print("Error: Not on the correct account page URL pattern")
        print(f"Expected pattern: {salesforce_url}/Account/{{account_id}}/view")
        return False, None
    
    found_account_id = match.group(1)
    
    if account_id and found_account_id != account_id:
        print(f"Error: Account ID mismatch. Found: {found_account_id}, Expected: {account_id}")
        return False, None
    
    print(f"Verified correct URL pattern with account ID: {found_account_id}")
    return True, found_account_id

def upload_single_file(page, file_to_upload, expected_items=1):
    """
    Upload a single file and verify the upload.
    
    Args:
        page: Playwright page object
        file_to_upload: Path to the file to upload
        expected_items: Number of items expected to be in the Files list after upload
    
    Returns:
        bool: True if the file was uploaded successfully, False otherwise
    """
    print("\nStarting file upload...")
    file_name = os.path.basename(file_to_upload)
    
    print(f"\nUploading file: {file_name}")
    print(f"Expected number of items after upload: {expected_items}")
    
    try:
        # Click Add Files button for each file
        add_files_button = page.wait_for_selector('div[title="Add Files"]', timeout=5000)
        if add_files_button and add_files_button.is_visible():
            print("Found 'Add Files' button")
            add_files_button.click()
            print("Clicked 'Add Files' button")
        
        # Wait for the upload dialog
        print("Waiting for upload dialog...")
        page.wait_for_selector('div.modal-container', timeout=10000)
        
        # Set single file to upload
        print(f"\nSetting file to upload: {file_name}")
        page.set_input_files('input[type="file"]', [file_to_upload])
        print("File set for upload")
        
        # Wait for upload to complete
        print("\nWaiting for upload to complete...")
        page.wait_for_selector('div.progress-indicator', timeout=30000, state='hidden')
        print("File upload completed")
        
        # Refresh the page to ensure we're in a clean state
        print("Refreshing page...")
        page.reload()
        page.wait_for_load_state('networkidle')
        
        # Verify files are visible in the list
        print("\nVerifying uploaded files...")
        
        # First verify we're on the correct URL pattern
        current_url = page.url
        pattern = r'Account/([^/]+)/related/AttachedContentDocuments/view'
        match = re.search(pattern, current_url)
        if not match:
            print(f"Error: Not on the correct Files page URL pattern. Current URL: {current_url}")
            return False
        account_id = match.group(1)
        print(f"Verified correct URL pattern with account ID: {account_id}")
        
        # Now check the number of items
        files = page.wait_for_selector('h1[title="Files"].slds-page-header__title', timeout=10000)
        if files:
            print("Files page is visible")
            # Wait a moment for the files to appear
            time.sleep(2)
            # Check for the number of items
            items_text = page.locator('span[aria-live="polite"].countSortedByFilteredBy').first.text_content()
            print(f"Items text: {items_text}")
            
            # Extract the number of items from the text
            items_match = re.search(r'(\d+)\s+items?\s+•', items_text)
            if items_match:
                num_items = int(items_match.group(1))
                print(f"Found {num_items} items, expected {expected_items} items")
                
                if num_items < expected_items:
                    print(f"Warning: Number of items ({num_items}) is less than expected ({expected_items})")
                    return False
                elif num_items > expected_items:
                    print(f"Warning: Number of items ({num_items}) is more than expected ({expected_items})")
                    return False
                else:
                    print("Success: Number of items matches expected count")
                    return True
            else:
                print("Could not determine number of items from text")
                return False
        else:
            print("Error: Files list not visible")
            return False
                
    except Exception as e:
        print(f"Error during file upload: {str(e)}")
        return False

def upload_files_for_account(page, account, debug_mode=True, max_tries=3):
    """
    Upload files for a specific account, handling the entire process from setup to verification.
    
    Args:
        page: Playwright page object
        account: Dictionary containing account information including files to upload
        debug_mode: Whether to enable debug mode (default: True)
        max_tries: Maximum number of retry attempts per file (default: 3)
    
    Returns:
        bool: True if all files were uploaded successfully, False otherwise
    """
    print(f"\nPreparing to upload files for account...")
    
    # Verify we're on the correct account page
    is_valid, account_id = verify_account_page_url(page)
    if not is_valid:
        return False
    
    # Create temporary directory for test files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test files
        files_to_upload = []
        for file_info in account['files']:
            file_path = os.path.join(temp_dir, file_info['name'])
            with open(file_path, 'wb') as f:
                f.write(file_info['content'])
            files_to_upload.append(file_path)
            print(f"Created test file: {file_path}")
        
        # Show files to be uploaded
        print("\nFiles to be uploaded:")
        for file in files_to_upload:
            print(f"  + {os.path.basename(file)}")
        
        # Initialize Salesforce page objects
        accounts_page = AccountsPage(page, debug_mode=debug_mode)

        # Upload files
        upload_success = True
        expected_items = 0  # Start with 0 files
        for file_path in files_to_upload:
            
            print(f"***Uploading file: {file_path}")

            # Try uploading the file with retries
            current_try = 1
            file_success = False
            while current_try <= max_tries and not file_success:
                print(f"Attempt {current_try} of {max_tries}")

                # Navigate to Files page before each upload
                print("\nNavigating to Files page...")
                num_files = accounts_page.navigate_to_files()
                print(f"***Number of files in account: {num_files}")
                
                # Wait for page to be fully loaded
                print("Waiting for page to be fully loaded...")
                page.wait_for_load_state('networkidle')
                
                # Update expected items count
                expected_items = num_files + 1
                print(f"***Number of files: {num_files}")
                print(f"***Expected number of items: {expected_items}")

                if upload_single_file(page, file_path, expected_items):
                    file_success = True

                # Navigate back to the original account page
                print("\nNavigating back to account page...")
                page.goto(f"{os.getenv('SALESFORCE_URL')}/lightning/r/Account/{account_id}/view")
                page.wait_for_load_state('networkidle')
                print("Back on account page")

                if not file_success:
                    print("File upload failed. Retrying...")
                    if current_try < max_tries:
                        print(f"Retrying upload... (Attempt {current_try + 1} of {max_tries})")
                        current_try += 1
                        continue
                    else:
                        print("Maximum retry attempts reached. Upload may be incomplete.")
                        upload_success = False
                        if not input("Do you want to try again? (y/n): ").lower().startswith('y'):
                            print("Stopping as requested.")
                            sys.exit(0)
        
        return upload_success

def main():
    # Enable debug mode
    debug_mode = True
    max_tries = 3  # Number of retry attempts per file
    logging.basicConfig(level=logging.INFO)
    
    # Get mock account data
    mock_accounts = get_mock_accounts()
    test_account = mock_accounts[0]  # Use John Smith's account for testing
    
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
        
        # Verify we're on the correct account page
        if not verify_account_page_url(page):
            print("Please navigate to the account page first.")
            sys.exit(1)
        
        # Initialize Salesforce page objects
        accounts_page = AccountsPage(page, debug_mode=debug_mode)
        
        # Upload files for the account
        upload_success = upload_files_for_account(page, test_account, debug_mode=debug_mode, max_tries=max_tries)
        
        if not upload_success:
            print("File upload process completed with errors")
            sys.exit(1)

if __name__ == "__main__":
    main() 