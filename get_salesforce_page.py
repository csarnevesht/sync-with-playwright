from playwright.sync_api import Playwright
import sys

def get_salesforce_page(playwright: Playwright, remote_url="http://localhost:9222", salesforce_domain="lightning.force.com"):
    """
    Connect to an existing Chrome browser and return the first Salesforce page found.
    """
    browser = playwright.chromium.connect_over_cdp(remote_url)
    salesforce_page = None
    for context in browser.contexts:
        for pg in context.pages:
            if salesforce_domain in pg.url:
                salesforce_page = pg
                break
        if salesforce_page:
            break
    if not salesforce_page:
        print(f"Error: No Salesforce page found. Please make sure you have a Salesforce page open at {salesforce_domain}.")
        browser.close()
        sys.exit(1)
    return browser, salesforce_page 