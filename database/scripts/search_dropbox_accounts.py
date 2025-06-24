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
    """Search for Dropbox accounts by folder name."""
    print("🔍 Dropbox Account Search")
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
            print("5. (q) Exit")
            
            choice = input("\nEnter your choice (1-5 or shortcut): ").strip().lower()
            
            if choice in ['1', 'e']:
                search_exact(client)
            elif choice in ['2', 'p']:
                search_partial(client)
            elif choice in ['3', 'l']:
                list_all_accounts(client)
            elif choice in ['4', 's']:
                show_statistics(client)
            elif choice in ['5', 'q']:
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
        result = client.client.table('dropbox_accounts').select('*').eq('folder', folder_name).execute()
        
        if result.data:
            print(f"\n✅ Found {len(result.data)} exact match(es):")
            display_accounts(client, result.data)
        else:
            print(f"\n❌ No exact match found for: '{folder_name}'")
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
        # Get all accounts and filter manually since ilike may not be available
        print("🔍 Searching all accounts...")
        all_result = client.client.table('dropbox_accounts').select('*').execute()
        
        if all_result.data:
            # Filter results manually for case-insensitive partial matching
            matches = [account for account in all_result.data 
                      if search_term.lower() in account.get('folder', '').lower()]
            
            if matches:
                print(f"\n✅ Found {len(matches)} match(es) for '{search_term}':")
                display_accounts(client, matches)
            else:
                print(f"\n❌ No matches found for: '{search_term}'")
                print(f"💡 Searched through {len(all_result.data)} total accounts.")
        else:
            print("❌ No accounts found in database.")
            
    except Exception as e:
        print(f"❌ Error searching: {e}")
        import traceback
        traceback.print_exc()

def list_all_accounts(client):
    """List first 20 accounts."""
    try:
        result = client.client.table('dropbox_accounts').select('*').limit(20).order('folder').execute()
        
        if result.data:
            print(f"\n📋 First 20 Dropbox accounts (sorted by folder name):")
            display_accounts(client, result.data)
        else:
            print("❌ No accounts found.")
            
    except Exception as e:
        print(f"❌ Error listing accounts: {e}")

def show_statistics(client):
    """Show account statistics."""
    try:
        # Get total count
        total_result = client.client.table('dropbox_accounts').select('id', count='exact').execute()
        total_accounts = total_result.count if hasattr(total_result, 'count') else len(total_result.data)
        
        # Get accounts with files
        with_files_result = client.client.table('dropbox_accounts').select('id').gt('total_files', 0).execute()
        accounts_with_files = len(with_files_result.data)
        
        # Get processed accounts
        processed_result = client.client.table('dropbox_accounts').select('id').gt('processed_files', 0).execute()
        processed_accounts = len(processed_result.data)
        
        print(f"\n📊 Account Statistics:")
        print(f"   Total accounts: {total_accounts}")
        print(f"   Accounts with files: {accounts_with_files}")
        print(f"   Accounts with processed files: {processed_accounts}")
        print(f"   Accounts without files: {total_accounts - accounts_with_files}")
        
        # Show some examples
        if total_accounts > 0:
            print(f"\n📝 Sample account names:")
            sample_result = client.client.table('dropbox_accounts').select('folder').limit(5).execute()
            for i, account in enumerate(sample_result.data, 1):
                print(f"   {i}. {account['folder']}")
                
    except Exception as e:
        print(f"❌ Error getting statistics: {e}")

def display_accounts(client, accounts):
    """Display account information in a formatted way."""
    for i, account in enumerate(accounts, 1):
        print(f"\n{i}. {account['folder']} (ID: {account['id']})")
        print(f"   📁 Total files: {account.get('total_files', 0)}")
        print(f"   ✅ Processed files: {account.get('processed_files', 0)}")
        print(f"   ❌ Failed files: {account.get('failed_files', 0)}")
        
        # Show person info if available
        if account.get('total_files', 0) > 0:
            try:
                # Get related application files
                files_result = client.client.table('dropbox_account_application_files').select('*').eq('dropbox_account_id', account['id']).execute()
                
                if files_result.data:
                    print(f"   📄 Application files:")
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

if __name__ == '__main__':
    search_dropbox_accounts() 