from playwright.sync_api import Page, expect
from typing import Optional, List, Dict
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

    def _debug_prompt(self, message: str) -> bool:
        """Prompt the user for input in debug mode."""
        if not self.debug_mode:
            return True
            
        while True:
            response = input(f"{message} (y/n): ").lower()
            if response in ['y', 'Y']:
                return response == 'y'
            logging.info("Please enter 'y' or 'n'")

    def navigate_to_accounts(self) -> bool:
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

    def get_all_accounts(self) -> List[Dict[str, str]]:
        """
        Navigate to accounts, select the "All Accounts" list view, and return the list of accounts.
        
        Returns:
            List[Dict[str, str]]: List of accounts with their details, or empty list if failed
        """
        try:
            # Navigate to accounts page
            if not self.navigate_to_accounts():
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
            logging.info("Selecting 'All Accounts' from list view...")
            self.page.wait_for_timeout(1000)  # Give time for dropdown animation
            
            # Find and click the All Accounts option
            all_accounts_option = self.page.locator('text="All Accounts"').first
            if not all_accounts_option.is_visible():
                logging.error("Could not find visible 'All Accounts' option")
                self.page.screenshot(path="all-accounts-not-found.png")
                return []
            all_accounts_option.click()
            logging.info("Selected 'All Accounts' list view")
            
            # Wait for the table to update and stabilize
            self.page.wait_for_load_state('networkidle', timeout=10000)
            table = self.page.wait_for_selector('table[role="grid"]', timeout=10000)
            if not table:
                logging.error("Accounts table not found after selecting All Accounts")
                return []
            
            # Wait for the table to be populated
            logging.info("Waiting for table to be populated...")
            self.page.wait_for_timeout(2000)
            
            # Wait for the summary span to appear
            logging.info("Waiting for summary span to appear...")
            summary_span = self.page.wait_for_selector("span[aria-label='All Accounts']", timeout=10000)
            if not summary_span:
                logging.error("Could not find summary span for 'All Accounts'")
                return []

            summary_text = summary_span.text_content().strip()
            logging.info(f"Summary text: {summary_text}")

            # Extract number of items (allow for "50 items" or "50+ items")
            items_match = re.search(r'(\d+\+?)\s+items?\s+•', summary_text)
            if not items_match:
                logging.error("Could not extract number of items from summary text")
                return []

            num_items = items_match.group(1)
            logging.info(f"Number of items: {num_items}")

            # Verify the filter
            logging.info(f"Verifying filter: {summary_text}")
            if "Filtered by All accounts" not in summary_text:
                logging.error("Summary text does not indicate 'Filtered by All accounts'")
                return []
            
            # Get all account rows using nth-child
            logging.info("Getting all account rows using nth-child...")
            row_count = self.page.locator('table[role="grid"] tbody tr').count()
            logging.info(f"Found {row_count} rows in the table using nth-child.")
            logging.info(f"Getting all account rows using nth-child...")
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
                    match = re.search(r'/Account/([a-zA-Z0-9]{15,18})/', href)
                    if i < MAX_LOGGED_ROWS:
                        logging.info(f"Row {i+1}: ID match: {match}")
                    if match:
                        account_id = match.group(1)
                if name and account_id:
                    accounts.append({'name': name, 'id': account_id})

            logging.info(f"Found {len(accounts)} accounts")
            return accounts

        except Exception as e:
            logging.error(f"Error getting all accounts: {str(e)}")
            self.page.screenshot(path="get-all-accounts-error.png")
            return [] 