-- ============================================================================
-- SIMPLIFIED DATABASE SCHEMA
-- ============================================================================
-- This schema focuses on core Dropbox functionality without Salesforce complexity
-- Use this for immediate development and testing

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
END$$;

-- Create enums
CREATE TYPE application_status AS ENUM ('Processed', 'Failed', 'Error', 'Skipped');
CREATE TYPE application_type AS ENUM ('Life Insurance', 'Annuity', 'EquiTrust Annuity', 'Security Benefit', 'Unknown');

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

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE dropbox_accounts IS 'Core table storing Dropbox account information and folder metadata';
COMMENT ON TABLE dropbox_account_application_info IS 'Stores person information extracted from application files (owners and joint owners)';
COMMENT ON TABLE dropbox_account_application_files IS 'Stores comprehensive file data and processing metadata';
COMMENT ON TABLE dropbox_account_client_list_info IS 'Stores data extracted from client list Excel files';
COMMENT ON TABLE dropbox_account_best_info IS 'Stores the best available information from both Dropbox sources (merged/consolidated)';
