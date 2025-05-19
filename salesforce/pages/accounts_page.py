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
            
            # Check if we need to log in
            if "login.salesforce.com" in self.page.url:
                logging.info("Detected login page, waiting for login to complete...")
                self.page.wait_for_url(lambda url: "login.salesforce.com" not in url, timeout=60000)
                logging.info("Login completed, redirecting to Accounts page...")
                self.page.goto(url)
            
            # Wait for the page to be ready
            logging.info("Waiting for page to load...")
            
            # First wait for the page to be in a stable state
            self.page.wait_for_load_state('domcontentloaded')
            logging.info("DOM content loaded")
            
            # Try to find any of these elements that indicate the page is loaded
            selectors = [
                'div.slds-template_default',
                'div.slds-page-header',
                'div.slds-global-header',
                'div.slds-global-navigation',
                'div.slds-scrollable',
                'div.slds-page-header__title'
            ]
            
            logging.info("Checking for page elements...")
            found_selector = False
            for selector in selectors:
                try:
                    logging.info(f"Trying selector: {selector}")
                    element = self.page.wait_for_selector(selector, timeout=10000)
                    if element:
                        logging.info(f"Found selector: {selector}")
                        found_selector = True
                        break
                except Exception as e:
                    logging.info(f"Selector {selector} not found: {str(e)}")
                    continue
            
            if not found_selector:
                logging.warning("No standard selectors found, checking page content...")
                # Take a screenshot for debugging
                self.page.screenshot(path="page-state.png")
                logging.info("Page state screenshot saved as page-state.png")
                
                # Check if we can find any Salesforce-related content
                page_content = self.page.content()
                if "salesforce" in page_content.lower():
                    logging.info("Found Salesforce content in page")
                else:
                    logging.warning("No Salesforce content found in page")
            
            # Wait for the search input with a longer timeout
            logging.info("Waiting for search input...")
            try:
                search_input = self.page.wait_for_selector('input[placeholder="Search this list..."]', timeout=30000)
                if search_input:
                    logging.info("Search input found")
                else:
                    logging.error("Search input not found")
                    raise Exception("Search input not found")
            except Exception as e:
                logging.error(f"Error waiting for search input: {str(e)}")
                # Take a screenshot for debugging
                self.page.screenshot(path="search-input-error.png")
                logging.info("Error screenshot saved as search-input-error.png")
                raise
            
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
                # First wait for the loading spinner to disappear (short timeout)
                self.page.wait_for_selector('div.slds-spinner_container', state='hidden', timeout=5000)
                logging.info("Loading spinner disappeared")
                
                # Then wait for either results or no results message (short timeout)
                self.page.wait_for_selector('table[role="grid"], div.slds-text-align_center', timeout=5000)
                logging.info("Search results loaded")
                
                # Check if we found any results
                has_results = self.page.locator('table[role="grid"]').is_visible()
                logging.info(f"Search results found: {has_results}")
                return has_results
                
            except Exception as e:
                logging.info(f"No results found or timeout: {str(e)}")
                return False
            
        except Exception as e:
            logging.error(f"Error searching for account: {e}")
            return False

    def click_first_account(self):
        """Click on the first account in the search results."""
        self.page.click('table[role="grid"] >> tr >> td:first-child')

    def navigate_to_files(self):
        """Navigate to the Files tab of the current account."""
        logging.info("Attempting to navigate to Files tab...")
        try:
            # Try different selectors for the Files tab
            selectors = [
                'text=Files',
                'a:has-text("Files")',
                'button:has-text("Files")',
                'div[role="tab"]:has-text("Files")',
                'li[role="presentation"]:has-text("Files")',
                '//span[contains(text(), "Files")]',
                '//a[contains(text(), "Files")]'
            ]
            
            for selector in selectors:
                try:
                    logging.info(f"Trying Files tab selector: {selector}")
                    element = self.page.wait_for_selector(selector, timeout=5000)
                    if element and element.is_visible():
                        element.click()
                        logging.info(f"Successfully clicked Files tab using selector: {selector}")
                        # Wait for the Files tab content to load
                        self.page.wait_for_load_state('networkidle')
                        return
                except Exception as e:
                    logging.info(f"Selector {selector} failed: {str(e)}")
                    continue
            
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
        """Click the Add Files button."""
        self.page.click('button:has-text("Add Files")')
        self.page.click('button:has-text("Upload Files")')

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

            # Wait for navigation to account detail page or toast message
            try:
                self.page.wait_for_url(lambda url: '/view' in url or '/detail' in url, timeout=10000)
                current_url = self.page.url
                logging.info(f"Landed on URL after Save: {current_url}")
                # First, look for a Salesforce toast message
                try:
                    toast = self.page.wait_for_selector('div.slds-notify_toast, div.slds-notify--toast', timeout=5000)
                    if toast and toast.is_visible():
                        toast_text = toast.text_content()
                        logging.info(f"Found toast message after Save: {toast_text}")
                        if 'success' in toast_text.lower() or 'was created' in toast_text.lower():
                            logging.info("Successfully confirmed account creation by toast message.")
                            # Navigate back to accounts list
                            logging.info("Navigating back to accounts list...")
                            self.navigate_to_accounts()
                            # Search for the newly created account
                            account_name = f"{first_name} {last_name}"
                            logging.info(f"Searching for newly created account: {account_name}")
                            if self.search_account(account_name):
                                logging.info("Found newly created account in the list")
                                # Click on the account in the search results
                                logging.info("Clicking on the account in search results...")
                                try:
                                    # Try different selectors for the account link
                                    selectors = [
                                        'table[role="grid"] >> tr >> td:first-child',
                                        f'text={account_name}',
                                        f'a:has-text("{account_name}")',
                                        f'span:has-text("{account_name}")'
                                    ]
                                    for selector in selectors:
                                        try:
                                            element = self.page.wait_for_selector(selector, timeout=5000)
                                            if element and element.is_visible():
                                                element.click()
                                                logging.info(f"Successfully clicked account using selector: {selector}")
                                                # Wait for the account detail page to load
                                                self.page.wait_for_load_state('networkidle')
                                                # Now navigate to Files tab
                                                logging.info("Navigating to Files tab...")
                                                self.navigate_to_files()
                                                return True
                                        except Exception as e:
                                            logging.info(f"Selector {selector} failed: {str(e)}")
                                            continue
                                    raise Exception("Could not click on account in search results")
                                except Exception as e:
                                    logging.error(f"Error clicking account: {str(e)}")
                                    raise
                            else:
                                logging.error("Could not find newly created account in the list")
                                raise Exception("Could not find newly created account in the list")
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
                    logging.info("Successfully confirmed account creation by Account Name match.")
                    return True
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