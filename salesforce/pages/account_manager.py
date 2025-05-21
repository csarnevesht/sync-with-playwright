from typing import Optional, Dict, List
import logging
import re
from ..base_page import BasePage
from playwright.sync_api import Page
from config import SALESFORCE_URL

class AccountManager(BasePage):
    """Handles account-related operations in Salesforce."""
    
    def __init__(self, page: Page, debug_mode: bool = False):
        super().__init__(page, debug_mode)
        self.current_account_id = None
        
    def navigate_to_accounts(self) -> bool:
        """Navigate to the Accounts page."""
        url = f"{SALESFORCE_URL}/lightning/o/Account/list?filterName=__Recent"
        self.logger.info(f"Navigating to Accounts page: {url}")
        
        try:
            self.page.goto(url)
            self.page.wait_for_load_state('domcontentloaded')
            
            # Wait for the search input
            if not self._wait_for_selector('ACCOUNT', 'search_input', timeout=30000):
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
            
    def search_account(self, account_name: str) -> int:
        """Search for an account by name and return the number of items found."""
        try:
            self.logger.info(f"Searching for account: {account_name}")
            
            # Wait for the search input to be visible
            self.logger.info("Waiting for search input...")
            search_input = self.page.wait_for_selector('input[placeholder="Search this list..."]', timeout=60000)
            if not search_input:
                self.logger.error("Search input not found")
                return 0
                
            # Clear and fill the search input
            self.logger.info("Clearing search input...")
            search_input.fill("")
            self.logger.info("Entering account name...")
            search_input.fill(account_name)
            self.logger.info("Pressing Enter...")
            self.page.keyboard.press("Enter")
            
            # Wait for search results with a more specific check
            self.logger.info("Waiting for search results...")
            try:
                # First wait for the loading spinner to disappear
                self.page.wait_for_selector('div.slds-spinner_container', state='hidden', timeout=30000)
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
                                self.logger.info("Extracting the number of items...")
                                match = re.search(r'(\d+)\s+items?\s+•', status_text)
                                if match:
                                    item_count = int(match.group(1))
                                    self.logger.info(f"Found {item_count} items in search results")
                                    return item_count
                        except Exception as e:
                            self.logger.info(f"Selector {selector} failed: {str(e)}")
                            continue
                    
                    # If we get here, none of the selectors worked
                    self.logger.info("Could not find status message with any selector")
                    return 0
                    
                except Exception as e:
                    self.logger.info(f"Error checking status message: {str(e)}")
                    return 0
                
            except Exception as e:
                self.logger.info(f"Error waiting for search results: {str(e)}")
                return 0
            
        except Exception as e:
            self.logger.error(f"Error searching for account: {e}")
            return 0
            
    def account_exists(self, account_name: str) -> bool:
        """Check if an account exists with the exact name."""
        self.logger.info(f"Checking if account exists: {account_name}")
        
        try:
            # Search for the account
            item_count = self.search_account(account_name)
            
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
        try:
            # Try the specific selector first
            try:
                self.logger.info(f"Trying specific selector: a[title='{account_name}']")
                account_link = self.page.wait_for_selector(f"a[title='{account_name}']", timeout=5000)
                if account_link and account_link.is_visible():
                    # Scroll the element into view
                    account_link.scroll_into_view_if_needed()
                    # Wait a bit for any animations to complete
                    self.page.wait_for_timeout(1000)
                    # Click the element
                    account_link.click()
                    self.logger.info(f"***Clicked account link using specific selector")
                    
                    # # Wait for navigation to complete
                    # print(f"****Waiting for navigation to complete")
                    # self.page.wait_for_load_state("networkidle")
                    # self.page.wait_for_timeout(2000)  # Additional wait for page to stabilize
                    
                    # Verify we're on the account view page
                    print(f"****Verifying we're on the account view page")
                    current_url = self.page.url
                    if '/view' not in current_url:
                        self.logger.error(f"Not on account view page. Current URL: {current_url}")
                        return False
                    print(f"****Current URL: {current_url}")

                    # Extract account ID from URL
                    print(f"****Extracting account ID from URL: {current_url}")
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
                    account_link = self.page.wait_for_selector(selector, timeout=5000)
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
            
    def create_new_account(self, first_name: str, last_name: str, 
                          middle_name: Optional[str] = None, 
                          account_info: Optional[Dict[str, str]] = None) -> bool:
        """Create a new account with the given information."""
        try:
            self.logger.info(f"Creating new account for: {first_name} {last_name}")
            
            # Click New button
            if not self._click_element('ACCOUNT', 'new_button'):
                self.logger.error("Could not find or click New button")
                return False
                
            # Select Client radio button
            if not self._click_element('FORM', 'client_radio'):
                self.logger.error("Could not find or click Client radio button")
                return False
                
            # Click Next button
            if not self._click_element('FORM', 'next_button'):
                self.logger.error("Could not find or click Next button")
                return False
                
            # Fill name fields
            if not self._fill_input('FORM', 'name_fields.first_name', first_name):
                self.logger.error("Could not fill First Name field")
                return False
                
            if not self._fill_input('FORM', 'name_fields.last_name', last_name):
                self.logger.error("Could not fill Last Name field")
                return False
                
            if middle_name and not self._fill_input('FORM', 'name_fields.middle_name', middle_name):
                self.logger.error("Could not fill Middle Name field")
                return False
                
            # Fill additional account info if provided
            if account_info and 'phone' in account_info:
                if not self._fill_input('FORM', 'phone_field', account_info['phone']):
                    self.logger.error("Could not fill Phone field")
                    return False
                    
            # Click Save button
            if not self._click_element('ACCOUNT', 'save_button'):
                self.logger.error("Could not find or click Save button")
                return False
                
            # Wait for save confirmation
            self.page.wait_for_load_state('networkidle')
            self.page.wait_for_timeout(5000)
            
            # Verify account creation
            if not self._verify_account_creation(first_name, last_name, middle_name):
                self.logger.error("Could not verify account creation")
                return False
                
            self.logger.info("Successfully created new account")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating new account: {str(e)}")
            self._take_screenshot("account-creation-error")
            return False
            
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
            # Wait for the page to fully load
            self.page.wait_for_load_state('networkidle')
            self.page.wait_for_timeout(5000)  # Additional wait for list to refresh
            
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
            if self.current_account_id is None:
                self.current_account_id = account_id
                self.logger.info(f"Stored created account ID: {account_id}")
            # If we're viewing an existing account, verify it matches the created account
            elif self.current_account_id != account_id:
                raise Exception(f"Account ID mismatch. Expected: {self.current_account_id}, Got: {account_id}")
            
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