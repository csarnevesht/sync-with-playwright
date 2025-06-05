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
                
            # Convert the list of special cases to a dictionary keyed by folder_name
            special_cases_dict = {}
            for case in special_cases.get('special_cases', []):
                folder_name = case.get('folder_name')
                if folder_name:
                    # Ensure both expected matches lists exist
                    if 'expected_salesforce_matches' not in case:
                        case['expected_salesforce_matches'] = []
                    if 'expected_dropbox_matches' not in case:
                        case['expected_dropbox_matches'] = []
                    # Add both the original folder name and the cleaned version (without parentheses)
                    special_cases_dict[folder_name] = case
                    cleaned_name = re.sub(r'\([^)]*\)', '', folder_name).strip()
                    if cleaned_name != folder_name:
                        special_cases_dict[cleaned_name] = case
                    # Also add the name with parentheses removed but keeping the content
                    if '(' in folder_name and ')' in folder_name:
                        paren_content = folder_name[folder_name.find('(')+1:folder_name.find(')')].strip()
                        name_without_parens = re.sub(r'\([^)]*\)', '', folder_name).strip()
                        name_with_content = f"{name_without_parens} {paren_content}"
                        special_cases_dict[name_with_content] = case
            
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
    # Check both the original name and the cleaned name (without parentheses)
    cleaned_name = re.sub(r'\([^)]*\)', '', name).strip()
    # Also check the name with parentheses removed but keeping the content
    if '(' in name and ')' in name:
        paren_content = name[name.find('(')+1:name.find(')')].strip()
        name_without_parens = re.sub(r'\([^)]*\)', '', name).strip()
        name_with_content = f"{name_without_parens} {paren_content}"
        return name in special_cases or cleaned_name in special_cases or name_with_content in special_cases
    return name in special_cases or cleaned_name in special_cases

def _get_special_case_rules(name: str) -> Optional[Dict[str, Any]]:
    """Get the rules for a special case name.
    
    Args:
        name (str): The name to get rules for
        
    Returns:
        Optional[Dict[str, Any]]: The rules for the special case, or None if not found
    """
    special_cases = _load_special_cases()
    # Try to get rules for both the original name and the cleaned name
    rules = special_cases.get(name)
    if rules is None:
        cleaned_name = re.sub(r'\([^)]*\)', '', name).strip()
        rules = special_cases.get(cleaned_name)
        if rules is None and '(' in name and ')' in name:
            paren_content = name[name.find('(')+1:name.find(')')].strip()
            name_without_parens = re.sub(r'\([^)]*\)', '', name).strip()
            name_with_content = f"{name_without_parens} {paren_content}"
            rules = special_cases.get(name_with_content)
    return rules

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

    # Initialize normalized_names list
    normalized_names = []
    
    if log:
        logger.info(f"Processing name: {name}")

    # Check for parentheses for additional info
    if '(' in name and ')' in name:
        main_name = name[:name.find('(')].strip()
        additional_info = name[name.find('(')+1:name.find(')')].strip()
        logging.info(f"Found additional info in parentheses: {additional_info}")
        result['additional_info'] = additional_info
        name = main_name
    
    # Check for special cases first
    if _is_special_case(name):
        if log:
            logger.info(f"Found special case: {name}")
        rules = _get_special_case_rules(name)
        if rules:
            # Update result with all fields from rules
            for key, value in rules.items():
                if key not in ['normalized_names', 'swapped_names']:  # Don't overwrite these as they'll be generated
                    result[key] = value
            if log:
                logger.info(f"Applied special case rules: {rules}")
            # Don't return early, continue with name normalization
    
    # Remove any text in parentheses and clean up
    name = re.sub(r'\([^)]*\)', '', name).strip()
    
    if log:
        logger.info(f"Cleaned name: {name}")
    
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
                
            # Add normalized names for comma-separated format
            normalized_names.extend([
                f"{result['last_name']}, {result['first_name']}",
                f"{result['last_name']},{result['first_name']}",
                f"{result['first_name']} {result['last_name']}"
            ])
                
            # Handle additional parts
            if len(parts) > 2:
                result['additional_info'] = ', '.join(parts[2:])
    else:
        # Handle names without commas
        parts = name.split()
        
        # Handle names with &/and
        if '&' in name or ' and ' in name:
            if log:
                logger.info(f"Found name with and/&: {name}")
            # Split on & or and
            if '&' in name:
                parts = [p.strip() for p in name.split('&')]
            else:
                # Split on " and " to avoid splitting words containing "and"
                parts = [p.strip() for p in name.split(' and ')]
            
            if log:
                logger.info(f"Split parts: {parts}")
            
            first_part = parts[0].split()
            if len(first_part) == 1:
                result['last_name'] = first_part[0]
                if len(parts) > 1:
                    result['first_name'] = ' '.join(parts[1:])
                else:
                    result['first_name'] = ''
                # Add normalized names for the first part if it has more than just the last name
                if len(parts[0].split()) > 1:
                    first_name_candidate = ' '.join(parts[0].split()[1:])
                    normalized_names.extend([
                        f"{result['last_name']}, {first_name_candidate}",
                        f"{result['last_name']},{first_name_candidate}",
                        f"{first_name_candidate} {result['last_name']}"
                    ])
                # Add normalized names for each part after "and"
                for part in parts[1:]:
                    part_words = part.split()
                    if len(part_words) >= 1:
                        normalized_names.extend([
                            f"{result['last_name']}, {part_words[0]}",
                            f"{result['last_name']},{part_words[0]}",
                            f"{part_words[0]} {result['last_name']}"
                        ])
            else:
                # If first part has multiple words, treat first word as last name
                result['last_name'] = first_part[0]
                result['first_name'] = ' '.join(first_part[1:])
                # Add normalized names for the first part
                normalized_names.extend([
                    f"{result['last_name']}, {result['first_name']}",
                    f"{result['last_name']},{result['first_name']}",
                    f"{result['first_name']} {result['last_name']}"
                ])
                # Additional parts are additional info
                if len(parts) > 1:
                    result['additional_info'] = ' '.join(parts[1:])
                    # Add normalized names for each part after "and"
                    for part in parts[1:]:
                        part_words = part.split()
                        if len(part_words) >= 1:
                            normalized_names.extend([
                                f"{result['last_name']}, {part_words[0]}",
                                f"{result['last_name']},{part_words[0]}",
                                f"{part_words[0]} {result['last_name']}"
                            ])
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
            
            # Add normalized names for regular names
            if result['first_name'] and result['last_name']:
                normalized_names.extend([
                    f"{result['last_name']}, {result['first_name']}",
                    f"{result['last_name']},{result['first_name']}",
                    f"{result['first_name']} {result['last_name']}"
                ])
    
    # Check for son/daughter patterns
    son_or_daughter_pattern = r'\b(son|sons|daughter)\b'
    if re.search(son_or_daughter_pattern, name, re.IGNORECASE):
        # Split the name into parts
        name_parts = name.split()
        for i, word in enumerate(name_parts):
            if word.lower() in ['son', 'sons', 'daughter']:
                # Check if there are two words after son/daughter
                if i + 2 < len(name_parts):
                    # Add the two words as a name
                    two_words = f"{name_parts[i+1]} {name_parts[i+2]}"
                    normalized_names.extend([
                        two_words,
                        f"{name_parts[i+2]}, {name_parts[i+1]}",
                        f"{name_parts[i+2]},{name_parts[i+1]}"
                    ])
                # Check if there is one word after son/daughter
                elif i + 1 < len(name_parts):
                    # Add the last name and the one word
                    if result['last_name']:
                        normalized_names.extend([
                            f"{result['last_name']} {name_parts[i+1]}",
                            f"{name_parts[i+1]}, {result['last_name']}",
                            f"{name_parts[i+1]},{result['last_name']}"
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
    
    # Add normalized names to result
    result['normalized_names'] = normalized_names
    
    # Generate swapped names
    if result['first_name'] and result['last_name']:
        result['swapped_names'] = [
            f"{result['first_name']} {result['last_name']}",
            f"{result['last_name']} {result['first_name']}"
        ]
    
    if log:
        logger.info(f"Final result: {result}")
    
    return result


