#!/usr/bin/env python3
"""
Script to create the new schema with renamed tables
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from supabase_client import SupabaseClient

def create_new_schema():
    """Create the new schema with renamed tables"""
    print("🏗️ Creating new schema with renamed tables...")
    
    try:
        # Create Supabase client
        client = SupabaseClient()
        
        # SQL to create the new schema
        schema_sql = """
        -- Create enums
        CREATE TYPE application_status AS ENUM ('Processed', 'Failed', 'Error', 'Skipped');
        CREATE TYPE application_type AS ENUM ('Life Insurance', 'Annuity', 'EquiTrust Annuity', 'Security Benefit', 'Unknown');
        
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
            dropbox_account_id INTEGER,
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
        
        print("Executing schema creation SQL...")
        
        # For now, let's check if the tables already exist and provide instructions
        print("🔍 Checking existing tables...")
        
        try:
            # Try to access the tables to see if they exist
            result = client.client.table('dropbox_account_application_info').select('count').execute()
            print("✅ Table dropbox_account_application_info already exists")
        except Exception as e:
            print("❌ Table dropbox_account_application_info does not exist")
            print("💡 You may need to run the SQL manually in your Supabase dashboard or use a different approach.")
            print("   The SQL schema is:")
            print(schema_sql)
            return False
        
        try:
            result = client.client.table('dropbox_account_application_files').select('count').execute()
            print("✅ Table dropbox_account_application_files already exists")
        except Exception as e:
            print("❌ Table dropbox_account_application_files does not exist")
            print("💡 You may need to run the SQL manually in your Supabase dashboard or use a different approach.")
            return False
        
        print("✅ All required tables exist!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating schema: {e}")
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
        success = create_new_schema()
        if success:
            check_tables()
    except Exception as e:
        print(f"❌ Schema creation failed: {e}")
        sys.exit(1) 