import os
import sys
import json
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import argparse
from dotenv import load_dotenv
from supabase_client.client import SupabaseClient
from sync.commands.check_docker import ensure_docker_and_supabase

# Add src to Python path
src_path = str(Path(__file__).parent.parent.parent.parent)
if src_path not in sys.path:
    sys.path.append(src_path)

from supabase_client.schema import Application, DropboxAccount

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Log the current working directory
logger.debug(f"Current working directory: {os.getcwd()}")

# Default Supabase credentials for local development
DEFAULT_URL = "http://localhost:18000"
DEFAULT_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"

def get_user_input(prompt: str, default: str = None) -> str:
    """
    Get user input with an optional default value
    """
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default
    return input(f"{prompt}: ").strip()

def get_supabase_credentials() -> tuple[str, str]:
    """
    Get Supabase credentials from environment or prompt user
    """
    load_dotenv()
    
    url = os.getenv("SUPABASE_URL", DEFAULT_URL)
    key = os.getenv("SUPABASE_KEY", DEFAULT_KEY)
    
    if url == DEFAULT_URL and key == DEFAULT_KEY:
        print("\nUsing default local Supabase credentials:")
        print(f"URL: {url}")
        print(f"Key: {key}")
    else:
        print("\nUsing Supabase credentials from .env file")
    
    return url, key

def get_log_file_path(cli_log_file: str = None) -> str:
    """
    Get log file path from CLI flag or prompt user for log file path and validate it exists
    """
    if cli_log_file:
        logger.debug(f"Checking log file path: {cli_log_file}")
        if os.path.exists(cli_log_file):
            return cli_log_file
        logger.error(f"File not found at {cli_log_file}")
        sys.exit(1)
    while True:
        log_file_path = get_user_input("Enter the path to the log file")
        logger.debug(f"Checking log file path: {log_file_path}")
        if os.path.exists(log_file_path):
            return log_file_path
        logger.error(f"File not found at {log_file_path}")
        retry = get_user_input("Would you like to try again? (y/n)", "y").lower()
        if retry != 'y':
            sys.exit(1)

def parse_log_file(log_file_path: str) -> List[Dict[str, Any]]:
    """
    Parse the log file and extract relevant information
    Returns a list of dictionaries containing the parsed data
    """
    parsed_data = []
    current_folder = None
    current_items = []
    no_applications_found = False

    with open(log_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if line.startswith('Dropbox Account Folder:'):
                if current_folder and current_items:
                    parsed_data.append({
                        'folder': current_folder,
                        'items': current_items,
                        'no_applications_found': no_applications_found
                    })
                current_folder = line.replace('Dropbox Account Folder:', '').strip()
                current_items = []
                no_applications_found = False
            elif current_folder:
                if '❌ No application files found for' in line:
                    no_applications_found = True
                elif '✅🎂' in line:
                    birthdate_match = re.search(r'\[(\d{2}/\d{2}/\d{4})', line)
                    birthdate = birthdate_match.group(1) if birthdate_match else None
                    gender = None
                    if '❌ F/M' in line:
                        gender = 'Unknown'
                    elif '☑️ 👨 M' in line:
                        gender = 'Male'
                    elif '☑️ 👩 F' in line:
                        gender = 'Female'
                    current_items.append({
                        'file_name': line,
                        'birthdate': birthdate,
                        'gender': gender
                    })

    if current_folder and current_items:
        parsed_data.append({
            'folder': current_folder,
            'items': current_items,
            'no_applications_found': no_applications_found
        })

    return parsed_data

def store_in_supabase(parsed_data: List[Dict[str, Any]], folder: str) -> None:
    """
    Store the parsed data in Supabase
    """
    client = SupabaseClient()
    
    for folder_data in parsed_data:
        folder_name = folder_data['folder']
        items = folder_data['items']
        no_applications_found = folder_data['no_applications_found']
        
        # Create a DropboxAccount for this folder
        account = DropboxAccount(
            folder=folder_name,
            first_name="",  # These will be populated from the first application
            middle_name=None,
            last_name="",
            applications=[],
            household_head=None,
            household_members=[]
        )
        
        if not no_applications_found and items:
            # Create applications from parsed items
            for item in items:
                if item.get('birthdate'):
                    try:
                        birthdate = datetime.strptime(item['birthdate'], '%m/%d/%Y').date()
                    except ValueError:
                        birthdate = None
                else:
                    birthdate = None
                    
                # Extract file name from the line
                file_name = item['file_name'].split('[')[0].strip()
                
                application = Application(
                    file_name=file_name,
                    first_name="",  # These will need to be extracted from the file name
                    last_name="",
                    birthdate=birthdate,
                    gender=item.get('gender', ''),
                    address=""
                )
                account.applications.append(application)
            
            # If we have applications, use the first one's name for the account
            if account.applications:
                # TODO: Extract name from file name or application data
                account.first_name = "Unknown"
                account.last_name = "Unknown"
            
            # Store in Supabase
            client.store_dropbox_account(account)

def main() -> None:
    """
    Main function to parse log file and store in Supabase
    """
    # First ensure Docker and Supabase are running
    ensure_docker_and_supabase()
    
    parser = argparse.ArgumentParser(description="Parse a log file and store DOB and gender info in Supabase.")
    parser.add_argument('--log-file', type=str, help='Path to the log file (e.g. ./accounts/accounts-dob-gender.log)')
    args = parser.parse_args()

    print("Welcome to the Log Parser for DOB and Gender Information")
    print("This tool will parse a log file and store the information in Supabase.")
    print("-" * 80)

    # Get Supabase credentials
    url, key = get_supabase_credentials()

    # Get log file path
    log_file_path = get_log_file_path(args.log_file)
    print(f"\nUsing log file: {log_file_path}")

    # Use the directory name of the log file as the folder name
    folder = os.path.dirname(log_file_path)
    print(f"Using folder name: {folder}")

    print("\nParsing log file...")
    parsed_data = parse_log_file(log_file_path)
    
    if not parsed_data:
        print("No valid data found in log file")
        return
    
    print(f"\nFound {len(parsed_data)} entries to process")
    
    # Show preview of data
    print("\nPreview of data to be stored:")
    for i, folder_data in enumerate(parsed_data[:3], 1):
        print(f"\nEntry {i}:")
        print(f"  Folder: {folder_data['folder']}")
        print(f"  No Applications Found: {folder_data['no_applications_found']}")
        if not folder_data['no_applications_found'] and folder_data['items']:
            print(f"  Items: {len(folder_data['items'])}")
            for item in folder_data['items'][:2]:  # Show first 2 items
                print(f"    - {item['file_name']}")
                print(f"      DOB: {item.get('birthdate', 'N/A')}")
                print(f"      Gender: {item.get('gender', 'N/A')}")
    
    if len(parsed_data) > 3:
        print(f"\n... and {len(parsed_data) - 3} more entries")

    # Confirm with user
    confirm = get_user_input("\nWould you like to proceed with storing this data in Supabase? (y/n)", "y").lower()
    if confirm != 'y':
        print("Operation cancelled by user")
        return

    print("\nStoring data in Supabase...")
    store_in_supabase(parsed_data, folder)
    print("Data successfully stored in Supabase!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        sys.exit(1) 