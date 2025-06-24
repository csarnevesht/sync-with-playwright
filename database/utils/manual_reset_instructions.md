# Manual Database Reset Instructions

If the automated scripts don't work, you can manually reset the database through the Supabase dashboard.

## Step 1: Access Supabase Dashboard

1. Go to your Supabase project dashboard
2. Navigate to the **SQL Editor** section

## Step 2: Drop All Tables

Run these SQL commands in order:

```sql
-- Drop tables in dependency order (children first)
DROP TABLE IF EXISTS dropbox_account_application_files CASCADE;
DROP TABLE IF EXISTS dropbox_account_application_info CASCADE;
DROP TABLE IF EXISTS dropbox_account_applications CASCADE;
DROP TABLE IF EXISTS dropbox_account_household_members CASCADE;
DROP TABLE IF EXISTS applications CASCADE;
DROP TABLE IF EXISTS household_members CASCADE;
DROP TABLE IF EXISTS dropbox_accounts CASCADE;
```

## Step 3: Drop Custom Types

```sql
-- Drop custom types
DROP TYPE IF EXISTS household_role CASCADE;
DROP TYPE IF EXISTS application_status CASCADE;
DROP TYPE IF EXISTS application_type CASCADE;
```

## Step 4: Recreate Schema

Copy and paste the entire contents of `schema.sql` into the SQL editor and execute it.

## Step 5: Verify

Run this query to verify the tables were created:

```sql
-- Check if tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
    'dropbox_accounts',
    'dropbox_account_application_info',
    'dropbox_account_application_files'
);
```

## Alternative: Quick Reset

If you just want to clear all data without dropping tables:

```sql
-- Clear all data from tables
TRUNCATE TABLE dropbox_account_application_files CASCADE;
TRUNCATE TABLE dropbox_account_application_info CASCADE;
TRUNCATE TABLE dropbox_account_applications CASCADE;
TRUNCATE TABLE dropbox_account_household_members CASCADE;
TRUNCATE TABLE applications CASCADE;
TRUNCATE TABLE household_members CASCADE;
TRUNCATE TABLE dropbox_accounts CASCADE;
```

Then run the schema creation SQL to ensure the structure is correct. 