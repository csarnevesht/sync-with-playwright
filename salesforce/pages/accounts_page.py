from playwright.sync_api import Page, expect
from typing import Optional, List, Dict, Callable, Any
import re
import os
import time
import logging
from config import SALESFORCE_URL
import sys

MAX_LOGGED_ROWS = 5  # Only log details for the first N rows/links

class AccountsPage:
    def __init__(self, page: Page, debug_mode: bool = False):
        self.page = page
        self.debug_mode = debug_mode
        self.current_account_id = None  # Store the ID of the last created account
        if debug_mode:
            logging.info("Debug mode is enabled for AccountsPage")

    def select_list_view(self, view_name: str) -> bool:
        """
        Select a specific list view from the dropdown.
        
        Args:
            view_name: Name of the list view to select (e.g., "All Accounts", "All Clients")
            
        Returns:
            bool: True if selection was successful, False otherwise
        """
        try:
            # Click the list view selector
            logging.info("Clicking list view selector...")
            list_view_button = self.page.wait_for_selector('button[title="Select a List View: Accounts"]', timeout=10000)
            if not list_view_button:
                logging.error("Could not find list view selector button")
                return False
            list_view_button.click()
            logging.info("Clicked list view selector")

            # Wait for the dropdown content to appear
            logging.info(f"Selecting '{view_name}' from list view...")
            self.page.wait_for_timeout(1000)  # Give time for dropdown animation

            # Find and click the desired option
            option = self.page.locator(f'text="{view_name}"').first
            if not option.is_visible():
                logging.error(f"Could not find visible '{view_name}' option")
                self.page.screenshot(path=f"{view_name.replace(' ', '_').lower()}-not-found.png")
                return False
            option.click()
            logging.info(f"Selected '{view_name}' list view")

            # Wait for the table to update and stabilize
            self.page.wait_for_timeout(2000)
            return True

        except Exception as e:
            logging.error(f"Error selecting list view '{view_name}': {str(e)}")
            return False

    def navigate_to_accounts_list_page(self) -> bool:
        """Navigate to the Accounts page."""
        target_url = f"{SALESFORCE_URL}/lightning/o/Account/list?filterName=__Recent"
        logging.info(f"Navigating to Accounts page: {target_url}")
        
        try:
            # Check if we're already on the accounts page
            current_url = self.page.url
            if "/lightning/o/Account/list" in current_url:
                logging.info("Already on Accounts page")
                # Wait for the page to be fully loaded
                self.page.wait_for_load_state('domcontentloaded', timeout=10000)
            else:
                # Navigate to the page
                self.page.goto(target_url)
                # Wait for initial page load
                self.page.wait_for_load_state('domcontentloaded', timeout=30000)
            
            # Wait for the search input with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    search_input = self.page.wait_for_selector('input[placeholder="Search this list..."]', timeout=10000)
                    if search_input:
                        break
                except Exception as e:
                    if attempt == max_retries - 1:
                        logging.error(f"Search input not found after {max_retries} attempts. Current URL: {self.page.url}")
                        # Log all visible div classes
                        divs = self.page.locator('div').all()
                        for div in divs:
                            if div.is_visible():
                                logging.info(f"Visible div class: {div.get_attribute('class')}")
                        self.page.screenshot(path="accounts-navigation-error.png")
                        return False
                    logging.warning(f"Attempt {attempt + 1} to find search input failed, retrying...")
                    self.page.wait_for_timeout(2000)
            
            # Wait for the table to be visible with retry
            for attempt in range(max_retries):
                try:
                    table = self.page.wait_for_selector('table[role="grid"]', timeout=10000)
                    if table and table.is_visible():
                        break
                except Exception as e:
                    if attempt == max_retries - 1:
                        logging.error(f"Accounts table not found or not visible after {max_retries} attempts. Current URL: {self.page.url}")
                        # Log all visible div classes
                        divs = self.page.locator('div').all()
                        for div in divs:
                            if div.is_visible():
                                logging.info(f"Visible div class: {div.get_attribute('class')}")
                        self.page.screenshot(path="accounts-table-not-found.png")
                        return False
                    logging.warning(f"Attempt {attempt + 1} to find table failed, retrying...")
                    self.page.wait_for_timeout(2000)
            
            # Additional wait to ensure everything is stable
            self.page.wait_for_timeout(2000)
            
            logging.info("Successfully navigated to Accounts page")
            return True
            
        except Exception as e:
            logging.error(f"Error navigating to Accounts page: {str(e)}")
            self.page.screenshot(path="accounts-navigation-error.png")
            return False

    def _get_accounts_base(self, drop_down_option_text: str = "All Clients") -> List[Dict[str, str]]:
        """
        Get all accounts from the current list view.
        
        Args:
            drop_down_option_text: Name of the list view to select
            
        Returns:
            List[Dict[str, str]]: List of account dictionaries with 'name' and 'id' keys
        """
        try:
            # Navigate to accounts page
            if not self.navigate_to_accounts_list_page():
                logging.error("Failed to navigate to Accounts page")
                return []

            # Select the specified list view
            if not self.select_list_view(drop_down_option_text):
                return []

            # Get all account rows
            account_rows = self.page.locator('table[role="grid"] tr').all()
            accounts = []
            
            for row in account_rows:
                try:
                    # Get account name and ID
                    name_cell = row.locator('td:first-child a').first
                    if not name_cell:
                        continue
                        
                    name = name_cell.text_content().strip()
                    href = name_cell.get_attribute('href')
                    account_id = href.split('/')[-1] if href else None
                    
                    if name and account_id:
                        accounts.append({
                            'name': name,
                            'id': account_id
                        })
                except Exception as e:
                    logging.warning(f"Error processing account row: {str(e)}")
                    continue
            
            return accounts
            
        except Exception as e:
            logging.error(f"Error getting accounts: {str(e)}")
            return []

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
        

    

    

    



    