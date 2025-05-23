import os
import sys
import logging
from playwright.sync_api import sync_playwright
from dropbox_renamer.utils.dropbox_utils import DropboxClient
from salesforce.browser import get_salesforce_page
from salesforce.pages.account_manager import AccountManager
from dropbox.exceptions import ApiError
from dotenv import load_dotenv
from dropbox_renamer.utils.path_utils import clean_dropbox_path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ping_services.log"),
        logging.StreamHandler()
    ]
)

def get_DROPBOX_FOLDER(env_file='.env'):
    """Get the Dropbox root folder from environment or prompt user."""
    # Load environment variables
    load_dotenv(env_file)
    
    # Try to get root folder from environment
    root_folder = os.getenv('DROPBOX_FOLDER')
    
    # If no root folder found, prompt user
    if not root_folder:
        print("\nDropbox Root Folder not found in .env file.")
        print("Please enter the Dropbox folder path to process (e.g., /Customers or full Dropbox URL):")
        root_folder = input().strip()
        
        if not root_folder:
            print("Error: No folder path provided")
            return get_DROPBOX_FOLDER(env_file)
        
        # Update .env file with the new root folder
        update_env_file(env_file, root_folder=root_folder)
    
    return root_folder

def update_env_file(env_file, root_folder=None):
    """Update the .env file with the new root folder."""
    try:
        # Read existing content
        existing_content = {}
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        existing_content[key] = value
        
        # Update values
        if root_folder:
            existing_content['DROPBOX_FOLDER'] = root_folder
        
        # Write back to file
        with open(env_file, 'w') as f:
            for key, value in existing_content.items():
                f.write(f"{key}={value}\n")
        
        if root_folder:
            print(f"✓ Root folder saved to {env_file}")
    except Exception as e:
        print(f"✗ Error saving to {env_file}: {e}")
        raise

def ping_dropbox(token: str) -> bool:
    """Ping Dropbox service to verify connectivity."""
    try:
        # Get the Dropbox folder path
        dropbox_path = get_DROPBOX_FOLDER()
        
        # Clean and format the path
        dropbox_path = clean_dropbox_path(dropbox_path)
        
        # Initialize Dropbox client
        dbx = DropboxClient(token, debug_mode=False)
        
        # Test account connection
        account = dbx.dbx.users_get_current_account()
        logging.info(f"Successfully connected to Dropbox as: {account.name.display_name}")
        logging.info(f"Account ID: {account.account_id}")
        logging.info(f"Email: {account.email}")
        
        # Test folder access
        try:
            metadata = dbx.dbx.files_get_metadata(dropbox_path)
            logging.info(f"Successfully accessed Dropbox folder: {dropbox_path}")
            logging.info(f"Folder type: {type(metadata).__name__}")
            return True
        except ApiError as e:
            logging.error(f"Error accessing Dropbox folder: {e}")
            return False
            
    except ApiError as e:
        logging.error(f"Error connecting to Dropbox: {e}")
        return False
    except Exception as e:
        logging.error(f"Failed to ping Dropbox: {str(e)}")
        return False

def ping_salesforce(page) -> bool:
    """Ping Salesforce CRM to verify connectivity."""
    try:
        account_manager = AccountManager(page, debug_mode=False)
        # Try to navigate to accounts page as a connectivity test
        if account_manager.navigate_to_accounts_list_page():
            logging.info("Successfully pinged Salesforce CRM")
            return True
        return False
    except Exception as e:
        logging.error(f"Failed to ping Salesforce CRM: {str(e)}")
        return False

def main():
    """Main function to ping both services."""
    # Get Dropbox token from environment
    token = os.getenv('DROPBOX_TOKEN')
    if not token:
        logging.error("DROPBOX_TOKEN environment variable is not set")
        sys.exit(1)

    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            # Ping both services
            dropbox_status = ping_dropbox(token)
            salesforce_status = ping_salesforce(page)

            # Log overall status
            if dropbox_status and salesforce_status:
                logging.info("All services are up and running")
                sys.exit(0)
            else:
                logging.error("One or more services are down")
                sys.exit(1)

        except Exception as e:
            logging.error(f"Error in main execution: {str(e)}")
            sys.exit(1)
        finally:
            if 'browser' in locals():
                browser.close()

if __name__ == "__main__":
    main() 