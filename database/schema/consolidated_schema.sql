-- ============================================================================
-- CONSOLIDATED DATABASE SCHEMA
-- ============================================================================
-- This schema consolidates all database tables into a single, consistent design
-- that supports Dropbox account processing and Salesforce integration

-- ============================================================================
-- ENUM DEFINITIONS
-- ============================================================================

-- Drop enum types if they exist (for clean recreation)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'application_status') THEN
        DROP TYPE application_status CASCADE;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'application_type') THEN
        DROP TYPE application_type CASCADE;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'salesforce_account_type') THEN
        DROP TYPE salesforce_account_type CASCADE;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'salesforce_sync_status') THEN
        DROP TYPE salesforce_sync_status CASCADE;
    END IF;
END$$;

-- Create enums
CREATE TYPE application_status AS ENUM ('Processed', 'Failed', 'Error', 'Skipped');
CREATE TYPE application_type AS ENUM ('Life Insurance', 'Annuity', 'EquiTrust Annuity', 'Security Benefit', 'Unknown');
CREATE TYPE salesforce_account_type AS ENUM ('Contact', 'Household', 'Household_Head', 'Household_Member');
CREATE TYPE salesforce_sync_status AS ENUM ('pending', 'synced', 'failed', 'needs_update');

-- ============================================================================
-- CORE DROPBOX TABLES
-- ============================================================================

-- 1. DROPBOX ACCOUNTS (Core table)
-- Stores basic Dropbox account information and folder metadata
CREATE TABLE IF NOT EXISTS dropbox_accounts (
    id SERIAL PRIMARY KEY,
    folder VARCHAR(255) NOT NULL UNIQUE,
    first_name VARCHAR(100),
    middle_name VARCHAR(100),
    last_name VARCHAR(100),
    total_account_application_files INTEGER DEFAULT 0,
    processed_account_application_files INTEGER DEFAULT 0,
    failed_account_application_files INTEGER DEFAULT 0,
    processing_timestamp TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. DROPBOX ACCOUNT APPLICATION INFO
-- Stores person information extracted from application files (owners and joint owners)
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

-- 3. DROPBOX ACCOUNT APPLICATION FILES
-- Stores comprehensive file data and processing metadata
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

-- 4. DROPBOX ACCOUNT CLIENT LIST INFO
-- Stores data extracted from client list Excel files
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

-- 5. DROPBOX ACCOUNT BEST INFO (MERGED/CONSOLIDATED)
-- Stores the best available information from both Dropbox sources
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
    data_sources JSONB DEFAULT '{}', -- Track which Dropbox sources contributed data
    field_precedence JSONB DEFAULT '{}', -- Track which Dropbox source was used for each field
    confidence_score DECIMAL(3,2), -- Overall confidence in the merged Dropbox data
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- SALESFORCE TABLES (Optional - for future integration)
-- ============================================================================

-- 6. SALESFORCE ACCOUNTS
-- Stores data from Salesforce CRM system
CREATE TABLE IF NOT EXISTS salesforce_accounts (
    id SERIAL PRIMARY KEY,
    salesforce_account_id VARCHAR(255) UNIQUE, -- Salesforce Account ID
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

-- 7. SALESFORCE HOUSEHOLDS
-- Stores Salesforce household relationships
CREATE TABLE IF NOT EXISTS salesforce_households (
    id SERIAL PRIMARY KEY,
    salesforce_household_id VARCHAR(255) UNIQUE, -- Salesforce Household ID
    household_name VARCHAR(255),
    household_head_id VARCHAR(255) REFERENCES salesforce_accounts(salesforce_account_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. SALESFORCE HOUSEHOLD MEMBERS
-- Stores many-to-many relationship between households and members
CREATE TABLE IF NOT EXISTS salesforce_household_members (
    id SERIAL PRIMARY KEY,
    household_id VARCHAR(255) REFERENCES salesforce_households(salesforce_household_id),
    member_id VARCHAR(255) REFERENCES salesforce_accounts(salesforce_account_id),
    role VARCHAR(50), -- 'Head', 'Member', etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- MAPPING AND SYNC TABLES
-- ============================================================================

-- 9. DROPBOX TO SALESFORCE MAPPING
-- Links Dropbox accounts to Salesforce accounts
CREATE TABLE IF NOT EXISTS dropbox_salesforce_mapping (
    id SERIAL PRIMARY KEY,
    dropbox_account_id INTEGER REFERENCES dropbox_accounts(id),
    salesforce_account_id VARCHAR(255) REFERENCES salesforce_accounts(salesforce_account_id),
    mapping_type VARCHAR(50), -- 'Household_Head', 'Household_Member', 'Direct'
    confidence_score DECIMAL(3,2), -- Confidence in the mapping
    mapping_rules JSONB DEFAULT '{}', -- Rules used to create the mapping
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(dropbox_account_id, salesforce_account_id)
);

-- 10. SYNC STATUS AND HISTORY
-- Tracks synchronization between Dropbox and Salesforce
CREATE TABLE IF NOT EXISTS sync_status (
    id SERIAL PRIMARY KEY,
    dropbox_account_id INTEGER REFERENCES dropbox_accounts(id),
    salesforce_account_id VARCHAR(255) REFERENCES salesforce_accounts(salesforce_account_id),
    sync_status salesforce_sync_status DEFAULT 'pending',
    sync_direction VARCHAR(20), -- 'dropbox_to_salesforce', 'salesforce_to_dropbox', 'bidirectional'
    last_sync_timestamp TIMESTAMP WITH TIME ZONE,
    sync_errors JSONB DEFAULT '[]',
    fields_synced JSONB DEFAULT '[]',
    fields_failed JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 11. ACCOUNT ANALYSIS
-- Stores analysis results comparing Dropbox and Salesforce data
CREATE TABLE IF NOT EXISTS account_analysis (
    id SERIAL PRIMARY KEY,
    dropbox_account_id INTEGER REFERENCES dropbox_accounts(id),
    salesforce_account_id VARCHAR(255) REFERENCES salesforce_accounts(salesforce_account_id),
    analysis_type VARCHAR(100), -- 'data_comparison', 'mapping_validation', 'sync_recommendations'
    analysis_data JSONB DEFAULT '{}',
    recommendations JSONB DEFAULT '[]',
    missing_fields JSONB DEFAULT '[]',
    field_mappings JSONB DEFAULT '{}',
    data_differences JSONB DEFAULT '{}',
    analysis_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Dropbox indexes
CREATE INDEX IF NOT EXISTS idx_dropbox_accounts_folder ON dropbox_accounts(folder);
CREATE INDEX IF NOT EXISTS idx_dropbox_accounts_names ON dropbox_accounts(first_name, last_name);

CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_info_names ON dropbox_account_application_info(first_name, last_name);
CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_info_dob ON dropbox_account_application_info(date_of_birth);

CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_files_file_name ON dropbox_account_application_files(file_name);
CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_files_dropbox_account_id ON dropbox_account_application_files(dropbox_account_id);
CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_files_status ON dropbox_account_application_files(status);
CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_files_type ON dropbox_account_application_files(application_type);

CREATE INDEX IF NOT EXISTS idx_dropbox_account_client_list_info_dropbox_account_id ON dropbox_account_client_list_info(dropbox_account_id);
CREATE INDEX IF NOT EXISTS idx_dropbox_account_client_list_info_names ON dropbox_account_client_list_info(first_name, last_name);
CREATE INDEX IF NOT EXISTS idx_dropbox_account_client_list_info_match_status ON dropbox_account_client_list_info(match_status);

CREATE INDEX IF NOT EXISTS idx_dropbox_account_best_info_dropbox_account_id ON dropbox_account_best_info(dropbox_account_id);
CREATE INDEX IF NOT EXISTS idx_dropbox_account_best_info_names ON dropbox_account_best_info(first_name, last_name);

-- Salesforce indexes
CREATE INDEX IF NOT EXISTS idx_salesforce_accounts_salesforce_id ON salesforce_accounts(salesforce_account_id);
CREATE INDEX IF NOT EXISTS idx_salesforce_accounts_names ON salesforce_accounts(first_name, last_name);
CREATE INDEX IF NOT EXISTS idx_salesforce_accounts_type ON salesforce_accounts(account_type);

CREATE INDEX IF NOT EXISTS idx_salesforce_households_household_id ON salesforce_households(salesforce_household_id);
CREATE INDEX IF NOT EXISTS idx_salesforce_households_head_id ON salesforce_households(household_head_id);

CREATE INDEX IF NOT EXISTS idx_salesforce_household_members_household_id ON salesforce_household_members(household_id);
CREATE INDEX IF NOT EXISTS idx_salesforce_household_members_member_id ON salesforce_household_members(member_id);

-- Mapping indexes
CREATE INDEX IF NOT EXISTS idx_dropbox_salesforce_mapping_dropbox_id ON dropbox_salesforce_mapping(dropbox_account_id);
CREATE INDEX IF NOT EXISTS idx_dropbox_salesforce_mapping_salesforce_id ON dropbox_salesforce_mapping(salesforce_account_id);
CREATE INDEX IF NOT EXISTS idx_dropbox_salesforce_mapping_type ON dropbox_salesforce_mapping(mapping_type);

-- Sync indexes
CREATE INDEX IF NOT EXISTS idx_sync_status_dropbox_id ON sync_status(dropbox_account_id);
CREATE INDEX IF NOT EXISTS idx_sync_status_salesforce_id ON sync_status(salesforce_account_id);
CREATE INDEX IF NOT EXISTS idx_sync_status_status ON sync_status(sync_status);

-- Analysis indexes
CREATE INDEX IF NOT EXISTS idx_account_analysis_dropbox_id ON account_analysis(dropbox_account_id);
CREATE INDEX IF NOT EXISTS idx_account_analysis_salesforce_id ON account_analysis(salesforce_account_id);
CREATE INDEX IF NOT EXISTS idx_account_analysis_type ON account_analysis(analysis_type);

-- ============================================================================
-- FOREIGN KEY CONSTRAINTS
-- ============================================================================

-- Dropbox constraints
ALTER TABLE dropbox_account_application_files 
ADD CONSTRAINT fk_dropbox_account_application_files_dropbox_account 
FOREIGN KEY (dropbox_account_id) REFERENCES dropbox_accounts(id);

ALTER TABLE dropbox_account_client_list_info 
ADD CONSTRAINT fk_dropbox_account_client_list_info_dropbox_account 
FOREIGN KEY (dropbox_account_id) REFERENCES dropbox_accounts(id);

ALTER TABLE dropbox_account_best_info 
ADD CONSTRAINT fk_dropbox_account_best_info_dropbox_account 
FOREIGN KEY (dropbox_account_id) REFERENCES dropbox_accounts(id);

-- Mapping constraints
ALTER TABLE dropbox_salesforce_mapping 
ADD CONSTRAINT fk_dropbox_salesforce_mapping_dropbox_account 
FOREIGN KEY (dropbox_account_id) REFERENCES dropbox_accounts(id);

ALTER TABLE dropbox_salesforce_mapping 
ADD CONSTRAINT fk_dropbox_salesforce_mapping_salesforce_account 
FOREIGN KEY (salesforce_account_id) REFERENCES salesforce_accounts(salesforce_account_id);

-- Sync constraints
ALTER TABLE sync_status 
ADD CONSTRAINT fk_sync_status_dropbox_account 
FOREIGN KEY (dropbox_account_id) REFERENCES dropbox_accounts(id);

ALTER TABLE sync_status 
ADD CONSTRAINT fk_sync_status_salesforce_account 
FOREIGN KEY (salesforce_account_id) REFERENCES salesforce_accounts(salesforce_account_id);

-- Analysis constraints
ALTER TABLE account_analysis 
ADD CONSTRAINT fk_account_analysis_dropbox_account 
FOREIGN KEY (dropbox_account_id) REFERENCES dropbox_accounts(id);

ALTER TABLE account_analysis 
ADD CONSTRAINT fk_account_analysis_salesforce_account 
FOREIGN KEY (salesforce_account_id) REFERENCES salesforce_accounts(salesforce_account_id);

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE dropbox_accounts IS 'Core table storing Dropbox account information and folder metadata';
COMMENT ON TABLE dropbox_account_application_info IS 'Stores person information extracted from application files (owners and joint owners)';
COMMENT ON TABLE dropbox_account_application_files IS 'Stores comprehensive file data and processing metadata';
COMMENT ON TABLE dropbox_account_client_list_info IS 'Stores data extracted from client list Excel files';
COMMENT ON TABLE dropbox_account_best_info IS 'Stores the best available information from both Dropbox sources (merged/consolidated)';
COMMENT ON TABLE salesforce_accounts IS 'Stores data from Salesforce CRM system';
COMMENT ON TABLE salesforce_households IS 'Stores Salesforce household relationships';
COMMENT ON TABLE salesforce_household_members IS 'Stores many-to-many relationship between households and members';
COMMENT ON TABLE dropbox_salesforce_mapping IS 'Links Dropbox accounts to Salesforce accounts';
COMMENT ON TABLE sync_status IS 'Tracks synchronization between Dropbox and Salesforce';
COMMENT ON TABLE account_analysis IS 'Stores analysis results comparing Dropbox and Salesforce data'; 