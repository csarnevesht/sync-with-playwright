from playwright.sync_api import Page, TimeoutError
import logging
import time
from typing import Optional, Any, List
from .selectors import Selectors

class BasePage:
    """Base class for all page objects with common functionality."""
    
    def __init__(self, page: Page, debug_mode: bool = False):
        self.page = page
        self.debug_mode = debug_mode
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def _wait_for_selector(self, category: str, key: str, timeout: int = 3000) -> Optional[Any]:
        """Wait for a selector to be visible and return the element."""
        selectors = Selectors.get_selectors(category, key)
        for selector in selectors:
            try:
                element = self.page.wait_for_selector(selector, timeout=timeout)
                if element and element.is_visible():
                    return element
            except TimeoutError:
                continue
        return None
        
    def _click_element(self, category: str, key: str, timeout: int = 3000) -> bool:
        """Click an element using various strategies."""
        element = self._wait_for_selector(category, key, timeout)
        if not element:
            return False
            
        try:
            # Try normal click
            element.click()
            return True
        except Exception:
            try:
                # Try JavaScript click
                self.page.evaluate('(element) => element.click()', element)
                return True
            except Exception:
                try:
                    # Try scrolling into view and clicking
                    element.scroll_into_view_if_needed()
                    time.sleep(1)  # Wait for scroll
                    element.click()
                    return True
                except Exception as e:
                    self.logger.error(f"Failed to click element: {str(e)}")
                    return False
                    
    def _fill_input(self, category: str, key: str, value: str, timeout: int = 3000) -> bool:
        """Fill an input field with a value."""
        element = self._wait_for_selector(category, key, timeout)
        if not element:
            return False
            
        try:
            element.fill(value)
            return True
        except Exception as e:
            self.logger.error(f"Failed to fill input: {str(e)}")
            return False
            
    def _debug_prompt(self, message: str) -> bool:
        """Prompt the user for confirmation in debug mode."""
        if not self.debug_mode:
            return True
            
        while True:
            response = input(f"\n{message} (y/n): ").lower().strip()
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            print("Please enter 'y' or 'n'")
            
    def _take_screenshot(self, name: str) -> None:
        """Take a screenshot for debugging purposes."""
        try:
            self.page.screenshot(path=f"{name}.png")
            self.logger.info(f"Screenshot saved as {name}.png")
        except Exception as e:
            self.logger.error(f"Failed to take screenshot: {str(e)}")
            
    def _retry_operation(self, operation: callable, max_retries: int = 3, 
                        delay: int = 1000) -> Any:
        """Retry an operation with exponential backoff."""
        for attempt in range(max_retries):
            try:
                return operation()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                self.logger.warning(f"Operation failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                time.sleep(delay * (2 ** attempt)) 