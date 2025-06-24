#!/usr/bin/env python3
"""
Remove Legacy Tables Script

This script removes the legacy applications table and related junction table
that are no longer used in the current database schema.
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def load_environment():
    """Load environment variables."""
    load_dotenv()
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env file")
        sys.exit(1)
    
    return url, key

def remove_legacy_tables():
    """Remove legacy applications table and junction table."""
    url, key = load_environment()
    supabase: Client = create_client(url, key)
    
    print("🗑️  Removing legacy tables...")
    print("=" * 50)
    
    try:
        # First, check if the tables exist and have any data
        print("📊 Checking current table status...")
        
        # Check applications table
        try:
            result = supabase.table("applications").select("*").limit(1).execute()
            app_count = len(result.data) if result.data else 0
            print(f"   - applications table: {app_count} records")
        except Exception as e:
            print(f"   - applications table: does not exist or error: {e}")
            app_count = 0
        
        # Check dropbox_account_applications junction table
        try:
            result = supabase.table("dropbox_account_applications").select("*").limit(1).execute()
            junction_count = len(result.data) if result.data else 0
            print(f"   - dropbox_account_applications table: {junction_count} records")
        except Exception as e:
            print(f"   - dropbox_account_applications table: does not exist or error: {e}")
            junction_count = 0
        
        if app_count > 0 or junction_count > 0:
            print(f"\n⚠️  Warning: Found {app_count} application records and {junction_count} junction records")
            response = input("Do you want to proceed with deletion? (y/N): ")
            if response.lower() != 'y':
                print("❌ Deletion cancelled")
                return
        
        print("\n🗑️  Removing tables...")
        
        # Remove junction table first (due to foreign key constraints)
        try:
            supabase.rpc('exec_sql', {'sql': 'DROP TABLE IF EXISTS dropbox_account_applications CASCADE;'}).execute()
            print("   ✅ Removed dropbox_account_applications table")
        except Exception as e:
            print(f"   ⚠️  Error removing dropbox_account_applications: {e}")
        
        # Remove applications table
        try:
            supabase.rpc('exec_sql', {'sql': 'DROP TABLE IF EXISTS applications CASCADE;'}).execute()
            print("   ✅ Removed applications table")
        except Exception as e:
            print(f"   ⚠️  Error removing applications: {e}")
        
        print("\n✅ Legacy tables removed successfully!")
        
        # Verify removal
        print("\n🔍 Verifying removal...")
        try:
            result = supabase.table("applications").select("*").limit(1).execute()
            print("   ❌ applications table still exists")
        except Exception:
            print("   ✅ applications table successfully removed")
        
        try:
            result = supabase.table("dropbox_account_applications").select("*").limit(1).execute()
            print("   ❌ dropbox_account_applications table still exists")
        except Exception:
            print("   ✅ dropbox_account_applications table successfully removed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    remove_legacy_tables() 