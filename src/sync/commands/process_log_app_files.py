import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

#!/usr/bin/env python3
"""
Command to process application files from log directories.
This script allows users to select a log directory and process all application files
found in the app_files subdirectory, storing the data in the database.
"""

import os
import json
import logging
import glob
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from project root
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loading environment variables from {env_path}")
else:
    print(f"Warning: .env file not found at {env_path}")

from supabase_client import SupabaseClient
from supabase_client.schema import (
    DropboxAccountWithFiles,
    DropboxAccountApplicationFile,
    DropboxAccountApplicationInfo,
    ApplicationStatus,
    ApplicationType
)
from sync.utils.date_utils import convert_date
# Import DropboxClient directly from the utils module to avoid circular imports
from sync.dropbox_client.utils.dropbox_utils import DropboxClient
from sync.cmd_runner import _store_dropbox_client_list_data_in_database

logger = logging.getLogger(__name__)


def get_log_directories() -> List[str]:
    """Get all log directories sorted by creation time (most recent first)."""
    logs_dir = 'logs'
    if not os.path.exists(logs_dir):
        return []
    
    log_dirs = [d for d in os.listdir(logs_dir) if os.path.isdir(os.path.join(logs_dir, d))]
    if not log_dirs:
        return []
    
    # Sort by creation time (most recent first)
    log_dirs.sort(key=lambda x: os.path.getctime(os.path.join(logs_dir, x)), reverse=True)
    return log_dirs


def select_log_directory() -> Optional[str]:
    """Interactive log directory selection."""
    log_dirs = get_log_directories()
    
    if not log_dirs:
        print("❌ No log directories found in 'logs' folder")
        return None
    
    print("\n📁 Available Log Directories:")
    print("=" * 60)
    
    for i, log_dir in enumerate(log_dirs, 1):
        # Get creation time for display
        full_path = os.path.join('logs', log_dir)
        creation_time = datetime.fromtimestamp(os.path.getctime(full_path))
        time_str = creation_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Check if app_files directory exists
        app_files_path = os.path.join(full_path, 'app_files')
        has_app_files = os.path.exists(app_files_path)
        app_files_indicator = "📄" if has_app_files else "❌"
        
        print(f"{i:2d}. {app_files_indicator} {log_dir} ({time_str})")
    
    print("=" * 60)
    print("Use ↑/↓ arrows to navigate, Enter to select, 'q' to quit")
    
    selected_index = 0
    while True:
        # Clear screen and show current selection
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("\n📁 Available Log Directories:")
        print("=" * 60)
        
        for i, log_dir in enumerate(log_dirs):
            full_path = os.path.join('logs', log_dir)
            creation_time = datetime.fromtimestamp(os.path.getctime(full_path))
            time_str = creation_time.strftime('%Y-%m-%d %H:%M:%S')
            
            app_files_path = os.path.join(full_path, 'app_files')
            has_app_files = os.path.exists(app_files_path)
            app_files_indicator = "📄" if has_app_files else "❌"
            
            # Highlight current selection
            if i == selected_index:
                print(f"  > {i+1:2d}. {app_files_indicator} {log_dir} ({time_str})")
            else:
                print(f"    {i+1:2d}. {app_files_indicator} {log_dir} ({time_str})")
        
        print("=" * 60)
        print("Use ↑/↓ arrows to navigate, Enter to select, 'q' to quit")
        
        # Get user input
        try:
            if os.name == 'nt':  # Windows
                import msvcrt
                key = msvcrt.getch()
                if key == b'H':  # Up arrow
                    selected_index = max(0, selected_index - 1)
                elif key == b'P':  # Down arrow
                    selected_index = min(len(log_dirs) - 1, selected_index + 1)
                elif key == b'\r':  # Enter
                    break
                elif key == b'q':  # Quit
                    return None
            else:  # Unix/Linux/Mac
                import tty
                import termios
                
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                try:
                    tty.setraw(sys.stdin.fileno())
                    ch = sys.stdin.read(1)
                    if ch == '\x1b':  # Escape sequence
                        ch = sys.stdin.read(1)
                        if ch == '[':
                            ch = sys.stdin.read(1)
                            if ch == 'A':  # Up arrow
                                selected_index = max(0, selected_index - 1)
                            elif ch == 'B':  # Down arrow
                                selected_index = min(len(log_dirs) - 1, selected_index + 1)
                    elif ch == '\r':  # Enter
                        break
                    elif ch == 'q':  # Quit
                        return None
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except (ImportError, OSError):
            # Fallback to simple input if arrow key detection fails
            print("\nEnter the number of the log directory to select:")
            try:
                user_input = input("> ").strip()
                if user_input.lower() == 'q':
                    return None
                
                selected_index = int(user_input) - 1
                if 0 <= selected_index < len(log_dirs):
                    break
                else:
                    print("❌ Invalid selection. Please try again.")
                    input("Press Enter to continue...")
            except (ValueError, KeyboardInterrupt):
                return None
    
    selected_log_dir = log_dirs[selected_index]
    full_path = os.path.join('logs', selected_log_dir)
    
    print(f"\n✅ Selected: {selected_log_dir}")
    return full_path


def parse_response_file(file_path: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Parse a response file to extract the application file name and JSON data."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # Find the "Processing file:" line
        lines = content.split('\n')
        application_file = None
        
        for line in lines:
            if line.startswith('Processing file:'):
                application_file = line.replace('Processing file:', '').strip()
                break
        
        if not application_file:
            logger.warning(f"No 'Processing file:' line found in {file_path}")
            logger.debug(f"File content preview: {content[:200]}...")
            return None, None
        
        # Find the JSON data (everything after the first line)
        json_start = content.find('{')
        if json_start == -1:
            logger.warning(f"No JSON data found in {file_path}")
            logger.debug(f"File content preview: {content[:200]}...")
            return application_file, None
        
        json_content = content[json_start:]
        try:
            json_data = json.loads(json_content)
            return application_file, json_data
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in {file_path}: {e}")
            logger.debug(f"JSON content preview: {json_content[:200]}...")
            return application_file, None
            
    except FileNotFoundError:
        logger.error(f"Response file not found: {file_path}")
        return None, None
    except PermissionError:
        logger.error(f"Permission denied reading file: {file_path}")
        return None, None
    except UnicodeDecodeError as e:
        logger.error(f"Unicode decode error reading {file_path}: {e}")
        return None, None
    except Exception as e:
        logger.error(f"Unexpected error parsing response file {file_path}: {e}")
        logger.debug(f"Error type: {type(e).__name__}")
        return None, None


def convert_json_to_application_file(application_file: str, json_data: Dict[str, Any], 
                                   dropbox_account_folder_name: str) -> Optional[DropboxAccountApplicationFile]:
    """Convert JSON data to a DropboxAccountApplicationFile object."""
    try:
        # Extract owner information
        owner_data = json_data.get('owner', {})
        
        # Create ApplicationInfo object for owner
        owner = DropboxAccountApplicationInfo(
            first_name=owner_data.get('firstName'),
            last_name=owner_data.get('lastName'),
            date_of_birth=convert_date(owner_data.get('dateOfBirth')) if owner_data.get('dateOfBirth') else None,
            gender=owner_data.get('gender'),
            mailing_address_street=owner_data.get('mailingAddressStreet'),
            mailing_address_city=owner_data.get('mailingAddressCity'),
            mailing_address_state=owner_data.get('mailingAddressState'),
            mailing_address_zip=owner_data.get('mailingAddressZip'),
            phone_number=owner_data.get('phoneNumber'),
            email_address=owner_data.get('emailAddress'),
            ocr_method=owner_data.get('ocrMethod')
        )
        
        # Extract joint owner information
        joint_owner_data = json_data.get('jointOwner', {})
        
        # Create ApplicationInfo object for joint owner
        joint_owner = DropboxAccountApplicationInfo(
            first_name=joint_owner_data.get('firstName'),
            last_name=joint_owner_data.get('lastName'),
            date_of_birth=convert_date(joint_owner_data.get('dateOfBirth')) if joint_owner_data.get('dateOfBirth') else None,
            gender=joint_owner_data.get('gender'),
            mailing_address_street=joint_owner_data.get('mailingAddressStreet'),
            mailing_address_city=joint_owner_data.get('mailingAddressCity'),
            mailing_address_state=joint_owner_data.get('mailingAddressState'),
            mailing_address_zip=joint_owner_data.get('mailingAddressZip'),
            phone_number=joint_owner_data.get('phoneNumber'),
            email_address=joint_owner_data.get('emailAddress'),
            ocr_method=joint_owner_data.get('ocrMethod')
        )
        
        # Determine application type from filename or data
        app_type_str = json_data.get('application_type', 'Unknown')
        try:
            app_type = ApplicationType(app_type_str)
        except ValueError:
            app_type = ApplicationType.UNKNOWN
        
        # Create ApplicationFile object
        app_file = DropboxAccountApplicationFile(
            file_name=application_file,
            file_path=f"{dropbox_account_folder_name}/{application_file}",
            application_type=app_type,
            status=ApplicationStatus.PROCESSED,
            owner=owner,
            joint_owner=joint_owner,
            notes=json_data.get('notes', []),
            extracted_text=json_data.get('extracted_text'),
            processing_timestamp=datetime.now(),
            ocr_confidence=json_data.get('ocr_confidence'),
            lm_studio_model_used=json_data.get('lm_studio_model_used'),
            processing_duration_seconds=json_data.get('processing_duration_seconds')
        )
        
        return app_file
        
    except Exception as e:
        logger.error(f"Error converting JSON to application file for {application_file} in folder '{dropbox_account_folder_name}': {e}")
        logger.debug(f"JSON data for {application_file}: {json_data}")
        return None


def process_app_files_directory(app_files_dir: str, supabase_client: SupabaseClient) -> Dict[str, Any]:
    """Process all application files in a directory."""
    results = {
        'total_directories': 0,
        'processed_directories': 0,
        'total_files': 0,
        'processed_files': 0,
        'errors': [],
        'details': []
    }
    
    if not os.path.exists(app_files_dir):
        logger.error(f"App files directory does not exist: {app_files_dir}")
        results['errors'].append(f"Directory not found: {app_files_dir}")
        return results
    
    # Initialize Dropbox client for searching client list data
    try:
        dropbox_client = DropboxClient()
        logger.info("✅ Dropbox client initialized for client list searches")
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize Dropbox client: {e}")
        dropbox_client = None
    
    # Get all subdirectories (each represents a dropbox account)
    account_dirs = [d for d in os.listdir(app_files_dir) 
                   if os.path.isdir(os.path.join(app_files_dir, d))]
    
    results['total_directories'] = len(account_dirs)
    logger.info(f"Found {len(account_dirs)} account directories to process")
    
    for account_dir in account_dirs:
        account_path = os.path.join(app_files_dir, account_dir)
        dropbox_account_folder_name = account_dir
        
        logger.info(f"Processing account directory: {dropbox_account_folder_name}")
        
        try:
            # Find all response files in this directory
            response_files = glob.glob(os.path.join(account_path, "response_*.txt"))
            
            if not response_files:
                logger.warning(f"No response files found in {account_path}")
                continue
            
            logger.info(f"Found {len(response_files)} response files for {dropbox_account_folder_name}")
            
            # Process each response file
            application_files = []
            for response_file in response_files:
                application_file, json_data = parse_response_file(response_file)
                
                if application_file and json_data:
                    app_file = convert_json_to_application_file(
                        application_file, json_data, dropbox_account_folder_name
                    )
                    
                    if app_file:
                        application_files.append(app_file)
                        results['processed_files'] += 1
                        logger.info(f"✅ Processed: {application_file} in folder '{dropbox_account_folder_name}'")
                    else:
                        error_msg = f"Failed to convert {application_file} in folder '{dropbox_account_folder_name}'"
                        logger.error(error_msg)
                        results['errors'].append(error_msg)
                else:
                    error_msg = f"Failed to parse {response_file} in folder '{dropbox_account_folder_name}'"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                
                results['total_files'] += 1
            
            # Store the application files in the database
            if application_files:
                # Check if client list data already exists for this account
                existing_client_list_info = supabase_client.get_client_list_info_by_folder(dropbox_account_folder_name)
                
                if existing_client_list_info:
                    logger.info(f"✅ Found existing client list data for {dropbox_account_folder_name}")
                else:
                    logger.info(f"ℹ️ No existing client list data found for {dropbox_account_folder_name}")
                    
                    # Try to search for client list data using Dropbox client
                    if dropbox_client:
                        try:
                            logger.info(f"🔍 Searching for client list data for {dropbox_account_folder_name}")
                            
                            # Parse account name parts for search
                            account_name_parts = dropbox_account_folder_name.split(', ')
                            if len(account_name_parts) >= 2:
                                # Try to search for the account
                                dropbox_account_search_result = dropbox_client.dropbox_search_account(
                                    dropbox_account_folder_name, 
                                    account_name_parts, 
                                    None  # No excel file needed for this search
                                )
                                
                                if dropbox_account_search_result and dropbox_account_search_result.get('account_data'):
                                    logger.info(f"✅ Found client list data via Dropbox search for {dropbox_account_folder_name}")
                                    
                                    # Store the client list data in database
                                    client_list_store_success = _store_dropbox_client_list_data_in_database(
                                        dropbox_account_search_result, 
                                        dropbox_account_folder_name,
                                        supabase_client
                                    )
                                    
                                    if client_list_store_success:
                                        logger.info(f"✅ Successfully stored client list data for {dropbox_account_folder_name}")
                                        # Get the newly stored client list info
                                        existing_client_list_info = supabase_client.get_client_list_info_by_folder(dropbox_account_folder_name)
                                    else:
                                        logger.warning(f"⚠️ Failed to store client list data for {dropbox_account_folder_name}")
                                else:
                                    logger.info(f"ℹ️ No client list data found via Dropbox search for {dropbox_account_folder_name}")
                            else:
                                logger.info(f"ℹ️ Cannot search for client list data - account name format not recognized: {dropbox_account_folder_name}")
                                
                        except Exception as e:
                            logger.warning(f"⚠️ Error searching for client list data for {dropbox_account_folder_name}: {e}")
                    else:
                        logger.info(f"ℹ️ Dropbox client not available - skipping client list search for {dropbox_account_folder_name}")
                
                # Create DropboxAccountWithFiles object
                account = DropboxAccountWithFiles(
                    folder=dropbox_account_folder_name,
                    application_files=application_files,
                    client_list_info=existing_client_list_info,  # Include existing client list data if available
                    total_account_application_files=len(application_files),
                    processed_account_application_files=len(application_files),
                    failed_account_application_files=0,
                    processing_timestamp=datetime.now()
                )
                
                # Store in Supabase
                try:
                    account_id = supabase_client.store_dropbox_account_with_files(
                        account, force=False, update_existing=True
                    )
                    
                    if account_id:
                        logger.info(f"✅ Successfully stored {len(application_files)} files for {dropbox_account_folder_name} (ID: {account_id})")
                        results['processed_directories'] += 1
                        results['details'].append({
                            'account': dropbox_account_folder_name,
                            'account_id': account_id,
                            'files_processed': len(application_files),
                            'client_list_available': existing_client_list_info is not None
                        })
                    else:
                        error_msg = f"Failed to store files for {dropbox_account_folder_name} - no account ID returned"
                        logger.error(error_msg)
                        results['errors'].append(error_msg)
                        
                except Exception as e:
                    error_msg = f"Database error storing files for {dropbox_account_folder_name}: {e}"
                    logger.error(error_msg)
                    logger.debug(f"Account data for {dropbox_account_folder_name}: {account.dict()}")
                    results['errors'].append(error_msg)
            else:
                logger.warning(f"No valid application files found for {dropbox_account_folder_name}")
                
        except Exception as e:
            error_msg = f"Error processing directory {dropbox_account_folder_name}: {e}"
            logger.error(error_msg)
            logger.debug(f"Full error details for {dropbox_account_folder_name}: {str(e)}")
            results['errors'].append(error_msg)
    
    return results


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Process application files from log directories')
    parser.add_argument('--log-dir', help='Specific log directory to process (skips selection)')
    parser.add_argument('--force', action='store_true', help='Force re-processing even if data exists')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Select log directory
    if args.log_dir:
        log_dir = args.log_dir
        if not os.path.exists(log_dir):
            print(f"❌ Log directory does not exist: {log_dir}")
            sys.exit(1)
    else:
        log_dir = select_log_directory()
        if not log_dir:
            print("❌ No log directory selected")
            sys.exit(1)
    
    # Check if app_files directory exists
    app_files_dir = os.path.join(log_dir, 'app_files')
    if not os.path.exists(app_files_dir):
        print(f"❌ No app_files directory found in {log_dir}")
        sys.exit(1)
    
    print(f"\n📁 Processing log directory: {log_dir}")
    print(f"📄 App files directory: {app_files_dir}")
    
    # Initialize Supabase client
    try:
        supabase_client = SupabaseClient()
        print("✅ Connected to Supabase")
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        sys.exit(1)
    
    # Process the app files
    print("\n🔄 Processing application files...")
    results = process_app_files_directory(app_files_dir, supabase_client)
    
    # Display results
    print("\n" + "="*60)
    print("📊 PROCESSING RESULTS")
    print("="*60)
    print(f"📁 Total directories found: {results['total_directories']}")
    print(f"✅ Directories processed: {results['processed_directories']}")
    print(f"📄 Total files found: {results['total_files']}")
    print(f"✅ Files processed: {results['processed_files']}")
    
    if results['errors']:
        print(f"\n❌ Errors ({len(results['errors'])}):")
        for error in results['errors'][:10]:  # Show first 10 errors
            print(f"  • {error}")
        if len(results['errors']) > 10:
            print(f"  ... and {len(results['errors']) - 10} more errors")
    
    if results['details']:
        print(f"\n📋 Details:")
        for detail in results['details']:
            print(f"  • {detail['account']}: {detail['files_processed']} files (ID: {detail['account_id']}), Client List Available: {detail['client_list_available']}")
    
    print("\n" + "="*60)
    if results['errors']:
        print("⚠️  Processing completed with errors")
    else:
        print("✅ Processing completed successfully")


if __name__ == "__main__":
    main() 