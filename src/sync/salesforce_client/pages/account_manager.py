from typing import Callable, Optional, Dict, List, Union
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

class AccountManager(BasePage):
    """Handles account-related operations in Salesforce."""
    
    def __init__(self, page: Page, debug_mode: bool = False):
        super().__init__(page, debug_mode)
        self.current_account_id = None
        self.accounts_page = AccountsPage(page, debug_mode)
        self.special_cases = self._load_special_cases()
        
    def _load_special_cases(self) -> dict:
        """Load special cases from the configuration file.
        
        Returns:
            dict: Dictionary mapping folder names to their special case rules
        """
        try:
            special_cases_file = Path('accounts/special_cases.json')
            if not special_cases_file.exists():
                self.logger.info("No special cases file found")
                return {}
                
            with open(special_cases_file, 'r') as f:
                data = json.load(f)
                # Convert list to dictionary for easier lookup
                return {case['folder_name']: case for case in data.get('special_cases', [])}
        except Exception as e:
            self.logger.error(f"Error loading special cases: {str(e)}")
            return {}
            
    def _is_special_case(self, folder_name: str) -> bool:
        """Check if a folder name is a special case.
        
        Args:
            folder_name: The folder name to check
            
        Returns:
            bool: True if the folder name is a special case, False otherwise
        """
        return folder_name in self.special_cases
        
    def _get_special_case_rules(self, folder_name: str) -> dict:
        """Get the special case rules for a folder name.
        
        Args:
            folder_name: The folder name to get rules for
            
        Returns:
            dict: The special case rules or None if not found
        """
        return self.special_cases.get(folder_name)
        
    def navigate_to_accounts_list_page(self, view_name: str = "All Clients") -> bool:
        """Navigate to the Accounts page with a specific list view.
        
        Args:
            view_name: Name of the list view to use (default: "All Clients")
            
        Returns:
            bool: True if navigation was successful, False otherwise
        """
        try:
            # Navigate to the list view
            if not self._navigate_to_accounts_list_view_url(view_name):
                self.logger.error("Failed to navigate to list view")
                self._take_screenshot("accounts-navigation-error")
                return False
                
            # Wait for the search input
            if not self._wait_for_selector('ACCOUNT', 'search_input', timeout=20000):
                self.logger.error("Search input not found")
                self._take_screenshot("accounts-navigation-error")
                return False
                
            # Verify the accounts table is visible
            if not self._wait_for_selector('ACCOUNT', 'account_table'):
                self.logger.error("Accounts table not visible")
                return False
                
            self.logger.info("Successfully navigated to Accounts page")
            return True
            
        except Exception as e:
            self.logger.error(f"Error navigating to Accounts page: {str(e)}")
            self._take_screenshot("accounts-navigation-error")
            return False

    def _navigate_to_accounts_list_view_url(self, view_name: str) -> bool:
        """Navigate to a specific list view URL.
        
        Args:
            view_name: Name of the list view to navigate to
            
        Returns:
            bool: True if navigation was successful, False otherwise
        """
        try:
            # Construct the URL with the correct list view filter
            # Convert view_name to the format expected by Salesforce (e.g., "All Clients" -> "AllClients")
            filter_name = view_name.replace(" ", "")
            url = f"{SALESFORCE_URL}/lightning/o/Account/list?filterName={filter_name}"
            
            # Check if we're already on the correct URL
            current_url = self.page.url
            if current_url == url:
                self.logger.info(f"Already on the correct list view URL: {url}")
                return True
                
            self.logger.info(f"Navigating directly to list view URL: {url}")
            
            # Navigate to the URL
            self.page.goto(url)
            self.page.wait_for_load_state('networkidle', timeout=10000)
            self.page.wait_for_load_state('domcontentloaded', timeout=10000)
            return True
        except Exception as e:
            self.logger.error(f"Error navigating to list view URL: {str(e)}")
            return False

    def search_account(self, search_term: str, view_name: str = "All Clients") -> bool:
        """
        Search for an account in Salesforce.
        
        Args:
            search_term: The term to search for
            view_name: The name of the list view to use
            
        Returns:
            bool: True if search was successful, False otherwise
        """
        try:
            # Navigate to accounts page if not already there
            if not self.navigate_to_accounts_list_page():
                return False
            
            # Clear any existing search
            self.clear_search()
            
            # Enter search term
            search_input = self.page.locator("input[placeholder='Search this list...']")
            search_input.fill(search_term)
            search_input.press("Enter")
            logging.info(f"Pressed Enter for search term: {search_term}")
           
            logging.info(f"Waiting for 1 second(s)...")
            self.page.wait_for_timeout(1000)
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
                    self.logger.info(f"No items to display for search term: {search_term}")
                    return True
            except Exception as e:
                self.logger.warning(f"Error waiting for empty content or table: {str(e)}")
            
            # Wait for search results
            try:
                # Wait for the loading spinner to disappear
                self.page.wait_for_selector('div.slds-spinner_container', state='hidden', timeout=5000)
                
                # Wait for the table to be visible
                table = self.page.wait_for_selector('table.slds-table', timeout=10000)
                if not table:
                    self.logger.error("Search results table not found")
                    return False
                
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
                                self.logger.info(f"Salesforce reports {num_items_str} items (50+ means 50 or more) for search term: {search_term}")
                            else:
                                num_items = int(num_items_str)
                                self.logger.info(f"Salesforce reports {num_items} items for search term: {search_term}")
                        else:
                            self.logger.warning(f"Could not parse number of items from status bar: '{status_text}'")
                    else:
                        self.logger.warning("Status bar element not found for item count.")
                except Exception as e:
                    self.logger.warning(f"Error parsing number of items from status bar: {str(e)}")
                
                # CAROLINA HERE HERE
                # Wait for any rows to be visible
                rows = self.page.locator('table.slds-table tbody tr').all()
                num_rows = len(rows)
                self.logger.info(f"Found {num_rows} rows in table for search term: {search_term}")

                # If status bar says 50+ and num_rows < 50, warn about lazy loading
                if num_items is not None and isinstance(num_items, int) and num_rows < num_items:
                    self.logger.warning(f"Table may not have loaded all rows: status bar says {num_items}+ items, but only {num_rows} rows are visible. Consider implementing scrolling or pagination.")
                    # After warning, check for the empty content indicator
                    empty_content = self.page.locator('div.emptyContent.slds-is-absolute').first
                    if empty_content and empty_content.is_visible():
                        self.logger.info(f"No items to display for search term: {search_term}")
                        return True
                    else:
                        self.logger.info(f"***Table loaded with {num_rows} rows for search term: {search_term}")
                
                # Log each result
                found_account_names = []  # Initialize once before the loop
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
                            self.logger.info(f"Found account: {name}")
                            found_account_names.append(name)
                        else:
                            self.logger.warning(f"Could not find account name link in row for search term: {search_term}")
                    except Exception as e:
                        self.logger.warning(f"Error getting account name from row: {str(e)}")
                        continue
                # Only log if no account names were found (use the correct variable)
                self.logger.info(f"DEBUG: found_account_names = {found_account_names}")
                self.logger.info(f"DEBUG: len(found_account_names) = {len(found_account_names)}")
                if len(found_account_names) == 0:
                    self.logger.info("***No account names found in search results")
                
                # Compare the parsed number of items to the number of rows
                if num_items is not None:
                    if num_items != num_rows:
                        self.logger.warning(f"Discrepancy: Salesforce reports {num_items} items, but found {num_rows} rows in table for search term: {search_term}")
                    else:
                        self.logger.info(f"Number of items matches number of rows for search term: {search_term}")
                
                # If 0 items, log and return
                if num_items == 0 or num_rows == 0:
                    self.logger.info(f"No results found for search term: {search_term}")
                    return True
                
                return True
                
            except Exception as e:
                self.logger.error(f"Error waiting for search results: {str(e)}")
                return False
            
        except Exception as e:
            self.logger.error(f"Error searching for account: {str(e)}")
            return False

    def clear_search(self):
        """Clear the search field."""
        try:
            search_input = self.page.locator("input[placeholder='Search this list...']")
            search_input.fill("")
            search_input.press("Enter")
            self.page.wait_for_timeout(1000)  # Wait for search to clear
        except Exception as e:
            self.logger.error(f"Error clearing search: {str(e)}")

    def get_account_names(self) -> List[str]:
        """
        Get the names of all accounts in the current search results.
        
        Returns:
            List[str]: List of account names
        """
        try:
            # Wait for the table to be visible
            table = self.page.wait_for_selector('table.slds-table', timeout=10000)
            if not table:
                self.logger.error("Search results table not found")
                return []
            
            # Get all account names from the table
            account_elements = self.page.locator('table.slds-table tbody tr td:nth-child(2) a').all()
            logging.info(f"INFO: ***account_elements = {account_elements}")
            if not account_elements:
                self.logger.info("+++No account names found in search results")
                return []
            
            account_names = []
            for element in account_elements:
                try:
                    name = element.text_content().strip()
                    if name:
                        account_names.append(name)
                except Exception as e:
                    self.logger.warning(f"Error getting account name: {str(e)}")
                    continue
                
            self.logger.info(f"Found {len(account_names)} account names in search results")
            return account_names
            
        except Exception as e:
            self.logger.error(f"Error getting account names: {str(e)}")
            return []

    def account_exists(self, account_name: str, view_name: str = "All Accounts") -> bool:
        """Check if an account exists with the exact name.
        
        Args:
            account_name: The name of the account to check
            view_name: The name of the list view to use (default: "All Accounts")
            
        Returns:
            bool: True if the account exists, False otherwise
        """
        self.logger.info(f"Checking if account exists: {account_name} in view: {view_name}")
        
        try:
            # Navigate to the list view
            if not self._navigate_to_accounts_list_view_url(view_name):
                self.logger.error("Failed to navigate to list view")
                return False
            
            # Wait for the search input to be visible
            self.logger.info("Waiting for search input...")
            search_input = self.page.wait_for_selector('input[placeholder="Search this list..."]', timeout=20000)
            if not search_input:
                self.logger.error("Search input not found")
                self._take_screenshot("search-input-not-found")
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
                self.logger.error(f"Search text mismatch. Expected: {account_name}, Got: {actual_text}")
                self._take_screenshot("search-text-mismatch")
                return False
            
            # Press Enter and wait for results
            self.page.keyboard.press("Enter")
            
            # Wait for search results
            self.logger.info("Waiting for search results...")
            try:
                # Wait for the loading spinner to disappear
                self.page.wait_for_selector('.slds-spinner_container', state='hidden', timeout=5000)
                self.logger.info("Loading spinner disappeared")
                
                # Wait a moment for results to appear
                self.page.wait_for_timeout(1000)  # Reduced wait time
                
                # Check for the exact account name
                account_link = self.page.locator(f'a[title="{account_name}"]').first
                if account_link and account_link.is_visible():
                    self.logger.info(f"Account exists: {account_name}")
                    return True
                
                self.logger.info(f"Account does not exist: {account_name}")
                return False
                
            except Exception as e:
                self.logger.error(f"Error waiting for search results: {str(e)}")
                return False
            
        except Exception as e:
            self.logger.error(f"Error checking if account exists: {str(e)}")
            return False

    def click_account_name(self, account_name: str) -> bool:
        """Click on the account name in the search results."""
        try:
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
                        self.page.wait_for_load_state("networkidle", timeout=5000)
                        
                        # Verify we're on the account view page and extract ID
                        current_url = self.page.url
                        if '/view' in current_url:
                            account_id_match = re.search(r'/Account/([^/]+)/view', current_url)
                            if account_id_match:
                                self.current_account_id = account_id_match.group(1)
                                return True
                except Exception:
                    continue
            
            self.logger.error(f"Could not find or click account link for: {account_name}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error clicking account name: {str(e)}")
            return False

    def click_save_button(self) -> bool:
        """Click the Save button."""
        # Save the account
        logging.info("Clicking Save button...")
        try:
            # First try to find and click the visible Save button directly
            save_button = self.page.locator('button:has-text("Save")').first
            if save_button and save_button.is_visible():
                save_button.scroll_into_view_if_needed()
                self.page.wait_for_timeout(500)
                save_button.click()
                logging.info("Successfully clicked visible Save button")
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
                            logging.info("Successfully clicked visible Save button")
                            return True
                except Exception:
                    continue

            raise Exception("Could not find an enabled Save button to click")
        except Exception as e:
            logging.error(f"Error clicking Save button: {str(e)}")
            self.page.screenshot(path="save-button-error.png")
            logging.info("Error screenshot saved as save-button-error.png")
            raise Exception("Could not click Save button")
            

    def click_next_button(self) -> bool:    
        """Click the Next button."""
        
        logging.info("Clicking Next button...")
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
        try:
            full_name = self.get_full_name(first_name, last_name, middle_name)
            self.logger.info(f"Creating new account for: {full_name}")
            
            # Click New button
            self.logger.info("Step 1: Attempting to click New button...")
            if not self._click_element('ACCOUNT', 'new_button'):
                self.logger.error("Could not find or click New button")
                self._take_screenshot("new-button-error")
                sys.exit(1)
            self.logger.info("Successfully clicked New button")
                
            # Select Client radio button
            self.logger.info("Step 2: Attempting to select Client radio button...")
            # Log the page content for debugging
            # self.logger.info("Current page content:")
            # self.logger.info(self.page.content())
            
            # Click Next button
            self.logger.info("Step 3: Attempting to click Next button...")
            self.click_next_button()
            self.logger.info("Successfully clicked Next button")
                
            # Fill name fields
            self.logger.info("Step 4: Attempting to fill First Name field...")
            if not self._fill_input('FORM', 'first_name', first_name):
                self.logger.error("Could not fill First Name field")
                self._take_screenshot("first-name-error")
                sys.exit(1)
            self.logger.info(f"Successfully filled First Name with: {first_name}")
                
            self.logger.info("Step 5: Attempting to fill Last Name field...")
            if not self._fill_input('FORM', 'last_name', last_name):
                self.logger.error("Could not fill Last Name field")
                self._take_screenshot("last-name-error")
                sys.exit(1)
            self.logger.info(f"Successfully filled Last Name with: {last_name}")
                
            if middle_name:
                self.logger.info("Step 6: Attempting to fill Middle Name field...")
                if not self._fill_input('FORM', 'middle_name', middle_name):
                    self.logger.error("Could not fill Middle Name field")
                    self._take_screenshot("middle-name-error")
                    sys.exit(1)
                self.logger.info(f"Successfully filled Middle Name with: {middle_name}")
                
            # Fill additional account info if provided
            if account_info and 'phone' in account_info:
                self.logger.info("Step 7: Attempting to fill Phone field...")
                if not self._fill_input('FORM', 'phone_field', account_info['phone']):
                    self.logger.error("Could not fill Phone field")
                    self._take_screenshot("phone-field-error")
                    sys.exit(1)
                self.logger.info(f"Successfully filled Phone with: {account_info['phone']}")
                    
            # Click Save button
            self.logger.info("Step 8: Attempting to click Save button...")
            # if not self._click_element('ACCOUNT', 'save_button'):
            #     self.logger.error("Could not find or click Save button")
            #     self._take_screenshot("save-button-error")
            #     sys.exit(1)
            # self.logger.info("Successfully clicked Save button")
            self.click_save_button()
                
            # Wait for save confirmation with increased timeout
            self.logger.info("Step 9: Waiting for save confirmation...")
            try:
                # Wait for network to be idle
                self.page.wait_for_load_state('networkidle', timeout=60000)  # 60 second timeout
                
                # Try multiple confirmation methods
                confirmation_found = False
                
                logging.info(f"****Waiting for save confirmation")
                logging.info(f"Method 1: Check for toast message")
                # Method 1: Check for toast message
                try:
                    toast = self.page.wait_for_selector('div.slds-notify_toast, div.slds-notify--toast', timeout=40000)
                    if toast and toast.is_visible():
                        toast_text = toast.text_content()
                        self.logger.info(f"Found toast message: {toast_text}")
                        if 'success' in toast_text.lower() or 'was created' in toast_text.lower():
                            confirmation_found = True
                except Exception as e:
                    self.logger.info(f"No toast message found: {str(e)}")
                
                logging.info(f"Method 2: Check URL change")
                # Method 2: Check URL change
                logging.info(f"confirmation_found: {confirmation_found}")
                if not confirmation_found:
                    try:
                        # Wait for URL to change to view page
                        self.page.wait_for_url(lambda url: '/view' in url, timeout=40000)
                        self.logger.info("URL changed to view page")
                        confirmation_found = True
                        
                        # Additional wait for page load after URL change
                        self.page.wait_for_load_state('networkidle', timeout=20000)
                        self.page.wait_for_load_state('domcontentloaded', timeout=20000)
                    except Exception as e:
                        self.logger.info(f"URL did not change: {str(e)}")
                
                logging.info(f"Method 3: Check for account name")
                # Method 3: Check for account name
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
                            if self.page.locator(selector).first.is_visible():
                                self.logger.info(f"Account name found with selector: {selector}")
                                confirmation_found = True
                                break
                        except Exception as e:
                            self.logger.info(f"Selector {selector} failed: {str(e)}")
                
                if not confirmation_found:
                    raise Exception("Could not confirm save operation completed")
                
                self.logger.info("Save confirmation received")
                
                # Verify account creation
                self.logger.info("Step 10: Verifying account creation...")
                if not self._verify_account_creation(first_name, last_name, middle_name):
                    self.logger.error("Could not verify account creation")
                    self._take_screenshot("account-verification-error")
                    return False
                self.logger.info("Successfully verified account creation")
                
                self.logger.info("Successfully created new account")
                return True
                
            except Exception as e:
                self.logger.error(f"Error during save confirmation: {str(e)}")
                self._take_screenshot("save-confirmation-error")
                return False
            
        except Exception as e:
            self.logger.error(f"Error creating new account: {str(e)}")
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
        try:
            # # Wait for the page to fully load
            # self.page.wait_for_load_state('networkidle')
            # self.page.wait_for_timeout(5000)  # Additional wait for list to refresh
            
            # Verify URL contains /view and extract account ID
            current_url = self.page.url
            self.logger.info(f"Current URL: {current_url}")
            if '/view' not in current_url:
                raise Exception(f"Not on account view page. Current URL: {current_url}")
            
            # Extract account ID from URL
            account_id_match = re.search(r'/Account/([^/]+)/view', current_url)
            if not account_id_match:
                raise Exception(f"Could not extract account ID from URL: {current_url}")
            
            account_id = account_id_match.group(1)
            self.logger.info(f"Extracted account ID from URL: {account_id}")
            
            # If this is after account creation, store the ID
            self.current_account_id = account_id
            self.logger.info(f"Stored created account ID: {account_id}")
            
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
                        self.logger.info(f"Account name '{account_name}' is visible on the page (selector: {selector})")
                        name_found = True
                        break
                except Exception as e:
                    self.logger.info(f"Account name selector {selector} failed: {str(e)}")
                    
            if not name_found:
                self.logger.error(f"Could not find account name '{account_name}' on the page after Save.")
                self.page.screenshot(path="account-name-not-found.png")
                return False
                
            self.logger.info("Successfully verified account creation")
            return True
            
        except Exception as e:
            self.logger.error(f"Error verifying account creation: {str(e)}")
            self.page.screenshot(path="account-creation-verification-error.png")
            return False
            

    def navigate_to_account_by_id(self, account_id: str) -> bool:
        """Navigate to an account using its ID.
        
        Args:
            account_id: The Salesforce account ID to navigate to
            
        Returns:
            bool: True if navigation was successful, False otherwise
        """
        self.logger.info(f"Navigating to account with ID: {account_id}")
        
        try:
            # Construct the URL for the account
            url = f"{SALESFORCE_URL}/lightning/r/Account/{account_id}/view"
            self.logger.info(f"Navigating to URL: {url}")
            
            # Navigate to the URL
            self.page.goto(url)
            # self.page.wait_for_load_state('networkidle')
            
            # Verify we're on the correct account page
            current_url = self.page.url
            if f"/Account/{account_id}/view" not in current_url:
                self.logger.error(f"Navigation failed. Expected URL containing /Account/{account_id}/view, got: {current_url}")
                self._take_screenshot("account-navigation-error")
                sys.exit(1)
                
            # Store the account ID
            self.current_account_id = account_id
            self.logger.info(f"Successfully navigated to account {account_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error navigating to account {account_id}: {str(e)}")
            self._take_screenshot("account-navigation-error")
            sys.exit(1)
            
    def navigate_back_to_account_page(self):
        """Navigate back to the current account page."""
        logging.info("Navigating back to account page...")
        if not self.current_account_id:
            logging.error("No current account ID available")
            self._take_screenshot("account-navigation-error")
            sys.exit(1)
            
        try:
            url = f"{SALESFORCE_URL}/lightning/r/Account/{self.current_account_id}/view"
            logging.info(f"Navigating to URL: {url}")
            self.page.goto(url)
            # self.page.wait_for_load_state('networkidle')
            # checking url 
            current_url = self.page.url
            if f"/Account/{self.current_account_id}/view" not in current_url:
                logging.error(f"Navigation failed. Expected URL containing /Account/{self.current_account_id}/view, got: {current_url}")
                self._take_screenshot("account-navigation-error")
                sys.exit(1)
            logging.info("Back on account page")
        except Exception as e:
            logging.error(f"Error navigating back to account page: {str(e)}")
            self._take_screenshot("account-navigation-error")
            sys.exit(1) 

    def navigate_to_files_and_get_number_of_files_for_this_account(self, account_id: str) -> Union[int, str]:
        """
        Navigate to the Files related list for the given account_id.
        Returns either an integer or a string (e.g. "50+") representing the number of files.
        """
        files_url = f"{SALESFORCE_URL}/lightning/r/Account/{account_id}/related/AttachedContentDocuments/view"
        logging.info(f"Checking current URL for account {account_id}")
        
        # Check if we're already on the correct files URL
        current_url = self.page.url
        if current_url != files_url:
            logging.info(f"Navigating to Files page for account {account_id}: {files_url}")
            self.page.goto(files_url)
        else:
            logging.info(f"Already on Files page for account {account_id}")
            
        file_manager_instance = file_manager.FileManager(self.page)
        num_files = file_manager_instance.extract_files_count_from_status()
        logging.info(f"Initial number of files: {num_files}")
        
        # Scroll to load all files if we see a "50+" count
        if isinstance(num_files, str) and '+' in str(num_files):
            logging.info("Found '{num_files}+' count, scrolling to load all files...")
            actual_count = file_manager_instance.scroll_to_bottom_of_page()
            if actual_count > 0:
                logging.info(f"Final number of files after scrolling: {actual_count}")
                return actual_count
            
        return num_files

    def get_all_file_names_for_account(self, account_id: str) -> List[str]:
        """
        Get all file names associated with an account.
        
        Args:
            account_id: The Salesforce account ID
        
        Returns:
            List[str]: List of file names found in the account
        """
        self.logger.info(f"Getting all file names for account {account_id}")
        
        try:
            # Navigate to files section
            logging.info("Navigating to files section")
            logging.info(f"account_id: {account_id}")
            num_files = self.navigate_to_files_and_get_number_of_files_for_this_account(account_id)
            if num_files == -1:
                logging.error("Failed to navigate to Files")
                return []
                
            # Use FileManager to get file names
            file_manager_instance = file_manager.FileManager(self.page)
            return file_manager_instance.get_all_file_names()
            
        except Exception as e:
            self.logger.error(f"Error getting file names: {str(e)}")
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
        try:
            self.logger.debug(f"Getting accounts base: {view_name}")
            # Navigate to accounts page
            self.logger.debug(f"Navigating to Accounts page: {SALESFORCE_URL}/lightning/o/Account/list?filterName=__Recent")
            if not self.navigate_to_accounts_list_page():
                self.logger.error("Failed to navigate to Accounts page")
                return []

            # Select the specified list view
            self.logger.debug(f"Selecting list view: {view_name}")
            if not self._navigate_to_accounts_list_view_url(view_name):
                return []

            # Wait for table to be visible
            self.logger.debug(f"Waiting for table to be visible")
            try:
                table = self.page.wait_for_selector('table[role="grid"]', timeout=10000)
                if not table:
                    self.logger.error("Table element not found")
                    return []
                self.logger.debug("Table element found")
            except Exception as e:
                self.logger.error(f"Table not found after 10 seconds: {str(e)}")
                return []

            # Wait for table to be populated and visible
            self.logger.debug(f"Waiting for table to be populated and visible")
            try:
                # Wait for the table to be fully loaded
                self.logger.debug("Waiting for network to be idle")
                self.page.wait_for_load_state('networkidle', timeout=10000)
                
                # Wait for the loading spinner to disappear (if present)
                try:
                    self.logger.debug("Waiting for loading spinner to disappear")
                    self.page.wait_for_selector('.slds-spinner_container', state='hidden', timeout=5000)
                except:
                    self.logger.debug("No loading spinner found")
                
                # Force the table to be visible by evaluating JavaScript
                self.logger.debug("Forcing table visibility with JavaScript")
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
                self.logger.debug("Getting all table rows")
                rows = self.page.locator('table[role="grid"] tr').all()
                if not rows:
                    self.logger.error("No rows found in table")
                    return []
                
                self.logger.debug(f"Found {len(rows)} rows in table")
                
                # Additional wait to ensure table is fully rendered
                self.logger.debug("Waiting for table to stabilize")
                self.page.wait_for_timeout(2000)
                
            except Exception as e:
                self.logger.error(f"Error waiting for table rows: {str(e)}")
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
                        self.logger.warning(f"Could not get outer HTML for row {idx}: {e}")
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
                        self.logger.debug(f"***Account name: {name} found")
                        self.logger.debug(f"***Account id: {account_id} found")
                       
                    except Exception as e:
                        self.logger.warning(f"Error getting text content for row: {str(e)}")
                        continue
                except Exception as e:
                    self.logger.warning(f"Error processing account row: {str(e)}")
                    continue
            
            return accounts
            
        except Exception as e:
            self.logger.error(f"Error getting accounts: {str(e)}")
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
            logging.debug(f"Processing account: {account['name']}")
            files_count = self.navigate_to_files_and_get_number_of_files_for_this_account(account['id'])
            account['files_count'] = files_count
            processed_accounts.append(account)
            if the_condition(account):
                accounts.append(account)
                if len(accounts) >= max_number:
                    break
        logging.info(f"Total accounts processed: {len(processed_accounts)}")
        for acc in processed_accounts:
            logging.info(f"Processed account: Name={acc['name']}, ID={acc['id']}, Files={acc['files_count']}")
        return accounts

    def verify_account_page_url(self) -> tuple[bool, Optional[str]]:
        """Verify that the current URL is a valid account page URL and extract the account ID.
        
        Returns:
            tuple[bool, Optional[str]]: A tuple containing:
                - bool: True if the URL is valid, False otherwise
                - Optional[str]: The account ID if found, None otherwise
        """
        try:
            current_url = self.page.url
            self.logger.info(f"Current URL: {current_url}")
            
            # Check if we're on an account page
            if not re.match(r'.*Account/\w+/view.*', current_url):
                self.logger.error(f"Not on account page. Current URL: {current_url}")
                return False, None
            
            # Extract account ID from URL
            account_id_match = re.search(r'/Account/(\w+)/view', current_url)
            if not account_id_match:
                self.logger.error(f"Could not extract account ID from URL: {current_url}")
                return False, None
            
            account_id = account_id_match.group(1)
            self.logger.info(f"Extracted account ID from URL: {account_id}")
            return True, account_id
            
        except Exception as e:
            self.logger.error(f"Error verifying account page URL: {str(e)}")
            return False, None

    def account_has_files(self, account_id: str) -> bool:
        """
        Check if the account has files.
        """
        num_files = self.navigate_to_files_and_get_number_of_files_for_this_account(account_id)
        if isinstance(num_files, str):
            # If we have a string like "50+", we know there are files
            return True
        return num_files > 0
    
    
    def deprecated_account_has_files(self, account_id: str) -> bool:
        """
        Check if the account has files.
        """
        account_url = f"{SALESFORCE_URL}/lightning/r/{account_id}/view"
        logging.info(f"Navigating to account view page: {account_url}")
        self.page.goto(account_url)
        # self.page.wait_for_load_state('networkidle', timeout=30000)
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
                    logging.info(f"Account {account_id} Files count: {files_number}")
                    found = True
                    return files_number > 0
            if not found:
                logging.error(f"Files card not found for account {account_id}")
                sys.exit(1)
        except Exception as e:
            logging.error(f"Could not extract files count for account {account_id}: {e}")
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
        try:
            # Search for the account
            if not self.account_exists(full_name, view_name=view_name):
                self.logger.error(f"Account {full_name} does not exist")
                return False
            # Click on the account name to navigate to it
            if not self.click_account_name(full_name):
                self.logger.error(f"Failed to navigate to account view page for: {full_name}")
                return False
            # Verify we're on the correct account page
            is_valid, account_id = self.verify_account_page_url()
            if not is_valid:
                self.logger.error("Not on a valid account page")
                return False
            self.logger.info(f"Successfully navigated to account {full_name} with ID {account_id}")
            # Wait for page to load completely and stabilize
            self.page.wait_for_load_state('networkidle')
            self.page.wait_for_timeout(2000)
            # Step 1: Click the left-panel Delete button (try several selectors and log all candidates)
            delete_selectors = [
                "button[title='Delete']",
                "button:has-text('Delete')",
                "input[value='Delete']",
                "a[title='Delete']",
                "a:has-text('Delete')",
            ]
            delete_btn = None
            for selector in delete_selectors:
                try:
                    elements = self.page.query_selector_all(selector)
                    for el in elements:
                        try:
                            visible = el.is_visible()
                            enabled = el.is_enabled()
                            text = el.text_content()
                            attrs = el.get_attribute('outerHTML')
                            self.logger.info(f"Delete button candidate: selector={selector}, visible={visible}, enabled={enabled}, text={text}, outerHTML={attrs}")
                            if visible and enabled:
                                delete_btn = el
                                break
                        except Exception as e:
                            self.logger.info(f"Error checking delete button candidate: {e}")
                    if delete_btn:
                        self.logger.info(f"Found delete button with selector: {selector}")
                        break
                except Exception as e:
                    self.logger.info(f"Error finding delete button with selector {selector}: {e}")
                    continue
            if not delete_btn:
                self.logger.error("Could not find enabled/visible left-panel Delete button with any selector")
                self.page.screenshot(path="delete-btn-not-found.png")
                return False
            try:
                delete_btn.click()
                self.logger.info("Clicked left-panel Delete button.")
            except Exception as e:
                self.logger.error(f"Error clicking left-panel Delete button: {e}")
                self.page.screenshot(path="delete-btn-click-error.png")
                return False
            self.page.wait_for_timeout(1000)
            # Step 2: Wait for the modal and confirm deletion
            try:
                self.page.wait_for_selector('button[title="Delete"] span.label.bBody', timeout=5000)
            except Exception:
                self.logger.error("Delete confirmation modal did not appear after clicking delete button")
                self.page.screenshot(path="delete-modal-not-found.png")
                return False
            # Log modal text for debugging
            try:
                modal = self.page.query_selector('div[role="dialog"]')
                if modal:
                    modal_text = modal.text_content()
                    self.logger.info(f"Delete modal text: {modal_text}")
            except Exception:
                pass
            # Click the modal's Delete button using the provided selector
            try:
                modal_delete_btn_span = self.page.wait_for_selector('button[title="Delete"] span.label.bBody', timeout=5000)
                if not modal_delete_btn_span:
                    self.logger.error("Could not find modal Delete button span.label.bBody")
                    self.page.screenshot(path="modal-delete-btn-not-found.png")
                    return False
                modal_delete_btn_span.click()
                self.logger.info("Clicked modal Delete button.")
            except Exception as e:
                self.logger.error(f"Error clicking modal Delete button: {e}")
                self.page.screenshot(path="modal-delete-btn-click-error.png")
                return False
            # Wait for the modal to close
            try:
                self.page.wait_for_selector('button[title="Delete"] span.label.bBody', state='detached', timeout=8000)
                self.logger.info("Delete confirmation modal closed.")
            except Exception:
                self.logger.warning("Delete confirmation modal did not close in time.")
            # Wait for deletion confirmation (toast)
            try:
                self.page.wait_for_selector('div.slds-notify_toast, div.slds-notify--toast', timeout=15000)
                self.logger.info(f"Successfully deleted account: {full_name}")
                return True
            except Exception as e:
                self.logger.warning(f"Could not confirm account deletion by toast: {str(e)}. Checking if account still exists.")
                # Fallback: check if account still exists
                self.navigate_to_accounts_list_page()
                if not self.account_exists(full_name):
                    self.logger.info(f"Account {full_name} no longer exists. Deletion successful.")
                    return True
                else:
                    self.logger.error(f"Account {full_name} still exists after attempted deletion.")
                    self.page.screenshot(path="delete-toast-not-found.png")
                    return False
        except Exception as e:
            self.logger.error(f"Error deleting account {full_name}: {str(e)}")
            self.page.screenshot(path="delete-error.png")
            return False

    def extract_name_parts(self, name: str) -> dict:
        """Extract name parts from a name string.
        
        Rules:
        1. If there's a comma, everything before the comma is the last name
        2. If there's no comma:
           - If there are 2 words, the last name is the 2nd word
           - If there's '&' or 'and', first word is first name, second word is last name, and anything after &/'and' is additional info
           - If there are 3 words and no '&'/'and', last name is 3rd word, middle name is 2nd word
        3. Special cases can override these rules
        """
        # Check for special case first
        if self._is_special_case(name):
            self.logger.info(f"Found special case for folder: {name}")
            special_case = self._get_special_case_rules(name)
            result = {
                'last_name': special_case['last_name'],
                'first_name': '',
                'middle_name': '',
                'additional_info': '',
                'swapped_names': [],
                'normalized_names': [],
                'expected_matches': special_case['expected_matches']
            }
            
            # Add normalized versions for the expected matches
            for match in special_case['expected_matches']:
                result['normalized_names'].append(match.lower().strip())
                # Also add the swapped version
                parts = match.split()
                if len(parts) >= 2:
                    swapped = f"{parts[1]} {parts[0]}"
                    result['normalized_names'].append(swapped.lower().strip())
            
            return result
            
        # Continue with normal name parsing if not a special case
        result = {
            'last_name': '',
            'first_name': '',
            'middle_name': '',
            'additional_info': '',
            'swapped_names': []
        }
        
        # Extract additional info in parentheses
        if '(' in name:
            parts = name.split('(')
            main_name = parts[0].strip()
            result['additional_info'] = parts[1].rstrip(')').strip()
        else:
            main_name = name
        
        # Handle names with commas
        if ',' in main_name:
            parts = main_name.split(',')
            result['last_name'] = parts[0].strip()
            if len(parts) > 1:
                # Split the remaining part into first and middle names
                name_parts = parts[1].strip().split()
                if name_parts:
                    result['first_name'] = name_parts[0]
                    if len(name_parts) > 1:
                        result['middle_name'] = ' '.join(name_parts[1:])
        else:
            # Split the name into words
            name_parts = main_name.split()
            
            # Check for '&' or 'and'
            has_ampersand = '&' in main_name
            has_and = ' and ' in main_name.lower()
            
            if has_ampersand or has_and:
                # Handle names with '&' or 'and'
                if has_ampersand:
                    parts = main_name.split('&')
                else:
                    parts = main_name.lower().split(' and ')
                
                # First part is the main name
                main_parts = parts[0].strip().split()
                if len(main_parts) >= 2:
                    result['first_name'] = main_parts[0]
                    result['last_name'] = main_parts[1]
                    if len(main_parts) > 2:
                        result['middle_name'] = ' '.join(main_parts[2:])
                
                # Everything after & or 'and' is additional info
                if len(parts) > 1:
                    result['additional_info'] = parts[1].strip()
            else:
                # Handle names without '&' or 'and'
                if len(name_parts) == 2:
                    # Two words: first word is first name, second word is last name
                    result['first_name'] = name_parts[0]
                    result['last_name'] = name_parts[1]
                elif len(name_parts) == 3:
                    # Three words: first word is first name, second word is middle name, third word is last name
                    result['first_name'] = name_parts[0]
                    result['middle_name'] = name_parts[1]
                    result['last_name'] = name_parts[2]
                elif len(name_parts) > 3:
                    # More than three words: first word is first name, last word is last name, everything in between is middle name
                    result['first_name'] = name_parts[0]
                    result['last_name'] = name_parts[-1]
                    result['middle_name'] = ' '.join(name_parts[1:-1])
                else:
                    # Single word: treat as last name
                    result['last_name'] = main_name
        
        # Normalize the name parts
        result['last_name'] = result['last_name'].strip()
        result['first_name'] = result['first_name'].strip()
        result['middle_name'] = result['middle_name'].strip()
        result['additional_info'] = result['additional_info'].strip()
        
        # Create normalized versions of the name
        result['normalized_names'] = []
        
        # Add the original name
        result['normalized_names'].append(name.lower().strip())
        
        # Add comma-separated version
        if result['first_name'] and result['last_name']:
            result['normalized_names'].append(f"{result['last_name']}, {result['first_name']}".lower().strip())
            result['normalized_names'].append(f"{result['last_name']},{result['first_name']}".lower().strip())
            
            # Add comma-separated version with middle name
            if result['middle_name']:
                result['normalized_names'].append(f"{result['last_name']}, {result['first_name']} {result['middle_name']}".lower().strip())
                result['normalized_names'].append(f"{result['last_name']},{result['first_name']} {result['middle_name']}".lower().strip())
            
            # Add swapped name variations
            result['swapped_names'].append(f"{result['first_name']} {result['last_name']}".lower().strip())
            if result['middle_name']:
                result['swapped_names'].append(f"{result['first_name']} {result['middle_name']} {result['last_name']}".lower().strip())
            
            # Add version with additional info
            if result['additional_info']:
                result['normalized_names'].append(f"{result['first_name']} {result['last_name']} & {result['additional_info']}".lower().strip())
                result['normalized_names'].append(f"{result['first_name']} {result['last_name']} and {result['additional_info']}".lower().strip())
        
        # Add space-separated version
        if result['first_name'] and result['last_name']:
            result['normalized_names'].append(f"{result['first_name']} {result['last_name']}".lower().strip())
        
        # Add version with middle name
        if result['middle_name']:
            if result['first_name'] and result['last_name']:
                result['normalized_names'].append(f"{result['first_name']} {result['middle_name']} {result['last_name']}".lower().strip())
        
        # Remove duplicates and empty strings
        result['normalized_names'] = list(set(n for n in result['normalized_names'] if n))
        result['swapped_names'] = list(set(n for n in result['swapped_names'] if n))
        
        return result

    def fuzzy_search_account(self, folder_name: str) -> dict:
        """
        Perform a fuzzy search for an account based on a folder name.
        
        Args:
            folder_name: The Dropbox folder name to search for
            
        Returns:
            dict: A dictionary containing:
                - status: 'Exact Match', 'Partial Match', or 'No Match'
                - matches: List of matching account names
                - search_attempts: List of search attempts with details
                - timing: Dictionary with timing information
        """
        start_time = time.time()
        result = {
            'status': 'No Match',
            'matches': [],
            'search_attempts': [],
            'timing': {}
        }
        
        try:
            # Extract name parts
            name_parts = self.extract_name_parts(folder_name)
            if not name_parts:
                self.logger.error(f"Failed to extract name parts from folder name: {folder_name}")
                return result
            
            # Get normalized names for comparison
            normalized_names = name_parts.get('normalized_names', [])
            if not normalized_names:
                self.logger.error(f"No normalized names found for folder name: {folder_name}")
                return result
            
            # Get swapped names for comparison
            swapped_names = name_parts.get('swapped_names', [])
            
            # Search by last name first
            last_name = name_parts.get('last_name', '')
            if last_name:
                last_name_result = self.search_by_last_name(last_name)
                if last_name_result:
                    result['search_attempts'].append({
                        'type': 'Last Name',
                        'query': last_name,
                        'matching_accounts': last_name_result,
                        'matches': len(last_name_result)
                    })
                    # Add matches to the result
                    result['matches'].extend(last_name_result)
            
            # Search by full name variations
            for name in normalized_names + swapped_names:
                full_name_result = self.search_by_full_name(name)
                if full_name_result:
                    result['search_attempts'].append({
                        'type': 'Full Name',
                        'query': name,
                        'matching_accounts': full_name_result,
                        'matches': len(full_name_result)
                    })
                    # Add matches to the result
                    result['matches'].extend(full_name_result)
            
            # Remove duplicates from matches
            result['matches'] = list(set(result['matches']))
            
            # Check for exact matches (case-insensitive, including expected_matches)
            expected_names = name_parts.get('expected_matches', [])
            all_expected = [n.lower() for n in normalized_names + swapped_names + expected_names]
            exact_matches = []
            for match in result['matches']:
                if match.lower() in all_expected:
                    exact_matches.append(match)
            
            # Update result status and matches
            if exact_matches:
                result['status'] = 'Exact Match'
                result['matches'] = exact_matches
            elif result['matches']:
                result['status'] = 'Partial Match'
            
            # Add timing information
            result['timing'] = {
                'total_duration': time.time() - start_time,
                'name_extraction': name_parts.get('timing', {}).get('total', 0)
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error during fuzzy search: {str(e)}")
            result['status'] = 'Error'
            result['error'] = str(e)
            return result

    def search_by_last_name(self, last_name: str) -> List[str]:
        """
        Search for accounts by last name.
        
        Args:
            last_name: The last name to search for
            
        Returns:
            List[str]: List of matching account names
        """
        try:
            logging.info(f"INFO: ***searching for last name: {last_name}")
            # Search for the last name
            self.search_account(last_name)
            # Get matching accounts
            matching_accounts = self.get_account_names()
            return matching_accounts
        except Exception as e:
            self.logger.error(f"Error searching by last name: {str(e)}")
            return []

    def search_by_full_name(self, full_name: str) -> List[str]:
        """
        Search for accounts by full name.
        
        Args:
            full_name: The full name to search for
            
        Returns:
            List[str]: List of matching account names
        """
        try:
            logging.info(f"INFO: ***searching for full name: {full_name}")
            # Search for the full name
            self.search_account(full_name)
            # Get matching accounts
            matching_accounts = self.get_account_names()
            return matching_accounts
        except Exception as e:
            self.logger.error(f"Error searching by full name: {str(e)}")
            return []