#!/usr/bin/env python3
"""
Script to execute DDL statements to drop legacy tables
"""

import os
import sys
import httpx
from dotenv import load_dotenv

def load_environment():
    """Load environment variables"""
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
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

def execute_ddl():
    """Execute DDL to drop legacy tables"""
    print("🗑️ Executing DDL to drop legacy tables...")
    
    # Load environment
    base_url, api_key = load_environment()
    headers = {
        'apikey': api_key,
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    print(f"Using Supabase URL: {base_url}")
    
    # DDL to drop tables
    ddl_sql = """
    -- Drop legacy tables first
    DROP TABLE IF EXISTS dropbox_account_applications CASCADE;
    DROP TABLE IF EXISTS applications CASCADE;
    DROP TABLE IF EXISTS household_members CASCADE;
    DROP TABLE IF EXISTS dropbox_account_household_members CASCADE;
    
    -- Drop current tables (in dependency order)
    DROP TABLE IF EXISTS dropbox_account_application_files CASCADE;
    DROP TABLE IF EXISTS dropbox_account_application_info CASCADE;
    DROP TABLE IF EXISTS dropbox_accounts CASCADE;
    """
    
    try:
        # Try using the SQL endpoint
        url = f"{base_url}/rest/v1/rpc/exec_sql"
        data = {"sql": ddl_sql}
        
        print("Executing DDL via RPC...")
        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=data)
            response.raise_for_status()
            print("✅ DDL executed successfully!")
            return True
            
    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e.response.status_code} - {e.response.text}")
        print("\n💡 Trying alternative approach...")
        
        # Try direct table deletion via REST API
        try:
            # Legacy tables to drop
            legacy_tables = ['dropbox_account_applications', 'applications', 'household_members', 'dropbox_account_household_members']
            
            # Current tables to drop (in dependency order)
            current_tables = ['dropbox_account_application_files', 'dropbox_account_application_info', 'dropbox_accounts']
            
            tables_to_drop = legacy_tables + current_tables
            
            for table in tables_to_drop:
                print(f"Dropping table: {table}")
                url = f"{base_url}/rest/v1/{table}"
                
                with httpx.Client() as client:
                    # Try to delete the table by dropping all rows first
                    response = client.delete(url, headers=headers)
                    if response.status_code == 200:
                        print(f"✅ Cleared table: {table}")
                    else:
                        print(f"⚠️  Could not clear table: {table} - {response.status_code}")
            
            print("\n💡 Tables may need to be dropped manually in Supabase dashboard")
            return False
            
        except Exception as e2:
            print(f"Alternative approach failed: {e2}")
            return False
            
    except Exception as e:
        print(f"Request error: {e}")
        return False

if __name__ == "__main__":
    try:
        success = execute_ddl()
        if success:
            print("✅ Legacy tables dropped successfully!")
        else:
            print("⚠️  Some operations may need manual intervention")
    except Exception as e:
        print(f"❌ DDL execution failed: {e}")
        sys.exit(1) 