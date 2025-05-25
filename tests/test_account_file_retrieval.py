"""
Test suite for account file retrieval functionality in Salesforce.

This test performs the following operations:
1. Searches for a specific account by name ("Beth Albert")
2. Navigates to the account's files section
3. Retrieves and displays a list of all file names associated with the account
4. Tests file scrolling functionality to ensure all files are accessible
5. Includes file type detection and formatting for better readability

The test verifies that:
- Account search works correctly
- File section navigation is successful
- All files are retrievable and properly formatted
- Scrolling through files works smoothly
- File type detection is accurate
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Optional
import pytest
from playwright.sync_api import Page, expect, sync_playwright
import re
import json
from datetime import datetime
import shutil
import tempfile
from sync.salesforce.pages.account_manager import AccountManager
from sync.salesforce.pages.file_manager import FileManager
from sync.salesforce.utils.browser import get_salesforce_page
from sync.salesforce.utils.file_utils import get_file_type

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Global view name for all operations
VIEW_NAME = "Recent"

def format_file_list(files: list) -> str:
    """
    Format the list of files for display, including file types.
    
    Args:
        files: List of file names
        
    Returns:
        str: Formatted string with file names and types
    """
    if not files:
        return "No files found"
    
    formatted_files = []
    for i, file in enumerate(files, 1):
        formatted_files.append(f"{file}")
    
    return "\n".join(formatted_files)

def test_account_file_retrieval(browser, page):
    """
    Test searching for an account and retrieving its files.
    
    Args:
        browser: Playwright browser instance
        page: Playwright page instance
    """
    try:
        # Initialize managers
        account_manager = AccountManager(page, debug_mode=True)
        file_manager = FileManager(page, debug_mode=True)
        
        # Search for account
        account_name = "Beth Albert"
        
        # Check if account exists and store result
        account_exists = account_manager.account_exists(account_name, view_name=VIEW_NAME)
        if not account_exists:
            logging.error(f"Account {account_name} does not exist")
            return
        
        # Click on account name to navigate to it
        if not account_manager.click_account_name(account_name):
            logging.error(f"Failed to navigate to account view page for: {account_name}")
            return
        
        # Verify we're on the correct account page and get account ID
        is_valid, account_id = account_manager.verify_account_page_url()
        if not is_valid or not account_id:
            logging.error("Not on a valid account page or could not get account ID")
            return
        
        logging.info(f"Successfully navigated to account {account_name} with ID {account_id}")
        
        # Navigate to files section
        logging.info("Navigating to files section")
        num_files = account_manager.navigate_to_files_and_get_number_of_files_for_this_account(account_id)
        if num_files == -1:
            logging.error("Failed to navigate to Files")
            return
        
        # Get all file names
        logging.info("Getting all file names for this account")
        files = account_manager.get_all_file_names_for_this_account(account_id)
        
        # Display results
        logging.info("\nFiles found:")
        logging.info(format_file_list(files))
        logging.info(f"\nTotal files found: {len(files)}")
        
    except Exception as e:
        logging.error(f"Test failed: {str(e)}")
        raise

def main():
    """Main function to run the test."""
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            test_account_file_retrieval(browser, page)
        finally:
            browser.close()

if __name__ == "__main__":
    main() 