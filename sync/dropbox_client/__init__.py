"""
Dropbox integration package for Salesforce sync.

This package provides utilities for interacting with Dropbox, including:
- File operations
- Account management
- Path handling
- Date utilities
"""

from .utils.dropbox_utils import DropboxClient
from .utils.path_utils import clean_dropbox_path
from .utils.account_utils import read_accounts_folders, read_ignored_folders
from .utils.date_utils import has_date_prefix

__all__ = [
    'DropboxClient',
    'clean_dropbox_path',
    'read_accounts_folders',
    'read_ignored_folders',
    'has_date_prefix'
]

__version__ = "0.1.0" 