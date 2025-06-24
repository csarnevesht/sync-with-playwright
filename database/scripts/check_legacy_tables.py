#!/usr/bin/env python3
"""
Check for Legacy Tables Script

This script checks for any remaining legacy tables in the database
and reports their status.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from supabase_client import SupabaseClient

def check_legacy_tables():
    """Check for legacy tables in the database."""
    print("🔍 Checking for legacy tables...")
    print("=" * 50)
    
    try:
        # Create Supabase client
        client = SupabaseClient()
        
        # List of legacy tables to check
        legacy_tables = [
        ]
        
        found_tables = []
        
        for table_name in legacy_tables:
            try:
                # Try to query the table
                result = client.client.table(table_name).select('count').limit(1).execute()
                record_count = len(result.data) if result.data else 0
                print(f"❌ Found legacy table: {table_name} ({record_count} records)")
                found_tables.append((table_name, record_count))
            except Exception as e:
                # Table doesn't exist or other error
                print(f"✅ Legacy table not found: {table_name}")
        
        if found_tables:
            print(f"\n⚠️  Found {len(found_tables)} legacy tables:")
            for table_name, count in found_tables:
                print(f"   - {table_name}: {count} records")
            
            print(f"\n💡 Recommendation: Consider removing these legacy tables if they're no longer needed.")
            print(f"   Use the remove_legacy_tables.py script to clean them up.")
        else:
            print(f"\n✅ No legacy tables found! Database is clean.")
        
        # Also check current active tables
        print(f"\n📊 Current active tables:")
        active_tables = [
            'dropbox_accounts',
            'dropbox_account_application_info', 
            'dropbox_account_application_files'
        ]
        
        for table_name in active_tables:
            try:
                result = client.client.table(table_name).select('*').execute()
                record_count = len(result.data) if result.data else 0
                print(f"   ✅ {table_name}: {record_count} records")
            except Exception as e:
                print(f"   ❌ {table_name}: Error accessing table - {e}")
        
    except Exception as e:
        print(f"❌ Error checking legacy tables: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_legacy_tables() 