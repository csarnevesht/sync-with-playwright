"""
Test Account File Deletion

This test verifies the account file deletion functionality in Salesforce. It:
1. Searches for a specific account using mock data
2. If account doesn't exist, creates it
3. Navigates to the account's files section
4. Deletes the first file found
5. Verifies the deletion was successful
"""

import os
import sys
from playwright.sync_api import sync_playwright
import logging
from salesforce.pages.account_manager import AccountManager
from salesforce.pages.file_manager import FileManager
from get_salesforce_page import get_salesforce_page
from mock_data import get_mock_accounts
from file_upload import upload_files_for_account

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_full_name(account: dict) -> str:
    """
    Get the full name of an account including middle name if present.
    
    Args:
        account: Account dictionary from mock data
        
    Returns:
        str: Full name of the account
    """
    name_parts = [
        account['first_name'],
        account.get('middle_name'),
        account['last_name']
    ]
    return ' '.join(
        part for part in name_parts 
        if part and str(part).strip().lower() not in ['none', '']
    )

def test_account_file_delete():
    """Test deleting a file from a mock account."""
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            # Initialize managers
            account_manager = AccountManager(page, debug_mode=True)
            file_manager = FileManager(page, debug_mode=True)
            
            # Get mock accounts
            mock_accounts = get_mock_accounts()
            if not mock_accounts:
                logging.error("No mock accounts found")
                return
                
            # Use the first mock account
            account = mock_accounts[0]
            account_name = get_full_name(account)
            logging.info(f"Using mock account: {account_name}")
            
            # Navigate to accounts page
            if not account_manager.navigate_to_accounts_list_page():
                logging.error("Failed to navigate to accounts page")
                return
            
            # Check if account exists
            if not account_manager.account_exists(account_name):
                logging.info(f"Account {account_name} does not exist, creating it...")
                # Create new account
                if not account_manager.create_new_account(
                    first_name=account['first_name'],
                    last_name=account['last_name'],
                    middle_name=account.get('middle_name'),
                    account_info=account.get('account_info', {})
                ):
                    logging.error(f"Failed to create account: {account_name}")
                    return
                    
                # Upload files for new account
                logging.info(f"Uploading files for new account: {account_name}")
                upload_success = upload_files_for_account(page, account, debug_mode=True)
                if not upload_success:
                    logging.error(f"Failed to upload files for account: {account_name}")
                    return
            else:
                logging.info(f"Account exists: {account_name}")
            
            # Click on account name to navigate to it
            if not account_manager.click_account_name(account_name):
                logging.error(f"Failed to navigate to account view page for: {account_name}")
                return
            
            # Verify we're on the correct account page and get account ID
            is_valid, account_id = account_manager.verify_account_page_url()
            if not is_valid or not account_id:
                logging.error("Not on a valid account page or could not get account ID")
                return
            
            logging.info(f"Successfully navigated to account {account_name} with ID {account_id}")
            
            # Navigate to files section and get number of files
            num_files = account_manager.navigate_to_files_and_get_number_of_files_for_this_account(account_id)
            if num_files == -1:
                logging.error("Failed to navigate to Files")
                return
            
            logging.info(f"Found {num_files} files in account")
            
            if num_files == 0:
                logging.info("No files found in account to delete")
                return
            
            # Get list of all file names
            file_names = account_manager.get_all_file_names_for_this_account(account_id)
            if not file_names:
                logging.error("Failed to get file names")
                return
            
            logging.info(f"Found {len(file_names)} files:")
            for name in file_names:
                logging.info(f"  {name}")
            
            # Delete the first file
            first_file_name = file_names[0]
            logging.info(f"Attempting to delete first file: {first_file_name}")
            
            if not file_manager.delete_file(first_file_name):
                logging.error(f"Failed to delete file: {first_file_name}")
                return
            
            logging.info(f"Successfully deleted file: {first_file_name}")
            
            # Verify file was deleted by checking the new count
            new_num_files = account_manager.navigate_to_files_and_get_number_of_files_for_this_account(account_id)
            logging.info(f"New file count: {new_num_files}")
            
            if new_num_files >= num_files:
                logging.error("File count did not decrease after deletion")
                return
            
            logging.info("Test completed successfully")
            
        except Exception as e:
            logging.error(f"Test failed: {str(e)}")
            raise
        finally:
            browser.close()

def main():
    """Main function to run the test."""
    test_account_file_delete()

if __name__ == "__main__":
    main() 