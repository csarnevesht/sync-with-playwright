"""Utility functions for handling Dropbox folders."""

import urllib.parse
import logging
from typing import List, Optional

def remove_url_parts(path: str) -> str:
    """
    Remove Dropbox URL parts from the path.
    
    Args:
        path (str): The path that may contain Dropbox URL parts
        
    Returns:
        str: Path with URL parts removed
    """
    if 'dropbox.com/home' in path:
        path = path.split('dropbox.com/home')[-1]
        logging.debug(f"Removed URL parts: {path}")
    return path

def decode_url_encoding(path: str) -> str:
    """
    Decode URL-encoded characters in the path.
    
    Args:
        path (str): The path that may contain URL-encoded characters
        
    Returns:
        str: Path with URL-encoded characters decoded
    """
    try:
        decoded = urllib.parse.unquote(path)
        if decoded != path:
            logging.debug(f"Decoded URL encoding: {decoded}")
        return decoded
    except Exception as e:
        logging.warning(f"Failed to decode URL encoding: {e}")
        return path

def normalize_path_structure(path: str) -> str:
    """
    Normalize the path structure by handling slashes and prefixes.
    
    Args:
        path (str): The path to normalize
        
    Returns:
        str: Normalized path
    """
    # Remove trailing slashes
    path = path.rstrip('/')
    
    # Ensure path starts with a single forward slash
    if not path.startswith('/'):
        path = '/' + path
    
    # Remove "All files" prefix if present
    if path.startswith('/All files'):
        path = path[10:]
        logging.debug(f"Removed 'All files' prefix: {path}")
    
    return path

def get_case_variations(path_parts: List[str]) -> List[str]:
    """
    Generate different case variations of the path.
    
    Args:
        path_parts (List[str]): List of path components
        
    Returns:
        List[str]: List of paths with different case variations
    """
    variations = []
    
    # Original case
    variations.append('/' + '/'.join(path_parts))
    
    # Lowercase
    variations.append('/' + '/'.join(p.lower() for p in path_parts))
    
    # Uppercase
    variations.append('/' + '/'.join(p.upper() for p in path_parts))
    
    return variations

def clean_dropbox_folder_name(path: str) -> str:
    """
    Clean and format the Dropbox folder from URL or user input.
    
    This function handles:
    - Removing Dropbox URL parts
    - Decoding URL-encoded characters
    - Normalizing path structure
    - Handling case sensitivity
    
    Args:
        path (str): The Dropbox folder to clean, can be a full URL or relative path
        
    Returns:
        str: The cleaned and normalized path
        
    Raises:
        ValueError: If the path is empty or invalid
    """
    if not path or not isinstance(path, str):
        raise ValueError("Path must be a non-empty string")
    
    logging.debug(f"Cleaning path: {path}")
    
    # Step 1: Remove URL parts
    path = remove_url_parts(path)
    
    # Step 2: Decode URL encoding
    path = decode_url_encoding(path)
    
    # Step 3: Normalize path structure
    path = normalize_path_structure(path)
    
    # Step 4: Handle case sensitivity
    path_parts = [p for p in path.split('/') if p]
    if path_parts:
        case_variations = get_case_variations(path_parts)
        logging.debug(f"Generated case variations: {case_variations}")
        # Return the original case variation as default
        path = case_variations[0]
    
    logging.debug(f"Final cleaned path: {path}")
    return path 