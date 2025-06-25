"""
Backfill salesforce_accounts_found_count for existing data
==========================================================

This script analyzes existing Salesforce data and backfills the 
salesforce_accounts_found_count field for Dropbox accounts that have 
Salesforce data but no count recorded.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from supabase_client import SupabaseClient
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def backfill_salesforce_count():
    """Backfill the salesforce_accounts_found_count field for existing data."""
    logger.info("Starting salesforce_accounts_found_count backfill...")
    
    try:
        # Initialize Supabase client
        supabase_client = SupabaseClient()
        
        # Get all dropbox accounts
        logger.info("Fetching all Dropbox accounts...")
        dropbox_accounts_result = supabase_client.client.table('dropbox_accounts').select('*').execute()
        
        if not dropbox_accounts_result.data:
            logger.info("No Dropbox accounts found")
            return
        
        logger.info(f"Found {len(dropbox_accounts_result.data)} Dropbox accounts")
        
        # Statistics
        total_accounts = len(dropbox_accounts_result.data)
        accounts_with_count = 0
        accounts_without_count = 0
        accounts_updated = 0
        accounts_with_salesforce_data = 0
        
        for account in dropbox_accounts_result.data:
            folder_name = account['folder']
            current_count = account.get('salesforce_accounts_found_count')
            
            logger.info(f"\nProcessing: {folder_name}")
            logger.info(f"  Current count: {current_count}")
            
            if current_count is not None:
                accounts_with_count += 1
                logger.info(f"  ✅ Already has count: {current_count}")
                continue
            
            accounts_without_count += 1
            
            # Check if this account has Salesforce data
            salesforce_data = supabase_client.search_salesforce_account_information(folder_name)
            
            if salesforce_data:
                accounts_with_salesforce_data += 1
                accounts_found = len(salesforce_data.get('accounts', []))
                
                logger.info(f"  📊 Found Salesforce data: {accounts_found} accounts")
                
                # Update the count using direct SQL
                success = update_count_direct_sql(supabase_client, folder_name, accounts_found)
                
                if success:
                    accounts_updated += 1
                    logger.info(f"  ✅ Updated count to: {accounts_found}")
                else:
                    logger.error(f"  ❌ Failed to update count")
            else:
                logger.info(f"  📭 No Salesforce data found")
        
        # Print summary
        logger.info(f"\n{'='*60}")
        logger.info(f"BACKFILL SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total Dropbox accounts: {total_accounts}")
        logger.info(f"Accounts with existing count: {accounts_with_count}")
        logger.info(f"Accounts without count: {accounts_without_count}")
        logger.info(f"Accounts with Salesforce data: {accounts_with_salesforce_data}")
        logger.info(f"Accounts updated: {accounts_updated}")
        logger.info(f"Accounts still missing count: {accounts_without_count - accounts_updated}")
        
        if accounts_updated > 0:
            logger.info(f"\n✅ Successfully backfilled {accounts_updated} accounts!")
        else:
            logger.info(f"\nℹ️ No accounts needed backfilling")
            
    except Exception as e:
        logger.error(f"Error during backfill: {e}")
        import traceback
        traceback.print_exc()

def update_count_direct_sql(supabase_client, folder_name: str, count: int) -> bool:
    """Update the count using direct SQL command."""
    try:
        # Use RPC to execute SQL directly
        sql = f"""
        UPDATE dropbox_accounts 
        SET salesforce_accounts_found_count = {count}, 
            updated_at = CURRENT_TIMESTAMP 
        WHERE folder = '{folder_name}'
        """
        
        result = supabase_client.client.rpc('exec_sql', {'sql': sql}).execute()
        logger.debug(f"SQL update result: {result}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating count with SQL: {e}")
        return False

def verify_backfill():
    """Verify the backfill results."""
    logger.info("\nVerifying backfill results...")
    
    try:
        supabase_client = SupabaseClient()
        
        # Get accounts with null count using direct SQL
        sql_null = """
        SELECT folder FROM dropbox_accounts 
        WHERE salesforce_accounts_found_count IS NULL
        """
        
        null_result = supabase_client.client.rpc('exec_sql', {'sql': sql_null}).execute()
        
        if null_result.data:
            logger.warning(f"⚠️ Found {len(null_result.data)} accounts still with null count:")
            for account in null_result.data[:10]:  # Show first 10
                logger.warning(f"  - {account['folder']}")
            if len(null_result.data) > 10:
                logger.warning(f"  ... and {len(null_result.data) - 10} more")
        else:
            logger.info("✅ All accounts now have salesforce_accounts_found_count populated!")
        
        # Get accounts with count
        sql_with_count = """
        SELECT folder, salesforce_accounts_found_count 
        FROM dropbox_accounts 
        WHERE salesforce_accounts_found_count IS NOT NULL
        """
        
        with_count_result = supabase_client.client.rpc('exec_sql', {'sql': sql_with_count}).execute()
        
        if with_count_result.data:
            logger.info(f"📊 Accounts with count: {len(with_count_result.data)}")
            
            # Show distribution
            count_distribution = {}
            for account in with_count_result.data:
                count = account['salesforce_accounts_found_count']
                count_distribution[count] = count_distribution.get(count, 0) + 1
            
            logger.info("Count distribution:")
            for count in sorted(count_distribution.keys()):
                logger.info(f"  {count}: {count_distribution[count]} accounts")
        
    except Exception as e:
        logger.error(f"Error during verification: {e}")

if __name__ == "__main__":
    print("Salesforce Accounts Found Count Backfill")
    print("=" * 50)
    
    backfill_salesforce_count()
    verify_backfill() 