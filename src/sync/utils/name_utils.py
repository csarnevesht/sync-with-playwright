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

# Set up logger
logger = logging.getLogger(__name__)

# Special cases for name parsing (fallback if JSON file is not available)
SPECIAL_CASES = {}

def _load_special_cases() -> Dict[str, str]:
    """
    Load special cases from JSON file
    Returns a dictionary of special cases where the key is the folder_name
    """
    try:
        special_cases_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'accounts', 'special_cases.json')
        # logger.debug(f"[DEBUG] _load_special_cases: loading file from {special_cases_file}")
        with open(special_cases_file, 'r') as f:
            data = json.load(f)
        
        # Convert array of special cases to dictionary with folder_name as key
        special_cases_dict = {case['folder_name']: case for case in data.get('special_cases', [])}
        # logger.debug(f"[DEBUG] _load_special_cases: loaded data keys={list(special_cases_dict.keys())}")
        return special_cases_dict
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding special cases JSON file: {str(e)}")
        return {}
    except Exception as e:
        logger.error(f"Error loading special cases file: {str(e)}")
        return {}

def _is_special_case(name: str) -> bool:
    """
    Check if a name is a special case using the more robust _get_special_case_rules function
    """
    logger.debug(f"[DEBUG] _is_special_case: checking name='{name}'")
    rules = _get_special_case_rules(name)
    is_special = rules is not None
    logger.debug(f"[DEBUG] _is_special_case: is_special={is_special}")
    return is_special

def _get_special_case_rules(name: str) -> Optional[Dict[str, Any]]:
    """Get the rules for a special case name.
    
    Args:
        name (str): The name to get rules for
        
    Returns:
        Optional[Dict[str, Any]]: The rules for the special case, or None if not found
    """
    special_cases = _load_special_cases()
    normalized_name = ' '.join(name.split())
    logger.debug(f"[DEBUG] _get_special_case_rules: normalized_name='{normalized_name}'")
    # logger.debug(f"[DEBUG] _get_special_case_rules: special_cases keys={list(special_cases.keys())}")
    
    # First try exact match
    rules = special_cases.get(normalized_name)
    if rules is not None:
        logger.debug(f"[DEBUG] _get_special_case_rules: found exact match")
        return rules
    
    # Try without parentheses
    cleaned_name = re.sub(r'\([^)]*\)', '', normalized_name).strip()
    logger.debug(f"[DEBUG] _get_special_case_rules: cleaned_name='{cleaned_name}'")
    rules = special_cases.get(cleaned_name)
    if rules is not None:
        logger.debug(f"[DEBUG] _get_special_case_rules: found match without parentheses")
        return rules
    
    # Try with parentheses content
    if '(' in normalized_name and ')' in normalized_name:
        paren_content = normalized_name[normalized_name.find('(')+1:normalized_name.find(')')].strip()
        name_without_parens = re.sub(r'\([^)]*\)', '', normalized_name).strip()
        name_with_content = f"{name_without_parens} {paren_content}"
        logger.debug(f"[DEBUG] _get_special_case_rules: name_with_content='{name_with_content}'")
        rules = special_cases.get(name_with_content)
        if rules is not None:
            logger.debug(f"[DEBUG] _get_special_case_rules: found match with parentheses content")
            return rules
    
    logger.debug(f"[DEBUG] _get_special_case_rules: no rules found")
    return None

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

    # --- FIX: Check for special case using original name (with parentheses) first ---
    original_name = name
    if _is_special_case(original_name):
        if log:
            logger.info(f"Found special case: {original_name}")
        rules = _get_special_case_rules(original_name)
        if rules:
            expected_dropbox_matches = rules.get('expected_dropbox_matches', [])
            expected_salesforce_matches = rules.get('expected_salesforce_matches', [])
            if not isinstance(expected_dropbox_matches, list):
                expected_dropbox_matches = [expected_dropbox_matches]
            if not isinstance(expected_salesforce_matches, list):
                expected_salesforce_matches = [expected_salesforce_matches]
            for key, value in rules.items():
                if key not in ['normalized_names', 'swapped_names', 'expected_dropbox_matches', 'expected_salesforce_matches']:
                    result[key] = value
            result['expected_dropbox_matches'] = expected_dropbox_matches
            result['expected_salesforce_matches'] = expected_salesforce_matches
            if log:
                logger.info(f"Applied special case rules: {rules}")
            
            # If we have valid first and last names from special case, skip normal parsing
            if result.get('first_name') and result.get('last_name'):
                if log:
                    logger.info(f"Special case provided valid names, skipping normal parsing")
                # Generate normalized names based on special case names
                normalized_names.extend([
                    f"{result['last_name']}, {result['first_name']}",
                    f"{result['last_name']},{result['first_name']}",
                    f"{result['first_name']} {result['last_name']}"
                ])
                result['normalized_names'] = normalized_names
                result['swapped_names'] = [
                    f"{result['first_name']} {result['last_name']}",
                    f"{result['last_name']} {result['first_name']}"
                ]
                return result
    # --- END FIX ---

    # Check for parentheses for additional info
    if '(' in name and ')' in name:
        main_name = name[:name.find('(')].strip()
        additional_info = name[name.find('(')+1:name.find(')')].strip()
        logging.info(f"Found additional info in parentheses: {additional_info}")
        result['additional_info'] = additional_info
        name = main_name

    # Check for special cases again after stripping parentheses (for legacy cases)
    if not result['expected_dropbox_matches'] and not result['expected_salesforce_matches']:
        if _is_special_case(name):
            if log:
                logger.info(f"Found special case: {name}")
            rules = _get_special_case_rules(name)
            if rules:
                expected_dropbox_matches = rules.get('expected_dropbox_matches', [])
                expected_salesforce_matches = rules.get('expected_salesforce_matches', [])
                if not isinstance(expected_dropbox_matches, list):
                    expected_dropbox_matches = [expected_dropbox_matches]
                if not isinstance(expected_salesforce_matches, list):
                    expected_salesforce_matches = [expected_salesforce_matches]
                for key, value in rules.items():
                    if key not in ['normalized_names', 'swapped_names', 'expected_dropbox_matches', 'expected_salesforce_matches']:
                        result[key] = value
                result['expected_dropbox_matches'] = expected_dropbox_matches
                result['expected_salesforce_matches'] = expected_salesforce_matches
                if log:
                    logger.info(f"Applied special case rules: {rules}")
                
                # If we have valid first and last names from special case, skip normal parsing
                if result.get('first_name') and result.get('last_name'):
                    if log:
                        logger.info(f"Special case provided valid names, skipping normal parsing")
                    # Generate normalized names based on special case names
                    normalized_names.extend([
                        f"{result['last_name']}, {result['first_name']}",
                        f"{result['last_name']},{result['first_name']}",
                        f"{result['first_name']} {result['last_name']}"
                    ])
                    result['normalized_names'] = normalized_names
                    result['swapped_names'] = [
                        f"{result['first_name']} {result['last_name']}",
                        f"{result['last_name']} {result['first_name']}"
                    ]
                    return result

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
    
    # if log:
    #     logger.info(f"Final result: {result}")
    
    return result

def should_skip_command_for_account(account_name: str, command_name: str) -> bool:
    """
    Check if a command should be skipped for a given account based on special case rules.
    
    Args:
        account_name (str): The account name to check
        command_name (str): The command name to check
        
    Returns:
        bool: True if the command should be skipped, False otherwise
    """
    try:
        special_cases = _load_special_cases()
        normalized_name = ' '.join(account_name.split())
        special_case = special_cases.get(normalized_name)
        
        if special_case and special_case.get('skip_commands'):
            skip_commands = special_case['skip_commands']
            if command_name in skip_commands:
                logger.info(f"Command '{command_name}' skipped for account '{account_name}' due to special case rule")
                return True
        
        return False
    except Exception as e:
        logger.error(f"Error checking skip command for {account_name}: {str(e)}")
        return False


