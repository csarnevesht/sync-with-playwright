"""
Salesforce Account Relationship Processor

This module handles the processing of Salesforce account relationships,
including navigating to accounts, extracting relationship data, and
organizing the information into structured data.
"""

import logging
from typing import Dict, List, Optional, Tuple, Set

logger = logging.getLogger(__name__)

class SalesforceRelationshipProcessor:
    """
    Handles processing of Salesforce account relationships and account information.
    """
    
    def __init__(self, account_manager, report_logger=None):
        """
        Initialize the relationship processor.
        
        Args:
            account_manager: The Salesforce account manager instance
            report_logger: Optional report logger for detailed logging
        """
        self.account_manager = account_manager
        self.report_logger = report_logger
        self.logger = logging.getLogger(__name__)
    
    def process_account_relationships(self, salesforce_matches: List[str], 
                                   dropbox_account_folder_name: str,
                                   view_name: str = "All Clients") -> Dict:
        """
        Process Salesforce account relationships for given matches.
        
        Args:
            salesforce_matches: List of Salesforce account names to process
            dropbox_account_folder_name: Name of the Dropbox account folder
            view_name: Salesforce view name to use for searches
            
        Returns:
            Dict containing structured account relationship information
        """
        self.logger.info('Processing Salesforce Account Relationships')
        if self.report_logger:
            self.report_logger.info("\n=== SALESFORCE ACCOUNT RELATIONSHIPS ===")
        
        # Initialize salesforce_account_information structure
        salesforce_account_information = {
            'names_found': salesforce_matches if salesforce_matches else [],
            'household': None,
            'head': None,
            'members': [],
            'accounts': [],
            'not_found_accounts': []
        }
        
        # Only process relationships if there are matches
        if not salesforce_matches:
            return salesforce_account_information
        
        # Keep track of processed relationships to avoid duplicates
        processed_relationships = set()
        
        for match in salesforce_matches:
            self._process_single_account_relationship(
                match, view_name, salesforce_account_information, 
                processed_relationships, dropbox_account_folder_name
            )
        
        return salesforce_account_information
    
    def _process_single_account_relationship(self, match: str, view_name: str,
                                           salesforce_account_information: Dict,
                                           processed_relationships: Set,
                                           dropbox_account_folder_name: str) -> None:
        """
        Process relationships for a single Salesforce account.
        
        Args:
            match: Salesforce account name to process
            view_name: Salesforce view name
            salesforce_account_information: Structure to populate with account data
            processed_relationships: Set of already processed relationships
            dropbox_account_folder_name: Name of the Dropbox account folder
        """
        self.logger.info(f"Processing relationships for account: {match}")
        
        # Try to find and access the account
        account_info, account_id, found_account, found_view = self._find_and_access_account(match, view_name)
        
        if not (found_account or found_view):
            self._handle_account_not_found(match, salesforce_account_information)
            return
        
        # Create account structure
        account_data = self._create_account_data_structure(match, account_info)
        
        # Determine account type and role
        if match.endswith('Household'):
            account_data['type'] = 'Household'
            salesforce_account_information['household'] = account_data
        else:
            account_data['type'] = 'Contact'
        
        # Log account information
        self._log_account_information(account_info)
        
        # Process relationships
        self._process_account_relationships_section(
            account_id, account_data, salesforce_account_information,
            processed_relationships, view_name, dropbox_account_folder_name
        )
        
        # Add account to accounts list
        salesforce_account_information['accounts'].append(account_data)
    
    def _find_and_access_account(self, match: str, view_name: str) -> Tuple[Optional[Dict], Optional[str], bool, Optional[str]]:
        """
        Find and access a Salesforce account.
        
        Returns:
            Tuple of (account_info, account_id, found_account, found_view)
        """
        found_account = False
        found_view = None
        account_info = None
        account_id = None
        
        # Try to click on the account from search results
        self.logger.info(f"Clicking account name: {match} in 'Search All'")
        if self.account_manager.click_account_name(match):
            self.logger.info(f"Account found: {match}")
            is_valid, account_id = self.account_manager.verify_account_page_url()
            if is_valid and account_id:
                account_info = self.account_manager.get_account_information(account_id)
                found_account = True
                if self.report_logger:
                    self.report_logger.info(f"Account found: {match}")
                    self.report_logger.info(f"Account ID: {account_id}")
        else:
            self.logger.error(f"Could not navigate to Salesforce account: {match} from 'Search All'")
        
        # If not found in search, try different views
        if not found_account:
            found_view = self._try_find_account_in_views(match)
            if found_view:
                if self.account_manager.click_account_name(match):
                    is_valid, account_id = self.account_manager.verify_account_page_url()
                    if is_valid and account_id:
                        account_info = self.account_manager.get_account_information(account_id)
        
        return account_info, account_id, found_account, found_view
    
    def _try_find_account_in_views(self, match: str) -> Optional[str]:
        """
        Try to find an account in different Salesforce views.
        
        Args:
            match: Account name to search for
            
        Returns:
            View name where account was found, or None
        """
        self.logger.info(f"Account not found: {match}")
        self.logger.info(f"Checking if account exists in appropriate view based on name: {match}")
        
        if match.endswith('Household'):
            if self.account_manager.account_exists(match, view_name="All Accounts"):
                return "All Accounts"
        else:
            if self.account_manager.account_exists(match, view_name="All Clients"):
                return "All Clients"
            elif self.account_manager.account_exists(match, view_name="All Accounts"):
                return "All Accounts"
        
        return None
    
    def _create_account_data_structure(self, match: str, account_info: Dict) -> Dict:
        """
        Create a structured account data dictionary.
        
        Args:
            match: Account name
            account_info: Raw account information from Salesforce
            
        Returns:
            Structured account data dictionary
        """
        return {
            'account_name': match,
            'type': 'Contact',  # Default type
            'role': None,
            'stage': account_info.get('stage', '') if account_info else '',
            'email': account_info.get('email', '') if account_info else '',
            'phone': account_info.get('phone', '') if account_info else '',
            'mailing_address': account_info.get('mailing_address', '') if account_info else '',
            'ssn/tax_id': account_info.get('ssn/tax_id', '') if account_info else '',
            'relationships': []
        }
    
    def _log_account_information(self, account_info: Dict) -> None:
        """
        Log account information to the report logger.
        
        Args:
            account_info: Account information to log
        """
        if self.report_logger and account_info:
            self.report_logger.info(f"\nAccount Information:")
            for key, value in account_info.items():
                self.report_logger.info(f"  {key}: {value}")
    
    def _process_account_relationships_section(self, account_id: str, account_data: Dict,
                                             salesforce_account_information: Dict,
                                             processed_relationships: Set, view_name: str,
                                             dropbox_account_folder_name: str) -> None:
        """
        Process the relationships section for an account.
        
        Args:
            account_id: Salesforce account ID
            account_data: Account data structure to populate
            salesforce_account_information: Main account information structure
            processed_relationships: Set of processed relationships
            view_name: Salesforce view name
            dropbox_account_folder_name: Dropbox account folder name
        """
        relationships = self.account_manager.get_account_relationships(account_id)
        if not relationships:
            self.logger.info(f"No relationships found for account: {account_data['account_name']}")
            return
        
        if self.report_logger:
            self.report_logger.info(f"\nFound {len(relationships)} relationship accounts:")
        
        for rel in relationships:
            self._process_single_relationship(
                rel, account_data, salesforce_account_information,
                processed_relationships, view_name
            )
    
    def _process_single_relationship(self, rel: Dict, account_data: Dict,
                                   salesforce_account_information: Dict,
                                   processed_relationships: Set, view_name: str) -> None:
        """
        Process a single relationship.
        
        Args:
            rel: Relationship data
            account_data: Account data structure
            salesforce_account_information: Main account information structure
            processed_relationships: Set of processed relationships
            view_name: Salesforce view name
        """
        # Create a unique key for this relationship
        rel_key = (rel['name'], rel['role'], rel['type'])
        
        # Skip if we've already processed this relationship
        if rel_key in processed_relationships:
            self.logger.info(f"Skipping already processed relationship: {rel['name']}")
            return
        
        self._log_relationship_info(rel)
        
        # Check if account exists and process it
        self.logger.info(f"Checking if account exists: {rel['name']} in view: {view_name}")
        account_exists = self.account_manager.account_exists(rel['name'], view_name=view_name)
        
        if account_exists:
            self._process_existing_relationship(
                rel, account_data, salesforce_account_information,
                processed_relationships, rel_key
            )
        else:
            self.logger.error(f"Could not verify account page or get account ID for: {rel['name']}")
    
    def _log_relationship_info(self, rel: Dict) -> None:
        """
        Log relationship information.
        
        Args:
            rel: Relationship data to log
        """
        if self.report_logger:
            self.report_logger.info(f"\nRelationship Account:")
            self.report_logger.info(f"  Name: {rel['name']}")
            self.report_logger.info(f"  Type: {rel['type']}")
            self.report_logger.info(f"  Role: {rel['role']}")
    
    def _process_existing_relationship(self, rel: Dict, account_data: Dict,
                                     salesforce_account_information: Dict,
                                     processed_relationships: Set, rel_key: Tuple) -> None:
        """
        Process an existing relationship.
        
        Args:
            rel: Relationship data
            account_data: Account data structure
            salesforce_account_information: Main account information structure
            processed_relationships: Set of processed relationships
            rel_key: Unique key for this relationship
        """
        self.logger.info(f"Account exists: {rel['name']}")
        
        # Click on the relationship account
        if self.account_manager.click_account_name(rel['name']):
            rel_is_valid, rel_account_id = self.account_manager.verify_account_page_url()
            if rel_is_valid and rel_account_id:
                rel_info = self.account_manager.get_account_information(rel_account_id)
                rel['account_info'] = rel_info
                
                # Create relationship account structure
                rel_account_data = self._create_relationship_account_data(rel, rel_info)
                
                # Add to appropriate category
                self._categorize_relationship_account(rel, rel_account_data, account_data, salesforce_account_information)
                
                # Add to relationships list
                account_data['relationships'].append(rel_account_data)
                
                # Mark this relationship as processed
                processed_relationships.add(rel_key)
                
                # Navigate back to original account
                self.account_manager.navigate_back_to_account_page()
    
    def _create_relationship_account_data(self, rel: Dict, rel_info: Dict) -> Dict:
        """
        Create relationship account data structure.
        
        Args:
            rel: Relationship data
            rel_info: Relationship account information
            
        Returns:
            Relationship account data structure
        """
        return {
            'account_name': rel['name'],
            'type': rel['type'],
            'role': rel['role'],
            'stage': rel_info.get('stage', ''),
            'email': rel_info.get('email', ''),
            'phone': rel_info.get('phone', ''),
            'mailing_address': rel_info.get('mailing_address', ''),
            'ssn/tax_id': rel_info.get('ssn/tax_id', ''),
            'relationships': []
        }
    
    def _categorize_relationship_account(self, rel: Dict, rel_account_data: Dict,
                                       account_data: Dict, salesforce_account_information: Dict) -> None:
        """
        Categorize a relationship account into the appropriate section.
        
        Args:
            rel: Relationship data
            rel_account_data: Relationship account data
            account_data: Main account data
            salesforce_account_information: Main account information structure
        """
        if rel['role'] == 'Household Head':
            salesforce_account_information['head'] = rel_account_data
            account_data['role'] = 'Household Head'
        elif rel['role'] == 'Member':
            salesforce_account_information['members'].append(rel_account_data)
            account_data['role'] = 'Member'
    
    def _handle_account_not_found(self, match: str, salesforce_account_information: Dict) -> None:
        """
        Handle case where account is not found.
        
        Args:
            match: Account name that was not found
            salesforce_account_information: Account information structure to update
        """
        self.logger.error(f"Account not found in Search:All or in All Clients or All Accounts view: {match}")
        salesforce_account_information['not_found_accounts'].append({
            'account_name': match,
            'reason': 'Account not found in All Clients or All Accounts view',
            'found_in_search': True,
            'accessible_in_views': False
        }) 