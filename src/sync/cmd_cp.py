import os
import sys
import logging
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from src.sync.config import SALESFORCE_URL, CHROME_DEBUG_PORT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cp_services.log"),
        logging.StreamHandler()
    ]
)

def main():
    """Launch a browser with remote debugging and go to SALESFORCE_URL."""
    # Load environment variables
    load_dotenv()

    # Use Playwright to launch Chrome with remote debugging
    with sync_playwright() as p:
        # Launch a new browser with remote debugging enabled
        browser = p.chromium.launch(
            headless=False,
            args=[f'--remote-debugging-port={CHROME_DEBUG_PORT}']
        )
        page = browser.new_page()
        logging.info(f"Navigating to SALESFORCE_URL: {SALESFORCE_URL}")
        page.goto(SALESFORCE_URL)
        print(f"Opened {SALESFORCE_URL} in a new browser window.")
        input("Press Enter to close the browser...")
        browser.close()

if __name__ == "__main__":
    main() 