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