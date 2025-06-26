#!/usr/bin/env python3
"""
Unified script to apply any schema type
"""

import os
import sys
import argparse
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from supabase_client import SupabaseClient

def apply_schema(schema_type='simplified'):
    """Apply the specified schema type"""
    print(f"🏗️ Applying {schema_type} schema...")
    
    try:
        # Create Supabase client
        client = SupabaseClient()
        
        # Determine schema file
        if schema_type == 'simplified':
            schema_file = Path(__file__).parent.parent / 'schema' / 'simplified_schema.sql'
        elif schema_type == 'consolidated':
            schema_file = Path(__file__).parent.parent / 'schema' / 'consolidated_schema.sql'
        else:
            raise ValueError(f"Unknown schema type: {schema_type}")
        
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

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Apply database schema')
    parser.add_argument('--schema-type', choices=['simplified', 'consolidated'], 
                       default='simplified', help='Schema type to apply (default: simplified)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("UNIFIED SCHEMA APPLICATION")
    print("=" * 60)
    
    success = apply_schema(args.schema_type)
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 SCHEMA APPLICATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Test basic functionality:")
        print("   python -m sync.cmd_runner --dropbox-accounts")
        print("2. Check database contents:")
        print("   python database/scripts/check_supabase_contents.py")
    else:
        print("\n" + "=" * 60)
        print("❌ SCHEMA APPLICATION FAILED!")
        print("=" * 60)

if __name__ == "__main__":
    main()
