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
            
            if not existing_tables['dropbox_account_client_list_info']:
                create_client_list_table(client)
            
            if not existing_tables['dropbox_account_best_info']:
                create_best_info_table(client)
            
            if not existing_tables['salesforce_accounts']:
                create_salesforce_accounts_table(client)
            
            if not existing_tables['salesforce_households']:
                create_salesforce_households_table(client)
            
            if not existing_tables['salesforce_household_members']:
                create_salesforce_household_members_table(client)
            
            if not existing_tables['dropbox_salesforce_mapping']:
                create_dropbox_salesforce_mapping_table(client)
            
            if not existing_tables['sync_status']:
                create_sync_status_table(client)
            
            if not existing_tables['account_analysis']:
                create_account_analysis_table(client)
        
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

def create_best_info_table(client):
    """Create the dropbox account best info table"""
    try:
        sql = """
        -- Create dropbox_account_best_info table for merged/consolidated data
        CREATE TABLE IF NOT EXISTS dropbox_account_best_info (
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
            ssn_tax_id VARCHAR(50),
            data_sources JSONB DEFAULT '{}',
            field_precedence JSONB DEFAULT '{}',
            confidence_score DECIMAL(3,2),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_dropbox_account_best_info_dropbox_account_id ON dropbox_account_best_info(dropbox_account_id);
        CREATE INDEX IF NOT EXISTS idx_dropbox_account_best_info_names ON dropbox_account_best_info(first_name, last_name);
        """
        
        client.client.rpc('exec_sql', {'sql': sql}).execute()
        print("✅ Best info table created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating best info table: {e}")

def create_salesforce_accounts_table(client):
    """Create the salesforce accounts table"""
    try:
        sql = """
        -- Create salesforce_account_type enum
        CREATE TYPE IF NOT EXISTS salesforce_account_type AS ENUM ('Contact', 'Household', 'Household_Head', 'Household_Member');
        
        -- Create salesforce_accounts table
        CREATE TABLE IF NOT EXISTS salesforce_accounts (
            id SERIAL PRIMARY KEY,
            salesforce_account_id VARCHAR(255) UNIQUE,
            account_name VARCHAR(255),
            account_type salesforce_account_type,
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
            ssn_tax_id VARCHAR(50),
            stage VARCHAR(100),
            writing_advisor VARCHAR(255),
            prospecting_status VARCHAR(100),
            account_record_type VARCHAR(100),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_salesforce_accounts_salesforce_id ON salesforce_accounts(salesforce_account_id);
        CREATE INDEX IF NOT EXISTS idx_salesforce_accounts_names ON salesforce_accounts(first_name, last_name);
        CREATE INDEX IF NOT EXISTS idx_salesforce_accounts_type ON salesforce_accounts(account_type);
        """
        
        client.client.rpc('exec_sql', {'sql': sql}).execute()
        print("✅ Salesforce accounts table created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating salesforce accounts table: {e}")

def create_salesforce_households_table(client):
    """Create the salesforce households table"""
    try:
        sql = """
        -- Create salesforce_households table
        CREATE TABLE IF NOT EXISTS salesforce_households (
            id SERIAL PRIMARY KEY,
            salesforce_household_id VARCHAR(255) UNIQUE,
            household_name VARCHAR(255),
            household_head_id VARCHAR(255) REFERENCES salesforce_accounts(salesforce_account_id),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_salesforce_households_household_id ON salesforce_households(salesforce_household_id);
        CREATE INDEX IF NOT EXISTS idx_salesforce_households_head_id ON salesforce_households(household_head_id);
        """
        
        client.client.rpc('exec_sql', {'sql': sql}).execute()
        print("✅ Salesforce households table created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating salesforce households table: {e}")

def create_salesforce_household_members_table(client):
    """Create the salesforce household members table"""
    try:
        sql = """
        -- Create salesforce_household_members table
        CREATE TABLE IF NOT EXISTS salesforce_household_members (
            id SERIAL PRIMARY KEY,
            household_id VARCHAR(255) REFERENCES salesforce_households(salesforce_household_id),
            member_id VARCHAR(255) REFERENCES salesforce_accounts(salesforce_account_id),
            role VARCHAR(50),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_salesforce_household_members_household_id ON salesforce_household_members(household_id);
        CREATE INDEX IF NOT EXISTS idx_salesforce_household_members_member_id ON salesforce_household_members(member_id);
        """
        
        client.client.rpc('exec_sql', {'sql': sql}).execute()
        print("✅ Salesforce household members table created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating salesforce household members table: {e}")

def create_dropbox_salesforce_mapping_table(client):
    """Create the dropbox to salesforce mapping table"""
    try:
        sql = """
        -- Create dropbox_salesforce_mapping table
        CREATE TABLE IF NOT EXISTS dropbox_salesforce_mapping (
            id SERIAL PRIMARY KEY,
            dropbox_account_id INTEGER REFERENCES dropbox_accounts(id),
            salesforce_account_id VARCHAR(255) REFERENCES salesforce_accounts(salesforce_account_id),
            mapping_type VARCHAR(50),
            confidence_score DECIMAL(3,2),
            mapping_rules JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(dropbox_account_id, salesforce_account_id)
        );

        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_dropbox_salesforce_mapping_dropbox_id ON dropbox_salesforce_mapping(dropbox_account_id);
        CREATE INDEX IF NOT EXISTS idx_dropbox_salesforce_mapping_salesforce_id ON dropbox_salesforce_mapping(salesforce_account_id);
        CREATE INDEX IF NOT EXISTS idx_dropbox_salesforce_mapping_type ON dropbox_salesforce_mapping(mapping_type);
        """
        
        client.client.rpc('exec_sql', {'sql': sql}).execute()
        print("✅ Dropbox Salesforce mapping table created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating dropbox salesforce mapping table: {e}")

def create_sync_status_table(client):
    """Create the sync status table"""
    try:
        sql = """
        -- Create salesforce_sync_status enum
        CREATE TYPE IF NOT EXISTS salesforce_sync_status AS ENUM ('pending', 'synced', 'failed', 'needs_update');
        
        -- Create sync_status table
        CREATE TABLE IF NOT EXISTS sync_status (
            id SERIAL PRIMARY KEY,
            dropbox_account_id INTEGER REFERENCES dropbox_accounts(id),
            salesforce_account_id VARCHAR(255) REFERENCES salesforce_accounts(salesforce_account_id),
            sync_status salesforce_sync_status DEFAULT 'pending',
            sync_direction VARCHAR(20),
            last_sync_timestamp TIMESTAMP WITH TIME ZONE,
            sync_errors JSONB DEFAULT '[]',
            fields_synced JSONB DEFAULT '[]',
            fields_failed JSONB DEFAULT '[]',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_sync_status_dropbox_id ON sync_status(dropbox_account_id);
        CREATE INDEX IF NOT EXISTS idx_sync_status_salesforce_id ON sync_status(salesforce_account_id);
        CREATE INDEX IF NOT EXISTS idx_sync_status_status ON sync_status(sync_status);
        """
        
        client.client.rpc('exec_sql', {'sql': sql}).execute()
        print("✅ Sync status table created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating sync status table: {e}")

def create_account_analysis_table(client):
    """Create the account analysis table"""
    try:
        sql = """
        -- Create account_analysis table
        CREATE TABLE IF NOT EXISTS account_analysis (
            id SERIAL PRIMARY KEY,
            dropbox_account_id INTEGER REFERENCES dropbox_accounts(id),
            salesforce_account_id VARCHAR(255) REFERENCES salesforce_accounts(salesforce_account_id),
            analysis_type VARCHAR(100),
            analysis_data JSONB DEFAULT '{}',
            recommendations JSONB DEFAULT '[]',
            missing_fields JSONB DEFAULT '[]',
            field_mappings JSONB DEFAULT '{}',
            data_differences JSONB DEFAULT '{}',
            analysis_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_account_analysis_dropbox_id ON account_analysis(dropbox_account_id);
        CREATE INDEX IF NOT EXISTS idx_account_analysis_salesforce_id ON account_analysis(salesforce_account_id);
        CREATE INDEX IF NOT EXISTS idx_account_analysis_type ON account_analysis(analysis_type);
        """
        
        client.client.rpc('exec_sql', {'sql': sql}).execute()
        print("✅ Account analysis table created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating account analysis table: {e}")

def create_application_info_table(client):
    """Create the dropbox account application info table"""
    try:
        sql = """
        -- Create application_status enum
        CREATE TYPE IF NOT EXISTS application_status AS ENUM ('Processed', 'Failed', 'Error', 'Skipped');
        
        -- Create application_type enum
        CREATE TYPE IF NOT EXISTS application_type AS ENUM ('Life Insurance', 'Annuity', 'EquiTrust Annuity', 'Security Benefit', 'Unknown');
        
        -- Create dropbox_account_application_info table
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

        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_info_names ON dropbox_account_application_info(first_name, last_name);
        """
        
        client.client.rpc('exec_sql', {'sql': sql}).execute()
        print("✅ Application info table created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating application info table: {e}")

def create_application_files_table(client):
    """Create the dropbox account application files table"""
    try:
        sql = """
        -- Create dropbox_account_application_files table
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

        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_files_file_name ON dropbox_account_application_files(file_name);
        CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_files_dropbox_account_id ON dropbox_account_application_files(dropbox_account_id);
        CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_files_status ON dropbox_account_application_files(status);
        """
        
        client.client.rpc('exec_sql', {'sql': sql}).execute()
        print("✅ Application files table created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating application files table: {e}")

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

def check_existing_tables(client):
    """Check if the required tables exist. Returns a dict of table_name: exists (bool)."""
    tables = [
        'dropbox_account_application_info',
        'dropbox_account_application_files',
        'dropbox_account_client_list_info',
        'dropbox_account_best_info',
        'salesforce_accounts',
        'salesforce_households',
        'salesforce_household_members',
        'dropbox_salesforce_mapping',
        'sync_status',
        'account_analysis'
    ]
    exists = {}
    for table in tables:
        try:
            client.client.table(table).select('id').limit(1).execute()
            exists[table] = True
        except Exception as e:
            if 'does not exist' in str(e) or 'relation' in str(e):
                exists[table] = False
            else:
                print(f"⚠️ Error checking table {table}: {e}")
                exists[table] = False
    return exists

def check_new_tables(client):
    """Check if the new tables exist and print their status."""
    tables = [
        'dropbox_account_client_list_info',
        'dropbox_account_best_info',
        'salesforce_accounts',
        'salesforce_households',
        'salesforce_household_members',
        'dropbox_salesforce_mapping',
        'sync_status',
        'account_analysis'
    ]
    for table in tables:
        try:
            client.client.table(table).select('id').limit(1).execute()
            print(f"✅ Table {table} exists")
        except Exception as e:
            print(f"❌ Table {table} does not exist: {e}")

if __name__ == "__main__":
    try:
        success = create_tables()
        if success:
            check_tables()
    except Exception as e:
        print(f"❌ Table creation failed: {e}")
        sys.exit(1) 