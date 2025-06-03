"""Utility functions for handling account-related operations."""

import os
import logging
from typing import List, Set, Dict, Any
from src.sync.utils.name_utils import prepare_account_data_for_search

logger = logging.getLogger(__name__)

def read_accounts_folders(file_path: str) -> List[str]:
    """
    Read account folder names from a file.
    
    Args:
        file_path: Path to the file containing account folder names
        
    Returns:
        List of account folder names
    """
    try:
        with open(file_path, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logger.error(f"Accounts file not found: {file_path}")
        return []
    except Exception as e:
        logger.error(f"Error reading accounts file: {str(e)}")
        return []

def read_ignored_folders(file_path: str = 'accounts/ignore.txt') -> Set[str]:
    """
    Read list of folders to ignore from a file.
    
    Args:
        file_path: Path to the ignore file (default: accounts/ignore.txt)
        
    Returns:
        Set of folder names to ignore
    """
    ignored_folders = set()
    
    try:
        # If the file path doesn't include 'accounts/', look in the accounts directory
        if not file_path.startswith('accounts/'):
            accounts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'accounts')
            file_path = os.path.join(accounts_dir, file_path)
            
        if not os.path.exists(file_path):
            logger.warning(f"Ignore file not found: {file_path}")
            return ignored_folders
            
        logger.info(f"Reading ignored folders from: {os.path.abspath(file_path)}")
            
        with open(file_path, 'r') as f:
            for line in f:
                folder = line.strip()
                if folder:
                    # Validate folder name
                    if '/' in folder or '\\' in folder:
                        logger.warning(f"Invalid folder name in ignore list (contains path separators): {folder}")
                        continue
                    if not folder.strip():
                        logger.warning("Empty folder name found in ignore list, skipping")
                        continue
                    ignored_folders.add(folder)
                    
        # Log detailed information about ignored folders
        if ignored_folders:
            logger.info(f"Found {len(ignored_folders)} folders to ignore:")
            for folder in sorted(ignored_folders):
                logger.info(f"  - {folder}")
        else:
            logger.info("No folders found in ignore list")
            
        return ignored_folders
        
    except Exception as e:
        logger.error(f"Error reading ignore file: {str(e)}")
        return ignored_folders

def read_allowed_folders(file_path: str = 'main.txt') -> Set[str]:
    """
    Read list of allowed folder names from a file.
    
    Args:
        file_path: Path to the allowed folders file (default: main.txt)
        
    Returns:
        Set of allowed folder names
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"Allowed folders file not found: {file_path}")
            return set()
            
        with open(file_path, 'r') as f:
            return {line.strip() for line in f if line.strip()}
    except Exception as e:
        logger.error(f"Error reading allowed folders file: {str(e)}")
        return set()

def prepare_dropbox_account_name_parts_for_search(account_name: str, view_name: str) -> Dict[str, Any]:
    """Prepare Dropbox account data for search operations.
    
    This function extracts and normalizes name components from a Dropbox account name,
    creating a standardized data structure for search operations.
    
    Args:
        account_name (str): The Dropbox account name to process
        
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
    return prepare_account_data_for_search(account_name, view_name) 