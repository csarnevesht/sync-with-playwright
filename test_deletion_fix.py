#!/usr/bin/env python3
"""
Test script to verify that the improved Salesforce account deletion logic works correctly.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from supabase_client import SupabaseClient

def test_deletion_fix():
    """Test the improved deletion logic"""
    print("🔍 Testing improved Salesforce account deletion logic...")
    
    # Test with the problematic folder name
    test_folder_name = "Campos, Maria"
    
    try:
        # Create Supabase client
        client = SupabaseClient()
        
        print(f"\n📋 Testing deletion for folder: {test_folder_name}")
        
        # First, check what accounts exist
        print("\n📊 Checking existing accounts before deletion:")
        response = client.client.table('salesforce_accounts').select('*').execute()
        
        campos_accounts = []
        for account in response.data:
            account_name = account.get('account_name', '')
            if 'campos' in account_name.lower():
                campos_accounts.append(account)
                print(f"  - {account_name} (ID: {account.get('salesforce_account_id')})")
        
        if not campos_accounts:
            print("  No Campos accounts found")
            return
        
        print(f"\n🔍 Found {len(campos_accounts)} Campos accounts")
        
        # Test the deletion method
        print(f"\n🗑️ Testing deletion...")
        success = client.delete_salesforce_accounts_by_folder_name(test_folder_name)
        
        print(f"\n📊 Deletion result: {'✅ Success' if success else '❌ Failed'}")
        
        # Check what accounts remain
        print(f"\n📊 Checking remaining accounts after deletion:")
        response = client.client.table('salesforce_accounts').select('*').execute()
        
        remaining_campos_accounts = []
        for account in response.data:
            account_name = account.get('account_name', '')
            if 'campos' in account_name.lower():
                remaining_campos_accounts.append(account)
                print(f"  - {account_name} (ID: {account.get('salesforce_account_id')})")
        
        if not remaining_campos_accounts:
            print("  No Campos accounts remaining - deletion successful!")
        else:
            print(f"  {len(remaining_campos_accounts)} Campos accounts still remain")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_deletion_fix() 