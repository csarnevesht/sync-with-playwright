import os
import sys
from playwright.sync_api import sync_playwright
import logging
from salesforce.pages.accounts_page import AccountsPage
import pytest
from get_salesforce_page import get_salesforce_page

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_get_all_accounts():
    """Test the get_all_accounts method of AccountsPage."""
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            # Initialize AccountsPage
            accounts_page = AccountsPage(page, debug_mode=True)
            
            # Test get_all_accounts
            assert accounts_page.get_all_accounts(), "Failed to get all accounts"
            
            # Verify we're on the accounts page
            current_url = page.url
            assert "/lightning/o/Account/list" in current_url, f"Not on accounts list page. Current URL: {current_url}"
            
            # Log and check all possible elements for the selected list view name
            logging.info("Checking for selected list view label in common elements...")
            found = False
            # Check spans
            for el in page.locator('span').all():
                if el.is_visible():
                    text = el.text_content() or ""
                    logging.info(f"span: {text}")
                    if "All Accounts" in text:
                        found = True
            # Check h1/h2
            for el in page.locator('h1, h2').all():
                if el.is_visible():
                    text = el.text_content() or ""
                    logging.info(f"h1/h2: {text}")
                    if "All Accounts" in text:
                        found = True
            # Check elements with class containing 'listView' or 'selected'
            for el in page.locator('[class*="listView"], [class*="selected"]').all():
                if el.is_visible():
                    text = el.text_content() or ""
                    logging.info(f"class*listView/selected: {text}")
                    if "All Accounts" in text:
                        found = True
            assert found, "List view not set to All Accounts. Could not find 'All Accounts' in any common label."
            
            # Verify the accounts table is visible
            assert page.locator('table[role="grid"]').is_visible(), "Accounts table not visible"
            
            logging.info("Test passed successfully")
            
        except Exception as e:
            logging.error(f"Test failed: {str(e)}")
            page.screenshot(path="test-failure.png")
            raise
        finally:
            browser.close()

if __name__ == "__main__":
    test_get_all_accounts() 