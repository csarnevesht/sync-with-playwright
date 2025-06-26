"""General date utility functions for the sync module."""

from datetime import datetime
from typing import Optional


def convert_date(date_str: Optional[str]) -> Optional[datetime.date]:
    """
    Convert a date string to a date object, handling multiple formats.
    
    Args:
        date_str: Date string in MM/DD/YYYY or YYYY-MM-DD format
        
    Returns:
        datetime.date object if successful, None if conversion fails or input is None
    """
    if not date_str:
        return None
    try:
        # Handle MM/DD/YYYY format
        if '/' in date_str:
            date_obj = datetime.strptime(date_str, '%m/%d/%Y')
            return date_obj.date()
        # Handle YYYY-MM-DD format
        elif '-' in date_str:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj.date()
        else:
            return None
    except ValueError:
        return None


def parse_datetime_string(datetime_str: Optional[str], format_str: str = '%Y-%m-%d_%H-%M-%S') -> Optional[datetime]:
    """
    Parse a datetime string with a specific format.
    
    Args:
        datetime_str: The datetime string to parse
        format_str: The format string to use for parsing
        
    Returns:
        datetime object if successful, None if conversion fails or input is None
    """
    if not datetime_str:
        return None
    try:
        return datetime.strptime(datetime_str, format_str)
    except ValueError:
        return None 