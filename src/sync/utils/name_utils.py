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
        logger.debug(f"[DEBUG] _load_special_cases: loading file from {special_cases_file}")
        with open(special_cases_file, 'r') as f:
            data = json.load(f)
        
        # Convert array of special cases to dictionary with folder_name as key
        special_cases_dict = {case['folder_name']: case for case in data.get('special_cases', [])}
        logger.debug(f"[DEBUG] _load_special_cases: loaded data keys={list(special_cases_dict.keys())}")
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

def extract_name_parts(name: str, log: bool = False) -> Tuple[str, Optional[str], str]:
    """
    Extract first, middle, and last name from a full name
    Returns a tuple of (first_name, middle_name, last_name)
    """
    logger.debug(f"[DEBUG] extract_name_parts: starting with name='{name}'")
    
    # Check for special cases first
    if _is_special_case(name):
        logger.debug(f"[DEBUG] extract_name_parts: found special case for '{name}'")
        special_cases = _load_special_cases()
        case = special_cases[name]
        logger.debug(f"[DEBUG] extract_name_parts: using special case data: {case}")
        result = (case['first_name'], None, case['last_name'])
        logger.debug(f"[DEBUG] extract_name_parts: returning special case result: {result}")
        return result

    # Split the name into parts
    parts = name.split(',')
    logger.debug(f"[DEBUG] extract_name_parts: split parts={parts}")
    
    if len(parts) != 2:
        if log:
            logger.warning(f"Invalid name format: {name}")
        logger.debug(f"[DEBUG] extract_name_parts: invalid format, returning ({name}, None, '')")
        return name, None, ""

    last_name = parts[0].strip()
    first_middle = parts[1].strip()
    logger.debug(f"[DEBUG] extract_name_parts: last_name='{last_name}', first_middle='{first_middle}'")

    # Split first and middle names
    first_middle_parts = first_middle.split()
    logger.debug(f"[DEBUG] extract_name_parts: first_middle_parts={first_middle_parts}")
    
    if len(first_middle_parts) == 1:
        result = (first_middle_parts[0], None, last_name)
        logger.debug(f"[DEBUG] extract_name_parts: single first name, returning {result}")
        return result
    elif len(first_middle_parts) == 2:
        result = (first_middle_parts[0], first_middle_parts[1], last_name)
        logger.debug(f"[DEBUG] extract_name_parts: first and middle name, returning {result}")
        return result
    else:
        result = (first_middle_parts[0], " ".join(first_middle_parts[1:]), last_name)
        logger.debug(f"[DEBUG] extract_name_parts: multiple middle names, returning {result}")
        return result


