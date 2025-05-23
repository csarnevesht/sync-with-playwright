"""
Browser initialization and management for Salesforce automation.
"""

import os
import sys
from playwright.sync_api import sync_playwright, Browser, Page
import logging
from config import SALESFORCE_URL, SALESFORCE_USERNAME, SALESFORCE_PASSWORD

def get_salesforce_page(playwright) -> tuple[Browser, Page]:
    """
    Initialize a browser and navigate to Salesforce login page.
    
    Args:
        playwright: The Playwright instance
        
    Returns:
        tuple[Browser, Page]: A tuple containing the browser and page objects
    """
    try:
        # Launch browser
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # Navigate to Salesforce
        page.goto(SALESFORCE_URL)
        
        # Login to Salesforce
        page.fill('input[name="username"]', SALESFORCE_USERNAME)
        page.fill('input[name="pw"]', SALESFORCE_PASSWORD)
        page.click('input[name="Login"]')
        
        # Wait for navigation to complete
        page.wait_for_load_state('networkidle')
        
        return browser, page
        
    except Exception as e:
        logging.error(f"Error initializing Salesforce page: {str(e)}")
        if 'browser' in locals():
            browser.close()
        sys.exit(1) 