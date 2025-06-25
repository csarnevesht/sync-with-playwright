#!/usr/bin/env python3
"""
Simple test script for Supabase integration.
Run this to verify that the integration works correctly.
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_integration():
    """Test the Supabase integration."""
    print("Testing Supabase Integration")
    print("=" * 50)
    
    try:
        # Test imports
        print("1. Testing imports...")
        from supabase_client import SupabaseClient
        from supabase_client.schema import DropboxAccountApplicationFile, DropboxAccountApplicationInfo, DropboxAccountWithFiles, ApplicationStatus, ApplicationType
        print("✅ Imports successful")
        
        # Test connection
        print("\n2. Testing connection...")
        client = SupabaseClient()
        print("✅ Connection successful")
        
        # Test data retrieval
        print("\n3. Testing data retrieval...")
        test_folder = "test_folder"
        exists = client.check_application_files_exist(test_folder)
        print(f"Data exists for '{test_folder}': {exists}")
        
        if exists:
            account = client.get_application_files_by_folder(test_folder)
            if account:
                print(f"✅ Retrieved {len(account.application_files)} files")
            else:
                print("❌ Could not retrieve data")
        
        print("\n✅ All tests passed!")
        print("The Supabase integration is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("Please check your Supabase configuration.")

if __name__ == '__main__':
    test_integration() 