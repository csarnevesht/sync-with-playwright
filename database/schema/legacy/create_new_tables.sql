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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_files_file_name ON dropbox_account_application_files(file_name);
CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_files_dropbox_account_id ON dropbox_account_application_files(dropbox_account_id);
CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_files_status ON dropbox_account_application_files(status);
CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_info_names ON dropbox_account_application_info(first_name, last_name); 