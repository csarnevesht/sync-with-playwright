#!/usr/bin/env python3
"""
Script to create new tables via REST API calls
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from supabase_client import SupabaseClient

def create_tables():
    """Create the new tables via REST API"""
    print("🏗️ Creating new tables via REST API...")
    
    try:
        # Create Supabase client
        client = SupabaseClient()
        
        # Check existing tables
        print("🔍 Checking existing tables...")
        existing_tables = check_existing_tables(client)
        
        if all(existing_tables.values()):
            print("✅ All required tables already exist!")
        else:
            print("📋 Creating missing tables...")
            
            # Create tables that don't exist
            if not existing_tables['dropbox_account_application_info']:
                create_application_info_table(client)
            
            if not existing_tables['dropbox_account_application_files']:
                create_application_files_table(client)
        
        # Check if client list table exists
        print("🔍 Checking if client list table exists...")
        try:
            result = client.client.table('dropbox_account_client_list_info').select('id').limit(1).execute()
            print("✅ Table dropbox_account_client_list_info already exists")
        except Exception as e:
            if 'does not exist' in str(e) or 'relation' in str(e):
                print("📋 Creating client list table...")
                create_client_list_table(client)
            else:
                print(f"❌ Error checking client list table: {e}")
        
        print("🔍 Checking if new tables exist...")
        check_new_tables(client)
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

def create_client_list_table(client):
    """Create the client list table"""
    try:
        sql = """
        -- Create dropbox_account_client_list_info table for client list file data
        CREATE TABLE IF NOT EXISTS dropbox_account_client_list_info (
            id SERIAL PRIMARY KEY,
            dropbox_account_id INTEGER REFERENCES dropbox_accounts(id),
            account_name VARCHAR(255),
            first_name VARCHAR(100),
            middle_name VARCHAR(100),
            last_name VARCHAR(100),
            birthdate DATE,
            gender VARCHAR(50),
            phone VARCHAR(50),
            address TEXT,
            city VARCHAR(100),
            state VARCHAR(50),
            zip_code VARCHAR(20),
            email VARCHAR(255),
            additional_info TEXT,
            match_status VARCHAR(100),
            drivers_license_data JSONB DEFAULT '{}',
            search_info JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        -- Create indexes for better performance
        CREATE INDEX IF NOT EXISTS idx_dropbox_account_client_list_info_dropbox_account_id ON dropbox_account_client_list_info(dropbox_account_id);
        CREATE INDEX IF NOT EXISTS idx_dropbox_account_client_list_info_names ON dropbox_account_client_list_info(first_name, last_name);
        CREATE INDEX IF NOT EXISTS idx_dropbox_account_client_list_info_match_status ON dropbox_account_client_list_info(match_status);

        -- Add foreign key constraint
        ALTER TABLE dropbox_account_client_list_info 
        ADD CONSTRAINT fk_dropbox_account_client_list_info_dropbox_account 
        FOREIGN KEY (dropbox_account_id) REFERENCES dropbox_accounts(id);
        """
        
        # Execute the SQL
        client.client.rpc('exec_sql', {'sql': sql}).execute()
        print("✅ Client list table created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating client list table: {e}")

def check_tables():
    """Check if the new tables exist"""
    print("🔍 Checking if new tables exist...")
    
    try:
        client = SupabaseClient()
        
        tables_to_check = [
            'dropbox_account_application_info',
            'dropbox_account_application_files'
        ]
        
        for table in tables_to_check:
            try:
                result = client.client.table(table).select('count').execute()
                print(f"✅ Table {table} exists")
            except Exception as e:
                print(f"❌ Table {table} does not exist: {e}")
                
    except Exception as e:
        print(f"❌ Error checking tables: {e}")

if __name__ == "__main__":
    try:
        success = create_tables()
        if success:
            check_tables()
    except Exception as e:
        print(f"❌ Table creation failed: {e}")
        sys.exit(1) 