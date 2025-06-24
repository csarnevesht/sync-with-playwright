#!/usr/bin/env python3
"""
Script to create the complete account schema with all tables
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from supabase_client import SupabaseClient

def create_complete_schema():
    """Create the complete account schema"""
    print("🏗️ Creating complete account schema...")
    
    try:
        # Create Supabase client
        client = SupabaseClient()
        
        # Read the complete schema SQL file
        schema_file = Path(__file__).parent.parent / 'schema' / 'create_complete_account_schema.sql'
        
        if not schema_file.exists():
            print(f"❌ Schema file not found: {schema_file}")
            return False
        
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        print(f"📄 Executing schema from: {schema_file}")
        
        # Split the SQL into individual statements
        statements = []
        current_statement = ""
        
        for line in schema_sql.split('\n'):
            line = line.strip()
            if line and not line.startswith('--'):
                current_statement += line + " "
                if line.endswith(';'):
                    statements.append(current_statement.strip())
                    current_statement = ""
        
        # Execute each statement
        for i, statement in enumerate(statements, 1):
            if statement.strip():
                try:
                    print(f"  [{i}/{len(statements)}] Executing: {statement[:50]}...")
                    client.client.rpc('exec_sql', {'sql': statement}).execute()
                except Exception as e:
                    # Check if it's a "relation already exists" error (which is fine)
                    if 'already exists' in str(e).lower():
                        print(f"    ⚠️  Table already exists, skipping")
                    else:
                        print(f"    ❌ Error: {e}")
                        return False
        
        print("✅ Complete schema created successfully!")
        
        # Verify the tables were created
        print("\n🔍 Verifying tables...")
        verify_tables(client)
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating complete schema: {e}")
        return False

def verify_tables(client):
    """Verify that the expected tables exist"""
    expected_tables = [
        'dropbox_account_client_list_info',
        'dropbox_account_best_info',
        'salesforce_accounts',
        'salesforce_households',
        'salesforce_household_members',
        'dropbox_salesforce_mapping',
        'sync_status',
        'account_analysis'
    ]
    
    for table in expected_tables:
        try:
            result = client.client.table(table).select('count').limit(1).execute()
            print(f"  ✅ Table {table} exists")
        except Exception as e:
            if 'does not exist' in str(e).lower() or 'relation' in str(e).lower():
                print(f"  ❌ Table {table} does not exist: {e}")
            else:
                print(f"  ⚠️  Table {table} check failed: {e}")

if __name__ == "__main__":
    try:
        success = create_complete_schema()
        if success:
            print("\n🎉 Complete schema creation completed successfully!")
        else:
            print("\n❌ Schema creation failed!")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Script failed: {e}")
        sys.exit(1) 