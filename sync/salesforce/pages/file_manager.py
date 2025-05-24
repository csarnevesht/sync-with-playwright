from typing import List, Optional, Union
import os
import logging
from .base_page import BasePage
from playwright.sync_api import Page
import re
import sys
from ..utils.debug_utils import debug_prompt

class FileManager(BasePage):
    """Handles file-related operations in Salesforce."""
    
    def __init__(self, page: Page, debug_mode: bool = True):
        logging.info(f"****Initializing FileManager")
        super().__init__(page, debug_mode)
        self.current_account_id = None

    def scroll_to_bottom_of_page(self):
        """Scroll the files list to load all items and get actual count instead of 50+."""
        logging.info(f"****Scrolling files list to load all items")
        
        try:
            # Get initial item count
            initial_count = self.extract_files_count_from_status()
            logging.info(f"Initial item count: {initial_count}")
            
            if not initial_count or initial_count == 0:
                logging.warning("No initial count found, skipping scroll")
                return 0
                
            max_attempts = 10  # Increased to allow for stable attempts
            wait_time = 0.2
            unique_file_hrefs = set()
            stable_count = 0
            last_count = 0
            no_new_files_count = 0
            found_stable = False
            
            # Wait for the file list container to be visible with shorter timeout
            file_list = self.page.locator('div.slds-card__body table, div.slds-scrollable_y table, div[role="main"] table').first
            file_list.wait_for(state="visible", timeout=2000)
            
            # Get initial file links
            all_links = self.page.locator('a[href*="/ContentDocument/"]').all()
            for link in all_links:
                href = link.get_attribute('href')
                if href and '/ContentDocument/' in href:
                    unique_file_hrefs.add(href)
            
            # If we already have a good initial count (not "50+"), use that
            if isinstance(initial_count, int) and initial_count > 0:
                logging.info(f"Using initial count of {initial_count} files")
                return initial_count
            
            # Log initial count from first collection
            initial_links_count = len(unique_file_hrefs)
            logging.info(f"Initial collection found {initial_links_count} unique file links")
            
            # Start from attempt 1
            for attempt in range(1, max_attempts + 1):
                current_count = len(unique_file_hrefs)
                logging.info(f"Scroll attempt {attempt}: found {current_count} unique file links")
                
                # If we haven't found any new files in the last attempt
                if current_count == last_count:
                    no_new_files_count += 1
                    if not found_stable:
                        logging.info(f"No new files found, count stable for {no_new_files_count} attempts")
                        if no_new_files_count >= 2:  # Wait for 2 stable attempts
                            found_stable = True
                            stable_count = 0  # Reset stable count for final attempts
                            logging.info("Count is stable, making 2 final attempts...")
                    else:
                        stable_count += 1
                        logging.info(f"Making final attempt {stable_count}/2")
                        if stable_count >= 2:  # Stop after 2 final attempts
                            logging.info("Completed 2 final attempts, stopping scroll.")
                            break
                else:
                    # Reset counters when we find new files
                    no_new_files_count = 0
                    found_stable = False
                    stable_count = 0
                    logging.info(f"Found new files! Total: {len(unique_file_hrefs)}")
                
                # Try a more aggressive scroll if we haven't found new files
                if current_count == last_count:
                    try:
                        # Method 1: Scroll the table container with a larger offset
                        file_list.evaluate('el => el.scrollIntoView({block: "end", behavior: "auto"})')
                        self.page.wait_for_timeout(200)
                        
                        # Method 2: Scroll the parent container with a larger offset
                        parent = file_list.locator('xpath=..')
                        parent.evaluate('el => el.scrollBy(0, 3000)')
                        self.page.wait_for_timeout(200)
                        
                        # Method 3: Use keyboard to scroll multiple times
                        for _ in range(2):
                            self.page.keyboard.press('PageDown')
                            self.page.wait_for_timeout(100)
                    except Exception as e:
                        logging.warning(f"Failed to scroll: {str(e)}")
                        self.page.evaluate('window.scrollBy(0, 3000)')
                else:
                    # Normal scroll when finding new files
                    try:
                        file_list.evaluate('el => el.scrollIntoView({block: "end", behavior: "auto"})')
                        self.page.wait_for_timeout(int(wait_time * 1000))
                    except Exception as e:
                        logging.warning(f"Failed to scroll: {str(e)}")
                        self.page.evaluate('window.scrollBy(0, 2000)')
                
                # Get new file links after scroll
                all_links = self.page.locator('a[href*="/ContentDocument/"]').all()
                for link in all_links:
                    href = link.get_attribute('href')
                    if href and '/ContentDocument/' in href:
                        unique_file_hrefs.add(href)
                
                # Update last count for next iteration
                last_count = current_count
            
            return len(unique_file_hrefs)
                
        except Exception as e:
            logging.error(f"Error during scrolling: {str(e)}")
            self.page.screenshot(path="scroll-error.png")
            return 0

    def extract_files_count_from_status(self) -> Union[int, str]:
        """
        Extract the number of files from the Files status message on the page.
        Returns the item count as either an integer or a string (e.g. "50+"), or 0 if not found.
        """
        try:
            status_message = self.page.wait_for_selector('span[aria-label="Files"]', timeout=4000)
            if status_message:
                status_text = status_message.text_content()
                self.logger.info(f"Files status message: {status_text}")

                # Extract the number of items
                self.logger.info("Extracting the number of items...")
                match = re.search(r'(\d+\+?)\s+items?\s+•', status_text)
                if match:
                    item_count_str = match.group(1)
                    # If the count has a plus sign, return it as a string
                    if '+' in item_count_str:
                        self.logger.info(f"Found {item_count_str} files in the account")
                        return item_count_str
                    # Otherwise convert to int
                    item_count = int(item_count_str)
                    self.logger.info(f"Found {item_count} files in the account")
                    return item_count
                else:
                    self.logger.info("No items found or count not in expected format")
        except Exception as e:
            self.logger.info(f"Error checking files count: {str(e)}")
        return 0

    def navigate_to_files_click_on_files_card_to_facilitate_upload(self) -> int:
        """Navigate to the Files page of the current account. Assumes you are already on the account detail page.
        
        Returns:
            int: Number of files found in the account, -1 if there was an error
        """
        self.logger.info("****Attempting to navigate to Files...")
        self.logger.info(f"Current URL: {self.page.url}")
        
        try:
            # Try the most specific selector first: span[title="Files"]
            try:
                self.logger.info("Trying span[title='Files'] selector...")
                files_span = self.page.wait_for_selector('span[title="Files"]', timeout=4000)
                if files_span and files_span.is_visible():
                    # Try to click the parent element (often the tab itself)
                    parent = files_span.evaluate_handle('el => el.closest("a,button,li,div[role=\'tab\']")')
                    if parent:
                        parent.as_element().click()
                        self.logger.info("Clicked Files card using span[title='Files'] parent.")
                        
                        # Verify URL pattern
                        current_url = self.page.url
                        self.logger.info(f"Current URL after clicking Files tab: {current_url}")
                        
                        # Verify URL pattern: Account/{account_id}/related/AttachedContentDocuments/view
                        if not re.match(r'.*Account/\w+/related/AttachedContentDocuments/view.*', current_url):
                            raise Exception(f"Not on Files page. Current URL: {current_url}")
                        
                        # Extract and store account ID from URL
                        account_id_match = re.search(r'/Account/(\w+)/related', current_url)
                        if account_id_match:
                            account_id = account_id_match.group(1)
                            self.logger.info(f"Extracted account ID from Files page URL: {account_id}")
                            self.current_account_id = account_id
                        
                        # Use the new reusable method
                        item_count = self.extract_files_count_from_status()
                        return item_count
                    else:
                        # If no parent found, try clicking the span directly
                        files_span.click()
                        self.logger.info("Clicked Files tab using span[title='Files'] directly.")
                        self.page.wait_for_selector('div.slds-tabs_default__content', timeout=2000)
                        self.logger.info("Files tab content loaded")
                        return 0
            except Exception as e:
                self.logger.info(f"span[title='Files'] selector failed: {str(e)}")

            # If we get here, none of the selectors worked
            self.logger.error("Could not find Files tab with any of the selectors")
            
            if self.debug_mode:
                if not debug_prompt("Do you want to proceed with navigating to Files?"):
                    self.logger.info("Skipping navigation to Files. Exiting...")
                    sys.exit(1)
            
            # Take a screenshot for debugging
            self.page.screenshot(path="files-tab-error.png")
            self.logger.info("Error screenshot saved as files-tab-error.png")
            return -1
            
        except Exception as e:
            self.logger.error(f"Error navigating to Files tab: {str(e)}")
            # Take a screenshot for debugging
            self.page.screenshot(path="files-tab-error.png")
            self.logger.info("Error screenshot saved as files-tab-error.png")
            return -1
    
    def _extract_file_info_from_row(self, row) -> dict:
        """Extract file name and type information from a table row.
        
        Args:
            row: The table row element
            
        Returns:
            dict: Dictionary containing:
                - name: The clean file name
                - type: The file type
                - full_name: The full file name with type
        """
        try:
            # Get file name
            self.logger.info("Looking for span.itemTitle in row...")
            title_span = row.locator('span.itemTitle').first
            if not title_span:
                self.logger.info("No span.itemTitle found in row")
                return None
                
            self.logger.info("Getting text content from title span...")
            file_name = title_span.text_content(timeout=3000).strip()
            if not file_name:
                self.logger.info("No text content found in title span")
                return None
            
            self.logger.info(f"Raw file name from span: '{file_name}'")
            
            # Get file type from the type column
            file_type = 'Unknown'
            try:
                self.logger.info("Attempting to get file type from type column...")
                type_cell = row.locator('th:nth-child(2) span a div').first
                if type_cell:
                    type_text = type_cell.text_content(timeout=1000).strip()
                    self.logger.info(f"Raw type text from cell: '{type_text}'")
                    if type_text:
                        # Extract just the file type by matching the beginning of the string
                        # that matches the raw file name
                        if file_name in type_text:
                            file_type = type_text.split(file_name)[0].strip()
                            self.logger.info(f"Extracted file type from type column: '{file_type}'")
                            
                            # Convert common file type formats to standard format
                            file_type = file_type.lower()
                            if 'pdf' in file_type:
                                file_type = 'PDF'
                            elif 'doc' in file_type:
                                file_type = 'DOC'
                            elif 'xls' in file_type:
                                file_type = 'XLS'
                            elif 'txt' in file_type:
                                file_type = 'TXT'
                            elif any(img_type in file_type for img_type in ['jpg', 'jpeg', 'png', 'image file']):
                                file_type = 'IMG'
                            self.logger.info(f"Converted file type to standard format: '{file_type}'")
                        else:
                            file_type = type_text
                            self.logger.info(f"Using full type text as file type: '{file_type}'")
            except Exception as e:
                self.logger.info(f"Failed to get type from column, falling back to extension: {str(e)}")
                # If we can't get the type from the cell, try file extension
                file_type = self._get_file_type_from_extension(file_name)
                self.logger.info(f"Determined file type from extension: '{file_type}'")
            
            # Clean the file name by removing any existing numbers and file types
            self.logger.info("Cleaning file name...")
            clean_name = re.sub(r'^\d+\.\s*', '', file_name)
            self.logger.info(f"After removing leading numbers: '{clean_name}'")
            clean_name = re.sub(r'\s*\[\w+\]\s*$', '', clean_name)
            self.logger.info(f"After removing trailing type tags: '{clean_name}'")
            
            result = {
                'name': clean_name,
                'type': file_type,
                'full_name': f"{clean_name} [{file_type}]"
            }
            self.logger.info(f"Final file info: {result}")
            return result
            
        except Exception as e:
            self.logger.warning(f"Error extracting file info from row: {str(e)}")
            return None

    def search_file(self, file_pattern: str) -> bool:
        """Search for a file using a pattern."""
        self.logger.info(f"********Searching for file: {file_pattern}")
        
        try:
            # Wait for the table to be visible and loaded
            self.logger.info("Waiting for the files table to be visible...")
            table = self.page.wait_for_selector('div.slds-card__body table, div.slds-scrollable_y table, div[role="main"] table', timeout=5000)
            if not table:
                self.logger.error("Files table not found")
                return False
                
            # Wait for the table header to be visible
            self.logger.info("Waiting for table header...")
            self.page.wait_for_selector('span[title="Title"]', timeout=5000)
            
            # Wait a bit for content to load
            self.page.wait_for_timeout(1000)
            
            # Get all file rows
            self.logger.info("Getting all file rows from table...")
            file_rows = self.page.locator('table.slds-table tbody tr').all()
            if not file_rows:
                self.logger.info("No file rows found")
                return False
            
            self.logger.info(f"Found {len(file_rows)} file rows to search through")
            
            # Search through each row
            for i, row in enumerate(file_rows, 1):
                self.logger.info(f"Processing row {i}/{len(file_rows)}")
                file_info = self._extract_file_info_from_row(row)
                if not file_info:
                    self.logger.info(f"Skipping row {i} - no file info extracted")
                    continue
                    
                # Check if the file pattern matches either the clean name or full name
                self.logger.info(f"Checking row {i} against pattern '{file_pattern}'")
                self.logger.info(f"Clean name: '{file_info['name']}'")
                self.logger.info(f"Full name: '{file_info['full_name']}'")
                
                # Parse the search pattern into file info
                search_file_info = self._parse_search_file_pattern(file_pattern)
                self.logger.info(f"Search file info: {search_file_info}")
                
                # Normalize both the pattern and the file names for comparison
                normalized_pattern = search_file_info['name'].lower()
                normalized_name = file_info['name'].lower()
                
                # Create the exact file name with extension that we expect to match
                expected_name = f"{file_info['name']}.{file_info['type'].lower()}"
                self.logger.info(f"Expected file name: '{expected_name}'")
                
                # Do exact matching instead of partial matching
                name_match = normalized_pattern == normalized_name
                extension_match = normalized_pattern == expected_name.lower()
                
                self.logger.info(f"Name match: {name_match}")
                self.logger.info(f"Extension match: {extension_match}")
                
                if name_match or extension_match:
                    self.logger.info(f"Found matching file in row {i}: {file_info['full_name']}")
                    return True
                else:
                    self.logger.info(f"No match in row {i}")
            
            self.logger.info(f"No file found matching pattern: {file_pattern}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error searching for file: {str(e)}")
            self.page.screenshot(path="file-search-error.png")
            self.logger.info("Error screenshot saved as file-search-error.png")
            return False

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
            # Navigate to files section
            logging.info("Navigating to files section")
            logging.info(f"account_id: {account_id}")
            num_files = self.navigate_to_files_and_get_number_of_files_for_this_account(account_id)
            if num_files == -1:
                logging.error("Failed to navigate to Files")
                return []
                
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
                    
                    file_info = self._extract_file_info_from_row(row)
                    if file_info:
                        file_names.append(f"{i}. {file_info['full_name']}")
                        self.logger.info(f"Successfully processed file {i}: {file_info['full_name']}")
                except Exception as e:
                    self.logger.warning(f"Error getting file info for row {i}: {str(e)}")
                    continue
            
            self.logger.info(f"Completed processing {len(file_names)}/{total_rows} files successfully")
            return file_names
            
        except Exception as e:
            self.logger.error(f"Error getting file names: {str(e)}")
            return []

    def _verify_files_url(self, url: str) -> bool:
        """Verify that the current URL is a valid Files page URL."""
        return bool(re.match(r'.*Account/\w+/related/AttachedContentDocuments/view.*', url))
        
    def _extract_account_id(self, url: str) -> Optional[str]:
        """Extract the account ID from the URL."""
        match = re.search(r'/Account/(\w+)/related', url)
        return match.group(1) if match else None 

    def _get_file_type_from_extension(self, file_name: str) -> str:
        """Determine the file type from the file name extension.
        
        Args:
            file_name: The name of the file
            
        Returns:
            str: The standardized file type (PDF, DOC, XLS, TXT, IMG, or Unknown)
        """
        file_name = file_name.lower()
        if file_name.endswith('.pdf'):
            return 'PDF'
        elif file_name.endswith(('.doc', '.docx')):
            return 'DOC'
        elif file_name.endswith(('.xls', '.xlsx')):
            return 'XLS'
        elif file_name.endswith('.txt'):
            return 'TXT'
        elif file_name.endswith(('.jpg', '.jpeg', '.png')):
            return 'IMG'
        return 'Unknown'

    def _parse_search_file_pattern(self, file_pattern: str) -> dict:
        """Parse a search file pattern into a file info dictionary.
        
        Args:
            file_pattern: The file pattern to search for (e.g., "John Smith Application.pdf")
            
        Returns:
            dict: Dictionary containing:
                - name: The file name without extension
                - type: The file type (PDF, DOC, etc.)
                - full_name: The full file name with type in brackets
        """
        # Split the pattern to get name and extension
        search_file_name = file_pattern.split('.')[0].strip()
        search_file_type = self._get_file_type_from_extension(file_pattern)
        
        return {
            'name': search_file_name,
            'type': search_file_type,
            'full_name': f"{search_file_name} [{search_file_type}]"
        }

    