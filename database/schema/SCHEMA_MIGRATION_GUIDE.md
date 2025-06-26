# Database Schema Migration Guide

## Overview

This guide helps you migrate from the current fragmented schema to a new consolidated, consistent database design. The new schema addresses several issues with the current setup:

### Current Issues
1. **Schema Fragmentation** - Multiple schema files with overlapping definitions
2. **Inconsistent Naming** - Different field names across tables (e.g., `date_of_birth` vs `birthdate`)
3. **Missing Core Table** - The `dropbox_accounts` table is referenced but not consistently defined
4. **Salesforce Integration Complexity** - The complete schema includes Salesforce tables that may not be needed yet

### New Schema Benefits
1. **Consolidated Design** - Single, consistent schema file
2. **Clear Data Flow** - Well-defined relationships between tables
3. **Flexible Architecture** - Supports both simple and complex use cases
4. **Future-Proof** - Easy to extend with Salesforce integration when needed

## Schema Options

### Option 1: Simplified Schema (Recommended for immediate use)
**File:** `database/schema/simplified_schema.sql`

**Features:**
- Core Dropbox functionality only
- 5 main tables focused on Dropbox data processing
- No Salesforce complexity
- Perfect for development and testing

**Tables:**
1. `dropbox_accounts` - Core account metadata
2. `dropbox_account_application_info` - Person information from applications
3. `dropbox_account_application_files` - File processing data
4. `dropbox_account_client_list_info` - Client list data
5. `dropbox_account_best_info` - Merged/consolidated data

### Option 2: Complete Schema (For full Salesforce integration)
**File:** `database/schema/consolidated_schema.sql`

**Features:**
- Full Dropbox + Salesforce integration
- 11 tables with comprehensive mapping and sync
- Advanced analysis and relationship tracking
- Production-ready for complex workflows

**Additional Tables:**
6. `salesforce_accounts` - Salesforce account data
7. `salesforce_households` - Household relationships
8. `salesforce_household_members` - Household members
9. `dropbox_salesforce_mapping` - Cross-system mapping
10. `sync_status` - Synchronization tracking
11. `account_analysis` - Analysis results

## Migration Steps

### Step 1: Backup Current Data
```bash
# Create a backup of your current database
python database/scripts/backup_database.py
```

### Step 2: Choose Your Schema
Decide which schema to use based on your needs:

- **Use Simplified Schema** if you're focusing on Dropbox processing only
- **Use Complete Schema** if you need full Salesforce integration

### Step 3: Reset Database
```bash
# Clear existing data and schema
python database/scripts/reset_database.py

# Or for a complete reset
python database/scripts/force_clear_database.py
```

### Step 4: Apply New Schema
```bash
# For simplified schema
python database/scripts/apply_simplified_schema.py

# For complete schema
python database/scripts/apply_consolidated_schema.py
```

### Step 5: Verify Schema
```bash
# Check that all tables were created correctly
python database/scripts/check_supabase_contents.py

# Test basic operations
python database/scripts/test_schema_operations.py
```

## Schema Comparison

### Field Name Standardization

| Old Field Names | New Standardized Names | Notes |
|----------------|----------------------|-------|
| `date_of_birth` | `date_of_birth` (application_info)<br>`birthdate` (client_list_info) | Consistent with source context |
| `phone_number` | `phone_number` (application_info)<br>`phone` (client_list_info) | Consistent with source context |
| `email_address` | `email_address` (application_info)<br>`email` (client_list_info) | Consistent with source context |

### Table Structure Changes

#### Before (Fragmented)
```
- schema.sql (basic tables)
- create_complete_account_schema.sql (full schema)
- create_client_list_table.sql (client list only)
- create_new_tables.sql (additional tables)
- init.sql (initialization)
```

#### After (Consolidated)
```
- simplified_schema.sql (core functionality)
- consolidated_schema.sql (full functionality)
```

### Key Improvements

1. **Consistent Naming** - All field names follow a consistent pattern
2. **Clear Relationships** - Foreign key constraints are properly defined
3. **Comprehensive Indexing** - Performance indexes for all common queries
4. **Documentation** - Table and field comments for clarity
5. **Data Integrity** - Proper constraints and validation

## Data Migration

If you have existing data that needs to be preserved:

### Step 1: Export Current Data
```bash
python database/scripts/export_current_data.py
```

### Step 2: Transform Data
```bash
python database/scripts/transform_data_for_new_schema.py
```

### Step 3: Import Transformed Data
```bash
python database/scripts/import_transformed_data.py
```

## Testing the New Schema

### Basic Functionality Test
```bash
# Test Dropbox account creation
python -m sync.cmd_runner --dropbox-accounts --dropbox-account-info

# Test file processing
python -m sync.cmd_runner --dropbox-account-files

# Test client list processing
python -m sync.cmd_runner --dropbox-account-info
```

### Advanced Testing (Complete Schema Only)
```bash
# Test Salesforce integration
python -m sync.cmd_runner --salesforce-accounts --salesforce-account-info

# Test mapping functionality
python database/scripts/test_mapping_functionality.py

# Test sync operations
python database/scripts/test_sync_operations.py
```

## Troubleshooting

### Common Issues

1. **Foreign Key Constraint Errors**
   - Ensure all referenced tables exist
   - Check that data types match between tables

2. **Index Creation Failures**
   - Some indexes may already exist
   - Use `IF NOT EXISTS` to avoid conflicts

3. **Enum Type Conflicts**
   - The schema includes cleanup for existing enum types
   - If issues persist, manually drop and recreate

### Rollback Plan

If you need to rollback to the previous schema:

```bash
# Restore from backup
python database/scripts/restore_from_backup.py

# Or recreate old schema
python database/scripts/recreate_old_schema.py
```

## Next Steps

After successful migration:

1. **Update Application Code** - Ensure your application uses the new schema
2. **Update Documentation** - Update any schema documentation
3. **Performance Tuning** - Monitor query performance and adjust indexes as needed
4. **Data Validation** - Verify that all data migrated correctly

## Support

If you encounter issues during migration:

1. Check the logs in `database/scripts/logs/`
2. Review the troubleshooting section above
3. Use the rollback plan if needed
4. Contact the development team for assistance

---

**Note:** This migration guide assumes you're using Supabase as your database provider. Adjust the commands and scripts according to your specific database setup. 