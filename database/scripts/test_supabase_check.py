#!/usr/bin/env python3
"""
Test script to check if Supabase data existence check is working correctly.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from supabase_client import SupabaseClient

def test_supabase_check():
    """Test the Supabase data existence check."""
    print("Testing Supabase data existence check...")
    
    try:
        # Create Supabase client
        client = SupabaseClient()
        
        # Test folder name
        folder_name = "Afanador, Isabel"
        
        print(f"Checking if data exists for folder: {folder_name}")
        
        # Check if data exists
        exists = client.check_application_files_exist(folder_name)
        
        print(f"Data exists: {exists}")
        
        if exists:
            # Try to retrieve the data
            account = client.get_application_files_by_folder(folder_name)
            if account:
                print(f"Successfully retrieved data:")
                print(f"  Total files: {len(account.application_files)}")
                print(f"  Processed files: {account.processed_files}")
                print(f"  Failed files: {account.failed_files}")
                print(f"  Processing timestamp: {account.processing_timestamp}")
                
                # Show some file details
                for i, app_file in enumerate(account.application_files[:3]):  # Show first 3 files
                    print(f"  File {i+1}: {app_file.file_name}")
                    print(f"    Type: {app_file.application_type.value}")
                    print(f"    Status: {app_file.status.value}")
            else:
                print("Data exists but could not be retrieved")
        else:
            print("No data found in Supabase")
            
    except Exception as e:
        print(f"Error testing Supabase check: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_supabase_check() 