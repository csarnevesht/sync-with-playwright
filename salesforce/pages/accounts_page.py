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
        Extract all accounts from the current list view (name and id only, no filtering).
        Optionally select a different list view by drop_down_option_text.
        """
        accounts = []
        try:
            # Navigate to accounts page
            if not self.navigate_to_accounts_list_page():
                logging.error("Failed to navigate to Accounts page")
                return []

            # Click the list view selector
            logging.info("Clicking list view selector...")
            list_view_button = self.page.wait_for_selector('button[title="Select a List View: Accounts"]', timeout=10000)
            if not list_view_button:
                logging.error("Could not find list view selector button")
                return []
            list_view_button.click()
            logging.info("Clicked list view selector")

            # Wait for the dropdown content to appear
            logging.info(f"Selecting '{drop_down_option_text}' from list view...")
            self.page.wait_for_timeout(1000)  # Give time for dropdown animation

            # Find and click the desired option
            option = self.page.locator(f'text="{drop_down_option_text}"').first
            if not option.is_visible():
                logging.error(f"Could not find visible '{drop_down_option_text}' option")
                self.page.screenshot(path=f"{drop_down_option_text.replace(' ', '_').lower()}-not-found.png")
                return []
            option.click()
            logging.info(f"Selected '{drop_down_option_text}' list view")

            # Wait for the table to update and stabilize
            logging.info(f"Waiting for the table to update and stabilize")
            self.page.wait_for_load_state('networkidle', timeout=60000)
            table = self.page.wait_for_selector('table[role="grid"]', timeout=60000)
            if not table:
                logging.error("Accounts table not found after selecting list view")
                return []
            self.page.wait_for_timeout(2000)

            # Get all account rows using nth-child
            row_count = self.page.locator('table[role="grid"] tbody tr').count()
            logging.info(f"Found {row_count} rows in the table using nth-child.")
            accounts = []
            for i in range(row_count):
                row = self.page.locator(f'table[role=\"grid\"] tbody tr:nth-child({i+1})')
                # Diagnostic: log all cell texts for the first MAX_LOGGED_ROWS
                if i < MAX_LOGGED_ROWS:
                    cell_count = row.locator('td').count()
                    cell_texts = []
                    for j in range(cell_count):
                        cell = row.locator(f'td:nth-child({j+1})')
                        try:
                            cell_texts.append(cell.text_content(timeout=1000))
                        except Exception:
                            cell_texts.append(None)
                    logging.info(f"Row {i+1} cell texts: {cell_texts}")
                    # Log th text
                    th = row.locator('th').first
                    try:
                        th_text = th.text_content(timeout=1000)
                    except Exception:
                        th_text = None
                    logging.info(f"Row {i+1} th text: {th_text}")
                # Try to get the account name from th a (link in header cell)
                try:
                    th_link = row.locator('th a').first
                    name = th_link.text_content(timeout=1000).strip()
                    href = th_link.get_attribute('href')
                except Exception:
                    # If not a link, try plain text in th
                    try:
                        th_cell = row.locator('th').first
                        name = th_cell.text_content(timeout=1000).strip()
                        href = None
                    except Exception:
                        # Fallback: try td as before
                        try:
                            name_cell = row.locator('td:nth-child(2) a').first
                            name = name_cell.text_content(timeout=1000).strip()
                            href = name_cell.get_attribute('href')
                        except Exception:
                            try:
                                name_cell = row.locator('td:nth-child(2)').first
                                name = name_cell.text_content(timeout=1000).strip()
                                href = None
                            except Exception:
                                name = None
                                href = None
                                if i < MAX_LOGGED_ROWS:
                                    logging.warning(f"Row {i+1}: Could not extract name from th, link, or plain text. Row text: {row.text_content(timeout=1000)}")
                if i < MAX_LOGGED_ROWS:
                    logging.info(f"Row {i+1}: name={name}, href={href}")
                # Extract account ID from href
                account_id = None
                if href:
                    match = re.search(r'/r/([a-zA-Z0-9]{15,18})/view', href)
                    if i < MAX_LOGGED_ROWS:
                        logging.info(f"Row {i+1}: ID match: {match}")
                    if match:
                        account_id = match.group(1)
                if name and account_id:
                    accounts.append({'name': name, 'id': account_id})

            logging.info(f"Found {len(accounts)} accounts")
            return accounts

        except Exception as e:
            logging.error(f"Error getting accounts: {str(e)}")
            self.page.screenshot(path="get-accounts-error.png")
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

    def account_has_files(self, account_id: str) -> bool:
        """
        Check if the account has files.
        """
        account_url = f"{SALESFORCE_URL}/lightning/r/{account_id}/view"
        logging.info(f"Navigating to account view page: {account_url}")
        self.page.goto(account_url)
        self.page.wait_for_load_state('networkidle', timeout=30000)
        try:
            # Find all matching <a> elements
            files_links = self.page.locator('a.slds-card__header-link.baseCard__header-title-container')
            found = False
            for i in range(files_links.count()):
                a = files_links.nth(i)
                href = a.get_attribute('href')
                outer_html = a.evaluate('el => el.outerHTML')
                # logging.info(f"Account {account_id} a[{i}] href: {href}")
                # logging.info(f"Account {account_id} a[{i}] outer HTML: {outer_html}")
                if href and 'AttachedContentDocuments' in href:
                    # This is the Files card
                    files_number_span = a.locator('span').nth(1)
                    files_number_text = files_number_span.text_content(timeout=1000)
                    files_number_match = re.search(r'\((\d+\+?)\)', files_number_text)
                    if files_number_match:
                        files_number_str = files_number_match.group(1)
                        files_number = int(files_number_str.rstrip('+'))
                    else:
                        files_number = 0
                    logging.info(f"Account {account_id} Files count: {files_number}")
                    found = True
                    return files_number > 0
            if not found:
                logging.error(f"Files card not found for account {account_id}")
                sys.exit(1)
        except Exception as e:
            logging.error(f"Could not extract files count for account {account_id}: {e}")
            sys.exit(1)

    

    



    