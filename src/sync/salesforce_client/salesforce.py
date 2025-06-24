"""
Main Salesforce class for handling Salesforce operations.
"""

import logging
from typing import Dict, List, Optional, Union, Any
from pathlib import Path

from playwright.sync_api import Page
from src.config import SALESFORCE_URL
from .pages.account_manager import AccountManager
from .utils.browser import get_salesforce_page
from .utils.mock_data import get_mock_accounts
from .utils.file_upload import upload_account_files
from .pages.file_manager import SalesforceFileManager

def setup_salesforce_components_if_needed(p, account_manager, file_manager, command_runner, report_logger, args):
    """Setup Salesforce components if needed."""
    try:
        if not args.salesforce_accounts:
            logging.getLogger(__name__).info("Salesforce components not needed")
            return None, None

        logging.getLogger(__name__).info("Salesforce components needed")

        # If no command_runner, just create and return new instances
        if not account_manager:
            browser, page = get_salesforce_page(p)
            account_manager = AccountManager(page, debug_mode=True)
            account_manager.logger.report_logger = report_logger
            file_manager = SalesforceFileManager(page, debug_mode=True)

        # If command_runner is available, use its context
        if command_runner:
            if browser and page and account_manager and file_manager:
                command_runner.set_context('browser', browser)
                command_runner.set_context('page', page)
                command_runner.set_context('account_manager', account_manager)
                command_runner.set_context('file_manager', file_manager)
            # Always return the context objects (now guaranteed to be set)
            return account_manager, file_manager

        return account_manager, file_manager

    except Exception as e:
        logging.getLogger(__name__).error(f"Error setting up Salesforce components: {str(e)}")
        return None, None

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
        
    def account_exists(self, account_name: str, view_name: str = "All Clients") -> bool:
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
        
    def search_account(self, folder_name: str, view_name: str = "All Clients") -> dict:
        """Perform a fuzzy search for an account."""
        return self.account_manager.salesforce_search_account(folder_name, view_name) 