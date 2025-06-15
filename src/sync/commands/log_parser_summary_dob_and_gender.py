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
from sync.cmd_runner import setup_logging, format_args_for_logging

# Add src to Python path
src_path = str(Path(__file__).parent.parent.parent.parent)
if src_path not in sys.path:
    sys.path.append(src_path)

from supabase_client.schema import Application, DropboxAccount

# Path to store the last used log file
LAST_LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), '.last_log_file.json')

def get_last_log_file() -> Optional[str]:
    """Get the last used log file path from storage"""
    try:
        if os.path.exists(LAST_LOG_FILE_PATH):
            with open(LAST_LOG_FILE_PATH, 'r') as f:
                data = json.load(f)
                return data.get('last_log_file')
    except Exception as e:
        logging.warning(f"Error reading last log file: {e}")
    return None

def save_last_log_file(log_file_path: str) -> None:
    """Save the last used log file path to storage"""
    try:
        with open(LAST_LOG_FILE_PATH, 'w') as f:
            json.dump({'last_log_file': log_file_path}, f)
    except Exception as e:
        logging.warning(f"Error saving last log file: {e}")

def get_user_input(prompt: str, default: str = None) -> str:
    """
    Get user input with an optional default value
    """
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default
    return input(f"{prompt}: ").strip()

def get_supabase_credentials():
    """Get Supabase credentials from environment variables"""
    # Load environment variables from .env file
    load_dotenv()
    
    url = os.getenv('SUPABASE_URL', 'http://localhost:8000')
    key = os.getenv('SUPABASE_SERVICE_KEY')
    if not key:
        raise ValueError("SUPABASE_SERVICE_KEY environment variable is required")
    return url, key

def get_log_file_path(cli_log_file: str = None) -> str:
    """
    Get log file path from CLI flag or prompt user for log file path and validate it exists
    """
    if cli_log_file:
        logging.debug(f"Checking log file path: {cli_log_file}")
        if os.path.exists(cli_log_file):
            save_last_log_file(cli_log_file)
            return cli_log_file
        logging.error(f"File not found at {cli_log_file}")
        sys.exit(1)

    # Get the last used log file path
    last_log_file = get_last_log_file()
    
    while True:
        log_file_path = get_user_input("Enter the path to the log file", last_log_file)
        logging.debug(f"Checking log file path: {log_file_path}")
        if os.path.exists(log_file_path):
            save_last_log_file(log_file_path)
            return log_file_path
        logging.error(f"File not found at {log_file_path}")
        retry = get_user_input("Would you like to try again? (y/n)", "y").lower()
        if retry != 'y':
            sys.exit(1)

def parse_log_file(log_file_path: str, report_logger: logging.Logger) -> Dict[str, Dict]:
    """
    Parse the log file to extract DOB and gender information.
    Returns a dictionary with folder names as keys and their data as values.
    """
    parsed_data = {}
    current_folder = None
    current_applications = []
    no_applications_found = False

    try:
        with open(log_file_path, 'r') as file:
            for line in file:
                line = line.strip()
                
                # Check for folder entry
                if line.startswith('Dropbox Account Folder:'):
                    # If we have a previous folder, save its data
                    if current_folder:
                        parsed_data[current_folder] = {
                            'applications': current_applications,
                            'no_applications_found': no_applications_found
                        }
                        # Log to report log for every folder
                        report_logger.info(f"Folder: {current_folder}")
                        if no_applications_found:
                            report_logger.info(f"  No applications found")
                        else:
                            report_logger.info(f"  Applications: {len(current_applications)}")
                    
                    # Start new folder
                    current_folder = line.replace('Dropbox Account Folder:', '').strip()
                    current_applications = []
                    no_applications_found = False
                    logging.info(f"Processing folder: {current_folder}")
                
                # Check for no applications found
                elif line.startswith('❌ No application files found for'):
                    no_applications_found = True
                    logging.warning(f"No applications found for {current_folder}")
                
                # Check for application entry
                elif line.startswith('Application:'):
                    file_name = line.replace('Application:', '').strip()
                    logging.info(f"Found application: {file_name}")
                    current_applications.append({
                        'file_name': file_name,
                        'birthdate': None,
                        'gender': None
                    })
                
                # Check for birthdate entry
                elif line.startswith('Birthdate:'):
                    if current_applications:
                        birthdate_str = line.replace('Birthdate:', '').strip()
                        try:
                            birthdate = datetime.strptime(birthdate_str, '%Y-%m-%d').date()
                            current_applications[-1]['birthdate'] = birthdate
                            logging.info(f"Found birthdate: {birthdate}")
                        except ValueError:
                            logging.warning(f"Invalid birthdate format: {birthdate_str}")
                
                # Check for gender entry
                elif line.startswith('Gender:'):
                    if current_applications:
                        gender = line.replace('Gender:', '').strip()
                        current_applications[-1]['gender'] = gender
                        logging.info(f"Found gender: {gender}")
            
            # Save the last folder's data
            if current_folder:
                parsed_data[current_folder] = {
                    'applications': current_applications,
                    'no_applications_found': no_applications_found
                }
                # Log to report log for the last folder
                report_logger.info(f"Folder: {current_folder}")
                if no_applications_found:
                    report_logger.info(f"  No applications found")
                else:
                    report_logger.info(f"  Applications: {len(current_applications)}")
        
        return parsed_data
    except Exception as e:
        logging.error(f"Error parsing log file: {str(e)}")
        raise

def store_in_supabase(parsed_data: Dict[str, Dict], folder: str, logger, report_logger) -> None:
    """
    Store the parsed data in Supabase.
    """
    logger.info("\nStarting to store data in Supabase...")
    report_logger.info("\nStarting to store data in Supabase...")
    
    try:
        # Initialize Supabase client
        supabase = SupabaseClient()
        
        # Process each folder in the parsed data
        for folder_name, folder_data in parsed_data.items():
            logger.info(f"\nProcessing folder: {folder_name}")
            report_logger.info(f"\nProcessing folder: {folder_name}")
            
            applications = folder_data['applications']
            no_applications_found = folder_data['no_applications_found']
            
            logger.info(f"Number of applications: {len(applications)}")
            logger.info(f"No applications found: {no_applications_found}")
            
            # Create an account even if no applications are found
            try:
                # Create account
                account = DropboxAccount(
                    folder=folder_name,
                    first_name="",  # These will be populated from the first application
                    middle_name=None,
                    last_name="",
                    applications=[],
                    household_head=None,
                    household_members=[]
                )
                account_id = supabase.store_dropbox_account(account)
                logger.info(f"Created account with ID: {account_id}")
                report_logger.info(f"Created account with ID: {account_id}")
                
                # If no applications were found, log it and continue to next folder
                if no_applications_found:
                    logger.warning(f"No applications found for {folder_name}")
                    report_logger.warning(f"No applications found for {folder_name}")
                    continue
                
                # Process applications if any exist
                for app in applications:
                    logger.info(f"\nProcessing application: {app['file_name']}")
                    logger.info(f"Birthdate: {app['birthdate']}")
                    logger.info(f"Gender: {app['gender']}")
                    
                    # Create application
                    application = Application(
                        account_id=account_id,
                        file_name=app['file_name'],
                        birthdate=app['birthdate'],
                        gender=app['gender'],
                        application_type="Insurance",
                        status="Pending"
                    )
                    
                    # Store application
                    application_id = supabase.store_application(application)
                    logger.info(f"Created application with ID: {application_id}")
                    report_logger.info(f"Created application with ID: {application_id}")
                
            except Exception as e:
                logger.error(f"Error processing folder {folder_name}: {str(e)}")
                report_logger.error(f"Error processing folder {folder_name}: {str(e)}")
                continue
        
        logger.info("\nSuccessfully stored all data in Supabase")
        report_logger.info("\nSuccessfully stored all data in Supabase")
        
    except Exception as e:
        logger.error(f"Error storing data in Supabase: {str(e)}")
        report_logger.error(f"Error storing data in Supabase: {str(e)}")
        raise

def main() -> None:
    """
    Main function to parse log file and store in Supabase
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Parse a log file and store DOB and gender info in Supabase.")
    parser.add_argument('--log-file', type=str, help='Path to the log file (e.g. ./accounts/accounts-dob-gender.log)')
    parser.add_argument('--keep-log', action='store_true', help='Keep this log folder')
    args = parser.parse_args()

    # Format command for logging
    command = f"python -m sync.commands.log_parser_summary_dob_and_gender {format_args_for_logging(args)}"

    # Setup logging
    logger, report_logger, summary_logger, red_logger = setup_logging(args, command)

    # First ensure Docker and Supabase are running
    ensure_docker_and_supabase()
    
    logger.info("Welcome to the Log Parser for DOB and Gender Information")
    report_logger.info("Welcome to the Log Parser for DOB and Gender Information")
    logger.info("This tool will parse a log file and store the information in Supabase.")
    report_logger.info("This tool will parse a log file and store the information in Supabase.")
    logger.info("-" * 80)
    report_logger.info("-" * 80)

    # Get Supabase credentials
    url, key = get_supabase_credentials()

    # Get log file path
    log_file_path = get_log_file_path(args.log_file)
    logger.info(f"\nUsing log file: {log_file_path}")
    report_logger.info(f"\nUsing log file: {log_file_path}")

    # Use the directory name of the log file as the folder name
    folder = os.path.dirname(log_file_path)
    logger.info(f"Using folder name: {folder}")
    report_logger.info(f"Using folder name: {folder}")

    logger.info("\nParsing log file...")
    report_logger.info("\nParsing log file...")
    parsed_data = parse_log_file(log_file_path, report_logger)
    
    if not parsed_data:
        logger.warning("No valid data found in log file")
        report_logger.info("No valid data found in log file")
        return
    
    logger.info(f"\nFound {len(parsed_data)} entries to process")
    report_logger.info(f"\nFound {len(parsed_data)} entries to process")
    
    # Show preview of data
    logger.info("\nPreview of data to be stored:")
    # Convert dictionary items to list and take first 3
    preview_items = list(parsed_data.items())[:3]
    for i, (folder_name, folder_data) in enumerate(preview_items, 1):
        logger.info(f"\nEntry {i}:")
        logger.info(f"  Dropbox Account Folder: {folder_name}")
        logger.info(f"  No Applications Found: {folder_data['no_applications_found']}")
        if not folder_data['no_applications_found'] and folder_data['applications']:
            logger.info(f"  Applications: {len(folder_data['applications'])}")
            for application in folder_data['applications'][:2]:  # Show first 2 applications
                logger.info(f"    - {application['file_name']}")
                logger.info(f"      DOB: {application.get('birthdate', 'N/A')}")
                logger.info(f"      Gender: {application.get('gender', 'N/A')}")
                report_logger.info(f"      Gender: {application.get('gender', 'N/A')}")
    
    if len(parsed_data) > 3:
        logger.info(f"\n... and {len(parsed_data) - 3} more entries")
        report_logger.info(f"\n... and {len(parsed_data) - 3} more entries")

    # Confirm with user
    confirm = get_user_input("\nWould you like to proceed with storing this data in Supabase? (y/n)", "y").lower()
    if confirm != 'y':
        logger.info("Operation cancelled by user")
        report_logger.info("Operation cancelled by user")
        return

    logger.info("\nStoring data in Supabase...")
    report_logger.info("\nStoring data in Supabase...")
    store_in_supabase(parsed_data, folder, logger, report_logger)
    logger.info("Data successfully stored in Supabase!")
    report_logger.info("Data successfully stored in Supabase!")

# Setup basic logging for the global scope
logging.basicConfig(level=logging.INFO)
global_logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        global_logger.info("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        global_logger.error(f"\nAn error occurred: {str(e)}")
        sys.exit(1) 