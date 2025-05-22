import os
import sys
from playwright.sync_api import sync_playwright, expect
import logging
from salesforce.pages.account_manager import AccountManager
from salesforce.pages.accounts_page import AccountsPage
import pytest
from get_salesforce_page import get_salesforce_page
from salesforce.pages.file_manager import FileManager
import time
from mock_data import get_mock_accounts
from file_upload import upload_files_for_account

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def incremental_scroll_until_all_files_loaded(page, max_attempts=20, wait_time=0.3):
    """
    Incrementally scrolls the file list container until no new file links appear.
    Returns the set of unique file hrefs (filtered for /ContentDocument/).
    """
    unique_file_hrefs = set()
    stable_count = 0
    
    # Wait for the file list container to be visible and get its height
    file_list = page.locator('div.slds-card__body table, div.slds-scrollable_y table, div[role="main"] table').first
    file_list.wait_for(state="visible")
    
    # Get initial file links
    all_links = page.locator('a[href*="/ContentDocument/"]').all()
    for link in all_links:
        href = link.get_attribute('href')
        if href and '/ContentDocument/' in href:
            unique_file_hrefs.add(href)
    
    for attempt in range(max_attempts):
        current_count = len(unique_file_hrefs)
        logging.info(f"Scroll attempt {attempt+1}: found {current_count} unique file links")
        
        # Try multiple scrolling methods
        try:
            # Method 1: Scroll the table container
            file_list.evaluate('el => el.scrollIntoView({block: "end", behavior: "auto"})')
            
            # Method 2: Scroll the parent container
            parent = file_list.locator('xpath=..')
            parent.evaluate('el => el.scrollBy(0, 1000)')
            
            # Method 3: Use keyboard to scroll
            page.keyboard.press('PageDown')
            
        except Exception as e:
            logging.warning(f"Failed to scroll: {str(e)}")
            # Fallback to window scroll
            page.evaluate('window.scrollBy(0, 1000)')
        
        # Wait for any animations and content to load
        time.sleep(wait_time)
        
        # Get new file links after scroll
        all_links = page.locator('a[href*="/ContentDocument/"]').all()
        for link in all_links:
            href = link.get_attribute('href')
            if href and '/ContentDocument/' in href:
                unique_file_hrefs.add(href)
        
        # Check if we found new files
        if len(unique_file_hrefs) == current_count:
            stable_count += 1
            logging.info(f"Count stable for {stable_count} attempts")
        else:
            stable_count = 0
            logging.info(f"Found new files! Total: {len(unique_file_hrefs)}")
        
        if stable_count >= 3:
            logging.info("File count stabilized, stopping scroll.")
            break
    
    return unique_file_hrefs

def test_search_account(account_name: str, expected_files: int = 74):
    """Test searching for an account by name and checking its files."""
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            account_manager = AccountManager(page, debug_mode=True)
            file_manager = FileManager(page, debug_mode=True)
            
            # Navigate to accounts page
            if not account_manager.navigate_to_accounts_list_page():
                logging.error("Failed to navigate to accounts page")
                return
            
            # Ensure the account exists (create if not)
            just_created = False
            if not account_manager.account_exists(account_name):
                logging.info(f"Account {account_name} does not exist, creating it...")
                # Use mock data for creation
                mock_accounts = get_mock_accounts()
                mock = next((a for a in mock_accounts if f"{a['first_name']} {a['last_name']}" == account_name), None)
                if not mock:
                    logging.error(f"No mock data found for {account_name}")
                    return
                created = account_manager.create_new_account(
                    first_name=mock['first_name'],
                    last_name=mock['last_name'],
                    middle_name=mock.get('middle_name'),
                    account_info=mock.get('account_info', {})
                )
                assert created, f"Failed to create account: {account_name}"
                logging.info(f"Account {account_name} created.")
                just_created = True
                # Navigate back to accounts page
                assert account_manager.navigate_to_accounts_list_page(), "Failed to navigate to Accounts page after creation"
            
            # Search for the account
            if not account_manager.account_exists(account_name):
                logging.error(f"Account {account_name} does not exist after creation")
                return
            
            # Click on the account name
            if not account_manager.click_account_name(account_name):
                logging.error(f"Failed to navigate to account view page for: {account_name}")
                return
            
            # Verify we're on the correct account page
            is_valid, account_id = account_manager.verify_account_page_url()
            if not is_valid:
                logging.error("Not on a valid account page")
                return
            
            logging.info(f"Successfully navigated to account {account_name} with ID {account_id}")
            
            # If just created, upload files
            if just_created:
                mock_accounts = get_mock_accounts()
                mock = next((a for a in mock_accounts if f"{a['first_name']} {a['last_name']}" == account_name), None)
                if mock and mock.get('files'):
                    logging.info(f"Uploading files for newly created account: {account_name}")
                    upload_success = upload_files_for_account(page, mock, debug_mode=True)
                    assert upload_success, f"Failed to upload files for account: {account_name}"
            
            # Navigate to files and get count
            logging.info(f"Navigating to files for account {account_name}")
            num_files = account_manager.navigate_to_files_and_get_number_of_files_for_this_account(account_id)
            
            if num_files == -1:
                logging.error("Failed to navigate to files page")
                return
            
            logging.info(f"Final file count: {num_files}")
            assert num_files == expected_files, f"Expected {expected_files} files, but found {num_files}"
            
            # Navigate back to account page
            account_manager.navigate_back_to_account_page()
            
            # Verify we're back on the account page
            is_valid, _ = account_manager.verify_account_page_url()
            assert is_valid, "Failed to navigate back to account page"
            
            logging.info("Test completed successfully")
            
        except Exception as e:
            logging.error(f"Test failed: {str(e)}")
            page.screenshot(path="test-failure.png")
            raise
        finally:
            browser.close()

def main():
    # Use the first mock account with files
    mock_accounts = get_mock_accounts()
    # Find a mock account with files
    account = next((a for a in mock_accounts if a.get('files')), None)
    if not account:
        print("No suitable mock account found for test_search_account.")
        sys.exit(1)
    expected_files = len(account['files'])
    test_search_account(f"{account['first_name']} {account['last_name']}", expected_files=expected_files)

if __name__ == "__main__":
    main() 