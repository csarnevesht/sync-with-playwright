import os
import sys
from playwright.sync_api import sync_playwright
import logging
from salesforce.pages.account_manager import AccountManager
from salesforce.pages.file_manager import FileManager
from get_salesforce_page import get_salesforce_page

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_file_type(file_name: str) -> str:
    """Extract file type from the file name."""
    # Common file extensions to look for
    extensions = {
        'pdf': 'PDF',
        'xlsx': 'Excel',
        'xls': 'Excel',
        'doc': 'Word',
        'docx': 'Word',
        'txt': 'Text',
        'csv': 'CSV',
        'jpg': 'Image',
        'jpeg': 'Image',
        'png': 'Image',
        'gif': 'Image'
    }
    
    # Look for file extension in the name
    for ext, file_type in extensions.items():
        if file_name.lower().endswith(f'.{ext}'):
            return file_type
    
    # If no extension found, check for common patterns
    if 'pdf' in file_name.lower():
        return 'PDF'
    elif 'excel' in file_name.lower():
        return 'Excel'
    elif 'word' in file_name.lower() or 'doc' in file_name.lower():
        return 'Word'
    
    return 'Unknown'

def format_file_name(file_name: str) -> tuple[str, str]:
    """Format the file name by separating 'Adobe PDF' from the rest of the name and get file type."""
    if file_name.startswith('Adobe PDF'):
        # Remove 'Adobe PDF' and any leading/trailing whitespace
        cleaned_name = file_name[9:].strip()
    else:
        cleaned_name = file_name.strip()
    
    file_type = get_file_type(file_name)
    return cleaned_name, file_type

def test_account_account_files():
    """Test searching for Beth Albert's account and getting its files."""
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            # Initialize managers
            account_manager = AccountManager(page, debug_mode=True)
            file_manager = FileManager(page, debug_mode=True)
            
            # Navigate to Accounts page
            assert account_manager.navigate_to_accounts_list_page(), "Failed to navigate to Accounts page"
            
            # Search for Beth Albert's account
            account_name = "Beth Albert"
            if not account_manager.account_exists(account_name):
                logging.error(f"Account {account_name} does not exist")
                return
            
            # Click on the account name to navigate to it
            if not account_manager.click_account_name(account_name):
                logging.error(f"Failed to navigate to account view page for: {account_name}")
                return
            
            # Verify we're on the correct account page
            is_valid, account_id = account_manager.verify_account_page_url()
            if not is_valid:
                logging.error("Not on a valid account page")
                return
            
            logging.info(f"Successfully navigated to account {account_name} with ID {account_id}")
            
            # Navigate to Files and get count
            num_files = account_manager.navigate_to_files_and_get_number_of_files_for_this_account(account_id)
            if num_files == -1:
                logging.error("Failed to navigate to Files")
                return
            
            logging.info(f"Number of files found: {num_files}")
            
            # Get list of file names
            file_list = page.locator('a[href*="/ContentDocument/"]').all()
            file_names = []
            file_types = {}  # Dictionary to count file types
            
            for file_link in file_list:
                try:
                    file_name = file_link.text_content()
                    if file_name:
                        file_names.append(file_name)
                except Exception as e:
                    logging.warning(f"Error getting file name: {str(e)}")
                    continue
            
            logging.info(f"Found {len(file_names)} files:")
            for name in file_names:
                formatted_name, file_type = format_file_name(name)
                logging.info(f"- [{file_type}] {formatted_name}")
                # Count file types
                file_types[file_type] = file_types.get(file_type, 0) + 1
            
            # Verify we got the expected number of files
            if isinstance(num_files, str):
                # If we have "50+" files, we can't verify exact count
                assert num_files == "50+" or len(file_names) >= 50, f"Expected at least 50 files, got {len(file_names)}"
            else:
                assert len(file_names) == num_files, f"Expected {num_files} files, got {len(file_names)}"
            
            # Print summary at the end
            logging.info("\n=== Summary ===")
            logging.info(f"Total number of files found: {len(file_names)}")
            if isinstance(num_files, str):
                logging.info(f"Salesforce reported: {num_files} files")
            else:
                logging.info(f"Salesforce reported: {num_files} files")
            
            # Print file type breakdown
            logging.info("\nFile type breakdown:")
            for file_type, count in sorted(file_types.items()):
                logging.info(f"- {file_type}: {count} files")
            logging.info("==============\n")
            
            logging.info("Test completed successfully")
            
        except Exception as e:
            logging.error(f"Test failed: {str(e)}")
            page.screenshot(path="test-failure.png")
            raise
        finally:
            browser.close()

def main():
    test_account_account_files()

if __name__ == "__main__":
    main() 