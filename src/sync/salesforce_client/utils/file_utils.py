from typing import Dict

def get_file_type(file_name: str) -> str:
    """Determine the file type from the file name extension.
    
    Args:
        file_name: The name of the file
        
    Returns:
        str: The standardized file type (PDF, DOC, XLS, TXT, IMG, or Unknown)
    """
    file_name = file_name.lower()
    if file_name.endswith('.pdf'):
        return 'PDF'
    elif file_name.endswith(('.doc', '.docx')):
        return 'DOC'
    elif file_name.endswith(('.xls', '.xlsx')):
        return 'XLS'
    elif file_name.endswith('.txt'):
        return 'TXT'
    elif file_name.endswith(('.jpg', '.jpeg', '.png')):
        return 'IMG'
    return 'Unknown'

def parse_search_file_pattern(file_pattern: str) -> Dict:
    """Parse a search file pattern into a file info dictionary.
    
    Args:
        file_pattern: The file pattern to search for (e.g., "John Smith Application.pdf")
        
    Returns:
        dict: Dictionary containing:
            - name: The file name without extension
            - type: The file type (PDF, DOC, etc.)
            - full_name: The full file name with type in brackets
    """
    # Split the pattern to get name and extension
    search_file_name = file_pattern.split('.')[0].strip()
    search_file_type = get_file_type(file_pattern)
    
    return {
        'name': search_file_name,
        'type': search_file_type,
        'full_name': f"{search_file_name} [{search_file_type}]"
    } 