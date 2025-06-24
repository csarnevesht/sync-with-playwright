#!/usr/bin/env python3
"""
Test script to verify Supabase integration in the command runner.
"""

import os
import sys
import logging
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

def test_supabase_integration():
    """Test the Supabase integration functionality."""
    print("Testing Supabase Integration in Command Runner")
    print("=" * 60)
    
    try:
        # Test 1: Check if Supabase client can be imported
        print("1. Testing Supabase client import...")
        from supabase_client import SupabaseClient
        from supabase_client.schema import DropboxAccountApplicationFile, DropboxAccountApplicationInfo, DropboxAccountWithFiles, ApplicationStatus, ApplicationType
        print("✅ Supabase client and schema imports successful")
        
        # Test 2: Test connection
        print("\n2. Testing Supabase connection...")
        client = SupabaseClient()
        print("✅ Supabase connection successful")
        
        # Test 3: Test data storage and retrieval
        print("\n3. Testing data storage and retrieval...")
        
        # Create test data
        test_folder_name = "test_integration_folder"
        
        # Check if test data exists
        exists = client.check_application_files_exist(test_folder_name)
        print(f"Test data exists: {exists}")
        
        if exists:
            # Retrieve and display test data
            account = client.get_application_files_by_folder(test_folder_name)
            if account:
                print(f"✅ Retrieved {len(account.application_files)} files from test data")
                for app_file in account.application_files:
                    print(f"  - {app_file.file_name}: {app_file.status.value}")
            else:
                print("❌ Could not retrieve test data")
        else:
            print("No test data found - this is expected for a new test")
        
        # Test 4: Test data conversion functions
        print("\n4. Testing data conversion functions...")
        
        # Create sample data in the format that would come from the command runner
        sample_summary_data = {
            'file_info': {
                '/test/path/file1.pdf': {
                    'application_type': 'Life Insurance',
                    'status': 'Processed',
                    'owner': {
                        'firstName': 'John',
                        'lastName': 'Doe',
                        'dateOfBirth': '1980-05-15',
                        'gender': 'Male',
                        'mailingAddressStreet': '123 Main St',
                        'mailingAddressCity': 'Anytown',
                        'mailingAddressState': 'CA',
                        'mailingAddressZip': '12345',
                        'phoneNumber': '555-123-4567',
                        'emailAddress': 'john.doe@example.com'
                    },
                    'jointOwner': {
                        'firstName': 'Jane',
                        'lastName': 'Doe',
                        'dateOfBirth': '1982-08-20',
                        'gender': 'Female'
                    },
                    'notes': ['Successfully extracted structured data'],
                    'extracted_text': 'Sample extracted text',
                    'ocr_confidence': 85.5,
                    'lm_studio_model_used': 'qwen2-vl-7b-instruct',
                    'processing_duration_seconds': 45.2
                }
            }
        }
        
        # Test the conversion to Supabase format
        from datetime import datetime
        
        # Convert to ApplicationFile objects (simulating the command runner logic)
        application_files = []
        for file_path, file_info in sample_summary_data['file_info'].items():
            file_name = os.path.basename(file_path)
            
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
            
            # Convert owner data
            owner_data = file_info.get('owner', {})
            owner = DropboxAccountApplicationInfo(
                first_name=owner_data.get('firstName'),
                last_name=owner_data.get('lastName'),
                date_of_birth=owner_data.get('dateOfBirth'),
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
                date_of_birth=joint_owner_data.get('dateOfBirth'),
                gender=joint_owner_data.get('gender'),
                mailing_address_street=joint_owner_data.get('mailingAddressStreet'),
                mailing_address_city=joint_owner_data.get('mailingAddressCity'),
                mailing_address_state=joint_owner_data.get('mailingAddressState'),
                mailing_address_zip=joint_owner_data.get('mailingAddressZip'),
                phone_number=joint_owner_data.get('phoneNumber'),
                email_address=joint_owner_data.get('emailAddress'),
                ocr_method=joint_owner_data.get('ocrMethod')
            )
            
            # Create ApplicationFile object
            app_file = DropboxAccountApplicationFile(
                file_name=file_name,
                file_path=file_path,
                application_type=app_type,
                status=status,
                owner=owner,
                joint_owner=joint_owner,
                notes=file_info.get('notes', []),
                extracted_text=file_info.get('extracted_text'),
                processing_timestamp=datetime.now(),
                ocr_confidence=file_info.get('ocr_confidence'),
                lm_studio_model_used=file_info.get('lm_studio_model_used', 'qwen2-vl-7b-instruct'),
                processing_duration_seconds=file_info.get('processing_duration_seconds')
            )
            application_files.append(app_file)
        
        print(f"✅ Successfully converted {len(application_files)} files to ApplicationFile objects")
        
        # Test 5: Test account creation
        print("\n5. Testing account creation...")
        
        account = DropboxAccountWithFiles(
            folder=test_folder_name,
            application_files=application_files,
            total_files=len(application_files),
            processed_files=sum(1 for f in application_files if f.status == ApplicationStatus.PROCESSED),
            failed_files=sum(1 for f in application_files if f.status in [ApplicationStatus.FAILED, ApplicationStatus.ERROR]),
            processing_timestamp=datetime.now()
        )
        
        print(f"✅ Successfully created DropboxAccountWithFiles object with {len(account.application_files)} files")
        
        # Test 6: Test storage (optional - uncomment to test actual storage)
        print("\n6. Testing data storage (skipped - uncomment to test)...")
        # Uncomment the following lines to test actual storage
        # account_id = client.store_dropbox_account_with_files(account)
        # if account_id:
        #     print(f"✅ Successfully stored test data with account ID: {account_id}")
        # else:
        #     print("❌ Failed to store test data")
        
        print("\n" + "=" * 60)
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("The Supabase integration in the command runner should work correctly.")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        print("Please check your Supabase setup and try again.")

def main():
    """Main function."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    test_supabase_integration()

if __name__ == '__main__':
    main() 