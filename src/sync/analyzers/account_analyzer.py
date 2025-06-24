"""
Account Analyzer Module

This module provides comprehensive analysis of Salesforce and Dropbox account information,
comparing data between sources, identifying gaps, and generating migration plans.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import re

from ..models import (
    AccountAnalysisReport, AccountComparison, HouseholdComparison,
    FieldComparison, DataQualityAnalysis, MigrationPlan,
    FieldStatus, MigrationPriority, DataSource, AccountType, AccountRole
)

logger = logging.getLogger(__name__)


class AccountAnalyzer:
    """Analyzer for comparing Salesforce and Dropbox account information."""
    
    def __init__(self):
        """Initialize the account analyzer."""
        self.logger = logging.getLogger(__name__)
        
        # Define field mappings between Salesforce and Dropbox
        self.field_mappings = {
            'first_name': {
                'salesforce': 'first_name',
                'dropbox_client_list': 'first_name',
                'dropbox_application_files': 'first_name',
                'dropbox_merged': 'first_name'
            },
            'last_name': {
                'salesforce': 'last_name',
                'dropbox_client_list': 'last_name',
                'dropbox_application_files': 'last_name',
                'dropbox_merged': 'last_name'
            },
            'middle_name': {
                'salesforce': 'middle_name',
                'dropbox_client_list': 'middle_name',
                'dropbox_application_files': 'middle_name',
                'dropbox_merged': 'middle_name'
            },
            'email': {
                'salesforce': 'email',
                'dropbox_client_list': 'email',
                'dropbox_application_files': 'email',
                'dropbox_merged': 'email'
            },
            'phone': {
                'salesforce': 'phone',
                'dropbox_client_list': 'phone',
                'dropbox_application_files': 'phone',
                'dropbox_merged': 'phone'
            },
            'address': {
                'salesforce': 'address',
                'dropbox_client_list': 'address',
                'dropbox_application_files': 'address',
                'dropbox_merged': 'address'
            },
            'birthdate': {
                'salesforce': 'birthdate',
                'dropbox_client_list': 'birthdate',
                'dropbox_application_files': 'birthdate',
                'dropbox_merged': 'birthdate'
            },
            'gender': {
                'salesforce': 'gender',
                'dropbox_client_list': 'gender',
                'dropbox_application_files': 'gender',
                'dropbox_merged': 'gender'
            },
            'ssn_tax_id': {
                'salesforce': 'ssn_tax_id',
                'dropbox_client_list': 'ssn_tax_id',
                'dropbox_application_files': 'ssn_tax_id',
                'dropbox_merged': 'ssn_tax_id'
            }
        }
        
        # Define migration priorities for different fields
        self.field_priorities = {
            'first_name': MigrationPriority.HIGH,
            'last_name': MigrationPriority.HIGH,
            'email': MigrationPriority.HIGH,
            'phone': MigrationPriority.MEDIUM,
            'address': MigrationPriority.MEDIUM,
            'birthdate': MigrationPriority.MEDIUM,
            'gender': MigrationPriority.LOW,
            'middle_name': MigrationPriority.LOW,
            'ssn_tax_id': MigrationPriority.HIGH
        }
    
    def analyze_account(self, 
                       dropbox_account_folder: str,
                       salesforce_account_information: Optional[Dict[str, Any]] = None,
                       dropbox_account_information: Optional[Dict[str, Any]] = None) -> AccountAnalysisReport:
        """
        Analyze a single account by comparing Salesforce and Dropbox information.
        
        Args:
            dropbox_account_folder: The Dropbox account folder name
            salesforce_account_information: Salesforce account information structure
            dropbox_account_information: Dropbox account information structure
            
        Returns:
            AccountAnalysisReport with comprehensive analysis
        """
        print(f"[ANALYSIS START] Analyzing account for folder: {dropbox_account_folder}")
        self.logger.info(f"[ANALYSIS START] Analyzing account for folder: {dropbox_account_folder}")
        
        # Initialize the report
        report = AccountAnalysisReport(
            dropbox_account_folder=dropbox_account_folder,
            salesforce_account_information=salesforce_account_information,
            dropbox_account_information=dropbox_account_information
        )
        
        try:
            # Parse Dropbox folder name to understand account structure
            folder_analysis = self._analyze_dropbox_folder_name(dropbox_account_folder)
            report.dropbox_folder_analysis = folder_analysis
            
            # Extract and normalize account data
            salesforce_accounts = self._extract_salesforce_accounts(salesforce_account_information)
            dropbox_accounts = self._merge_dropbox_data_sources(dropbox_account_information)
            
            # Deduplicate Salesforce and Dropbox accounts by (account_name, type)
            def deduplicate_accounts(accounts):
                seen = set()
                deduped = []
                for acc in accounts:
                    name = acc.get('account_name', '')
                    acc_type = acc.get('type', '')
                    key = (name, acc_type)
                    if name and key not in seen:
                        deduped.append(acc)
                        seen.add(key)
                return deduped
            salesforce_accounts = deduplicate_accounts(salesforce_accounts)
            dropbox_accounts = deduplicate_accounts(dropbox_accounts)
            
            # Generate expected Salesforce mapping based on Dropbox folder
            expected_salesforce_mapping = self._generate_expected_salesforce_mapping(folder_analysis, dropbox_account_information)
            report.expected_salesforce_mapping = expected_salesforce_mapping
            
            # Update report statistics
            report.total_accounts_found = len(salesforce_accounts) + len(dropbox_accounts)
            
            # Compare accounts with enhanced mapping
            account_comparisons = self._compare_accounts_with_mapping(
                salesforce_accounts, dropbox_accounts, expected_salesforce_mapping
            )
            report.account_comparisons = account_comparisons
            
            # Analyze household structure with enhanced logic
            household_comparison = self._analyze_household_structure_enhanced(
                salesforce_account_information, dropbox_account_information, folder_analysis
            )
            report.household_comparison = household_comparison
            
            # Calculate data quality metrics
            data_quality = self._calculate_data_quality(account_comparisons)
            report.data_quality = data_quality
            
            # Generate enhanced migration plans
            migration_plans = self._generate_enhanced_migration_plans(
                account_comparisons, household_comparison, expected_salesforce_mapping
            )
            report.migration_plans = migration_plans
            
            # Generate field mapping analysis
            field_mapping_analysis = self._analyze_field_mappings(
                dropbox_account_information, salesforce_account_information
            )
            report.field_mapping_analysis = field_mapping_analysis
            
            # Update final statistics
            report.total_accounts_matched = len([c for c in account_comparisons if c.migration_needed])
            report.total_migrations_needed = len(migration_plans)
            
            # Generate enhanced recommendations
            report.recommendations = self._generate_recommendations(report)
            report.warnings = self._generate_enhanced_warnings(report)
            
            # Ensure data_quality is always set
            if not report.data_quality:
                report.data_quality = DataQualityAnalysis(
                    total_fields_compared=0,
                    fields_present_in_salesforce=0,
                    fields_present_in_dropbox=0,
                    fields_missing_in_salesforce=0,
                    fields_missing_in_dropbox=0,
                    fields_different=0,
                    data_completeness_score=0.0,
                    data_consistency_score=0.0
                )
            
            self.logger.info(f"Analysis completed for {dropbox_account_folder}")
            
        except Exception as e:
            self.logger.error(f"Error analyzing account {dropbox_account_folder}: {str(e)}")
            report.errors.append(f"Analysis failed: {str(e)}")
        
        return report
    
    def _extract_salesforce_accounts(self, salesforce_info: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract and normalize Salesforce account data."""
        accounts = []
        
        if not salesforce_info:
            return accounts
        
        # Extract accounts from the salesforce_account_information structure
        salesforce_accounts = salesforce_info.get('accounts', [])
        
        for account in salesforce_accounts:
            normalized_account = {
                'account_name': account.get('account_name', ''),
                'type': account.get('type', 'Contact'),
                'role': account.get('role'),
                'stage': account.get('stage'),
                'first_name': self._extract_name_part(account.get('account_name', ''), 'first'),
                'last_name': self._extract_name_part(account.get('account_name', ''), 'last'),
                'middle_name': None,  # Not typically available in Salesforce
                'email': account.get('email', ''),
                'phone': account.get('phone', ''),
                'address': account.get('mailing_address', ''),
                'birthdate': None,  # Not typically available in Salesforce
                'gender': None,  # Not typically available in Salesforce
                'ssn_tax_id': account.get('ssn/tax_id', ''),
                'source': DataSource.SALESFORCE
            }
            accounts.append(normalized_account)
        
        return accounts
    
    def _merge_dropbox_data_sources(self, dropbox_info: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge data from both Dropbox sources (client list and application files) 
        to create a comprehensive data source with the best available information.
        """
        merged_accounts = []
        
        if not dropbox_info:
            return merged_accounts
        
        # Get accounts from the correct structure
        accounts = dropbox_info.get('accounts', [])
        
        self.logger.debug(f"Found {len(accounts)} accounts in Dropbox data")
        
        # Group accounts by normalized name to merge them intelligently
        accounts_by_normalized_name = {}
        for account in accounts:
            account_name = account.get('account_name', '')
            if account_name:
                # Generate name variations and use ALL variations as keys to ensure proper grouping
                name_variations = self._generate_name_variations(account_name)
                self.logger.debug(f"Account '{account_name}' has variations: {name_variations}")
                
                # Use all variations as keys to ensure accounts with different formats are grouped together
                for variation in name_variations:
                    normalized_key = variation.lower()
                    if normalized_key not in accounts_by_normalized_name:
                        accounts_by_normalized_name[normalized_key] = []
                    accounts_by_normalized_name[normalized_key].append(account)
        
        self.logger.debug(f"Grouped accounts by normalized name: {list(accounts_by_normalized_name.keys())}")
        
        # Track which accounts have been processed to avoid duplicates
        processed_accounts = set()
        
        # Merge accounts with the same normalized name
        for normalized_name, account_list in accounts_by_normalized_name.items():
            # Filter out already processed accounts
            unprocessed_accounts = [acc for acc in account_list if id(acc) not in processed_accounts]
            
            if not unprocessed_accounts:
                continue
                
            if len(unprocessed_accounts) == 1:
                # Single account, no merging needed
                account = unprocessed_accounts[0]
                merged_account = self._create_merged_account(account)
                merged_accounts.append(merged_account)
                processed_accounts.add(id(account))
            else:
                # Multiple accounts with same normalized name, merge them
                self.logger.debug(f"Merging {len(unprocessed_accounts)} accounts for normalized name: {normalized_name}")
                for acc in unprocessed_accounts:
                    self.logger.debug(f"  - {acc.get('account_name', '')} (source: {acc.get('source', '')})")
                merged_account = self._merge_accounts_with_same_name(unprocessed_accounts)
                merged_accounts.append(merged_account)
                # Mark all accounts as processed
                for acc in unprocessed_accounts:
                    processed_accounts.add(id(acc))
        
        return merged_accounts
    
    def _create_merged_account(self, account: Dict[str, Any]) -> Dict[str, Any]:
        """Create a merged account from a single account."""
        account_name = account.get('account_name', '')
        
        # Always convert type to AccountType if possible
        raw_type = account.get('account_type', 'Primary')
        try:
            acc_type = AccountType(raw_type)
        except Exception:
            self.logger.warning(f"Invalid account_type '{raw_type}' for Dropbox account '{account_name}', defaulting to Contact.")
            acc_type = AccountType.CONTACT
        
        # Determine the correct source - only use DROPBOX_MERGED if it actually came from multiple sources
        original_source = account.get('source', '')
        if original_source == 'dropbox_client_list':
            source = DataSource.DROPBOX_CLIENT_LIST
        elif original_source == 'dropbox_application_files':
            source = DataSource.DROPBOX_APPLICATION_FILES
        else:
            source = DataSource.DROPBOX_MERGED
        
        merged_account = {
            'account_name': account_name,
            'type': acc_type,
            'role': None,
            'stage': None,
            'first_name': account.get('first_name', ''),
            'last_name': account.get('last_name', ''),
            'middle_name': account.get('middle_name', ''),
            'email': account.get('email', ''),
            'phone': account.get('phone', ''),
            'address': account.get('address', ''),
            'birthdate': account.get('birthdate', ''),
            'gender': account.get('gender', ''),
            'ssn_tax_id': account.get('ssn_tax_id', ''),
            'drivers_license': account.get('drivers_license', {}),
            'source': source,
            'data_sources': {
                'client_list': account.get('source') == 'client_list_file',
                'application_files': account.get('source') == 'application_files'
            },
            'merged_from': [{  # Single account, so it's merged from itself
                'account_name': account.get('account_name', ''),
                'source': account.get('source', ''),
                'first_name': account.get('first_name', ''),
                'last_name': account.get('last_name', ''),
                'email': account.get('email', ''),
                'phone': account.get('phone', ''),
                'address': account.get('address', ''),
                'birthdate': account.get('birthdate', ''),
                'gender': account.get('gender', '')
            }]
        }
        
        self.logger.debug(f"Created account: {account_name} with source: {merged_account['source']}")
        self.logger.debug(f"Account data: first_name='{merged_account['first_name']}', last_name='{merged_account['last_name']}', phone='{merged_account['phone']}'")
        
        return merged_account
    
    def _merge_accounts_with_same_name(self, accounts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple accounts with the same name, combining the best available data."""
        if not accounts:
            return {}
        
        # Use the first account as the base
        base_account = accounts[0]
        account_name = base_account.get('account_name', '')
        
        # Always convert type to AccountType if possible
        raw_type = base_account.get('account_type', 'Primary')
        try:
            acc_type = AccountType(raw_type)
        except Exception:
            self.logger.warning(f"Invalid account_type '{raw_type}' for Dropbox account '{account_name}', defaulting to Contact.")
            acc_type = AccountType.CONTACT
        
        # Determine the correct source - only use DROPBOX_MERGED if there are multiple accounts
        if len(accounts) > 1:
            source = DataSource.DROPBOX_MERGED
        else:
            # Single account, use the original source
            original_source = base_account.get('source', '')
            if original_source == 'dropbox_client_list':
                source = DataSource.DROPBOX_CLIENT_LIST
            elif original_source == 'dropbox_application_files':
                source = DataSource.DROPBOX_APPLICATION_FILES
            else:
                source = DataSource.DROPBOX_MERGED
        
        # Initialize merged data
        merged_data = {
            'account_name': account_name,
            'type': acc_type,
            'role': None,
            'stage': None,
            'first_name': '',
            'last_name': '',
            'middle_name': '',
            'email': '',
            'phone': '',
            'address': '',
            'birthdate': '',
            'gender': '',
            'ssn_tax_id': '',
            'drivers_license': {},
            'source': source,
            'data_sources': {
                'client_list': False,
                'application_files': False
            },
            'merged_from': []  # Store the original accounts that were merged
        }
        
        # Store the original accounts that were merged
        for account in accounts:
            merged_data['merged_from'].append({
                'account_name': account.get('account_name', ''),
                'source': account.get('source', ''),
                'first_name': account.get('first_name', ''),
                'last_name': account.get('last_name', ''),
                'email': account.get('email', ''),
                'phone': account.get('phone', ''),
                'address': account.get('address', ''),
                'birthdate': account.get('birthdate', ''),
                'gender': account.get('gender', '')
            })
        
        # Merge data from all accounts, preferring client_list_file for basic info and application_files for detailed personal info
        for field in ['first_name', 'last_name', 'middle_name', 'phone', 'address', 'email', 'birthdate', 'gender', 'ssn_tax_id']:
            # Try to get the best value from all sources, preferring client_list_file if present and non-blank
            best_value = ''
            for account in accounts:
                source = account.get('source', '')
                value = account.get(field, '')
                if source == 'dropbox_client_list' and value and str(value).strip():
                    best_value = value
                    break  # Prefer client list value if present
                elif not best_value and value and str(value).strip():
                    best_value = value  # Use application files value if client list is missing/blank
            merged_data[field] = best_value
        
        # Merge drivers license if available
        for account in accounts:
            if account.get('drivers_license'):
                merged_data['drivers_license'] = account.get('drivers_license', {})
                break
        
        if len(accounts) > 1:
            self.logger.debug(f"Merged {len(accounts)} accounts for {account_name}")
            self.logger.debug(f"Final data: first_name='{merged_data['first_name']}', last_name='{merged_data['last_name']}', gender='{merged_data['gender']}', birthdate='{merged_data['birthdate']}'")
        
        return merged_data
    
    def _get_best_value(self, client_list_value: Any, application_value: Any) -> Any:
        """
        Get the best available value from two sources, preferring client_list_file
        for ALL fields, and only using application_files if client_list_file is missing.
        """
        # Prefer client_list_file for ALL fields
        if client_list_value and str(client_list_value).strip():
            return client_list_value
        elif application_value and str(application_value).strip():
            return application_value
        else:
            return None
    
    def _compare_accounts_with_mapping(self, salesforce_accounts: List[Dict[str, Any]], 
                                     dropbox_accounts: List[Dict[str, Any]],
                                     expected_mapping: Dict[str, Any]) -> List[AccountComparison]:
        """Compare accounts with enhanced mapping logic that matches accounts by name."""
        try:
            self.logger.debug("Starting _compare_accounts_with_mapping")
            comparisons = []
            
            # Deduplicate Salesforce and Dropbox accounts by account_name
            def deduplicate_accounts(accounts):
                try:
                    self.logger.debug(f"Deduplicating {len(accounts)} accounts")
                    seen = set()
                    deduped = []
                    for i, acc in enumerate(accounts):
                        try:
                            name = acc.get('account_name', '')
                            acc_type = acc.get('type', '')
                            self.logger.debug(f"Account {i}: name='{name}', type='{acc_type}' (type={type(acc_type)})")
                            
                            # Ensure acc_type is hashable
                            if isinstance(acc_type, dict):
                                self.logger.error(f"Found dict as account_type: {acc_type}")
                                acc_type = str(acc_type)
                            elif hasattr(acc_type, 'value'):
                                acc_type = str(acc_type.value)
                            else:
                                acc_type = str(acc_type)
                            
                            key = (name, acc_type)
                            self.logger.debug(f"Account {i}: key={key}")
                            
                            if name and key not in seen:
                                deduped.append(acc)
                                seen.add(key)
                            else:
                                self.logger.debug(f"Account {i}: Skipping duplicate or empty name")
                        except Exception as e:
                            self.logger.error(f"Error processing account {i}: {e}")
                            continue
                    self.logger.debug(f"Deduplicated to {len(deduped)} accounts")
                    return deduped
                except Exception as e:
                    self.logger.error(f"Error in deduplicate_accounts: {e}")
                    return accounts
            
            try:
                self.logger.debug("Deduplicating Salesforce accounts")
                salesforce_accounts = deduplicate_accounts(salesforce_accounts)
                self.logger.debug("Deduplicating Dropbox accounts")
                dropbox_accounts = deduplicate_accounts(dropbox_accounts)
            except Exception as e:
                self.logger.error(f"Error during account deduplication: {e}")
                raise
            
            # Prepare sets to track matched accounts
            matched_sf_accounts = set()
            matched_db_accounts = set()
            
            # Build lookup for dropbox accounts by all name variations
            try:
                self.logger.debug("Building Dropbox name lookup")
                db_name_to_accounts = {}
                for db_account in dropbox_accounts:
                    db_name = db_account.get('account_name', '')
                    for variation in self._generate_name_variations(db_name):
                        db_name_to_accounts.setdefault(variation.lower(), []).append(db_account)
                self.logger.debug(f"Built lookup with {len(db_name_to_accounts)} name variations")
            except Exception as e:
                self.logger.error(f"Error building Dropbox name lookup: {e}")
                raise
            
            # For each Salesforce account, match to the first unmatched Dropbox account by any name variation
            try:
                self.logger.debug("Processing Salesforce accounts for matching")
                for sf_account in salesforce_accounts:
                    sf_name = sf_account.get('account_name', '')
                    sf_type = str(sf_account.get('type', ''))
                    sf_key = (sf_name, sf_type)
                    
                    self.logger.debug(f"Processing Salesforce account: name='{sf_name}', type='{sf_type}'")
                    
                    found_match = False
                    for variation in self._generate_name_variations(sf_name):
                        self.logger.debug(f"Checking name variation: '{variation}'")
                        possible_db_accounts = db_name_to_accounts.get(variation.lower(), [])
                        self.logger.debug(f"Found {len(possible_db_accounts)} possible Dropbox accounts for variation '{variation}'")
                        
                        for db_account in possible_db_accounts:
                            db_name = db_account.get('account_name', '')
                            db_type = str(db_account.get('type', ''))
                            db_key = (db_name, db_type)
                            
                            self.logger.debug(f"Checking Dropbox account: name='{db_name}', type='{db_type}', already matched: {db_key in matched_db_accounts}")
                            
                            # Allow multiple Salesforce accounts to match the same Dropbox account
                            # This handles cases like "Maria Montesino Household" and "Maria Montesino" both matching the same person
                            if db_key not in matched_db_accounts or self._should_allow_multiple_matches(sf_account, db_account):
                                self.logger.debug(f"Creating comparison for Salesforce '{sf_name}' ({sf_type}) and Dropbox '{db_name}' ({db_type})")
                                comparison = self._create_account_comparison_with_mapping(
                                    sf_account, db_account, expected_mapping, DataSource.SALESFORCE
                                )
                                comparisons.append(comparison)
                                matched_sf_accounts.add(sf_key)
                                # Only mark Dropbox account as matched if it's a one-to-one relationship
                                if not self._should_allow_multiple_matches(sf_account, db_account):
                                    matched_db_accounts.add(db_key)
                                found_match = True
                                break
                        if found_match:
                            break
                    
                    if not found_match:
                        self.logger.debug(f"No Dropbox match found for Salesforce account '{sf_name}' ({sf_type})")
                        # No Dropbox match found for this Salesforce account
                        comparison = self._create_account_comparison_with_mapping(
                            sf_account, None, expected_mapping, DataSource.SALESFORCE
                        )
                        comparisons.append(comparison)
                        matched_sf_accounts.add(sf_key)
            except Exception as e:
                self.logger.error(f"Error processing Salesforce accounts: {e}")
                raise
            
            # Add unmatched Dropbox accounts
            try:
                self.logger.debug("Adding unmatched Dropbox accounts")
                for db_account in dropbox_accounts:
                    db_name = db_account.get('account_name', '')
                    db_type = str(db_account.get('type', ''))
                    db_key = (db_name, db_type)
                    
                    # Only add Dropbox accounts that weren't matched with any Salesforce accounts
                    # If a Dropbox account was matched, it means there's already a Salesforce account
                    # and the field comparison has already been done through the Salesforce matching
                    if db_key not in matched_db_accounts:
                        # Check if this Dropbox account was matched with any Salesforce account
                        was_matched_with_salesforce = False
                        for sf_key in matched_sf_accounts:
                            # If any Salesforce account was matched to this Dropbox account,
                            # we don't need to create a separate comparison
                            if self._accounts_represent_same_person(db_account, sf_key):
                                was_matched_with_salesforce = True
                                break
                        
                        if not was_matched_with_salesforce:
                            self.logger.debug(f"Adding unmatched Dropbox account: {db_name} ({db_type})")
                            comparison = self._create_account_comparison_with_mapping(
                                None, db_account, expected_mapping, db_account.get('source')
                            )
                            comparisons.append(comparison)
                            matched_db_accounts.add(db_key)
                        else:
                            self.logger.debug(f"Skipping Dropbox account {db_name} ({db_type}) - already matched with Salesforce account")
                    else:
                        self.logger.debug(f"Skipping Dropbox account {db_name} ({db_type}) - already processed")
            except Exception as e:
                self.logger.error(f"Error adding unmatched Dropbox accounts: {e}")
                raise
            
            # Create comparisons for expected accounts that don't exist
            try:
                self.logger.debug("Creating comparisons for expected accounts")
                existing_names = {c.account_name for c in comparisons}
                existing_salesforce_names = {acc.get('account_name', '') for acc in salesforce_accounts}
                
                for expected_account in expected_mapping.get('accounts', []):
                    expected_name = expected_account['name']
                    
                    # Additional validation to prevent creating phantom accounts
                    # Skip expected accounts that:
                    # 1. Are already in the comparisons list
                    # 2. Are already in the actual Salesforce accounts
                    # 3. Contain descriptive text that indicates they're not real accounts
                    # 4. Are just fragments or variations of existing names
                    
                    if (expected_name not in existing_names and 
                        expected_name not in existing_salesforce_names and
                        # Validate that the expected name doesn't contain descriptive text
                        not any(word in expected_name.lower() for word in ['daughter', 'son', 'children', 'family']) and
                        # Validate that it's not just a fragment
                        len(expected_name.split()) >= 2 and
                        # Validate that it doesn't contain special characters that indicate it's not a real name
                        not any(char in expected_name for char in ['(', ')', '&'])):
                        
                        self.logger.debug(f"Creating expected account comparison for: {expected_name}")
                        comparison = self._create_account_comparison_with_mapping(
                            None, None, expected_mapping, DataSource.SALESFORCE,
                            expected_account=expected_account
                        )
                        comparisons.append(comparison)
                    else:
                        self.logger.debug(f"Skipping expected account {expected_name} - validation failed or already exists in actual data")
            except Exception as e:
                self.logger.error(f"Error creating expected account comparisons: {e}")
                raise
            
            # Debug: Log all generated comparisons before returning
            self.logger.debug("Generated account comparisons:")
            for c in comparisons:
                self.logger.debug(f"Comparison: {c.account_name} | Source: {c.source}")
            
            # Deduplicate final comparisons by (account_name, account_type)
            try:
                self.logger.debug("Deduplicating final comparisons")
                seen_comparisons = set()
                deduped_comparisons = []
                for i, comp in enumerate(comparisons):
                    try:
                        # Debug: log the type and value of account_type
                        self.logger.debug(f"Deduplication [{i}]: account_name={comp.account_name}, account_type={comp.account_type} (type={type(comp.account_type)})")
                        
                        # Robustly convert account_type to string for deduplication
                        if hasattr(comp.account_type, 'value'):
                            account_type_str = str(comp.account_type.value)
                        elif isinstance(comp.account_type, dict):
                            self.logger.error(f"Found dict as account_type: {comp.account_type}")
                            account_type_str = str(comp.account_type)
                        else:
                            account_type_str = str(comp.account_type)
                        
                        key = (comp.account_name, account_type_str)
                        self.logger.debug(f"Deduplication [{i}]: key={key}")
                        
                        if key not in seen_comparisons:
                            deduped_comparisons.append(comp)
                            seen_comparisons.add(key)
                        else:
                            self.logger.debug(f"Deduplication [{i}]: Skipping duplicate key={key}")
                            
                    except Exception as e:
                        self.logger.error(f"Error in deduplication for comparison {i}: {e}")
                        self.logger.error(f"Comparison details: account_name={getattr(comp, 'account_name', 'N/A')}, account_type={getattr(comp, 'account_type', 'N/A')}")
                        # Continue with other comparisons instead of failing completely
                        continue
                
                self.logger.debug(f"Deduplicated {len(comparisons)} comparisons to {len(deduped_comparisons)}")
                return deduped_comparisons
            except Exception as e:
                self.logger.error(f"Error in final deduplication: {e}")
                raise
                
        except Exception as e:
            self.logger.error(f"Error in _compare_accounts_with_mapping: {e}")
            raise
    
    def _generate_name_variations(self, name: str) -> List[str]:
        """Generate different name variations for matching."""
        variations = set()  # Use set to avoid duplicates
        variations.add(name)  # Add original name
        
        # Clean the name first - remove parentheses and nicknames for matching
        clean_name = name
        if '(' in name and ')' in name:
            # Remove nickname in parentheses
            start = name.find('(')
            end = name.find(')')
            if start < end:
                clean_name = (name[:start] + name[end+1:]).strip()
                # Remove any extra spaces or commas
                clean_name = re.sub(r'\s+', ' ', clean_name).strip()
                clean_name = clean_name.rstrip(',').strip()
        
        if ', ' in clean_name:
            # Handle "Last, First" format
            parts = clean_name.split(', ')
            if len(parts) >= 2:
                last_name = parts[0].strip()
                first_name = parts[1].strip()
                # Add "First Last" variation
                variations.add(f"{first_name} {last_name}")
                # Add "First Last Household" variation for household matching
                variations.add(f"{first_name} {last_name} Household")
        else:
            # Handle "First Last" format
            parts = clean_name.split()
            if len(parts) >= 2:
                first_name = parts[0].strip()
                last_name = parts[1].strip()
                # Add "Last, First" variation
                variations.add(f"{last_name}, {first_name}")
                # Add "First Last Household" variation for household matching
                variations.add(f"{first_name} {last_name} Household")
        
        return list(variations)  # Convert back to list
    
    def _create_account_comparison_with_mapping(self, sf_account: Optional[Dict[str, Any]],
                                              db_account: Optional[Dict[str, Any]],
                                              expected_mapping: Dict[str, Any],
                                              source: DataSource,
                                              expected_account: Optional[Dict[str, Any]] = None) -> AccountComparison:
        """Create account comparison with enhanced mapping logic."""
        if expected_account:
            account_name = expected_account['name']
            try:
                account_type = AccountType(expected_account['type'])
            except Exception:
                self.logger.warning(f"Invalid account_type '{expected_account['type']}' for expected account '{account_name}', defaulting to Contact.")
                account_type = AccountType.CONTACT
            role = AccountRole(expected_account['role'])
        elif sf_account:
            account_name = sf_account.get('account_name', '')
            try:
                account_type = AccountType(sf_account.get('type', 'Contact'))
            except Exception:
                self.logger.warning(f"Invalid account_type '{sf_account.get('type')}' for Salesforce account '{account_name}', defaulting to Contact.")
                account_type = AccountType.CONTACT
            role = AccountRole(sf_account.get('role')) if sf_account.get('role') else None
        else:
            account_name = db_account.get('account_name', '') if db_account else ''
            raw_type = db_account.get('type', 'Contact') if db_account else 'Contact'
            # Ensure type is never a dict
            if isinstance(raw_type, dict):
                self.logger.error(f"Dropbox account '{account_name}' has dict as type: {raw_type}. Defaulting to Contact.")
                account_type = AccountType.CONTACT
            else:
                try:
                    account_type = AccountType(raw_type)
                except Exception:
                    self.logger.warning(f"Invalid account_type '{raw_type}' for Dropbox account '{account_name}', defaulting to Contact.")
                    account_type = AccountType.CONTACT
            role = None
        
        # Get field values from expected mapping
        expected_fields = expected_mapping.get('field_mappings', {})
        
        # Create field comparisons
        field_comparisons = {}
        for field_name in ['first_name', 'last_name', 'email', 'phone', 'address', 'birthdate', 'gender', 'middle_name', 'ssn_tax_id']:
            sf_value = sf_account.get(field_name) if sf_account else None
            db_value = db_account.get(field_name) if db_account else expected_fields.get(field_name)
            
            field_comparison = self._compare_field(field_name, sf_account, db_account)
            field_comparisons[field_name] = field_comparison
        
        # Determine migration needs
        migration_needed = any(fc.status in [FieldStatus.MISSING, FieldStatus.DIFFERENT] 
                             for fc in field_comparisons.values())
        
        # Create the comparison with the merged account data
        comparison = AccountComparison(
            account_name=account_name,
            account_type=account_type,
            role=role,
            source=source,
            first_name=field_comparisons['first_name'],
            last_name=field_comparisons['last_name'],
            middle_name=field_comparisons['middle_name'],
            email=field_comparisons['email'],
            phone=field_comparisons['phone'],
            address=field_comparisons['address'],
            birthdate=field_comparisons['birthdate'],
            gender=field_comparisons['gender'],
            ssn_tax_id=field_comparisons['ssn_tax_id'],
            migration_needed=migration_needed,
            migration_priority=MigrationPriority.HIGH if migration_needed else MigrationPriority.NOT_NEEDED
        )
        
        # Store the merged account data for summary generation
        if db_account and db_account.get('merged_from'):
            comparison.merged_from = db_account.get('merged_from')
        
        return comparison
    
    def _compare_field(self, field_name: str, salesforce_account: Optional[Dict[str, Any]], 
                      dropbox_account: Optional[Dict[str, Any]]) -> FieldComparison:
        """Compare a single field between Salesforce and Dropbox accounts."""
        
        # Get field values
        salesforce_value = None
        dropbox_value = None
        
        if salesforce_account:
            salesforce_field = self.field_mappings[field_name]['salesforce']
            salesforce_value = salesforce_account.get(salesforce_field, '')
        
        if dropbox_account:
            # Get the source type from the dropbox account
            source_type = dropbox_account.get('source')
            if source_type:
                # Convert enum to string for field mapping lookup
                if hasattr(source_type, 'value'):
                    source_key = source_type.value
                else:
                    source_key = str(source_type)
                
                # Debug logging for source type
                self.logger.debug(f"Dropbox account source: {source_type} -> {source_key}")
                
                # Get the field mapping for this source
                if source_key in self.field_mappings[field_name]:
                    dropbox_field = self.field_mappings[field_name][source_key]
                    dropbox_value = dropbox_account.get(dropbox_field, '')
                    self.logger.debug(f"Field mapping for {field_name}: {source_key} -> {dropbox_field}, value: {dropbox_value}")
                else:
                    # Fallback to direct field access
                    dropbox_value = dropbox_account.get(field_name, '')
                    self.logger.debug(f"No field mapping found for {field_name} with source {source_key}, using direct access: {dropbox_value}")
            else:
                # Fallback to direct field access
                dropbox_value = dropbox_account.get(field_name, '')
                self.logger.debug(f"No source type found, using direct field access for {field_name}: {dropbox_value}")
        
        # Normalize values for comparison
        salesforce_value = self._normalize_value(salesforce_value)
        dropbox_value = self._normalize_value(dropbox_value)
        
        # Debug logging for field comparison
        self.logger.debug(f"Comparing field '{field_name}': Salesforce='{salesforce_value}', Dropbox='{dropbox_value}'")
        
        # Determine status
        if not salesforce_value and not dropbox_value:
            status = FieldStatus.MISSING
        elif not salesforce_value and dropbox_value:
            status = FieldStatus.MISSING
        elif salesforce_value and not dropbox_value:
            status = FieldStatus.MISSING
        elif salesforce_value == dropbox_value:
            status = FieldStatus.PRESENT
        else:
            status = FieldStatus.DIFFERENT
        
        # Get migration priority
        migration_priority = self.field_priorities.get(field_name, MigrationPriority.LOW)
        
        # Generate notes
        notes = self._generate_field_notes(field_name, salesforce_value, dropbox_value, status)
        
        return FieldComparison(
            field_name=field_name,
            salesforce_value=salesforce_value,
            dropbox_value=dropbox_value,
            status=status,
            migration_priority=migration_priority,
            notes=notes
        )
    
    def _normalize_value(self, value: Any) -> Optional[str]:
        """Normalize a value for comparison."""
        if value is None or value == '':
            return None
        
        # Convert to string and clean up
        normalized = str(value).strip()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized if normalized else None
    
    def _generate_field_notes(self, field_name: str, salesforce_value: Optional[str], 
                            dropbox_value: Optional[str], status: FieldStatus) -> Optional[str]:
        """Generate notes for field comparison."""
        if status == FieldStatus.PRESENT:
            return "Values match between systems"
        elif status == FieldStatus.MISSING:
            if not salesforce_value and dropbox_value:
                return f"Field missing in Salesforce, available in Dropbox"
            elif salesforce_value and not dropbox_value:
                return f"Field missing in Dropbox, available in Salesforce"
            else:
                return f"Field missing in both systems"
        elif status == FieldStatus.DIFFERENT:
            return f"Values differ: Salesforce='{salesforce_value}', Dropbox='{dropbox_value}'"
        
        return None
    
    def _analyze_household_structure_enhanced(self, salesforce_info: Optional[Dict[str, Any]],
                                            dropbox_info: Optional[Dict[str, Any]],
                                            folder_analysis: Dict[str, Any]) -> Optional[HouseholdComparison]:
        """Analyze household structure with enhanced logic for joint accounts."""
        if not salesforce_info and not dropbox_info:
            return None
        
        # Get household name - handle both joint and single accounts
        household_name = folder_analysis.get('expected_household_name')
        if not household_name:
            # For single accounts, generate household name from the folder name
            original_name = folder_analysis.get('original_name', '')
            if ', ' in original_name:
                # Handle "Last, First" format - convert to "First Last Household"
                parts = original_name.split(',')
                if len(parts) >= 2:
                    last_name = parts[0].strip()
                    first_name = parts[1].strip()
                    household_name = f"{first_name} {last_name} Household"
                else:
                    household_name = f"{original_name} Household"
            else:
                # Handle "First Last" format
                household_name = f"{original_name} Household"
        
        comparison = HouseholdComparison(
            household_name=household_name,
            salesforce_household=salesforce_info.get('household') if salesforce_info else None,
            dropbox_household=dropbox_info
        )
        
        # Analyze household structure
        if folder_analysis.get('is_joint_account'):
            comparison.structure_match = self._check_joint_account_structure(
                salesforce_info, folder_analysis
            )
        else:
            comparison.structure_match = self._check_single_account_structure(
                salesforce_info, folder_analysis
            )
        
        # Identify missing and extra members
        expected_members = [acc['name'] for acc in folder_analysis.get('expected_accounts', [])]
        actual_members = []
        
        if salesforce_info and salesforce_info.get('accounts'):
            actual_members = [acc.get('account_name', '') for acc in salesforce_info['accounts']]
        
        comparison.missing_members = [m for m in expected_members if m not in actual_members]
        comparison.extra_members = [m for m in actual_members if m not in expected_members]
        
        comparison.migration_needed = len(comparison.missing_members) > 0 or len(comparison.extra_members) > 0
        comparison.migration_priority = MigrationPriority.HIGH if comparison.migration_needed else MigrationPriority.NOT_NEEDED
        
        return comparison
    
    def _check_joint_account_structure(self, salesforce_info: Optional[Dict[str, Any]], 
                                     folder_analysis: Dict[str, Any]) -> bool:
        """Check if Salesforce structure matches expected joint account structure."""
        if not salesforce_info or not salesforce_info.get('accounts'):
            return False
        
        expected_names = [acc['name'] for acc in folder_analysis.get('expected_accounts', [])]
        actual_names = [acc.get('account_name', '') for acc in salesforce_info['accounts']]
        
        # Check if all expected names are present
        return all(name in actual_names for name in expected_names)
    
    def _check_single_account_structure(self, salesforce_info: Optional[Dict[str, Any]], 
                                      folder_analysis: Dict[str, Any]) -> bool:
        """Check if Salesforce structure matches expected single account structure."""
        if not salesforce_info or not salesforce_info.get('accounts'):
            return False
        
        primary_name = folder_analysis.get('primary_account_holder') or folder_analysis['original_name']
        actual_names = [acc.get('account_name', '') for acc in salesforce_info['accounts']]
        
        return primary_name in actual_names
    
    def _generate_enhanced_migration_plans(self, account_comparisons: List[AccountComparison],
                                         household_comparison: Optional[HouseholdComparison],
                                         expected_mapping: Dict[str, Any]) -> List[MigrationPlan]:
        """Generate enhanced migration plans with specific field mappings."""
        plans = []
        
        # Create household migration plan if needed
        if household_comparison and household_comparison.migration_needed:
            household_plan = MigrationPlan(
                account_name=household_comparison.household_name,
                migration_type="create" if not household_comparison.salesforce_household else "update",
                priority=household_comparison.migration_priority,
                estimated_effort="medium",
                fields_to_create=["account_name", "type", "role"],
                notes=f"Household structure needs to be created/updated for {household_comparison.household_name}"
            )
            plans.append(household_plan)
        
        # Create account migration plans
        for comparison in account_comparisons:
            if comparison.migration_needed:
                plan = self._create_migration_plan_for_account(comparison, expected_mapping)
                plans.append(plan)
        
        return plans
    
    def _create_migration_plan_for_account(self, comparison: AccountComparison,
                                         expected_mapping: Dict[str, Any]) -> MigrationPlan:
        """Create a detailed migration plan for a specific account."""
        fields_to_create = []
        fields_to_update = []
        
        # Analyze each field
        for field_name, field_comp in comparison.model_dump().items():
            if isinstance(field_comp, dict) and field_comp.get('status') == FieldStatus.MISSING:
                if field_comp.get('dropbox_value'):
                    fields_to_create.append(field_name)
                elif field_comp.get('salesforce_value'):
                    fields_to_update.append(field_name)
        
        migration_type = "create" if not comparison.source == DataSource.SALESFORCE else "update"
        
        return MigrationPlan(
            account_name=comparison.account_name,
            migration_type=migration_type,
            priority=comparison.migration_priority,
            estimated_effort="medium" if len(fields_to_create) + len(fields_to_update) > 5 else "low",
            fields_to_create=fields_to_create,
            fields_to_update=fields_to_update,
            notes=f"Account {comparison.account_name} needs {migration_type} with {len(fields_to_create)} new fields and {len(fields_to_update)} updated fields"
        )
    
    def _analyze_field_mappings(self, dropbox_info: Optional[Dict[str, Any]],
                              salesforce_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze field mappings between Dropbox and Salesforce."""
        mapping_analysis = {
            'field_mappings': {},
            'missing_fields': [],
            'mapping_notes': []
        }
        
        # Define expected field mappings
        expected_mappings = {
            'first_name': ['first_name', 'firstName'],
            'last_name': ['last_name', 'lastName'],
            'email': ['email', 'emailAddress'],
            'phone': ['phone', 'phoneNumber'],
            'address': ['address', 'mailing_address', 'mailingAddressStreet'],
            'birthdate': ['birthdate', 'dateOfBirth'],
            'gender': ['gender'],
            'ssn_tax_id': ['ssn', 'ssn/tax_id']
        }
        
        # Analyze each field mapping
        for sf_field, db_fields in expected_mappings.items():
            sf_value = None
            db_value = None
            
            # Get Salesforce value
            if salesforce_info and salesforce_info.get('accounts'):
                for account in salesforce_info['accounts']:
                    for db_field in db_fields:
                        if db_field in account:
                            sf_value = account[db_field]
                            break
                    if sf_value:
                        break
            
            # Get Dropbox value
            if dropbox_info and dropbox_info.get('account_data'):
                account_data = dropbox_info['account_data']
                for db_field in db_fields:
                    if db_field in account_data:
                        db_value = account_data[db_field]
                        break
            
            mapping_analysis['field_mappings'][sf_field] = {
                'salesforce_value': sf_value,
                'dropbox_value': db_value,
                'mapped': sf_value is not None or db_value is not None,
                'consistent': sf_value == db_value if sf_value and db_value else True
            }
        
        # Identify missing fields
        for field, mapping in mapping_analysis['field_mappings'].items():
            if not mapping['mapped']:
                mapping_analysis['missing_fields'].append(field)
            elif not mapping['consistent']:
                mapping_analysis['mapping_notes'].append(f"Field {field} has different values: SF='{mapping['salesforce_value']}', DB='{mapping['dropbox_value']}'")
        
        return mapping_analysis
    
    def _generate_recommendations(self, report: 'AccountAnalysisReport') -> List[str]:
        """Generate enhanced recommendations based on analysis."""
        recommendations = []
        
        # Household structure recommendations
        if report.household_comparison and report.household_comparison.migration_needed:
            if report.household_comparison.missing_members:
                recommendations.append(f"Create missing household members: {', '.join(report.household_comparison.missing_members)}")
            if report.household_comparison.extra_members:
                recommendations.append(f"Review extra household members: {', '.join(report.household_comparison.extra_members)}")
        
        # Field mapping recommendations
        if hasattr(report, 'field_mapping_analysis') and report.field_mapping_analysis:
            missing_fields = report.field_mapping_analysis.get('missing_fields', [])
            if missing_fields:
                recommendations.append(f"Populate missing fields: {', '.join(missing_fields)}")
        
        # Account migration recommendations - distinguish between missing and needing updates
        accounts_needing_updates = [c for c in report.account_comparisons if c.migration_needed and c.source == DataSource.SALESFORCE]
        accounts_missing_from_salesforce = [c for c in report.account_comparisons if c.migration_needed and c.source != DataSource.SALESFORCE]
        
        if accounts_needing_updates:
            recommendations.append(f"Update {len(accounts_needing_updates)} existing Salesforce accounts with missing data")
        
        if accounts_missing_from_salesforce:
            recommendations.append(f"Create {len(accounts_missing_from_salesforce)} missing Salesforce accounts")
        
        # Data quality recommendations
        if report.data_quality and report.data_quality.data_completeness_score < 0.8:
            recommendations.append("Improve data completeness by filling missing required fields")
        
        return recommendations
    
    def _generate_enhanced_warnings(self, report: 'AccountAnalysisReport') -> List[str]:
        """Generate enhanced warnings based on analysis."""
        warnings = []
        
        # Data inconsistency warnings
        if hasattr(report, 'field_mapping_analysis') and report.field_mapping_analysis:
            mapping_notes = report.field_mapping_analysis.get('mapping_notes', [])
            warnings.extend(mapping_notes)
        
        # Structure mismatch warnings
        if report.household_comparison and not report.household_comparison.structure_match:
            warnings.append(f"Household structure mismatch for {report.household_comparison.household_name}")
        
        # High priority migration warnings
        high_priority_migrations = [p for p in report.migration_plans if p.priority == MigrationPriority.HIGH]
        if high_priority_migrations:
            warnings.append(f"{len(high_priority_migrations)} high-priority migrations require immediate attention")
        
        return warnings
    
    def _calculate_data_quality(self, account_comparisons: List[AccountComparison]) -> DataQualityAnalysis:
        """Calculate data quality metrics."""
        total_fields = 0
        fields_present_salesforce = 0
        fields_present_dropbox = 0
        fields_missing_salesforce = 0
        fields_missing_dropbox = 0
        fields_different = 0
        
        for comparison in account_comparisons:
            for field_name in self.field_mappings.keys():
                field_comparison = getattr(comparison, field_name)
                total_fields += 1
                
                if field_comparison.salesforce_value:
                    fields_present_salesforce += 1
                else:
                    fields_missing_salesforce += 1
                
                if field_comparison.dropbox_value:
                    fields_present_dropbox += 1
                else:
                    fields_missing_dropbox += 1
                
                if field_comparison.status == FieldStatus.DIFFERENT:
                    fields_different += 1
        
        # Calculate scores
        completeness_score = (fields_present_salesforce + fields_present_dropbox) / (total_fields * 2) if total_fields > 0 else 0.0
        consistency_score = (total_fields - fields_different) / total_fields if total_fields > 0 else 0.0
        
        return DataQualityAnalysis(
            total_fields_compared=total_fields,
            fields_present_in_salesforce=fields_present_salesforce,
            fields_present_in_dropbox=fields_present_dropbox,
            fields_missing_in_salesforce=fields_missing_salesforce,
            fields_missing_in_dropbox=fields_missing_dropbox,
            fields_different=fields_different,
            data_completeness_score=completeness_score,
            data_consistency_score=consistency_score
        )
    
    def _analyze_dropbox_folder_name(self, folder_name: str) -> Dict[str, Any]:
        """Analyze Dropbox folder name to understand account structure."""
        analysis = {
            'original_name': folder_name,
            'is_joint_account': False,
            'primary_account_holder': None,
            'joint_account_holder': None,
            'children_info': [],
            'parsed_names': [],
            'expected_household_name': None,
            'expected_accounts': []
        }
        
        # Check for joint account indicators - but be more careful about parentheses
        # Don't treat names with parentheses as joint accounts unless they clearly contain "&" or "and"
        has_joint_indicator = False
        
        # First, check if there's a clear "&" or "and" separator
        if '&' in folder_name:
            has_joint_indicator = True
        elif ' and ' in folder_name.lower():
            # Only treat as joint if "and" is clearly separating two names
            # Check if "and" is between two name-like parts
            and_parts = folder_name.lower().split(' and ')
            if len(and_parts) >= 2:
                # Check if both parts look like names (not just fragments)
                part1 = and_parts[0].strip()
                part2 = and_parts[1].strip()
                
                # Both parts should have at least one word and not be just fragments
                if (len(part1.split()) >= 1 and len(part2.split()) >= 1 and
                    not part1.startswith('(') and not part2.startswith('(') and
                    not part1.endswith(')') and not part2.endswith(')')):
                    has_joint_indicator = True
        
        if has_joint_indicator:
            analysis['is_joint_account'] = True
            
            # Split by common joint account separators
            if '&' in folder_name:
                parts = folder_name.split('&')
            else:
                parts = folder_name.lower().split('and')
            
            if len(parts) >= 2:
                primary = parts[0].strip().rstrip(',')
                joint = parts[1].strip()
                
                analysis['primary_account_holder'] = primary
                analysis['joint_account_holder'] = joint
                
                # Generate expected household name
                primary_last = self._extract_name_part(primary, 'last')
                if primary_last:
                    analysis['expected_household_name'] = f"{primary_last} Household"
                
                # Generate expected accounts
                analysis['expected_accounts'] = [
                    {'name': primary, 'type': 'Contact', 'role': 'Household Head'},
                    {'name': joint, 'type': 'Contact', 'role': 'Member'}
                ]
        
        # Check for children information (son, daughter, etc.)
        children_patterns = [
            r'son\s+([^,]+)',
            r'daughter\s+([^,]+)',
            r'children\s+([^,]+)'
        ]
        
        for pattern in children_patterns:
            matches = re.findall(pattern, folder_name, re.IGNORECASE)
            analysis['children_info'].extend(matches)
        
        # Parse all names in the folder - improved to handle parentheses and complex names
        # First, handle the case where we have "Last, First (Nickname)" format
        if ', ' in folder_name:
            # Split on comma first to separate last and first names
            parts = folder_name.split(', ', 1)  # Split only on first comma
            if len(parts) == 2:
                last_name = parts[0].strip()
                first_part = parts[1].strip()
                
                # Check if first part contains parentheses (nickname)
                if '(' in first_part and ')' in first_part:
                    # Extract the main name and nickname
                    main_name = first_part.split('(')[0].strip()
                    nickname = first_part[first_part.find('(')+1:first_part.find(')')].strip()
                    
                    # Create the full name without nickname for parsing
                    full_name_without_nickname = f"{main_name} {last_name}"
                    full_name_with_nickname = f"{last_name}, {main_name} ({nickname})"
                    
                    analysis['parsed_names'] = [full_name_without_nickname, full_name_with_nickname]
                else:
                    # Simple "Last, First" format
                    full_name = f"{first_part} {last_name}"
                    analysis['parsed_names'] = [full_name, folder_name]
            else:
                analysis['parsed_names'] = [folder_name]
        else:
            # No comma, treat as single name
            analysis['parsed_names'] = [folder_name]
        
        return analysis
    
    def _generate_expected_salesforce_mapping(self, folder_analysis: Dict[str, Any], 
                                            dropbox_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate expected Salesforce account mapping based on Dropbox folder analysis."""
        mapping = {
            'household': {
                'name': folder_analysis.get('expected_household_name'),
                'type': 'Household',
                'role': 'Household Head'
            },
            'accounts': [],
            'field_mappings': {}
        }
        
        # Add expected accounts from joint account analysis
        for expected_account in folder_analysis.get('expected_accounts', []):
            mapping['accounts'].append(expected_account)
        
        # If no joint account, create single account mapping
        if not folder_analysis.get('is_joint_account'):
            # For single accounts, we should be more conservative about creating expected accounts
            # Only create expected accounts if we have clear evidence they should exist
            
            # Check if we have any parsed names that are different from the original folder name
            parsed_names = folder_analysis.get('parsed_names', [])
            original_name = folder_analysis['original_name']
            
            # Only create expected accounts if we have meaningful parsed names
            # and they're different from the original folder name
            if parsed_names and len(parsed_names) > 0:
                # Use the first parsed name as the primary name (without nickname)
                primary_name = parsed_names[0]
                
                # Only create expected account if it's meaningfully different from the folder name
                # and it looks like a proper name (not just fragments)
                if (primary_name != original_name and 
                    len(primary_name.split()) >= 2 and  # At least first and last name
                    not any(char in primary_name for char in ['(', ')', '&']) and  # No special characters
                    primary_name.strip() and
                    # Additional validation: ensure the parsed name doesn't contain descriptive text
                    not any(word in primary_name.lower() for word in ['daughter', 'son', 'children', 'family', 'household']) and
                    # Ensure it's not just a fragment of the original name
                    not (len(primary_name) < len(original_name) * 0.7)):
                    
                    last_name = self._extract_name_part(primary_name, 'last')
                    if last_name:
                        # For simple cases, show both options: "First Last Household" OR "Last Household"
                        household_name = f"{primary_name} Household or {last_name} Household"
                        mapping['household']['name'] = household_name
                        
                        # Create both household and contact accounts
                        mapping['accounts'] = [
                            {'name': f"{primary_name} Household", 'type': 'Household', 'role': 'Household Head'},
                            {'name': primary_name, 'type': 'Contact', 'role': 'Household Head'}
                        ]
                    else:
                        self.logger.debug(f"Skipping expected account creation - could not extract last name from '{primary_name}'")
                else:
                    self.logger.debug(f"Skipping expected account creation - parsed name '{primary_name}' is not suitable or same as folder name")
            else:
                self.logger.debug(f"No parsed names available for expected account creation")
        
        # Generate field mappings based on Dropbox data
        if dropbox_info and dropbox_info.get('account_data'):
            account_data = dropbox_info['account_data']
            mapping['field_mappings'] = {
                'first_name': account_data.get('first_name'),
                'last_name': account_data.get('last_name'),
                'email': account_data.get('email'),
                'phone': account_data.get('phone'),
                'address': account_data.get('address'),
                'city': account_data.get('city'),
                'state': account_data.get('state'),
                'zip': account_data.get('zip')
            }
        
        return mapping
    
    def _extract_name_part(self, full_name: str, part: str) -> Optional[str]:
        """Extract first or last name from a full name."""
        if not full_name:
            return None
        
        name_parts = full_name.strip().split()
        if part == 'first' and name_parts:
            return name_parts[0]
        elif part == 'last' and len(name_parts) > 1:
            return name_parts[-1]
        return None

    def _format_field_status(self, field_comparison):
        """Return a string indicating which system is missing the field, or if both are present/missing."""
        sf_present = field_comparison.salesforce_value not in [None, '', 'None']
        db_present = field_comparison.dropbox_value not in [None, '', 'None']
        if sf_present and db_present:
            return '✅ Present'
        elif not sf_present and db_present:
            return '❌ Missing in Salesforce'
        elif sf_present and not db_present:
            return '❌ Missing in Dropbox'
        else:
            return '❌ Missing in Both'

    def _should_allow_multiple_matches(self, sf_account: Dict[str, Any], db_account: Dict[str, Any]) -> bool:
        """Determine if multiple Salesforce accounts should match the same Dropbox account."""
        sf_name = sf_account.get('account_name', '').lower()
        sf_type = str(sf_account.get('type', '')).lower()
        db_name = db_account.get('account_name', '').lower()
        
        # Allow multiple matches when:
        # 1. Salesforce account is a Household and Dropbox account is a Primary/Contact
        # 2. Salesforce account is a Contact and Dropbox account is a Primary/Contact
        # 3. Both represent the same person (name similarity check)
        
        # Check if names are similar (same person, different contexts)
        sf_name_clean = sf_name.replace(' household', '').replace(' contact', '').strip()
        db_name_clean = db_name.replace(' household', '').replace(' contact', '').strip()
        
        # If names are essentially the same person, allow multiple matches
        if sf_name_clean == db_name_clean:
            return True
        
        # Allow Household and Contact accounts to match the same Dropbox account
        if 'household' in sf_type and 'primary' in str(db_account.get('type', '')).lower():
            return True
        
        if 'contact' in sf_type and 'primary' in str(db_account.get('type', '')).lower():
            return True
        
        return False

    def _accounts_represent_same_person(self, db_account: Dict[str, Any], sf_key: Tuple[str, str]) -> bool:
        """Determine if a Dropbox account represents the same person as a Salesforce account."""
        db_name = db_account.get('account_name', '')
        sf_name = sf_key[0]
        
        # Generate variations for both names and check for matches
        db_variations = self._generate_name_variations(db_name)
        sf_variations = self._generate_name_variations(sf_name)
        
        # Check if any variations match
        for db_var in db_variations:
            for sf_var in sf_variations:
                if db_var.lower() == sf_var.lower():
                    return True
        
        return False 