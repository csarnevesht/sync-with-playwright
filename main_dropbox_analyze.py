import os
from dotenv import load_dotenv
from sync.dropbox_client import DropboxClient
import logging
from dropbox.exceptions import ApiError
from dropbox_renamer.utils.path_utils import clean_dropbox_path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dropbox_analyze.log'),
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

def main():
    # Load environment variables
    load_dotenv()
    
    # Get Dropbox token from environment variable
    dropbox_token = os.getenv('DROPBOX_TOKEN')
    if not dropbox_token:
        logging.error("DROPBOX_TOKEN environment variable not found")
        return
    
    try:
        # Get and clean the Dropbox folder path
        dropbox_path = get_DROPBOX_FOLDER()
        dropbox_path = clean_dropbox_path(dropbox_path)
        logging.info(f"Testing path: {dropbox_path}")
        
        # Initialize Dropbox client
        client = DropboxClient(token=dropbox_token, debug_mode=True)
        logging.info("Successfully connected to Dropbox")
        
        # Test account connection
        account = client.dbx.users_get_current_account()
        logging.info(f"Connected as: {account.name.display_name}")
        logging.info(f"Account ID: {account.account_id}")
        logging.info(f"Email: {account.email}")
        
        # Test folder access
        try:
            metadata = client.dbx.files_get_metadata(dropbox_path)
            logging.info(f"Successfully accessed Dropbox folder: {dropbox_path}")
            logging.info(f"Folder type: {type(metadata).__name__}")
            
            # Get list of account folders
            account_folders = client.get_account_folders()
            
            # Print results
            logging.info(f"Found {len(account_folders)} account folders:")
            for folder in account_folders:
                logging.info(f"- {folder}")
                
        except ApiError as e:
            logging.error(f"Error accessing Dropbox folder: {e}")
            
    except Exception as e:
        logging.error(f"Error: {e}")

if __name__ == "__main__":
    main() 