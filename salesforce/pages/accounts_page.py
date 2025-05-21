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
        """Prompt the user for input in debug mode."""
        if not self.debug_mode:
            return True
            
        while True:
            response = input(f"{message} (y/n): ").lower()
            if response in ['y', 'Y']:
                return response == 'y'
            logging.info("Please enter 'y' or 'n'")

    def navigate_to_accounts(self) -> bool:
        """Navigate to the Accounts page."""
        target_url = f"{SALESFORCE_URL}/lightning/o/Account/list?filterName=__Recent"
        logging.info(f"Navigating to Accounts page: {target_url}")
        
        try:
            # Check if we're already on the accounts page
            current_url = self.page.url
            if "/lightning/o/Account/list" in current_url:
                logging.info("Already on Accounts page")
                # Wait for the page to be fully loaded
                self.page.wait_for_load_state('networkidle', timeout=10000)
            else:
                # Navigate to the page
                self.page.goto(target_url)
                # Wait for the page to be fully loaded
                self.page.wait_for_load_state('networkidle', timeout=30000)
            
            # Wait for the search input
            search_input = self.page.wait_for_selector('input[placeholder="Search this list..."]', timeout=10000)
            if not search_input:
                logging.error("Search input not found")
                self.page.screenshot(path="accounts-navigation-error.png")
                return False
            
            # Wait for the table to be visible
            table = self.page.wait_for_selector('table[role="grid"]', timeout=10000)
            if not table:
                logging.error("Accounts table not found")
                self.page.screenshot(path="accounts-table-not-found.png")
                return False
                
            if not table.is_visible():
                logging.error("Accounts table not visible")
                self.page.screenshot(path="accounts-table-not-visible.png")
                return False
            
            # Additional wait to ensure everything is stable
            self.page.wait_for_timeout(2000)
            
            logging.info("Successfully navigated to Accounts page")
            return True
            
        except Exception as e:
            logging.error(f"Error navigating to Accounts page: {str(e)}")
            self.page.screenshot(path="accounts-navigation-error.png")
            return False

    def get_all_accounts(self) -> bool:
        """
        Navigate to accounts and select the "All Accounts" list view.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Navigate to accounts page
            if not self.navigate_to_accounts():
                logging.error("Failed to navigate to Accounts page")
                return False
                
            # Click the list view selector
            logging.info("Clicking list view selector...")
            list_view_button = self.page.wait_for_selector('button[title="Select a List View: Accounts"]', timeout=10000)
            if not list_view_button:
                logging.error("Could not find list view selector button")
                return False
                
            list_view_button.click()
            logging.info("Clicked list view selector")
            
            # Wait for the dropdown content to appear
            logging.info("Selecting 'All Accounts' from list view...")
            self.page.wait_for_timeout(1000)  # Give time for dropdown animation
            
            # Find any visible element containing 'All Accounts'
            all_accounts_options = self.page.locator('text="All Accounts"').all()
            visible_option = None
            for option in all_accounts_options:
                if option.is_visible():
                    visible_option = option
                    break
            if not visible_option:
                logging.error("Could not find visible 'All Accounts' option")
                self.page.screenshot(path="all-accounts-not-found.png")
                return False
            visible_option.click()
            logging.info("Selected 'All Accounts' list view")
            
            # Log the text of all visible elements near the list view selector
            logging.info("Logging visible elements near the list view selector for debugging...")
            parent = list_view_button.evaluate_handle('node => node.parentElement')
            siblings = parent.evaluate('node => Array.from(node.children).map(child => child.textContent)')
            logging.info(f"Sibling texts of list view button: {siblings}")
            # Also log the text of the button itself
            button_text = list_view_button.text_content()
            logging.info(f"List view button text: {button_text}")
            
            # Wait for the list to update and stabilize
            self.page.wait_for_load_state('networkidle', timeout=10000)
            self.page.wait_for_selector('table[role="grid"]', timeout=10000)
            
            # Additional wait to ensure the list view is fully loaded
            self.page.wait_for_timeout(2000)

            return True

        except Exception as e:
            logging.error(f"Error selecting All Accounts list view: {str(e)}")
            self.page.screenshot(path="list-view-error.png")
            return False 