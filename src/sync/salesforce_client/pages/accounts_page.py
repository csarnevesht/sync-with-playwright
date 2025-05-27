from playwright.sync_api import Page, expect
from typing import Optional, List, Dict, Callable, Any
import re
import os
import time
import logging
from src.config import SALESFORCE_URL
import sys
from .base_page import BasePage

MAX_LOGGED_ROWS = 5  # Only log details for the first N rows/links

class AccountsPage:
    def __init__(self, page: Page, debug_mode: bool = False):
        self.page = page
        self.debug_mode = debug_mode
        self.current_account_id = None  # Store the ID of the last created account
        if debug_mode:
            logging.info("Debug mode is enabled for AccountsPage")

    def _navigate_to_accounts_list_view_url(self, view_name: str) -> bool:
        """Navigate to a specific list view URL.
        
        Args:
            view_name: Name of the list view to navigate to
            
        Returns:
            bool: True if navigation was successful, False otherwise
        """
        try:
            # Construct the URL with the correct list view filter
            filter_name = view_name.replace(" ", "")
            url = f"{SALESFORCE_URL}/lightning/o/Account/list?filterName={filter_name}"
            logging.info(f"Navigating directly to list view URL: {url}")
            
            # Navigate to the URL
            self.page.goto(url)
            self.page.wait_for_load_state('networkidle', timeout=10000)
            self.page.wait_for_load_state('domcontentloaded', timeout=10000)
            return True
        except Exception as e:
            logging.error(f"Error navigating to list view URL: {str(e)}")
            return False

    def _extract_files_count_from_files_card_in_account(self, account_id: str) -> Optional[int]:
        """
        Extract the number of files from the Files card for a given account.
        
        Args:
            account_id (str): The ID of the account to check
            
        Returns:
            Optional[int]: The number of files found, or None if not found
        """
        try:
            files_card = self._find_files_card()
            if not files_card:
                logging.warning(f"Files card not found for account {account_id}")
                return None
                
            files_number = self._parse_files_count_from_files_card_in_account(files_card)
            logging.info(f"Account {account_id} Files count: {files_number}")
            return files_number
            
        except Exception as e:
            logging.warning(f"Could not extract files count for account {account_id}: {e}")
            return None
            
    def _find_files_card(self) -> Optional[Any]:
        """
        Find the Files card in the page.
        
        Returns:
            Optional[Any]: The Files card element if found, None otherwise
        """
        files_links = self.page.locator('a.slds-card__header-link.baseCard__header-title-container')
        
        for i in range(files_links.count()):
            link = files_links.nth(i)
            href = link.get_attribute('href')
            outer_html = link.evaluate('el => el.outerHTML')
            
            logging.debug(f"Checking link[{i}] href: {href}")
            logging.debug(f"Checking link[{i}] outer HTML: {outer_html}")
            
            if href and 'AttachedContentDocuments' in href:
                return link
                
        return None
        
    def _parse_files_count_from_files_card_in_account(self, files_card: Any) -> int:
        """
        Parse the files count from the Files card element.
        
        Args:
            files_card (Any): The Files card element
            
        Returns:
            int: The number of files found, 0 if not found
        """
        try:
            files_number_span = files_card.locator('span').nth(1)
            files_number_text = files_number_span.text_content(timeout=1000)
            
            files_number_match = re.search(r'\((\d+\+?)\)', files_number_text)
            if not files_number_match:
                return 0
                
            files_number_str = files_number_match.group(1)
            return int(files_number_str.rstrip('+'))
            
        except Exception as e:
            logging.warning(f"Error parsing files count: {e}")
            return 0
        

    

    

    



    