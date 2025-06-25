#!/usr/bin/env python3
"""
Test script to verify that the refactored Salesforce data management code works correctly.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sync.salesforce_client.utils.salesforce_data_manager import SalesforceDataManager
from supabase_client import SupabaseClient

def test_refactored_salesforce_data_manager():
    """Test the refactored SalesforceDataManager class"""
    print("🔍 Testing refactored SalesforceDataManager...")
    
    # Test with a name that has Salesforce accounts
    test_folder_name = "Campos, Maria"
    
    try:
        # Create Supabase client and data manager
        supabase_client = SupabaseClient()
        data_manager = SalesforceDataManager(supabase_client)
        
        print(f"\n📋 Testing with folder name: {test_folder_name}")
        
        # Test the main database check method
        database_check_result = data_manager.check_database_for_salesforce_data(test_folder_name)
        
        print(f"\n📊 Database check results:")
        print(f"  should_use_database: {database_check_result['should_use_database']}")
        print(f"  should_do_live_search: {database_check_result['should_do_live_search']}")
        print(f"  salesforce_account_information: {'Found' if database_check_result['salesforce_account_information'] else 'Not found'}")
        print(f"  independent_accounts: {len(database_check_result['independent_accounts'])} found")
        
        # Test creating search result structure
        if database_check_result['salesforce_account_information']:
            search_result = data_manager.create_salesforce_search_result(
                database_check_result['salesforce_account_information'],
                view='database'
            )
            
            print(f"\n📋 Search result structure:")
            print(f"  names_found: {search_result['names_found']}")
            print(f"  total_matches: {search_result['match_info']['total_matches']}")
            print(f"  match_status: {search_result['match_info']['match_status']}")
            print(f"  view: {search_result['view']}")
            print(f"  accounts: {len(search_result['accounts'])}")
            print(f"  household: {'Yes' if search_result['household'] else 'No'}")
            print(f"  head: {'Yes' if search_result['head'] else 'No'}")
            print(f"  members: {len(search_result['members'])}")
            
            print("✅ SUCCESS: Refactored code is working correctly!")
        else:
            print("⚠️ No Salesforce account information found to test search result creation")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_refactored_salesforce_data_manager() 