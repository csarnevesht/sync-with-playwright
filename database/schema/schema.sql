-- Create enums
CREATE TYPE household_role AS ENUM ('Head', 'Member');
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
    dropbox_account_id INTEGER REFERENCES dropbox_accounts(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create dropbox_accounts table
CREATE TABLE IF NOT EXISTS dropbox_accounts (
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
);

-- Create household_members table
CREATE TABLE IF NOT EXISTS household_members (
    id SERIAL PRIMARY KEY,
    role household_role NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    stage VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50) NOT NULL,
    writing_advisor VARCHAR(255) NOT NULL,
    prospecting_status VARCHAR(100) NOT NULL,
    account_record_type VARCHAR(100) NOT NULL,
    mailing_address TEXT NOT NULL,
    ssn_tax_id VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create junction table for dropbox_accounts and household_members
CREATE TABLE IF NOT EXISTS dropbox_account_household_members (
    dropbox_account_id INTEGER REFERENCES dropbox_accounts(id),
    household_member_id INTEGER REFERENCES household_members(id),
    PRIMARY KEY (dropbox_account_id, household_member_id)
);

-- Add foreign key constraint for dropbox_account_application_files
ALTER TABLE dropbox_account_application_files 
ADD CONSTRAINT fk_dropbox_account_application_files_dropbox_account 
FOREIGN KEY (dropbox_account_id) REFERENCES dropbox_accounts(id);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_files_file_name ON dropbox_account_application_files(file_name);
CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_files_dropbox_account_id ON dropbox_account_application_files(dropbox_account_id);
CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_files_status ON dropbox_account_application_files(status);
CREATE INDEX IF NOT EXISTS idx_dropbox_accounts_folder ON dropbox_accounts(folder);
CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_info_names ON dropbox_account_application_info(first_name, last_name);
    
