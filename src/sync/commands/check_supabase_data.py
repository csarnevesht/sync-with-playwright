#!/usr/bin/env python3
"""
Command to check and retrieve application files data from Supabase.
"""

import os
import sys
import logging
from typing import Optional

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

def check_data_exists(folder_name: str) -> bool:
    """Check if application files data exists for a folder."""
    try:
        supabase_client = SupabaseClient()
        return supabase_client.check_application_files_exist(folder_name)
    except Exception as e:
        logger.error(f"Error checking data existence: {e}")
        return False

def get_data_summary(folder_name: str) -> Optional[str]:
    """Get a summary of application files data for a folder."""
    try:
        supabase_client = SupabaseClient()
        account = supabase_client.get_application_files_by_folder(folder_name)
        
        if not account:
            return None
        
        summary_lines = []
        summary_lines.append(f"Application Files Data for: {folder_name}")
        summary_lines.append("=" * (len(folder_name) + 30))
        summary_lines.append(f"Total files: {len(account.application_files)}")
        summary_lines.append(f"Processed: {account.processed_files}")
        summary_lines.append(f"Failed: {account.failed_files}")
        summary_lines.append(f"Processing timestamp: {account.processing_timestamp}")
        
        summary_lines.append("\nFiles:")
        for app_file in account.application_files:
            status_emoji = "✅" if app_file.status.value == "Processed" else "❌"
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
        logger.error(f"Error getting data summary: {e}")
        return None

def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Check and retrieve application files data from Supabase')
    parser.add_argument('folder_name', help='Name of the Dropbox folder')
    parser.add_argument('--summary', action='store_true', help='Get detailed summary of stored data')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Check if data exists
    exists = check_data_exists(args.folder_name)
    print(f"Application files data exists for {args.folder_name}: {exists}")
    
    if exists and args.summary:
        print("\n" + "="*50)
        summary = get_data_summary(args.folder_name)
        if summary:
            print(summary)
        else:
            print("Error retrieving data summary")

if __name__ == '__main__':
    main() 