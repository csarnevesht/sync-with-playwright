#!/usr/bin/env python3
"""
Script to test Supabase connection and verify the setup.
"""

import os
import sys
import logging

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

def test_connection():
    """Test the Supabase connection."""
    try:
        print("Testing Supabase connection...")
        client = SupabaseClient()
        print("✅ Successfully connected to Supabase")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        return False

def test_schema():
    """Test if the required tables exist."""
    try:
        print("\nTesting database schema...")
        client = SupabaseClient()
        
        # Test if tables exist by trying to query them
        tables_to_test = [
            'dropbox_accounts',
            'application_files', 
            'person_info'
        ]
        
        for table in tables_to_test:
            try:
                result = client.client.table(table).select('count').limit(1).execute()
                print(f"✅ Table '{table}' exists and is accessible")
            except Exception as e:
                print(f"❌ Table '{table}' not found or not accessible: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing schema: {e}")
        return False

def test_basic_operations():
    """Test basic database operations."""
    try:
        print("\nTesting basic operations...")
        client = SupabaseClient()
        
        # Test inserting a simple record
        test_data = {
            'folder': 'test_connection_folder',
            'total_files': 0,
            'processed_files': 0,
            'failed_files': 0
        }
        
        result = client.client.table('dropbox_accounts').insert(test_data).execute()
        if result.data:
            print("✅ Successfully inserted test record")
            test_id = result.data[0]['id']
            
            # Test retrieving the record
            retrieve_result = client.client.table('dropbox_accounts').select('*').eq('id', test_id).execute()
            if retrieve_result.data:
                print("✅ Successfully retrieved test record")
                
                # Test deleting the record
                client.client.table('dropbox_accounts').delete().eq('id', test_id).execute()
                print("✅ Successfully deleted test record")
            else:
                print("❌ Failed to retrieve test record")
                return False
        else:
            print("❌ Failed to insert test record")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing basic operations: {e}")
        return False

def check_environment():
    """Check environment variables."""
    print("Checking environment variables...")
    
    required_vars = ['SUPABASE_URL', 'SUPABASE_SERVICE_KEY']
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask the service key for security
            if var == 'SUPABASE_SERVICE_KEY':
                masked_value = value[:10] + '...' + value[-10:] if len(value) > 20 else '***'
                print(f"✅ {var}: {masked_value}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: Not set")
            return False
    
    return True

def main():
    """Run all tests."""
    print("SUPABASE CONNECTION TEST")
    print("=" * 50)
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    all_tests_passed = True
    
    # Test 1: Environment variables
    if not check_environment():
        print("\n❌ Environment check failed. Please check your .env file.")
        all_tests_passed = False
    else:
        print("\n✅ Environment check passed")
    
    # Test 2: Connection
    if not test_connection():
        print("\n❌ Connection test failed.")
        all_tests_passed = False
    else:
        print("\n✅ Connection test passed")
    
    # Test 3: Schema (only if connection passed)
    if all_tests_passed and not test_schema():
        print("\n❌ Schema test failed. You may need to run the schema setup.")
        all_tests_passed = False
    elif all_tests_passed:
        print("\n✅ Schema test passed")
    
    # Test 4: Basic operations (only if previous tests passed)
    if all_tests_passed and not test_basic_operations():
        print("\n❌ Basic operations test failed.")
        all_tests_passed = False
    elif all_tests_passed:
        print("\n✅ Basic operations test passed")
    
    # Summary
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED!")
        print("Your Supabase setup is working correctly.")
        print("\nYou can now use the application files storage functionality.")
    else:
        print("❌ SOME TESTS FAILED!")
        print("\nPlease check:")
        print("1. Your .env file has the correct Supabase credentials")
        print("2. Your Supabase instance is running")
        print("3. The database schema has been set up")
        print("4. Your service key has the necessary permissions")
        
        print("\nTo set up the schema, run:")
        print("python src/sync/commands/setup_supabase_schema.py --print-only")
        print("Then copy the SQL and paste it into your Supabase SQL editor.")
    
    print("=" * 50)

if __name__ == '__main__':
    main() 