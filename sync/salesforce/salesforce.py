"""
Main Salesforce class for handling Salesforce operations.
"""

import logging
from typing import Dict, List, Optional, Union, Any
from pathlib import Path

from playwright.sync_api import Page
from sync.config import SALESFORCE_URL
from .pages.account_manager import AccountManager
from .utils.browser import get_salesforce_page
from .utils.mock_data import get_mock_accounts
from .utils.file_upload import upload_files_for_account

class Salesforce:
    """Main class for Salesforce operations."""
    
    def __init__(self, page: Page):
        """Initialize Salesforce with a Playwright page."""
        self.page = page
        self.account_manager = AccountManager(page)
        self.logger = logging.getLogger(__name__)
        
    def create_new_account(self, first_name: str, last_name: str, 
                          middle_name: Optional[str] = None, 
                          account_info: Optional[Dict[str, str]] = None) -> bool:
        """Create a new account."""
        return self.account_manager.create_new_account(
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            account_info=account_info
        )
        
    def account_exists(self, account_name: str, view_name: str = "All Accounts") -> bool:
        """Check if an account exists."""
        return self.account_manager.account_exists(account_name, view_name)
        
    def upload_file(self, file_path: Union[str, Path]) -> bool:
        """Upload a file to Salesforce."""
        # TODO: Implement file upload functionality
        self.logger.info(f"Uploading file: {file_path}")
        return True
        
    def download_file(self, file_name: str, target_dir: Union[str, Path]) -> bool:
        """Download a file from Salesforce."""
        # TODO: Implement file download functionality
        self.logger.info(f"Downloading file: {file_name} to {target_dir}")
        return True
        
    def delete_account(self, full_name: str, view_name: str = "Recent") -> bool:
        """Delete an account."""
        return self.account_manager.delete_account(full_name, view_name=view_name)
        
    def fuzzy_search_account(self, folder_name: str, view_name: str = "All Clients") -> dict:
        """Perform a fuzzy search for an account."""
        return self.account_manager.fuzzy_search_account(folder_name, view_name) 