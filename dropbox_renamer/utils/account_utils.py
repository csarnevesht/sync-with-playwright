"""Utility functions for handling account-related operations."""

import os
from typing import List, Optional

def read_accounts_folders(accounts_file: Optional[str] = None) -> List[str]:
    """
    Read account folder names from a file in the accounts directory.
    By default, reads from main.txt if no file is specified.
    
    Args:
        accounts_file: Optional name of the file in the accounts directory to read from.
                      If not provided, defaults to 'main.txt'.
    
    Returns:
        List of account folder names.
    """
    # Determine the accounts directory path
    accounts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'accounts')
    
    # Use main.txt if no file specified
    if not accounts_file:
        accounts_file = 'main.txt'
    
    # Construct the full path to the accounts file
    file_path = os.path.join(accounts_dir, accounts_file)
    
    try:
        with open(file_path, 'r') as f:
            # Read lines and strip whitespace, filtering out empty lines
            accounts = [line.strip() for line in f if line.strip()]
        return accounts
    except FileNotFoundError:
        print(f"Error: Accounts file not found at {file_path}")
        return []
    except Exception as e:
        print(f"Error reading accounts file: {e}")
        return [] 