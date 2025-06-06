from typing import Callable, Optional, Dict, List, Union, Any
import logging
import re
import time
import json
from pathlib import Path

from . import file_manager
from .base_page import BasePage
from playwright.sync_api import Page, TimeoutError
from src.config import SALESFORCE_URL
import sys
import os
from .accounts_page import AccountsPage
from ..utils.selectors import Selectors
from sync.utils.name_utils import _load_special_cases, _is_special_case, _get_special_case_rules, extract_name_parts

class LoggingHelper:
    """Helper class to manage logging indentation and color based on call depth and keyword."""
    _indent_level = 0
    _indent_str = "  "  # 2 spaces per level
    _timing_stack = []  # Stack to track timing of nested operations

    # ANSI color codes
    COLORS = {
        'reset': '\033[0m',
        'search_account': '\033[1;36m',      # Bold Cyan
        'found_account_names': '\033[1;32m', # Bold Green
        'get_account_names': '\033[1;35m',   # Bold Magenta
        'account_elements': '\033[1;34m',    # Bold Blue
        'search_by_last_name': '\033[95m',   # Pink (Bright Magenta)
        'search_by_full_name': '\033[95m',   # Pink (Bright Magenta)
        'fuzzy_search_account': '\033[1;37m',# Bold White
        'timing': '\033[1;33m',             # Bold Yellow
        'default': '',
    }

    @classmethod
    def format_duration(cls, seconds: float) -> str:
        """Format duration in seconds to a human-readable string."""
        if seconds < 60:
            return f"{seconds:.2f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.2f} minutes"
        else:
            hours = seconds / 3600
            return f"{hours:.2f} hours"

    @classmethod
    def start_timing(cls):
        """Start timing an operation."""
        cls._timing_stack.append(time.time())

    @classmethod
    def end_timing(cls) -> float:
        """End timing an operation and return the duration in seconds."""
        if not cls._timing_stack:
            return 0.0
        start_time = cls._timing_stack.pop()
        duration = time.time() - start_time
        return duration

    @classmethod
    def indent(cls):
        """Increase indentation level."""
        cls._indent_level += 1

    @classmethod
    def dedent(cls):
        """Decrease indentation level."""
        cls._indent_level = max(0, cls._indent_level - 1)

    @classmethod
    def get_indent(cls):
        """Get current indentation string."""
        return cls._indent_str * cls._indent_level

    @classmethod
    def colorize(cls, msg: str) -> str:
        # Assign color based on keyword in the message
        color = None
        if 'search_account' in msg:
            color = cls.COLORS['search_account']
        elif 'found_account_names' in msg:
            color = cls.COLORS['found_account_names']
        elif 'get_account_names' in msg:
            color = cls.COLORS['get_account_names']
        elif 'account_elements' in msg:
            color = cls.COLORS['account_elements']
        elif 'search_by_last_name' in msg:
            color = cls.COLORS['search_by_last_name']
        elif 'search_by_full_name' in msg:
            color = cls.COLORS['search_by_full_name']
        elif 'fuzzy_search_account' in msg:
            color = cls.COLORS['fuzzy_search_account']
        elif 'timing' in msg:
            color = cls.COLORS['timing']
        if color:
            return f"{color}{msg}{cls.COLORS['reset']}"
        return msg

    @classmethod
    def log(cls, logger, level, msg, *args, **kwargs):
        """Log a message with current indentation."""
        indent = cls.get_indent()
        if isinstance(msg, str):
            msg = f"{indent}{msg}"
            msg = cls.colorize(msg)
        
        # Ensure the message is logged to both the provided logger and root logger
        getattr(logger, level)(msg, *args, **kwargs)
        root_logger = logging.getLogger()
        if root_logger != logger:  # Avoid duplicate logging
            getattr(root_logger, level)(msg, *args, **kwargs)

    @classmethod
    def log_timing(cls, logger, operation_name: str):
        """Log the timing of an operation."""
        duration = cls.end_timing()
        formatted_duration = cls.format_duration(duration)
        cls.log(logger, 'info', f"Timing for {operation_name}: {formatted_duration}")

class AccountManager(BasePage):
    """Handles account-related operations in Salesforce."""
    
    log_helper = LoggingHelper()  # fallback for class-level access
    
    def __init__(self, page: Page, debug_mode: bool = False):
        super().__init__(page, debug_mode)
        self.current_account_id = None
        self.accounts_page = AccountsPage(page, debug_mode)
        self.special_cases = _load_special_cases()
        if not hasattr(self, 'log_helper') or self.log_helper is None:
            self.log_helper = LoggingHelper()
        
        # Get the root logger and set it as the logger for this instance
        self.logger = logging.getLogger()
        if debug_mode:
            self.logger.setLevel(logging.DEBUG)
    

    def navigate_to_accounts_list_page(self, view_name: str = "All Clients") -> bool:
        """Navigate to the Accounts page with a specific list view.
        
        Args:
            view_name: Name of the list view to use (default: "All Clients")
            
        Returns:
            bool: True if navigation was successful, False otherwise
        """
        self.log_helper.start_timing()
        self.log_helper.indent()
        try:
            # Navigate to the list view
            if not self._navigate_to_accounts_list_view_url(view_name):
                self.log_helper.log(self.logger, 'error', "Failed to navigate to list view")
                self._take_screenshot("accounts-navigation-error")
                self.log_helper.dedent()
                return False
                
            # Wait for the search input
            if not self._wait_for_selector('ACCOUNT', 'search_input', timeout=20000):
                self.log_helper.log(self.logger, 'error', "Search input not found")
                self._take_screenshot("accounts-navigation-error")
                self.log_helper.dedent()
                return False
                
            # Verify the accounts table is visible
            if not self._wait_for_selector('ACCOUNT', 'account_table'):
                self.log_helper.log(self.logger, 'error', "Accounts table not visible")
                self.log_helper.dedent()
                return False
                
            self.log_helper.log(self.logger, 'info', "Successfully navigated to Accounts page")
            self.log_helper.dedent()
            self.log_helper.log_timing(self.logger, f"navigate_to_accounts_list_page for view: {view_name}")
            return True
            
        except Exception as e:
            self.log_helper.log(self.logger, 'error', f"Error navigating to Accounts page: {str(e)}")
            self.log_helper.log_timing(self.logger, f"navigate_to_accounts_list_page (error) for view: {view_name}")
            self._take_screenshot("accounts-navigation-error")
            self.log_helper.dedent()
            return False

    def _navigate_to_accounts_list_view_url(self, view_name: str) -> bool:
        """Navigate to a specific list view URL.
        
        Args:
            view_name: Name of the list view to navigate to
            
        Returns:
            bool: True if navigation was successful, False otherwise
        """
        self.log_helper.indent()
        self.log_helper.log(self.logger, 'info', f"Navigating to list view URL (_navigate_to_accounts_list_view_url): {view_name}")
        
        max_attempts = 3
        attempt = 1
        
        while attempt <= max_attempts:
            try:
                # Construct the URL with the correct list view filter
                filter_name = view_name.replace(" ", "")
                url = f"{SALESFORCE_URL}/lightning/o/Account/list?filterName={filter_name}"

                # Check if we're already on the correct URL
                current_url = self.page.url
                if current_url == url:
                    self.log_helper.log(self.logger, 'info', f"Already on the correct list view URL: {url}")
                    self.log_helper.dedent()
                    return True
                    
                self.log_helper.log(self.logger, 'info', f"Attempt {attempt}/{max_attempts}: Navigating to list view URL: {url}")
                
                # Navigate to the URL with increased timeout
                self.page.goto(url, timeout=30000)  # Increased timeout to 30 seconds
                
                # Wait for network to be idle with increased timeout
                # try:
                #     self.page.wait_for_load_state('networkidle', timeout=20000)  # Increased timeout to 20 seconds
                # except Exception as e:
                #     self.log_helper.log(self.logger, 'warning', f"Network idle timeout, but continuing: {str(e)}")
                
                # Wait for DOM content to be loaded
                # try:
                #     self.page.wait_for_load_state('domcontentloaded', timeout=20000)  # Increased timeout to 20 seconds
                # except Exception as e:
                #     self.log_helper.log(self.logger, 'warning', f"DOM content load timeout, but continuing: {str(e)}")
                
                # Verify we're on the correct page
                current_url = self.page.url
                if url in current_url:
                    self.log_helper.log(self.logger, 'info', f"Successfully navigated to list view URL: {url}")
                    self.log_helper.dedent()
                    return True
                else:
                    self.log_helper.log(self.logger, 'warning', f"URL mismatch. Expected: {url}, Got: {current_url}")
                    if attempt < max_attempts:
                        self.log_helper.log(self.logger, 'info', f"Retrying in 2 seconds...")
                        self.page.wait_for_timeout(2000)
                    attempt += 1
                    
            except Exception as e:
                self.log_helper.log(self.logger, 'error', f"Error navigating to list view URL (attempt {attempt}/{max_attempts}): {str(e)}")
                if attempt < max_attempts:
                    self.log_helper.log(self.logger, 'info', f"Retrying in 2 seconds...")
                    self.page.wait_for_timeout(2000)
                attempt += 1
        
        self.log_helper.log(self.logger, 'error', f"Failed to navigate to list view URL after {max_attempts} attempts")
        self.log_helper.dedent()
        return False

    def search_account(self, search_term: str, view_name: str = "All Clients") -> List[str]:
        """
        Search for an account in Salesforce.
        
        Args:
            search_term: The term to search for
            view_name: The name of the list view to use
            
        Returns:
            bool: True if search was successful, False otherwise
        """
        self.log_helper.start_timing()
        found_account_names = []  # Initialize once before the loop
        self.log_helper.indent()
        try:
            # Navigate to accounts page if not already there
            if not self.navigate_to_accounts_list_page():
                self.log_helper.dedent()
                return found_account_names
            
            # Clear any existing search
            self.clear_search()
            
            self.log_helper.log(self.logger, 'info', f"INFO: search_account ***searching for search term: {search_term}")

            # Enter search term
            search_input = self.page.locator("input[placeholder='Search this list...']")
            search_input.fill(search_term)
            search_input.press("Enter")
            self.log_helper.log(self.logger, 'info', f"Pressed Enter for search term: {search_term}")
            self.log_helper.log(self.logger, 'info', f"Waiting for 2 second(s)...")
            self.page.wait_for_timeout(2000)
            
            # After pressing Enter, check for empty content before checking for rows
            try:
                # Wait for either the empty content or the table to appear
                self.page.wait_for_selector(
                    'div.emptyContent.slds-is-absolute, table.slds-table',
                    timeout=10000
                )
                # Check if the empty content is visible
                empty_content = self.page.locator('div.emptyContent.slds-is-absolute').first
                if empty_content and empty_content.is_visible():
                    self.log_helper.log(self.logger, 'info', f"No items to display for search term: {search_term}")
                    self.log_helper.dedent()
                    return found_account_names
            except Exception as e:
                self.log_helper.log(self.logger, 'warning', f"Error waiting for empty content or table: {str(e)}")
            
            # Wait for search results
            try:
                # Wait for the loading spinner to disappear
                self.page.wait_for_selector('div.slds-spinner_container', state='hidden', timeout=5000)
                
                # Wait for the table to be visible
                table = self.page.wait_for_selector('table.slds-table', timeout=10000)
                if not table:
                    self.log_helper.log(self.logger, 'error', "Search results table not found")
                    self.log_helper.dedent()
                    return found_account_names
                
                # Parse the number of items from the status bar (e.g., '0 items' or '50+ items')
                num_items = None
                try:
                    status_bar = self.page.locator('span.countSortedByFilteredBy[role="status"]').first
                    if status_bar:
                        status_bar.wait_for(state='visible', timeout=5000)
                        status_text = status_bar.text_content().strip()
                        import re
                        match = re.search(r'(\d+\+?) items?', status_text)
                        if match:
                            num_items_str = match.group(1)
                            if num_items_str.endswith('+'):
                                num_items = int(num_items_str[:-1])
                                self.log_helper.log(self.logger, 'info', f"Salesforce reports {num_items_str} items (50+ means 50 or more) for search term: {search_term}")
                            else:
                                num_items = int(num_items_str)
                                self.log_helper.log(self.logger, 'info', f"Salesforce reports {num_items} items for search term: {search_term}")
                        else:
                            self.log_helper.log(self.logger, 'warning', f"Could not parse number of items from status bar: '{status_text}'")
                    else:
                        self.log_helper.log(self.logger, 'warning', "Status bar element not found for item count.")
                except Exception as e:
                    self.log_helper.log(self.logger, 'warning', f"Error parsing number of items from status bar: {str(e)}")
                
                # Wait for any rows to be visible
                rows = self.page.locator('table.slds-table tbody tr').all()
                num_rows = len(rows)
                self.log_helper.log(self.logger, 'info', f"Found {num_rows} rows in table for search term: {search_term}")

                # If status bar says 50+ and num_rows < 50, warn about lazy loading
                if num_items is not None and isinstance(num_items, int) and num_rows < num_items:
                    self.log_helper.log(self.logger, 'warning', f"Table may not have loaded all rows: status bar says {num_items}+ items, but only {num_rows} rows are visible. Consider implementing scrolling or pagination.")
                    # After warning, check for the empty content indicator
                    empty_content = self.page.locator('div.emptyContent.slds-is-absolute').first
                    if empty_content and empty_content.is_visible():
                        self.log_helper.log(self.logger, 'info', f"No items to display for search term: {search_term}")
                        self.log_helper.dedent()
                        return found_account_names
                    else:
                        self.log_helper.log(self.logger, 'info', f"***Table loaded with {num_rows} rows for search term: {search_term}")
                
                # Log each result
                for row in rows:
                    try:
                        # Try several selectors for the account name
                        name_cell = None
                        for selector in ['td:nth-child(2) a', 'th[scope="row"] a', 'td:first-child a']:
                            candidate = row.locator(selector).first
                            try:
                                if candidate and candidate.is_visible(timeout=1000):
                                    name_cell = candidate
                                    break
                            except Exception:
                                continue
                        
                        if name_cell:
                            name = name_cell.text_content(timeout=2000).strip()
                            self.log_helper.log(self.logger, 'info', f"Found account: {name} in name_cell")
                            found_account_names.append(name)
                        else:
                            self.log_helper.log(self.logger, 'warning', f"Could not find account name link in row for search term: {search_term}")
                    except Exception as e:
                        self.log_helper.log(self.logger, 'warning', f"Error getting account name from row: {str(e)}")
                        continue
                
                # Only log if no account names were found
                self.log_helper.log(self.logger, 'info', f"DEBUG: found_account_names = {found_account_names}")
                self.log_helper.log(self.logger, 'info', f"DEBUG: len(found_account_names) = {len(found_account_names)}")
                if len(found_account_names) == 0:
                    self.log_helper.log(self.logger, 'info', "***No account names found in search results")
                
                # Compare the parsed number of items to the number of rows
                if num_items is not None:
                    if num_items != num_rows:
                        self.log_helper.log(self.logger, 'warning', f"Discrepancy: Salesforce reports {num_items} items, but found {num_rows} rows in table for search term: {search_term}")
                    else:
                        self.log_helper.log(self.logger, 'info', f"Number of items matches number of rows for search term: {search_term}")
                
                # If 0 items, log and return
                if num_items == 0 or num_rows == 0:
                    self.log_helper.log(self.logger, 'info', f"No results found for search term: {search_term}")
                    self.log_helper.dedent()
                    return found_account_names
                
                self.log_helper.dedent()
                self.log_helper.log_timing(self.logger, f"search_account for term: {search_term}")
                return found_account_names
                
            except Exception as e:
                self.log_helper.log(self.logger, 'error', f"Error waiting for search results: {str(e)}")
                self.log_helper.dedent()
                return found_account_names
            
        except Exception as e:
            self.log_helper.log(self.logger, 'error', f"Error searching for account: {str(e)}")
            self.log_helper.log_timing(self.logger, f"search_account (error) for term: {search_term}")
            self.log_helper.dedent()
            return []

    def clear_search(self):
        """Clear the search field by searching for '--' and verifying no results."""
        self.log_helper.indent()
        max_attempts = 2
        attempt = 1
        
        while attempt <= max_attempts:
            try:
                self.log_helper.log(self.logger, 'info', f"Clear search attempt {attempt}/{max_attempts}")
                
                # Clear and fill search input
                search_input = self.page.locator("input[placeholder='Search this list...']")
                self.log_helper.log(self.logger, 'info', "Found search input field")
                
                search_input.fill("--")
                self.log_helper.log(self.logger, 'info', "Filled search input with '--'")
                
                search_input.press("Enter")
                self.log_helper.log(self.logger, 'info', "Pressed Enter")
                
                self.page.wait_for_timeout(1000)  # Wait for search to complete
                self.log_helper.log(self.logger, 'info', "Waited for search to complete")
                
                # Wait for the status bar to be visible
                status_bar = self.page.locator('span.countSortedByFilteredBy[role="status"]').first
                if status_bar:
                    self.log_helper.log(self.logger, 'info', "Found status bar element")
                    status_bar.wait_for(state='visible', timeout=5000)
                    status_text = status_bar.text_content().strip()
                    self.log_helper.log(self.logger, 'info', f"Status bar text: '{status_text}'")
                    
                    import re
                    match = re.search(r'(\d+\+?) items?', status_text)
                    if match:
                        num_items_str = match.group(1)
                        if num_items_str.endswith('+'):
                            num_items = int(num_items_str[:-1])
                        else:
                            num_items = int(num_items_str)
                        
                        self.log_helper.log(self.logger, 'info', f"Found {num_items_str} items")
                        
                        if num_items == 0:
                            self.log_helper.log(self.logger, 'info', "Successfully cleared search (0 items found)")
                            self.log_helper.dedent()
                            return True
                        else:
                            self.log_helper.log(self.logger, 'warning', f"Attempt {attempt}: Found {num_items_str} items, expected 0")
                    else:
                        self.log_helper.log(self.logger, 'warning', f"Attempt {attempt}: Could not parse number of items from status bar: '{status_text}'")
                else:
                    self.log_helper.log(self.logger, 'warning', f"Attempt {attempt}: Status bar element not found")
                
                # If we get here, the attempt failed
                if attempt < max_attempts:
                    self.log_helper.log(self.logger, 'info', f"Retrying in 1 second...")
                    self.page.wait_for_timeout(1000)
                attempt += 1
                
            except Exception as e:
                self.log_helper.log(self.logger, 'error', f"Attempt {attempt} failed with error: {str(e)}")
                if attempt < max_attempts:
                    self.log_helper.log(self.logger, 'info', f"Retrying in 1 second...")
                    self.page.wait_for_timeout(1000)
                attempt += 1
        
        # If we get here, all attempts failed
        self.log_helper.log(self.logger, 'error', f"Failed to clear search after {max_attempts} attempts")
        # Call navigate_to_salesforce and refresh_page before exiting
        self.log_helper.log(self.logger, 'info', "Navigating to Salesforce base URL and refreshing page after failed clear_search attempts.")
        self.navigate_to_salesforce()
        self.refresh_page()
        if not self.navigate_to_accounts_list_page():
            self.log_helper.log(self.logger, 'error', "Failed to navigate to accounts list page after failed clear_search attempts.")
            self.log_helper.dedent()
            sys.exit(1)
        self.log_helper.dedent()

    def deprecated_get_account_names(self) -> List[str]:
        """
        Get the names of all accounts in the current search results.
        
        Returns:
            List[str]: List of account names
        """
        self.log_helper.indent()
        try:
            logging.info(f"INFO: get_account_names")
            # Wait for the table to be visible
            table = self.page.wait_for_selector('table.slds-table', timeout=10000)
            if not table:
                self.log_helper.log(self.logger, 'error', "Search results table not found")
                self.log_helper.dedent()
                return []
            
            # Get all account names from the table
            account_elements = self.page.locator('table.slds-table tbody tr td:nth-child(2) a').all()
            self.log_helper.log(self.logger, 'info', f"INFO: ***account_elements = {account_elements}")
            if not account_elements:
                self.log_helper.log(self.logger, 'info', "+++No account names found in search results")
                self.log_helper.dedent()
                return []
            
            account_names = []
            for element in account_elements:
                try:
                    name = element.text_content().strip()
                    if name:
                        account_names.append(name)
                except Exception as e:
                    self.log_helper.log(self.logger, 'warning', f"Error getting account name: {str(e)}")
                    continue
                
            self.log_helper.log(self.logger, 'info', f"Found {len(account_names)} account names in search results")
            self.log_helper.dedent()
            return account_names
            
        except Exception as e:
            self.log_helper.log(self.logger, 'error', f"Error getting account names: {str(e)}")
            self.log_helper.dedent()
            return []

    def account_exists(self, account_name: str, view_name: str = "All Accounts") -> bool:
        """Check if an account exists with the exact name.
        
        Args:
            account_name: The name of the account to check
            view_name: The name of the list view to use (default: "All Accounts")
            
        Returns:
            bool: True if the account exists, False otherwise
        """
        self.log_helper.log(self.logger, 'info', f"Checking if account exists: {account_name} in view: {view_name}")
        
        self.log_helper.indent()
        try:
            # Navigate to the list view
            if not self._navigate_to_accounts_list_view_url(view_name):
                self.log_helper.log(self.logger, 'error', "Failed to navigate to list view")
                self.log_helper.dedent()
                return False
            
            # Wait for the search input to be visible
            self.log_helper.log(self.logger, 'info', "Waiting for search input...")
            search_input = self.page.wait_for_selector('input[placeholder="Search this list..."]', timeout=20000)
            if not search_input:
                self.log_helper.log(self.logger, 'error', "Search input not found")
                self._take_screenshot("search-input-not-found")
                self.log_helper.dedent()
                return False
            
            # Ensure the search input is visible and clickable
            search_input.scroll_into_view_if_needed()
            self.page.wait_for_timeout(500)  # Short wait for scroll to complete
            
            # Click the search input to ensure it's focused
            search_input.click()
            self.page.wait_for_timeout(500)  # Short wait for focus
            
            # Clear and fill the search input
            search_input.fill("")
            self.page.wait_for_timeout(500)  # Short wait for clear
            search_input.fill(account_name)
            self.page.wait_for_timeout(500)  # Short wait for fill
            
            # Verify the text was entered correctly
            actual_text = search_input.input_value()
            if actual_text != account_name:
                self.log_helper.log(self.logger, 'error', f"Search text mismatch. Expected: {account_name}, Got: {actual_text}")
                self._take_screenshot("search-text-mismatch")
                self.log_helper.dedent()
                return False
            
            # Press Enter and wait for results
            self.page.keyboard.press("Enter")
            
            # Wait for search results
            self.log_helper.log(self.logger, 'info', "Waiting for search results...")
            try:
                # Wait for the loading spinner to disappear
                self.page.wait_for_selector('.slds-spinner_container', state='hidden', timeout=5000)
                self.log_helper.log(self.logger, 'info', "Loading spinner disappeared")
                
                # Wait a moment for results to appear
                self.page.wait_for_timeout(1000)  # Reduced wait time
                
                # Check for the exact account name
                account_link = self.page.locator(f'a[title="{account_name}"]').first
                if account_link and account_link.is_visible():
                    self.log_helper.log(self.logger, 'info', f"Account exists: {account_name}")
                    self.log_helper.dedent()
                    return True
                
                self.log_helper.log(self.logger, 'info', f"Account does not exist: {account_name}")
                self.log_helper.dedent()
                return False
                
            except Exception as e:
                self.log_helper.log(self.logger, 'error', f"Error waiting for search results: {str(e)}")
                self.log_helper.dedent()
                return False
            
        except Exception as e:
            self.log_helper.log(self.logger, 'error', f"Error checking if account exists: {str(e)}")
            self.log_helper.dedent()
            return False

    def click_account_name(self, account_name: str) -> bool:
        """Click on the account name in the search results."""
        self.log_helper.indent()
        self.log_helper.start_timing()
        try:
            self.log_helper.log(self.logger, 'info', f"Clicking account name: {account_name}")
            # Try the most specific and reliable selectors first
            selectors = [
                f'a[title="{account_name}"]',  # Most specific
                f'a[data-refid="recordId"][data-special-link="true"][title="{account_name}"]',
                f'td:first-child a[title="{account_name}"]',
                f'table[role="grid"] tr:first-child td:first-child a',
                f'table[role="grid"] tr:first-child a[data-refid="recordLink"]'
            ]
            
            for selector in selectors:
                try:
                    account_link = self.page.wait_for_selector(selector, timeout=2000)
                    if account_link and account_link.is_visible():
                        # Scroll and click in one operation
                        account_link.scroll_into_view_if_needed()
                        account_link.click()
                        
                        # Wait for navigation with a shorter timeout
                        # self.page.wait_for_load_state("networkidle", timeout=5000)
                        
                        # Verify we're on the account view page and extract ID
                        current_url = self.page.url
                        if '/view' in current_url:
                            account_id_match = re.search(r'/Account/([^/]+)/view', current_url)
                            if account_id_match:
                                self.current_account_id = account_id_match.group(1)
                                duration = self.log_helper.end_timing()
                                self.log_helper.log(self.logger, 'info', f"Successfully clicked account name in {duration}")
                                self.log_helper.dedent()
                                return True
                except Exception:
                    continue
            
            duration = self.log_helper.end_timing()
            self.log_helper.log(self.logger, 'error', f"Could not find or click account link for: {account_name} after {duration}")
            self.log_helper.dedent()
            return False
            
        except Exception as e:
            duration = self.log_helper.end_timing()
            self.log_helper.log(self.logger, 'error', f"Error clicking account name after {duration}: {str(e)}")
            self.log_helper.dedent()
            return False

    def click_save_button(self) -> bool:
        """Click the Save button."""
        # Save the account
        self.log_helper.log(self.logger, 'info', "Clicking Save button...")
        self.log_helper.indent()
        try:
            # First try to find and click the visible Save button directly
            save_button = self.page.locator('button:has-text("Save")').first
            if save_button and save_button.is_visible():
                save_button.scroll_into_view_if_needed()
                self.page.wait_for_timeout(500)
                save_button.click()
                self.log_helper.log(self.logger, 'info', "Successfully clicked visible Save button")
                self.log_helper.dedent()
                return True

            # If no visible Save button found, try finding it through all buttons
            save_buttons = self.page.locator('button').all()
            for idx, button in enumerate(save_buttons):
                try:
                    text = button.text_content()
                    visible = button.is_visible()
                    enabled = button.is_enabled()
                    if text and text.strip() == "Save" and enabled:
                        if visible:
                            button.scroll_into_view_if_needed()
                            self.page.wait_for_timeout(500)
                            button.click()
                            self.log_helper.log(self.logger, 'info', "Successfully clicked visible Save button")
                            self.log_helper.dedent()
                            return True
                except Exception:
                    continue

            raise Exception("Could not find an enabled Save button to click")
        except Exception as e:
            self.log_helper.log(self.logger, 'error', f"Error clicking Save button: {str(e)}")
            self.page.screenshot(path="save-button-error.png")
            self.log_helper.log(self.logger, 'info', "Error screenshot saved as save-button-error.png")
            self.log_helper.dedent()
            raise Exception("Could not click Save button")
            

    def click_next_button(self) -> bool:    
        """Click the Next button."""
        
        self.log_helper.log(self.logger, 'info', "Clicking Next button...")
        next_button = self.page.wait_for_selector('button:has-text("Next")', timeout=4000)
        if next_button:
            # Use JavaScript to click the Next button
            self.page.evaluate("""() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const nextButton = buttons.find(button => button.textContent.trim() === 'Next');
                if (nextButton) {
                    nextButton.click();
                }
            }""")
        else:
            raise Exception("Next button not found")
            
    def get_full_name(self, first_name: str, last_name: str, middle_name: Optional[str] = None) -> str:
        """Get the full name including middle name if available.
        
        Args:
            first_name: First name
            last_name: Last name
            middle_name: Optional middle name
            
        Returns:
            str: Full name in the format "FirstName MiddleName LastName" or "FirstName LastName"
        """
        if middle_name:
            return f"{first_name} {middle_name} {last_name}"
        return f"{first_name} {last_name}"

    def create_new_account(self, first_name: str, last_name: str, 
                          middle_name: Optional[str] = None, 
                          account_info: Optional[Dict[str, str]] = None) -> bool:
        """Create a new account with the given information."""
        self.log_helper.start_timing()
        self.log_helper.indent()
        try:
            full_name = self.get_full_name(first_name, last_name, middle_name)
            self.log_helper.log(self.logger, 'info', f"Creating new account for: {full_name}")
            
            # Click New button
            self.log_helper.log(self.logger, 'info', "Step 1: Attempting to click New button...")
            if not self._click_element('ACCOUNT', 'new_button'):
                self.log_helper.log(self.logger, 'error', "Could not find or click New button")
                self._take_screenshot("new-button-error")
                sys.exit(1)
            self.log_helper.log(self.logger, 'info', "Successfully clicked New button")
                
            # Select Client radio button
            self.log_helper.log(self.logger, 'info', "Step 2: Attempting to select Client radio button...")
            # Log the page content for debugging
            # self.logger.info("Current page content:")
            # self.logger.info(self.page.content())
            
            # Click Next button
            self.log_helper.log(self.logger, 'info', "Step 3: Attempting to click Next button...")
            self.click_next_button()
            self.log_helper.log(self.logger, 'info', "Successfully clicked Next button")
                
            # Fill name fields
            self.log_helper.log(self.logger, 'info', "Step 4: Attempting to fill First Name field...")
            if not self._fill_input('FORM', 'first_name', first_name):
                self.log_helper.log(self.logger, 'error', "Could not fill First Name field")
                self._take_screenshot("first-name-error")
                sys.exit(1)
            self.log_helper.log(self.logger, 'info', f"Successfully filled First Name with: {first_name}")
                
            self.log_helper.log(self.logger, 'info', "Step 5: Attempting to fill Last Name field...")
            if not self._fill_input('FORM', 'last_name', last_name):
                self.log_helper.log(self.logger, 'error', "Could not fill Last Name field")
                self._take_screenshot("last-name-error")
                sys.exit(1)
            self.log_helper.log(self.logger, 'info', f"Successfully filled Last Name with: {last_name}")
                
            if middle_name:
                self.log_helper.log(self.logger, 'info', "Step 6: Attempting to fill Middle Name field...")
                if not self._fill_input('FORM', 'middle_name', middle_name):
                    self.log_helper.log(self.logger, 'error', "Could not fill Middle Name field")
                    self._take_screenshot("middle-name-error")
                    sys.exit(1)
                self.log_helper.log(self.logger, 'info', f"Successfully filled Middle Name with: {middle_name}")
                
            # Fill additional account info if provided
            if account_info and 'phone' in account_info:
                self.log_helper.log(self.logger, 'info', "Step 7: Attempting to fill Phone field...")
                if not self._fill_input('FORM', 'phone_field', account_info['phone']):
                    self.log_helper.log(self.logger, 'error', "Could not fill Phone field")
                    self._take_screenshot("phone-field-error")
                    sys.exit(1)
                self.log_helper.log(self.logger, 'info', f"Successfully filled Phone with: {account_info['phone']}")
                    
            # Click Save button
            self.log_helper.log(self.logger, 'info', "Step 8: Attempting to click Save button...")
            # if not self._click_element('ACCOUNT', 'save_button'):
            #     self.logger.error("Could not find or click Save button")
            #     self._take_screenshot("save-button-error")
            #     sys.exit(1)
            # self.logger.info("Successfully clicked Save button")
            self.click_save_button()
                
            # Wait for save confirmation with increased timeout
            self.log_helper.log(self.logger, 'info', "Step 9: Waiting for save confirmation...")
            try:
                # Try multiple confirmation methods
                confirmation_found = False
                max_attempts = 3
                attempt = 1
                
                while attempt <= max_attempts and not confirmation_found:
                    self.log_helper.log(self.logger, 'info', f"Save confirmation attempt {attempt}/{max_attempts}")
                    
                    # Method 1: Check for toast message first (most reliable)
                    self.log_helper.log(self.logger, 'info', f"Method 1: Check for toast message")
                    try:
                        # Log all toast-related elements for debugging
                        toast_elements = self.page.query_selector_all('div[class*="notify"], div[class*="toast"], div[role="alert"]')
                        self.log_helper.log(self.logger, 'info', f"Found {len(toast_elements)} potential toast elements")
                        for idx, el in enumerate(toast_elements):
                            try:
                                visible = el.is_visible()
                                text = el.text_content()
                                classes = el.get_attribute('class')
                                self.log_helper.log(self.logger, 'info', f"Toast element {idx + 1}: visible={visible}, text={text}, classes={classes}")
                            except Exception as e:
                                self.log_helper.log(self.logger, 'info', f"Error inspecting toast element {idx + 1}: {str(e)}")

                        toast = self.page.wait_for_selector('div.slds-notify_toast, div.slds-notify--toast, div[role="alert"]', timeout=20000)
                        if toast and toast.is_visible():
                            toast_text = toast.text_content()
                            self.log_helper.log(self.logger, 'info', f"Found toast message: {toast_text}")
                            if 'success' in toast_text.lower() or 'was created' in toast_text.lower():
                                confirmation_found = True
                    except Exception as e:
                        self.log_helper.log(self.logger, 'info', f"No toast message found: {str(e)}")
                    
                    # Method 2: Check URL change
                    self.log_helper.log(self.logger, 'info', f"Method 2: Check URL change")
                    self.log_helper.log(self.logger, 'info', f"confirmation_found: {confirmation_found}")
                    if not confirmation_found:
                        try:
                            current_url = self.page.url
                            self.log_helper.log(self.logger, 'info', f"Current URL before waiting: {current_url}")
                            # Wait for URL to change to view page
                            self.page.wait_for_url(lambda url: '/view' in url, timeout=20000)
                            new_url = self.page.url
                            self.log_helper.log(self.logger, 'info', f"URL changed to view page: {new_url}")
                            confirmation_found = True
                            
                            # Wait for page load after URL change with shorter timeouts
                            self.log_helper.log(self.logger, 'info', "Waiting for page load after URL change...")
                            try:
                                self.page.wait_for_load_state('domcontentloaded', timeout=10000)
                                self.log_helper.log(self.logger, 'info', "DOM content loaded")
                            except Exception as e:
                                self.log_helper.log(self.logger, 'info', f"DOM content load timeout: {str(e)}")
                                
                            try:
                                self.page.wait_for_load_state('networkidle', timeout=10000)
                                self.log_helper.log(self.logger, 'info', "Network is idle")
                            except Exception as e:
                                self.log_helper.log(self.logger, 'info', f"Network idle timeout: {str(e)}")
                                
                        except Exception as e:
                            self.log_helper.log(self.logger, 'info', f"URL did not change: {str(e)}")
                    
                    # Method 3: Check for account name
                    self.log_helper.log(self.logger, 'info', f"Method 3: Check for account name")
                    if not confirmation_found:
                        account_name = f"{first_name} {middle_name} {last_name}" if middle_name else f"{first_name} {last_name}"
                        name_selectors = [
                            f"h1:has-text('{account_name}')",
                            f"span:has-text('{account_name}')",
                            f"div:has-text('{account_name}')",
                            f"text={account_name}"
                        ]
                        for selector in name_selectors:
                            try:
                                elements = self.page.query_selector_all(selector)
                                self.log_helper.log(self.logger, 'info', f"Found {len(elements)} elements matching selector: {selector}")
                                for idx, el in enumerate(elements):
                                    try:
                                        visible = el.is_visible()
                                        text = el.text_content()
                                        self.log_helper.log(self.logger, 'info', f"Element {idx + 1} for selector {selector}: visible={visible}, text={text}")
                                        if visible:
                                            self.log_helper.log(self.logger, 'info', f"Account name found with selector: {selector}")
                                            confirmation_found = True
                                            break
                                    except Exception as e:
                                        self.log_helper.log(self.logger, 'info', f"Error inspecting element {idx + 1} for selector {selector}: {str(e)}")
                                    if confirmation_found:
                                        break
                            except Exception as e:
                                self.log_helper.log(self.logger, 'info', f"Selector {selector} failed: {str(e)}")
                    
                    # Method 4: Check for loading spinner to disappear
                    if not confirmation_found:
                        self.log_helper.log(self.logger, 'info', f"Method 4: Check for loading spinner")
                        try:
                            self.page.wait_for_selector('.slds-spinner_container', state='hidden', timeout=10000)
                            self.log_helper.log(self.logger, 'info', "Loading spinner disappeared")
                            # If spinner disappeared and we're on a view page, consider it a success
                            if '/view' in self.page.url:
                                confirmation_found = True
                        except Exception as e:
                            self.log_helper.log(self.logger, 'info', f"No loading spinner found or already disappeared: {str(e)}")
                    
                    if not confirmation_found and attempt < max_attempts:
                        self.log_helper.log(self.logger, 'info', f"Save confirmation not found, retrying in 2 seconds...")
                        self.page.wait_for_timeout(2000)
                        attempt += 1
                    elif not confirmation_found and attempt == max_attempts:
                        # Take a screenshot of the current state
                        self._take_screenshot("save-confirmation-not-found")
                        # Log the page HTML for debugging
                        page_content = self.page.content()
                        self.log_helper.log(self.logger, 'info', f"Current page HTML: {page_content}")
                        raise Exception("Could not confirm save operation completed after all attempts")
                
                self.log_helper.log(self.logger, 'info', "Save confirmation received")
                
                # Verify account creation
                self.log_helper.log(self.logger, 'info', "Step 10: Verifying account creation...")
                if not self._verify_account_creation(first_name, last_name, middle_name):
                    self.log_helper.log(self.logger, 'error', "Could not verify account creation")
                    self._take_screenshot("account-verification-error")
                    self.log_helper.dedent()
                    return False
                self.log_helper.log(self.logger, 'info', "Successfully verified account creation")
                
                self.log_helper.log(self.logger, 'info', "Successfully created new account")
                self.log_helper.dedent()
                self.log_helper.log_timing(self.logger, f"create_new_account for: {first_name} {last_name}")
                return True
                
            except Exception as e:
                self.log_helper.log(self.logger, 'error', f"Error during save confirmation: {str(e)}")
                self._take_screenshot("save-confirmation-error")
                self.log_helper.dedent()
                return False
            
        except Exception as e:
            self.log_helper.log(self.logger, 'error', f"Error creating new account: {str(e)}")
            self.log_helper.log_timing(self.logger, f"create_new_account (error) for: {first_name} {last_name}")
            self._take_screenshot("account-creation-error")
            sys.exit(1)
            
    def _get_status_message(self) -> Optional[str]:
        """Get the status message from the page."""
        try:
            status_element = self.page.locator('span.countSortedByFilteredBy, span.slds-text-body_small, div.slds-text-body_small, span[class*="count"]').first
            if status_element:
                return status_element.text_content()
        except Exception:
            pass
        return None
        
    def _extract_account_id(self, url: str) -> Optional[str]:
        """Extract the account ID from the URL."""
        match = re.search(r'/Account/([^/]+)/view', url)
        return match.group(1) if match else None
        
    def _verify_account_creation(self, first_name: str, last_name: str, 
                               middle_name: Optional[str] = None) -> bool:
        """Verify that the account was created successfully."""
        self.log_helper.indent()
        try:
            # # Wait for the page to fully load
            # self.page.wait_for_load_state('networkidle')
            # self.page.wait_for_timeout(5000)  # Additional wait for list to refresh
            
            # Verify URL contains /view and extract account ID
            current_url = self.page.url
            self.log_helper.log(self.logger, 'info', f"Current URL: {current_url}")
            if '/view' not in current_url:
                raise Exception(f"Not on account view page. Current URL: {current_url}")
            
            # Extract account ID from URL
            account_id_match = re.search(r'/Account/(\w+)/view', current_url)
            if not account_id_match:
                raise Exception(f"Could not extract account ID from URL: {current_url}")
            
            account_id = account_id_match.group(1)
            self.log_helper.log(self.logger, 'info', f"Extracted account ID from URL: {account_id}")
            
            # If this is after account creation, store the ID
            self.current_account_id = account_id
            self.log_helper.log(self.logger, 'info', f"Stored created account ID: {account_id}")
            
            # Verify the account name is visible on the page
            account_name = f"{first_name} {middle_name} {last_name}" if middle_name else f"{first_name} {last_name}"
            name_found = False
            name_selectors = [
                f"h1:has-text('{account_name}')",
                f"span:has-text('{account_name}')",
                f"div:has-text('{account_name}')",
                f"text={account_name}"
            ]
            
            for selector in name_selectors:
                try:
                    if self.page.locator(selector).first.is_visible():
                        self.log_helper.log(self.logger, 'info', f"Account name '{account_name}' is visible on the page (selector: {selector})")
                        name_found = True
                        break
                except Exception as e:
                    self.log_helper.log(self.logger, 'info', f"Account name selector {selector} failed: {str(e)}")
                    
            if not name_found:
                self.log_helper.log(self.logger, 'error', f"Could not find account name '{account_name}' on the page after Save.")
                self.page.screenshot(path="account-name-not-found.png")
                self.log_helper.dedent()
                return False
                
            self.log_helper.log(self.logger, 'info', "Successfully verified account creation")
            self.log_helper.dedent()
            return True
            
        except Exception as e:
            self.log_helper.log(self.logger, 'error', f"Error verifying account creation: {str(e)}")
            self.page.screenshot(path="account-creation-verification-error.png")
            self.log_helper.dedent()
            return False
            

    def navigate_to_account_by_id(self, account_id: str) -> bool:
        """Navigate to an account using its ID.
        
        Args:
            account_id: The Salesforce account ID to navigate to
            
        Returns:
            bool: True if navigation was successful, False otherwise
        """
        self.log_helper.log(self.logger, 'info', f"Navigating to account with ID: {account_id}")
        
        self.log_helper.indent()
        try:
            # Construct the URL for the account
            url = f"{SALESFORCE_URL}/lightning/r/Account/{account_id}/view"
            self.log_helper.log(self.logger, 'info', f"Navigating to URL: {url}")
            
            # Navigate to the URL
            self.page.goto(url)
            # self.page.wait_for_load_state('networkidle')
            
            # Verify we're on the correct account page
            current_url = self.page.url
            if f"/Account/{account_id}/view" not in current_url:
                self.log_helper.log(self.logger, 'error', f"Navigation failed. Expected URL containing /Account/{account_id}/view, got: {current_url}")
                self._take_screenshot("account-navigation-error")
                sys.exit(1)
                
            # Store the account ID
            self.current_account_id = account_id
            self.log_helper.log(self.logger, 'info', f"Successfully navigated to account {account_id}")
            self.log_helper.dedent()
            return True
            
        except Exception as e:
            self.log_helper.log(self.logger, 'error', f"Error navigating to account {account_id}: {str(e)}")
            self._take_screenshot("account-navigation-error")
            sys.exit(1)
            
    def navigate_back_to_account_page(self):
        """Navigate back to the current account page."""
        self.log_helper.log(self.logger, 'info', "Navigating back to account page...")
        if not self.current_account_id:
            self.log_helper.log(self.logger, 'error', "No current account ID available")
            self._take_screenshot("account-navigation-error")
            sys.exit(1)
            
        self.log_helper.indent()
        try:
            url = f"{SALESFORCE_URL}/lightning/r/Account/{self.current_account_id}/view"
            self.log_helper.log(self.logger, 'info', f"Navigating to URL: {url}")
            self.page.goto(url)
            # self.page.wait_for_load_state('networkidle')
            # checking url 
            current_url = self.page.url
            if f"/Account/{self.current_account_id}/view" not in current_url:
                self.log_helper.log(self.logger, 'error', f"Navigation failed. Expected URL containing /Account/{self.current_account_id}/view, got: {current_url}")
                self._take_screenshot("account-navigation-error")
                sys.exit(1)
            self.log_helper.log(self.logger, 'info', "Back on account page")
        except Exception as e:
            self.log_helper.log(self.logger, 'error', f"Error navigating back to account page: {str(e)}")
            self._take_screenshot("account-navigation-error")
            sys.exit(1) 

    def navigate_to_account_files_and_get_number_of_files(self, account_id: str, scroll_to_bottom_of_account_files: bool = False) -> Union[int, str]:
        """
        Navigate to the Files related list for the given account_id.
        Returns either an integer or a string (e.g. "50+") representing the number of files.
        """
        self.log_helper.log(self.logger, 'info', f"****navigate_to_files_and_get_number_of_account_files")
        self.log_helper.log(self.logger, 'info', f"****Attempting to navigate to Files...")
        self.log_helper.log(self.logger, 'info', f"Current URL: {self.page.url}")
        
        try:
            # First ensure we're on the account view page
            if not self.ensure_account_view_page(account_id):
                self.log_helper.log(self.logger, 'error', "Failed to ensure account view page")
                self.log_helper.dedent()
                return -1

            # Navigate to files section
            num_files = self.navigate_to_account_files_click_on_files_card_to_facilitate_file_operation()
            
            # Get file count using FileManager
            file_manager_instance = file_manager.SalesforceFileManager(self.page)
            self.log_helper.log(self.logger, 'info', f"Initial number of files: {num_files}")
            
            # If we have a string count like "50+", handle it appropriately
            if isinstance(num_files, str) and '+' in str(num_files):
                if not scroll_to_bottom_of_account_files:
                    self.log_helper.log(self.logger, 'info', f"Found '{num_files}' count, not scrolling to load all files...")
                    return num_files
                
                self.log_helper.log(self.logger, 'info', f"Found '{num_files}' count, scrolling to load all files...")
                actual_count = file_manager_instance.scroll_to_bottom_of_page()
                if isinstance(actual_count, (int, str)) and actual_count != 0:
                    self.log_helper.log(self.logger, 'info', f"Final number of files after scrolling: {actual_count}")
                    self.log_helper.dedent()
                    return actual_count
                return num_files
            elif isinstance(num_files, int) and num_files > 0:
                self.log_helper.dedent()
                return num_files
            
            self.log_helper.dedent()
            return num_files
            
        except Exception as e:
            self.log_helper.log(self.logger, 'error', f"Error navigating to Files: {str(e)}")
            self.log_helper.dedent()
            return -1

    def get_salesforce_account_file_names(self, account_id: str) -> List[str]:
        """
        Get all file names associated with an account.
        
        Args:
            account_id: The Salesforce account ID
        
        Returns:
            List[str]: List of file names found in the account
        """
        self.log_helper.log(self.logger, 'info', f"Getting all file names for account {account_id}")
        
        self.log_helper.indent()
        try:
            # First ensure we're on the account view page
            if not self.ensure_account_view_page(account_id):
                self.log_helper.log(self.logger, 'error', "Failed to ensure account view page")
                self.log_helper.dedent()
                return []
            
            # Navigate to files section
            self.log_helper.log(self.logger, 'info', "Navigating to files section")
            self.log_helper.log(self.logger, 'info', f"account_id: {account_id}")
            num_files = self.navigate_to_account_files_and_get_number_of_files(account_id, scroll_to_bottom_of_account_files=True)
    
            # Use FileManager to get file names
            file_manager_instance = file_manager.SalesforceFileManager(self.page)
            self.log_helper.dedent()
            
            # Check if we have files (either a positive integer or a string like "50+")
            if (isinstance(num_files, int) and num_files > 0) or (isinstance(num_files, str) and '+' in str(num_files)):
                return file_manager_instance.get_all_file_names()
            else:
                return []
            
        except Exception as e:
            self.log_helper.log(self.logger, 'error', f"Error getting file names: {str(e)}")
            self.log_helper.dedent()
            return []

    def get_default_condition(self):
        """Get the default condition for filtering accounts."""
        def condition(account):
            return self.account_has_files(account['id'])
        return condition

    def _get_accounts_base(self, view_name: str = "All Clients") -> List[Dict[str, str]]:
        """
        Get all accounts from the current list view.
        
        Args:
            view_name: Name of the list view to select
            
        Returns:
            List[Dict[str, str]]: List of account dictionaries with 'name' and 'id' keys
        """
        self.log_helper.indent()
        try:
            self.log_helper.log(self.logger, 'debug', f"Getting accounts base: {view_name}")
            # Navigate to accounts page
            self.log_helper.log(self.logger, 'debug', f"Navigating to Accounts page: {SALESFORCE_URL}/lightning/o/Account/list?filterName=__Recent")
            if not self.navigate_to_accounts_list_page():
                self.log_helper.log(self.logger, 'error', "Failed to navigate to Accounts page")
                self.log_helper.dedent()
                return []

            # Select the specified list view
            self.log_helper.log(self.logger, 'debug', f"Selecting list view: {view_name}")
            if not self._navigate_to_accounts_list_view_url(view_name):
                self.log_helper.dedent()
                return []

            # Wait for table to be visible
            self.log_helper.log(self.logger, 'debug', f"Waiting for table to be visible")
            try:
                table = self.page.wait_for_selector('table[role="grid"]', timeout=10000)
                if not table:
                    self.log_helper.log(self.logger, 'error', "Table element not found")
                    self.log_helper.dedent()
                    return []
                self.log_helper.log(self.logger, 'debug', "Table element found")
            except Exception as e:
                self.log_helper.log(self.logger, 'error', f"Table not found after 10 seconds: {str(e)}")
                self.log_helper.dedent()
                return []

            # Wait for table to be populated and visible
            self.log_helper.log(self.logger, 'debug', f"Waiting for table to be populated and visible")
            try:
                # Wait for the table to be fully loaded
                self.log_helper.log(self.logger, 'debug', "Waiting for network to be idle")
                self.page.wait_for_load_state('networkidle', timeout=10000)
                
                # Wait for the loading spinner to disappear (if present)
                try:
                    self.log_helper.log(self.logger, 'debug', "Waiting for loading spinner to disappear")
                    self.page.wait_for_selector('.slds-spinner_container', state='hidden', timeout=5000)
                except:
                    self.log_helper.log(self.logger, 'debug', "No loading spinner found")
                
                # Force the table to be visible by evaluating JavaScript
                self.log_helper.log(self.logger, 'debug', "Forcing table visibility with JavaScript")
                self.page.evaluate("""
                    () => {
                        const table = document.querySelector('table[role="grid"]');
                        if (table) {
                            console.log('Found table element');
                            table.style.visibility = 'visible';
                            table.style.display = 'table';
                            const rows = table.querySelectorAll('tr');
                            console.log('Found ' + rows.length + ' rows');
                            rows.forEach(row => {
                                row.style.visibility = 'visible';
                                row.style.display = 'table-row';
                            });
                            return rows.length;
                        }
                        return 0;
                    }
                """)
                
                # Get all rows
                self.log_helper.log(self.logger, 'debug', "Getting all table rows")
                rows = self.page.locator('table[role="grid"] tr').all()
                if not rows:
                    self.log_helper.log(self.logger, 'error', "No rows found in table")
                    self.log_helper.dedent()
                    return []
                
                self.log_helper.log(self.logger, 'debug', f"Found {len(rows)} rows in table")
                
                # Additional wait to ensure table is fully rendered
                self.log_helper.log(self.logger, 'debug', "Waiting for table to stabilize")
                self.page.wait_for_timeout(2000)
                
            except Exception as e:
                self.log_helper.log(self.logger, 'error', f"Error waiting for table rows: {str(e)}")
                self.log_helper.dedent()
                return []

            accounts = []
            
            for idx, row in enumerate(rows):
                try:
                    # Log the outer HTML of the row for debugging
                    try:
                        outer_html = row.evaluate('el => el.outerHTML')
                        # self.logger.debug(f"Row {idx} outer HTML: {outer_html}")
                        for handler in logging.getLogger().handlers:
                            handler.flush()
                    except Exception as e:
                        self.log_helper.log(self.logger, 'warning', f"Could not get outer HTML for row {idx}: {e}")
                    # Skip header rows
                    first_cell = row.locator('th, td').nth(0)
                    if first_cell.count() > 0:
                        tag = first_cell.evaluate('el => el.tagName.toLowerCase()')
                        scope = first_cell.get_attribute('scope')
                        if tag == 'th' and (scope == 'col' or (first_cell.get_attribute('role') == 'cell' and scope == 'col')):
                            continue
                    # Try to get account name and ID from <th scope="row"> a
                    name_cell = row.locator('th[scope="row"] a')
                    if name_cell.count() == 0:
                        # Fallback to <td:first-child a>
                        name_cell = row.locator('td:first-child a')
                    if name_cell.count() == 0:
                        continue
                    try:
                        name = name_cell.nth(0).text_content(timeout=10000).strip()
                        href = name_cell.nth(0).get_attribute('href')
                        # ***Account name: Irasis Abislaiman-Saade href: /lightning/r/001Dn00000VskmFIAR/view

                        account_id = href.split('/')[-2] if href else None
                        if name and account_id:
                            accounts.append({
                                'name': name,
                                'id': account_id
                            })
                        self.log_helper.log(self.logger, 'debug', f"***Account name: {name} found")
                        self.log_helper.log(self.logger, 'debug', f"***Account id: {account_id} found")
                       
                    except Exception as e:
                        self.log_helper.log(self.logger, 'warning', f"Error getting text content for row: {str(e)}")
                        continue
                except Exception as e:
                    self.log_helper.log(self.logger, 'warning', f"Error processing account row: {str(e)}")
                    continue
            
            self.log_helper.dedent()
            return accounts
            
        except Exception as e:
            self.log_helper.log(self.logger, 'error', f"Error getting accounts: {str(e)}")
            self.log_helper.dedent()
            return []

    def get_accounts_matching_condition(
        self,
        max_number: int = 10,
        condition: Callable[[Dict[str, str]], bool] = None,
        view_name: str = "All Clients"
    ) -> List[Dict[str, str]]:
        """
        Keep iterating through all accounts until max_number accounts that match a condition.
        By default, returns accounts that have more than 0 files.
        """
        accounts = []
        all_accounts = self._get_accounts_base(view_name=view_name)
        processed_accounts = []
        the_condition = condition if condition is not None else self.get_default_condition()
        for account in all_accounts:
            self.log_helper.log(self.logger, 'debug', f"Processing account: {account['name']}")
            files_count = self.navigate_to_account_files_and_get_number_of_files(account['id'], scroll_to_bottom_of_account_files=True)
            account['files_count'] = files_count
            processed_accounts.append(account)
            if the_condition(account):
                accounts.append(account)
                if len(accounts) >= max_number:
                    break
        self.log_helper.log(self.logger, 'info', f"Total accounts processed: {len(processed_accounts)}")
        for acc in processed_accounts:
            self.log_helper.log(self.logger, 'info', f"Processed account: Name={acc['name']}, ID={acc['id']}, Files={acc['files_count']}")
        self.log_helper.dedent()
        return accounts

    def verify_account_page_url(self) -> tuple[bool, Optional[str]]:
        """Verify that the current URL is a valid account page URL and extract the account ID.
        
        Returns:
            tuple[bool, Optional[str]]: A tuple containing:
                - bool: True if the URL is valid, False otherwise
                - Optional[str]: The account ID if found, None otherwise
        """
        self.log_helper.indent()
        try:
            current_url = self.page.url
            self.log_helper.log(self.logger, 'info', f"Current URL: {current_url}")
            
            # Check if we're on an account page
            if not re.match(r'.*Account/\w+/view.*', current_url):
                self.log_helper.log(self.logger, 'error', f"Not on account page. Current URL: {current_url}")
                self.log_helper.dedent()
                return False, None
            
            # Extract account ID from URL
            account_id_match = re.search(r'/Account/(\w+)/view', current_url)
            if not account_id_match:
                self.log_helper.log(self.logger, 'error', f"Could not extract account ID from URL: {current_url}")
                self.log_helper.dedent()
                return False, None
            
            account_id = account_id_match.group(1)
            self.log_helper.log(self.logger, 'info', f"Extracted account ID from URL: {account_id}")
            self.log_helper.dedent()
            return True, account_id
            
        except Exception as e:
            self.log_helper.log(self.logger, 'error', f"Error verifying account page URL: {str(e)}")
            self.log_helper.dedent()
            return False, None

    def account_has_files(self, account_id: str) -> bool:
        """
        Check if the account has files.
        """
        num_files = self.navigate_to_account_files_and_get_number_of_files(account_id, scroll_to_bottom_of_account_files=False)
        if isinstance(num_files, str):
            # If we have a string like "50+", we know there are files
            self.log_helper.dedent()
            return True
        self.log_helper.dedent()
        return num_files > 0
    
    
    def deprecated_account_has_files(self, account_id: str) -> bool:
        """
        Check if the account has files.
        """
        account_url = f"{SALESFORCE_URL}/lightning/r/{account_id}/view"
        self.log_helper.log(self.logger, 'info', f"Navigating to account view page: {account_url}")
        self.page.goto(account_url)
        # self.page.wait_for_load_state('networkidle', timeout=30000)
        self.log_helper.indent()
        try:
            # Find all matching <a> elements
            files_links = self.page.locator('a.slds-card__header-link.baseCard__header-title-container')
            found = False
            for i in range(files_links.count()):
                a = files_links.nth(i)
                href = a.get_attribute('href')
                outer_html = a.evaluate('el => el.outerHTML')
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
                    self.log_helper.log(self.logger, 'info', f"Account {account_id} Files count: {files_number}")
                    found = True
                    self.log_helper.dedent()
                    return files_number > 0
            if not found:
                self.log_helper.log(self.logger, 'error', f"Files card not found for account {account_id}")
                sys.exit(1)
        except Exception as e:
            self.log_helper.log(self.logger, 'error', f"Could not extract files count for account {account_id}: {e}")
            sys.exit(1)

    def delete_account(self, full_name: str, view_name: str = "Recent") -> bool:
        """
        Delete an account by name.
        Args:
            full_name: Full name of the account to delete
            view_name: Name of the view to search in (default: "Recent")
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        self.log_helper.start_timing()
        self.log_helper.indent()
        try:
            self.log_helper.log(self.logger, 'info', f"Starting delete_account for: {full_name}")
            self.log_helper.log(self.logger, 'info', f"Current URL before any operations: {self.page.url}")
            
            # Search for the account
            self.log_helper.log(self.logger, 'info', f"Step 1: Checking if account exists: {full_name}")
            if not self.account_exists(full_name, view_name=view_name):
                self.log_helper.log(self.logger, 'error', f"Account {full_name} does not exist")
                self.log_helper.dedent()
                return False
                
            # Click on the account name to navigate to it
            self.log_helper.log(self.logger, 'info', f"Step 2: Clicking account name: {full_name}")
            if not self.click_account_name(full_name):
                self.log_helper.log(self.logger, 'error', f"Failed to navigate to account view page for: {full_name}")
                self.log_helper.dedent()
                return False
                
            # Verify we're on the correct account page
            self.log_helper.log(self.logger, 'info', "Step 3: Verifying account page URL")
            is_valid, account_id = self.verify_account_page_url()
            if not is_valid:
                self.log_helper.log(self.logger, 'error', "Not on a valid account page")
                self.log_helper.dedent()
                return False
                
            self.log_helper.log(self.logger, 'info', f"Successfully navigated to account {full_name} with ID {account_id}")
            
            # Wait for page to load completely and stabilize
            self.log_helper.log(self.logger, 'info', "Step 4: Waiting for page to load and stabilize")
            try:
                self.log_helper.log(self.logger, 'info', "Waiting for network to be idle...")
                self.page.wait_for_load_state('networkidle', timeout=10000)
                self.log_helper.log(self.logger, 'info', "Network is idle")
            except Exception as e:
                self.log_helper.log(self.logger, 'warning', f"Network idle timeout, but continuing: {str(e)}")
                
            try:
                self.log_helper.log(self.logger, 'info', "Waiting for DOM content to load...")
                self.page.wait_for_load_state('domcontentloaded', timeout=10000)
                self.log_helper.log(self.logger, 'info', "DOM content loaded")
            except Exception as e:
                self.log_helper.log(self.logger, 'warning', f"DOM content load timeout, but continuing: {str(e)}")
                
            self.log_helper.log(self.logger, 'info', "Waiting additional 2 seconds for page to stabilize...")
            self.page.wait_for_timeout(2000)
            
            # Log the current page state
            self.log_helper.log(self.logger, 'info', f"Current URL after page load: {self.page.url}")
            try:
                page_title = self.page.title()
                self.log_helper.log(self.logger, 'info', f"Page title: {page_title}")
            except Exception as e:
                self.log_helper.log(self.logger, 'warning', f"Could not get page title: {str(e)}")
                
            # Log all buttons on the page for debugging
            try:
                self.log_helper.log(self.logger, 'info', "Logging all buttons on the page...")
                buttons = self.page.query_selector_all('button')
                self.log_helper.log(self.logger, 'info', f"Found {len(buttons)} buttons on the page")
                for idx, btn in enumerate(buttons):
                    try:
                        text = btn.text_content()
                        visible = btn.is_visible()
                        enabled = btn.is_enabled()
                        classes = btn.get_attribute('class')
                        self.log_helper.log(self.logger, 'info', f"Button {idx + 1}:")
                        self.log_helper.log(self.logger, 'info', f"  - Text: {text}")
                        self.log_helper.log(self.logger, 'info', f"  - Visible: {visible}")
                        self.log_helper.log(self.logger, 'info', f"  - Enabled: {enabled}")
                        self.log_helper.log(self.logger, 'info', f"  - Classes: {classes}")
                    except Exception as e:
                        self.log_helper.log(self.logger, 'info', f"Error inspecting button {idx + 1}: {str(e)}")
            except Exception as e:
                self.log_helper.log(self.logger, 'warning', f"Error finding buttons: {str(e)}")
            
            # Step 1: Click the left-panel Delete button (try several selectors and log all candidates)
            delete_selectors = [
                "button[title='Delete']",
                "button:has-text('Delete')",
                "input[value='Delete']",
                "a[title='Delete']",
                "a:has-text('Delete')",
                "button.slds-button.slds-button_neutral[name='Delete']",  # New selector
                "button[class='slds-button slds-button_neutral'][name='Delete']",  # Alternative format
                "button[part='button'][name='Delete']",  # Another alternative
            ]
            delete_btn = None
            self.log_helper.log(self.logger, 'info', "Starting delete button search...")
            for selector in delete_selectors:
                try:
                    self.log_helper.log(self.logger, 'info', f"Trying selector: {selector}")
                    elements = self.page.query_selector_all(selector)
                    self.log_helper.log(self.logger, 'info', f"Found {len(elements)} elements for selector {selector}")
                    for idx, el in enumerate(elements):
                        try:
                            visible = el.is_visible()
                            enabled = el.is_enabled()
                            text = el.text_content()
                            attrs = el.get_attribute('outerHTML')
                            classes = el.get_attribute('class')
                            self.log_helper.log(self.logger, 'info', f"Element {idx + 1} for selector {selector}:")
                            self.log_helper.log(self.logger, 'info', f"  - Visible: {visible}")
                            self.log_helper.log(self.logger, 'info', f"  - Enabled: {enabled}")
                            self.log_helper.log(self.logger, 'info', f"  - Text: {text}")
                            self.log_helper.log(self.logger, 'info', f"  - Classes: {classes}")
                            self.log_helper.log(self.logger, 'info', f"  - HTML: {attrs}")
                            if visible and enabled:
                                delete_btn = el
                                self.log_helper.log(self.logger, 'info', f"Found suitable delete button with selector: {selector}")
                                break
                        except Exception as e:
                            self.log_helper.log(self.logger, 'info', f"Error checking element {idx + 1} for selector {selector}: {str(e)}")
                    if delete_btn:
                        break
                except Exception as e:
                    self.log_helper.log(self.logger, 'info', f"Error finding elements with selector {selector}: {str(e)}")
                    continue

            if not delete_btn:
                self.log_helper.log(self.logger, 'error', "Could not find enabled/visible left-panel Delete button with any selector")
                self.page.screenshot(path="delete-btn-not-found.png")
                self.log_helper.dedent()
                return False

            try:
                self.log_helper.log(self.logger, 'info', "Attempting to click delete button...")
                delete_btn.scroll_into_view_if_needed()
                self.log_helper.log(self.logger, 'info', "Scrolled delete button into view")
                self.page.wait_for_timeout(1000)  # Wait for scroll to complete
                delete_btn.click()
                self.log_helper.log(self.logger, 'info', "Clicked left-panel Delete button.")
            except Exception as e:
                self.log_helper.log(self.logger, 'error', f"Error clicking left-panel Delete button: {str(e)}")
                self.page.screenshot(path="delete-btn-click-error.png")
                self.log_helper.dedent()
                return False

            self.page.wait_for_timeout(1000)

            # Step 2: Wait for the modal and confirm deletion
            self.log_helper.log(self.logger, 'info', "Waiting for delete confirmation modal...")
            try:
                modal = self.page.wait_for_selector('div[role="dialog"]', timeout=5000)
                if modal:
                    modal_text = modal.text_content()
                    self.log_helper.log(self.logger, 'info', f"Delete modal text: {modal_text}")
                else:
                    self.log_helper.log(self.logger, 'error', "Modal element found but is None")
            except Exception as e:
                self.log_helper.log(self.logger, 'error', f"Delete confirmation modal did not appear: {str(e)}")
                self.page.screenshot(path="delete-modal-not-found.png")
                self.log_helper.dedent()
                return False

            # Log all buttons in the modal for debugging
            try:
                modal_buttons = self.page.query_selector_all('div[role="dialog"] button')
                self.log_helper.log(self.logger, 'info', f"Found {len(modal_buttons)} buttons in modal")
                for idx, btn in enumerate(modal_buttons):
                    try:
                        text = btn.text_content()
                        visible = btn.is_visible()
                        enabled = btn.is_enabled()
                        classes = btn.get_attribute('class')
                        self.log_helper.log(self.logger, 'info', f"Modal button {idx + 1}:")
                        self.log_helper.log(self.logger, 'info', f"  - Text: {text}")
                        self.log_helper.log(self.logger, 'info', f"  - Visible: {visible}")
                        self.log_helper.log(self.logger, 'info', f"  - Enabled: {enabled}")
                        self.log_helper.log(self.logger, 'info', f"  - Classes: {classes}")
                    except Exception as e:
                        self.log_helper.log(self.logger, 'info', f"Error inspecting modal button {idx + 1}: {str(e)}")
            except Exception as e:
                self.log_helper.log(self.logger, 'info', f"Error finding modal buttons: {str(e)}")

            # Click the modal's Delete button
            try:
                self.log_helper.log(self.logger, 'info', "Looking for modal delete button...")
                modal_delete_btn = self.page.wait_for_selector('button[title="Delete"]', timeout=5000)
                if not modal_delete_btn:
                    self.log_helper.log(self.logger, 'error', "Could not find modal Delete button")
                    self.page.screenshot(path="modal-delete-btn-not-found.png")
                    self.log_helper.dedent()
                    return False

                self.log_helper.log(self.logger, 'info', "Found modal delete button, attempting to click...")
                modal_delete_btn.scroll_into_view_if_needed()
                self.page.wait_for_timeout(1000)  # Wait for scroll to complete
                modal_delete_btn.click()
                self.log_helper.log(self.logger, 'info', "Clicked modal Delete button.")
            except Exception as e:
                self.log_helper.log(self.logger, 'error', f"Error clicking modal Delete button: {str(e)}")
                self.page.screenshot(path="modal-delete-btn-click-error.png")
                self.log_helper.dedent()
                return False

            # Wait for the modal to close
            try:
                self.log_helper.log(self.logger, 'info', "Waiting for modal to close...")
                self.page.wait_for_selector('div[role="dialog"]', state='detached', timeout=8000)
                self.log_helper.log(self.logger, 'info', "Delete confirmation modal closed.")
            except Exception as e:
                self.log_helper.log(self.logger, 'warning', f"Delete confirmation modal did not close in time: {str(e)}")

            # Wait for deletion confirmation (toast)
            try:
                self.log_helper.log(self.logger, 'info', "Waiting for deletion confirmation toast...")
                toast = self.page.wait_for_selector('div.slds-notify_toast, div.slds-notify--toast', timeout=15000)
                if toast:
                    toast_text = toast.text_content()
                    self.log_helper.log(self.logger, 'info', f"Found toast message: {toast_text}")
                self.log_helper.log(self.logger, 'info', f"Successfully deleted account: {full_name}")
                self.log_helper.dedent()
                self.log_helper.log_timing(self.logger, f"delete_account for: {full_name}")
                return True
            except Exception as e:
                self.log_helper.log(self.logger, 'warning', f"Could not confirm account deletion by toast: {str(e)}. Checking if account still exists.")
                # Fallback: check if account still exists
                self.navigate_to_accounts_list_page()
                if not self.account_exists(full_name):
                    self.log_helper.log(self.logger, 'info', f"Account {full_name} no longer exists. Deletion successful.")
                    self.log_helper.dedent()
                    return True
                else:
                    self.log_helper.log(self.logger, 'error', f"Account {full_name} still exists after attempted deletion.")
                    self.page.screenshot(path="delete-toast-not-found.png")
                    self.log_helper.dedent()
                    return False
        except Exception as e:
            self.log_helper.log(self.logger, 'error', f"Error deleting account {full_name}: {str(e)}")
            self.log_helper.log_timing(self.logger, f"delete_account (error) for: {full_name}")
            self.page.screenshot(path="delete-error.png")
            self.log_helper.dedent()
            return False


    def salesforce_search_account(self, folder_name: str, view_name: str = "All Clients", dropbox_account_name_parts: dict = None) -> Dict[str, Any]:
        """Perform a fuzzy search based on a folder name."""
        start_time = time.time()
        result = {
            'folder_name': folder_name,
            'status': 'not_found',
            'matches': [],
            'search_attempts': [],
            'timing': {},
            'view': view_name,
            'normalized_names': [],
            'swapped_names': [],
            'expected_salesforce_matches': [],
            'match_info': {
                'match_status': "No match found",
                'total_matches': 0,
                'total_partial_matches': 0,
                'total_no_matches': 1
            }
        }
        
        try:
            self.logger.info(f"***fuzzy_search_account: {folder_name}") 
            # Extract name parts
            # name_parts = extract_name_parts(folder_name)
            last_name = dropbox_account_name_parts.get('last_name', '')
            # full_name = dropbox_account_name_parts.get('full_name', '')
            
            # Add normalized and swapped names to result
            result['normalized_names'] = dropbox_account_name_parts.get('normalized_names', [])
            result['swapped_names'] = dropbox_account_name_parts.get('swapped_names', [])
            result['expected_salesforce_matches'] = dropbox_account_name_parts.get('expected_salesforce_matches', [])
            
            self.logger.info(f"\nExtracted name parts for '{folder_name}':")
            self.logger.info(f"    First name: {dropbox_account_name_parts.get('first_name', '')}")
            self.logger.info(f"    Last name: {last_name}")
            self.logger.info(f"    Normalized names: {result['normalized_names']}")
            self.logger.info(f"    Swapped names: {result['swapped_names']}")
            self.logger.info(f"    Expected matches: {result['expected_salesforce_matches']}")
            
            # Search by last name first
            self.logger.info(f"\nSearching in view: {view_name}")
            search_result = self.search_by_last_name(last_name, view_name=view_name)
            self.logger.info(f"Type of search_result: {type(search_result)}")
            self.logger.info(f"Value of search_result: {search_result}")
            self.logger.info(f"\nSearch results for last name '{last_name}':")
            self.logger.info(f"    Found {len(search_result)} matches")
            for match in search_result:
                self.logger.info(f"    - {match}")
            
            # Store the search attempt
            search_attempt = {
                'type': 'Last Name',
                'query': last_name,
                'matching_accounts': search_result,
                'view': view_name
            }
            result['search_attempts'].append(search_attempt)

            self.logger.info(f"***search_result: {search_result}")
            
            # Update matches if found
            if search_result:
                # Check for exact matches first
                matches = []
                for match in search_result:
                    match_lower = match.lower()
                    # Check normalized names
                    for normalized in result['normalized_names']:
                        normalized_lower = normalized.lower()
                        if match_lower in normalized_lower or normalized_lower in match_lower:
                            if match not in matches:
                                matches.append(match)
                                self.logger.info(f"Found exact match: {match} (matches normalized name: {normalized})")
                    
                    # Check swapped names
                    for swapped in result['swapped_names']:
                        swapped_lower = swapped.lower()
                        if match_lower in swapped_lower or swapped_lower in match_lower:
                            if match not in matches:
                                matches.append(match)
                                self.logger.info(f"Found exact match: {match} (matches swapped name: {swapped})")

                    logging.info(f"***result['expected_salesforce_matches']: {result['expected_salesforce_matches']}")
                    expected_salesforce_matches_exists = result['expected_salesforce_matches'] != []
                    expected_match_found = False
                    for expected_match in result['expected_salesforce_matches']:
                        expected_match_lower = expected_match.lower()
                        if match_lower in expected_match_lower or expected_match_lower in match_lower:
                            expected_match_found = True
                            if match not in matches:
                                matches.append(match)
                                self.logger.info(f"Found exact match: {match} (matches expected match: {expected_match})")
                        
                
                if matches:
                    result['status'] = 'match'
                    result['matches'] = matches  # Only include exact matches
                    self.logger.info(f"Found {len(matches)} exact matches: {matches}")
                else:
                    if expected_salesforce_matches_exists and expected_match_found:
                        result['matches'] = search_result 
                        result['status'] = 'partial_match'
                    else:
                        self.logger.info(f'no expected match found, so no partial match found')
                        result['matches'] = []
                        result['status'] = 'no_match'
                
                result['view'] = view_name
                match_info = self.get_match_info(result)
                result['match_info'] = match_info
                self.logger.info(f"match_info: {match_info}")
                self.logger.info(f"result: {result}")

                self.logger.info(f"\nDropbox account folder name: {folder_name} status:[{result['status']}] match:[{result['match_info']['match_status']}] view:[{result['view']}]")
                for match in result['matches']:
                    self.logger.info(f"  👤 Salesforce Account Search Results: {match}")
                
                # Add timing information
                result['timing'] = {
                    'total': time.time() - start_time,
                    'search': 0  # No timing info from search_by_last_name
                }
                
                self.logger.info(f"  Timing for fuzzy_search_account for folder: {folder_name}: {result['timing']['total']:.2f} seconds")
                # self.logger.info(f"Returning from fuzzy_search_account: {result}")
                return result
            else:
                result['folder_name'] = folder_name
                result['status'] = 'not_found'
                result['matches'] = []
                result['search_attempts'] = []
                result['timing'] = {}
                result['view'] = view_name
                match_info = self.get_match_info(result)
                result['match_info'] = match_info
                result['timing'] = { 
                    'total': time.time() - start_time,
                    'search': 0 
                }
                return result
            
        except Exception as e:
            self.logger.error(f"Error in fuzzy_search_account: {str(e)}")
            result['status'] = 'error'
            result['error'] = str(e)
            return result

    def search_by_last_name(self, last_name: str, view_name: str = "All Clients") -> List[str]:
        """
        Search for accounts by last name.
        
        Args:
            last_name: The last name to search for
            view_name: The name of the list view to use
            
        Returns:
            List[str]: List of matching account names
        """
        self.log_helper.indent()
        try:
            self.log_helper.log(self.logger, 'info', f"INFO: ***search_by_last_name: searching for last name: {last_name}")
            # Search for the last name
            matching_accounts = self.search_account(last_name, view_name=view_name)
            self.log_helper.log(self.logger, 'info', f"Found {len(matching_accounts)} matching accounts:")
            for account in matching_accounts:
                self.log_helper.log(self.logger, 'info', f"  - {account}")
            self.log_helper.dedent()
            return matching_accounts
        except Exception as e:
            self.log_helper.log(self.logger, 'error', f"Error searching by last name: {str(e)}")
            self.log_helper.dedent()
            return []

    def search_by_full_name(self, full_name: str) -> List[str]:
        self.log_helper.indent()
        try:
            self.log_helper.log(self.logger, 'info', f"INFO: search_by_full_name ***searching for full name: {full_name}")
            # Search for the full name
            matching_accounts = self.search_account(full_name)
            # Get matching accounts
            # matching_accounts = self.get_account_names()
            self.log_helper.dedent()
            return matching_accounts
        except Exception as e:
            self.log_helper.log(self.logger, 'error', f"Error searching by full name: {str(e)}")
            self.log_helper.dedent()
            return []

    def refresh_page(self) -> bool:
        """Refresh the current page and wait for it to load.
        
        Returns:
            bool: True if refresh was successful, False otherwise
        """
        self.log_helper.indent()
        try:
            self.log_helper.log(self.logger, 'info', "Refreshing page...")
            
            # Store current URL for verification
            current_url = self.page.url
            self.log_helper.log(self.logger, 'info', f"Current URL before refresh: {current_url}")
            
            # Refresh the page
            self.page.reload()
            
            # Wait for network to be idle
            # self.page.wait_for_load_state('networkidle', timeout=10000)
            # self.log_helper.log(self.logger, 'info', "Network is idle after refresh")
            
            # Wait for DOM content to be loaded
            # self.page.wait_for_load_state('domcontentloaded', timeout=10000)
            self.log_helper.log(self.logger, 'info', "DOM content loaded after refresh")
            
            # Verify we're still on the same page
            new_url = self.page.url
            if new_url != current_url:
                self.log_helper.log(self.logger, 'warning', f"URL changed after refresh. Old: {current_url}, New: {new_url}")
            
            # Wait for any loading spinners to disappear
            try:
                self.page.wait_for_selector('.slds-spinner_container', state='hidden', timeout=5000)
                self.log_helper.log(self.logger, 'info', "Loading spinner disappeared")
            except Exception as e:
                self.log_helper.log(self.logger, 'info', f"No loading spinner found or already disappeared: {str(e)}")
            
            self.log_helper.log(self.logger, 'info', "Page refresh completed successfully")
            self.log_helper.dedent()
            return True
            
        except Exception as e:
            self.log_helper.log(self.logger, 'error', f"Error refreshing page: {str(e)}")
            self._take_screenshot("page-refresh-error")
            self.log_helper.dedent()
            return False
    
    def get_match_info(self, result):
        """
        Get match info for a given result.
        
        Args:
            result (dict): The search result dictionary
        """
        try:
            logging.info(f"get_match_info: {result}")

            matches = result['matches']
            
            # Initialize counters for match types
            total_matches = 0
            total_partial_matches = 0
            total_no_matches = 0
            
            # Determine expected names for exact match (case-insensitive)
            expected_names = []
            
            # Try to get expected matches from special case logic if available
            if 'expected_salesforce_matches' in result:
                expected_names = [n.lower() for n in result['expected_salesforce_matches']]
            else:
                # Use normalized names from the search term, or just the dropbox name
                expected_names = [result['folder_name'].lower()]
            
            
            # Determine match status
            match_status = "No match found"
            if matches != "--" and matches:
                if isinstance(matches, list):
                    for name in matches:
                        if name.lower() in expected_names:
                            match_status = "Match Found"
                            break
                    if result['status'] == 'match':
                        match_status = "Match Found"
                    if match_status != "Match Found":
                        match_status = "Partial Match"
                else:
                    if matches.lower() in expected_names:
                        match_status = "Match Found"
                    else:
                        match_status = "Partial Match"
            
            # Update counters based on match status
            if match_status == "Match Found":
                total_matches += 1
            elif match_status == "Partial Match":
                total_partial_matches += 1
            else:
                total_no_matches += 1
            
            return {
                'match_status': match_status,
                'total_matches': total_matches,
                'total_partial_matches': total_partial_matches,
                'total_no_matches': total_no_matches
            }
        except (KeyError, TypeError) as e:
            return {
                'match_status': "No match found",
                'total_matches': 0,
                'total_partial_matches': 0,
                'total_no_matches': 1
            }

    def ensure_account_view_page(self, account_id: str) -> bool:
        """Ensure we are on the account view page for the specified account.
        
        Args:
            account_id: The Salesforce account ID to navigate to
            
        Returns:
            bool: True if successfully on account view page, False otherwise
        """
        self.log_helper.log(self.logger, 'info', f"****ensure_account_view_page for account {account_id}")
        
        self.log_helper.indent()
        try:
            # Check if we're already on the correct account view page
            current_url = self.page.url
            expected_url_pattern = f".*Account/{account_id}/view.*"
            
            if re.match(expected_url_pattern, current_url):
                self.log_helper.log(self.logger, 'info', f"Already on account view page for {account_id}")
                self.log_helper.dedent()
                return True
                
            # If not on the correct page, navigate to it
            self.log_helper.log(self.logger, 'info', f"Not on account view page, navigating to account {account_id}")
            account_url = f"{SALESFORCE_URL}/lightning/r/Account/{account_id}/view"
            self.page.goto(account_url)
            
            # Wait for the page to load
            self.page.wait_for_load_state('networkidle')
            
            # Verify we're on the correct page
            current_url = self.page.url
            if not re.match(expected_url_pattern, current_url):
                self.log_helper.log(self.logger, 'error', f"Failed to navigate to account view page. Current URL: {current_url}")
                self._take_screenshot("account-navigation-error")
                self.log_helper.dedent()
                return False
                
            self.log_helper.log(self.logger, 'info', f"Successfully navigated to account view page for {account_id}")
            self.log_helper.dedent()
            return True
            
        except Exception as e:
            self.log_helper.log(self.logger, 'error', f"Error ensuring account view page: {str(e)}")
            self._take_screenshot("account-navigation-error")
            self.log_helper.dedent()
            return False

    def navigate_to_account_files_click_on_files_card_to_facilitate_file_operation(self) -> int:
        """Navigate to the Files page of the current account. Assumes you are already on the account detail page.
        
        Returns:
            int: Number of files found in the account, -1 if there was an error
        """
        self.log_helper.log(self.logger, 'info', "****navigate_to_account_files_click_on_files_card_to_facilitate_file_operation")
        self.log_helper.log(self.logger, 'info', "****Attempting to navigate to Files...")
        self.log_helper.log(self.logger, 'info', f"Current URL: {self.page.url}")
        
        try:
            # Try the most specific selector first: span[title="Files"]
            try:
                self.log_helper.log(self.logger, 'info', "Trying span[title='Files'] selector...")
                files_span = self.page.wait_for_selector('span[title="Files"]', timeout=10000)
                if files_span and files_span.is_visible():
                    # Try to click the parent element (often the tab itself)
                    parent = files_span.evaluate_handle('el => el.closest("a,button,li,div[role=\'tab\']")')
                    if parent:
                        parent.as_element().click()
                        self.log_helper.log(self.logger, 'info', "Clicked Files card using span[title='Files'] parent.")
                        
                        # Verify URL pattern
                        current_url = self.page.url
                        self.log_helper.log(self.logger, 'info', f"Current URL after clicking Files tab: {current_url}")
                        
                        # Verify URL pattern: Account/{account_id}/related/AttachedContentDocuments/view
                        if not re.match(r'.*Account/\w+/related/AttachedContentDocuments/view.*', current_url):
                            raise Exception(f"Not on Files page. Current URL: {current_url}")
                        
                        # Extract and store account ID from URL
                        account_id_match = re.search(r'/Account/(\w+)/related', current_url)
                        if account_id_match:
                            account_id = account_id_match.group(1)
                            self.log_helper.log(self.logger, 'info', f"Extracted account ID from Files page URL: {account_id}")
                            self.current_account_id = account_id
                        
                        # Use the new reusable method
                        file_manager_instance = file_manager.SalesforceFileManager(self.page)
                        item_count = file_manager_instance.extract_files_count_from_status()
                        return item_count
                    else:
                        # If no parent found, try clicking the span directly
                        files_span.click()
                        self.log_helper.log(self.logger, 'info', "Clicked Files tab using span[title='Files'] directly.")
                        self.page.wait_for_selector('div.slds-tabs_default__content', timeout=2000)
                        self.log_helper.log(self.logger, 'info', "Files tab content loaded")
                        return 0
            except Exception as e:
                self.log_helper.log(self.logger, 'info', f"span[title='Files'] selector failed: {str(e)}")

            # If we get here, none of the selectors worked
            self.log_helper.log(self.logger, 'error', "Could not find Files tab with any of the selectors")
            
            # Take a screenshot for debugging
            self.page.screenshot(path="files-tab-error.png")
            self.log_helper.log(self.logger, 'info', "Error screenshot saved as files-tab-error.png")
            return -1
            
        except Exception as e:
            self.log_helper.log(self.logger, 'error', f"Error navigating to Files tab: {str(e)}")
            # Take a screenshot for debugging
            self.page.screenshot(path="files-tab-error.png")
            self.log_helper.log(self.logger, 'info', "Error screenshot saved as files-tab-error.png")
            return -1