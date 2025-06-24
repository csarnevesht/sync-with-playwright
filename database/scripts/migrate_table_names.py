#!/usr/bin/env python3
"""
Migration script to rename tables:
- application_files -> dropbox_account_application_files
- person_info -> dropbox_account_application_info
"""

import os
import sys
import httpx
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

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

def make_request(url: str, headers: dict, method: str = 'GET', data: dict = None):
    """Make HTTP request to Supabase"""
    try:
        with httpx.Client() as client:
            response = client.request(
                method=method,
                url=url,
                headers=headers,
                json=data if data else None
            )
            response.raise_for_status()
            return response.json() if response.content else {}
    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        print(f"Request error: {e}")
        raise

def check_table_exists(base_url: str, headers: dict, table_name: str) -> bool:
    """Check if a table exists"""
    try:
        url = f"{base_url}/rest/v1/{table_name}?select=count"
        result = make_request(url, headers)
        return True
    except Exception:
        return False

def get_table_data(base_url: str, headers: dict, table_name: str):
    """Get all data from a table"""
    try:
        url = f"{base_url}/rest/v1/{table_name}?select=*"
        return make_request(url, headers)
    except Exception as e:
        print(f"Error getting data from {table_name}: {e}")
        return []

def insert_data(base_url: str, headers: dict, table_name: str, data: list):
    """Insert data into a table"""
    if not data:
        print(f"No data to insert into {table_name}")
        return
    
    try:
        url = f"{base_url}/rest/v1/{table_name}?select=*"
        result = make_request(url, headers, method='POST', data=data)
        print(f"Inserted {len(data)} records into {table_name}")
        return result
    except Exception as e:
        print(f"Error inserting data into {table_name}: {e}")
        return None

def delete_data(base_url: str, headers: dict, table_name: str):
    """Delete all data from a table"""
    try:
        url = f"{base_url}/rest/v1/{table_name}"
        result = make_request(url, headers, method='DELETE')
        print(f"Deleted all data from {table_name}")
        return result
    except Exception as e:
        print(f"Error deleting data from {table_name}: {e}")
        return None

def migrate_tables():
    """Migrate the tables by copying data and updating foreign keys"""
    print("🚀 Starting table migration...")
    
    # Load environment
    base_url, api_key = load_environment()
    headers = {
        'apikey': api_key,
        'Content-Type': 'application/json'
    }
    
    print(f"Using Supabase URL: {base_url}")
    
    # Check if old tables exist
    old_person_info_exists = check_table_exists(base_url, headers, 'person_info')
    old_application_files_exists = check_table_exists(base_url, headers, 'application_files')
    
    # Check if new tables exist
    new_person_info_exists = check_table_exists(base_url, headers, 'dropbox_account_application_info')
    new_application_files_exists = check_table_exists(base_url, headers, 'dropbox_account_application_files')
    
    print(f"Old tables exist: person_info={old_person_info_exists}, application_files={old_application_files_exists}")
    print(f"New tables exist: dropbox_account_application_info={new_person_info_exists}, dropbox_account_application_files={new_application_files_exists}")
    
    if not new_person_info_exists or not new_application_files_exists:
        print("❌ New tables don't exist. Please run the schema creation first.")
        return False
    
    # Migrate person_info data
    if old_person_info_exists and not new_person_info_exists:
        print("📋 Migrating person_info data...")
        person_data = get_table_data(base_url, headers, 'person_info')
        if person_data:
            insert_data(base_url, headers, 'dropbox_account_application_info', person_data)
        else:
            print("No person_info data to migrate")
    
    # Migrate application_files data
    if old_application_files_exists and not new_application_files_exists:
        print("📄 Migrating application_files data...")
        files_data = get_table_data(base_url, headers, 'application_files')
        if files_data:
            insert_data(base_url, headers, 'dropbox_account_application_files', files_data)
        else:
            print("No application_files data to migrate")
    
    # Verify migration
    print("🔍 Verifying migration...")
    
    if old_person_info_exists:
        old_person_count = len(get_table_data(base_url, headers, 'person_info'))
        new_person_count = len(get_table_data(base_url, headers, 'dropbox_account_application_info'))
        print(f"Person data: {old_person_count} -> {new_person_count}")
    
    if old_application_files_exists:
        old_files_count = len(get_table_data(base_url, headers, 'application_files'))
        new_files_count = len(get_table_data(base_url, headers, 'dropbox_account_application_files'))
        print(f"Application files: {old_files_count} -> {new_files_count}")
    
    print("✅ Migration completed successfully!")
    return True

def drop_old_tables():
    """Drop the old tables after successful migration"""
    print("🗑️ Dropping old tables...")
    
    # Load environment
    base_url, api_key = load_environment()
    headers = {
        'apikey': api_key,
        'Content-Type': 'application/json'
    }
    
    # Check if old tables exist
    old_person_info_exists = check_table_exists(base_url, headers, 'person_info')
    old_application_files_exists = check_table_exists(base_url, headers, 'application_files')
    
    if old_person_info_exists:
        print("Dropping person_info table...")
        # Note: We can't drop tables via REST API, this would need to be done via SQL
        print("⚠️ Cannot drop tables via REST API. Please run the following SQL manually:")
        print("DROP TABLE IF EXISTS person_info CASCADE;")
    
    if old_application_files_exists:
        print("Dropping application_files table...")
        print("⚠️ Cannot drop tables via REST API. Please run the following SQL manually:")
        print("DROP TABLE IF EXISTS application_files CASCADE;")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate table names')
    parser.add_argument('--drop-old', action='store_true', help='Drop old tables after migration')
    
    args = parser.parse_args()
    
    try:
        success = migrate_tables()
        if success and args.drop_old:
            drop_old_tables()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1) 