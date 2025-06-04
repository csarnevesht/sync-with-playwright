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
    
    Returns:
        Dict[str, Dict[str, Any]]: Dictionary of special cases
    """
    special_cases_path = os.path.join('accounts', 'special_cases.json')
    if os.path.exists(special_cases_path):
        try:
            with open(special_cases_path, 'r') as f:
                special_cases = json.load(f)
                
            # Process each special case to ensure it has both expected matches
            for case in special_cases.get('special_cases', []):
                # Get the expected matches
                expected_salesforce_matches = case.get('expected_salesforce_matches', [])
                expected_dropbox_matches = case.get('expected_dropbox_matches', [])
                
                # Update the case with both expected matches
                case['expected_salesforce_matches'] = expected_salesforce_matches
                case['expected_dropbox_matches'] = expected_dropbox_matches
            
            # Convert the list of special cases to a dictionary keyed by folder_name
            special_cases_dict = {case['folder_name']: case for case in special_cases.get('special_cases', [])}
            return special_cases_dict
            
        except Exception as e:
            logging.error(f"Error loading special cases: {str(e)}")
            return {}
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
            - expected_salesforce_matches (List[str]): List of expected matches for Salesforce
            - expected_dropbox_matches (List[str]): List of expected matches for Dropbox
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
        'expected_salesforce_matches': [],
        'expected_dropbox_matches': []
    }
    
    # Check for special cases first
    if _is_special_case(name):
        if log:
            logger.info(f"Found special case: {name}")
        rules = _get_special_case_rules(name)
        if rules:
            result.update(rules)
            # If expected_dropbox_matches is not specified, use expected_salesforce_matches
            if 'expected_salesforce_matches' in rules and 'expected_dropbox_matches' not in rules:
                result['expected_dropbox_matches'] = rules['expected_salesforce_matches']
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

def parse_name(self, name: str) -> Dict[str, Any]:
    """Parse a name into its components.
    
    Args:
        name (str): The name to parse
        
    Returns:
        Dict[str, Any]: Dictionary containing:
            - folder_name (str): Original folder name
            - last_name (str): Last name
            - full_name (str): Full name
            - normalized_names (List[str]): List of normalized name variations
            - swapped_names (List[str]): List of name variations with swapped first/last
            - expected_salesforce_matches (List[str]): List of expected matches for Salesforce
            - expected_dropbox_matches (List[str]): List of expected matches for Dropbox
    """
    logger = logging.getLogger('name_utils')
    logger.info(f"\nParsing name: {name}")
    
    # Initialize result dictionary
    result = {
        'folder_name': name,
        'last_name': '',
        'full_name': '',
        'normalized_names': [],
        'swapped_names': [],
        'expected_salesforce_matches': [],
        'expected_dropbox_matches': []
    }
    
    try:
        # Clean the name
        name = self._clean_name(name)
        
        # Check for special cases
        special_cases = self._load_special_cases()
        for case in special_cases.get('special_cases', []):
            if case.get('folder_name') == name:
                result.update({
                    'last_name': case.get('last_name', ''),
                    'full_name': case.get('full_name', ''),
                    'normalized_names': case.get('normalized_names', []),
                    'swapped_names': case.get('swapped_names', []),
                    'expected_salesforce_matches': case.get('expected_salesforce_matches', []),
                    'expected_dropbox_matches': case.get('expected_dropbox_matches', [])
                })
                logger.info(f"Found special case for: {name}")
                logger.info(f"  First Name: {case.get('first_name', '')}")
                logger.info(f"  Last Name: {case.get('last_name', '')}")
                logger.info(f"  Middle Name: {case.get('middle_name', '')}")
                logger.info(f"  Additional Info: {case.get('additional_info', '')}")
                logger.info(f"  Full Name: {case.get('full_name', '')}")
                logger.info(f"  Normalized Names: {case.get('normalized_names', [])}")
                logger.info(f"  Swapped Names: {case.get('swapped_names', [])}")
                logger.info(f"  Expected Dropbox Matches: {case.get('expected_dropbox_matches', [])}")
                logger.info(f"  Expected Salesforce Matches: {case.get('expected_salesforce_matches', [])}")
                return result
        
        # If no special case found, parse the name
        # Remove any leading numbers and dots
        name = re.sub(r'^\d+\.\s*', '', name)
        
        # Split the name into parts
        parts = name.split(',')
        if len(parts) > 1:
            # Last, First format
            last_name = parts[0].strip()
            first_name = parts[1].strip()
            
            # Extract additional info from parentheses
            additional_info = ''
            if '(' in first_name and ')' in first_name:
                match = re.search(r'\((.*?)\)', first_name)
                if match:
                    additional_info = match.group(1)
                    first_name = first_name.replace(f'({additional_info})', '').strip()
            
            # Create normalized names
            normalized_names = [
                f"{last_name}, {first_name}",
                f"{first_name} {last_name}",
                f"{last_name} {first_name}"
            ]
            
            # Create swapped names
            swapped_names = [
                f"{first_name}, {last_name}",
                f"{last_name}, {first_name}"
            ]
            
            # Create expected matches for both Salesforce and Dropbox
            base_matches = [last_name]
            if additional_info:
                base_matches.append(f"{last_name} ({additional_info})")
            
            # Add household and family variations
            household_variation = f"{last_name} Household"
            family_variation = f"{last_name} Family"
            
            # Set both expected matches lists
            result.update({
                'last_name': last_name,
                'full_name': f"{first_name} {last_name}",
                'normalized_names': normalized_names,
                'swapped_names': swapped_names,
                'expected_salesforce_matches': base_matches + [household_variation, family_variation],
                'expected_dropbox_matches': base_matches + [household_variation, family_variation]
            })
        else:
            # Single name format
            name = name.strip()
            result.update({
                'last_name': name,
                'full_name': name,
                'normalized_names': [name],
                'swapped_names': [name],
                'expected_salesforce_matches': [name],
                'expected_dropbox_matches': [name]
            })
        
        # Log the parsed results
        logger.info(f"Parsed name: {name}")
        logger.info(f"  First Name: {result.get('first_name', '')}")
        logger.info(f"  Last Name: {result.get('last_name', '')}")
        logger.info(f"  Middle Name: {result.get('middle_name', '')}")
        logger.info(f"  Additional Info: {result.get('additional_info', '')}")
        logger.info(f"  Full Name: {result.get('full_name', '')}")
        logger.info(f"  Normalized Names: {result.get('normalized_names', [])}")
        logger.info(f"  Swapped Names: {result.get('swapped_names', [])}")
        logger.info(f"  Expected Dropbox Matches: {result.get('expected_dropbox_matches', [])}")
        logger.info(f"  Expected Salesforce Matches: {result.get('expected_salesforce_matches', [])}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error parsing name '{name}': {str(e)}")
        return result
