import os
import sys
import json
import logging
import re
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import argparse
from dotenv import load_dotenv
from supabase_client.client import SupabaseClient
from sync.commands.check_docker import ensure_docker_and_supabase
from sync.cmd_runner import setup_logging, format_args_for_logging
from pydantic import BaseModel
from supabase import create_client

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

def generate_database_summary(supabase, logger, report_logger, summary_logger) -> None:
    """
    Generate a summary of the database contents and log it using summary_logger
    """
    logger.info("\nGenerating database summary...")
    report_logger.info("\nGenerating database summary...")
    summary_logger.info("Database Summary\n================\n")
    try:
        # Get all dropbox accounts with their applications
        accounts_result = supabase.table('dropbox_accounts').select('*, applications(*)').execute()
        accounts = accounts_result.data
        report_logger.info(f"Found {len(accounts)} dropbox accounts")
        summary_logger.info(f"Total Dropbox Accounts: {len(accounts)}")
        
        # Debug log first few accounts
        if accounts:
            report_logger.info(f"First account: {accounts[0]}")
        
        # Log summary for each account
        for account in accounts:
            folder = account['folder']
            apps = account.get('applications', [])
            
            summary_logger.info(f"Dropbox Account Folder: {folder}")
            if not apps:
                summary_logger.info(f"  ❌ No application files found for {folder}")
            else:
                for app in apps:
                    # Format date as MM/DD/YYYY
                    birthdate = app.get('birthdate')
                    if birthdate:
                        try:
                            # Parse ISO format string to datetime
                            from datetime import datetime
                            dob = datetime.fromisoformat(birthdate)
                            dob_str = dob.strftime('%m/%d/%Y')
                        except (ValueError, TypeError):
                            dob_str = birthdate  # Use raw string if parsing fails
                    else:
                        dob_str = 'N/A'
                    
                    # Get gender emoji
                    gender_emoji = '👩' if app.get('gender') == 'Female' else '👨' if app.get('gender') == 'Male' else ''
                    gender_str = app.get('gender', 'Unknown')
                    summary_logger.info(f"  ✅🎂 {app['file_name']} [{dob_str}, ☑️ {gender_emoji} {gender_str}]")
            summary_logger.info("")
        
        report_logger.info(f"Summary logged using summary_logger")
        
    except Exception as e:
        logger.error(f"Error generating database summary: {str(e)}")
        report_logger.error(f"Error generating database summary: {str(e)}")
        raise

class DropboxAccount(BaseModel):
    folder: str
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    applications: List[Application] = []
    no_applications_found: bool = False
    household_head: Optional[str] = None
    household_members: List[str] = []

    model_config = {
        'json_encoders': {
            date: lambda v: v.isoformat() if v else None
        }
    }

def store_in_supabase(parsed_data: Dict[str, Any], folder: str, logger: logging.Logger, report_logger: logging.Logger) -> None:
    """
    Store the parsed data in Supabase.
    
    Args:
        parsed_data: Dictionary containing parsed data
        folder: The folder name to store data for
        logger: Logger for general logging
        report_logger: Logger for report logging
    """
    # Get Supabase credentials
    url, key = get_supabase_credentials()
    supabase = create_client(url, key)
    
    # Get data for this folder
    folder_data = parsed_data.get(folder)
    if not folder_data:
        logger.warning(f"No data found for folder: {folder}")
        report_logger.info(f"No data found for folder: {folder}")
        return
    
    # Create dropbox account data
    account_data = {
        "folder": folder,
        "first_name": "Unknown",
        "middle_name": "Unknown",
        "last_name": "Unknown"
    }
    
    # Insert dropbox account
    try:
        result = supabase.table("dropbox_accounts").insert(account_data).execute()
        if not result.data:
            logger.error(f"Failed to insert dropbox account for folder: {folder}")
            report_logger.info(f"Failed to insert dropbox account for folder: {folder}")
            return
            
        dropbox_account_id = result.data[0]["id"]
        logger.info(f"Successfully inserted dropbox account for folder: {folder}")
        report_logger.info(f"Successfully inserted dropbox account for folder: {folder}")
        
        # Insert applications if any
        if not folder_data["no_applications_found"] and folder_data["applications"]:
            applications = []
            for app in folder_data["applications"]:
                # Convert birthdate to ISO format string if it exists
                birthdate = app.get("birthdate")
                if birthdate and hasattr(birthdate, "isoformat"):
                    birthdate = birthdate.isoformat()
                
                application_data = {
                    "dropbox_account_id": dropbox_account_id,
                    "file_name": app["file_name"],
                    "first_name": "Unknown",
                    "last_name": "Unknown",
                    "address": "Unknown",
                    "application_type": "Unknown",
                    "status": "Unknown",
                    "birthdate": birthdate,
                    "gender": app.get("gender")
                }
                applications.append(application_data)
            
            if applications:
                result = supabase.table("applications").insert(applications).execute()
                if result.data:
                    logger.info(f"Successfully inserted {len(applications)} applications for folder: {folder}")
                    report_logger.info(f"Successfully inserted {len(applications)} applications for folder: {folder}")
                else:
                    logger.error(f"Failed to insert applications for folder: {folder}")
                    report_logger.info(f"Failed to insert applications for folder: {folder}")
        
    except Exception as e:
        logger.error(f"Error storing data in Supabase: {str(e)}")
        report_logger.info(f"Error storing data in Supabase: {str(e)}")

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
        report_logger.info("Operation cancelled by user")
        return

    report_logger.info("\nStoring data in Supabase...")
    # Store data for each folder in parsed_data
    for folder_name, folder_data in parsed_data.items():
        store_in_supabase(parsed_data, folder_name, logger, report_logger)
    report_logger.info("Data successfully stored in Supabase!")

    # Generate and write database summary
    supabase = create_client(url, key)
    generate_database_summary(supabase, logger, report_logger, summary_logger)

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