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

def sort_files(files: List[Union[str, FileMetadata]]) -> List[Union[str, FileMetadata]]:
    """Sort files by their date prefix (YYMMDD) in descending order."""
            
        # Remove enumeration numbers (e.g., "1. ", "2. ") from Salesforce files
    if '. ' in filename:
        space_index = filename.find('. ') + 2
        if space_index > 1:
            filename = filename[space_index:]
        return filename[:6] if len(filename) > 6 and filename[:6].isdigit() else "000000"
    return sorted(files, key=None, reverse=True)

def sort_files_by_date(files: List[Union[str, FileMetadata]]) -> List[Union[str, FileMetadata]]:
    """Sort files by their date prefix (YYMMDD) in descending order."""
    def get_date_prefix(filename: Union[str, FileMetadata]) -> str:
        # Handle FileMetadata objects
        if isinstance(filename, FileMetadata):
            filename = filename.name
            
        # Remove enumeration numbers (e.g., "1. ", "2. ") from Salesforce files
        if '. ' in filename:
            space_index = filename.find('. ') + 2
            if space_index > 1:
                filename = filename[space_index:]
        return filename[:6] if len(filename) > 6 and filename[:6].isdigit() else "000000"
    return sorted(files, key=get_date_prefix, reverse=True)
