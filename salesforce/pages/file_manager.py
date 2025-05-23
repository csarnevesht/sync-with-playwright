from typing import List, Optional, Union
import os
import logging
from ..base_page import BasePage
from playwright.sync_api import Page
import re
import sys
from ..utils.debug_utils import debug_prompt

class FileManager(BasePage):
    """Handles file-related operations in Salesforce."""
    
    def __init__(self, page: Page, debug_mode: bool = False):
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

    def delete_file(self, file_name: str) -> bool:
        """
        Delete a file from the current account.
        
        Args:
            file_name: Name of the file to delete (can include index and type)
            
        Returns:
            bool: True if file was deleted successfully, False otherwise
        """
        try:
            # Extract just the file name without index and type
            base_name = file_name.split('. ', 1)[-1].split(' [')[0]
            self.logger.info(f"Looking for file with base name: {base_name}")
            
            self.page.wait_for_selector('table', state='visible', timeout=10000)
            file_row = self.page.locator(f'tr:has-text("{base_name}")').first
            if not file_row:
                self.logger.error(f"Could not find file row for: {base_name}")
                return False
            file_row.wait_for(state='visible', timeout=5000)
            
            # Try all clickable elements in the last td of the row
            last_td = file_row.locator('td').last
            dropdown = None
            for selector in ['button', 'a', 'div', '[role="button"]']:
                try:
                    candidate = last_td.locator(selector).first
                    candidate.wait_for(state='visible', timeout=1000)
                    if candidate.is_visible():
                        dropdown = candidate
                        break
                except Exception:
                    continue
            if not dropdown:
                self.logger.error("Could not find any clickable dropdown trigger in last cell")
                row_path = "/Users/carolinasarneveshtair/projects/sync-with-playwright/file-row.png"
                self.logger.info(f"Saving file row screenshot to {row_path}")
                file_row.screenshot(path=row_path)
                return False
            try:
                dropdown.click()
                self.page.wait_for_timeout(700)  # Wait for menu to open
                screenshot_path = "/Users/carolinasarneveshtair/projects/sync-with-playwright/dropdown-opened.png"
                self.logger.info(f"Saving dropdown-opened screenshot to {screenshot_path}")
                self.page.screenshot(path=screenshot_path)
                self.logger.info(f"Screenshot saved to {screenshot_path}")
            except Exception as e:
                self.logger.error(f"Error clicking dropdown trigger: {str(e)}")
                row_path = "/Users/carolinasarneveshtair/projects/sync-with-playwright/file-row.png"
                self.logger.info(f"Saving file row screenshot to {row_path}")
                file_row.screenshot(path=row_path)
                return False
            
            # Immediately try to find and click the Delete option globally
            global_delete = None
            for selector in ['a:has-text("Delete")', '[role="menuitem"]:has-text("Delete")', 'li:has-text("Delete")', 'div:has-text("Delete")']:
                try:
                    candidate = self.page.locator(selector).first
                    if candidate and candidate.is_visible():
                        global_delete = candidate
                        break
                except Exception:
                    continue
            if global_delete:
                global_delete.wait_for(state='visible', timeout=5000)
                global_delete.click()
            else:
                self.logger.error("Could not find Delete option globally after dropdown opened.")
                self.page.screenshot(path="/Users/carolinasarneveshtair/projects/sync-with-playwright/delete-option-not-found-global.png")
                return False
            
            confirm_button = self.page.locator('button:has-text("Delete")').first
            if not confirm_button:
                self.logger.error("Could not find confirm button")
                return False
            confirm_button.wait_for(state='visible', timeout=5000)
            confirm_button.click()
            self.page.wait_for_timeout(2000)
            if self.search_file(base_name):
                self.logger.error(f"File {base_name} still exists after deletion")
                return False
            self.logger.info(f"Successfully deleted file: {base_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting file: {str(e)}")
            return False

    