def get_file_type(filename: str) -> str:
    """
    Determine the file type based on the file extension.
    
    Args:
        filename: Name of the file
        
    Returns:
        str: File type (PDF, DOC, XLS, etc.) or 'Unknown' if type cannot be determined
    """
    extension = filename.split('.')[-1].lower() if '.' in filename else ''
    file_types = {
        'pdf': 'PDF',
        'doc': 'DOC',
        'docx': 'DOC',
        'xls': 'XLS',
        'xlsx': 'XLS',
        'txt': 'TXT',
        'csv': 'CSV',
        'jpg': 'JPG',
        'jpeg': 'JPG',
        'png': 'PNG',
        'gif': 'GIF',
        'zip': 'ZIP',
        'rar': 'RAR',
        '7z': '7Z',
        'ppt': 'PPT',
        'pptx': 'PPT'
    }
    return file_types.get(extension, 'Unknown') 