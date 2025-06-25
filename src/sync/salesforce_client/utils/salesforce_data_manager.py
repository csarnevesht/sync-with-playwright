"""
Salesforce Data Manager - Handles Salesforce data retrieval and decision logic
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import asdict

from supabase_client import SupabaseClient
from supabase_client.schema import SalesforceAccount

logger = logging.getLogger(__name__)


class SalesforceDataManager:
    """Manages Salesforce data retrieval and decision logic"""
    
    def __init__(self, supabase_client: SupabaseClient):
        self.supabase_client = supabase_client
    
    def check_database_for_salesforce_data(self, folder_name: str) -> Dict[str, Any]:
        """
        Check database for existing Salesforce data and determine next steps.
        
        Args:
            folder_name: The folder name to search for
            
        Returns:
            Dict containing:
                - should_use_database: bool
                - should_do_live_search: bool
                - salesforce_account_information: Optional[Dict]
                - salesforce_count: Optional[int]
                - independent_accounts: List[SalesforceAccount]
        """
        # Get all possible data sources
        salesforce_count = self.supabase_client.get_salesforce_accounts_found_count(folder_name)
        salesforce_account_information = self.supabase_client.search_salesforce_account_information(folder_name)
        independent_salesforce_accounts = self.supabase_client.get_salesforce_accounts_by_name(folder_name)
        
        # Log what we found
        self._log_database_check_results(folder_name, salesforce_count, salesforce_account_information, independent_salesforce_accounts)
        
        # Determine the best course of action
        decision = self._determine_data_source_strategy(
            salesforce_count, 
            salesforce_account_information, 
            independent_salesforce_accounts
        )
        
        # If we found independent accounts but no existing data, convert them
        if decision['should_use_database'] and independent_salesforce_accounts and not salesforce_account_information:
            salesforce_account_information = self._convert_independent_accounts_to_structure(independent_salesforce_accounts)
        
        return {
            'should_use_database': decision['should_use_database'],
            'should_do_live_search': decision['should_do_live_search'],
            'salesforce_account_information': salesforce_account_information,
            'salesforce_count': salesforce_count,
            'independent_accounts': independent_salesforce_accounts
        }
    
    def _log_database_check_results(self, folder_name: str, salesforce_count: Optional[int], 
                                   salesforce_account_information: Optional[Dict], 
                                   independent_accounts: List[SalesforceAccount]) -> None:
        """Log the results of database checks"""
        logger.info(f"Database check for {folder_name}:")
        logger.info(f"  salesforce_accounts_found_count: {salesforce_count}")
        logger.info(f"  existing_salesforce_data: {'Found' if salesforce_account_information else 'Not found'}")
        logger.info(f"  independent_salesforce_accounts: {len(independent_accounts)} found")
    
    def _determine_data_source_strategy(self, salesforce_count: Optional[int], 
                                       salesforce_account_information: Optional[Dict], 
                                       independent_accounts: List[SalesforceAccount]) -> Dict[str, bool]:
        """
        Determine whether to use database data or do live search.
        
        Returns:
            Dict with 'should_use_database' and 'should_do_live_search' flags
        """
        should_use_database = False
        should_do_live_search = False
        
        # Priority 1: Check for independent Salesforce accounts
        if independent_accounts and not salesforce_account_information:
            logger.info(f"✅ Found {len(independent_accounts)} independent Salesforce accounts, using database data")
            should_use_database = True
        
        # Priority 2: Check existing search count logic
        elif salesforce_count is not None:
            if salesforce_count >= 0:
                if salesforce_account_information:
                    should_use_database = True
                    logger.info(f"✅ Using database data - search previously performed, found {salesforce_count} accounts")
                else:
                    should_do_live_search = True
                    logger.warning(f"⚠️ Database inconsistency - count shows {salesforce_count} accounts but no data found, doing live search")
            else:
                should_do_live_search = True
                logger.info(f"🔄 Previous search failed (count = {salesforce_count}), doing live search")
        
        # Priority 3: Check for existing data without count
        else:
            if salesforce_account_information:
                should_use_database = True
                logger.info(f"✅ Using database data - found existing data but no count recorded")
            else:
                should_do_live_search = True
                logger.info(f"🔄 No previous search performed, doing live search")
        
        return {
            'should_use_database': should_use_database,
            'should_do_live_search': should_do_live_search
        }
    
    def _convert_independent_accounts_to_structure(self, accounts: List[SalesforceAccount]) -> Dict[str, Any]:
        """
        Convert independent Salesforce accounts to the expected structure.
        
        Args:
            accounts: List of SalesforceAccount objects
            
        Returns:
            Dict in the expected salesforce_account_information format
        """
        names_found = [acc.account_name for acc in accounts]
        account_dicts = [self._convert_account_to_dict(acc) for acc in accounts]
        
        # Create the base structure
        salesforce_account_information = {
            'names_found': names_found,
            'household': None,
            'head': None,
            'members': [],
            'accounts': account_dicts,
            'not_found_accounts': []
        }
        
        # Categorize accounts
        self._categorize_accounts(accounts, salesforce_account_information)
        
        return salesforce_account_information
    
    def _convert_account_to_dict(self, account: SalesforceAccount) -> Dict[str, Any]:
        """Convert a SalesforceAccount object to a dictionary"""
        return {
            'account_name': account.account_name,
            'type': account.account_type,
            'role': account.role,
            'stage': account.stage,
            'email': account.email,
            'phone': account.phone,
            'mailing_address': account.address,
            'ssn/tax_id': account.ssn_tax_id,
            'relationships': []
        }
    
    def _categorize_accounts(self, accounts: List[SalesforceAccount], 
                           salesforce_account_information: Dict[str, Any]) -> None:
        """Categorize accounts into household, head, and members"""
        for acc in accounts:
            account_dict = self._convert_account_to_dict(acc)
            
            if acc.account_type == 'Household':
                salesforce_account_information['household'] = account_dict
            elif acc.role == 'Household Head':
                salesforce_account_information['head'] = account_dict
            elif acc.role == 'Member':
                salesforce_account_information['members'].append(account_dict)
    
    def create_salesforce_search_result(self, salesforce_account_information: Dict[str, Any], 
                                       view: str = 'database') -> Dict[str, Any]:
        """
        Create a complete salesforce_account_search_result structure.
        
        Args:
            salesforce_account_information: The account information structure
            view: The view type ('database' or 'live')
            
        Returns:
            Complete salesforce_account_search_result structure
        """
        names_found = salesforce_account_information.get('names_found', [])
        accounts = salesforce_account_information.get('accounts', [])
        
        # Create match_info structure
        match_status = "Match found" if names_found else "No match found"
        match_info = {
            'match_status': match_status,
            'total_matches': len(names_found),
            'total_partial_matches': 0,
            'total_no_matches': 0 if names_found else 1
        }
        
        return {
            'names_found': names_found,
            'household': salesforce_account_information.get('household'),
            'head': salesforce_account_information.get('head'),
            'members': salesforce_account_information.get('members', []),
            'accounts': accounts,
            'not_found_accounts': salesforce_account_information.get('not_found_accounts', []),
            'match_info': match_info,
            'matches': names_found,
            'view': view,
            'salesforce_account_information': salesforce_account_information
        } 