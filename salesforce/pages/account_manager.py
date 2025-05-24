from typing import Callable, Optional, Dict, List, Union
import logging
import re

from salesforce.pages import file_manager
from .base_page import BasePage
from playwright.sync_api import Page
from sync.config import SALESFORCE_URL
import sys
import os
from salesforce.pages.accounts_page import AccountsPage

class AccountManager(BasePage):
    """Handles account-related operations in Salesforce."""
    
    def __init__(self, page: Page, debug_mode: bool = False):
        super().__init__(page, debug_mode)
        self.current_account_id = None
        self.accounts_page = AccountsPage(page, debug_mode)
        
    def navigate_to_accounts_list_page(self) -> bool:
        """Navigate to the Accounts page."""
        url = f"{SALESFORCE_URL}/lightning/o/Account/list?filterName=__Recent"
        self.logger.info(f"Navigating to Accounts page: {url}")
        
        try:
            self.page.goto(url)
            self.page.wait_for_load_state('domcontentloaded')
            
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
            
    def search_account(self, account_name: str, view_name: str = "All Accounts") -> int:
        """Search for an account by name and return the number of items found.
        
        Args:
            account_name: The name of the account to search for
            view_name: The name of the list view to use (default: "All Accounts")
            
        Returns:
            int: The number of items found
        """
        try:
            self.logger.info(f"Searching for account: {account_name} in view: {view_name}")
            
            # First ensure we're on the accounts list page
            if not self.navigate_to_accounts_list_page():
                self.logger.error("Failed to navigate to accounts list page")
                return 0
            
            # Select the specified view
            self.logger.info(f"Selecting '{view_name}' view...")
            if not self.accounts_page.select_list_view(view_name):
                self.logger.error(f"Failed to select '{view_name}' view")
                return 0
            
            # Wait for the page to be fully loaded
            self.page.wait_for_load_state('networkidle', timeout=10000)
            self.page.wait_for_load_state('domcontentloaded', timeout=10000)
            
            # Wait for the search input to be visible with increased timeout
            self.logger.info("Waiting for search input...")
            search_input = self.page.wait_for_selector('input[placeholder="Search this list..."]', timeout=20000)
            if not search_input:
                self.logger.error("Search input not found")
                self._take_screenshot("search-input-not-found")
                return 0
            
            # Ensure the search input is visible and clickable
            self.logger.info("Ensuring search input is visible and clickable...")
            search_input.scroll_into_view_if_needed()
            self.page.wait_for_timeout(1000)  # Wait for scroll to complete
            
            # Click the search input to ensure it's focused
            search_input.click()
            self.page.wait_for_timeout(500)  # Wait for focus
            
            # Clear the search input
            self.logger.info("Clearing search input...")
            search_input.fill("")
            self.page.wait_for_timeout(500)  # Wait for clear
            
            # Type the account name character by character with longer delays
            self.logger.info(f"Typing account name: {account_name}")
            for char in account_name:
                search_input.type(char, delay=200)  # Increased delay between characters
                self.page.wait_for_timeout(100)  # Increased wait between characters
            
            # Verify the text was entered correctly
            actual_text = search_input.input_value()
            if actual_text != account_name:
                self.logger.error(f"Search text mismatch. Expected: {account_name}, Got: {actual_text}")
                self._take_screenshot("search-text-mismatch")
                return 0
            
            self.logger.info("Pressing Enter...")
            self.page.keyboard.press("Enter")
            
            # Wait for search results with a more specific check
            self.logger.info("Waiting for search results...")
            try:
                # First wait for the loading spinner to disappear
                self.page.wait_for_selector('div.slds-spinner_container', state='hidden', timeout=5000)
                self.logger.info("Loading spinner disappeared")
                
                # Wait a moment for results to appear
                self.page.wait_for_timeout(2000)
                
                # Check the item count in the status message
                try:
                    # Try multiple selectors for the status message
                    status_selectors = [
                        'span.countSortedByFilteredBy',
                        'span.slds-text-body_small',
                        'div.slds-text-body_small',
                        'span[class*="count"]'
                    ]
                    
                    for selector in status_selectors:
                        try:
                            status_message = self.page.wait_for_selector(selector, timeout=5000)
                            if status_message:
                                status_text = status_message.text_content()
                                self.logger.info(f"Status message: {status_text}")
                                
                                # Extract the number of items
                                self.logger.info("***Extracting the number of items...")
                                match = re.search(r'(\d+\+?)\s+items?\s+•', status_text)
                                if match:
                                    item_count_str = match.group(1)
                                    # Remove the plus sign if present and convert to int
                                    item_count = int(item_count_str.rstrip('+'))
                                    self.logger.info(f"Found {item_count} items in search results")
                                    return item_count
                        except Exception as e:
                            self.logger.info(f"Selector {selector} failed: {str(e)}")
                            continue
                    
                    # If we get here, none of the selectors worked
                    self.logger.info("Could not find status message with any selector")
                    self._take_screenshot("status-message-not-found")
                    return 0
                    
                except Exception as e:
                    self.logger.info(f"Error checking status message: {str(e)}")
                    return 0
                
            except Exception as e:
                self.logger.info(f"Error waiting for search results: {str(e)}")
                return 0
            
        except Exception as e:
            self.logger.error(f"Error searching for account: {e}")
            self._take_screenshot("search-error")
            return 0
            
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
            # Search for the account
            item_count = self.search_account(account_name, view_name=view_name)
            
            if item_count > 0:
                # Verify the account name matches exactly
                account_link = self.page.locator(f'a[title="{account_name}"]').first
                if account_link and account_link.is_visible():
                    self.logger.info(f"Account exists: {account_name}")
                    return True
                    
            self.logger.info(f"Account does not exist: {account_name}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking if account exists: {str(e)}")
            return False
            
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
            
    def create_new_account(self, first_name: str, last_name: str, 
                          middle_name: Optional[str] = None, 
                          account_info: Optional[Dict[str, str]] = None) -> bool:
        """Create a new account with the given information."""
        try:
            self.logger.info(f"Creating new account for: {first_name} {last_name}")
            
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
                # # Wait for network to be idle
                # self.page.wait_for_load_state('networkidle', timeout=600)  # Increased to 60 seconds
                # self.page.wait_for_timeout(10000)  # Additional 10 second wait
                
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
                        logging.info(f"Waiting for URL lambda url: '/view' in url") 
                        self.page.wait_for_url(lambda url: '/view' in url, timeout=4000)
                        self.logger.info("URL changed to view page")
                        confirmation_found = True
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
                    sys.exit(1)
                self.logger.info("Successfully verified account creation")
                
                self.logger.info("Successfully created new account")
                return True
                
            except Exception as e:
                self.logger.error(f"Error during save confirmation: {str(e)}")
                self._take_screenshot("save-confirmation-error")
                sys.exit(1)
            
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
        logging.info(f"Navigating to Files page for account {account_id}: {files_url}")
        self.page.goto(files_url)
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

        
    def get_all_file_names_for_this_account(self, account_id: str) -> List[str]:
        """
        Get all file names associated with an account.
        
        Args:
            account_id: The Salesforce account ID
            
        Returns:
            List[str]: List of file names found in the account
        """
        self.logger.info(f"Getting all file names for account {account_id}")
        
        try:

            # CAROLINA HERE
            logging.info("Navigating to files section")
            logging.info(f"account_id: {account_id}")
            num_files = self.navigate_to_files_and_get_number_of_files_for_this_account(account_id)
            if num_files == -1:
                logging.error("Failed to navigate to Files")
                return
            # Wait for the files table to be visible and at least one file row to appear
            max_attempts = 5
            for attempt in range(max_attempts):
                try:
                    table = self.page.wait_for_selector('table.slds-table', timeout=4000)
                    file_rows = self.page.locator('table.slds-table tbody tr').all()
                    if file_rows and len(file_rows) > 0:
                        # Optionally, check if at least one row has a visible span.itemTitle
                        has_title = False
                        for row in file_rows:
                            if row.locator('span.itemTitle').count() > 0:
                                has_title = True
                                break
                        if has_title:
                            break
                    self.logger.info(f"Attempt {attempt+1}/{max_attempts}: Table or file rows not ready, retrying...")
                    self.page.wait_for_timeout(1000)
                except Exception as e:
                    self.logger.info(f"Attempt {attempt+1}/{max_attempts}: Waiting for files table failed: {str(e)}")
                    self.page.wait_for_timeout(1000)
            else:
                self.logger.error("Files table or file rows did not become visible after multiple attempts.")
                return []

            # Get all file rows immediately (after waiting)
            file_rows = self.page.locator('table.slds-table tbody tr').all()
            if not file_rows:
                self.logger.error("No file rows found after waiting")
                return []
            
            self.logger.info(f"Found {len(file_rows)} file rows")
            
            # Get file information with minimal waits
            logging.info("Getting file information with minimal waits")
            file_names = []
            total_rows = len(file_rows)
            self.logger.info(f"Starting to process {total_rows} file rows...")
            
            for i, row in enumerate(file_rows, 1):
                try:
                    # Log progress every 10 files or at the start
                    if i == 1 or i % 10 == 0:
                        self.logger.info(f"Processing file {i}/{total_rows} ({(i/total_rows)*100:.1f}%)")
                    
                    # Get file name
                    title_span = row.locator('span.itemTitle').first
                    if not title_span:
                        self.logger.warning(f"Skipping row {i}: No title span found")
                        continue
                    try:
                        file_name = title_span.text_content(timeout=3000).strip()
                    except Exception as e:
                        self.logger.warning(f"Timeout or error getting file name for row {i}: {str(e)}")
                        continue
                    if not file_name:
                        self.logger.warning(f"Skipping row {i}: Empty file name")
                        continue
                    
                    # Get file type from the type column
                    file_type = 'Unknown'
                    try:
                        type_cell = row.locator('th:nth-child(2) span a div').first
                        if type_cell:
                            type_text = type_cell.text_content(timeout=1000).strip()
                            if type_text:
                                # Extract just the file type by removing the filename part
                                # The filename part starts with a number or is all caps
                                type_match = re.match(r'^([A-Za-z\s]+)(?=\d|[A-Z]{2,})', type_text)
                                if type_match:
                                    file_type = type_match.group(1).strip()
                                else:
                                    file_type = type_text
                    except Exception:
                        # If we can't get the type from the cell, try file extension
                        if file_name.lower().endswith('.pdf'):
                            file_type = 'PDF'
                        elif file_name.lower().endswith(('.doc', '.docx')):
                            file_type = 'DOC'
                        elif file_name.lower().endswith(('.xls', '.xlsx')):
                            file_type = 'XLS'
                        elif file_name.lower().endswith('.txt'):
                            file_type = 'TXT'
                        elif file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                            file_type = 'IMG'
                    
                    # Clean the file name by removing any existing numbers and file types
                    clean_name = re.sub(r'^\d+\.\s*', '', file_name)
                    clean_name = re.sub(r'\s*\[\w+\]\s*$', '', clean_name)
                    
                    file_names.append(f"{i}. {clean_name} [{file_type}]")
                    self.logger.debug(f"Successfully processed file {i}: {clean_name} [{file_type}]")
                except Exception as e:
                    self.logger.warning(f"Error getting file info for row {i}: {str(e)}")
                    continue
            
            self.logger.info(f"Completed processing {len(file_names)}/{total_rows} files successfully")
            return file_names
        except Exception as e:
            self.logger.error(f"Error getting file names: {str(e)}")
            return [] 

    def get_default_condition(self):
        """Get the default condition for filtering accounts."""
        def condition(account):
            return self.account_has_files(account['id'])
        return condition

    def get_accounts_matching_condition(
        self,
        max_number: int = 10,
        condition: Callable[[Dict[str, str]], bool] = None,
        drop_down_option_text: str = "All Clients"
    ) -> List[Dict[str, str]]:
        """
        Keep iterating through all accounts until max_number accounts that match a condition.
        By default, returns accounts that have more than 0 files.
        """
        accounts = []
        all_accounts = self.accounts_page._get_accounts_base(drop_down_option_text=drop_down_option_text)
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

    def delete_account(self, full_name: str) -> bool:
        """
        Delete an account by name.
        Args:
            full_name: Full name of the account to delete
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            # Search for the account
            if not self.account_exists(full_name):
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

    def get_account_names(self) -> list:
        """
        Extract account names from the current page.
        
        Returns:
            list: List of account names found on the page
        """
        account_names = []
        try:
            # Wait for table with timeout
            try:
                self.page.wait_for_selector('table[role="grid"]', timeout=5000)
            except Exception as e:
                self.logger.error(f"Table with role='grid' not found: {str(e)}")
                return []
            
            # Get all account rows immediately
            rows = self.page.locator('table[role="grid"] tr').all()
            self.logger.info(f"Found {len(rows)} rows in the table")
            if not rows or len(rows) <= 1:
                self.logger.error("No data rows found in the accounts table (or only header row present)")
                return []
            
            # Skip header row
            for i, row in enumerate(rows[1:], 1):  # Skip the first row (header)
                try:
                    # Prioritize extracting from <th scope="row"> a
                    name_cell = row.locator('th[scope="row"] a')
                    if name_cell.count() > 0:
                        try:
                            account_name = name_cell.nth(0).text_content(timeout=1000)
                            if account_name and account_name.strip():
                                account_names.append(account_name.strip())
                                self.logger.info(f"Found account using <th scope='row'> a: {account_name.strip()}")
                                continue
                        except Exception as e:
                            self.logger.warning(f"Timeout or error getting text for <th scope='row'> a in row {i}: {str(e)}")
                    # Fallback to previous selectors if needed
                    selectors = [
                        'td:first-child a',  # Standard link in first cell
                        'td:first-child',    # First cell if no link
                        'td a',              # Any link in the row
                        'td'                 # Any cell
                    ]
                    found = False
                    for selector in selectors:
                        element = row.locator(selector).first
                        if element.count() > 0:
                            try:
                                account_name = element.text_content(timeout=1000)
                                if account_name and account_name.strip():
                                    account_names.append(account_name.strip())
                                    self.logger.info(f"Found account using selector '{selector}': {account_name.strip()}")
                                    found = True
                                    break
                            except Exception as e:
                                self.logger.warning(f"Timeout or error getting text for selector '{selector}' in row {i}: {str(e)}")
                                continue
                    if not found:
                        # Log the row's HTML for debugging
                        try:
                            row_html = row.inner_html(timeout=1000)
                            self.logger.warning(f"Could not find account name in row {i}. Row HTML: {row_html}")
                        except Exception as e:
                            self.logger.warning(f"Could not get HTML for row {i}: {str(e)}")
                        continue
                except Exception as e:
                    self.logger.warning(f"Error getting account name for row {i}: {str(e)}")
                    continue
        except Exception as e:
            self.logger.error(f"Error extracting account names: {str(e)}")
        self.logger.info(f"Total accounts extracted: {len(account_names)}")
        self.logger.info(f"Extracted accounts: {account_names}")
        return account_names

    def fuzzy_search_account(self, folder_name: str, view_name: str = "All Clients") -> dict:
        """
        Perform a fuzzy search for an account using a folder name.
        
        Args:
            folder_name: The folder name to search for
            view_name: The name of the list view to use (default: "All Clients")
            
        Returns:
            dict: Dictionary containing:
                - status: 'Exact Match', 'Partial Match', or 'Not Found'
                - matches: List of matching account names
                - search_attempts: List of search attempts with their results
        """
        def extract_name_parts(name: str) -> dict:
            """Extract name parts from a name string."""
            result = {
                'last_name': '',
                'first_name': '',
                'middle_name': '',
                'additional_info': ''
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
                    name_parts = parts[1].strip().split()
                    if name_parts:
                        result['first_name'] = name_parts[0]
                        if len(name_parts) > 1:
                            result['middle_name'] = ' '.join(name_parts[1:])
            else:
                # Handle names with ampersands
                if '&' in main_name:
                    parts = main_name.split('&')
                    main_name = parts[0].strip()
                
                # Split remaining name parts
                name_parts = main_name.split()
                if len(name_parts) >= 2:
                    # Take the last word as the last name
                    result['last_name'] = name_parts[-1]
                    result['first_name'] = name_parts[0]
                    if len(name_parts) > 2:
                        result['middle_name'] = ' '.join(name_parts[1:-1])
                else:
                    result['last_name'] = main_name
            
            return result

        # Initialize result
        result = {
            'status': 'Not Found',
            'matches': [],
            'search_attempts': []
        }
        
        try:
            # Extract name parts
            name_parts = extract_name_parts(folder_name)
            self.logger.info(f"Extracted name parts: {name_parts}")
            
            # Select the specified view
            self.logger.info(f"Selecting '{view_name}' view...")
            if not self.accounts_page.select_list_view(view_name):
                self.logger.error(f"Failed to select '{view_name}' view")
                return result
            
            # Search by last name first
            self.logger.info(f"Attempt 1/3: Searching by last name '{name_parts['last_name']}'...")
            search_result = self.search_account(name_parts['last_name'], view_name=view_name)
            
            # Get matching account names
            matching_accounts = []
            if search_result > 0:
                self.logger.info(f"Found {search_result} matches, extracting account names...")
                matching_accounts = self.get_account_names()
            
            result['search_attempts'].append({
                'type': 'last_name',
                'query': name_parts['last_name'],
                'matches': search_result,
                'matching_accounts': matching_accounts
            })
            
            if search_result > 0:
                # Check for exact matches
                exact_matches = []
                partial_matches = []
                
                # Check for exact matches based on name parts
                if name_parts['first_name'] and name_parts['last_name']:
                    # Normalize all possible forms of the folder name
                    folder_full_name = f"{name_parts['first_name']} {name_parts['last_name']}".lower().replace(',', '').strip()
                    folder_reverse_name = f"{name_parts['last_name']} {name_parts['first_name']}".lower().replace(',', '').strip()
                    folder_comma_name = f"{name_parts['last_name']}, {name_parts['first_name']}".lower().replace(',', '').strip()
                    folder_comma_nospace = f"{name_parts['last_name']},{name_parts['first_name']}".lower().replace(',', '').strip()

                    for account in matching_accounts:
                        normalized_account = account.lower().replace(',', '').strip()
                        if normalized_account in [folder_full_name, folder_reverse_name, folder_comma_name.replace(',', ''), folder_comma_nospace.replace(',', '')]:
                            exact_matches.append(account)
                        else:
                            partial_matches.append(account)
                
                # If we have exact matches, update the result
                if exact_matches:
                    result['status'] = 'Exact Match'
                    result['matches'] = exact_matches
                else:
                    # If no exact matches, try searching with first name
                    if name_parts['first_name']:
                        self.logger.info(f"Attempt 2/3: Searching with full name '{name_parts['first_name']} {name_parts['last_name']}'...")
                        search_result = self.search_account(f"{name_parts['first_name']} {name_parts['last_name']}", view_name=view_name)
                        
                        # Get matching account names
                        matching_accounts = []
                        if search_result > 0:
                            self.logger.info(f"Found {search_result} matches, extracting account names...")
                            matching_accounts = self.get_account_names()
                        
                        result['search_attempts'].append({
                            'type': 'full_name',
                            'query': f"{name_parts['first_name']} {name_parts['last_name']}",
                            'matches': search_result,
                            'matching_accounts': matching_accounts
                        })
                        
                        # Add any new matches to partial matches
                        partial_matches.extend([m for m in matching_accounts if m not in partial_matches])
                    
                    # If still no match, try searching with additional info
                    if name_parts['additional_info']:
                        search_query = f"{name_parts['last_name']} {name_parts['additional_info']}"
                        self.logger.info(f"Attempt 3/3: Searching with additional info '{search_query}'...")
                        search_result = self.search_account(search_query, view_name=view_name)
                        
                        # Get matching account names
                        matching_accounts = []
                        if search_result > 0:
                            self.logger.info(f"Found {search_result} matches, extracting account names...")
                            matching_accounts = self.get_account_names()
                        
                        result['search_attempts'].append({
                            'type': 'with_additional_info',
                            'query': search_query,
                            'matches': search_result,
                            'matching_accounts': matching_accounts
                        })
                        
                        # Add any new matches to partial matches
                        partial_matches.extend([m for m in matching_accounts if m not in partial_matches])
                    
                    # Update status if we found any matches
                    if partial_matches:
                        result['status'] = 'Partial Match'
                        result['matches'] = partial_matches
            
        except Exception as e:
            self.logger.error(f"Error in fuzzy search: {str(e)}")
        
        return result