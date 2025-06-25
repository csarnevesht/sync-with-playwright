-- Migration script to rename file-related fields in dropbox_accounts table
-- This makes the field names more specific to account application files

-- Rename columns to be more specific about account application files
ALTER TABLE dropbox_accounts 
RENAME COLUMN total_files TO total_account_application_files;

ALTER TABLE dropbox_accounts 
RENAME COLUMN processed_files TO processed_account_application_files;

ALTER TABLE dropbox_accounts 
RENAME COLUMN failed_files TO failed_account_application_files;

-- Add comments to explain the renamed fields
COMMENT ON COLUMN dropbox_accounts.total_account_application_files IS 'Total number of account application files found in the Dropbox folder';
COMMENT ON COLUMN dropbox_accounts.processed_account_application_files IS 'Number of account application files successfully processed to extract account information';
COMMENT ON COLUMN dropbox_accounts.failed_account_application_files IS 'Number of account application files that failed to process or encountered errors';

-- Update any existing indexes that reference the old column names
-- (PostgreSQL will automatically update indexes when columns are renamed) 