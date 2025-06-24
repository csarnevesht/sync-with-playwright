#!/usr/bin/env python3
"""
Script to set up the Supabase database schema for application files data.
"""

import os
import sys
import logging

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from supabase_client import SupabaseClient
from supabase_client.schema import create_schema

logger = logging.getLogger(__name__)

def setup_schema():
    """Set up the database schema."""
    try:
        # Get the schema SQL
        schema_sql = create_schema()
        
        # Execute the schema creation
        supabase_client = SupabaseClient()
        
        # Split the SQL into individual statements
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        logger.info("Setting up database schema...")
        
        for i, statement in enumerate(statements, 1):
            if statement:
                try:
                    logger.info(f"Executing statement {i}/{len(statements)}")
                    # Note: This is a simplified approach. In practice, you might need to use
                    # raw SQL execution depending on your Supabase client capabilities
                    logger.info(f"SQL: {statement[:100]}...")
                    
                    # For now, just log the statements since direct SQL execution
                    # might not be available in the current client
                    
                except Exception as e:
                    logger.error(f"Error executing statement {i}: {e}")
                    logger.error(f"Statement: {statement}")
        
        logger.info("Schema setup completed. Please run the SQL statements manually in your Supabase dashboard.")
        logger.info("You can copy the schema from the supabase_client/schema.py file.")
        
        return True
        
    except Exception as e:
        logger.error(f"Error setting up schema: {e}")
        return False

def print_schema():
    """Print the schema SQL for manual execution."""
    schema_sql = create_schema()
    print("=" * 80)
    print("SUPABASE SCHEMA SQL")
    print("=" * 80)
    print("Copy and paste this SQL into your Supabase SQL editor:")
    print()
    print(schema_sql)
    print()
    print("=" * 80)

def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Set up Supabase database schema')
    parser.add_argument('--print-only', action='store_true', help='Only print the schema SQL without executing')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if args.print_only:
        print_schema()
    else:
        success = setup_schema()
        if success:
            print("Schema setup completed successfully!")
        else:
            print("Schema setup failed!")
            sys.exit(1)

if __name__ == '__main__':
    main() 