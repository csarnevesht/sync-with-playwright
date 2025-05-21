import logging
import sys

def debug_prompt(message: str) -> bool:
    """
    Prompt the user for input in debug mode.
    
    Args:
        message (str): The message to display to the user
        
    Returns:
        bool: True if the user wants to proceed, False otherwise
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Debug prompt: {message}")
    
    while True:
        response = input(f"{message} (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            logger.info("Invalid response. Please enter 'y' or 'n'.") 