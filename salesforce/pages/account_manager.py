from typing import Optional, Dict, List
import logging
import re
from ..base_page import BasePage
from playwright.sync_api import Page
from config import SALESFORCE_URL
import sys
import os
from salesforce.pages.accounts_page import AccountsPage

class AccountManager(BasePage):
    """Handles account-related operations in Salesforce."""
    
    def __init__(self, page: Page, debug_mode: bool = False):
        super().__init__(page, debug_mode)
        self.current_account_id = None
        self.accounts_page = AccountsPage(page, debug_mode)
        
    def navigate_to_accounts(self) -> bool:
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
            
    def search_account(self, account_name: str) -> int:
        """Search for an account by name and return the number of items found."""
        try:
            self.logger.info(f"Searching for account: {account_name}")
            
            # Wait for the search input to be visible
            self.logger.info("Waiting for search input...")
            search_input = self.page.wait_for_selector('input[placeholder="Search this list..."]', timeout=6000)
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
                self.page.wait_for_selector('div.slds-spinner_container', state='hidden', timeout=2000)
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
                            status_message = self.page.wait_for_selector(selector, timeout=4000)
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
            # Find all Save buttons
            save_buttons = self.page.locator('button').all()
            found = False
            for idx, button in enumerate(save_buttons):
                try:
                    text = button.text_content()
                    visible = button.is_visible()
                    enabled = button.is_enabled()
                    aria_label = button.get_attribute('aria-label')
                    class_attr = button.get_attribute('class')
                    logging.info(f"Button {idx}: text='{text}', visible={visible}, enabled={enabled}, aria-label={aria_label}, class={class_attr}")
                    if text and text.strip() == "Save" and enabled:
                        # Try normal click if visible
                        if visible:
                            button.scroll_into_view_if_needed()
                            self.page.wait_for_timeout(500)
                            button.click()
                            logging.info("Successfully clicked visible Save button")
                            found = True
                            break
                        else:
                            # Try JS click if not visible
                            self.page.evaluate('(btn) => btn.click()', button)
                            logging.info("Successfully clicked hidden Save button using JS")
                            found = True
                            break
                except Exception as e:
                    logging.info(f"Error inspecting/clicking button {idx}: {str(e)}")
            if not found:
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
            self.page.goto(f"{os.getenv('SALESFORCE_URL')}/lightning/r/Account/{self.current_account_id}/view")
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