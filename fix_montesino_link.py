#!/usr/bin/env python3
"""
Script to fix the link between Maria Montesino's person record and her application file
"""

import sys
import os
sys.path.insert(0, 'src')

from supabase_client import SupabaseClient

def fix_montesino_link():
    """Fix the link between Maria Montesino's person record and her application file"""
    print("🔧 Fixing Maria Montesino's application file link...")
    
    try:
        client = SupabaseClient()
        
        # Get the application file for Montesino
        file_result = client.client.table('dropbox_account_application_files').select('*').eq('dropbox_account_id', 11).execute()
        if not file_result.data:
            print("❌ Application file not found")
            return False
            
        file = file_result.data[0]
        print(f"📄 Found application file: {file['file_name']} (ID: {file['id']})")
        print(f"   Current owner_id: {file.get('owner_id')}")
        
        # Find Maria Montesino's person record
        person_result = client.client.table('dropbox_account_application_info').select('*').eq('first_name', 'Maria').eq('last_name', 'Montesino').execute()
        if not person_result.data:
            print("❌ Maria Montesino person record not found")
            return False
            
        person = person_result.data[0]
        print(f"👤 Found Maria Montesino: ID {person['id']}")
        print(f"   Name: {person['first_name']} {person['last_name']}")
        print(f"   DOB: {person.get('date_of_birth')}")
        print(f"   Phone: {person.get('phone_number')}")
        print(f"   Email: {person.get('email_address')}")
        print(f"   Address: {person.get('mailing_address_street')}")
        print(f"   City/State/Zip: {person.get('mailing_address_city')}, {person.get('mailing_address_state')} {person.get('mailing_address_zip')}")
        
        # Update the application file to link to Maria
        # Since we can't use update directly, we'll delete and reinsert
        print("\n🔄 Updating application file link...")
        
        # Delete the current file record
        client.client.table('dropbox_account_application_files').delete().eq('id', file['id']).execute()
        
        # Reinsert with the correct owner_id
        new_file_data = {
            'file_name': file['file_name'],
            'file_path': file['file_path'],
            'application_type': file['application_type'],
            'status': file['status'],
            'owner_id': person['id'],  # Link to Maria
            'joint_owner_id': file.get('joint_owner_id'),
            'notes': file.get('notes', []),
            'extracted_text': file.get('extracted_text'),
            'processing_timestamp': file['processing_timestamp'],
            'ocr_confidence': file.get('ocr_confidence'),
            'lm_studio_model_used': file['lm_studio_model_used'],
            'processing_duration_seconds': file.get('processing_duration_seconds'),
            'dropbox_account_id': file['dropbox_account_id']
        }
        
        insert_result = client.client.table('dropbox_account_application_files').insert(new_file_data).execute()
        if insert_result.data:
            print("✅ Successfully updated application file link!")
            print(f"   New file ID: {insert_result.data[0]['id']}")
            print(f"   Owner ID: {insert_result.data[0]['owner_id']}")
            return True
        else:
            print("❌ Failed to reinsert application file")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing link: {e}")
        return False

if __name__ == "__main__":
    success = fix_montesino_link()
    if success:
        print("\n✅ Maria Montesino's application file is now properly linked!")
        print("💡 You can now run the search script to see all the detailed information.")
    else:
        print("\n❌ Failed to fix the link.") 