#!/usr/bin/env python3
"""
Script to test the client list storage functionality.
"""

import os
import sys
from pathlib import Path
from datetime import date

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from supabase_client import SupabaseClient
from supabase_client.schema import DropboxAccountClientListInfo

def test_client_list_storage():
    """Test storing and retrieving client list data."""
    print("🧪 Testing client list storage functionality...")
    
    try:
        # Create Supabase client
        client = SupabaseClient()
        
        # Test data
        test_folder = "Test Client List Account"
        test_client_list_info = DropboxAccountClientListInfo(
            account_name="John Doe",
            first_name="John",
            middle_name="Michael",
            last_name="Doe",
            birthdate=date(1980, 5, 15),
            gender="Male",
            phone="555-123-4567",
            address="123 Main Street",
            city="Anytown",
            state="CA",
            zip_code="90210",
            email="john.doe@example.com",
            additional_info="Test account for client list storage",
            match_status="Match found",
            drivers_license_data={
                "license_number": "DL123456789",
                "expiration_date": "2025-12-31"
            },
            search_info={
                "search_method": "last_name_search",
                "sheets_searched": ["Client Mailing List"]
            }
        )
        
        print(f"📝 Test data created for folder: {test_folder}")
        
        # First, create a test dropbox account
        print("\n1. Creating test dropbox account...")
        account_data = {
            'folder': test_folder,
            'first_name': 'John',
            'last_name': 'Doe',
            'total_files': 0,
            'processed_files': 0,
            'failed_files': 0
        }
        
        account_response = client.client.table('dropbox_accounts').insert(account_data).execute()
        if not account_response.data:
            print("❌ Failed to create test account")
            return False
        
        account_id = account_response.data[0]['id']
        print(f"✅ Test account created with ID: {account_id}")
        
        # Store client list info
        print("\n2. Storing client list info...")
        client_list_id = client.store_client_list_info(test_client_list_info, account_id)
        if client_list_id:
            print(f"✅ Client list info stored with ID: {client_list_id}")
        else:
            print("❌ Failed to store client list info")
            return False
        
        # Retrieve client list info
        print("\n3. Retrieving client list info...")
        retrieved_info = client.get_client_list_info_by_folder(test_folder)
        if retrieved_info:
            print("✅ Client list info retrieved successfully")
            print(f"   Name: {retrieved_info.first_name} {retrieved_info.last_name}")
            print(f"   Email: {retrieved_info.email}")
            print(f"   Phone: {retrieved_info.phone}")
            print(f"   Address: {retrieved_info.address}, {retrieved_info.city}, {retrieved_info.state} {retrieved_info.zip_code}")
            print(f"   Match Status: {retrieved_info.match_status}")
        else:
            print("❌ Failed to retrieve client list info")
            return False
        
        # Test the enhanced get_application_files_by_folder method
        print("\n4. Testing enhanced get_application_files_by_folder...")
        account_with_files = client.get_application_files_by_folder(test_folder)
        if account_with_files and account_with_files.client_list_info:
            print("✅ Account with client list info retrieved successfully")
            print(f"   Folder: {account_with_files.folder}")
            print(f"   Client List Name: {account_with_files.client_list_info.first_name} {account_with_files.client_list_info.last_name}")
        else:
            print("❌ Failed to retrieve account with client list info")
            return False
        
        # Clean up test data
        print("\n5. Cleaning up test data...")
        client.delete_client_list_info_for_folder(test_folder)
        client.client.table('dropbox_accounts').delete().eq('id', account_id).execute()
        print("✅ Test data cleaned up")
        
        print("\n🎉 All tests passed! Client list storage is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_client_list_storage()
    if not success:
        sys.exit(1) 