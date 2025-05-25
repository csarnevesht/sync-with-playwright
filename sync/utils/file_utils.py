from typing import List, Union
from dropbox.files import FileMetadata

def get_date_prefix(filename: str) -> str:
    """Extract the date prefix (YYMMDD) from a filename."""
    # Handle Salesforce file names with enumeration numbers (e.g., "1. ", "2. ")
    if isinstance(filename, str) and '. ' in filename:
        # Find the first space after the enumeration number
        space_index = filename.find('. ') + 2
        if space_index > 1:  # If we found a valid enumeration pattern
            filename = filename[space_index:]
    
    # Extract the first 6 characters as the date prefix
    try:
        return filename[:6]
    except (IndexError, TypeError):
        return ""

