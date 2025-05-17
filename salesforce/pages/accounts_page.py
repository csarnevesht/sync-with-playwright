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
        self.page.click('text=Files')

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
            
            # Wait for the first name field to be visible (try multiple selectors)
            logging.info("Waiting for first name field...")
            first_name_selectors = [
                '//label[contains(text(), "First Name")]/following-sibling::input',
                '//input[contains(@placeholder, "First Name")]',
                'input[name="firstName"]',
                'input[id*="FirstName"]',
                'input[aria-label="First Name"]',
                'input'
            ]
            found = False
            for selector in first_name_selectors:
                try:
                    logging.info(f"Trying selector for First Name: {selector}")
                    el = self.page.wait_for_selector(selector, timeout=5000)
                    if el and el.is_visible():
                        logging.info(f"Found First Name field with selector: {selector}")
                        found = True
                        break
                except Exception as e:
                    logging.info(f"Selector {selector} failed: {str(e)}")
            if not found:
                # Log the form content for debugging
                try:
                    form_content = self.page.content()
                    with open("form-content.html", "w") as f:
                        f.write(form_content)
                    logging.error("Could not find First Name field. Form content saved as form-content.html")
                except Exception as e:
                    logging.error(f"Failed to save form content: {str(e)}")
                raise Exception("Could not find First Name field on the new account form.")

            # Fill in basic information (use the first working selector)
            self.page.fill(selector, first_name)

            # Robust selector logic for Last Name
            last_name_selectors = [
                '//label[contains(text(), "Last Name")]/following-sibling::input',
                '//input[contains(@placeholder, "Last Name")]',
                'input[name="lastName"]',
                'input[id*="LastName"]',
                'input[aria-label="Last Name"]',
                'input'
            ]
            found_last = False
            for last_selector in last_name_selectors:
                try:
                    logging.info(f"Trying selector for Last Name: {last_selector}")
                    el = self.page.wait_for_selector(last_selector, timeout=5000)
                    if el and el.is_visible():
                        logging.info(f"Found Last Name field with selector: {last_selector}")
                        found_last = True
                        break
                except Exception as e:
                    logging.info(f"Selector {last_selector} failed: {str(e)}")
            if not found_last:
                # Log the form content for debugging
                try:
                    form_content = self.page.content()
                    with open("form-content.html", "w") as f:
                        f.write(form_content)
                    logging.error("Could not find Last Name field. Form content saved as form-content.html")
                except Exception as e:
                    logging.error(f"Failed to save form content: {str(e)}")
                raise Exception("Could not find Last Name field on the new account form.")

            self.page.fill(last_selector, last_name)

            if middle_name:
                self.page.fill('//label[contains(text(), "Middle Name")]/following-sibling::input', middle_name)

            # Fill in additional information if available
            if account_info:
                logging.info("Filling in additional information...")
                def fill_field(field_name, value, selectors):
                    found = False
                    for sel in selectors:
                        try:
                            logging.info(f"Trying selector for {field_name}: {sel}")
                            el = self.page.wait_for_selector(sel, timeout=3000)
                            if el and el.is_visible():
                                logging.info(f"Found {field_name} field with selector: {sel}")
                                self.page.fill(sel, value)
                                found = True
                                break
                        except Exception as e:
                            logging.info(f"Selector {sel} failed: {str(e)}")
                    if not found:
                        try:
                            form_content = self.page.content()
                            with open("form-content.html", "w") as f:
                                f.write(form_content)
                            logging.error(f"Could not find {field_name} field. Form content saved as form-content.html")
                        except Exception as e:
                            logging.error(f"Failed to save form content: {str(e)}")
                        raise Exception(f"Could not find {field_name} field on the new account form.")

                def select_field(field_name, value, selectors):
                    found = False
                    for sel in selectors:
                        try:
                            logging.info(f"Trying selector for {field_name}: {sel}")
                            el = self.page.wait_for_selector(sel, timeout=3000)
                            if el and el.is_visible():
                                logging.info(f"Found {field_name} field with selector: {sel}")
                                self.page.select_option(sel, value)
                                found = True
                                break
                        except Exception as e:
                            logging.info(f"Selector {sel} failed: {str(e)}")
                    if not found:
                        try:
                            form_content = self.page.content()
                            with open("form-content.html", "w") as f:
                                f.write(form_content)
                            logging.error(f"Could not find {field_name} field. Form content saved as form-content.html")
                        except Exception as e:
                            logging.error(f"Failed to save form content: {str(e)}")
                        raise Exception(f"Could not find {field_name} field on the new account form.")

                # Date of Birth
                if 'date_of_birth' in account_info:
                    fill_field('Date of Birth', account_info['date_of_birth'], [
                        '//label[contains(text(), "Date of Birth")]/following-sibling::input',
                        '//input[contains(@placeholder, "Date of Birth")]',
                        'input[name="dateOfBirth"]',
                        'input[id*="DateOfBirth"]',
                        'input[aria-label="Date of Birth"]',
                        'input[type="date"]',
                        'input'
                    ])

                # Age
                if 'age' in account_info:
                    fill_field('Age', account_info['age'], [
                        '//label[contains(text(), "Age")]/following-sibling::input',
                        '//input[contains(@placeholder, "Age")]',
                        'input[name="age"]',
                        'input[id*="Age"]',
                        'input[aria-label="Age"]',
                        'input[type="number"]',
                        'input'
                    ])

                # Sex
                if 'sex' in account_info:
                    select_field('Sex', account_info['sex'], [
                        '//label[contains(text(), "Sex")]/following-sibling::select',
                        'select[name="sex"]',
                        'select[id*="Sex"]',
                        'select[aria-label="Sex"]',
                        'select'
                    ])

                # SSN
                if 'ssn' in account_info:
                    fill_field('SSN', account_info['ssn'], [
                        '//label[contains(text(), "SSN")]/following-sibling::input',
                        '//input[contains(@placeholder, "SSN")]',
                        'input[name="ssn"]',
                        'input[id*="SSN"]',
                        'input[aria-label="SSN"]',
                        'input'
                    ])

                # Contact Information
                if 'email' in account_info:
                    fill_field('Email', account_info['email'], [
                        '//label[contains(text(), "Email")]/following-sibling::input',
                        '//input[contains(@placeholder, "Email")]',
                        'input[name="email"]',
                        'input[id*="Email"]',
                        'input[aria-label="Email"]',
                        'input[type="email"]',
                        'input'
                    ])

                if 'phone' in account_info:
                    fill_field('Phone', account_info['phone'], [
                        '//label[contains(text(), "Phone")]/following-sibling::input',
                        '//input[contains(@placeholder, "Phone")]',
                        'input[name="phone"]',
                        'input[id*="Phone"]',
                        'input[aria-label="Phone"]',
                        'input[type="tel"]',
                        'input'
                    ])

                if 'address' in account_info:
                    fill_field('Address', account_info['address'], [
                        '//label[contains(text(), "Address")]/following-sibling::input',
                        '//input[contains(@placeholder, "Address")]',
                        'input[name="address"]',
                        'input[id*="Address"]',
                        'input[aria-label="Address"]',
                        'input'
                    ])

                if 'city' in account_info:
                    fill_field('City', account_info['city'], [
                        '//label[contains(text(), "City")]/following-sibling::input',
                        '//input[contains(@placeholder, "City")]',
                        'input[name="city"]',
                        'input[id*="City"]',
                        'input[aria-label="City"]',
                        'input'
                    ])

                if 'state' in account_info:
                    select_field('State', account_info['state'], [
                        '//label[contains(text(), "State")]/following-sibling::select',
                        'select[name="state"]',
                        'select[id*="State"]',
                        'select[aria-label="State"]',
                        'select'
                    ])

                if 'zip' in account_info:
                    fill_field('Zip', account_info['zip'], [
                        '//label[contains(text(), "Zip")]/following-sibling::input',
                        '//input[contains(@placeholder, "Zip")]',
                        'input[name="zip"]',
                        'input[id*="Zip"]',
                        'input[aria-label="Zip"]',
                        'input'
                    ])

            # Debug prompt before saving
            if not self._debug_prompt(f"\nAccount information to be saved:\nFirst Name: {first_name}\nLast Name: {last_name}\nMiddle Name: {middle_name}\nAdditional Info: {account_info}\n\nContinue with saving?"):
                logging.info("User chose to stop account creation")
                return

            # Save the account
            logging.info("Clicking Save button...")
            self.page.click('button:has-text("Save")')

            # Wait for save to complete
            logging.info("Waiting for save to complete...")
            self.page.wait_for_selector('text=Account saved successfully', timeout=10000)

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