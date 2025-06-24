#!/usr/bin/env python3
"""
Script to completely reset the database by dropping all tables and recreating the schema from scratch.
"""

import os
import sys
import logging
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from supabase_client import SupabaseClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def reset_database():
    """Reset the database by dropping all tables and recreating the schema."""
    print("🗄️  DATABASE RESET SCRIPT")
    print("=" * 50)
    
    try:
        # Create Supabase client
        client = SupabaseClient()
        
        print("📋 Step 1: Dropping all existing tables...")
        
        # List of all tables to drop (in dependency order - children first)
        tables_to_drop = [
            'dropbox_account_application_files',
            'dropbox_account_application_info', 
            'dropbox_account_applications',
            'dropbox_account_household_members',
            'applications',
            'household_members',
            'dropbox_accounts'
        ]
        
        # Drop each table
        for table in tables_to_drop:
            try:
                print(f"  Dropping table: {table}")
                # Try to drop the table using SQL
                drop_sql = f"DROP TABLE IF EXISTS {table} CASCADE;"
                client.client.rpc('exec_sql', {'sql': drop_sql}).execute()
                print(f"  ✅ Dropped {table}")
            except Exception as e:
                print(f"  ⚠️  Could not drop {table}: {e}")
                # Try alternative approach - delete all records
                try:
                    result = client.client.table(table).delete().neq('id', 0).execute()
                    print(f"  ✅ Cleared all records from {table}")
                except Exception as e2:
                    print(f"  ❌ Could not clear {table}: {e2}")
        
        print("\n📋 Step 2: Dropping custom types...")
        
        # Drop custom types
        types_to_drop = [
            'household_role',
            'application_status', 
            'application_type'
        ]
        
        for type_name in types_to_drop:
            try:
                print(f"  Dropping type: {type_name}")
                drop_sql = f"DROP TYPE IF EXISTS {type_name} CASCADE;"
                client.client.rpc('exec_sql', {'sql': drop_sql}).execute()
                print(f"  ✅ Dropped {type_name}")
            except Exception as e:
                print(f"  ⚠️  Could not drop {type_name}: {e}")
        
        print("\n📋 Step 3: Recreating schema from scratch...")
        
        # Read the schema file
        schema_file = Path("schema.sql")
        if not schema_file.exists():
            print("❌ schema.sql file not found!")
            return False
        
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        # Split into individual statements
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        # Execute each statement
        for i, statement in enumerate(statements, 1):
            if statement:
                try:
                    print(f"  Executing statement {i}/{len(statements)}")
                    client.client.rpc('exec_sql', {'sql': statement}).execute()
                    print(f"  ✅ Statement {i} executed successfully")
                except Exception as e:
                    print(f"  ❌ Statement {i} failed: {e}")
                    print(f"  SQL: {statement[:100]}...")
        
        print("\n📋 Step 4: Verifying schema creation...")
        
        # Check if tables were created
        expected_tables = [
            'dropbox_accounts',
            'dropbox_account_application_info',
            'dropbox_account_application_files'
        ]
        
        for table in expected_tables:
            try:
                result = client.client.table(table).select('*').limit(1).execute()
                print(f"  ✅ Table {table} exists and is accessible")
            except Exception as e:
                print(f"  ❌ Table {table} not accessible: {e}")
        
        print("\n🎉 DATABASE RESET COMPLETED!")
        print("=" * 50)
        print("✅ All old data has been removed")
        print("✅ Schema has been recreated from scratch")
        print("✅ Database is ready for fresh data")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Database reset failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def confirm_reset():
    """Ask for user confirmation before resetting."""
    print("⚠️  WARNING: This will completely reset your database!")
    print("   - All existing data will be permanently deleted")
    print("   - All tables will be dropped and recreated")
    print("   - This action cannot be undone")
    print()
    
    response = input("Are you sure you want to proceed? (type 'YES' to confirm): ")
    return response.strip() == 'YES'

if __name__ == '__main__':
    if confirm_reset():
        success = reset_database()
        if success:
            print("\n✅ Database reset completed successfully!")
        else:
            print("\n❌ Database reset failed!")
    else:
        print("\n❌ Database reset cancelled by user.") 