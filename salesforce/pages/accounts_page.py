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
        """
        Prompt the user for confirmation in debug mode.
        Returns True if the user wants to continue, False otherwise.
        """
        if not self.debug_mode:
            return True
            
        while True:
            response = input(f"\n{message} (y/n): ").lower().strip()
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            print("Please enter 'y' or 'n'")

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

    def navigate_to_accounts(self):
        """Navigate to the Accounts page."""
        url = f"{SALESFORCE_URL}/lightning/o/Account/list?filterName=__Recent"
        logging.info(f"Navigating to Accounts page: {url}")
        
        try:
            logging.info("Starting page navigation...")
            self.page.goto(url)
            logging.info("Page navigation initiated")
            
            # Wait for the page to be ready
            logging.info("Waiting for page to load...")
            self.page.wait_for_load_state('domcontentloaded')
            logging.info("DOM content loaded")
            
            # Wait for the search input with a longer timeout
            logging.info("Waiting for search input...")
            search_input = self.page.wait_for_selector('input[placeholder="Search this list..."]', timeout=30000)
            if search_input:
                logging.info("Search input found")
            else:
                logging.error("Search input not found")
                raise Exception("Search input not found")
            
            # Additional check for the table
            logging.info("Checking for accounts table...")
            if self.page.locator('table[role="grid"]').is_visible():
                logging.info("Accounts table is visible")
            else:
                logging.info("Accounts table not visible yet")
            
            logging.info("Successfully navigated to Accounts page")
            
        except Exception as e:
            logging.error(f"Error navigating to Accounts page: {str(e)}")
            logging.info("Current URL: " + self.page.url)
            logging.info("Page title: " + self.page.title())
            # Take a screenshot for debugging
            try:
                self.page.screenshot(path="error-screenshot.png")
                logging.info("Error screenshot saved as error-screenshot.png")
            except Exception as screenshot_error:
                logging.error(f"Failed to take screenshot: {str(screenshot_error)}")
            raise

    def search_account(self, account_name: str) -> int:
        """Search for an account by name and return the number of items found."""
        try:
            logging.info(f"Searching for account: {account_name}")
            
            # Wait for the search input to be visible
            logging.info("Waiting for search input...")
            search_input = self.page.wait_for_selector('input[placeholder="Search this list..."]', timeout=60000)
            if not search_input:
                logging.error("Search input not found")
                return 0
                
            # Clear and fill the search input
            logging.info("Clearing search input...")
            search_input.fill("")
            logging.info("Entering account name...")
            search_input.fill(account_name)
            logging.info("Pressing Enter...")
            self.page.keyboard.press("Enter")
            
            # Wait for search results with a more specific check
            logging.info("Waiting for search results...")
            try:
                # First wait for the loading spinner to disappear
                self.page.wait_for_selector('div.slds-spinner_container', state='hidden', timeout=30000)
                logging.info("Loading spinner disappeared")
                
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
                                logging.info(f"Status message: {status_text}")
                                
                                # Extract the number of items
                                logging.info("Extracting the number of items...")
                                match = re.search(r'(\d+)\s+items?\s+•', status_text)
                                if match:
                                    item_count = int(match.group(1))
                                    logging.info(f"Found {item_count} items in search results")
                                    return item_count
                        except Exception as e:
                            logging.info(f"Selector {selector} failed: {str(e)}")
                            continue
                    
                    # If we get here, none of the selectors worked
                    logging.info("Could not find status message with any selector")
                    return 0
                    
                except Exception as e:
                    logging.info(f"Error checking status message: {str(e)}")
                    return 0
                
            except Exception as e:
                logging.info(f"Error waiting for search results: {str(e)}")
                return 0
            
        except Exception as e:
            logging.error(f"Error searching for account: {e}")
            return 0

    def click_account_name(self, account_name: str) -> bool:
        """Click on the account name in the search results."""
        try:
            # Try the specific selector first
            try:
                logging.info(f"Trying specific selector: a[title='{account_name}']")
                account_link = self.page.wait_for_selector(f"a[title='{account_name}']", timeout=5000)
                if account_link and account_link.is_visible():
                    # Scroll the element into view
                    account_link.scroll_into_view_if_needed()
                    # Wait a bit for any animations to complete
                    self.page.wait_for_timeout(1000)
                    # Click the element
                    account_link.click()
                    logging.info(f"Clicked account link using specific selector")
                    
                    # Wait for navigation to complete
                    self.page.wait_for_load_state("networkidle")
                    self.page.wait_for_timeout(2000)  # Additional wait for page to stabilize
                    
                    # Verify we're on the account view page
                    current_url = self.page.url
                    if '/view' not in current_url:
                        logging.error(f"Not on account view page. Current URL: {current_url}")
                        return False
                        
                    # Extract account ID from URL
                    account_id_match = re.search(r'/Account/([^/]+)/view', current_url)
                    if not account_id_match:
                        logging.error(f"Could not extract account ID from URL: {current_url}")
                        return False
                    
                    # Store the account ID
                    self.current_account_id = account_id_match.group(1)
                    logging.info(f"Stored account ID: {self.current_account_id}")
                    return True
            except Exception as e:
                logging.info(f"Specific selector failed: {str(e)}")
            
            # If specific selector fails, try other selectors
            selectors = [
                f'a[data-refid="recordId"][data-special-link="true"][title="{account_name}"]',
                f'td:first-child a[title="{account_name}"]',
                f'table[role="grid"] tr:first-child td:first-child a',
                f'table[role="grid"] tr:first-child a[data-refid="recordLink"]'
            ]
            
            for selector in selectors:
                try:
                    logging.info(f"Trying selector: {selector}")
                    account_link = self.page.wait_for_selector(selector, timeout=5000)
                    if account_link and account_link.is_visible():
                        # Scroll the element into view
                        account_link.scroll_into_view_if_needed()
                        # Wait a bit for any animations to complete
                        self.page.wait_for_timeout(1000)
                        # Click the element
                        account_link.click()
                        logging.info(f"Clicked account link using selector: {selector}")
                        
                        # Wait for navigation to complete
                        self.page.wait_for_load_state("networkidle")
                        self.page.wait_for_timeout(2000)  # Additional wait for page to stabilize
                        
                        # Verify we're on the account view page
                        current_url = self.page.url
                        if '/view' not in current_url:
                            logging.error(f"Not on account view page. Current URL: {current_url}")
                            continue
                            
                        # Extract account ID from URL
                        account_id_match = re.search(r'/Account/([^/]+)/view', current_url)
                        if not account_id_match:
                            logging.error(f"Could not extract account ID from URL: {current_url}")
                            continue
                            
                        account_id = account_id_match.group(1)
                        logging.info(f"Successfully navigated to account view page. Account ID: {account_id}")
                        return True
                except Exception as e:
                    logging.info(f"Selector {selector} failed: {str(e)}")
                    continue
            
            logging.error("Could not find or click account link with any selector")
            return False
            
        except Exception as e:
            logging.error(f"Error clicking account name: {str(e)}")
            return False

    def click_first_account(self):
        """Click on the first account in the search results."""
        try:
            # Wait for the table to be visible
            self.page.wait_for_selector('table.slds-table', timeout=10000)
            
            # Try multiple selectors for the account name cell
            selectors = [
                'table.slds-table tbody tr:first-child td:first-child a',
                'table.slds-table tbody tr:first-child td:first-child',
                'table.slds-table tbody tr:first-child a[data-refid="recordLink"]'
            ]
            
            for selector in selectors:
                try:
                    # Wait for the element to be visible and clickable
                    element = self.page.wait_for_selector(selector, timeout=5000)
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

    def navigate_to_files(self) -> int:
        """Navigate to the Files page of the current account. Assumes you are already on the account detail page.
        
        Returns:
            int: Number of files found in the account, or 0 if there was an error
        """
        logging.info("Attempting to navigate to Files tab...")
        
        # # Prompt user to continue
        # if not input("Ready to proceed with Files page. Continue? (y/n): ").lower().startswith('y'):
        #     print("Stopping as requested.")
        #     sys.exit(0)

        print("***Navigating to Files page...")

        try:
            # Try the most specific selector first: span[title="Files"]
            try:
                logging.info("Trying span[title='Files'] selector...")
                files_span = self.page.wait_for_selector('span[title="Files"]', timeout=5000)
                if files_span and files_span.is_visible():
                    # Try to click the parent element (often the tab itself)
                    parent = files_span.evaluate_handle('el => el.closest("a,button,li,div[role=\'tab\']")')
                    if parent:
                        parent.as_element().click()
                        logging.info("Clicked Files tab using span[title='Files'] parent.")
                        
                        # Wait for navigation and verify URL pattern
                        self.page.wait_for_load_state('networkidle')
                        current_url = self.page.url
                        logging.info(f"Current URL after clicking Files tab: {current_url}")
                        
                        # Verify URL pattern: Account/{account_id}/related/AttachedContentDocuments/view
                        if not re.match(r'.*Account/\w+/related/AttachedContentDocuments/view.*', current_url):
                            raise Exception(f"Not on Files page. Current URL: {current_url}")
                        
                        # Extract and store account ID from URL
                        account_id_match = re.search(r'/Account/(\w+)/related', current_url)
                        if account_id_match:
                            account_id = account_id_match.group(1)
                            logging.info(f"Extracted account ID from Files page URL: {account_id}")
                            self.current_account_id = account_id
                        
                        # Wait for and check the items count
                        try:
                            status_message = self.page.wait_for_selector('span[aria-label="Files"]', timeout=5000)
                            if status_message:
                                status_text = status_message.text_content()
                                logging.info(f"Files status message: {status_text}")
                                
                                # Extract the number of items
                                logging.info("Extracting the number of items...")
                                match = re.search(r'(\d+)\s+items?\s+•', status_text)
                                if match:
                                    item_count = int(match.group(1))
                                    logging.info(f"Found {item_count} files in the account")
                                    return item_count
                                else:
                                    logging.info("No items found or count not in expected format")
                        except Exception as e:
                            logging.info(f"Error checking files count: {str(e)}")
                        
                        return 0
                    else:
                        # If no parent found, try clicking the span directly
                        files_span.click()
                        logging.info("Clicked Files tab using span[title='Files'] directly.")
                        self.page.wait_for_selector('div.slds-tabs_default__content', timeout=30000)
                        logging.info("Files tab content loaded")
                        return 0
            except Exception as e:
                logging.info(f"span[title='Files'] selector failed: {str(e)}")

            # If we get here, none of the selectors worked
            logging.error("Could not find Files tab with any of the selectors")
            # Take a screenshot for debugging
            self.page.screenshot(path="files-tab-error.png")
            logging.info("Error screenshot saved as files-tab-error.png")
            raise Exception("Could not find or click Files tab")
        except Exception as e:
            logging.error(f"Error navigating to Files tab: {str(e)}")
            # Take a screenshot for debugging
            self.page.screenshot(path="files-tab-error.png")
            logging.info("Error screenshot saved as files-tab-error.png")
            raise

    def get_number_of_files(self) -> int:
        """Get the number of files in the account."""
        status_message = self.page.wait_for_selector('span[aria-label="Files"]', timeout=5000)
        if not status_message:
            print("Could not find files status message")
            return 0
            
        text = status_message.text_content()
        print(f"***Number of files in get_number_of_files: {text}")
        match = re.search(r'(\d+)\s+items?\s+•', text)
        return int(match.group(1)) if match else 0
    

    def add_files(self):
        """Click the Add Files button and then the Upload Files button in the dialog."""
        try:
            # Click Add Files button using the specific selector
            add_files_button = self.page.wait_for_selector('div[title="Add Files"]', timeout=5000)
            if not add_files_button:
                raise Exception("Add Files button not found")
            add_files_button.click()
            logging.info("Clicked Add Files button")

            # Wait for and click Upload Files button in the dialog
            upload_files_button = self.page.wait_for_selector('button:has-text("Upload Files")', timeout=5000)
            if not upload_files_button:
                raise Exception("Upload Files button not found in dialog")
            upload_files_button.click()
            logging.info("Clicked Upload Files button in dialog")

            # Wait for the file input to be visible
            self.page.wait_for_selector('input[type="file"]', timeout=5000)
            logging.info("File input is visible")
        except Exception as e:
            logging.error(f"Error in add_files: {str(e)}")
            self.page.screenshot(path="add-files-error.png")
            raise

    def search_file(self, file_pattern: str) -> bool:
        """Search for a file using a pattern."""
        self.page.fill('input[placeholder="Search Files..."]', file_pattern)
        self.page.press('input[placeholder="Search Files..."]', 'Enter')
        # Wait for search results
        self.page.wait_for_selector('table[role="grid"]')
        # Check if any results are found
        return self.page.locator('table[role="grid"] >> tr').count() > 0

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

    def create_new_account(self, first_name: str, last_name: str, middle_name: Optional[str] = None, account_info: Optional[Dict[str, str]] = None):
        """
        Create a new account with the given information.
        Args:
            first_name: First name of the account holder
            last_name: Last name of the account holder
            middle_name: Middle name of the account holder (optional)
            account_info: Dictionary containing additional account information (optional)
        """
        try:
            # Click New button with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logging.info(f"Attempting to click New button (attempt {attempt + 1}/{max_retries})")
                    # Try different selectors for the New button
                    selectors = [
                        '(//div[@title="New"])[1]',
                        'button:has-text("New")',
                        'button.slds-button:has-text("New")',
                        'button[title="New"]',
                        '//button[contains(text(), "New")]'
                    ]
                    
                    for selector in selectors:
                        try:
                            logging.info(f"Trying selector: {selector}")
                            self.page.wait_for_selector(selector, timeout=10000)
                            self.page.click(selector)
                            logging.info("Successfully clicked New button")
                            break
                        except Exception as e:
                            logging.info(f"Selector {selector} failed: {str(e)}")
                            continue
                    else:
                        raise Exception("No New button selectors worked")
                    
                    # If we get here, the click was successful
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logging.warning(f"Failed to click New button: {str(e)}, retrying...")
                    self.page.wait_for_timeout(2000)  # Wait 2 seconds before retry

            # Wait for the record type selection modal
            logging.info("Waiting for record type selection modal...")
            self.page.wait_for_selector('div.slds-modal__content', timeout=30000)
            
            # Log the modal content for debugging
            modal_content = self.page.locator('div.slds-modal__content').text_content()
            logging.info(f"Modal content: {modal_content}")
            
            # Try different selectors for the Client radio button
            logging.info("Attempting to select Client record type...")
            selectors = [
                'input[type="radio"]',  # First radio button
                '.slds-modal__content input[type="radio"]',  # Radio button in modal
                '.slds-modal__content label:contains("Client") + input[type="radio"]',  # Radio button next to Client label
                '.slds-modal__content input[type="radio"]:first-of-type'  # First radio button in modal
            ]
            
            for selector in selectors:
                try:
                    logging.info(f"Trying selector: {selector}")
                    radio = self.page.wait_for_selector(selector, timeout=5000)
                    if radio:
                        logging.info(f"Found radio button with selector: {selector}")
                        # Use JavaScript to click the radio button
                        self.page.evaluate("""(selector) => {
                            const radio = document.querySelector(selector);
                            if (radio) {
                                radio.click();
                                radio.checked = true;
                                // Dispatch change event
                                radio.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                        }""", selector)
                        break
                except Exception as e:
                    logging.info(f"Selector {selector} failed: {str(e)}")
                    continue
            else:
                raise Exception("Could not find Client radio button")
            
            # Click Next button
            logging.info("Clicking Next button...")
            next_button = self.page.wait_for_selector('button:has-text("Next")', timeout=10000)
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
            
            # Wait for the new account form to appear
            logging.info("Waiting for new account form...")
            self.page.wait_for_selector('div.slds-modal__content', timeout=30000)
            
            # Log the form content for debugging
            form_content = self.page.content()
            with open("form-content.html", "w") as f:
                f.write(form_content)
            logging.info("Form content saved as form-content.html")
            
            # Wait for and fill First Name
            logging.info("Attempting to fill First Name...")
            first_name_selectors = [
                '//label[contains(text(), "First Name")]/following-sibling::input',
                '//input[contains(@placeholder, "First Name")]',
                'input[name="firstName"]',
                'input[id*="FirstName"]',
                'input[aria-label="First Name"]',
                'input[data-field="FirstName"]',
                'input[data-id="firstName"]',
                'input[data-element-id="firstName"]',
                'input'
            ]
            
            first_name_filled = False
            for selector in first_name_selectors:
                try:
                    logging.info(f"Trying First Name selector: {selector}")
                    element = self.page.wait_for_selector(selector, timeout=5000)
                    if element and element.is_visible():
                        logging.info(f"Found First Name field with selector: {selector}")
                        element.fill(first_name)
                        first_name_filled = True
                        logging.info(f"Successfully filled First Name with: {first_name}")
                        break
                except Exception as e:
                    logging.info(f"First Name selector {selector} failed: {str(e)}")
            
            if not first_name_filled:
                logging.error("Could not fill First Name field")
                raise Exception("Could not fill First Name field")
            
            # Wait for and fill Last Name
            logging.info("Attempting to fill Last Name...")
            last_name_selectors = [
                '//label[contains(text(), "Last Name")]/following-sibling::input',
                '//input[contains(@placeholder, "Last Name")]',
                'input[name="lastName"]',
                'input[id*="LastName"]',
                'input[aria-label="Last Name"]',
                'input[data-field="LastName"]',
                'input[data-id="lastName"]',
                'input[data-element-id="lastName"]',
                'input'
            ]
            
            last_name_filled = False
            for selector in last_name_selectors:
                try:
                    logging.info(f"Trying Last Name selector: {selector}")
                    element = self.page.wait_for_selector(selector, timeout=5000)
                    if element and element.is_visible():
                        logging.info(f"Found Last Name field with selector: {selector}")
                        element.fill(last_name)
                        last_name_filled = True
                        logging.info(f"Successfully filled Last Name with: {last_name}")
                        break
                except Exception as e:
                    logging.info(f"Last Name selector {selector} failed: {str(e)}")
            
            if not last_name_filled:
                logging.error("Could not fill Last Name field")
                raise Exception("Could not fill Last Name field")
            
            # Fill Middle Name if provided
            if middle_name:
                logging.info("Attempting to fill Middle Name...")
                middle_name_selectors = [
                    '//label[contains(text(), "Middle Name")]/following-sibling::input',
                    '//input[contains(@placeholder, "Middle Name")]',
                    'input[name="middleName"]',
                    'input[id*="MiddleName"]',
                    'input[aria-label="Middle Name"]',
                    'input[data-field="MiddleName"]',
                    'input[data-id="middleName"]',
                    'input[data-element-id="middleName"]',
                    'input'
                ]
                
                middle_name_filled = False
                for selector in middle_name_selectors:
                    try:
                        logging.info(f"Trying Middle Name selector: {selector}")
                        element = self.page.wait_for_selector(selector, timeout=5000)
                        if element and element.is_visible():
                            logging.info(f"Found Middle Name field with selector: {selector}")
                            element.fill(middle_name)
                            middle_name_filled = True
                            logging.info(f"Successfully filled Middle Name with: {middle_name}")
                            break
                    except Exception as e:
                        logging.info(f"Middle Name selector {selector} failed: {str(e)}")
                
                if not middle_name_filled:
                    logging.warning("Could not fill Middle Name field, continuing without it")

            # Get available form fields
            available_fields = self._get_available_form_fields()
            logging.info(f"Available form fields: {available_fields}")
            
            # Fill in additional information if available
            if account_info:
                logging.info("Filling in additional information...")
                
                # Only handle phone number for now
                if 'Phone' in available_fields and 'phone' in account_info:
                    try:
                        phone_selectors = [
                            '#input-226',  # Dynamic selector for phone input
                            '#input-251',  # Dynamic selector for phone input
                            'input[name="Phone"]',  # Generic selector for phone input
                            '#input-300',  # Previous static selector
                            '//label[contains(text(), "Phone")]/following-sibling::input',
                            '//input[contains(@placeholder, "Phone")]',
                            'input[type="tel"]',
                            'input[name="phone"]',
                            'input[id*="Phone"]',
                            'input[aria-label="Phone"]',
                            'input[data-field="Phone"]',
                            'input[data-id="phone"]',
                            'input[data-element-id="phone"]'
                        ]
                        phone_filled = False
                        for selector in phone_selectors:
                            try:
                                logging.info(f"Trying Phone selector: {selector}")
                                element = self.page.wait_for_selector(selector, timeout=5000)
                                if element and element.is_visible():
                                    logging.info(f"Found Phone field with selector: {selector}")
                                    element.fill(account_info['phone'])
                                    phone_filled = True
                                    logging.info(f"Successfully filled Phone with: {account_info['phone']}")
                                    break
                            except Exception as e:
                                logging.info(f"Phone selector {selector} failed: {str(e)}")
                        if not phone_filled:
                            logging.warning("Could not fill Phone field. Saving form HTML for inspection.")
                            with open("phone-field-form.html", "w") as f:
                                f.write(self.page.content())
                            logging.info("Form HTML saved as phone-field-form.html")
                    except Exception as e:
                        logging.warning(f"Error filling phone number: {str(e)}")

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

            # Wait for navigation or toast message
            try:
                # First, look for a Salesforce toast message
                try:
                    toast = self.page.wait_for_selector('div.slds-notify_toast, div.slds-notify--toast', timeout=5000)
                    if toast and toast.is_visible():
                        toast_text = toast.text_content()
                        logging.info(f"Found toast message after Save: {toast_text}")
                        if 'success' in toast_text.lower() or 'was created' in toast_text.lower():
                            logging.info("Successfully confirmed account creation by toast message.")
                                
                            try:
                                # Wait for the page to fully load
                                self.page.wait_for_load_state('networkidle')
                                self.page.wait_for_timeout(5000)  # Additional wait for list to refresh
                                
                                # Verify URL contains /view and extract account ID
                                current_url = self.page.url
                                print(f"***Current URL: {current_url}")
                                if '/view' not in current_url:
                                    raise Exception(f"Not on account view page. Current URL: {current_url}")
                                
                                # Extract account ID from URL
                                account_id_match = re.search(r'/Account/([^/]+)/view', current_url)
                                if not account_id_match:
                                    raise Exception(f"Could not extract account ID from URL: {current_url}")
                                
                                account_id = account_id_match.group(1)
                                logging.info(f"Extracted account ID from URL: {account_id}")
                                
                                # If this is after account creation, store the ID
                                if self.current_account_id is None:
                                    self.current_account_id = account_id
                                    logging.info(f"Stored created account ID: {account_id}")
                                # If we're viewing an existing account, verify it matches the created account
                                elif self.current_account_id != account_id:
                                    raise Exception(f"Account ID mismatch. Expected: {self.current_account_id}, Got: {account_id}")
                                
                                logging.info("Successfully verified we're on the correct account view page")
                                return True
                            except Exception as e:
                                logging.error(f"Failed to verify account view page: {str(e)}")
                                self.page.screenshot(path="account-view-verification-error.png")
                                raise Exception("Could not verify we're on the account view page")
                            # except Exception as e:
                            #     logging.error(f"Error clicking account link: {str(e)}")
                            #     self.page.screenshot(path="account-link-click-error.png")
                            #     raise Exception("Could not click on account link")
                except Exception as e:
                    logging.info(f"No toast message found: {str(e)}")
                # Fallback: Try to find the Account Name on the page
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
                            logging.info(f"Account name '{account_name}' is visible on the page (selector: {selector})")
                            name_found = True
                            break
                    except Exception as e:
                        logging.info(f"Account name selector {selector} failed: {str(e)}")
                if name_found:
                    logging.info("Account name is visible, clicking the visible element to go to detail page.")
                    # Click the first visible account name element directly
                    for selector in name_selectors:
                        try:
                            locator = self.page.locator(selector).first
                            if locator.is_visible():
                                locator.click()
                                logging.info(f"Clicked on account name using selector: {selector}")
                                self.page.wait_for_load_state('domcontentloaded')
                                self.page.wait_for_selector('h1, h1.slds-page-header__title, [data-aura-class*="pageHeader"]', timeout=30000)
                                return True
                        except Exception as e:
                            logging.info(f"Failed to click account name with selector {selector}: {str(e)}")
                    logging.error("Could not click any visible account name element.")
                    raise Exception("Could not click any visible account name element.")
                else:
                    logging.error(f"Could not find account name '{account_name}' on the page after Save.")
                    self.page.screenshot(path="account-name-not-found.png")
                    raise Exception("Could not confirm account was saved: Account Name not found")
            except Exception as e:
                logging.error(f"Error confirming account save: {str(e)}")
                self.page.screenshot(path="save-confirmation-error.png")
                raise Exception("Could not confirm account was saved")

        except Exception as e:
            logging.error(f"Error creating account: {e}")
            # Take a screenshot for debugging
            try:
                self.page.screenshot(path="create-account-error.png")
                logging.info("Error screenshot saved as create-account-error.png")
            except Exception as screenshot_error:
                logging.error(f"Failed to take screenshot: {str(screenshot_error)}")
            raise

    def upload_files(self, file_paths: List[str]) -> bool:
        """
        Upload multiple files to Salesforce.
        Returns True if upload was successful, False otherwise.
        """
        try:
            # Show files in debug mode
            file_paths = self._debug_show_files(file_paths)
            if not file_paths:
                logging.info("User chose to skip file upload")
                return False

            # Try multiple selectors for Add Files button
            add_files_selectors = [
                'div[title="Add Files"]',
                'button:has-text("Add Files")',
                'button[title="Add Files"]',
                'div.slds-button:has-text("Add Files")',
                'button.slds-button:has-text("Add Files")',
                '//button[contains(text(), "Add Files")]',
                '//div[contains(text(), "Add Files")]'
            ]

            add_files_button = None
            for selector in add_files_selectors:
                try:
                    add_files_button = self.page.wait_for_selector(selector, timeout=5000)
                    if add_files_button and add_files_button.is_visible():
                        logging.info(f"Found Add Files button with selector: {selector}")
                        break
                except Exception as e:
                    logging.debug(f"Selector {selector} failed: {str(e)}")
                    continue

            if not add_files_button:
                raise Exception("Could not find Add Files button with any selector")

            # Click Add Files button
            add_files_button.click()
            logging.info("Clicked Add Files button")

            # Wait for and click Upload Files button in the dialog
            upload_files_button = self.page.wait_for_selector('button:has-text("Upload Files")', timeout=5000)
            if not upload_files_button:
                raise Exception("Upload Files button not found in dialog")
            upload_files_button.click()
            logging.info("Clicked Upload Files button in dialog")

            # Wait for the file input to be visible
            file_input = self.page.wait_for_selector('input[type="file"]', timeout=5000)
            if not file_input:
                raise Exception("File input not found")

            # Set the files to upload
            file_input.set_input_files(file_paths)
            logging.info(f"Set {len(file_paths)} files to upload")

            # Wait for upload to complete with retries
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    # Wait for upload progress indicator
                    self.page.wait_for_selector('div.progress-indicator', timeout=30000, state='visible')
                    logging.info("Upload progress indicator visible")

                    # Wait for progress indicator to disappear
                    self.page.wait_for_selector('div.progress-indicator', timeout=30000, state='hidden')
                    logging.info("Upload progress indicator disappeared")

                    # Wait for success message
                    success_message = self.page.wait_for_selector('div.slds-notify--success', timeout=10000)
                    if success_message:
                        logging.info("Upload success message received")
                        return True

                except Exception as e:
                    retry_count += 1
                    logging.warning(f"Upload attempt {retry_count} failed: {str(e)}")
                    if retry_count < max_retries:
                        logging.info("Retrying upload...")
                        time.sleep(2)  # Wait before retry
                    else:
                        raise Exception(f"Upload failed after {max_retries} attempts")

            return False

        except Exception as e:
            logging.error(f"Error uploading files: {str(e)}")
            # Take a screenshot for debugging
            try:
                self.page.screenshot(path="upload-error.png")
                logging.info("Error screenshot saved as upload-error.png")
            except Exception as screenshot_error:
                logging.error(f"Failed to take screenshot: {str(screenshot_error)}")
            return False

    def verify_files_uploaded(self, file_names: List[str]) -> bool:
        """
        Verify that all files were uploaded successfully.
        Args:
            file_names: List of file names to check
        Returns:
            bool: True if all files are found, False otherwise
        """
        try:
            # Wait for the files list to be visible
            self.page.wait_for_selector('div.slds-scrollable_y', timeout=10000)
            logging.info("Files list is visible")

            # Wait a moment for the files to appear
            time.sleep(2)

            # Get the number of items
            items_text = self.page.locator('div.slds-text-body_small').first.text_content()
            logging.info(f"Items text: {items_text}")

            # Extract the number of items
            match = re.search(r'(\d+)\s+items?\s+•', items_text)
            if not match:
                logging.error("Could not find number of items in the text")
                return False

            num_items = int(match.group(1))
            logging.info(f"Found {num_items} items in the list")

            # Verify each file
            for file_name in file_names:
                # Try to find the file with pattern matching
                # Remove any date prefix from the file name for searching
                base_name = re.sub(r'^\d{8}\s+', '', file_name)
                search_pattern = f"*{base_name}"

                # Search for the file
                self.page.fill('input[placeholder="Search Files..."]', search_pattern)
                self.page.press('input[placeholder="Search Files..."]', 'Enter')

                # Wait for search results
                self.page.wait_for_selector('table[role="grid"]', timeout=5000)

                # Check if any results are found
                results = self.page.locator('table[role="grid"] >> tr').count()
                if results == 0:
                    logging.error(f"File not found: {file_name}")
                    return False

                logging.info(f"Found file: {file_name}")

            return True

        except Exception as e:
            logging.error(f"Error verifying files: {str(e)}")
            # Take a screenshot for debugging
            try:
                self.page.screenshot(path="verify-files-error.png")
                logging.info("Error screenshot saved as verify-files-error.png")
            except Exception as screenshot_error:
                logging.error(f"Failed to take screenshot: {str(screenshot_error)}")
            return False

    def get_account_id(self) -> str:
        """
        Get the ID of the current account being viewed.
        
        Returns:
            str: The account ID.
            
        Raises:
            Exception: If the account ID is not available.
        """
        if self.current_account_id:
            print(f"*****Current account ID: {self.current_account_id}")
            return self.current_account_id
            
        # Try to extract from current URL if not stored
        current_url = self.page.url
        account_id_match = re.search(r'/Account/([^/]+)/view', current_url)
        if account_id_match:
            self.current_account_id = account_id_match.group(1)
            return self.current_account_id
            
        raise Exception("No account ID available.")

    def navigate_back_to_account_page(self):
        """Navigate back to the original account page using the current account ID."""
        print("\nNavigating back to account page...")
        account_id = self.get_account_id()
        if account_id:
            self.page.goto(f"{os.getenv('SALESFORCE_URL')}/lightning/r/Account/{account_id}/view")
            self.page.wait_for_load_state('networkidle')
            print("Back on account page")
        else:
            print("Error: No account ID available to navigate back to account page.")

    def navigate_to_account_by_id(self, account_id: str):
        """Navigate to the account page using the provided account ID."""
        print(f"\nNavigating to account page for ID: {account_id}...")
        self.page.goto(f"{os.getenv('SALESFORCE_URL')}/lightning/r/Account/{account_id}/view")
        self.page.wait_for_load_state('networkidle')
        print("Successfully navigated to account page.")

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
            print(f"\nSearching for account: {account_name}")
            self.navigate_to_accounts()
            self.search_account(account_name)
            if self.click_account_name(account_name):
                print(f"Successfully navigated to account view page for: {account_name}")
            else:
                print(f"Failed to navigate to account view page for: {account_name}") 