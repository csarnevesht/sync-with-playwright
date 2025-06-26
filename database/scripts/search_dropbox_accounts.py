#!/usr/bin/env python3
"""
Search Dropbox Accounts Script

This script allows searching for specific Dropbox account folder names
and displays detailed information about matching accounts.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from supabase_client import SupabaseClient

def search_dropbox_accounts():
    """Search for Dropbox accounts by folder name and show related Salesforce information."""
    print("🔍 Dropbox & Salesforce Account Search")
    print("=" * 50)
    
    try:
        # Create Supabase client
        client = SupabaseClient()
        
        while True:
            print("\nSearch options:")
            print("1. (e) Search by exact folder name")
            print("2. (p) Search by partial folder name")
            print("3. (l) List all accounts (first 20)")
            print("4. (s) Show account statistics")
            print("5. (n) List accounts without client list info")
            print("6. (q) Exit")
            
            choice = input("\nEnter your choice (1-6 or shortcut): ").strip().lower()
            
            if choice in ['1', 'e']:
                search_exact(client)
            elif choice in ['2', 'p']:
                search_partial(client)
            elif choice in ['3', 'l']:
                list_all_accounts(client)
            elif choice in ['4', 's']:
                show_statistics(client)
            elif choice in ['5', 'n']:
                list_accounts_without_client_list(client)
            elif choice in ['6', 'q']:
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please try again.")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def search_exact(client):
    """Search for exact folder name match."""
    folder_name = input("Enter exact folder name to search: ").strip()
    
    if not folder_name:
        print("❌ Please enter a folder name.")
        return
    
    try:
        # Search Dropbox accounts
        result = client.client.table('dropbox_accounts').select('*').eq('folder', folder_name).execute()
        
        # Search Salesforce accounts
        sf_result = client.client.table('salesforce_accounts').select('*').eq('account_name', folder_name).execute()
        
        # Also search for name variations in Salesforce
        name_variations = [
            folder_name.replace(', ', ' '),  # "Montesino, Maria" -> "Montesino Maria"
            folder_name.split(', ')[1] + ' ' + folder_name.split(', ')[0] if ', ' in folder_name else None  # "Montesino, Maria" -> "Maria Montesino"
        ]
        name_variations = [name for name in name_variations if name]
        
        additional_sf_accounts = []
        for name_var in name_variations:
            var_result = client.client.table('salesforce_accounts').select('*').eq('account_name', name_var).execute()
            if var_result.data:
                for sf_acc in var_result.data:
                    if sf_acc not in sf_result.data:
                        additional_sf_accounts.append(sf_acc)
        
        # Combine all Salesforce results
        all_sf_accounts = sf_result.data + additional_sf_accounts
        
        print(f"\n🔍 Search Results for: '{folder_name}'")
        print("=" * 60)
        
        # Display Dropbox results
        if result.data:
            print(f"\n📁 Dropbox Accounts ({len(result.data)} match(es)):")
            display_accounts(client, result.data)
        else:
            print(f"\n📁 Dropbox Accounts: No matches found")
        
        # Display Salesforce results
        if all_sf_accounts:
            print(f"\n⚡ Salesforce Accounts ({len(all_sf_accounts)} match(es)):")
            display_salesforce_accounts(client, all_sf_accounts)
        else:
            print(f"\n⚡ Salesforce Accounts: No matches found")
            
        if not result.data and not all_sf_accounts:
            print(f"\n💡 No matches found in either Dropbox or Salesforce for: '{folder_name}'")
            print("💡 Try using partial search instead.")
            
    except Exception as e:
        print(f"❌ Error searching: {e}")

def search_partial(client):
    """Search for partial folder name match."""
    search_term = input("Enter partial folder name to search: ").strip()
    
    if not search_term:
        print("❌ Please enter a search term.")
        return
    
    try:
        print("🔍 Searching all accounts...")
        
        # Search Dropbox accounts
        all_result = client.client.table('dropbox_accounts').select('*').execute()
        dropbox_matches = []
        if all_result.data:
            # Filter results manually for case-insensitive partial matching
            dropbox_matches = [account for account in all_result.data 
                              if search_term.lower() in account.get('folder', '').lower()]
        
        # Search Salesforce accounts
        all_sf_result = client.client.table('salesforce_accounts').select('*').execute()
        salesforce_matches = []
        if all_sf_result.data:
            # Filter results manually for case-insensitive partial matching
            salesforce_matches = [account for account in all_sf_result.data 
                                 if search_term.lower() in account.get('account_name', '').lower()]
        
        print(f"\n🔍 Search Results for: '{search_term}'")
        print("=" * 60)
        
        # Display Dropbox results
        if dropbox_matches:
            print(f"\n📁 Dropbox Accounts ({len(dropbox_matches)} match(es)):")
            display_accounts(client, dropbox_matches)
        else:
            print(f"\n📁 Dropbox Accounts: No matches found")
        
        # Display Salesforce results
        if salesforce_matches:
            print(f"\n⚡ Salesforce Accounts ({len(salesforce_matches)} match(es)):")
            display_salesforce_accounts(client, salesforce_matches)
        else:
            print(f"\n⚡ Salesforce Accounts: No matches found")
        
        if not dropbox_matches and not salesforce_matches:
            print(f"\n❌ No matches found for: '{search_term}'")
            print(f"💡 Searched through {len(all_result.data) if all_result.data else 0} Dropbox accounts and {len(all_sf_result.data) if all_sf_result.data else 0} Salesforce accounts.")
            
    except Exception as e:
        print(f"❌ Error searching: {e}")
        import traceback
        traceback.print_exc()

def list_all_accounts(client):
    """List first 20 accounts with Dropbox and Salesforce information."""
    try:
        result = client.client.table('dropbox_accounts').select('*').limit(20).execute()
        
        if result.data:
            # Sort by folder name in Python
            sorted_data = sorted(result.data, key=lambda x: x['folder'])
            print(f"\n📋 First 20 Dropbox accounts (sorted by folder name):")
            display_accounts(client, sorted_data)
        else:
            print("❌ No accounts found.")
            
    except Exception as e:
        print(f"❌ Error listing accounts: {e}")

def show_statistics(client):
    """Show account statistics."""
    try:
        # Get Dropbox statistics - get all records and count manually for local client compatibility
        total_result = client.client.table('dropbox_accounts').select('*').execute()
        total_accounts = len(total_result.data) if total_result.data else 0
        
        # Get accounts with files
        with_files_result = client.client.table('dropbox_accounts').select('*').execute()
        accounts_with_files = 0
        if with_files_result.data:
            accounts_with_files = len([acc for acc in with_files_result.data if acc.get('total_account_application_files', 0) > 0])
        
        # Get processed accounts
        processed_accounts = 0
        if with_files_result.data:
            processed_accounts = len([acc for acc in with_files_result.data if acc.get('processed_account_application_files', 0) > 0])
        
        print(f"\n📊 Dropbox Account Statistics:")
        print(f"   Total accounts: {total_accounts}")
        print(f"   Accounts with files: {accounts_with_files}")
        print(f"   Accounts with processed files: {processed_accounts}")
        print(f"   Accounts without files: {total_accounts - accounts_with_files}")
        
        # Get Salesforce statistics - get all records and count manually
        sf_total_result = client.client.table('salesforce_accounts').select('*').execute()
        sf_total_accounts = len(sf_total_result.data) if sf_total_result.data else 0
        
        # Get Salesforce accounts by type
        sf_contacts = 0
        sf_households = 0
        if sf_total_result.data:
            sf_contacts = len([acc for acc in sf_total_result.data if acc.get('account_type') == 'Contact'])
            sf_households = len([acc for acc in sf_total_result.data if acc.get('account_type') == 'Household'])
        
        # Get household statistics
        hh_total_result = client.client.table('salesforce_households').select('*').execute()
        hh_total = len(hh_total_result.data) if hh_total_result.data else 0
        
        hh_members_result = client.client.table('salesforce_household_members').select('*').execute()
        hh_members = len(hh_members_result.data) if hh_members_result.data else 0
        
        print(f"\n⚡ Salesforce Account Statistics:")
        print(f"   Total Salesforce accounts: {sf_total_accounts}")
        print(f"   Contacts: {sf_contacts}")
        print(f"   Households: {sf_households}")
        print(f"   Total households: {hh_total}")
        print(f"   Household members: {hh_members}")
        
        # Show some examples
        if total_accounts > 0:
            print(f"\n📝 Sample Dropbox account names:")
            sample_result = client.client.table('dropbox_accounts').select('folder').execute()
            if sample_result.data:
                for i, account in enumerate(sample_result.data[:5], 1):  # Limit to 5
                    print(f"   {i}. {account['folder']}")
        
        if sf_total_accounts > 0:
            print(f"\n⚡ Sample Salesforce account names:")
            sf_sample_result = client.client.table('salesforce_accounts').select('account_name,account_type').execute()
            if sf_sample_result.data:
                for i, account in enumerate(sf_sample_result.data[:5], 1):  # Limit to 5
                    print(f"   {i}. {account['account_name']} ({account['account_type']})")
                
    except Exception as e:
        print(f"❌ Error getting statistics: {e}")
        import traceback
        traceback.print_exc()

def list_accounts_without_client_list(client):
    """List all accounts that don't have client list file info."""
    try:
        print("\n🔍 Finding accounts without client list info...")
        
        # Get all dropbox accounts
        all_result = client.client.table('dropbox_accounts').select('*').execute()
        
        if not all_result.data:
            print("❌ No accounts found.")
            return
        
        # Get all client list info
        client_list_result = client.client.table('dropbox_account_client_list_info').select('*').execute()
        client_list_account_ids = set()
        
        if client_list_result.data:
            client_list_account_ids = {info['dropbox_account_id'] for info in client_list_result.data}
        
        # Find accounts without client list info
        accounts_without_client_list = []
        for account in all_result.data:
            if account['id'] not in client_list_account_ids:
                accounts_without_client_list.append(account)
        
        print(f"\n📋 Accounts without client list info ({len(accounts_without_client_list)} found):")
        print("=" * 60)
        
        if accounts_without_client_list:
            # Sort by folder name
            sorted_accounts = sorted(accounts_without_client_list, key=lambda x: x['folder'])
            
            for i, account in enumerate(sorted_accounts, 1):
                folder_name = account['folder']
                account_id = account['id']
                total_files = account.get('total_account_application_files', 0)
                processed_files = account.get('processed_account_application_files', 0)
                
                print(f"{i}. {folder_name} (ID: {account_id})")
                print(f"   📁 Files: {total_files} total, {processed_files} processed")
                
                # Check if they have application files
                if total_files > 0:
                    print(f"   ✅ Has application files")
                else:
                    print(f"   ❌ No application files")
                
                print()
        else:
            print("✅ All accounts have client list info!")
            
    except Exception as e:
        print(f"❌ Error listing accounts without client list: {e}")
        import traceback
        traceback.print_exc()

def display_accounts(client, accounts):
    """Display account information in a formatted way."""
    for i, account in enumerate(accounts, 1):
        print(f"\n{i}. {account['folder']} (ID: {account['id']})")
        # Show Salesforce account information if available
        try:
            # Search for Salesforce accounts by name variations
            folder_name = account['folder']
            name_variations = [
                folder_name,
                folder_name.replace(', ', ' '),  # "Montesino, Maria" -> "Montesino Maria"
                folder_name.split(', ')[1] + ' ' + folder_name.split(', ')[0] if ', ' in folder_name else None  # "Montesino, Maria" -> "Maria Montesino"
            ]
            name_variations = [name for name in name_variations if name]
            
            salesforce_accounts = []
            for name_var in name_variations:
                # Search for exact matches first
                sf_result = client.client.table('salesforce_accounts').select('*').eq('account_name', name_var).execute()
                if sf_result.data:
                    salesforce_accounts.extend(sf_result.data)
                
                # Search for partial matches using contains (case-insensitive)
                try:
                    sf_partial_result = client.client.table('salesforce_accounts').select('*').contains('account_name', [name_var]).execute()
                    if sf_partial_result.data:
                        for sf_acc in sf_partial_result.data:
                            if sf_acc not in salesforce_accounts:
                                salesforce_accounts.append(sf_acc)
                except:
                    # Fallback: get all accounts and filter manually
                    all_sf_result = client.client.table('salesforce_accounts').select('*').execute()
                    if all_sf_result.data:
                        for sf_acc in all_sf_result.data:
                            if name_var.lower() in sf_acc.get('account_name', '').lower():
                                if sf_acc not in salesforce_accounts:
                                    salesforce_accounts.append(sf_acc)
            
            if salesforce_accounts:
                print(f"   ⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡")
                print(f"   ⚡ **SALESFORCE ACCOUNT INFORMATION** 📊")
                print(f"   ⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡")
                for j, sf_account in enumerate(salesforce_accounts, 1):
                    print(f"      {j}. {sf_account['account_name']} ({sf_account['account_type']})")
                    print(f"         📧 Email: {sf_account.get('email', 'N/A')}")
                    print(f"         📞 Phone: {sf_account.get('phone', 'N/A')}")
                    print(f"         📍 Address: {sf_account.get('address', 'N/A')}")
                    print(f"         🔒 SSN/Tax ID: {sf_account.get('ssn_tax_id', 'N/A')}")
                    print(f"         📋 Stage: {sf_account.get('stage', 'N/A')}")
                    
                    # Show household information if this is a household
                    if sf_account['account_type'] == 'Household':
                        household_result = client.client.table('salesforce_households').select('*').eq('salesforce_household_id', sf_account['salesforce_account_id']).execute()
                        if household_result.data:
                            household = household_result.data[0]
                            print(f"         🏠 Household Head ID: {household.get('household_head_id', 'N/A')}")
                            
                            # Show household members
                            members_result = client.client.table('salesforce_household_members').select('*').eq('household_id', sf_account['salesforce_account_id']).execute()
                            if members_result.data:
                                print(f"         👥 Household Members ({len(members_result.data)}):")
                                for member in members_result.data:
                                    print(f"            - {member.get('member_id', 'N/A')} ({member.get('role', 'N/A')})")
                    
                    # Show relationships if this is a contact
                    if sf_account['account_type'] == 'Contact':
                        # Check if this contact is a household head
                        head_result = client.client.table('salesforce_households').select('*').eq('household_head_id', sf_account['salesforce_account_id']).execute()
                        if head_result.data:
                            print(f"         👑 Household Head for: {head_result.data[0].get('household_name', 'N/A')}")
                        
                        # Check if this contact is a household member
                        member_result = client.client.table('salesforce_household_members').select('*').eq('member_id', sf_account['salesforce_account_id']).execute()
                        if member_result.data:
                            print(f"         👥 Household Member of: {member_result.data[0].get('household_id', 'N/A')}")
                    
                    print(f"         🕒 Created: {sf_account.get('created_at', 'N/A')}")
                    print(f"         🔄 Updated: {sf_account.get('updated_at', 'N/A')}")
            else:
                print(f"   ⚡ Salesforce Accounts: None found")
                
        except Exception as e:
            print(f"   ⚡ Salesforce Accounts: Error retrieving data - {e}")
            import traceback
            traceback.print_exc()
        
        # Show Dropbox account information (client list and/or application files)
        has_client_list = False
        has_application_files = False
        
        # Check if client list info exists
        try:
            client_list_result = client.client.table('dropbox_account_client_list_info').select('*').eq('dropbox_account_id', account['id']).execute()
            has_client_list = bool(client_list_result.data)
        except:
            pass
        
        # Check if application files exist
        has_application_files = account.get('total_account_application_files', 0) > 0
        
        # Show Dropbox account information if either exists
        if has_client_list or has_application_files:
            print(f"   📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦")
            print(f"   📦 **DROPBOX ACCOUNT INFORMATION** 📊")
            print(f"   📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦")
            
            # Show client list info if available
            if has_client_list:
                print(f"   📄 **Source: dropbox_client_list**")
                for client_list_info in client_list_result.data:
                    print(f"   👤 Account Name: {client_list_info.get('account_name', 'N/A')}")
                    print(f"   👤 First Name: {client_list_info.get('first_name', 'N/A')}")
                    print(f"   👤 Middle Name: {client_list_info.get('middle_name', 'N/A')}")
                    print(f"   👤 Last Name: {client_list_info.get('last_name', 'N/A')}")
                    print(f"   🎂 Birthdate: {client_list_info.get('birthdate', 'N/A')}")
                    print(f"   ♂️♀️ Gender: {client_list_info.get('gender', 'N/A')}")
                    print(f"   📞 Phone: {client_list_info.get('phone', 'N/A')}")
                    print(f"   📍 Address: {client_list_info.get('address', 'N/A')}")
                    print(f"   📍 City: {client_list_info.get('city', 'N/A')}")
                    print(f"   📍 State: {client_list_info.get('state', 'N/A')}")
                    print(f"   📍 ZIP: {client_list_info.get('zip_code', 'N/A')}")
                    print(f"   📧 Email: {client_list_info.get('email', 'N/A')}")
                    print(f"   ℹ️ Additional Info: {client_list_info.get('additional_info', 'N/A')}")
                    print(f"   ✅ Match Status: {client_list_info.get('match_status', 'N/A')}")
                    print(f"   🕒 Created: {client_list_info.get('created_at', 'N/A')}")
                    print(f"   🔄 Updated: {client_list_info.get('updated_at', 'N/A')}")
            
            # Show application files info if available
            if has_application_files:
                try:
                    # Get related application files
                    files_result = client.client.table('dropbox_account_application_files').select('*').eq('dropbox_account_id', account['id']).execute()
                    
                    if files_result.data:
                        print(f"   📄 **Source: dropbox_application_files**")
                        for file in files_result.data:
                            print(f"      - {file['file_name']} ({file.get('application_type', 'Unknown')})")
                            
                            # Show detailed owner info if available
                            if file.get('owner_id'):
                                owner_result = client.client.table('dropbox_account_application_info').select('*').eq('id', file['owner_id']).execute()
                                if owner_result.data:
                                    owner = owner_result.data[0]
                                    print(f"        👤 Owner Details:")
                                    print(f"          Name: {owner.get('first_name', '')} {owner.get('last_name', '')}".strip())
                                    print(f"          Birthdate: {owner.get('date_of_birth', 'N/A')}")
                                    print(f"          Gender: {owner.get('gender', 'N/A')}")
                                    print(f"          Phone: {owner.get('phone_number', 'N/A')}")
                                    print(f"          Email: {owner.get('email_address', 'N/A')}")
                                    print(f"          Address: {owner.get('mailing_address_street', 'N/A')}")
                                    if owner.get('mailing_address_city') or owner.get('mailing_address_state') or owner.get('mailing_address_zip'):
                                        address_parts = []
                                        if owner.get('mailing_address_city'):
                                            address_parts.append(owner['mailing_address_city'])
                                        if owner.get('mailing_address_state'):
                                            address_parts.append(owner['mailing_address_state'])
                                        if owner.get('mailing_address_zip'):
                                            address_parts.append(owner['mailing_address_zip'])
                                        print(f"          City/State/Zip: {', '.join(address_parts)}")
                                    print(f"          OCR Method: {owner.get('ocr_method', 'N/A')}")
                            
                            # Show detailed joint owner info if available
                            if file.get('joint_owner_id'):
                                joint_result = client.client.table('dropbox_account_application_info').select('*').eq('id', file['joint_owner_id']).execute()
                                if joint_result.data:
                                    joint = joint_result.data[0]
                                    print(f"        👥 Joint Owner Details:")
                                    print(f"          Name: {joint.get('first_name', '')} {joint.get('last_name', '')}".strip())
                                    print(f"          Birthdate: {joint.get('date_of_birth', 'N/A')}")
                                    print(f"          Gender: {joint.get('gender', 'N/A')}")
                                    print(f"          Phone: {joint.get('phone_number', 'N/A')}")
                                    print(f"          Email: {joint.get('email_address', 'N/A')}")
                                    print(f"          Address: {joint.get('mailing_address_street', 'N/A')}")
                                    if joint.get('mailing_address_city') or joint.get('mailing_address_state') or joint.get('mailing_address_zip'):
                                        address_parts = []
                                        if joint.get('mailing_address_city'):
                                            address_parts.append(joint['mailing_address_city'])
                                        if joint.get('mailing_address_state'):
                                            address_parts.append(joint['mailing_address_state'])
                                        if joint.get('mailing_address_zip'):
                                            address_parts.append(joint['mailing_address_zip'])
                                        print(f"          City/State/Zip: {', '.join(address_parts)}")
                                    print(f"          OCR Method: {joint.get('ocr_method', 'N/A')}")
                            
                            # Show file processing details
                            if file.get('processing_timestamp'):
                                print(f"        📅 Processed: {file['processing_timestamp']}")
                            if file.get('ocr_confidence'):
                                print(f"        🎯 OCR Confidence: {file['ocr_confidence']}%")
                            if file.get('lm_studio_model_used'):
                                print(f"        🤖 Model Used: {file['lm_studio_model_used']}")
                            if file.get('processing_duration_seconds'):
                                print(f"        ⏱️  Processing Time: {file['processing_duration_seconds']} seconds")
                    
                except Exception as e:
                    print(f"   ⚠️  Error getting file details: {e}")
        
        print(f"   🕒 Last processed: {account.get('processing_timestamp', 'Never')}")

def display_salesforce_accounts(client, salesforce_accounts):
    """Display Salesforce account information in a formatted way."""
    for i, sf_account in enumerate(salesforce_accounts, 1):
        print(f"\n{i}. {sf_account['account_name']} (ID: {sf_account['id']})")
        print(f"   📋 Account Type: {sf_account['account_type']}")
        print(f"   📧 Email: {sf_account.get('email', 'N/A')}")
        print(f"   📞 Phone: {sf_account.get('phone', 'N/A')}")
        print(f"   📍 Address: {sf_account.get('address', 'N/A')}")
        print(f"   🔒 SSN/Tax ID: {sf_account.get('ssn_tax_id', 'N/A')}")
        print(f"   📋 Stage: {sf_account.get('stage', 'N/A')}")
        print(f"   📅 Created: {sf_account.get('created_at', 'N/A')}")
        
        # Show household information if this is a household
        if sf_account['account_type'] == 'Household':
            try:
                household_result = client.client.table('salesforce_households').select('*').eq('salesforce_household_id', sf_account['salesforce_account_id']).execute()
                if household_result.data:
                    household = household_result.data[0]
                    print(f"   🏠 Household Head ID: {household.get('household_head_id', 'N/A')}")
                    
                    # Show household members
                    members_result = client.client.table('salesforce_household_members').select('*').eq('household_id', sf_account['salesforce_account_id']).execute()
                    if members_result.data:
                        print(f"   👥 Household Members ({len(members_result.data)}):")
                        for member in members_result.data:
                            print(f"      - {member.get('member_id', 'N/A')} ({member.get('role', 'N/A')})")
            except Exception as e:
                print(f"   ⚠️ Error fetching household data: {e}")
        
        # Show relationships if this is a contact
        if sf_account['account_type'] == 'Contact':
            try:
                # Check if this contact is a household head
                head_result = client.client.table('salesforce_households').select('*').eq('household_head_id', sf_account['salesforce_account_id']).execute()
                if head_result.data:
                    print(f"   👑 Household Head for: {head_result.data[0].get('household_name', 'N/A')}")
                
                # Check if this contact is a household member
                member_result = client.client.table('salesforce_household_members').select('*').eq('member_id', sf_account['salesforce_account_id']).execute()
                if member_result.data:
                    print(f"   👥 Household Member of: {member_result.data[0].get('household_id', 'N/A')}")
            except Exception as e:
                print(f"   ⚠️ Error fetching relationship data: {e}")
        
        print()  # Add spacing between accounts

if __name__ == '__main__':
    search_dropbox_accounts() 