"""Utility functions for date handling and formatting."""

import datetime
import re

def has_date_prefix(name):
    """Check if the filename already has a date prefix (YYYYMMDD or YYMMDD)."""
    # Regular expression to match various date formats at the beginning of the filename:
    # - YYYYMMDD (e.g., 20240101)
    # - YYYYMMDD with space and time (e.g., 20240101 123456)
    # - YYYYMMDD with underscore and time (e.g., 20240101_123456)
    # - YYMMDD (e.g., 210928)
    pattern = r'^(?:(?:19|20)\d{6}(?:\s+\d{6}|_\d{6}|\s+|$)|(?:[0-9]{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])))'
    return bool(re.match(pattern, name))

def format_duration(seconds):
    """Format duration in seconds to a human-readable string with hours, minutes, and seconds."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds:.1f}s"
    elif minutes > 0:
        return f"{minutes}m {seconds:.1f}s"
    else:
        return f"{seconds:.1f}s"

def get_folder_creation_date(dbx, path):
    """Get the creation date of a folder by looking at its contents."""
    try:
        # List the folder contents
        result = dbx.files_list_folder(path)
        
        # If folder has contents, find the oldest file
        if result.entries:
            oldest_date = None
            for entry in result.entries:
                if isinstance(entry, dropbox.files.FileMetadata):
                    if oldest_date is None or entry.server_modified < oldest_date:
                        oldest_date = entry.server_modified
            
            # If we found files, use the oldest file's date
            if oldest_date:
                return oldest_date
        
        # If no files found or empty folder, try looking at the folder info
        folder_info = dbx.files_get_metadata(path)
        
        # Some Dropbox API versions might include a 'client_modified' field
        if hasattr(folder_info, 'client_modified'):
            return folder_info.client_modified
            
        # Try getting the shared folder info which might have creation date
        try:
            shared_info = dbx.sharing_get_folder_metadata(path)
            if hasattr(shared_info, 'time_created'):
                return shared_info.time_created
        except:
            pass
        
        # If all else fails, use the current date
        return datetime.datetime.now()
        
    except Exception as e:
        print(f"Error getting folder creation date for {path}: {e}")
        return datetime.datetime.now() 