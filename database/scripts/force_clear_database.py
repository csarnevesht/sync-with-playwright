#!/usr/bin/env python3
"""
Script to force clear all data from the database by deleting records one by one.
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

def force_clear_database():
    """Force clear all data from the database by deleting records one by one."""
    print("🗄️  FORCE CLEARING DATABASE")
    print("=" * 50)
    
    try:
        # Create Supabase client
        client = SupabaseClient()
        
        print("📋 Force clearing all existing data...")
        
        # List of all tables to clear (in dependency order - children first)
        tables_to_clear = [
            'dropbox_account_application_files',
            'dropbox_account_application_info', 
            'dropbox_account_applications',
            'dropbox_account_household_members',
            'applications',
            'household_members',
            'dropbox_accounts'
        ]
        
        # Clear each table by deleting records one by one
        for table in tables_to_clear:
            try:
                print(f"  Clearing table: {table}")
                
                # Get all records from the table
                result = client.client.table(table).select('id').execute()
                
                if result.data:
                    print(f"    Found {len(result.data)} records to delete")
                    
                    # Delete each record by ID
                    for record in result.data:
                        record_id = record['id']
                        try:
                            client.client.table(table).delete().eq('id', record_id).execute()
                            print(f"    ✅ Deleted record {record_id}")
                        except Exception as e:
                            print(f"    ❌ Failed to delete record {record_id}: {e}")
                else:
                    print(f"    Table {table} is already empty")
                    
            except Exception as e:
                print(f"  ⚠️  Could not access {table}: {e}")
        
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
        
        print("\n🎉 DATABASE FORCE CLEARED!")
        print("=" * 50)
        print("✅ All data has been removed from tables")
        print("✅ Database is ready for fresh data")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Database force clear failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def confirm_clear():
    """Ask for user confirmation before clearing."""
    print("⚠️  WARNING: This will completely clear your database!")
    print("   - All existing data will be permanently deleted")
    print("   - Records will be deleted one by one")
    print("   - This action cannot be undone")
    print()
    
    response = input("Are you sure you want to proceed? (type 'YES' to confirm): ")
    return response.strip() == 'YES'

if __name__ == '__main__':
    if confirm_clear():
        success = force_clear_database()
        if success:
            print("\n✅ Database force cleared successfully!")
        else:
            print("\n❌ Database force clear failed!")
    else:
        print("\n❌ Database force clear cancelled by user.") 