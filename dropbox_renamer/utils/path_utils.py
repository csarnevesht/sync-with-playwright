"""Utility functions for handling Dropbox paths."""

import urllib.parse
import logging

def clean_dropbox_path(path: str) -> str:
    """
    Clean and format the Dropbox path from URL or user input.
    
    Args:
        path (str): The Dropbox path to clean, can be a full URL or relative path
        
    Returns:
        str: The cleaned and normalized path
    """
    logging.debug(f"Original path: {path}")
    
    # Remove URL parts if present
    if 'dropbox.com/home' in path:
        path = path.split('dropbox.com/home')[-1]
        logging.debug(f"After removing URL: {path}")
    
    # Remove any URL encoding
    path = path.replace('%20', ' ')
    logging.debug(f"After URL decoding: {path}")
    
    # Remove any trailing slashes
    path = path.rstrip('/')
    
    # Ensure path starts with a single forward slash
    if not path.startswith('/'):
        path = '/' + path
    
    # Remove any "All files" prefix if present
    if path.startswith('/All files'):
        path = path[10:]  # Remove '/All files' prefix
    
    # Try to normalize the path
    path_parts = [p for p in path.split('/') if p]
    
    # Handle case sensitivity issues by trying different case combinations
    if len(path_parts) > 0:
        # Try with original case first
        path = '/' + '/'.join(path_parts)
        logging.debug(f"Trying path with original case: {path}")
        
        # If that fails, try with lowercase
        path_lower = '/' + '/'.join(p.lower() for p in path_parts)
        logging.debug(f"Trying path with lowercase: {path_lower}")
        
        # If that fails, try with uppercase
        path_upper = '/' + '/'.join(p.upper() for p in path_parts)
        logging.debug(f"Trying path with uppercase: {path_upper}")
    
    logging.debug(f"Final cleaned path: {path}")
    return path 