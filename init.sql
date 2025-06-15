-- Create enum types if they don't exist
DO $$ BEGIN
    CREATE TYPE gender_type AS ENUM ('Male', 'Female', 'Unknown');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create tables if they don't exist
CREATE TABLE IF NOT EXISTS dropbox_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    folder_name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dropbox_account_id UUID REFERENCES dropbox_accounts(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    dob DATE,
    gender gender_type,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS household_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dropbox_account_id UUID REFERENCES dropbox_accounts(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    dob DATE,
    gender gender_type,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create junction tables for many-to-many relationships
CREATE TABLE IF NOT EXISTS application_household_members (
    application_id UUID REFERENCES applications(id) ON DELETE CASCADE,
    household_member_id UUID REFERENCES household_members(id) ON DELETE CASCADE,
    PRIMARY KEY (application_id, household_member_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_dropbox_accounts_folder_name ON dropbox_accounts(folder_name);
CREATE INDEX IF NOT EXISTS idx_applications_dropbox_account_id ON applications(dropbox_account_id);
CREATE INDEX IF NOT EXISTS idx_household_members_dropbox_account_id ON household_members(dropbox_account_id); 
