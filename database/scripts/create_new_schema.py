#!/usr/bin/env python3
"""
Script to create the new schema with renamed tables
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

def execute_sql(base_url: str, headers: dict, sql: str):
    """Execute SQL via REST API"""
    try:
        # Use the SQL endpoint
        url = f"{base_url}/rest/v1/rpc/exec_sql"
        data = {"sql": sql}
        
        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json() if response.content else {}
    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        print(f"Request error: {e}")
        raise

def create_new_schema():
    """Create the new schema with renamed tables"""
    print("🏗️ Creating new schema with renamed tables...")
    
    # Load environment
    base_url, api_key = load_environment()
    headers = {
        'apikey': api_key,
        'Content-Type': 'application/json'
    }
    
    print(f"Using Supabase URL: {base_url}")
    
    # SQL to create the new schema
    schema_sql = """
    -- Create enums if they don't exist
    DO $$ BEGIN
        CREATE TYPE household_role AS ENUM ('Head', 'Member');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    
    DO $$ BEGIN
        CREATE TYPE application_status AS ENUM ('Processed', 'Failed', 'Error', 'Skipped');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    
    DO $$ BEGIN
        CREATE TYPE application_type AS ENUM ('Life Insurance', 'Annuity', 'EquiTrust Annuity', 'Security Benefit', 'Unknown');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;

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
    
    try:
        print("Executing schema creation SQL...")
        result = execute_sql(base_url, headers, schema_sql)
        print("✅ Schema created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating schema: {e}")
        return False

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
        success = create_new_schema()
        if success:
            check_tables()
    except Exception as e:
        print(f"❌ Schema creation failed: {e}")
        sys.exit(1) 