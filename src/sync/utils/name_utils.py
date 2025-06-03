"""
Name parsing and normalization utilities.

This module provides functions for parsing and normalizing names, with support for:
- Complex name formats (with/without commas, ampersands, parentheses)
- Special case handling
- Name variations generation
- Detailed logging of the parsing process
"""

import logging
import re
import os
import json
from typing import Dict, List, Tuple, Optional, Any

# Special cases for name parsing (fallback if JSON file is not available)
SPECIAL_CASES = {}

def _load_special_cases() -> Dict[str, Dict[str, Any]]:
    """Load special cases for name parsing from accounts/special_cases.json.
    Falls back to hardcoded SPECIAL_CASES if the file is not available.
    
    For each special case, automatically adds 'Lastname Household' and 'Lastname Family'
    to expected matches if they're not already present.
    
    Returns:
        Dict[str, Dict[str, Any]]: Dictionary of special cases
    """
    special_cases_path = os.path.join('accounts', 'special_cases.json')
    if os.path.exists(special_cases_path):
        try:
            with open(special_cases_path, 'r') as f:
                special_cases = json.load(f)
                # Convert the list of special cases to a dictionary
                result = {}
                for case in special_cases.get('special_cases', []):
                    folder_name = case['folder_name']
                    # Get the last name from the case
                    last_name = case.get('last_name', '')
                    if last_name:
                        # Add household and family variations if not already present
                        expected_matches = case.get('expected_matches', [])
                        household_match = f"{last_name} Household"
                        family_match = f"{last_name} Family"
                        
                        if household_match not in expected_matches:
                            expected_matches.append(household_match)
                        if family_match not in expected_matches:
                            expected_matches.append(family_match)
                            
                        case['expected_matches'] = expected_matches
                    
                    result[folder_name] = case
                return result
        except Exception as e:
            logging.error(f"Error reading special cases file: {e}")
            return SPECIAL_CASES
    return SPECIAL_CASES

def _is_special_case(name: str) -> bool:
    """Check if a name is a special case.
    
    Args:
        name (str): The name to check
        
    Returns:
        bool: True if the name is a special case, False otherwise
    """
    special_cases = _load_special_cases()
    return name in special_cases

def _get_special_case_rules(name: str) -> Optional[Dict[str, Any]]:
    """Get the rules for a special case name.
    
    Args:
        name (str): The name to get rules for
        
    Returns:
        Optional[Dict[str, Any]]: The rules for the special case, or None if not found
    """
    special_cases = _load_special_cases()
    return special_cases.get(name)

def extract_name_parts(name: str, log: bool = False) -> Dict[str, Any]:
    """Extract and normalize name components from a full name.
    
    This method handles various name formats and special cases:
    - Names with commas (e.g., "Last, First")
    - Names with ampersands (e.g., "First & Last")
    - Names with parentheses
    - Special cases with predefined rules
    
    Args:
        name (str): The full name to parse
        log (bool): Whether to log the parsing process
        
    Returns:
        Dict[str, Any]: Dictionary containing:
            - first_name (str): First name
            - last_name (str): Last name
            - middle_name (str): Middle name or initial
            - additional_info (str): Any additional information
            - full_name (str): Original full name
            - normalized_names (List[str]): List of normalized name variations
            - swapped_names (List[str]): List of name variations with swapped first/last
            - expected_matches (List[str]): List of expected matches for special cases
    """
    logger = logging.getLogger('name_utils')
    
    if log:
        logger.info(f"INFO: extract_name_parts ***name: {name}")
    
    # Initialize result dictionary
    result = {
        'first_name': '',
        'last_name': '',
        'middle_name': '',
        'additional_info': '',
        'full_name': name,
        'normalized_names': [],
        'swapped_names': [],
        'expected_matches': []
    }
    
    # Check for special cases first
    if _is_special_case(name):
        if log:
            logger.info(f"Found special case: {name}")
        rules = _get_special_case_rules(name)
        if rules:
            result.update(rules)
            if log:
                logger.info(f"Applied special case rules: {rules}")
            return result
    
    # Remove any text in parentheses and clean up
    name = re.sub(r'\([^)]*\)', '', name).strip()
    
    # Handle names with commas
    if ',' in name:
        parts = [part.strip() for part in name.split(',')]
        if len(parts) >= 2:
            result['last_name'] = parts[0]
            first_part = parts[1]
            
            # Handle middle name in first part
            first_parts = first_part.split()
            if len(first_parts) > 1:
                result['first_name'] = first_parts[0]
                result['middle_name'] = ' '.join(first_parts[1:])
            else:
                result['first_name'] = first_part
                
            # Handle additional parts
            if len(parts) > 2:
                result['additional_info'] = ', '.join(parts[2:])
    else:
        # Handle names without commas
        parts = name.split()
        
        # Handle names with &/and
        if '&' in name or ' and ' in name:
            # Split on & or and
            if '&' in name:
                parts = [p.strip() for p in name.split('&')]
            else:
                parts = [p.strip() for p in name.split(' and ')]
            
            # First part is first name
            result['first_name'] = parts[0]
            
            # Last part is last name
            if len(parts) > 1:
                result['last_name'] = parts[-1]
                
            # Middle parts are additional info
            if len(parts) > 2:
                result['additional_info'] = ' '.join(parts[1:-1])
        else:
            # Handle regular names
            if len(parts) == 1:
                result['last_name'] = parts[0]
            elif len(parts) == 2:
                result['first_name'] = parts[0]
                result['last_name'] = parts[1]
            elif len(parts) > 2:
                result['first_name'] = parts[0]
                result['last_name'] = parts[-1]
                result['middle_name'] = ' '.join(parts[1:-1])
    
    # Generate normalized names
    normalized_names = []
    
    # Original name variations
    if result['first_name'] and result['last_name']:
        normalized_names.extend([
            f"{result['last_name']}, {result['first_name']}",
            f"{result['last_name']},{result['first_name']}",
            f"{result['first_name']} {result['last_name']}"
        ])
    
    # Middle name variations
    if result['middle_name']:
        if result['first_name'] and result['last_name']:
            normalized_names.extend([
                f"{result['last_name']}, {result['first_name']} {result['middle_name']}",
                f"{result['first_name']} {result['middle_name']} {result['last_name']}"
            ])
    
    # Additional info variations
    if result['additional_info']:
        if result['first_name'] and result['last_name']:
            normalized_names.extend([
                f"{result['last_name']}, {result['first_name']} ({result['additional_info']})",
                f"{result['first_name']} {result['last_name']} ({result['additional_info']})"
            ])
    
    # Generate swapped names
    swapped_names = []
    if result['first_name'] and result['last_name']:
        swapped_names.append(f"{result['last_name']} {result['first_name']}")
    
    # Update result with generated names
    result['normalized_names'] = [name.lower() for name in normalized_names]
    result['swapped_names'] = [name.lower() for name in swapped_names]
    
    if log:
        logger.info(f"Extracted name parts: {result}")
    
    return result

def prepare_account_data_for_search(account_name: str, view_name: str) -> Dict[str, Any]:
    """Prepare account data for search operations.
    
    This function extracts and normalizes name components from an account name,
    creating a standardized data structure for search operations.
    
    Args:
        account_name (str): The account name to process
        
    Returns:
        Dict[str, Any]: Dictionary containing:
            - last_name (str): Last name
            - full_name (str): Original full name
            - normalized_names (List[str]): List of normalized name variations
            - swapped_names (List[str]): List of name variations with swapped first/last
            - expected_matches (List[str]): List of expected matches for special cases
            - status (str): Status of the name processing
            - matches (List[str]): List of matches found
            - match_info (Dict[str, Any]): Information about matches
    """
    # Create standardized data structure
    name_parts = extract_name_parts(account_name, log=True)
    result = {
            'view': view_name,
            'folder_name': account_name,
            'last_name': name_parts['last_name'],
            'full_name': name_parts['full_name'],
            'normalized_names': name_parts['normalized_names'],
            'swapped_names': name_parts['swapped_names'],
            'expected_matches': name_parts['expected_matches'],
            'status': 'not_found',
            'matches': [],
            'search_attempts': [],
            'timing': {},
            'expected_matches': [],
            'match_info': {
                'match_status': "No match found",
                'total_exact_matches': 0,
                'total_partial_matches': 0,
                'total_no_matches': 1
            }
        }
    
    return result 