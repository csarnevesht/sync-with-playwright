"""
Browser initialization and management for Salesforce automation.
"""

import os
import sys
from playwright.sync_api import sync_playwright, Browser, Page
import logging
from src.sync.config import SALESFORCE_URL, SALESFORCE_USERNAME, SALESFORCE_PASSWORD, CHROME_DEBUG_PORT

def get_salesforce_page(playwright) -> tuple[Browser, Page]:
    """
    Connect to an existing Chrome browser and return the first Salesforce page found.
    
    Args:
        playwright: The Playwright instance
        
    Returns:
        tuple[Browser, Page]: A tuple containing the browser and page objects
        
    Raises:
        RuntimeError: If no Chrome browser is running or no Salesforce page is found
    """
    try:
        # Connect to existing Chrome browser
        remote_url = f"http://localhost:{CHROME_DEBUG_PORT}"
        try:
            browser = playwright.chromium.connect_over_cdp(remote_url)
        except Exception as e:
            raise RuntimeError(
                f"No Chrome browser found running on port {CHROME_DEBUG_PORT}. "
                "Please start Chrome with remote debugging enabled using:\n"
                f"chrome --remote-debugging-port={CHROME_DEBUG_PORT}"
            ) from e
        
        # Find Salesforce page
        salesforce_page = None
        for context in browser.contexts:
            for page in context.pages:
                if "lightning.force.com" in page.url:
                    salesforce_page = page
                    break
            if salesforce_page:
                break
                
        if not salesforce_page:
            browser.close()
            raise RuntimeError(
                "No Salesforce page found. Please make sure you have a Salesforce page open "
                f"at {SALESFORCE_URL}"
            )
            
        return browser, salesforce_page
        
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        logging.error(f"Error connecting to Chrome browser: {str(e)}")
        if 'browser' in locals():
            browser.close()
        raise RuntimeError(f"Failed to connect to Chrome browser: {str(e)}") 