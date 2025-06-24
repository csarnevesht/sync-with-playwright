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
    """Create tables by making REST API calls"""
    print("🏗️ Creating new tables via REST API...")
    
    try:
        # Create Supabase client
        client = SupabaseClient()
        
        # Check if tables already exist
        print("🔍 Checking existing tables...")
        
        tables_to_check = [
            'dropbox_account_application_info',
            'dropbox_account_application_files'
        ]
        
        existing_tables = []
        for table in tables_to_check:
            try:
                result = client.client.table(table).select('count').execute()
                print(f"✅ Table {table} already exists")
                existing_tables.append(table)
            except Exception as e:
                print(f"❌ Table {table} does not exist: {e}")
        
        if len(existing_tables) == len(tables_to_check):
            print("✅ All required tables already exist!")
            return True
        else:
            print(f"\n💡 Found {len(existing_tables)} existing tables out of {len(tables_to_check)} required")
            print("📝 Tables that need to be created:")
            for table in tables_to_check:
                if table not in existing_tables:
                    print(f"   - {table}")
            
            print("\n⚠️  Note: Table creation via REST API is limited.")
            print("   You may need to run the SQL schema manually in your Supabase dashboard:")
            print("\n   SQL to create missing tables:")
            
            # Provide the SQL for manual execution
            sql_schema = """
            -- Create dropbox_account_application_info table for owner and joint owner data
            CREATE TABLE IF NOT EXISTS dropbox_account_application_info (
                id SERIAL PRIMARY KEY,
                first_name VARCHAR(100),
                last_name VARCHAR(100),
                date_of_birth DATE,
                gender VARCHAR(50),
                mailing_address_street TEXT,
                mailing_address_city VARCHAR(100),
                mailing_address_state VARCHAR(50),
                mailing_address_zip VARCHAR(20),
                phone_number VARCHAR(50),
                email_address VARCHAR(255),
                ocr_method VARCHAR(50),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );

            -- Create dropbox_account_application_files table for comprehensive file data
            CREATE TABLE IF NOT EXISTS dropbox_account_application_files (
                id SERIAL PRIMARY KEY,
                file_name VARCHAR(255) NOT NULL,
                file_path TEXT,
                application_type application_type DEFAULT 'Unknown',
                status application_status DEFAULT 'Processed',
                owner_id INTEGER REFERENCES dropbox_account_application_info(id),
                joint_owner_id INTEGER REFERENCES dropbox_account_application_info(id),
                notes JSONB DEFAULT '[]',
                extracted_text TEXT,
                processing_timestamp TIMESTAMP WITH TIME ZONE,
                ocr_confidence DECIMAL(5,2),
                lm_studio_model_used VARCHAR(100),
                processing_duration_seconds DECIMAL(10,3),
                dropbox_account_id INTEGER REFERENCES dropbox_accounts(id),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );

            -- Add foreign key constraint for dropbox_account_application_files
            ALTER TABLE dropbox_account_application_files 
            ADD CONSTRAINT fk_dropbox_account_application_files_dropbox_account 
            FOREIGN KEY (dropbox_account_id) REFERENCES dropbox_accounts(id);

            -- Create indexes for better performance
            CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_files_file_name ON dropbox_account_application_files(file_name);
            CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_files_dropbox_account_id ON dropbox_account_application_files(dropbox_account_id);
            CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_files_status ON dropbox_account_application_files(status);
            CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_info_names ON dropbox_account_application_info(first_name, last_name);
            """
            
            print(sql_schema)
            return False
        
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        return False

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