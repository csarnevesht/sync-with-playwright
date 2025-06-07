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
    try:
        with open('accounts/special_cases.json', 'r') as f:
            data = json.load(f)
            special_cases = data.get('special_cases', [])
            
            # Process each case to ensure expected matches exist
            for case in special_cases:
                if 'expected_salesforce_matches' not in case:
                    case['expected_salesforce_matches'] = []
                if 'expected_dropbox_matches' not in case:
                    case['expected_dropbox_matches'] = []
            
            # Build dictionary with normalized folder names (single space)
            special_cases_dict = {}
            for case in special_cases:
                # Normalize whitespace in folder name (replace multiple spaces with single space)
                normalized_folder_name = ' '.join(case['folder_name'].split())
                special_cases_dict[normalized_folder_name] = case
            
            return special_cases_dict
    except FileNotFoundError:
        logger.warning("Special cases file not found, using hardcoded values")
        return {}
    except json.JSONDecodeError:
        logger.error("Error decoding special cases JSON file")
        return {}
    except Exception as e:
        logger.error(f"Error loading special cases: {str(e)}")
        return {}

def _is_special_case(name: str) -> bool:
    """Check if a name is a special case.
    
    Args:
        name (str): The name to check
        
    Returns:
        bool: True if the name is a special case, False otherwise
    """
    special_cases = _load_special_cases()
    # Normalize whitespace in the name
    normalized_name = ' '.join(name.split())
    cleaned_name = re.sub(r'\([^)]*\)', '', normalized_name).strip()
    
    logger = logging.getLogger('name_utils')
    logger.debug(f"[DEBUG] _is_special_case: normalized_name='{normalized_name}', cleaned_name='{cleaned_name}'")
    # logger.debug(f"[DEBUG] _is_special_case: special_cases keys={list(special_cases.keys())}")
    
    # Check if the name (with or without parentheses) is in special cases
    found = normalized_name in special_cases or cleaned_name in special_cases
    
    # If not found and name has parentheses, try with parentheses content
    if not found and '(' in normalized_name and ')' in normalized_name:
        paren_content = normalized_name[normalized_name.find('(')+1:normalized_name.find(')')].strip()
        name_without_parens = re.sub(r'\([^)]*\)', '', normalized_name).strip()
        name_with_content = f"{name_without_parens} {paren_content}"
        found = name_with_content in special_cases
    
    logger.debug(f"[DEBUG] _is_special_case: found={found}")
    return found

def _get_special_case_rules(name: str) -> Optional[Dict[str, Any]]:
    """Get the rules for a special case name.
    
    Args:
        name (str): The name to get rules for
        
    Returns:
        Optional[Dict[str, Any]]: The rules for the special case, or None if not found
    """
    special_cases = _load_special_cases()
    normalized_name = ' '.join(name.split())
    logger = logging.getLogger('name_utils')
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
            # Don't return early, continue with name normalization
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
    
    # if log:
    #     logger.info(f"Final result: {result}")
    
    return result


