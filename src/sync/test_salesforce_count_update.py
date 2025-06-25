"""
Test script for salesforce_accounts_found_count field updates
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from supabase_client import SupabaseClient
from database_models import DropboxAccount

def test_salesforce_count_update():
    """Test the salesforce_accounts_found_count update functionality"""
    print("Testing salesforce_accounts_found_count update functionality...")
    
    try:
        # Initialize Supabase client
        supabase_client = SupabaseClient()
        
        # Test folder name
        test_folder = "Test Account"
        
        print(f"\n1. Testing get_salesforce_accounts_found_count for folder: {test_folder}")
        current_count = supabase_client.get_salesforce_accounts_found_count(test_folder)
        print(f"   Current count: {current_count}")
        
        # Test different count values
        test_counts = [0, 1, 5, -1]
        
        for count in test_counts:
            print(f"\n2. Testing update_salesforce_accounts_found_count with count: {count}")
            
            # Update the count
            success = supabase_client.update_salesforce_accounts_found_count(test_folder, count)
            print(f"   Update success: {success}")
            
            if success:
                # Verify the update
                new_count = supabase_client.get_salesforce_accounts_found_count(test_folder)
                print(f"   Verified new count: {new_count}")
                
                if new_count == count:
                    print(f"   ✅ Count update verified successfully")
                else:
                    print(f"   ❌ Count update verification failed - expected {count}, got {new_count}")
            else:
                print(f"   ❌ Count update failed")
        
        # Test with None/null value
        print(f"\n3. Testing update_salesforce_accounts_found_count with None value")
        success = supabase_client.update_salesforce_accounts_found_count(test_folder, None)
        print(f"   Update success: {success}")
        
        if success:
            new_count = supabase_client.get_salesforce_accounts_found_count(test_folder)
            print(f"   Verified new count: {new_count}")
        
        print(f"\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

def test_dropbox_account_model():
    """Test the DropboxAccount model methods"""
    print("\nTesting DropboxAccount model methods...")
    
    # Test with different count values
    test_cases = [
        (None, "Not searched"),
        (-1, "Search attempted but failed"),
        (0, "Searched - No accounts found"),
        (1, "Searched - 1 accounts found"),
        (5, "Searched - 5 accounts found")
    ]
    
    for count, expected_status in test_cases:
        account = DropboxAccount(
            folder="Test Account",
            salesforce_accounts_found_count=count
        )
        
        has_search_been_done = account.has_salesforce_search_been_done()
        search_status = account.get_salesforce_search_status()
        
        print(f"\nCount: {count}")
        print(f"  has_salesforce_search_been_done(): {has_search_been_done}")
        print(f"  get_salesforce_search_status(): '{search_status}'")
        print(f"  Expected status: '{expected_status}'")
        
        if search_status == expected_status:
            print(f"  ✅ Status matches expected")
        else:
            print(f"  ❌ Status mismatch")

if __name__ == "__main__":
    print("Salesforce Accounts Found Count Test")
    print("=" * 50)
    
    test_dropbox_account_model()
    test_salesforce_count_update() 