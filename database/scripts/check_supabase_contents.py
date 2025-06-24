#!/usr/bin/env python3
"""
Script to check what's actually stored in the Supabase database.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from supabase_client import SupabaseClient

def check_supabase_contents():
    """Check what's stored in the Supabase database."""
    print("Checking Supabase database contents...")
    
    try:
        # Create Supabase client
        client = SupabaseClient()
        
        # Check dropbox accounts
        print("\n=== DROPBOX ACCOUNTS ===")
        try:
            accounts_result = client.client.table('dropbox_accounts').select('*').execute()
            if accounts_result.data:
                print(f"Found {len(accounts_result.data)} dropbox accounts:")
                for account in accounts_result.data:
                    print(f"  - {account['folder']} (ID: {account['id']})")
                    print(f"    Total files: {account.get('total_files', 'N/A')}")
                    print(f"    Processed files: {account.get('processed_files', 'N/A')}")
                    print(f"    Failed files: {account.get('failed_files', 'N/A')}")
                    print(f"    Processing timestamp: {account.get('processing_timestamp', 'N/A')}")
            else:
                print("No dropbox accounts found")
        except Exception as e:
            print(f"Error checking dropbox accounts: {e}")
        
        # Check application files
        print("\n=== APPLICATION FILES ===")
        try:
            files_result = client.client.table('dropbox_account_application_files').select('*').execute()
            if files_result.data:
                print(f"Found {len(files_result.data)} application files:")
                for file in files_result.data[:5]:  # Show first 5 files
                    print(f"  - {file['file_name']} (ID: {file['id']})")
                    print(f"    Account ID: {file['dropbox_account_id']}")
                    print(f"    Type: {file.get('application_type', 'N/A')}")
                    print(f"    Status: {file.get('status', 'N/A')}")
                    print(f"    Owner ID: {file.get('owner_id', 'N/A')}")
                    print(f"    Joint Owner ID: {file.get('joint_owner_id', 'N/A')}")
            else:
                print("No application files found")
        except Exception as e:
            print(f"Error checking application files: {e}")
        
        # Check person info
        print("\n=== PERSON INFO ===")
        try:
            persons_result = client.client.table('dropbox_account_application_info').select('*').execute()
            if persons_result.data:
                print(f"Found {len(persons_result.data)} person records:")
                for person in persons_result.data:
                    name = f"{person.get('first_name', '')} {person.get('last_name', '')}".strip()
                    if not name.strip():
                        name = f"Person ID {person['id']}"
                    
                    print(f"  - {name} (ID: {person['id']})")
                    print(f"    Date of birth: {person.get('date_of_birth', 'None')}")
                    print(f"    Gender: {person.get('gender', 'None')}")
                    
                    # Address information
                    street = person.get('mailing_address_street')
                    city = person.get('mailing_address_city')
                    state = person.get('mailing_address_state')
                    zip_code = person.get('mailing_address_zip')
                    
                    if street or city or state or zip_code:
                        print(f"    Address: {street or ''}")
                        if city or state or zip_code:
                            print(f"            {city or ''}, {state or ''} {zip_code or ''}")
                    else:
                        print(f"    Address: None")
                    
                    # Contact information
                    phone = person.get('phone_number')
                    email = person.get('email_address')
                    
                    if phone:
                        print(f"    Phone: {phone}")
                    if email:
                        print(f"    Email: {email}")
                    
                    # Processing information
                    ocr_method = person.get('ocr_method')
                    if ocr_method:
                        print(f"    OCR Method: {ocr_method}")
                    
                    print(f"    Created: {person.get('created_at', 'N/A')}")
                    print()
            else:
                print("No person records found")
        except Exception as e:
            print(f"Error checking person info: {e}")
            
    except Exception as e:
        print(f"Error checking Supabase contents: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_supabase_contents() 