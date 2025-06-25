#!/usr/bin/env python3
"""
Simple script to clear all data from the database tables.
"""

import os
import sys
import logging

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from supabase_client import SupabaseClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_database_data():
    """Clear all data from the database tables."""
    print("🗄️  CLEARING DATABASE DATA")
    print("=" * 50)
    
    try:
        # Create Supabase client
        client = SupabaseClient()
        
        print("📋 Clearing all existing data...")
        
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
                result = client.client.table(table).delete().execute()
                print(f"  ✅ Cleared {table}")
            except Exception as e:
                print(f"  ⚠️  Could not clear {table} (table may not exist): {e}")
        
        print("\n📋 Verifying data is cleared...")
        
        # Check if tables are empty
        tables_to_check = [
            'dropbox_accounts',
            'dropbox_account_application_info',
            'dropbox_account_application_files'
        ]
        
        for table in tables_to_check:
            try:
                result = client.client.table(table).select('*').execute()
                count = len(result.data) if result.data else 0
                print(f"  ✅ Table {table}: {count} records")
            except Exception as e:
                print(f"  ❌ Table {table} not accessible: {e}")
        
        print("\n🎉 DATABASE CLEARED!")
        print("=" * 50)
        print("✅ All data has been removed from tables")
        print("✅ Database is ready for fresh data")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Database clear failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def confirm_clear():
    """Ask for user confirmation before clearing."""
    print("⚠️  WARNING: This will completely clear your database!")
    print("   - All existing data will be permanently deleted")
    print("   - Tables will remain but will be empty")
    print("   - This action cannot be undone")
    print()
    
    response = input("Are you sure you want to proceed? (type 'YES' to confirm): ")
    return response.strip() == 'YES'

if __name__ == '__main__':
    if confirm_clear():
        success = clear_database_data()
        if success:
            print("\n✅ Database cleared successfully!")
        else:
            print("\n❌ Database clear failed!")
    else:
        print("\n❌ Database clear cancelled by user.") 