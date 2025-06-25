#!/usr/bin/env python3
"""
Script to create the client list table in the database.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from supabase_client import SupabaseClient

def create_client_list_table():
    """Create the client list table in the database."""
    print("🏗️ Creating client list table...")
    
    try:
        # Create Supabase client
        client = SupabaseClient()
        
        # Read the SQL file
        sql_file = Path(__file__).parent.parent / "schema" / "create_client_list_table.sql"
        if not sql_file.exists():
            print(f"❌ SQL file not found: {sql_file}")
            return False
        
        with open(sql_file, 'r') as f:
            sql_content = f.read()
        
        # Split into individual statements
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
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
        
        print("\n📋 Verifying table creation...")
        
        # Check if table was created
        try:
            result = client.client.table('dropbox_account_client_list_info').select('id').limit(1).execute()
            print("✅ Client list table created successfully!")
            return True
        except Exception as e:
            print(f"❌ Error verifying table creation: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating client list table: {e}")
        return False

if __name__ == "__main__":
    success = create_client_list_table()
    if success:
        print("\n🎉 Client list table creation completed successfully!")
    else:
        print("\n❌ Client list table creation failed!")
        sys.exit(1) 