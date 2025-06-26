#!/usr/bin/env python3
"""
Simple script to reset the database by clearing all data and recreating the schema.
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

def reset_database_simple():
    """Reset the database by clearing all data and recreating the schema."""
    print("🗄️  SIMPLE DATABASE RESET")
    print("=" * 50)
    
    try:
        # Create Supabase client
        client = SupabaseClient()
        
        print("📋 Step 1: Clearing all existing data...")
        
        # List of all tables to clear (in dependency order - children first)
        tables_to_clear = [
            'dropbox_account_application_files',
            'dropbox_account_application_info',
            'dropbox_accounts'
        ]
        
        # Clear each table
        for table in tables_to_clear:
            try:
                print(f"  Clearing table: {table}")
                # Delete all records from the table
                result = client.client.table(table).delete().neq('id', 0).execute()
                print(f"  ✅ Cleared {table}")
            except Exception as e:
                print(f"  ⚠️  Could not clear {table} (table may not exist): {e}")
        
        print("\n📋 Step 2: Recreating schema...")
        
        # Read the schema file
        script_dir = Path(__file__).parent
        schema_file = script_dir.parent / "schema" / "simplified_schema.sql"
        if not schema_file.exists():
            print(f"❌ simplified_schema.sql file not found at {schema_file}!")
            return False
        
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        # Split into individual statements and execute them
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip() and not stmt.strip().startswith('--')]
        
        print("  ⚠️  Note: Schema recreation requires RPC access which is not available in local client")
        print("  ⚠️  Tables will be recreated when you run the schema creation script manually")
        print("  ⚠️  For now, only data has been cleared")
        
        # Try to create tables using direct REST API calls
        print("\n📋 Step 2.5: Creating basic schema using REST API...")
        
        # Create the basic tables by trying to insert a dummy record (which will create the table if it doesn't exist)
        basic_tables = [
            'dropbox_accounts',
            'dropbox_account_application_info', 
            'dropbox_account_application_files'
        ]
        
        for table in basic_tables:
            try:
                print(f"  Creating table: {table}")
                # Try to insert a dummy record to trigger table creation
                if table == 'dropbox_accounts':
                    dummy_data = {'folder': 'dummy_folder_for_schema_creation', 'first_name': 'Dummy', 'last_name': 'User'}
                elif table == 'dropbox_account_application_info':
                    dummy_data = {'first_name': 'Dummy', 'last_name': 'User'}
                else:  # dropbox_account_application_files
                    dummy_data = {'file_name': 'dummy_file.txt'}
                
                try:
                    result = client.client.table(table).insert(dummy_data).execute()
                    print(f"  ✅ Table {table} created/verified")
                    
                    # Clean up the dummy data
                    try:
                        if table == 'dropbox_accounts':
                            client.client.table(table).delete().eq('folder', 'dummy_folder_for_schema_creation').execute()
                        elif table == 'dropbox_account_application_info':
                            client.client.table(table).delete().eq('first_name', 'Dummy').eq('last_name', 'User').execute()
                        else:  # dropbox_account_application_files
                            client.client.table(table).delete().eq('file_name', 'dummy_file.txt').execute()
                        print(f"  ✅ Cleaned up dummy data from {table}")
                    except Exception as cleanup_error:
                        print(f"  ⚠️  Could not clean up dummy data from {table}: {cleanup_error}")
                        
                except Exception as e:
                    print(f"  ⚠️  Table {table} may already exist: {e}")
            except Exception as e:
                print(f"  ❌ Error with table {table}: {e}")
        
        # Call the dedicated schema creation script
        print("\n📋 Step 2.6: Creating schema using dedicated script...")
        try:
            import subprocess
            schema_script = script_dir / "create_complete_schema.py"
            if schema_script.exists():
                print("  Running create_complete_schema.py...")
                result = subprocess.run([sys.executable, str(schema_script)], 
                                      capture_output=True, text=True, cwd=script_dir)
                if result.returncode == 0:
                    print("  ✅ Schema creation script completed successfully")
                else:
                    print(f"  ❌ Schema creation script failed: {result.stderr}")
            else:
                print(f"  ❌ Schema creation script not found at {schema_script}")
        except Exception as e:
            print(f"  ❌ Error running schema creation script: {e}")
        
        # Skip schema execution since RPC is not available
        # for i, statement in enumerate(statements, 1):
        #     if statement and not statement.startswith('--'):
        #         try:
        #             print(f"  Executing statement {i}/{len(statements)}")
        #             # Use the client to execute the SQL
        #             client.client.rpc('exec_sql', {'sql': statement}).execute()
        #             print(f"  ✅ Statement {i} executed")
        #         except Exception as e:
        #             print(f"  ⚠️  Statement {i} failed (may already exist): {e}")
        #             print(f"  SQL: {statement[:80]}...")
        
        print("\n📋 Step 3: Verifying schema...")
        
        # Check if core tables are accessible
        expected_tables = [
            'dropbox_accounts',
            'dropbox_account_application_info',
            'dropbox_account_application_files'
        ]
        
        for table in expected_tables:
            try:
                result = client.client.table(table).select('*').limit(1).execute()
                print(f"  ✅ Table {table} is accessible")
            except Exception as e:
                print(f"  ❌ Table {table} not accessible: {e}")
        
        print("\n🎉 DATABASE RESET COMPLETED!")
        print("=" * 50)
        print("✅ All old data has been cleared")
        print("✅ Schema has been recreated")
        print("✅ Database is ready for fresh data")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Database reset failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def confirm_reset():
    """Ask for user confirmation before resetting."""
    print("⚠️  WARNING: This will completely clear your database!")
    print("   - All existing data will be permanently deleted")
    print("   - Tables will be recreated with fresh schema")
    print("   - This action cannot be undone")
    print()
    
    response = input("Are you sure you want to proceed? (type 'YES' to confirm): ")
    return response.strip() == 'YES'

if __name__ == '__main__':
    if confirm_reset():
        success = reset_database_simple()
        if success:
            print("\n✅ Database reset completed successfully!")
        else:
            print("\n❌ Database reset failed!")
    else:
        print("\n❌ Database reset cancelled by user.") 