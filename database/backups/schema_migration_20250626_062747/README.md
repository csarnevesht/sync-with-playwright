# Database Management

This folder contains all database-related files, scripts, and utilities for the sync-with-playwright project.

## 📁 Folder Structure

### `/scripts/` - Database Management Scripts
- **`check_supabase_contents.py`** - Check what data is currently in the database
- **`clear_database_data.py`** - Clear all data from database tables
- **`force_clear_database.py`** - Force clear database by deleting records one by one
- **`reset_database.py`** - Complete database reset (drop and recreate schema)
- **`reset_database_simple.py`** - Simple database reset script
- **`create_tables_via_rest.py`** - Create tables via REST API
- **`create_new_schema.py`** - Create new database schema
- **`migrate_table_names.py`** - Migrate table names
- **`fix_supabase_auth.py`** - Fix Supabase authentication issues
- **`test_supabase_check.py`** - Test Supabase connectivity
- **`test_separated_approach.py`** - Test separated approach
- **`test_integration.py`** - Test database integration
- **`remove_legacy_tables.py`** - Remove legacy applications table and junction table
- **`generate_schema_diagram.py`** - Generate updated schema diagram

### `/schema/` - Database Schema Files
- **`schema.sql`** - Main database schema definition (updated - legacy tables removed)
- **`create_new_tables.sql`** - SQL to create new tables
- **`init.sql`** - Initial database setup script (updated - legacy tables removed)

### `/diagrams/` - Database Visualizations
- **`database_schema_diagram.html`** - Interactive database schema diagram (updated - legacy tables removed)
- **`database_schema_diagram.txt`** - Text-based database schema diagram
- **`database_schema_visual.txt`** - Visual database schema representation

### `/utils/` - Database Utilities
- **`manual_reset_instructions.md`** - Manual database reset instructions

## 🚀 Quick Start

### Check Database Contents
```bash
python database/scripts/check_supabase_contents.py
```

### Clear Database Data
```bash
python database/scripts/clear_database_data.py
```

### Reset Database (Complete)
```bash
python database/scripts/reset_database.py
```

### View Schema Diagram
Open `database/diagrams/database_schema_diagram.html` in your browser.

## 📋 Common Operations

### 1. Check Current Database State
```bash
python database/scripts/check_supabase_contents.py
```

### 2. Clear All Data (Keep Schema)
```bash
python database/scripts/clear_database_data.py
```

### 3. Complete Reset (Drop and Recreate)
```bash
python database/scripts/reset_database.py
```

### 4. Manual Reset via Supabase Dashboard
Follow instructions in `database/utils/manual_reset_instructions.md`

## 🔧 Troubleshooting

### Database Connection Issues
- Run `python database/scripts/test_supabase_check.py`
- Check environment variables in `.env` file

### Schema Issues
- Review `database/schema/schema.sql`
- Check `database/diagrams/database_schema_diagram.html`

### Data Issues
- Use `python database/scripts/check_supabase_contents.py` to inspect data
- Use `python database/scripts/clear_database_data.py` to clear data
- Use `python database/scripts/force_clear_database.py` for stubborn data

## 📊 Database Schema

The main schema is defined in `database/schema/schema.sql` and includes:

### **Core Tables:**
- **dropbox_accounts** - Dropbox account metadata and folder information
- **dropbox_account_application_info** - Person information extracted from applications (owners, joint owners)
- **dropbox_account_application_files** - Extracted application files with processing metadata

### **Key Features:**
- ✅ **Normalized Design** - Person info separated from file info
- ✅ **Flexible Relationships** - Same person can be owner/joint owner of multiple files
- ✅ **Processing Metadata** - OCR confidence, processing duration, model used
- ✅ **Structured Address Data** - Separate fields for street, city, state, zip
- ✅ **Status Tracking** - Processed, Failed, Error, Skipped statuses
- ✅ **Application Types** - Life Insurance, Annuity, EquiTrust, Security Benefit

### **Legacy Tables Removed:**
- ❌ **applications** - Legacy table (removed)
- ❌ **dropbox_account_applications** - Legacy junction table (removed)

The current schema is much more flexible and supports comprehensive file processing with detailed person information tracking.

For a visual representation, see `database/diagrams/database_schema_diagram.html`. 