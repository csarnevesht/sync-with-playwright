#!/usr/bin/env python3
"""
Script to create new tables via REST API calls
"""

import os
import sys
import httpx
from dotenv import load_dotenv

def load_environment():
    """Load environment variables"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    print(f"Loading environment variables from {env_path}")
    load_dotenv(env_path)
    
    supabase_url = os.getenv('SUPABASE_URL')
    if not supabase_url:
        supabase_url = os.getenv('SUPABASE_PUBLIC_URL')
    if not supabase_url:
        supabase_url = 'http://localhost:8000'
    
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    if not supabase_key:
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    if not supabase_key:
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_key:
        raise ValueError("No Supabase key found!")
    
    return supabase_url, supabase_key

def create_tables():
    """Create tables by making REST API calls"""
    print("🏗️ Creating new tables via REST API...")
    
    base_url, api_key = load_environment()
    headers = {
        'apikey': api_key,
        'Content-Type': 'application/json'
    }
    
    print(f"Using Supabase URL: {base_url}")
    
    # First, let's try to create the tables by making a request that might trigger creation
    # We'll use the schema from our schema.py file
    
    # Create dropbox_account_application_info table
    print("Creating dropbox_account_application_info table...")
    try:
        # Try to insert a test record to see if table exists
        test_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'date_of_birth': '1990-01-01',
            'gender': 'Unknown',
            'mailing_address_street': '123 Test St',
            'mailing_address_city': 'Test City',
            'mailing_address_state': 'TS',
            'mailing_address_zip': '12345',
            'phone_number': '555-1234',
            'email_address': 'test@example.com',
            'ocr_method': 'test'
        }
        
        url = f"{base_url}/rest/v1/dropbox_account_application_info?select=*"
        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=test_data)
            if response.status_code == 201 or response.status_code == 200:
                print("✅ dropbox_account_application_info table created/accessed successfully")
                # Delete the test record
                if response.json():
                    test_id = response.json()[0]['id']
                    delete_url = f"{base_url}/rest/v1/dropbox_account_application_info?id=eq.{test_id}"
                    client.delete(delete_url, headers=headers)
            else:
                print(f"❌ Failed to create dropbox_account_application_info table: {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"❌ Error creating dropbox_account_application_info table: {e}")
    
    # Create dropbox_account_application_files table
    print("Creating dropbox_account_application_files table...")
    try:
        # Try to insert a test record to see if table exists
        test_data = {
            'file_name': 'test_file.pdf',
            'file_path': '/test/path',
            'application_type': 'Unknown',
            'status': 'Processed',
            'notes': [],
            'extracted_text': 'Test extracted text',
            'processing_timestamp': '2024-01-01T00:00:00Z',
            'ocr_confidence': 0.95,
            'lm_studio_model_used': 'test_model',
            'processing_duration_seconds': 1.5,
            'dropbox_account_id': 1
        }
        
        url = f"{base_url}/rest/v1/dropbox_account_application_files?select=*"
        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=test_data)
            if response.status_code == 201 or response.status_code == 200:
                print("✅ dropbox_account_application_files table created/accessed successfully")
                # Delete the test record
                if response.json():
                    test_id = response.json()[0]['id']
                    delete_url = f"{base_url}/rest/v1/dropbox_account_application_files?id=eq.{test_id}"
                    client.delete(delete_url, headers=headers)
            else:
                print(f"❌ Failed to create dropbox_account_application_files table: {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"❌ Error creating dropbox_account_application_files table: {e}")

def check_tables():
    """Check if the new tables exist"""
    print("🔍 Checking if new tables exist...")
    
    base_url, api_key = load_environment()
    headers = {
        'apikey': api_key,
        'Content-Type': 'application/json'
    }
    
    tables_to_check = [
        'dropbox_account_application_info',
        'dropbox_account_application_files'
    ]
    
    for table in tables_to_check:
        try:
            url = f"{base_url}/rest/v1/{table}?select=count"
            with httpx.Client() as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                print(f"✅ Table {table} exists")
        except Exception as e:
            print(f"❌ Table {table} does not exist: {e}")

if __name__ == "__main__":
    try:
        create_tables()
        check_tables()
    except Exception as e:
        print(f"❌ Table creation failed: {e}")
        sys.exit(1) 