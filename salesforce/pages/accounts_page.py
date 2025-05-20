from playwright.sync_api import Page, expect
from typing import Optional, List, Dict
import re
import os
import time
import logging
from config import SALESFORCE_URL

class AccountsPage:
    def __init__(self, page: Page, debug_mode: bool = False):
        self.page = page
        self.debug_mode = debug_mode
        self.last_created_account_id = None  # Store the ID of the last created account
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

    def search_account(self, account_name: str) -> bool:
        """Search for an account by name."""
        try:
            logging.info(f"Searching for account: {account_name}")
            
            # Wait for the search input to be visible
            logging.info("Waiting for search input...")
            search_input = self.page.wait_for_selector('input[placeholder="Search this list..."]', timeout=60000)
            if not search_input:
                logging.error("Search input not found")
                return False
                
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
                
                # Check for results in multiple ways
                # 1. Check for the account name directly
                account_selector = f'a[data-refid="recordId"][data-special-link="true"][title="{account_name}"]'
                try:
                    account_element = self.page.wait_for_selector(account_selector, timeout=5000)
                    if account_element and account_element.is_visible():
                        logging.info(f"Found account name '{account_name}' in search results")
                        return True
                except Exception as e:
                    logging.info(f"Account name not found with specific selector: {str(e)}")
                
                # 2. Check for the table with results
                try:
                    table = self.page.wait_for_selector('table[role="grid"]', timeout=5000)
                    if table and table.is_visible():
                        # Check if the account name is in the table
                        account_in_table = self.page.locator(f'table[role="grid"] >> text="{account_name}"').is_visible()
                        if account_in_table:
                            logging.info(f"Found account name '{account_name}' in table")
                            return True
                except Exception as e:
                    logging.info(f"Table check failed: {str(e)}")
                
                # 3. Check for any element containing the account name
                try:
                    any_element = self.page.wait_for_selector(f':text("{account_name}")', timeout=5000)
                    if any_element and any_element.is_visible():
                        logging.info(f"Found account name '{account_name}' in page")
                        return True
                except Exception as e:
                    logging.info(f"General text search failed: {str(e)}")
                
                logging.info("No results found for account")
                return False
                
            except Exception as e:
                logging.info(f"Error waiting for search results: {str(e)}")
                return False
            
        except Exception as e:
            logging.error(f"Error searching for account: {e}")
            return False

    def click_account_name(self, account_name: str) -> bool:
        """Click on the account name in the search results."""
        try:
            # Wait for the account name link to be visible
            # Using a more specific selector that matches the exact element structure
            account_link = self.page.wait_for_selector(
                f'a[data-refid="recordId"][data-special-link="true"][title="{account_name}"]',
                state="visible",
                timeout=10000
            )
            
            if not account_link:
                print(f"Could not find account link for: {account_name}")
                return False
            
            # Click the account name
            account_link.click()
            
            # Wait for navigation to complete
            self.page.wait_for_load_state("networkidle")
            
            # Verify we're on the account view page
            if not self.page.url.endswith("/view"):
                print("Failed to navigate to account view page")
                return False
            
            return True
            
        except Exception as e:
            print(f"Error clicking account name: {str(e)}")
            return False

    def click_first_account(self):
        """Click on the first account in the search results."""
        try:
            logging.info("Attempting to click first account in search results...")
            
            # Wait for the table to be visible
            logging.info("Waiting for accounts table...")
            self.page.wait_for_selector('table[role="grid"]', timeout=30000)
            
            # Try multiple selectors for the account name cell
            selectors = [
                'table[role="grid"] >> tr >> td:first-child >> a',
                'table[role="grid"] >> tr >> td:first-child >> span >> a',
                'table[role="grid"] >> tr >> td:first-child >> div >> a',
                'table[role="grid"] >> tr >> td:first-child >> div >> span >> a'
            ]
            
            for selector in selectors:
                try:
                    logging.info(f"Trying selector: {selector}")
                    element = self.page.wait_for_selector(selector, timeout=5000)
                    if element and element.is_visible():
                        # Log element details for debugging
                        logging.info(f"Found element with selector {selector}:")
                        logging.info(f"Tag name: {element.evaluate('el => el.tagName')}")
                        logging.info(f"Class: {element.evaluate('el => el.className')}")
                        logging.info(f"Text content: {element.text_content()}")
                        
                        # Click the element
                        element.click()
                        logging.info(f"Successfully clicked account using selector: {selector}")
                        
                        # Wait for navigation to complete
                        self.page.wait_for_load_state('networkidle', timeout=30000)
                        logging.info("Navigation to account details completed")
                        return
                except Exception as e:
                    logging.info(f"Selector {selector} failed: {str(e)}")
                    continue
            
            # If we get here, none of the selectors worked
            logging.error("Could not find clickable account element with any of the selectors")
            # Take a screenshot for debugging
            self.page.screenshot(path="account-click-error.png")
            logging.info("Error screenshot saved as account-click-error.png")
            raise Exception("Could not find clickable account element")
            
        except Exception as e:
            logging.error(f"Error clicking first account: {str(e)}")
            raise

    def navigate_to_files(self):
        """Navigate to the Files tab of the current account. Assumes you are already on the account detail page."""
        logging.info("Attempting to navigate to Files tab...")
        try:
            # Wait for the tab bar to be visible
            logging.info("Waiting for tab bar...")
            self.page.wait_for_selector('div.slds-tabs_default', timeout=30000)
            # Try different selectors for the Files tab
            selectors = [
                'div.slds-tabs_default__nav >> text=Files',
                'div.slds-tabs_default__nav >> a:has-text("Files")',
                'div.slds-tabs_default__nav >> button:has-text("Files")',
                'div.slds-tabs_default__nav >> div[role="tab"]:has-text("Files")',
                'div.slds-tabs_default__nav >> li[role="presentation"]:has-text("Files")',
                'div.slds-tabs_default__nav >> span:has-text("Files")',
                'div.slds-tabs_default__nav >> a:has-text("Files")',
                'div.slds-tabs_default__nav >> button:has-text("Files")',
                'div.slds-tabs_default__nav >> div[role="tab"] >> span:has-text("Files")',
                'div.slds-tabs_default__nav >> div[role="tab"] >> a:has-text("Files")',
                'div.slds-tabs_default__nav >> div[role="tab"] >> button:has-text("Files")'
            ]
            # Log the current page content for debugging
            logging.info("Current page content:")
            logging.info(self.page.content())
            for selector in selectors:
                try:
                    logging.info(f"Trying Files tab selector: {selector}")
                    element = self.page.wait_for_selector(selector, timeout=5000)
                    if element and element.is_visible():
                        # Log element details for debugging
                        logging.info(f"Found element with selector {selector}:")
                        logging.info(f"Tag name: {element.evaluate('el => el.tagName')}")
                        logging.info(f"Class: {element.evaluate('el => el.className')}")
                        logging.info(f"Text content: {element.text_content()}")
                        # Click the element
                        element.click()
                        logging.info(f"Successfully clicked Files tab using selector: {selector}")
                        # Wait for the Files tab content to load
                        self.page.wait_for_selector('div.slds-tabs_default__content', timeout=30000)
                        logging.info("Files tab content loaded")
                        return
                except Exception as e:
                    logging.info(f"Selector {selector} failed: {str(e)}")
                    continue
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
        text = self.page.locator('text=items').first.text_content()
        match = re.search(r'(\d+)\s+items', text)
        return int(match.group(1)) if match else 0

    def add_files(self):
        """Click the Add Files button and then the Upload Files button in the dialog."""
        try:
            # Click Add Files button
            add_files_button = self.page.wait_for_selector('button:has-text("Add Files")', timeout=5000)
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
                            # After successful save, navigate back to accounts list and search for the account
                            logging.info("Navigating back to accounts list...")
                            self.navigate_to_accounts()
                            
                            # Wait for the page to fully load
                            self.page.wait_for_load_state('networkidle')
                            self.page.wait_for_timeout(5000)  # Additional wait for list to refresh
                            
                            # Always search for the account by name
                            account_name = f"{first_name} {last_name}"
                            logging.info(f"Searching for newly created account: {account_name}")
                            found = self.search_account(account_name)
                            if not found:
                                raise Exception(f"Could not find newly created account '{account_name}' in list.")
                            
                            # Wait for the search results table with a longer timeout
                            self.page.wait_for_selector("table[role='grid']", timeout=20000)
                            self.page.wait_for_timeout(2000)  # Additional wait for table to populate
                            
                            # Verify that there is at least one result
                            rows = self.page.query_selector_all("table[role='grid'] tr")
                            data_rows = [row for row in rows if row.query_selector('td')]
                            if len(data_rows) < 1:
                                raise Exception(f"Expected at least 1 result row, found {len(data_rows)}. Aborting.")
                            
                            # Click on the first item
                            first_cell = data_rows[0].query_selector("td:first-child a, td:first-child span, td:first-child")
                            if first_cell:
                                first_cell.click()
                                logging.info("Clicked on the first account in search results to go to detail page")
                                
                                # Wait for page load
                                self.page.wait_for_load_state('domcontentloaded')
                                
                                # Verify we're on the account view page by checking multiple indicators
                                try:
                                    # Wait for the account header
                                    self.page.wait_for_selector('h1.slds-page-header__title, [data-aura-class*="pageHeader"]', timeout=30000)
                                    
                                    # Verify URL contains /view and extract account ID
                                    current_url = self.page.url
                                    if '/view' not in current_url:
                                        raise Exception(f"Not on account view page. Current URL: {current_url}")
                                    
                                    # Extract account ID from URL
                                    account_id_match = re.search(r'/Account/([^/]+)/view', current_url)
                                    if not account_id_match:
                                        raise Exception(f"Could not extract account ID from URL: {current_url}")
                                    
                                    account_id = account_id_match.group(1)
                                    logging.info(f"Extracted account ID from URL: {account_id}")
                                    
                                    # If this is after account creation, store the ID
                                    if self.last_created_account_id is None:
                                        self.last_created_account_id = account_id
                                        logging.info(f"Stored created account ID: {account_id}")
                                    # If we're viewing an existing account, verify it matches the created account
                                    elif self.last_created_account_id != account_id:
                                        raise Exception(f"Account ID mismatch. Expected: {self.last_created_account_id}, Got: {account_id}")
                                    
                                    # Verify we have the standard Salesforce account view elements
                                    view_selectors = [
                                        'div.slds-tabs_default',  # Tab bar
                                        'div.slds-page-header__detail-row',  # Account details row
                                        'div.slds-page-header__meta-text'  # Account metadata
                                    ]
                                    
                                    for selector in view_selectors:
                                        if not self.page.locator(selector).is_visible():
                                            raise Exception(f"Account view element not found: {selector}")
                                    
                                    logging.info("Successfully verified we're on the correct account view page")
                                    return True
                                except Exception as e:
                                    logging.error(f"Failed to verify account view page: {str(e)}")
                                    self.page.screenshot(path="account-view-verification-error.png")
                                    raise Exception("Could not verify we're on the account view page")
                            else:
                                logging.error("Could not find clickable cell in the result row")
                                raise Exception("Could not find clickable cell in the result row")
                except Exception as e:
                    logging.info(f"No toast message found: {str(e)}")
                # Fallback: Try to find the Account Name on the page
                account_name = f"{first_name} {last_name}"
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

            # Click Add Files button
            self.add_files()

            # Wait for the file input to be visible
            file_input = self.page.locator('input[type="file"]')
            expect(file_input).to_be_visible()

            # Set the files to upload
            file_input.set_input_files(file_paths)

            # Wait for upload to complete
            self._wait_for_upload_completion()

            return True
        except Exception as e:
            logging.error(f"Error uploading files: {e}")
            return False

    def _wait_for_upload_completion(self, timeout: int = 300):
        """
        Wait for file upload to complete.
        Args:
            timeout: Maximum time to wait in seconds
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check for upload progress indicator
            progress_visible = self.page.locator('text=Uploading...').is_visible()
            if not progress_visible:
                # Check for success message
                success_visible = self.page.locator('text=Upload Complete').is_visible()
                if success_visible:
                    return
            time.sleep(1)
        raise TimeoutError("File upload timed out")

    def verify_files_uploaded(self, file_names: List[str]) -> bool:
        """
        Verify that all files were uploaded successfully.
        Args:
            file_names: List of file names to check
        Returns:
            bool: True if all files are found, False otherwise
        """
        try:
            for file_name in file_names:
                # Search for the file
                if not self.search_file(file_name):
                    print(f"File not found: {file_name}")
                    return False
            return True
        except Exception as e:
            print(f"Error verifying files: {e}")
            return False 