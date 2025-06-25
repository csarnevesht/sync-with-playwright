#!/usr/bin/env python3
"""
Command to store application files data in Supabase.
This allows caching the results of LM Studio processing to avoid re-running the slow processor.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

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
    DropboxAccountApplicationFile, DropboxAccountApplicationInfo, DropboxAccountWithFiles,
    ApplicationStatus, ApplicationType
)

logger = logging.getLogger(__name__)

def convert_file_info_to_application_file(file_info: Dict[str, Any], file_name: str, file_path: str = None) -> DropboxAccountApplicationFile:
    """Convert file info from LM Studio processor to DropboxAccountApplicationFile model."""
    
    # Convert application type
    app_type_str = file_info.get('application_type', 'Unknown')
    try:
        app_type = ApplicationType(app_type_str)
    except ValueError:
        app_type = ApplicationType.UNKNOWN
    
    # Convert status
    status_str = file_info.get('status', 'Processed')
    try:
        status = ApplicationStatus(status_str)
    except ValueError:
        status = ApplicationStatus.PROCESSED
    
    # Helper function to convert date format
    def convert_date(date_str):
        if not date_str:
            return None
        try:
            # Handle MM/DD/YYYY format
            if '/' in date_str:
                date_obj = datetime.strptime(date_str, '%m/%d/%Y')
                return date_obj.date()
            # Handle YYYY-MM-DD format
            elif '-' in date_str:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                return date_obj.date()
            else:
                return None
        except ValueError:
            return None
    
    # Convert owner data
    owner_data = file_info.get('owner', {})
    owner = DropboxAccountApplicationInfo(
        first_name=owner_data.get('firstName'),
        last_name=owner_data.get('lastName'),
        date_of_birth=convert_date(owner_data.get('dateOfBirth')),
        gender=owner_data.get('gender'),
        mailing_address_street=owner_data.get('mailingAddressStreet'),
        mailing_address_city=owner_data.get('mailingAddressCity'),
        mailing_address_state=owner_data.get('mailingAddressState'),
        mailing_address_zip=owner_data.get('mailingAddressZip'),
        phone_number=owner_data.get('phoneNumber'),
        email_address=owner_data.get('emailAddress'),
        ocr_method=owner_data.get('ocrMethod')
    )
    
    # Convert joint owner data
    joint_owner_data = file_info.get('jointOwner', {})
    joint_owner = DropboxAccountApplicationInfo(
        first_name=joint_owner_data.get('firstName'),
        last_name=joint_owner_data.get('lastName'),
        date_of_birth=convert_date(joint_owner_data.get('dateOfBirth')),
        gender=joint_owner_data.get('gender'),
        mailing_address_street=joint_owner_data.get('mailingAddressStreet'),
        mailing_address_city=joint_owner_data.get('mailingAddressCity'),
        mailing_address_state=joint_owner_data.get('mailingAddressState'),
        mailing_address_zip=joint_owner_data.get('mailingAddressZip'),
        phone_number=joint_owner_data.get('phoneNumber'),
        email_address=joint_owner_data.get('emailAddress'),
        ocr_method=joint_owner_data.get('ocrMethod')
    )
    
    # Create DropboxAccountApplicationFile object
    app_file = DropboxAccountApplicationFile(
        file_name=file_name,
        file_path=file_path,
        application_type=app_type,
        status=status,
        owner=owner,
        joint_owner=joint_owner,
        notes=file_info.get('notes', []),
        extracted_text=file_info.get('extracted_text'),  # This might not be in the original data
        processing_timestamp=datetime.now(),
        ocr_confidence=file_info.get('ocr_confidence'),
        lm_studio_model_used=file_info.get('lm_studio_model_used', 'qwen2-vl-7b-instruct'),
        processing_duration_seconds=file_info.get('processing_duration_seconds')
    )
    
    return app_file

def load_application_files_from_logs(log_dir: str, folder_name: str) -> Optional[DropboxAccountWithFiles]:
    """Load application files data from log files."""
    
    # Look for the most recent analysis log directory
    log_path = Path(log_dir)
    if not log_path.exists():
        logger.error(f"Log directory does not exist: {log_dir}")
        return None
    
    # Find the most recent analysis directory
    analysis_dirs = [d for d in log_path.iterdir() if d.is_dir() and 'analysis' in d.name]
    if not analysis_dirs:
        logger.error(f"No analysis directories found in {log_dir}")
        return None
    
    # Sort by modification time and get the most recent
    latest_dir = max(analysis_dirs, key=lambda d: d.stat().st_mtime)
    logger.info(f"Using analysis directory: {latest_dir}")
    
    # Look for the specific folder's report
    reports_dir = latest_dir / 'reports'
    if not reports_dir.exists():
        logger.error(f"Reports directory not found: {reports_dir}")
        return None
    
    # Find the folder's report file
    report_file = None
    for file in reports_dir.iterdir():
        if file.is_file() and file.name.endswith('.txt') and folder_name in file.name:
            report_file = file
            break
    
    if not report_file:
        logger.error(f"No report file found for folder: {folder_name}")
        return None
    
    logger.info(f"Found report file: {report_file}")
    
    # Parse the report file to extract application files data
    application_files = []
    
    try:
        with open(report_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse the structured text format
        lines = content.split('\n')
        current_file_data = {}
        current_file_name = None
        in_file_section = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Look for file path markers
            if line.startswith('📁 /'):
                # Save previous file data if exists
                if current_file_name and current_file_data:
                    try:
                        app_file = convert_file_info_to_application_file(current_file_data, current_file_name)
                        application_files.append(app_file)
                    except Exception as e:
                        logger.warning(f"Error converting file data for {current_file_name}: {e}")
                
                # Start new file
                current_file_name = line.split('📁 ')[1].strip()
                current_file_data = {}
                in_file_section = True
                
            # Look for status (on the line after file path)
            elif in_file_section and line.startswith('   Status:'):
                status = line.split('Status:')[1].strip()
                if status:
                    current_file_data['status'] = status
                else:
                    current_file_data['status'] = 'Processed'
                
            # Look for owner information
            elif in_file_section and '👤 **Owner Information:**' in line:
                # Parse owner information from the following lines
                owner_data = {}
                j = i + 1
                while j < len(lines) and lines[j].strip() and not lines[j].strip().startswith('📄'):
                    owner_line = lines[j].strip()
                    if 'Name:' in owner_line:
                        name = owner_line.split('Name:')[1].strip()
                        if name:
                            name_parts = name.split()
                            if len(name_parts) >= 2:
                                owner_data['firstName'] = name_parts[0]
                                owner_data['lastName'] = ' '.join(name_parts[1:])
                    elif 'DOB:' in owner_line:
                        dob = owner_line.split('DOB:')[1].strip()
                        if dob:
                            owner_data['dateOfBirth'] = dob
                    elif 'Gender:' in owner_line:
                        gender = owner_line.split('Gender:')[1].strip()
                        if gender:
                            owner_data['gender'] = gender
                    elif 'Phone:' in owner_line:
                        phone = owner_line.split('Phone:')[1].strip()
                        if phone and phone != 'N/A':
                            owner_data['phoneNumber'] = phone
                    elif 'Email:' in owner_line:
                        email = owner_line.split('Email:')[1].strip()
                        if email and email != 'N/A':
                            owner_data['emailAddress'] = email
                    elif 'Address:' in owner_line:
                        address = owner_line.split('Address:')[1].strip()
                        if address and address != 'N/A':
                            # Parse address components
                            address_parts = address.split(',')
                            if len(address_parts) >= 2:
                                owner_data['mailingAddressStreet'] = address_parts[0].strip()
                                city_state_zip = address_parts[1].strip()
                                if len(address_parts) >= 3:
                                    zip_part = address_parts[2].strip()
                                    if zip_part:
                                        owner_data['mailingAddressZip'] = zip_part
                                # Try to extract city and state
                                city_state_parts = city_state_zip.split()
                                if len(city_state_parts) >= 2:
                                    owner_data['mailingAddressCity'] = city_state_parts[0].strip()
                                    owner_data['mailingAddressState'] = city_state_parts[1].strip()
                    j += 1
                
                current_file_data['owner'] = owner_data
                
            # Look for application type
            elif in_file_section and '📄 Application Type:' in line:
                app_type = line.split('📄 Application Type:')[1].strip()
                if app_type and app_type != 'Unknown':
                    current_file_data['application_type'] = app_type
                else:
                    current_file_data['application_type'] = 'Unknown'
                    
            # End of file section (look for next file or end of file details)
            elif in_file_section and (line.startswith('📁 /') or line.startswith('📊 **SUMMARY DATA**')):
                in_file_section = False
        
        # Don't forget the last file
        if current_file_name and current_file_data:
            try:
                app_file = convert_file_info_to_application_file(current_file_data, current_file_name)
                application_files.append(app_file)
            except Exception as e:
                logger.warning(f"Error converting file data for {current_file_name}: {e}")
    
    except Exception as e:
        logger.error(f"Error reading report file: {e}")
        return None
    
    if not application_files:
        logger.warning(f"No application files found in report for folder: {folder_name}")
        return None
    
    # Create DropboxAccountWithFiles object
    account = DropboxAccountWithFiles(
        folder=folder_name,
        application_files=application_files,
        total_account_application_files=len(application_files),
        processed_account_application_files=sum(1 for f in application_files if f.status == ApplicationStatus.PROCESSED),
        failed_account_application_files=sum(1 for f in application_files if f.status in [ApplicationStatus.FAILED, ApplicationStatus.ERROR]),
        processing_timestamp=datetime.now()
    )
    
    return account

def store_application_files_data(folder_name: str, log_dir: str = None, force: bool = False) -> bool:
    """Store application files data for a specific folder in Supabase."""
    
    if not log_dir:
        # Default to the logs directory in the project root
        project_root = Path(__file__).parent.parent.parent.parent
        log_dir = project_root / 'logs saved'
    
    logger.info(f"Storing application files data for folder: {folder_name}")
    logger.info(f"Using log directory: {log_dir}")
    
    try:
        # Load application files data from logs
        account = load_application_files_from_logs(str(log_dir), folder_name)
        if not account:
            logger.error(f"Failed to load application files data for folder: {folder_name}")
            return False
        
        # Store in Supabase
        supabase_client = SupabaseClient()
        account_id = supabase_client.store_dropbox_account_with_files(account, force=force)
        
        if account_id:
            logger.info(f"Successfully stored application files data for folder: {folder_name}")
            logger.info(f"Account ID: {account_id}")
            logger.info(f"Total files stored: {len(account.application_files)}")
            return True
        else:
            logger.error(f"Failed to store application files data for folder: {folder_name}")
            return False
            
    except Exception as e:
        logger.error(f"Error storing application files data: {e}")
        return False

def check_application_files_exist(folder_name: str) -> bool:
    """Check if application files data exists for a folder."""
    try:
        supabase_client = SupabaseClient()
        return supabase_client.check_application_files_exist(folder_name)
    except Exception as e:
        logger.error(f"Error checking application files existence: {e}")
        return False

def get_application_files_summary(folder_name: str) -> str:
    """Get a summary of application files data for a folder."""
    try:
        supabase_client = SupabaseClient()
        account = supabase_client.get_application_files_by_folder(folder_name)
        
        if not account:
            return f"No application files data found for folder: {folder_name}"
        
        summary_lines = []
        summary_lines.append(f"Application Files Summary for: {folder_name}")
        summary_lines.append("=" * (len(folder_name) + 30))
        summary_lines.append(f"Total files: {len(account.application_files)}")
        summary_lines.append(f"Processed: {account.processed_files}")
        summary_lines.append(f"Failed: {account.failed_files}")
        summary_lines.append(f"Processing timestamp: {account.processing_timestamp}")
        
        summary_lines.append("\nFiles:")
        for app_file in account.application_files:
            status_emoji = "✅" if app_file.status == ApplicationStatus.PROCESSED else "❌"
            summary_lines.append(f"  {status_emoji} {app_file.file_name}")
            summary_lines.append(f"    Type: {app_file.application_type.value}")
            summary_lines.append(f"    Status: {app_file.status.value}")
            
            if app_file.owner.first_name or app_file.owner.last_name:
                owner_name = f"{app_file.owner.first_name or ''} {app_file.owner.last_name or ''}".strip()
                summary_lines.append(f"    Owner: {owner_name}")
            
            if app_file.joint_owner.first_name or app_file.joint_owner.last_name:
                joint_name = f"{app_file.joint_owner.first_name or ''} {app_file.joint_owner.last_name or ''}".strip()
                summary_lines.append(f"    Joint Owner: {joint_name}")
            
            if app_file.notes:
                summary_lines.append(f"    Notes: {', '.join(app_file.notes[:3])}")  # Show first 3 notes
        
        return "\n".join(summary_lines)
        
    except Exception as e:
        logger.error(f"Error getting application files summary: {e}")
        return f"Error getting summary: {e}"

def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Store application files data in Supabase')
    parser.add_argument('folder_name', help='Name of the Dropbox folder')
    parser.add_argument('--log-dir', help='Directory containing log files')
    parser.add_argument('--check', action='store_true', help='Check if data exists')
    parser.add_argument('--summary', action='store_true', help='Get summary of stored data')
    parser.add_argument('--force', action='store_true', help='Force re-storage even if data exists')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if args.check:
        exists = check_application_files_exist(args.folder_name)
        print(f"Application files data exists for {args.folder_name}: {exists}")
        return
    
    if args.summary:
        summary = get_application_files_summary(args.folder_name)
        print(summary)
        return
    
    # Check if data already exists
    if not args.force and check_application_files_exist(args.folder_name):
        print(f"Application files data already exists for {args.folder_name}")
        print("Use --force to re-store the data")
        return
    
    # Store the data
    success = store_application_files_data(args.folder_name, args.log_dir, force=args.force)
    if success:
        print(f"Successfully stored application files data for {args.folder_name}")
        
        # Show summary
        summary = get_application_files_summary(args.folder_name)
        print("\n" + summary)
    else:
        print(f"Failed to store application files data for {args.folder_name}")
        sys.exit(1)

if __name__ == '__main__':
    main() 