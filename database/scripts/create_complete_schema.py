#!/usr/bin/env python3
"""
Script to create the complete account information schema in logical blocks.
Each type, table, index, and constraint is created one at a time, with clear reporting.
"""

import os
import sys
import httpx
from dotenv import load_dotenv

def load_environment():
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    print(f"Loading environment variables from {env_path}")
    load_dotenv(env_path)
    supabase_url = os.getenv('SUPABASE_URL') or os.getenv('SUPABASE_PUBLIC_URL') or 'http://localhost:8000'
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_ANON_KEY')
    if not supabase_key:
        raise ValueError("No Supabase key found!")
    return supabase_url, supabase_key

def get_schema_blocks():
    """Return a list of (label, SQL) tuples for each schema block."""
    blocks = [
        # Enums/Types
        ("application_status enum", "CREATE TYPE IF NOT EXISTS application_status AS ENUM ('Processed', 'Failed', 'Error', 'Skipped');"),
        ("application_type enum", "CREATE TYPE IF NOT EXISTS application_type AS ENUM ('Life Insurance', 'Annuity', 'EquiTrust Annuity', 'Security Benefit', 'Unknown');"),
        ("salesforce_account_type enum", "CREATE TYPE IF NOT EXISTS salesforce_account_type AS ENUM ('Contact', 'Household', 'Household_Head', 'Household_Member');"),
        ("salesforce_sync_status enum", "CREATE TYPE IF NOT EXISTS salesforce_sync_status AS ENUM ('pending', 'synced', 'failed', 'needs_update');"),
        # Tables
        ("dropbox_account_application_info table", '''CREATE TABLE IF NOT EXISTS dropbox_account_application_info (
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
);'''),
        ("dropbox_accounts table", '''CREATE TABLE IF NOT EXISTS dropbox_accounts (
    id SERIAL PRIMARY KEY,
    folder VARCHAR(255) NOT NULL UNIQUE,
    first_name VARCHAR(100),
    middle_name VARCHAR(100),
    last_name VARCHAR(100),
    total_files INTEGER DEFAULT 0,
    processed_files INTEGER DEFAULT 0,
    failed_files INTEGER DEFAULT 0,
    processing_timestamp TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);'''),
        ("dropbox_account_application_files table", '''CREATE TABLE IF NOT EXISTS dropbox_account_application_files (
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
);'''),
        ("dropbox_account_client_list_info table", '''CREATE TABLE IF NOT EXISTS dropbox_account_client_list_info (
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
);'''),
        ("dropbox_account_best_info table", '''CREATE TABLE IF NOT EXISTS dropbox_account_best_info (
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
);'''),
        ("salesforce_accounts table", '''CREATE TABLE IF NOT EXISTS salesforce_accounts (
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
);'''),
        ("salesforce_households table", '''CREATE TABLE IF NOT EXISTS salesforce_households (
    id SERIAL PRIMARY KEY,
    salesforce_household_id VARCHAR(255) UNIQUE,
    household_name VARCHAR(255),
    household_head_id VARCHAR(255) REFERENCES salesforce_accounts(salesforce_account_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);'''),
        ("salesforce_household_members table", '''CREATE TABLE IF NOT EXISTS salesforce_household_members (
    id SERIAL PRIMARY KEY,
    household_id VARCHAR(255) REFERENCES salesforce_households(salesforce_household_id),
    member_id VARCHAR(255) REFERENCES salesforce_accounts(salesforce_account_id),
    role VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);'''),
        ("dropbox_salesforce_mapping table", '''CREATE TABLE IF NOT EXISTS dropbox_salesforce_mapping (
    id SERIAL PRIMARY KEY,
    dropbox_account_id INTEGER REFERENCES dropbox_accounts(id),
    salesforce_account_id VARCHAR(255) REFERENCES salesforce_accounts(salesforce_account_id),
    mapping_type VARCHAR(50),
    confidence_score DECIMAL(3,2),
    mapping_rules JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(dropbox_account_id, salesforce_account_id)
);'''),
        ("sync_status table", '''CREATE TABLE IF NOT EXISTS sync_status (
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
);'''),
        ("account_analysis table", '''CREATE TABLE IF NOT EXISTS account_analysis (
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
);'''),
        # Indexes (add more as needed)
        ("idx_dropbox_account_application_files_file_name index", "CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_files_file_name ON dropbox_account_application_files(file_name);"),
        ("idx_dropbox_account_application_files_dropbox_account_id index", "CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_files_dropbox_account_id ON dropbox_account_application_files(dropbox_account_id);"),
        ("idx_dropbox_account_application_files_status index", "CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_files_status ON dropbox_account_application_files(status);"),
        ("idx_dropbox_accounts_folder index", "CREATE INDEX IF NOT EXISTS idx_dropbox_accounts_folder ON dropbox_accounts(folder);"),
        ("idx_dropbox_account_application_info_names index", "CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_info_names ON dropbox_account_application_info(first_name, last_name);"),
        ("idx_dropbox_account_client_list_info_dropbox_account_id index", "CREATE INDEX IF NOT EXISTS idx_dropbox_account_client_list_info_dropbox_account_id ON dropbox_account_client_list_info(dropbox_account_id);"),
        ("idx_dropbox_account_client_list_info_names index", "CREATE INDEX IF NOT EXISTS idx_dropbox_account_client_list_info_names ON dropbox_account_client_list_info(first_name, last_name);"),
        ("idx_dropbox_account_client_list_info_match_status index", "CREATE INDEX IF NOT EXISTS idx_dropbox_account_client_list_info_match_status ON dropbox_account_client_list_info(match_status);"),
        ("idx_dropbox_account_best_info_dropbox_account_id index", "CREATE INDEX IF NOT EXISTS idx_dropbox_account_best_info_dropbox_account_id ON dropbox_account_best_info(dropbox_account_id);"),
        ("idx_dropbox_account_best_info_names index", "CREATE INDEX IF NOT EXISTS idx_dropbox_account_best_info_names ON dropbox_account_best_info(first_name, last_name);"),
        ("idx_salesforce_accounts_salesforce_id index", "CREATE INDEX IF NOT EXISTS idx_salesforce_accounts_salesforce_id ON salesforce_accounts(salesforce_account_id);"),
        ("idx_salesforce_accounts_names index", "CREATE INDEX IF NOT EXISTS idx_salesforce_accounts_names ON salesforce_accounts(first_name, last_name);"),
        ("idx_salesforce_accounts_type index", "CREATE INDEX IF NOT EXISTS idx_salesforce_accounts_type ON salesforce_accounts(account_type);"),
        ("idx_salesforce_households_household_id index", "CREATE INDEX IF NOT EXISTS idx_salesforce_households_household_id ON salesforce_households(salesforce_household_id);"),
        ("idx_salesforce_households_head_id index", "CREATE INDEX IF NOT EXISTS idx_salesforce_households_head_id ON salesforce_households(household_head_id);"),
        ("idx_salesforce_household_members_household_id index", "CREATE INDEX IF NOT EXISTS idx_salesforce_household_members_household_id ON salesforce_household_members(household_id);"),
        ("idx_salesforce_household_members_member_id index", "CREATE INDEX IF NOT EXISTS idx_salesforce_household_members_member_id ON salesforce_household_members(member_id);"),
        ("idx_dropbox_salesforce_mapping_dropbox_id index", "CREATE INDEX IF NOT EXISTS idx_dropbox_salesforce_mapping_dropbox_id ON dropbox_salesforce_mapping(dropbox_account_id);"),
        ("idx_dropbox_salesforce_mapping_salesforce_id index", "CREATE INDEX IF NOT EXISTS idx_dropbox_salesforce_mapping_salesforce_id ON dropbox_salesforce_mapping(salesforce_account_id);"),
        ("idx_dropbox_salesforce_mapping_type index", "CREATE INDEX IF NOT EXISTS idx_dropbox_salesforce_mapping_type ON dropbox_salesforce_mapping(mapping_type);"),
        ("idx_sync_status_dropbox_id index", "CREATE INDEX IF NOT EXISTS idx_sync_status_dropbox_id ON sync_status(dropbox_account_id);"),
        ("idx_sync_status_salesforce_id index", "CREATE INDEX IF NOT EXISTS idx_sync_status_salesforce_id ON sync_status(salesforce_account_id);"),
        ("idx_sync_status_status index", "CREATE INDEX IF NOT EXISTS idx_sync_status_status ON sync_status(sync_status);"),
        ("idx_account_analysis_dropbox_id index", "CREATE INDEX IF NOT EXISTS idx_account_analysis_dropbox_id ON account_analysis(dropbox_account_id);"),
        ("idx_account_analysis_salesforce_id index", "CREATE INDEX IF NOT EXISTS idx_account_analysis_salesforce_id ON account_analysis(salesforce_account_id);"),
        ("idx_account_analysis_type index", "CREATE INDEX IF NOT EXISTS idx_account_analysis_type ON account_analysis(analysis_type);")
    ]
    return blocks

def create_complete_schema():
    print("🏗️ Creating complete account information schema (block-by-block)...")
    base_url, api_key = load_environment()
    headers = {
        'apikey': api_key,
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    blocks = get_schema_blocks()
    success_count = 0
    for i, (label, sql) in enumerate(blocks, 1):
        print(f"\n[{i}/{len(blocks)}] Creating {label}...")
        url = f"{base_url}/rest/v1/rpc/exec_sql"
        data = {"sql": sql}
        try:
            with httpx.Client() as client:
                response = client.post(url, headers=headers, json=data)
                response.raise_for_status()
            print(f"✅ {label} created successfully!")
            success_count += 1
        except Exception as e:
            print(f"❌ Failed to create {label}: {e}")
            print(f"   SQL: {sql[:100]}...")
    print(f"\n📊 Block-by-block schema creation summary:")
    print(f"   Successful: {success_count} out of {len(blocks)} blocks")
    if success_count == len(blocks):
        print("🎉 Complete schema created successfully!")
        return True
    else:
        print("⚠️  Some blocks may not have been created properly")
        return False

def show_schema_overview():
    print("\n" + "="*80)
    print("📋 COMPLETE ACCOUNT INFORMATION SCHEMA OVERVIEW")
    print("="*80)
    print("\n🎯 For each Dropbox account folder, you can now store:")
    print("\n1️⃣  DROPBOX ACCOUNT INFORMATION 'FROM APPLICATION FILES'")
    print("   📄 dropbox_account_application_files - File metadata and processing info")
    print("   👤 dropbox_account_application_info - Owner and joint owner data")
    print("   🔗 Links to: dropbox_accounts table")
    print("\n2️⃣  DROPBOX ACCOUNT INFORMATION 'FROM CLIENT LIST FILE'")
    print("   📋 dropbox_account_client_list_info - Data from Excel client lists")
    print("   🔍 Includes: match status, search info, driver's license data")
    print("   🔗 Links to: dropbox_accounts table")
    print("\n3️⃣  DROPBOX BEST ACCOUNT INFORMATION")
    print("   ⭐ dropbox_account_best_info - Merged/consolidated best data")
    print("   📊 Tracks: data sources, field precedence, confidence scores")
    print("   🔗 Links to: dropbox_accounts table")
    print("\n4️⃣  SALESFORCE ACCOUNT INFORMATION")
    print("   🏢 salesforce_accounts - Individual Salesforce account records")
    print("   🏠 salesforce_households - Salesforce household records")
    print("   👥 salesforce_household_members - Household relationships")
    print("   🔗 Links to: dropbox_accounts via mapping table")
    print("\n🔗 MAPPING & SYNCHRONIZATION")
    print("   🔄 dropbox_salesforce_mapping - Links Dropbox to Salesforce accounts")
    print("   📡 sync_status - Tracks synchronization status and history")
    print("   📊 account_analysis - Stores analysis and comparison results")
    print("\n💡 EXAMPLE: For folder 'Montesino, Maria'")
    print("   • Application files data → dropbox_account_application_files")
    print("   • Client list data → dropbox_account_client_list_info") 
    print("   • Best merged data → dropbox_account_best_info")
    print("   • Salesforce data → salesforce_accounts (if exists)")
    print("   • Mapping → dropbox_salesforce_mapping")
    print("   • Analysis → account_analysis")
    print("\n" + "="*80)

if __name__ == "__main__":
    success = create_complete_schema()
    if success:
        show_schema_overview()
        print("\n🎉 Complete account information schema is ready!")
    else:
        print("\n❌ Schema creation failed!")
        sys.exit(1) 