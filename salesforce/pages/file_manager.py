from typing import List, Optional
import os
import logging
from ..base_page import BasePage
from playwright.sync_api import Page
import re
import sys

class FileManager(BasePage):
    """Handles file-related operations in Salesforce."""
    
    def __init__(self, page: Page, debug_mode: bool = False):
        logging.info(f"****Initializing FileManager")
        super().__init__(page, debug_mode)
        self.current_account_id = None
        
    def extract_files_count_from_status(self) -> int:
        """
        Extract the number of files from the Files status message on the page.
        Returns the item count, or 0 if not found.
        """
        try:
            status_message = self.page.wait_for_selector('span[aria-label="Files"]', timeout=4000)
            if status_message:
                status_text = status_message.text_content()
                self.logger.info(f"Files status message: {status_text}")

                # Extract the number of items
                self.logger.info("Extracting the number of items...")
                match = re.search(r'(\d+)\s+items?\s+•', status_text)
                if match:
                    item_count = int(match.group(1))
                    self.logger.info(f"Found {item_count} files in the account")
                    return item_count
                else:
                    self.logger.info("No items found or count not in expected format")
        except Exception as e:
            self.logger.info(f"Error checking files count: {str(e)}")
        return 0

    def navigate_to_files(self) -> int:
        """Navigate to the Files page of the current account. Assumes you are already on the account detail page.
        
        Returns:
            int: Number of files found in the account, -1 if there was an error
        """
        self.logger.info("****Attempting to navigate to Files...")
        
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
                        self.logger.info("Clicked Files tab using span[title='Files'] parent.")
                        
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
            
    def get_number_of_files(self) -> int:
        """Get the number of files in the account."""
        try:
            status_message = self.page.wait_for_selector('span[aria-label="Files"]', timeout=4000)
            if not status_message:
                self.logger.error("Could not find files status message")
                return 0
                
            text = status_message.text_content()
            self.logger.info(f"***Number of files in get_number_of_files: {text}")
            match = re.search(r'(\d+)\s+items?\s+•', text)
            return int(match.group(1)) if match else 0
            
        except Exception as e:
            self.logger.error(f"Error getting number of files: {str(e)}")
            self.page.screenshot(path="get-files-count-error.png")
            return 0
            
    def search_file(self, file_pattern: str) -> bool:
        """Search for a file using a pattern."""
        self.logger.info(f"********Searching for file: {file_pattern}")
        
        try:
            # Look for the file name using the correct class and title attribute
            self.logger.info("Looking for the file name using the correct class and title attribute")
            self.logger.info("First wait for the table to be visible using span[title='Title']")
            # First wait for the table to be visible using span[title='Title']
            self.page.wait_for_selector('span[title="Title"]', timeout=2000)
            
            # Then look for the file name in the table
            file_selector = f"span.itemTitle[title='{file_pattern}']"
            # Use evaluate to check if the element exists and is visible
            is_visible = self.page.evaluate("""(selector) => {
                const elements = document.querySelectorAll(selector);
                for (const element of elements) {
                    if (window.getComputedStyle(element).display !== 'none') {
                        return true;
                    }
                }
                return false;
            }""", file_selector)
            
            self.logger.info(f"File search result: {'Found' if is_visible else 'Not found'}")
            return is_visible
            
        except Exception as e:
            self.logger.error(f"Error searching for file: {str(e)}")
            self.logger.info(f"Error searching for file: {str(e)}")
            self.page.screenshot(path="file-search-error.png")
            sys.exit(1)  # Stop execution after error
            
    def _verify_files_url(self, url: str) -> bool:
        """Verify that the current URL is a valid Files page URL."""
        return bool(re.match(r'.*Account/\w+/related/AttachedContentDocuments/view.*', url))
        
    def _extract_account_id(self, url: str) -> Optional[str]:
        """Extract the account ID from the URL."""
        match = re.search(r'/Account/(\w+)/related', url)
        return match.group(1) if match else None 