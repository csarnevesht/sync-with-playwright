#!/usr/bin/env python3
"""
Script to create tables directly via Docker exec to avoid pooler authentication issues
"""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

def load_environment():
    """Load environment variables"""
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    print(f"Loading environment variables from {env_path}")
    load_dotenv(env_path)
    
    # Get database connection details for Docker exec
    db_user = os.getenv('POSTGRES_USER', 'postgres')
    db_password = os.getenv('POSTGRES_PASSWORD', 'postgres')
    
    return db_user, db_password

def create_tables_direct():
    """Create tables directly via Docker exec"""
    print("🏗️ Creating tables directly via Docker exec...")
    
    try:
        # Load environment
        db_user, db_password = load_environment()
        
        # Read the complete schema SQL file
        schema_file = Path(__file__).parent.parent / 'schema' / 'create_complete_account_schema.sql'
        
        if not schema_file.exists():
            print(f"❌ Schema file not found: {schema_file}")
            return False
        
        print(f"📄 Executing schema from: {schema_file}")
        
        # Execute the SQL file directly using Docker exec
        cmd = [
            'docker', 'exec', '-i', 'supabase-db',
            'psql', '-U', db_user, '-d', 'postgres', '-f', '-'
        ]
        
        print(f"🔌 Executing: {' '.join(cmd)}")
        
        # Read the schema file and pipe it to the Docker command
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        # Execute the command
        result = subprocess.run(
            cmd,
            input=schema_sql,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Schema executed successfully!")
            print("Output:", result.stdout)
            
            # Verify the tables were created
            print("\n🔍 Verifying tables...")
            verify_tables_direct()
            
            return True
        else:
            print(f"❌ Error executing schema: {result.stderr}")
            return False
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

def verify_tables_direct():
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
            cmd = [
                'docker', 'exec', 'supabase-db',
                'psql', '-U', 'postgres', '-d', 'postgres',
                '-c', f"SELECT 1 FROM {table} LIMIT 1;"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"  ✅ Table {table} exists")
            else:
                if 'does not exist' in result.stderr.lower() or 'relation' in result.stderr.lower():
                    print(f"  ❌ Table {table} does not exist")
                else:
                    print(f"  ⚠️  Table {table} check failed: {result.stderr}")
                    
        except Exception as e:
            print(f"  ⚠️  Table {table} check failed: {e}")

if __name__ == "__main__":
    try:
        success = create_tables_direct()
        if success:
            print("\n🎉 Direct table creation completed successfully!")
        else:
            print("\n❌ Table creation failed!")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Script failed: {e}")
        sys.exit(1) 