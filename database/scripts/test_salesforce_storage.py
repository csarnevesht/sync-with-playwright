#!/usr/bin/env python3
"""
Test script to verify Salesforce data storage in Supabase
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from supabase_client import SupabaseClient
from supabase_client.schema import SalesforceAccount, SalesforceHousehold, SalesforceHouseholdMember

def test_salesforce_storage():
    """Test storing Salesforce account data in Supabase"""
    print("🧪 Testing Salesforce data storage in Supabase...")
    
    try:
        # Create Supabase client
        client = SupabaseClient()
        
        # Test data
        test_account = SalesforceAccount(
            salesforce_account_id="TEST_001",
            account_name="John Doe Test Account",
            account_type="Contact",
            first_name="John",
            last_name="Doe",
            email="john.doe@test.com",
            phone="555-123-4567",
            stage="Client"
        )
        
        test_household = SalesforceHousehold(
            salesforce_household_id="HH_001",
            household_name="Doe Household",
            household_head_id="TEST_001"
        )
        
        test_member = SalesforceHouseholdMember(
            household_id="HH_001",
            member_id="TEST_002",
            role="Member"
        )
        
        # Store test data
        print("📝 Storing test Salesforce account...")
        account_id = client.store_salesforce_account(test_account)
        
        if account_id:
            print(f"✅ Successfully stored Salesforce account: {account_id}")
        else:
            print("❌ Failed to store Salesforce account")
            return False
        
        print("📝 Storing test Salesforce household...")
        household_id = client.store_salesforce_household(test_household)
        
        if household_id:
            print(f"✅ Successfully stored Salesforce household: {household_id}")
        else:
            print("❌ Failed to store Salesforce household")
            return False
        
        print("📝 Storing test Salesforce household member...")
        member_id = client.store_salesforce_household_member(test_member)
        
        if member_id:
            print(f"✅ Successfully stored Salesforce household member: {member_id}")
        else:
            print("❌ Failed to store Salesforce household member")
            return False
        
        # Retrieve and verify data
        print("🔍 Retrieving stored data for verification...")
        retrieved_account = client.get_salesforce_account("TEST_001")
        
        if retrieved_account:
            print(f"✅ Successfully retrieved account: {retrieved_account.account_name}")
            print(f"   - Email: {retrieved_account.email}")
            print(f"   - Phone: {retrieved_account.phone}")
        else:
            print("❌ Failed to retrieve Salesforce account")
            return False
        
        # Clean up test data
        print("🧹 Cleaning up test data...")
        client.delete_salesforce_account("TEST_001")
        print("✅ Test completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_salesforce_storage()
    if success:
        print("\n🎉 Salesforce storage test passed!")
        sys.exit(0)
    else:
        print("\n💥 Salesforce storage test failed!")
        sys.exit(1) 