from playwright.sync_api import Page, expect
from typing import Optional, List, Dict
import re
import os
import time
import logging
from config import SALESFORCE_URL
import sys

from salesforce.pages import account_manager

class AccountsPage:
    def __init__(self, page: Page, debug_mode: bool = False):
        self.page = page
        self.debug_mode = debug_mode
        self.current_account_id = None  # Store the ID of the last created account
        if debug_mode:
            logging.info("Debug mode is enabled for AccountsPage")

    def _debug_prompt(self, message: str) -> bool:
        """Prompt the user for input in debug mode."""
        if not self.debug_mode:
            return True
            
        while True:
            response = input(f"{message} (y/n): ").lower()
            if response in ['y', 'Y']:
                return response == 'y'
            logging.info("Please enter 'y' or 'n'")



    def iterate_through_accounts(self, account_names: List[str]):
        """
        Iterate through a list of account names, search for each account, and navigate to the account view page.
        
        Args:
            account_names: List of account names to iterate through.
        """
        for account_name in account_names:
            logging.info(f"\nSearching for account: {account_name}")
            account_manager.navigate_to_accounts()
            self.search_account(account_name)
            if account_manager.click_account_name(account_name):
                logging.info(f"Successfully navigated to account view page for: {account_name}")
            else:
                logging.info(f"Failed to navigate to account view page for: {account_name}") 