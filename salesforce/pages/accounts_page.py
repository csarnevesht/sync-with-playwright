from playwright.sync_api import Page, expect
from typing import Optional, List, Dict
import re
import os
import time
import logging
from config import SALESFORCE_URL
import sys

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
            if response in ['y', 'n']:
                return response == 'y'
            logging.info("Please enter 'y' or 'n'")

    def _debug_show_files(self, files: List[str]) -> List[str]:
        """
        Show files to be uploaded and prompt for confirmation.
        Returns the list of files that will be uploaded.
        """
        if not self.debug_mode:
            return files

        print("\nFiles to be uploaded:")
        for file in files:
            print(f"  + {os.path.basename(file)}")

        if not self._debug_prompt("Continue with these files?"):
            return []
        return files


    def click_account_name(self, account_name: str) -> bool:
        """Click on the account name in the search results."""
        logging.info(f"****Clicking account name: {account_name}")
        try:
            # Try the specific selector first
            try:
                self.logger.info(f"Trying specific selector: a[title='{account_name}']")
                account_link = self.page.wait_for_selector(f"a[title='{account_name}']", timeout=4000)
                if account_link and account_link.is_visible():
                    # Scroll the element into view
                    account_link.scroll_into_view_if_needed()
                    # Wait a bit for any animations to complete
                    self.page.wait_for_timeout(1000)
                    # Click the element
                    account_link.click()
                    self.logger.info(f"***Clicked account link using specific selector")
                    
                    # Verify we're on the account view page
                    logging.info(f"****Verifying we're on the account view page")
                    current_url = self.page.url
                    if '/view' not in current_url:
                        self.logger.error(f"Not on account view page. Current URL: {current_url}")
                        return False
                    logging.info(f"****Current URL: {current_url}")

                    # Extract account ID from URL
                    logging.info(f"****Extracting account ID from URL: {current_url}")
                    account_id_match = re.search(r'/Account/([^/]+)/view', current_url)
                    if not account_id_match:
                        self.logger.error(f"Could not extract account ID from URL: {current_url}")
                        return False
                    
                    # Store the account ID
                    self.current_account_id = account_id_match.group(1)
                    self.logger.info(f"Stored account ID: {self.current_account_id}")
                    return True
            except Exception as e:
                self.logger.info(f"Specific selector failed: {str(e)}")
            
            # If specific selector fails, try other selectors
            selectors = [
                f'a[data-refid="recordId"][data-special-link="true"][title="{account_name}"]',
                f'td:first-child a[title="{account_name}"]',
                f'table[role="grid"] tr:first-child td:first-child a',
                f'table[role="grid"] tr:first-child a[data-refid="recordLink"]'
            ]
            
            for selector in selectors:
                try:
                    self.logger.info(f"Trying selector: {selector}")
                    account_link = self.page.wait_for_selector(selector, timeout=4000)
                    if account_link and account_link.is_visible():
                        # Scroll the element into view
                        account_link.scroll_into_view_if_needed()
                        # Wait a bit for any animations to complete
                        self.page.wait_for_timeout(1000)
                        # Click the element
                        account_link.click()
                        self.logger.info(f"Clicked account link using selector: {selector}")
                        
                        # Wait for navigation to complete
                        self.page.wait_for_load_state("networkidle")
                        self.page.wait_for_timeout(2000)  # Additional wait for page to stabilize
                        
                        # Verify we're on the account view page
                        current_url = self.page.url
                        if '/view' not in current_url:
                            self.logger.error(f"Not on account view page. Current URL: {current_url}")
                            continue
                            
                        # Extract account ID from URL
                        account_id_match = re.search(r'/Account/([^/]+)/view', current_url)
                        if not account_id_match:
                            self.logger.error(f"Could not extract account ID from URL: {current_url}")
                            continue
                            
                        account_id = account_id_match.group(1)
                        self.logger.info(f"Successfully navigated to account view page. Account ID: {account_id}")
                        return True
                except Exception as e:
                    self.logger.info(f"Selector {selector} failed: {str(e)}")
                    continue
            
            self.logger.error("Could not find or click account link with any selector")
            return False
            
        except Exception as e:
            self.logger.error(f"Error clicking account name: {str(e)}")
            return False

    def click_first_account(self):
        """Click on the first account in the search results."""
        try:
            # Wait for the table to be visible
            self.page.wait_for_selector('table.slds-table', timeout=4000)
            
            # Try multiple selectors for the account name cell
            selectors = [
                'table.slds-table tbody tr:first-child td:first-child a',
                'table.slds-table tbody tr:first-child td:first-child',
                'table.slds-table tbody tr:first-child a[data-refid="recordLink"]'
            ]
            
            for selector in selectors:
                try:
                    # Wait for the element to be visible and clickable
                    element = self.page.wait_for_selector(selector, timeout=4000)
                    if element:
                        # Scroll the element into view
                        element.scroll_into_view_if_needed()
                        # Wait a bit for any animations to complete
                        self.page.wait_for_timeout(1000)
                        # Click the element
                        element.click()
                        logging.info("Successfully clicked on first account")
                        return True
                except Exception as e:
                    logging.debug(f"Selector {selector} failed: {str(e)}")
                    continue
            
            logging.error("Failed to click on first account - no working selector found")
            return False
            
        except Exception as e:
            logging.error(f"Error clicking first account: {str(e)}")
            return False
    

    def add_files(self):
        """Click the Add Files button and then the Upload Files button in the dialog."""
        try:
            # Click Add Files button using the specific selector
            add_files_button = self.page.wait_for_selector('div[title="Add Files"]', timeout=4000)
            if not add_files_button:
                raise Exception("Add Files button not found")
            add_files_button.click()
            logging.info("Clicked Add Files button")

            # Wait for and click Upload Files button in the dialog
            upload_files_button = self.page.wait_for_selector('button:has-text("Upload Files")', timeout=4000)
            if not upload_files_button:
                raise Exception("Upload Files button not found in dialog")
            upload_files_button.click()
            logging.info("Clicked Upload Files button in dialog")

            # Wait for the file input to be visible
            self.page.wait_for_selector('input[type="file"]', timeout=4000)
            logging.info("File input is visible")
        except Exception as e:
            logging.error(f"Error in add_files: {str(e)}")
            self.page.screenshot(path="add-files-error.png")
            raise



    def _get_available_form_fields(self) -> List[str]:
        """
        Get a list of field names that are actually available in the form.
        Returns a list of field names that can be found in the form.
        """
        available_fields = []
        
        # Common field patterns to check
        field_patterns = {
            'First Name': ['//label[contains(text(), "First Name")]', 'input[placeholder*="First Name"]'],
            'Last Name': ['//label[contains(text(), "Last Name")]', 'input[placeholder*="Last Name"]'],
            'Middle Name': ['//label[contains(text(), "Middle Name")]', 'input[placeholder*="Middle Name"]'],
            'Email': ['//label[contains(text(), "Email")]', 'input[placeholder*="Email"]'],
            'Phone': ['//label[contains(text(), "Phone")]', 'input[placeholder*="Phone"]'],
            'Address': ['//label[contains(text(), "Address")]', 'input[placeholder*="Address"]'],
            'City': ['//label[contains(text(), "City")]', 'input[placeholder*="City"]'],
            'State': ['//label[contains(text(), "State")]', 'select[placeholder*="State"]'],
            'Zip': ['//label[contains(text(), "Zip")]', 'input[placeholder*="Zip"]']
        }
        
        # Check each field pattern
        for field_name, selectors in field_patterns.items():
            for selector in selectors:
                try:
                    element = self.page.locator(selector).first
                    if element and element.is_visible():
                        available_fields.append(field_name)
                        break
                except Exception:
                    continue
        
        logging.info(f"Available form fields: {available_fields}")
        return available_fields

    def get_account_id(self) -> str:
        """
        Get the ID of the current account being viewed.
        
        Returns:
            str: The account ID.
            
        Raises:
            Exception: If the account ID is not available.
        """
        if self.current_account_id:
            logging.info(f"*****Current account ID: {self.current_account_id}")
            return self.current_account_id
            
        # Try to extract from current URL if not stored
        current_url = self.page.url
        account_id_match = re.search(r'/Account/([^/]+)/view', current_url)
        if account_id_match:
            self.current_account_id = account_id_match.group(1)
            return self.current_account_id
            
        raise Exception("No account ID available.")


    def get_current_url(self) -> str:
        """Get the current URL of the page."""
        return self.page.url 

    def iterate_through_accounts(self, account_names: List[str]):
        """
        Iterate through a list of account names, search for each account, and navigate to the account view page.
        
        Args:
            account_names: List of account names to iterate through.
        """
        for account_name in account_names:
            logging.info(f"\nSearching for account: {account_name}")
            self.navigate_to_accounts()
            self.search_account(account_name)
            if self.click_account_name(account_name):
                logging.info(f"Successfully navigated to account view page for: {account_name}")
            else:
                logging.info(f"Failed to navigate to account view page for: {account_name}") 