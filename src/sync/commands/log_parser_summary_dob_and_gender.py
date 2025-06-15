import os
import sys
import json
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import argparse
from dotenv import load_dotenv
from supabase_client.client import SupabaseClient
from sync.commands.check_docker import ensure_docker_and_supabase
from sync.cmd_runner import setup_logging, format_args_for_logging
from pydantic import BaseModel

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

def parse_log_file(file_path: str, logger, report_logger) -> Dict[str, Dict]:
    """
    Parse the log file and extract information about applications and their DOB/gender.
    """
    # logger.info(f"\nParsing log file: {file_path}")
    report_logger.info(f"\nParsing log file: {file_path}")
    
    parsed_data = {}
    current_folder = None
    
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # Check if this is a folder line
                if line.startswith('Dropbox Account Folder:'):
                    current_folder = line.replace('Dropbox Account Folder:', '').strip()
                    if current_folder not in parsed_data:
                        parsed_data[current_folder] = {
                            'applications': [],
                            'no_applications_found': False
                        }
                    # logger.info(f"\nProcessing folder: {current_folder}")
                    report_logger.info(f"\nProcessing folder: {current_folder}")
                    continue
                
                # Check if this is a "no applications found" line
                if line.startswith('❌ No application files found for'):
                    if current_folder:
                        parsed_data[current_folder]['no_applications_found'] = True
                        # logger.info(f"No applications found for {current_folder}")
                        report_logger.info(f"No applications found for {current_folder}")
                    continue
                
                # Check if this is an application line
                if line.startswith('✅🎂'):
                    if not current_folder:
                        # logger.warning(f"Found application line without a folder: {line}")
                        report_logger.warning(f"Found application line without a folder: {line}")
                        continue
                    
                    # Extract file name and DOB/gender
                    try:
                        # Remove the emoji prefix
                        line = line.replace('✅🎂', '').strip()
                        
                        # Split into file name and DOB/gender
                        parts = line.split('[')
                        if len(parts) != 2:
                            # logger.warning(f"Invalid application line format: {line}")
                            report_logger.warning(f"Invalid application line format: {line}")
                            continue
                        
                        file_name = parts[0].strip()
                        dob_gender = parts[1].replace(']', '').strip()
                        
                        # Split DOB and gender
                        dob_gender_parts = dob_gender.split(',')
                        if len(dob_gender_parts) != 2:
                            # logger.warning(f"Invalid DOB/gender format: {dob_gender}")
                            report_logger.warning(f"Invalid DOB/gender format: {dob_gender}")
                            continue
                        
                        dob_str = dob_gender_parts[0].strip()
                        gender_str = dob_gender_parts[1].strip()
                        
                        # Parse DOB
                        try:
                            # Try different date formats
                            date_formats = [
                                '%m/%d/%Y',  # MM/DD/YYYY
                                '%Y-%m-%d',  # YYYY-MM-DD
                                '%d/%m/%y',  # DD/MM/YY
                                '%m/%d/%y',  # MM/DD/YY
                                '%d/%m/%Y',  # DD/MM/YYYY
                                '%m/%d/%Y'   # M/D/YYYY
                            ]
                            
                            dob = None
                            for date_format in date_formats:
                                try:
                                    dob = datetime.strptime(dob_str, date_format)
                                    break
                                except ValueError:
                                    continue
                            
                            if not dob:
                                # logger.warning(f"Invalid date format: {dob_str}")
                                report_logger.warning(f"Invalid date format: {dob_str}")
                                continue
                            
                        except Exception as e:
                            # logger.warning(f"Error parsing date {dob_str}: {str(e)}")
                            report_logger.warning(f"Error parsing date {dob_str}: {str(e)}")
                            continue
                        
                        # Extract gender
                        gender = None
                        if '☑️ 👩' in gender_str and 'F' in gender_str:
                            gender = 'Female'
                        elif '☑️ 👨' in gender_str and 'M' in gender_str:
                            gender = 'Male'
                        elif '❌ F/M' in gender_str:
                            gender = 'Unknown'
                        
                        if not gender:
                            # logger.warning(f"Could not determine gender from: {gender_str}")
                            report_logger.warning(f"Could not determine gender from: {gender_str}")
                            continue
                        
                        # Add to parsed data
                        parsed_data[current_folder]['applications'].append({
                            'file_name': file_name,
                            'birthdate': dob,
                            'gender': gender
                        })
                        
                        # logger.info(f"Parsed application: {file_name}")
                        # logger.info(f"DOB: {dob}")
                        # logger.info(f"Gender: {gender}")
                        report_logger.info(f"Parsed application: {file_name}")
                        report_logger.info(f"DOB: {dob}")
                        report_logger.info(f"Gender: {gender}")
                        
                    except Exception as e:
                        # logger.error(f"Error parsing application line: {line}")
                        # logger.error(f"Error details: {str(e)}")
                        report_logger.error(f"Error parsing application line: {line}")
                        report_logger.error(f"Error details: {str(e)}")
                        continue
        
        # Log summary of parsed data
        # logger.info("\nParsing complete. Summary:")
        report_logger.info("\nParsing complete. Summary:")
        for folder, data in parsed_data.items():
            # logger.info(f"\nFolder: {folder}")
            # logger.info(f"Number of applications: {len(data['applications'])}")
            # logger.info(f"No applications found: {data['no_applications_found']}")
            report_logger.info(f"\nFolder: {folder}")
            report_logger.info(f"Number of applications: {len(data['applications'])}")
            report_logger.info(f"No applications found: {data['no_applications_found']}")
        
        return parsed_data
        
    except Exception as e:
        # logger.error(f"Error parsing log file: {str(e)}")
        report_logger.error(f"Error parsing log file: {str(e)}")
        raise

def generate_database_summary(supabase: SupabaseClient, logger, report_logger) -> None:
    """
    Generate a summary of the database contents and write it to summary.log
    """
    logger.info("\nGenerating database summary...")
    report_logger.info("\nGenerating database summary...")
    
    try:
        # Get all dropbox accounts
        accounts_result = supabase.client.table('dropbox_accounts').select('*').execute()
        accounts = accounts_result.data
        # logger.info(f"Found {len(accounts)} dropbox accounts")
        report_logger.info(f"Found {len(accounts)} dropbox accounts")
        
        # Debug log first few accounts
        if accounts:
            # logger.info(f"First account: {accounts[0]}")
            report_logger.info(f"First account: {accounts[0]}")
        
        # Get all applications
        applications_result = supabase.client.table('applications').select('*').execute()
        applications = applications_result.data
        # logger.info(f"Found {len(applications)} applications")
        report_logger.info(f"Found {len(applications)} applications")
        
        # Debug log first few applications
        if applications:
            # logger.info(f"First application: {applications[0]}")
            report_logger.info(f"First application: {applications[0]}")
        
        # Group applications by dropbox account
        account_applications = {}
        for app in applications:
            account_id = app.get('dropbox_account_id')
            if account_id:
                if account_id not in account_applications:
                    account_applications[account_id] = []
                account_applications[account_id].append(app)
        
        # logger.info(f"Grouped applications into {len(account_applications)} accounts")
        report_logger.info(f"Grouped applications into {len(account_applications)} accounts")
        
        # Debug log first few grouped applications
        if account_applications:
            first_account_id = next(iter(account_applications))
            # logger.info(f"First account's applications: {account_applications[first_account_id]}")
            report_logger.info(f"First account's applications: {account_applications[first_account_id]}")
        
        # Write summary to file
        summary_path = os.path.join(os.path.dirname(__file__), 'summary.log')
        with open(summary_path, 'w') as f:
            f.write("Database Summary\n")
            f.write("================\n\n")
            
            f.write(f"Total Dropbox Accounts: {len(accounts)}\n")
            f.write(f"Total Applications: {len(applications)}\n\n")
            
            for account in accounts:
                folder = account['folder']
                account_id = account['id']
                apps = account_applications.get(account_id, [])
                
                f.write(f"Dropbox Account Folder: {folder}\n")
                if not apps:
                    f.write(f"  ❌ No application files found for {folder}\n")
                else:
                    for app in apps:
                        # Format date as MM/DD/YYYY
                        dob_str = app['birthdate'].strftime('%m/%d/%Y') if app.get('birthdate') else 'N/A'
                        # Get gender emoji
                        gender_emoji = '👩' if app.get('gender') == 'Female' else '👨' if app.get('gender') == 'Male' else ''
                        gender_str = app.get('gender', 'Unknown')
                        f.write(f"  ✅🎂 {app['file_name']} [{dob_str}, ☑️ {gender_emoji} {gender_str}]\n")
                f.write("\n")
        
        # logger.info(f"Summary written to {summary_path}")
        report_logger.info(f"Summary written to {summary_path}")
        
    except Exception as e:
        logger.error(f"Error generating database summary: {str(e)}")
        report_logger.error(f"Error generating database summary: {str(e)}")
        raise

class DropboxAccount(BaseModel):
    folder: str
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None

def store_in_supabase(parsed_data: Dict[str, Dict], folder: str, logger, report_logger) -> None:
    """
    Store the parsed data in Supabase.
    """
    # logger.info("\nStarting to store data in Supabase...")
    report_logger.info("\nStarting to store data in Supabase...")
    
    try:
        # Initialize Supabase client
        supabase = SupabaseClient()
        
        # Process each folder in the parsed data
        for i, (folder_name, folder_data) in enumerate(parsed_data.items(), 1):
            # logger.info(f"\n[{i}/{len(parsed_data)}] storing data for folder: {folder_name}")
            report_logger.info(f"\n[{i}/{len(parsed_data)}] storing data for folder: {folder_name}")
            
            applications = folder_data['applications']
            no_applications_found = folder_data['no_applications_found']
            
            report_logger.info(f"Number of applications: {len(applications)}")
            report_logger.info(f"No applications found: {no_applications_found}")
            
            # Create an account even if no applications are found
            try:
                # Create account with only required fields
                account = DropboxAccount(
                    folder=folder_name,
                    first_name=None,
                    middle_name=None,
                    last_name=None
                )
                # Store account and get the result
                account_result = supabase.client.table('dropbox_accounts').insert(account.model_dump()).execute()
                if not account_result.data:
                    raise RuntimeError("Failed to create dropbox account")
                account_id = account_result.data[0]['id']
                # logger.info(f"Created account with ID: {account_id}")
                report_logger.info(f"Created account with ID: {account_id}")
                
                # If no applications were found, log it and continue to next folder
                if no_applications_found:
                    # logger.warning(f"No applications found for {folder_name}")
                    report_logger.warning(f"No applications found for {folder_name}")
                    continue
                
                # Process applications if any exist
                for app in applications:
                    report_logger.info(f"\nProcessing application: {app['file_name']}")
                    report_logger.info(f"Birthdate: {app['birthdate']}")
                    report_logger.info(f"Gender: {app['gender']}")
                    
                    # Convert birthdate to ISO format string
                    birthdate_str = app['birthdate'].isoformat() if app['birthdate'] else None
                    
                    # Create application with only required fields
                    application = Application(
                        file_name=app['file_name'],
                        first_name=None,
                        last_name=None,
                        birthdate=birthdate_str,  # Use the ISO format string
                        gender=app['gender'],
                        address=None,
                        application_type="Insurance",
                        status="Pending",
                        dropbox_account_id=account_id  # Set the dropbox_account_id here
                    )
                    
                    # Debug log the application data
                    app_data = application.model_dump()
                    report_logger.info(f"Application data to be inserted: {app_data}")
                    
                    # Store application and get the result
                    app_result = supabase.client.table('applications').insert(app_data).execute()
                    if not app_result.data:
                        raise RuntimeError("Failed to create application")
                    application_id = app_result.data[0]['id']
                    report_logger.info(f"Created application with ID: {application_id}")
                    report_logger.info(f"Created application with ID: {application_id}")
                
            except Exception as e:
                logger.error(f"Error processing folder {folder_name}: {str(e)}")
                report_logger.error(f"Error processing folder {folder_name}: {str(e)}")
                continue
        
        report_logger.info("\nSuccessfully stored all data in Supabase")
        # report_logger.info("\nSuccessfully stored all data in Supabase")
        
        # Generate database summary
        generate_database_summary(supabase, logger, report_logger)
        
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
    logger.info("This tool will parse a log file and store the information in Supabase.")
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
    parsed_data = parse_log_file(log_file_path, logger, report_logger)
    
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
        # logger.info("Operation cancelled by user")
        report_logger.info("Operation cancelled by user")
        return

    # logger.info("\nStoring data in Supabase...")
    report_logger.info("\nStoring data in Supabase...")
    store_in_supabase(parsed_data, folder, logger, report_logger)
    # logger.info("Data successfully stored in Supabase!")
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