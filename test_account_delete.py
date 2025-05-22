import os
import sys
import logging
from playwright.sync_api import sync_playwright
from salesforce.pages.account_manager import AccountManager
from get_salesforce_page import get_salesforce_page
from mock_data import get_mock_accounts

def delete_account(account_manager: AccountManager, full_name: str) -> bool:
    """
    Delete an account by name.
    
    Args:
        account_manager: AccountManager instance
        full_name: Full name of the account to delete
        
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        # Search for the account
        if not account_manager.account_exists(full_name):
            logging.error(f"Account {full_name} does not exist")
            return False
            
        # Click on the account name to navigate to it
        if not account_manager.click_account_name(full_name):
            logging.error(f"Failed to navigate to account view page for: {full_name}")
            return False
            
        # Verify we're on the correct account page
        is_valid, account_id = account_manager.verify_account_page_url()
        if not is_valid:
            logging.error("Not on a valid account page")
            return False
            
        logging.info(f"Successfully navigated to account {full_name} with ID {account_id}")
        
        # Wait for page to load completely and stabilize
        account_manager.page.wait_for_load_state('networkidle')
        account_manager.page.wait_for_timeout(2000)
        
        # Step 1: Click the left-panel Delete button (try several selectors and log all candidates)
        delete_selectors = [
            "button[title='Delete']",
            "button:has-text('Delete')",
            "input[value='Delete']",
            "a[title='Delete']",
            "a:has-text('Delete')",
        ]
        delete_btn = None
        for selector in delete_selectors:
            try:
                elements = account_manager.page.query_selector_all(selector)
                for el in elements:
                    try:
                        visible = el.is_visible()
                        enabled = el.is_enabled()
                        text = el.text_content()
                        attrs = el.get_attribute('outerHTML')
                        logging.info(f"Delete button candidate: selector={selector}, visible={visible}, enabled={enabled}, text={text}, outerHTML={attrs}")
                        if visible and enabled:
                            delete_btn = el
                            break
                    except Exception as e:
                        logging.info(f"Error checking delete button candidate: {e}")
                if delete_btn:
                    logging.info(f"Found delete button with selector: {selector}")
                    break
            except Exception as e:
                logging.info(f"Error finding delete button with selector {selector}: {e}")
                continue
        if not delete_btn:
            logging.error("Could not find enabled/visible left-panel Delete button with any selector")
            account_manager.page.screenshot(path="delete-btn-not-found.png")
            return False
        try:
            delete_btn.click()
            logging.info("Clicked left-panel Delete button.")
        except Exception as e:
            logging.error(f"Error clicking left-panel Delete button: {e}")
            account_manager.page.screenshot(path="delete-btn-click-error.png")
            return False
        account_manager.page.wait_for_timeout(1000)
        # Step 2: Wait for the modal and confirm deletion
        try:
            account_manager.page.wait_for_selector('button[title="Delete"] span.label.bBody', timeout=5000)
        except Exception:
            logging.error("Delete confirmation modal did not appear after clicking delete button")
            account_manager.page.screenshot(path="delete-modal-not-found.png")
            return False
        # Log modal text for debugging
        try:
            modal = account_manager.page.query_selector('div[role="dialog"]')
            if modal:
                modal_text = modal.text_content()
                logging.info(f"Delete modal text: {modal_text}")
        except Exception:
            pass
        # Click the modal's Delete button using the provided selector
        try:
            modal_delete_btn_span = account_manager.page.wait_for_selector('button[title="Delete"] span.label.bBody', timeout=5000)
            if not modal_delete_btn_span:
                logging.error("Could not find modal Delete button span.label.bBody")
                account_manager.page.screenshot(path="modal-delete-btn-not-found.png")
                return False
            modal_delete_btn_span.click()
            logging.info("Clicked modal Delete button.")
        except Exception as e:
            logging.error(f"Error clicking modal Delete button: {e}")
            account_manager.page.screenshot(path="modal-delete-btn-click-error.png")
            return False
        # Wait for the modal to close
        try:
            account_manager.page.wait_for_selector('button[title="Delete"] span.label.bBody', state='detached', timeout=8000)
            logging.info("Delete confirmation modal closed.")
        except Exception:
            logging.warning("Delete confirmation modal did not close in time.")
        # Wait for deletion confirmation (toast)
        try:
            account_manager.page.wait_for_selector('div.slds-notify_toast, div.slds-notify--toast', timeout=15000)
            logging.info(f"Successfully deleted account: {full_name}")
            return True
        except Exception as e:
            logging.warning(f"Could not confirm account deletion by toast: {str(e)}. Checking if account still exists.")
            # Fallback: check if account still exists
            account_manager.navigate_to_accounts_list_page()
            if not account_manager.account_exists(full_name):
                logging.info(f"Account {full_name} no longer exists. Deletion successful.")
                return True
            else:
                logging.error(f"Account {full_name} still exists after attempted deletion.")
                account_manager.page.screenshot(path="delete-toast-not-found.png")
                return False
    except Exception as e:
        logging.error(f"Error deleting account {full_name}: {str(e)}")
        account_manager.page.screenshot(path="delete-error.png")
        return False

def main():
    # Enable debug mode
    debug_mode = True
    logging.basicConfig(level=logging.INFO)
    
    # Get mock account data
    mock_accounts = get_mock_accounts()
    test_account = mock_accounts[0]  # Use John Smith's account for testing
    
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            # Initialize managers
            account_manager = AccountManager(page, debug_mode=debug_mode)
            
            # Navigate to Accounts page
            assert account_manager.navigate_to_accounts_list_page(), "Failed to navigate to Accounts page"
            
            # Get full name
            full_name = f"{test_account['first_name']} {test_account['last_name']}"
            logging.info(f"Searching for account: {full_name}")
            
            # Delete the account
            if delete_account(account_manager, full_name):
                logging.info("Test completed successfully")
            else:
                logging.error("Failed to delete account")
                sys.exit(1)
                
        except Exception as e:
            logging.error(f"Test failed: {str(e)}")
            page.screenshot(path="test-failure.png")
            raise
        finally:
            browser.close()

if __name__ == "__main__":
    main() 