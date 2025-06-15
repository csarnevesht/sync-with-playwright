-- Drop enum type if it exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'gender_type') THEN
        DROP TYPE gender_type CASCADE;
    END IF;
END$$;

-- Now create the enum type
CREATE TYPE gender_type AS ENUM ('Male', 'Female', 'Unknown');

-- Drop tables and indexes for a clean slate
DROP TABLE IF EXISTS application_household_members;
DROP TABLE IF EXISTS household_members;
DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS dropbox_accounts;

-- Create main tables
CREATE TABLE IF NOT EXISTS dropbox_accounts (
    id SERIAL PRIMARY KEY,
    folder TEXT NOT NULL,
    first_name TEXT,
    middle_name TEXT,
    last_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS applications (
    id SERIAL PRIMARY KEY,
    dropbox_account_id INTEGER REFERENCES dropbox_accounts(id),
    file_name VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    application_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    birthdate DATE,
    gender gender_type,
    address TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS household_members (
    id SERIAL PRIMARY KEY,
    dropbox_account_id INTEGER REFERENCES dropbox_accounts(id),
    first_name TEXT,
    middle_name TEXT,
    last_name TEXT,
    date_of_birth DATE,
    gender gender_type,
    is_household_head BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create junction tables for many-to-many relationships
CREATE TABLE IF NOT EXISTS application_household_members (
    application_id INTEGER REFERENCES applications(id),
    household_member_id INTEGER REFERENCES household_members(id),
    PRIMARY KEY (application_id, household_member_id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_dropbox_accounts_folder ON dropbox_accounts(folder);
CREATE INDEX IF NOT EXISTS idx_applications_dropbox_account_id ON applications(dropbox_account_id);
CREATE INDEX IF NOT EXISTS idx_household_members_dropbox_account_id ON household_members(dropbox_account_id);
CREATE INDEX IF NOT EXISTS idx_application_household_members_application_id ON application_household_members(application_id);
CREATE INDEX IF NOT EXISTS idx_application_household_members_household_member_id ON application_household_members(household_member_id); 
