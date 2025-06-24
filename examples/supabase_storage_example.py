#!/usr/bin/env python3
"""
Example script demonstrating how to use the Supabase storage functionality
for application files data.
"""

import os
import sys
import logging
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from supabase_client import SupabaseClient
from supabase_client.schema import DropboxAccountApplicationFile, DropboxAccountApplicationInfo, DropboxAccountWithFiles, ApplicationStatus, ApplicationType
from datetime import datetime, date

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def example_check_data():
    """Example: Check if data exists for a folder."""
    print("=" * 60)
    print("EXAMPLE: Checking if data exists")
    print("=" * 60)
    
    folder_name = "Example Folder"
    client = SupabaseClient()
    
    exists = client.check_application_files_exist(folder_name)
    print(f"Data exists for '{folder_name}': {exists}")
    
    if exists:
        account = client.get_application_files_by_folder(folder_name)
        if account:
            print(f"Found {len(account.application_files)} files")
            print(f"Processed: {account.processed_files}, Failed: {account.failed_files}")

def example_store_data():
    """Example: Store sample application files data."""
    print("\n" + "=" * 60)
    print("EXAMPLE: Storing sample data")
    print("=" * 60)
    
    # Create sample person data
    owner = DropboxAccountApplicationInfo(
        first_name="John",
        last_name="Doe",
        date_of_birth=date(1980, 5, 15),
        gender="Male",
        mailing_address_street="123 Main St",
        mailing_address_city="Anytown",
        mailing_address_state="CA",
        mailing_address_zip="12345",
        phone_number="555-123-4567",
        email_address="john.doe@example.com"
    )
    
    joint_owner = DropboxAccountApplicationInfo(
        first_name="Jane",
        last_name="Doe",
        date_of_birth=date(1982, 8, 20),
        gender="Female",
        mailing_address_street="123 Main St",
        mailing_address_city="Anytown",
        mailing_address_state="CA",
        mailing_address_zip="12345",
        phone_number="555-123-4568",
        email_address="jane.doe@example.com"
    )
    
    # Create sample application files
    app_file1 = ApplicationFile(
        file_name="Life_Insurance_Application_John_Doe.pdf",
        application_type=ApplicationType.LIFE_INSURANCE,
        status=ApplicationStatus.PROCESSED,
        owner=owner,
        joint_owner=joint_owner,
        notes=["Successfully extracted structured data", "Both owner and joint owner found"],
        processing_timestamp=datetime.now(),
        lm_studio_model_used="qwen2-vl-7b-instruct",
        processing_duration_seconds=45.2
    )
    
    app_file2 = ApplicationFile(
        file_name="Annuity_Application_John_Doe.pdf",
        application_type=ApplicationType.ANNUITY,
        status=ApplicationStatus.PROCESSED,
        owner=owner,
        joint_owner=PersonInfo(),  # No joint owner for this file
        notes=["Successfully extracted owner data", "No joint owner found"],
        processing_timestamp=datetime.now(),
        lm_studio_model_used="qwen2-vl-7b-instruct",
        processing_duration_seconds=38.7
    )
    
    # Create account with files
    account = DropboxAccountWithFiles(
        folder="Example Folder",
        first_name="John",
        last_name="Doe",
        application_files=[app_file1, app_file2],
        total_files=2,
        processed_files=2,
        failed_files=0,
        processing_timestamp=datetime.now()
    )
    
    # Store in Supabase
    client = SupabaseClient()
    account_id = client.store_dropbox_account_with_files(account)
    
    if account_id:
        print(f"Successfully stored data with account ID: {account_id}")
        print(f"Stored {len(account.application_files)} application files")
    else:
        print("Failed to store data")

def example_retrieve_data():
    """Example: Retrieve and display stored data."""
    print("\n" + "=" * 60)
    print("EXAMPLE: Retrieving stored data")
    print("=" * 60)
    
    folder_name = "Example Folder"
    client = SupabaseClient()
    
    account = client.get_application_files_by_folder(folder_name)
    
    if account:
        print(f"Account: {account.folder}")
        print(f"Name: {account.first_name} {account.last_name}")
        print(f"Total files: {len(account.application_files)}")
        print(f"Processed: {account.processed_files}, Failed: {account.failed_files}")
        print(f"Processing timestamp: {account.processing_timestamp}")
        
        print("\nApplication Files:")
        for i, app_file in enumerate(account.application_files, 1):
            print(f"\n{i}. {app_file.file_name}")
            print(f"   Type: {app_file.application_type.value}")
            print(f"   Status: {app_file.status.value}")
            
            if app_file.owner.first_name or app_file.owner.last_name:
                owner_name = f"{app_file.owner.first_name or ''} {app_file.owner.last_name or ''}".strip()
                print(f"   Owner: {owner_name}")
                if app_file.owner.date_of_birth:
                    print(f"   DOB: {app_file.owner.date_of_birth}")
                if app_file.owner.gender:
                    print(f"   Gender: {app_file.owner.gender}")
            
            if app_file.joint_owner.first_name or app_file.joint_owner.last_name:
                joint_name = f"{app_file.joint_owner.first_name or ''} {app_file.joint_owner.last_name or ''}".strip()
                print(f"   Joint Owner: {joint_name}")
            
            if app_file.notes:
                print(f"   Notes: {', '.join(app_file.notes)}")
    else:
        print(f"No data found for folder: {folder_name}")

def example_delete_data():
    """Example: Delete stored data."""
    print("\n" + "=" * 60)
    print("EXAMPLE: Deleting stored data")
    print("=" * 60)
    
    folder_name = "Example Folder"
    client = SupabaseClient()
    
    # Check if data exists first
    exists = client.check_application_files_exist(folder_name)
    print(f"Data exists before deletion: {exists}")
    
    if exists:
        success = client.delete_application_files_for_folder(folder_name)
        if success:
            print(f"Successfully deleted data for folder: {folder_name}")
            
            # Verify deletion
            exists_after = client.check_application_files_exist(folder_name)
            print(f"Data exists after deletion: {exists_after}")
        else:
            print(f"Failed to delete data for folder: {folder_name}")
    else:
        print(f"No data to delete for folder: {folder_name}")

def main():
    """Run all examples."""
    print("SUPABASE STORAGE EXAMPLES")
    print("This script demonstrates the Supabase storage functionality")
    print("for application files data.")
    
    try:
        # Example 1: Check if data exists
        example_check_data()
        
        # Example 2: Store sample data
        example_store_data()
        
        # Example 3: Retrieve stored data
        example_retrieve_data()
        
        # Example 4: Delete data (optional)
        # Uncomment the next line if you want to delete the sample data
        # example_delete_data()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"Error running examples: {e}")
        print(f"\nError: {e}")
        print("Make sure your Supabase connection is configured correctly.")

if __name__ == '__main__':
    main() 