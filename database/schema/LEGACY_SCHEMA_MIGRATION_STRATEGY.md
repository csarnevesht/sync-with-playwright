# Legacy Schema Migration Strategy

## Overview

This document outlines the strategy for handling old schema files and existing scripts that reference them during the migration to the new consolidated schema.

## 📊 Current State Analysis

### Old Schema Files Still in Use

| File | Referenced By | Status | Action Required |
|------|---------------|--------|-----------------|
| `schema.sql` | `database/README.md`, `database/utils/manual_reset_instructions.md` | ✅ Active | Update references |
| `create_complete_account_schema.sql` | `database/scripts/create_complete_schema.py`, `database/scripts/create_tables_direct.py` | ✅ Active | Update references |
| `init.sql` | `database/scripts/reset_database.py`, `database/scripts/reset_database_simple.py` | ✅ Active | Update references |
| `create_client_list_table.sql` | `database/scripts/create_client_list_table.py`, `database/scripts/create_tables_via_rest.py` | ✅ Active | Update references |
| `create_new_tables.sql` | `database/scripts/create_tables_via_rest.py` | ✅ Active | Update references |

### Scripts That Need Updates

| Script | Current Schema Reference | New Schema Reference | Priority |
|--------|-------------------------|---------------------|----------|
| `create_complete_schema.py` | `create_complete_account_schema.sql` | `consolidated_schema.sql` | High |
| `create_tables_direct.py` | `create_complete_account_schema.sql` | `consolidated_schema.sql` | High |
| `reset_database.py` | `init.sql` | `simplified_schema.sql` | High |
| `reset_database_simple.py` | `init.sql` | `simplified_schema.sql` | High |
| `create_client_list_table.py` | `create_client_list_table.sql` | `simplified_schema.sql` | Medium |
| `create_tables_via_rest.py` | Multiple old files | `simplified_schema.sql` | Medium |

## 🎯 Migration Strategy

### Phase 1: Immediate Actions (Recommended)

#### 1.1 Update High-Priority Scripts

**Update `database/scripts/reset_database.py`:**
```python
# Change from:
schema_file = script_dir.parent / "schema" / "init.sql"

# To:
schema_file = script_dir.parent / "schema" / "simplified_schema.sql"
```

**Update `database/scripts/reset_database_simple.py`:**
```python
# Change from:
schema_file = script_dir.parent / "schema" / "init.sql"

# To:
schema_file = script_dir.parent / "schema" / "simplified_schema.sql"
```

#### 1.2 Update Documentation

**Update `database/README.md`:**
```markdown
# Change from:
- **`schema.sql`** - Main database schema definition
- **`init.sql`** - Initial database setup script

# To:
- **`simplified_schema.sql`** - Core database schema (recommended)
- **`consolidated_schema.sql`** - Complete schema with Salesforce integration
```

**Update `database/utils/manual_reset_instructions.md`:**
```markdown
# Change from:
Copy and paste the entire contents of `schema.sql` into the SQL editor

# To:
Copy and paste the entire contents of `simplified_schema.sql` into the SQL editor
```

### Phase 2: Script Consolidation

#### 2.1 Create New Unified Scripts

**Create `database/scripts/apply_schema.py`:**
```python
#!/usr/bin/env python3
"""
Unified script to apply any schema type
"""

import argparse
from pathlib import Path

def apply_schema(schema_type='simplified'):
    """Apply the specified schema type"""
    if schema_type == 'simplified':
        schema_file = Path(__file__).parent.parent / 'schema' / 'simplified_schema.sql'
    elif schema_type == 'consolidated':
        schema_file = Path(__file__).parent.parent / 'schema' / 'consolidated_schema.sql'
    else:
        raise ValueError(f"Unknown schema type: {schema_type}")
    
    # Apply the schema
    # ... implementation ...

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--schema-type', choices=['simplified', 'consolidated'], 
                       default='simplified', help='Schema type to apply')
    args = parser.parse_args()
    
    apply_schema(args.schema_type)
```

#### 2.2 Deprecate Old Scripts

**Add deprecation warnings to old scripts:**
```python
import warnings

def deprecated_warning():
    warnings.warn(
        "This script is deprecated. Use 'python database/scripts/apply_schema.py' instead.",
        DeprecationWarning,
        stacklevel=2
    )

# Add to old scripts
deprecated_warning()
```

### Phase 3: File Organization

#### 3.1 Create Legacy Directory

```bash
# Create legacy directory
mkdir -p database/schema/legacy

# Move old files
mv database/schema/schema.sql database/schema/legacy/
mv database/schema/init.sql database/schema/legacy/
mv database/schema/create_client_list_table.sql database/schema/legacy/
mv database/schema/create_new_tables.sql database/schema/legacy/
mv database/schema/create_complete_account_schema.sql database/schema/legacy/
```

#### 3.2 Update All References

**Create a script to update all references:**
```python
#!/usr/bin/env python3
"""
Script to update all schema file references
"""

import os
import re
from pathlib import Path

def update_file_references():
    """Update all file references to use new schema files"""
    
    # Files to update
    files_to_update = [
        'database/README.md',
        'database/utils/manual_reset_instructions.md',
        'database/scripts/reset_database.py',
        'database/scripts/reset_database_simple.py',
        'database/scripts/create_complete_schema.py',
        'database/scripts/create_tables_direct.py',
        'database/scripts/create_client_list_table.py',
        'database/scripts/create_tables_via_rest.py'
    ]
    
    # Replacement mappings
    replacements = {
        'schema.sql': 'simplified_schema.sql',
        'init.sql': 'simplified_schema.sql',
        'create_complete_account_schema.sql': 'consolidated_schema.sql',
        'create_client_list_table.sql': 'simplified_schema.sql',
        'create_new_tables.sql': 'simplified_schema.sql'
    }
    
    for file_path in files_to_update:
        if Path(file_path).exists():
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Apply replacements
            for old, new in replacements.items():
                content = content.replace(old, new)
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            print(f"✅ Updated {file_path}")

if __name__ == "__main__":
    update_file_references()
```

## 🔄 Migration Options

### Option 1: Gradual Migration (Recommended)

1. **Keep old files** but mark them as deprecated
2. **Update scripts gradually** to use new schema files
3. **Test each change** before moving to the next
4. **Move old files to legacy directory** after all updates are complete

### Option 2: Immediate Migration

1. **Update all references** at once
2. **Move old files** to legacy directory immediately
3. **Test everything** to ensure it works
4. **Rollback** if issues are found

### Option 3: Hybrid Approach

1. **Update high-priority scripts** immediately
2. **Keep old files** for backward compatibility
3. **Gradually update** remaining scripts
4. **Remove old files** when no longer needed

## 📋 Implementation Checklist

### Phase 1: Immediate Updates
- [ ] Update `reset_database.py` to use `simplified_schema.sql`
- [ ] Update `reset_database_simple.py` to use `simplified_schema.sql`
- [ ] Update `database/README.md` documentation
- [ ] Update `manual_reset_instructions.md`
- [ ] Test basic functionality

### Phase 2: Script Consolidation
- [ ] Create `apply_schema.py` unified script
- [ ] Add deprecation warnings to old scripts
- [ ] Update remaining script references
- [ ] Test all scripts work correctly

### Phase 3: Cleanup
- [ ] Create `database/schema/legacy/` directory
- [ ] Move old schema files to legacy directory
- [ ] Update any remaining references
- [ ] Remove deprecated scripts (optional)

## 🧪 Testing Strategy

### Before Migration
```bash
# Test current functionality
python -m sync.cmd_runner --dropbox-accounts --dropbox-account-info
python database/scripts/check_supabase_contents.py
```

### During Migration
```bash
# Test each script after update
python database/scripts/reset_database.py
python database/scripts/apply_simplified_schema.py
python -m sync.cmd_runner --dropbox-accounts
```

### After Migration
```bash
# Comprehensive testing
python database/scripts/check_supabase_contents.py
python -m sync.cmd_runner --dropbox-accounts --dropbox-account-info --dropbox-account-files
```

## 🚨 Rollback Plan

If issues arise during migration:

1. **Restore old schema files** from version control
2. **Revert script changes** to use old schema files
3. **Test functionality** to ensure everything works
4. **Investigate issues** before attempting migration again

## 📞 Support

If you encounter issues:

1. **Check the logs** in `database/scripts/logs/`
2. **Review this migration strategy**
3. **Use the rollback plan** if needed
4. **Contact the development team** for assistance

---

**Recommendation:** Use the **Gradual Migration (Option 1)** approach to minimize risk and ensure a smooth transition.
