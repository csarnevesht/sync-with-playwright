#!/usr/bin/env python3
"""
Script to check Salesforce accounts in the database
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from supabase_client import SupabaseClient

def check_salesforce_accounts():
    """Check Salesforce accounts in the database"""
    print("🔍 Checking Salesforce accounts in database...")
    
    try:
        # Create Supabase client
        client = SupabaseClient()
        
        # Query Salesforce accounts table
        response = client.client.table('salesforce_accounts').select('*').execute()
        
        if response.data:
            print(f"✅ Found {len(response.data)} Salesforce accounts:")
            print("=" * 80)
            
            for i, account in enumerate(response.data, 1):
                print(f"\n📋 Account {i}:")
                print(f"   ID: {account.get('id', 'N/A')}")
                print(f"   Salesforce Account ID: {account.get('salesforce_account_id', 'N/A')}")
                print(f"   Account Name: {account.get('account_name', 'N/A')}")
                print(f"   Account Type: {account.get('account_type', 'N/A')}")
                print(f"   First Name: {account.get('first_name', 'N/A')}")
                print(f"   Last Name: {account.get('last_name', 'N/A')}")
                print(f"   Email: {account.get('email', 'N/A')}")
                print(f"   Phone: {account.get('phone', 'N/A')}")
                print(f"   Stage: {account.get('stage', 'N/A')}")
                print(f"   Created: {account.get('created_at', 'N/A')}")
                print("-" * 40)
        else:
            print("❌ No Salesforce accounts found in database")
            
        # Also check Salesforce households
        print("\n🏠 Checking Salesforce households...")
        household_response = client.client.table('salesforce_households').select('*').execute()
        
        if household_response.data:
            print(f"✅ Found {len(household_response.data)} Salesforce households:")
            for household in household_response.data:
                print(f"   - {household.get('household_name', 'N/A')} (ID: {household.get('id', 'N/A')})")
        else:
            print("❌ No Salesforce households found in database")
            
    except Exception as e:
        print(f"❌ Error checking Salesforce accounts: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = check_salesforce_accounts()
    if success:
        print("\n✅ Salesforce accounts check completed!")
    else:
        print("\n❌ Salesforce accounts check failed!")
        sys.exit(1) 