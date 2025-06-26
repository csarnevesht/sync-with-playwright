#!/usr/bin/env python3
"""
Script to update all schema file references to use the new consolidated schema
"""

import os
import re
import shutil
from pathlib import Path
from datetime import datetime

def backup_files():
    """Create backups of files that will be modified"""
    backup_dir = Path('database/backups') / f"schema_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    files_to_backup = [
        'database/README.md',
        'database/utils/manual_reset_instructions.md',
        'database/scripts/reset_database.py',
        'database/scripts/reset_database_simple.py',
        'database/scripts/create_complete_schema.py',
        'database/scripts/create_tables_direct.py',
        'database/scripts/create_client_list_table.py',
        'database/scripts/create_tables_via_rest.py'
    ]
    
    print(f"📦 Creating backups in: {backup_dir}")
    
    for file_path in files_to_backup:
        if Path(file_path).exists():
            backup_path = backup_dir / Path(file_path).name
            shutil.copy2(file_path, backup_path)
            print(f"  ✅ Backed up: {file_path}")
    
    return backup_dir

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
    
    print("🔄 Updating file references...")
    
    for file_path in files_to_update:
        if Path(file_path).exists():
            print(f"  📝 Processing: {file_path}")
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            original_content = content
            
            # Apply replacements
            for old, new in replacements.items():
                content = content.replace(old, new)
            
            # Write back if changes were made
            if content != original_content:
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"    ✅ Updated references in {file_path}")
            else:
                print(f"    ℹ️  No changes needed in {file_path}")
        else:
            print(f"    ⚠️  File not found: {file_path}")

def create_legacy_directory():
    """Create legacy directory and move old schema files"""
    legacy_dir = Path('database/schema/legacy')
    legacy_dir.mkdir(exist_ok=True)
    
    old_files = [
        'database/schema/schema.sql',
        'database/schema/init.sql',
        'database/schema/create_client_list_table.sql',
        'database/schema/create_new_tables.sql',
        'database/schema/create_complete_account_schema.sql'
    ]
    
    print(f"📁 Moving old schema files to: {legacy_dir}")
    
    for file_path in old_files:
        if Path(file_path).exists():
            legacy_path = legacy_dir / Path(file_path).name
            shutil.move(file_path, legacy_path)
            print(f"  ✅ Moved: {file_path} -> {legacy_path}")
        else:
            print(f"  ⚠️  File not found: {file_path}")

def add_deprecation_warnings():
    """Add deprecation warnings to old scripts"""
    old_scripts = [
        'database/scripts/create_complete_schema.py',
        'database/scripts/create_tables_direct.py',
        'database/scripts/create_client_list_table.py',
        'database/scripts/create_tables_via_rest.py'
    ]
    
    deprecation_warning = '''
import warnings

def deprecated_warning():
    warnings.warn(
        "This script is deprecated. Use 'python database/scripts/apply_simplified_schema.py' instead.",
        DeprecationWarning,
        stacklevel=2
    )

# Add deprecation warning
deprecated_warning()
'''
    
    print("⚠️  Adding deprecation warnings to old scripts...")
    
    for script_path in old_scripts:
        if Path(script_path).exists():
            with open(script_path, 'r') as f:
                content = f.read()
            
            # Check if deprecation warning already exists
            if 'deprecated_warning' not in content:
                # Add deprecation warning after imports
                lines = content.split('\n')
                new_lines = []
                imports_done = False
                
                for line in lines:
                    new_lines.append(line)
                    
                    # Add deprecation warning after imports
                    if not imports_done and (line.startswith('import ') or line.startswith('from ')):
                        continue
                    elif not imports_done and line.strip() and not line.startswith('#'):
                        # We've reached the end of imports
                        new_lines.append(deprecation_warning)
                        imports_done = True
                
                content = '\n'.join(new_lines)
                
                with open(script_path, 'w') as f:
                    f.write(content)
                
                print(f"  ✅ Added deprecation warning to: {script_path}")
            else:
                print(f"  ℹ️  Deprecation warning already exists in: {script_path}")

def create_unified_schema_script():
    """Create a unified script to apply any schema type"""
    unified_script = '''#!/usr/bin/env python3
"""
Unified script to apply any schema type
"""

import os
import sys
import argparse
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from supabase_client import SupabaseClient

def apply_schema(schema_type='simplified'):
    """Apply the specified schema type"""
    print(f"🏗️ Applying {schema_type} schema...")
    
    try:
        # Create Supabase client
        client = SupabaseClient()
        
        # Determine schema file
        if schema_type == 'simplified':
            schema_file = Path(__file__).parent.parent / 'schema' / 'simplified_schema.sql'
        elif schema_type == 'consolidated':
            schema_file = Path(__file__).parent.parent / 'schema' / 'consolidated_schema.sql'
        else:
            raise ValueError(f"Unknown schema type: {schema_type}")
        
        if not schema_file.exists():
            print(f"❌ Schema file not found: {schema_file}")
            return False
        
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        print(f"📄 Read schema from: {schema_file}")
        print(f"📊 Schema size: {len(schema_sql)} characters")
        
        # Split into individual statements and execute them
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip() and not stmt.strip().startswith('--')]
        
        print(f"🔧 Executing {len(statements)} SQL statements...")
        
        success_count = 0
        error_count = 0
        
        for i, statement in enumerate(statements, 1):
            try:
                if statement.strip():
                    print(f"  [{i}/{len(statements)}] Executing statement...")
                    # Execute the SQL statement
                    client.client.rpc('exec_sql', {'sql': statement}).execute()
                    success_count += 1
            except Exception as e:
                print(f"  ❌ Error executing statement {i}: {e}")
                error_count += 1
                # Continue with other statements
        
        print(f"\\n✅ Schema application completed!")
        print(f"   Success: {success_count} statements")
        print(f"   Errors: {error_count} statements")
        
        if error_count == 0:
            print("🎉 All schema statements executed successfully!")
            return True
        else:
            print("⚠️  Some statements failed. Check the errors above.")
            return False
            
    except Exception as e:
        print(f"❌ Error applying schema: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Apply database schema')
    parser.add_argument('--schema-type', choices=['simplified', 'consolidated'], 
                       default='simplified', help='Schema type to apply (default: simplified)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("UNIFIED SCHEMA APPLICATION")
    print("=" * 60)
    
    success = apply_schema(args.schema_type)
    
    if success:
        print("\\n" + "=" * 60)
        print("🎉 SCHEMA APPLICATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\\nNext steps:")
        print("1. Test basic functionality:")
        print("   python -m sync.cmd_runner --dropbox-accounts")
        print("2. Check database contents:")
        print("   python database/scripts/check_supabase_contents.py")
    else:
        print("\\n" + "=" * 60)
        print("❌ SCHEMA APPLICATION FAILED!")
        print("=" * 60)

if __name__ == "__main__":
    main()
'''
    
    unified_script_path = Path('database/scripts/apply_schema.py')
    
    with open(unified_script_path, 'w') as f:
        f.write(unified_script)
    
    # Make executable
    os.chmod(unified_script_path, 0o755)
    
    print(f"✅ Created unified schema script: {unified_script_path}")

def main():
    """Main migration function"""
    print("=" * 60)
    print("LEGACY SCHEMA MIGRATION")
    print("=" * 60)
    
    # Step 1: Create backups
    backup_dir = backup_files()
    
    # Step 2: Update file references
    update_file_references()
    
    # Step 3: Create legacy directory and move old files
    create_legacy_directory()
    
    # Step 4: Add deprecation warnings
    add_deprecation_warnings()
    
    # Step 5: Create unified schema script
    create_unified_schema_script()
    
    print("\n" + "=" * 60)
    print("🎉 MIGRATION COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print(f"\n📦 Backups created in: {backup_dir}")
    print("\n📋 Summary of changes:")
    print("✅ Updated all script references to use new schema files")
    print("✅ Moved old schema files to database/schema/legacy/")
    print("✅ Added deprecation warnings to old scripts")
    print("✅ Created unified schema application script")
    print("\n🚀 Next steps:")
    print("1. Test the new schema:")
    print("   python database/scripts/apply_schema.py")
    print("2. Test basic functionality:")
    print("   python -m sync.cmd_runner --dropbox-accounts")
    print("3. Check database contents:")
    print("   python database/scripts/check_supabase_contents.py")
    print("\n📚 Documentation:")
    print("- database/schema/SCHEMA_MIGRATION_GUIDE.md")
    print("- database/schema/LEGACY_SCHEMA_MIGRATION_STRATEGY.md")

if __name__ == "__main__":
    main() 