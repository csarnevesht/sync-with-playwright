from typing import List, Optional, Union, Dict
import os
import logging
from .base_page import BasePage
from playwright.sync_api import Page
import re
import sys
from ..utils.debug_utils import debug_prompt
from ..utils.file_utils import get_file_type, parse_search_file_pattern
from dropbox.files import FileMetadata

class SalesforceFileManager(BasePage):
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
                files_span = self.page.wait_for_selector('span[title="Files"]', timeout=10000)
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
                            elif any(excel_type in file_type for excel_type in ['xls', 'excel spreadsheet']):
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
                file_type = get_file_type(file_name)
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

    def search_salesforce_file(self, file_pattern: str) -> bool:
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
                search_file_info = parse_search_file_pattern(file_pattern)
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

    def get_all_file_names(self) -> List[str]:
        """
        Get all file names from the current files page.
        
        Returns:
            List[str]: List of file names found in the format "1. filename [TYPE]"
        """
        self.logger.info(f"Getting all file names")
        
        try:
            # Verify we're on the correct Files page
            current_url = self.page.url
            if not current_url.endswith('/related/AttachedContentDocuments/view'):
                self.logger.error(f"Not on Files page. Current URL: {current_url}")
                return []
            
            # Wait for the files table to be visible and at least one file row to appear
            max_attempts = 5
            for attempt in range(max_attempts):
                try:
                    # Use the same selector as in navigation and deletion methods
                    table = self.page.wait_for_selector('div.slds-card__body table, div.slds-scrollable_y table, div[role="main"] table', timeout=6000)
                    file_rows = self.page.locator('div.slds-card__body table tbody tr, div.slds-scrollable_y table tbody tr, div[role="main"] table tbody tr').all()
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
            file_rows = self.page.locator('div.slds-card__body table tbody tr, div.slds-scrollable_y table tbody tr, div[role="main"] table tbody tr').all()
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
                    
                    # Use _extract_file_info_from_row to get file info
                    file_info = self._extract_file_info_from_row(row)
                    if file_info:
                        file_names.append(f"{file_info['full_name']}")
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

    def compare_salesforce_files(self, dropbox_files: List[FileMetadata], salesforce_files: List[str]) -> Dict:
        """
        Compare files between Dropbox and Salesforce, logging detailed information.
        Args:
            dropbox_files: List of FileMetadata objects from Dropbox
            salesforce_files: List of filenames from Salesforce
        Returns:
            dict: Comparison results with detailed status for each file
        """
        self.logger.info("\n" + "="*50)
        self.logger.info("Starting file comparison process")
        self.logger.info("\n" + "="*50)
        self.logger.info(f"\nInitial file counts:")
        self.logger.info(f"  Dropbox files: {len(dropbox_files)}")
        self.logger.info(f"  Salesforce files: {len(salesforce_files)}")

        # Sort both lists by date (newest first)
        sorted_dropbox = list(map(lambda f: parse_search_file_pattern(f.name)['full_name'], sorted(dropbox_files, key=lambda f: f.name, reverse=True)))        
        sorted_salesforce = sorted(salesforce_files, key=lambda f: f, reverse=True)
        # Log sorted lists with dates
        self.logger.info("\nDropbox files (sorted):")
        for file in sorted_dropbox:
            file_name = file.name if isinstance(file, FileMetadata) else file
            self.logger.info(f"  {file_name}")
        self.logger.info("\nSalesforce files (sorted):")
        for file in sorted_salesforce:
            self.logger.info(f"  {file}")

        # Initialize comparison results
        comparison = {
            'total_files': len(dropbox_files),
            'matched_files': 0,
            'missing_files': [],
            'extra_files': [],
            'file_details': {}
        }

        # Compare each Dropbox file
        self.logger.info("\n" + "-"*50)
        self.logger.info("Starting file comparison")
        self.logger.info("\n" + "-"*50)
        for dropbox_file in sorted_dropbox:
            dropbox_name = dropbox_file.name if isinstance(dropbox_file, FileMetadata) else dropbox_file
            self.logger.info(f"\nChecking Dropbox file: {dropbox_name}")
            found_match = False
            potential_matches = []
            for salesforce_file in sorted_salesforce:
                if dropbox_name == salesforce_file:
                    found_match = True
                    comparison['matched_files'] += 1
                    comparison['file_details'][dropbox_name] = {
                            'status': 'matched',
                            'salesforce_file': salesforce_file,
                            'match_type': 'exact'
                    }
                    break
                else:
                    self.logger.info(f"  {dropbox_name} != {salesforce_file}")
                sf_file = salesforce_file
                date_prefix = sf_file[:6]
                base_name = sf_file[6:].lower()
                if dropbox_name.startswith(date_prefix):
                    potential_matches.append(salesforce_file)
                    self.logger.info(f"  Found potential match with date prefix {date_prefix}: {salesforce_file}")
                    if base_name in sf_file[6:].lower():
                        self.logger.info(f"  ✓ MATCH FOUND: {salesforce_file}")
                        found_match = True
                        comparison['matched_files'] += 1
                        comparison['file_details'][dropbox_name] = {
                            'status': 'matched',
                            'salesforce_file': salesforce_file,
                            'match_type': 'exact' if base_name == sf_file[6:].lower() else 'partial'
                        }
                        break
                    else:
                        self.logger.info(f"  ✗ Date prefix matches but names differ:")
                        self.logger.info(f"    Dropbox:    {base_name}")
                        self.logger.info(f"    Salesforce: {sf_file[6:].lower()}")
            if not found_match:
                if potential_matches:
                    self.logger.info(f"  ✗ NO EXACT MATCH FOUND for {dropbox_name}")
                    self.logger.info(f"    Found {len(potential_matches)} files with matching date prefix:")
                    for match in potential_matches:
                        self.logger.info(f"      - {match}")
                else:
                    self.logger.info(f"  ✗ NO MATCH FOUND for {dropbox_name}")
                    self.logger.info(f"    No files found with date prefix {date_prefix}")
                comparison['missing_files'].append(dropbox_name)
                comparison['file_details'][dropbox_name] = {
                    'status': 'missing',
                    'reason': f"Not found in Salesforce (existing prefix: {date_prefix})",
                    'potential_matches': potential_matches
                }

        # Find extra files in Salesforce
        self.logger.info("\n" + "-"*50)
        self.logger.info("Checking for extra files in Salesforce")
        self.logger.info("-"*50)
        for salesforce_file in sorted_salesforce:
            found_match = False
            sf_file = salesforce_file
            if '. ' in sf_file:
                space_index = sf_file.find('. ') + 2
                if space_index > 1:
                    sf_file = sf_file[space_index:]
            for dropbox_file in sorted_dropbox:
                dropbox_name = dropbox_file.name if isinstance(dropbox_file, FileMetadata) else dropbox_file
                if sf_file.startswith(dropbox_name[:6]) and dropbox_name[6:].lower() in sf_file[6:].lower():
                    found_match = True
                    break
            if not found_match:
                self.logger.info(f"  ✗ Extra file in Salesforce: {salesforce_file}")
                self.logger.info(f"    Date prefix: {sf_file[:6]}")
                self.logger.info(f"    Base name: {sf_file[6:]}")
                comparison['extra_files'].append(salesforce_file)

        # Log summary
        self.logger.info("\n" + "="*50)
        self.logger.info("Comparison Summary")
        self.logger.info("="*50)
        self.logger.info(f"Total files to process: {comparison['total_files']}")
        self.logger.info(f"Successfully matched: {comparison['matched_files']}")
        self.logger.info(f"Missing files: {len(comparison['missing_files'])}")
        self.logger.info(f"Extra files in Salesforce: {len(comparison['extra_files'])}")
        if comparison['missing_files']:
            self.logger.info("\nMissing files:")
            for file in comparison['missing_files']:
                self.logger.info(f"  - {file}")
        if comparison['extra_files']:
            self.logger.info("\nExtra files in Salesforce:")
            for file in comparison['extra_files']:
                self.logger.info(f"  - {file}")
        self.logger.info("\n" + "="*50)
        return comparison

    def delete_salesforce_file(self, file_name: str) -> bool:
        """Delete a file from Salesforce.

        Args:
            file_name: The name of the file to delete (can include enumeration number)

        Returns:
            bool: True if the file was deleted successfully, False otherwise
        """
        self.logger.info(f"Attempting to delete file: {file_name}")

        try:
            # Wait for the table to be visible and loaded
            self.logger.info("Waiting for the files table to be visible...")
            table = self.page.wait_for_selector('div.slds-card__body table, div.slds-scrollable_y table, div[role=\"main\"] table', timeout=5000)
            if not table:
                self.logger.error("Files table not found")
                return False

            # Wait for the table header to be visible
            self.logger.info("Waiting for table header...")
            self.page.wait_for_selector('span[title=\"Title\"]', timeout=5000)

            # Wait a bit for content to load
            self.page.wait_for_timeout(2000)  # Increased wait time

            # Get all file rows (only visible ones)
            self.logger.info("Getting all file rows from table...")
            all_rows = self.page.locator('div.slds-card__body table tbody tr, div.slds-scrollable_y table tbody tr, div[role=\"main\"] table tbody tr')
            file_rows = [row for row in all_rows.all() if row.is_visible()]
            if not file_rows:
                self.logger.info("No visible file rows found")
                return False

            self.logger.info(f"Found {len(file_rows)} visible file rows to search through")

            # Search through each row
            for i, row in enumerate(file_rows, 1):
                self.logger.info(f"Processing row {i}/{len(file_rows)}")
                file_info = self._extract_file_info_from_row(row)
                if not file_info:
                    self.logger.info(f"Skipping row {i} - no file info extracted")
                    continue

                # Check if the file name matches
                self.logger.info(f"Checking row {i} against file name '{file_name}'")
                self.logger.info(f"Clean name: '{file_info['name']}'")
                self.logger.info(f"Full name: '{file_info['full_name']}'")

                # Remove enumeration number from file_name if present
                clean_file_name = file_name
                if '. ' in file_name:
                    space_index = file_name.find('. ') + 2
                    if space_index > 1:
                        clean_file_name = file_name[space_index:]

                # Check for match
                if clean_file_name == file_info['full_name'] or clean_file_name == file_info['name']:
                    self.logger.info(f"Found matching file in row {i}")

                    # Hover over the row to reveal action buttons
                    self.logger.info(f"Hovering over row {i} to reveal action buttons...")
                    try:
                        row.hover()
                        self.page.wait_for_timeout(500)
                    except Exception as e:
                        self.logger.warning(f"Failed to hover over row {i}: {str(e)}")

                    # Take a screenshot after hover for diagnostics
                    self.page.screenshot(path=f"row{i}-after-hover.png")
                    self.logger.info(f"Screenshot saved as row{i}-after-hover.png")

                    # Try to find the dropdown button or <a role="button"> in the last cell of the row
                    self.logger.info(f"Looking for dropdown action in the last cell of row {i}...")
                    try:
                        cells = row.locator('td').all()
                        if cells:
                            last_cell = cells[-1]
                            # Look for both <button> and <a role="button">
                            dropdown_candidates = last_cell.locator('button, a[role="button"]').all()
                            if dropdown_candidates:
                                # Use the first visible and enabled candidate
                                dropdown = None
                                for candidate in dropdown_candidates:
                                    if candidate.is_visible() and (candidate.is_enabled() if hasattr(candidate, 'is_enabled') else True):
                                        dropdown = candidate
                                        break
                                if dropdown:
                                    self.logger.info(f"Found dropdown action in last cell of row {i}.")
                                else:
                                    self.logger.error(f"Dropdown action in last cell is not visible/enabled.")
                                    self.page.screenshot(path=f"dropdown-not-visible-row{i}.png")
                                    self.logger.info(f"Screenshot saved as dropdown-not-visible-row{i}.png")
                                    return False
                            else:
                                self.logger.error(f"No <button> or <a role='button'> found in last cell of row {i}.")
                                self.page.screenshot(path=f"dropdown-not-found-in-last-cell-row{i}.png")
                                self.logger.info(f"Screenshot saved as dropdown-not-found-in-last-cell-row{i}.png")
                                return False
                        else:
                            self.logger.error(f"No cells found in row {i}.")
                            self.page.screenshot(path=f"no-cells-in-row{i}.png")
                            self.logger.info(f"Screenshot saved as no-cells-in-row{i}.png")
                            return False
                    except Exception as e:
                        self.logger.error(f"Error finding dropdown in last cell: {str(e)}")
                        self.page.screenshot(path=f"dropdown-error-row{i}.png")
                        self.logger.info(f"Screenshot saved as dropdown-error-row{i}.png")
                        return False

                    # Click the dropdown menu with retry
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            self.logger.info(f"Attempting to click dropdown (attempt {attempt + 1}/{max_retries})...")
                            dropdown.click(timeout=5000)
                            self.page.wait_for_timeout(1000)  # Wait for dropdown to appear
                            # Take a screenshot after clicking dropdown
                            self.page.screenshot(path=f"dropdown-opened-row{i}.png")
                            self.logger.info(f"Screenshot saved as dropdown-opened-row{i}.png")
                            # Look for the Delete menu item
                            delete_menuitem = None
                            menuitems = self.page.locator('a[role="menuitem"]').all()
                            self.logger.info(f"Dropdown has {len(menuitems)} menuitem(s):")
                            for idx, item in enumerate(menuitems, 1):
                                text = item.text_content().strip() if item else ''
                                self.logger.info(f"  Menuitem {idx}: text='{text}'")
                                if text.lower() == 'delete' and item.is_visible():
                                    delete_menuitem = item
                                    break
                            if delete_menuitem:
                                self.logger.info("Found 'Delete' menu item. Clicking...")
                                delete_menuitem.click(timeout=5000)
                                self.page.wait_for_timeout(1000)
                                break
                            else:
                                self.logger.error("Could not find 'Delete' menu item after opening dropdown.")
                                self.page.screenshot(path=f"delete-menuitem-not-found-row{i}.png")
                                self.logger.info(f"Screenshot saved as delete-menuitem-not-found-row{i}.png")
                                if attempt == max_retries - 1:
                                    return False
                                self.page.wait_for_timeout(1000)
                        except Exception as e:
                            self.logger.warning(f"Click attempt {attempt + 1} failed: {str(e)}")
                            self.page.screenshot(path=f"dropdown-click-fail-row{i}-attempt{attempt+1}.png")
                            self.logger.info(f"Screenshot saved as dropdown-click-fail-row{i}-attempt{attempt+1}.png")
                            if attempt == max_retries - 1:
                                self.logger.error("All click attempts failed")
                                return False
                            self.page.wait_for_timeout(1000)  # Wait before retry

                    # Wait for the confirmation dialog/modal to appear
                    self.logger.info("Waiting for confirmation dialog to appear...")
                    try:
                        # Wait for a modal/dialog to be visible
                        modal = self.page.wait_for_selector('.slds-modal__container, .slds-modal', timeout=5000)
                        if not modal or not modal.is_visible():
                            self.logger.error("Confirmation dialog/modal did not appear or is not visible.")
                            self.page.screenshot(path=f"delete-modal-not-visible-row{i}.png")
                            return False
                        self.logger.info("Confirmation dialog/modal is visible.")
                    except Exception as e:
                        self.logger.error(f"Error waiting for confirmation dialog: {str(e)}")
                        self.page.screenshot(path=f"delete-modal-error-row{i}.png")
                        return False

                    # Now look for the Delete button inside the modal
                    self.logger.info("Looking for Delete button inside the modal...")
                    try:
                        # Only search for buttons inside the modal
                        delete_button = None
                        buttons = modal.query_selector_all('button')
                        for idx, btn in enumerate(buttons, 1):
                            inner_text = btn.inner_text().strip() if hasattr(btn, 'inner_text') else ''
                            text_content = btn.text_content().strip() if hasattr(btn, 'text_content') else ''
                            title = btn.get_attribute('title')
                            classes = btn.get_attribute('class')
                            self.logger.info(f"  Modal Button {idx}: inner_text='{inner_text}', text_content='{text_content}', title='{title}', class='{classes}'")
                            if (inner_text.lower() == 'delete' or text_content.lower() == 'delete' or (title and title.lower() == 'delete')):
                                # Try to check visibility and enabled state if possible
                                is_visible = True
                                is_enabled = True
                                try:
                                    is_visible = btn.is_visible() if hasattr(btn, 'is_visible') else True
                                except Exception:
                                    pass
                                try:
                                    is_enabled = btn.is_enabled() if hasattr(btn, 'is_enabled') else True
                                except Exception:
                                    pass
                                if is_visible and is_enabled:
                                    delete_button = btn
                                    break
                        if not delete_button:
                            self.logger.error("Could not find visible and enabled Delete button in modal.")
                            self.page.screenshot(path=f"delete-button-not-found-in-modal-row{i}.png")
                            return False
                        self.logger.info("Found visible and enabled Delete button in modal. Attempting to click...")
                        delete_button.scroll_into_view_if_needed()
                        delete_button.click(timeout=5000)
                        self.page.wait_for_timeout(2000)  # Wait for deletion to complete
                    except Exception as e:
                        self.logger.error(f"Error clicking Delete button in modal: {str(e)}")
                        self.page.screenshot(path=f"delete-button-click-error-modal-row{i}.png")
                        return False

                    self.logger.info(f"Successfully deleted file: {file_name}")
                    return True
                else:
                    self.logger.info(f"No match in row {i}")

            self.logger.info(f"No file found matching name: {file_name}")
            return False

        except Exception as e:
            self.logger.error(f"Error deleting file: {str(e)}")
            self.page.screenshot(path="file-delete-error.png")
            self.logger.info("Error screenshot saved as file-delete-error.png")
            return False


    