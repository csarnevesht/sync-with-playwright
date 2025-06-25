#!/usr/bin/env python3
"""
Migration script to rename file-related fields in dropbox_accounts table
This makes the field names more specific about account application files.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from supabase_client import SupabaseClient

def migrate_file_field_names():
    """Migrate the file field names to be more specific about account application files."""
    print("🔄 Migrating file field names in dropbox_accounts table...")
    
    try:
        # Create Supabase client
        client = SupabaseClient()
        
        # Read the migration SQL
        sql_file_path = os.path.join(os.path.dirname(__file__), '..', 'schema', 'rename_file_fields.sql')
        
        if not os.path.exists(sql_file_path):
            print(f"❌ SQL file not found: {sql_file_path}")
            return False
        
        with open(sql_file_path, 'r') as f:
            sql_script = f.read()
        
        print("📋 Executing field name migration...")
        print("=" * 60)
        
        # Execute the SQL script
        try:
            # Split the script into individual statements
            statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
            
            for i, statement in enumerate(statements, 1):
                if statement:
                    print(f"Executing statement {i}/{len(statements)}...")
                    print(f"SQL: {statement[:100]}...")
                    
                    # Execute the statement using RPC
                    result = client.client.rpc('exec_sql', {'sql': statement}).execute()
                    
                    if hasattr(result, 'data') and result.data:
                        print(f"✅ Statement {i} executed successfully")
                    else:
                        print(f"⚠️ Statement {i} executed (no data returned)")
                    
                    print()
            
            print("✅ File field names migrated successfully!")
            print()
            print("📊 Field name changes:")
            print("   - total_files → total_account_application_files")
            print("   - processed_files → processed_account_application_files")
            print("   - failed_files → failed_account_application_files")
            print()
            print("🔍 The field names are now more specific and clearly indicate")
            print("   that these fields track account application files specifically.")
            
            return True
            
        except Exception as e:
            print(f"❌ Error executing SQL: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False

if __name__ == "__main__":
    success = migrate_file_field_names()
    if success:
        print("\n✅ Field name migration completed successfully!")
    else:
        print("\n❌ Field name migration failed!")
        sys.exit(1) 