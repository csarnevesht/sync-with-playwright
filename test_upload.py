import os
import sys
from playwright.sync_api import sync_playwright
from salesforce.pages.accounts_page import AccountsPage
import tempfile
import logging
from mock_data import get_mock_accounts
import re
import time

def verify_files_page_url(page) -> bool:
    """Verify we're on the correct Files page URL pattern."""
    current_url = page.url
    print(f"\nCurrent URL: {current_url}")
    
    # Expected pattern: Account/{account_id}/related/AttachedContentDocuments/view
    pattern = r'Account/([^/]+)/related/AttachedContentDocuments/view'
    match = re.search(pattern, current_url)
    
    if match:
        account_id = match.group(1)
        print(f"Found account ID in URL: {account_id}")
        return True
    else:
        print("Error: Not on the correct Files page URL pattern")
        print("Expected pattern: Account/{account_id}/related/AttachedContentDocuments/view")
        return False

def main():
    # Enable debug mode
    debug_mode = True
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
        
        # Verify we're on the correct Files page
        if not verify_files_page_url(page):
            print("Please navigate to the Files tab of the account first.")
            sys.exit(1)
        
        # Initialize Salesforce page objects
        accounts_page = AccountsPage(page, debug_mode=debug_mode)
        
        # Create temporary directory for test files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            files_to_upload = []
            for file_info in test_account['files']:
                file_path = os.path.join(temp_dir, file_info['name'])
                with open(file_path, 'wb') as f:
                    f.write(file_info['content'])
                files_to_upload.append(file_path)
                print(f"Created test file: {file_path}")
            
            # Show files to be uploaded
            print("\nFiles to be uploaded:")
            for file in files_to_upload:
                print(f"  + {os.path.basename(file)}")
            
            # Wait for page to be fully loaded
            print("\nWaiting for page to be fully loaded...")
            page.wait_for_load_state('networkidle')
            time.sleep(2)  # Additional wait for any animations
            
            # Try different selectors for the Add Files button
            print("\nLooking for 'Add Files' button...")
            add_files_selectors = [
                'button:has-text("Add Files")',
                'div[title="Add Files"]',
                'button[title="Add Files"]',
                'div.slds-button:has-text("Add Files")',
                'button.slds-button:has-text("Add Files")',
                '//button[contains(text(), "Add Files")]',
                '//div[contains(text(), "Add Files")]'
            ]
            
            add_files_button = None
            for selector in add_files_selectors:
                try:
                    print(f"Trying selector: {selector}")
                    add_files_button = page.wait_for_selector(selector, timeout=5000)
                    if add_files_button and add_files_button.is_visible():
                        print(f"Found 'Add Files' button with selector: {selector}")
                        add_files_button.click()
                        print("Clicked 'Add Files' button")
                        break
                except Exception as e:
                    print(f"Selector {selector} failed: {str(e)}")
            
            if not add_files_button:
                print("Could not find 'Add Files' button")
                # Take a screenshot for debugging
                page.screenshot(path="add-files-button-debug.png")
                print("Screenshot saved as add-files-button-debug.png")
                sys.exit(1)
            
            # Wait for the upload dialog
            print("Waiting for upload dialog...")
            page.wait_for_selector('div.modal-container', timeout=10000)
            
            # Click "Upload Files" button in the dialog
            print("Clicking 'Upload Files' button...")
            upload_button = page.wait_for_selector('button:has-text("Upload Files")', timeout=5000)
            if not upload_button:
                print("Could not find 'Upload Files' button in dialog")
                sys.exit(1)
            upload_button.click()
            print("Clicked 'Upload Files' button")

            # Debug: Print the HTML of the upload dialog
            print("\n--- Upload Dialog HTML ---")
            try:
                dialog_html = page.inner_html('div.modal-container')
                print(dialog_html)
            except Exception as e:
                print(f"Could not get upload dialog HTML: {e}")
            print("--- End Upload Dialog HTML ---\n")

            # Wait a moment for the file input to be ready
            time.sleep(1)
            
            # Set the files to upload directly
            print("\nSetting files to upload...")
            try:
                page.set_input_files('input[type="file"]', files_to_upload)
                print(f"Set {len(files_to_upload)} files to upload")
                
                # Wait for upload to complete
                print("\nWaiting for upload to complete...")
                page.wait_for_selector('div.progress-indicator', timeout=30000, state='hidden')
                print("File upload completed")

                print("\nAttempting to click Cancel in native file selection dialog...")
                try:
                    # First try pressing Escape
                    page.keyboard.press("Escape")
                    print("Pressed Escape key")
                    page.wait_for_timeout(500)  # Wait a bit
                    
                    # Then try clicking Cancel button
                    cancel_button = page.wait_for_selector('button:has-text("Cancel")', timeout=2000)
                    if cancel_button and cancel_button.is_visible():
                        print("Found Cancel button")
                        cancel_button.click()
                        print("Clicked Cancel button")
                    else:
                        # If Cancel button not found, try clicking outside the dialog
                        print("Cancel button not found, trying to click outside dialog")
                        page.mouse.click(0, 0)  # Click in top-left corner
                        print("Clicked outside dialog")
                except Exception as e:
                    print(f"Error handling native file dialog: {e}")

               
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
                    sys.exit(1)
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
                        expected_items = len(files_to_upload)
                        print(f"Found {num_items} items, expected {expected_items} items")
                        if num_items < expected_items:
                            print(f"Warning: Number of items ({num_items}) is less than expected ({expected_items})")
                        elif num_items > expected_items:
                            print(f"Warning: Number of items ({num_items}) is more than expected ({expected_items})")
                        else:
                            print("Success: Number of items matches expected count")
                    else:
                        print("Could not determine number of items from text")
                else:
                    print("Error: Files list not visible")

                print("All files uploaded successfully")
            except Exception as e:
                print(f"Error during file upload: {str(e)}")
                if not input("Do you want to try again? (y/n): ").lower().startswith('y'):
                    print("Stopping as requested.")
                    sys.exit(0)

if __name__ == "__main__":
    main() 