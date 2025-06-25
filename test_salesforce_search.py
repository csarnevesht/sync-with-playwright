#!/usr/bin/env python3
"""
Test script to verify Salesforce search functionality
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from supabase_client import SupabaseClient

def test_salesforce_search():
    """Test Salesforce account search functionality."""
    print("🧪 Testing Salesforce Search Functionality")
    print("=" * 50)
    
    try:
        # Create Supabase client
        client = SupabaseClient()
        
        # Test search for Maria Montesino
        folder_name = "Montesino, Maria"
        print(f"🔍 Testing search for: {folder_name}")
        
        # Create name variations
        name_variations = [
            folder_name,
            folder_name.replace(', ', ' '),  # "Montesino, Maria" -> "Montesino Maria"
            folder_name.split(', ')[1] + ' ' + folder_name.split(', ')[0] if ', ' in folder_name else None  # "Montesino, Maria" -> "Maria Montesino"
        ]
        name_variations = [name for name in name_variations if name]
        
        print(f"📝 Name variations to search: {name_variations}")
        
        salesforce_accounts = []
        for name_var in name_variations:
            print(f"\n🔍 Searching for exact match: '{name_var}'")
            # Search for exact matches first
            sf_result = client.client.table('salesforce_accounts').select('*').eq('account_name', name_var).execute()
            if sf_result.data:
                print(f"✅ Found {len(sf_result.data)} exact match(es)")
                salesforce_accounts.extend(sf_result.data)
            else:
                print(f"❌ No exact match found")
            
            # Search for partial matches using manual filtering
            print(f"🔍 Searching for partial matches containing: '{name_var}'")
            all_sf_result = client.client.table('salesforce_accounts').select('*').execute()
            if all_sf_result.data:
                partial_matches = []
                for sf_acc in all_sf_result.data:
                    if name_var.lower() in sf_acc.get('account_name', '').lower():
                        partial_matches.append(sf_acc)
                
                if partial_matches:
                    print(f"✅ Found {len(partial_matches)} partial match(es)")
                    for sf_acc in partial_matches:
                        if sf_acc not in salesforce_accounts:
                            salesforce_accounts.append(sf_acc)
                else:
                    print(f"❌ No partial matches found")
            else:
                print(f"❌ No Salesforce accounts in database")
        
        # Remove duplicates
        unique_accounts = []
        seen_ids = set()
        for account in salesforce_accounts:
            if account['salesforce_account_id'] not in seen_ids:
                unique_accounts.append(account)
                seen_ids.add(account['salesforce_account_id'])
        
        print(f"\n📊 Results Summary:")
        print(f"   Total unique Salesforce accounts found: {len(unique_accounts)}")
        
        if unique_accounts:
            print(f"\n⚡ Salesforce Accounts Found:")
            for j, sf_account in enumerate(unique_accounts, 1):
                print(f"   {j}. {sf_account['account_name']} ({sf_account['account_type']})")
                print(f"      📧 Email: {sf_account.get('email', 'N/A')}")
                print(f"      📞 Phone: {sf_account.get('phone', 'N/A')}")
                print(f"      📍 Address: {sf_account.get('address', 'N/A')}")
                print(f"      🔒 SSN/Tax ID: {sf_account.get('ssn_tax_id', 'N/A')}")
                print(f"      📋 Stage: {sf_account.get('stage', 'N/A')}")
        else:
            print(f"   ⚡ No Salesforce accounts found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_salesforce_search() 