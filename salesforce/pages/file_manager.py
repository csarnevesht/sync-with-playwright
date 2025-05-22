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
                return
                
            max_attempts = 30
            attempt = 0
            last_count = initial_count
            no_change_count = 0
            last_scroll_height = 0
            
            while attempt < max_attempts:
                # Debug: Log all table-related elements
                table_info = self.page.evaluate("""() => {
                    const elements = {
                        // File items
                        fileTitles: document.querySelectorAll('span[title]').length,
                        fileLinks: document.querySelectorAll('a[title]').length,
                        fileRows: document.querySelectorAll('tr[data-row-id]').length,
                        fileCards: document.querySelectorAll('div.slds-card').length,
                        
                        // Table structure
                        tables: document.querySelectorAll('table').length,
                        rows: document.querySelectorAll('tr').length,
                        
                        // Specific file list elements
                        fileListItems: document.querySelectorAll('li.slds-hint-parent').length,
                        fileGridItems: document.querySelectorAll('div[role="grid"] div[role="row"]').length,
                        fileListRows: document.querySelectorAll('div.slds-scrollable_y li').length,
                        
                        // Container elements
                        scrollableContainers: document.querySelectorAll('div.slds-scrollable_y').length,
                        gridContainers: document.querySelectorAll('div[role="grid"]').length,
                        cardContainers: document.querySelectorAll('div.slds-card__body').length,
                        
                        // Additional selectors
                        fileItems: document.querySelectorAll('div[data-aura-class="forceFileCard"]').length,
                        fileLinksInTable: document.querySelectorAll('tr a[data-aura-class="forceFileCard"]').length,
                        fileTitlesInTable: document.querySelectorAll('tr span[title]').length,
                        fileTitlesInBody: document.querySelectorAll('div.slds-table_body tr span[title]').length,
                        fileLinksInBody: document.querySelectorAll('div.slds-table_body tr a[data-aura-class="forceFileCard"]').length,
                        fileRowsInBody: document.querySelectorAll('div.slds-table_body tr').length,
                        fileCellsInBody: document.querySelectorAll('div.slds-table_body td').length,
                        headerTitles: document.querySelectorAll('div.slds-table_header tr span[title]').length,
                        headerRows: document.querySelectorAll('div.slds-table_header tr').length,
                        tableContainer: document.querySelector('div.slds-table_container') ? 'found' : 'not found',
                        tableBody: document.querySelector('div.slds-table_body') ? 'found' : 'not found',
                        tableHeader: document.querySelector('div.slds-table_header') ? 'found' : 'not found',
                        
                        // New selectors for file list
                        fileListContainer: document.querySelector('div.slds-file-list') ? 'found' : 'not found',
                        fileListItems: document.querySelectorAll('div.slds-file-list li').length,
                        fileListCards: document.querySelectorAll('div.slds-file-list div.slds-card').length,
                        fileListLinks: document.querySelectorAll('div.slds-file-list a').length,
                        fileListTitles: document.querySelectorAll('div.slds-file-list span[title]').length,
                        
                        // New selectors for grid view
                        gridViewContainer: document.querySelector('div.slds-grid') ? 'found' : 'not found',
                        gridViewItems: document.querySelectorAll('div.slds-grid div.slds-card').length,
                        gridViewLinks: document.querySelectorAll('div.slds-grid a').length,
                        gridViewTitles: document.querySelectorAll('div.slds-grid span[title]').length
                    };
                    return elements;
                }""")
                logging.info(f"Table elements found: {table_info}")
                
                # Count actual items using multiple selectors
                actual_items = self.page.evaluate("""() => {
                    const selectors = [
                        'div.slds-file-list li',  // File list items
                        'div.slds-file-list div.slds-card',  // File list cards
                        'div.slds-file-list a',  // File list links
                        'div.slds-file-list span[title]',  // File list titles
                        'div.slds-grid div.slds-card',  // Grid view items
                        'div.slds-grid a',  // Grid view links
                        'div.slds-grid span[title]',  // Grid view titles
                        'span[title]',  // File titles
                        'a[title]',  // File links
                        'tr[data-row-id]',  // Table rows
                        'div[role="grid"] div[role="row"]',  // Grid rows
                        'li.slds-hint-parent',  // List items
                        'div.slds-scrollable_y li',  // Scrollable list items
                        'div[data-aura-class="forceFileCard"]',  // File cards
                        'tr a[data-aura-class="forceFileCard"]',  // File links in table
                        'tr span[title]',  // File titles in table
                        'div.slds-table_body tr span[title]',  // File titles in table body
                        'div.slds-table_body tr a[data-aura-class="forceFileCard"]',  // File links in table body
                        'div.slds-table_body tr',  // All rows in table body
                        'td[data-aura-class="forceFileCard"]',  // File cells
                        'li[data-aura-class="forceFileCard"]',  // File list items
                        'div.slds-card'  // Card containers
                    ];
                    
                    for (const selector of selectors) {
                        const elements = document.querySelectorAll(selector);
                        if (elements.length > 0) {
                            return elements.length;
                        }
                    }
                    return 0;
                }""")
                logging.info(f"Actual items found: {actual_items}")
                
                # If we have more than 50 items and no '+', we're done
                if actual_items > 50 and not str(initial_count).endswith('+'):
                    logging.info(f"Found {actual_items} items in table")
                    break
                
                # Try to scroll using multiple methods
                scroll_result = self.page.evaluate("""() => {
                    let scrolled = false;
                    let maxScrollHeight = 0;
                    
                    // Try different scrollable containers
                    const containers = [
                        'div.slds-scrollable_y',
                        'div[role="grid"]',
                        'div.slds-card__body',
                        'div.slds-table_header-fixed_container',
                        'div.slds-table',
                        'div.slds-card',
                        'div.slds-table_container',
                        'div.slds-table_fixed-layout',
                        'div.slds-table_body',
                        'div.slds-scrollable',
                        'div.slds-file-list',
                        'div.slds-grid',
                        'div.slds-scrollable_x',
                        'div.slds-scrollable_y',
                        'div.slds-scrollable_xy'
                    ];
                    
                    for (const selector of containers) {
                        const container = document.querySelector(selector);
                        if (container) {
                            // Get current scroll height
                            const scrollHeight = container.scrollHeight;
                            maxScrollHeight = Math.max(maxScrollHeight, scrollHeight);
                            
                            // Scroll to bottom
                            container.scrollTop = scrollHeight;
                            
                            // Try to trigger any lazy loading
                            setTimeout(() => {
                                container.scrollTop = 0;
                                setTimeout(() => {
                                    container.scrollTop = scrollHeight;
                                }, 100);
                            }, 100);
                            
                            scrolled = true;
                        }
                    }
                    
                    return { scrolled, maxScrollHeight };
                }""")
                
                # Wait for content to load
                self.page.wait_for_timeout(2000)
                
                # Try clicking any "Load More" or similar buttons
                try:
                    load_more_selectors = [
                        'button:has-text("Load More")',
                        'button:has-text("Show More")',
                        'button:has-text("View More")',
                        'button.slds-button:has-text("More")',
                        'button[title="Load More"]',
                        'button[title="Show More"]',
                        'button.slds-button_neutral:has-text("More")',
                        'button.slds-button_brand:has-text("More")',
                        'button.slds-button:has-text("Load More Files")',
                        'button.slds-button:has-text("Show More Files")',
                        'button.slds-button:has-text("Load More Items")',
                        'button.slds-button:has-text("Show More Items")',
                        'button.slds-button:has-text("View More Items")'
                    ]
                    
                    for selector in load_more_selectors:
                        load_more = self.page.locator(selector).first
                        if load_more and load_more.is_visible():
                            load_more.click()
                            self.page.wait_for_timeout(2000)
                            break
                except Exception as e:
                    logging.info(f"No load more button found: {str(e)}")
                
                # Get current count
                current_count = self.extract_files_count_from_status()
                logging.info(f"Current item count: {current_count}")
                
                # If we've reached a number without '+', we're done
                if isinstance(current_count, int) or (isinstance(current_count, str) and '+' not in str(current_count)):
                    logging.info("Reached actual count without '+' symbol")
                    break
                
                # If count hasn't changed for 5 attempts, try a different approach
                if str(current_count) == str(last_count):
                    no_change_count += 1
                    if no_change_count >= 5:
                        # Try to force a refresh of the table
                        try:
                            refresh_button = self.page.locator('button[title="Refresh"]').first
                            if refresh_button and refresh_button.is_visible():
                                refresh_button.click()
                                self.page.wait_for_timeout(2000)
                        except Exception as e:
                            logging.info(f"No refresh button found: {str(e)}")
                        
                        # If still no change, break
                        if str(current_count) == str(last_count):
                            logging.info("Count stabilized, stopping scroll")
                            break
                else:
                    no_change_count = 0
                
                last_count = current_count
                attempt += 1
                
            if attempt >= max_attempts:
                logging.warning("Reached maximum scroll attempts")
                
        except Exception as e:
            logging.error(f"Error during scrolling: {str(e)}")
            self.page.screenshot(path="scroll-error.png")

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