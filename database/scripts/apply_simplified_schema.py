#!/usr/bin/env python3
"""
Script to apply the simplified database schema
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from supabase_client import SupabaseClient

def apply_simplified_schema():
    """Apply the simplified schema to the database"""
    print("🏗️ Applying simplified database schema...")
    
    try:
        # Create Supabase client
        client = SupabaseClient()
        
        # Read the simplified schema file
        schema_file = Path(__file__).parent.parent / 'schema' / 'simplified_schema.sql'
        
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
        
        print(f"\n✅ Schema application completed!")
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

def verify_schema():
    """Verify that the schema was applied correctly"""
    print("\n🔍 Verifying schema application...")
    
    try:
        client = SupabaseClient()
        
        # Check for expected tables
        expected_tables = [
            'dropbox_accounts',
            'dropbox_account_application_info',
            'dropbox_account_application_files',
            'dropbox_account_client_list_info',
            'dropbox_account_best_info'
        ]
        
        for table_name in expected_tables:
            try:
                # Try to query the table to see if it exists
                result = client.client.table(table_name).select('*').limit(1).execute()
                print(f"  ✅ Table '{table_name}' exists and is accessible")
            except Exception as e:
                print(f"  ❌ Table '{table_name}' not found or not accessible: {e}")
        
        print("🔍 Schema verification completed!")
        
    except Exception as e:
        print(f"❌ Error verifying schema: {e}")

def main():
    """Main function"""
    print("=" * 60)
    print("DATABASE SCHEMA APPLICATION")
    print("=" * 60)
    
    # Apply the schema
    success = apply_simplified_schema()
    
    if success:
        # Verify the schema
        verify_schema()
        
        print("\n" + "=" * 60)
        print("🎉 SCHEMA APPLICATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Test basic functionality:")
        print("   python -m sync.cmd_runner --dropbox-accounts")
        print("2. Check database contents:")
        print("   python database/scripts/check_supabase_contents.py")
        print("3. Run a full test:")
        print("   python -m sync.cmd_runner --dropbox-accounts --dropbox-account-info")
    else:
        print("\n" + "=" * 60)
        print("❌ SCHEMA APPLICATION FAILED!")
        print("=" * 60)
        print("\nTroubleshooting:")
        print("1. Check your database connection")
        print("2. Verify you have the necessary permissions")
        print("3. Check the error messages above")
        print("4. Try running: python database/scripts/reset_database.py")

if __name__ == "__main__":
    main() 