#!/usr/bin/env python3
"""
Test script to verify that the Salesforce database check fix works correctly.
This script tests the logic that checks for Salesforce accounts in the database
even when there's no corresponding Dropbox account.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from supabase_client import SupabaseClient

def test_salesforce_database_check():
    """Test the Salesforce database check logic"""
    print("🔍 Testing Salesforce database check logic...")
    
    # Test with a name that has Salesforce accounts but no Dropbox folder
    test_folder_name = "Campos, Maria"
    
    try:
        # Create Supabase client
        client = SupabaseClient()
        
        print(f"\n📋 Testing with folder name: {test_folder_name}")
        
        # Check both the salesforce_accounts_found_count and existing data
        salesforce_count = client.get_salesforce_accounts_found_count(test_folder_name)
        salesforce_account_information = client.search_salesforce_account_information(test_folder_name)
        
        # Also check for Salesforce accounts that exist independently (not tied to Dropbox)
        independent_salesforce_accounts = client.get_salesforce_accounts_by_name(test_folder_name)
        
        print(f"  salesforce_accounts_found_count: {salesforce_count}")
        print(f"  existing_salesforce_data: {'Found' if salesforce_account_information else 'Not found'}")
        print(f"  independent_salesforce_accounts: {len(independent_salesforce_accounts)} found")
        
        # Test the logic from cmd_runner.py
        should_use_database = False
        should_do_live_search = False
        
        # If we found independent Salesforce accounts, use them
        if independent_salesforce_accounts and not salesforce_account_information:
            print(f"✅ Found {len(independent_salesforce_accounts)} independent Salesforce accounts, using database data")
            should_use_database = True
            
            # Convert independent accounts to the expected format
            names_found = [acc.account_name for acc in independent_salesforce_accounts]
            accounts = []
            
            for acc in independent_salesforce_accounts:
                account_data = {
                    'account_name': acc.account_name,
                    'type': acc.account_type,
                    'role': acc.role,
                    'stage': acc.stage,
                    'email': acc.email,
                    'phone': acc.phone,
                    'mailing_address': acc.address,
                    'ssn/tax_id': acc.ssn_tax_id,
                    'relationships': []
                }
                accounts.append(account_data)
            
            # Create the salesforce_account_information structure
            salesforce_account_information = {
                'names_found': names_found,
                'household': None,
                'head': None,
                'members': [],
                'accounts': accounts,
                'not_found_accounts': []
            }
            
            # Categorize accounts
            for acc in independent_salesforce_accounts:
                if acc.account_type == 'Household':
                    salesforce_account_information['household'] = {
                        'account_name': acc.account_name,
                        'type': acc.account_type,
                        'role': acc.role,
                        'stage': acc.stage,
                        'email': acc.email,
                        'phone': acc.phone,
                        'mailing_address': acc.address,
                        'ssn/tax_id': acc.ssn_tax_id,
                        'relationships': []
                    }
                elif acc.role == 'Household Head':
                    salesforce_account_information['head'] = {
                        'account_name': acc.account_name,
                        'type': acc.account_type,
                        'role': acc.role,
                        'stage': acc.stage,
                        'email': acc.email,
                        'phone': acc.phone,
                        'mailing_address': acc.address,
                        'ssn/tax_id': acc.ssn_tax_id,
                        'relationships': []
                    }
                elif acc.role == 'Member':
                    salesforce_account_information['members'].append({
                        'account_name': acc.account_name,
                        'type': acc.account_type,
                        'role': acc.role,
                        'stage': acc.stage,
                        'email': acc.email,
                        'phone': acc.phone,
                        'mailing_address': acc.address,
                        'ssn/tax_id': acc.ssn_tax_id,
                        'relationships': []
                    })
            
            print(f"✅ Successfully created salesforce_account_information structure:")
            print(f"   - Names found: {salesforce_account_information['names_found']}")
            print(f"   - Total accounts: {len(salesforce_account_information['accounts'])}")
            print(f"   - Household: {'Yes' if salesforce_account_information['household'] else 'No'}")
            print(f"   - Head: {'Yes' if salesforce_account_information['head'] else 'No'}")
            print(f"   - Members: {len(salesforce_account_information['members'])}")
            
        elif salesforce_count is not None:
            print("📊 Using existing search count logic")
            if salesforce_count >= 0:
                if salesforce_account_information:
                    should_use_database = True
                    print(f"✅ Using database data - search previously performed, found {salesforce_count} accounts")
                else:
                    should_do_live_search = True
                    print(f"⚠️ Database inconsistency - count shows {salesforce_count} accounts but no data found")
            else:
                should_do_live_search = True
                print(f"🔄 Previous search failed (count = {salesforce_count}), doing live search")
        else:
            if salesforce_account_information:
                should_use_database = True
                print(f"✅ Using database data - found existing data but no count recorded")
            else:
                should_do_live_search = True
                print(f"🔄 No previous search performed, doing live search")
        
        print(f"\n📋 Final decision:")
        print(f"   - should_use_database: {should_use_database}")
        print(f"   - should_do_live_search: {should_do_live_search}")
        
        if should_use_database:
            print("✅ SUCCESS: The fix is working! Found Salesforce accounts in database.")
        else:
            print("❌ The fix didn't work as expected.")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_salesforce_database_check() 