"""
Test Account Fuzzy Search

This test verifies the fuzzy search functionality for accounts in Salesforce. It:
1. Takes a list of account folder names from a file
2. Extracts the last name from each folder name
3. Searches for accounts in Salesforce CRM using the last name
4. Verifies the search results
"""

import os
import sys
from playwright.sync_api import sync_playwright, TimeoutError
import logging
from salesforce.pages.account_manager import AccountManager
from get_salesforce_page import get_salesforce_page
from salesforce.pages.accounts_page import AccountsPage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def read_account_folders(file_path: str) -> list:
    """
    Read account folders from a file.
    
    Args:
        file_path: Path to the file containing account folders
        
    Returns:
        list: List of account folder names
    """
    try:
        with open(file_path, 'r') as f:
            # Read lines and strip whitespace, skip empty lines
            folders = [line.strip() for line in f if line.strip()]
        logging.info(f"Read {len(folders)} account folders from {file_path}")
        return folders
    except Exception as e:
        logging.error(f"Error reading account folders file: {str(e)}")
        return []

# Get the root directory (parent of tests directory)
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Construct path to account_folders.txt in root directory
account_folders_file = os.path.join(root_dir, 'account_folders.txt')

# Read account folders from file
ACCOUNT_FOLDERS = read_account_folders(account_folders_file)

# If no folders were read, use a default for testing
if not ACCOUNT_FOLDERS:
    logging.warning("No account folders read from file, using default test folder")
    ACCOUNT_FOLDERS = ["Andrews, Kathleen"]

def extract_name_parts(folder_name: str) -> dict:
    """
    Extract name parts from a folder name.
    
    Args:
        folder_name: The full folder name string
        
    Returns:
        dict: Dictionary containing:
            - last_name: The last name
            - first_name: The first name (if available)
            - middle_name: The middle name (if available)
            - additional_info: Any additional info in parentheses
    """
    # Initialize result dictionary
    result = {
        'last_name': '',
        'first_name': '',
        'middle_name': '',
        'additional_info': ''
    }
    
    # Extract additional info in parentheses
    if '(' in folder_name:
        parts = folder_name.split('(')
        main_name = parts[0].strip()
        result['additional_info'] = parts[1].rstrip(')').strip()
    else:
        main_name = folder_name
    
    # Handle names with commas
    if ',' in main_name:
        parts = main_name.split(',')
        result['last_name'] = parts[0].strip()
        if len(parts) > 1:
            name_parts = parts[1].strip().split()
            if name_parts:
                result['first_name'] = name_parts[0]
                if len(name_parts) > 1:
                    result['middle_name'] = ' '.join(name_parts[1:])
    else:
        # Handle names with ampersands
        if '&' in main_name:
            parts = main_name.split('&')
            main_name = parts[0].strip()
        
        # Split remaining name parts
        name_parts = main_name.split()
        if len(name_parts) >= 2:
            # Last word is the last name
            result['last_name'] = name_parts[-1]
            result['first_name'] = name_parts[0]
            if len(name_parts) > 2:
                result['middle_name'] = ' '.join(name_parts[1:-1])
        else:
            result['last_name'] = main_name
    
    logging.info(f"Extracted name parts from '{folder_name}': {result}")
    return result

def get_account_names(page) -> list:
    """
    Extract account names from the current page.
    
    Args:
        page: The Playwright page object
        
    Returns:
        list: List of account names found on the page
    """
    account_names = []
    try:
        # Wait for table with timeout
        page.wait_for_selector('table[role="grid"]', timeout=5000)
        
        # Get all account rows
        rows = page.locator('table[role="grid"] tr').all()
        logging.info(f"Found {len(rows)} rows in the table")
        
        # Skip header row
        for row in rows[1:]:  # Skip the first row (header)
            try:
                # Try different selectors to find the account name
                selectors = [
                    'td:first-child a',  # Standard link in first cell
                    'td:first-child',    # First cell if no link
                    'td a',              # Any link in the row
                    'td'                 # Any cell
                ]
                
                for selector in selectors:
                    element = row.locator(selector).first
                    if element.count() > 0:
                        account_name = element.text_content(timeout=1000)
                        if account_name and account_name.strip():
                            account_names.append(account_name.strip())
                            logging.info(f"Found account using selector '{selector}': {account_name.strip()}")
                            break
            except Exception as e:
                logging.warning(f"Error getting account name: {str(e)}")
                continue
    except TimeoutError:
        logging.error("Timeout waiting for account table")
    except Exception as e:
        logging.error(f"Error extracting account names: {str(e)}")
    
    logging.info(f"Total accounts extracted: {len(account_names)}")
    logging.info(f"Extracted accounts: {account_names}")
    return account_names

def test_accounts_fuzzy_find():
    """
    Test fuzzy search functionality for accounts using last names from folder names.
    """
    with sync_playwright() as p:
        browser, page = get_salesforce_page(p)
        try:
            # Initialize managers
            account_manager = AccountManager(page, debug_mode=True)
            accounts_page = AccountsPage(page, debug_mode=True)
            
            # Navigate to accounts page
            if not account_manager.navigate_to_accounts_list_page():
                logging.error("Failed to navigate to accounts page")
                return
            
            # Dictionary to store results for each folder
            results = {}
            total_folders = len(ACCOUNT_FOLDERS)
            
            logging.info(f"\nStarting to process {total_folders} folders...")
            
            # Process each folder name
            for index, folder_name in enumerate(ACCOUNT_FOLDERS, 1):
                logging.info(f"\n[{index}/{total_folders}] Processing folder: {folder_name}")
                name_parts = extract_name_parts(folder_name)
                logging.info(f"Extracted name parts: {name_parts}")
                
                # Initialize result for this folder
                results[folder_name] = {
                    'status': 'Not Found',
                    'matches': [],
                    'search_attempts': []
                }
                
                try:
                    # Select "All Clients" view with timeout
                    logging.info("Selecting 'All Clients' view...")
                    if not accounts_page.select_list_view("All Clients"):
                        logging.error("Failed to select 'All Clients' view")
                        continue
                    
                    # Search by last name first with timeout
                    logging.info(f"Attempt 1/3: Searching by last name '{name_parts['last_name']}'...")
                    search_result = account_manager.search_account(name_parts['last_name'], view_name="All Clients")
                    
                    # Get matching account names
                    matching_accounts = []
                    if search_result > 0:
                        logging.info(f"Found {search_result} matches, extracting account names...")
                        matching_accounts = get_account_names(page)
                        logging.info(f"Extracted account names: {matching_accounts}")
                    
                    results[folder_name]['search_attempts'].append({
                        'type': 'last_name',
                        'query': name_parts['last_name'],
                        'matches': search_result,
                        'matching_accounts': matching_accounts
                    })
                    logging.info(f"Last name search complete: {search_result} matches")
                    logging.info(f"Stored matching accounts: {matching_accounts}")
                    
                    if search_result > 0:
                        # If we found matches, try to find the exact account
                        if name_parts['first_name']:
                            full_name = f"{name_parts['first_name']} {name_parts['last_name']}"
                            logging.info(f"Attempt 2/3: Checking for exact match '{full_name}'...")
                            if account_manager.account_exists(full_name, view_name="All Clients"):
                                logging.info(f"Found exact match: {full_name}")
                                results[folder_name]['status'] = 'Exact Match'
                                results[folder_name]['matches'].append(full_name)
                                # Add the exact match to the last search attempt's matching_accounts
                                if results[folder_name]['search_attempts']:
                                    results[folder_name]['search_attempts'][-1]['matching_accounts'].append(full_name)
                                continue
                        
                        # If no exact match, try searching with first name
                        if name_parts['first_name']:
                            logging.info(f"Attempt 2/3: Searching with full name '{name_parts['first_name']} {name_parts['last_name']}'...")
                            search_result = account_manager.search_account(f"{name_parts['first_name']} {name_parts['last_name']}", view_name="All Clients")
                            
                            # Get matching account names
                            matching_accounts = []
                            if search_result > 0:
                                logging.info(f"Found {search_result} matches, extracting account names...")
                                matching_accounts = get_account_names(page)
                                logging.info(f"Extracted account names: {matching_accounts}")
                            
                            results[folder_name]['search_attempts'].append({
                                'type': 'full_name',
                                'query': f"{name_parts['first_name']} {name_parts['last_name']}",
                                'matches': search_result,
                                'matching_accounts': matching_accounts
                            })
                            logging.info(f"Full name search complete: {search_result} matches")
                            logging.info(f"Stored matching accounts: {matching_accounts}")
                        
                        # If still no match, try searching with additional info
                        if name_parts['additional_info']:
                            search_query = f"{name_parts['last_name']} {name_parts['additional_info']}"
                            logging.info(f"Attempt 3/3: Searching with additional info '{search_query}'...")
                            search_result = account_manager.search_account(search_query, view_name="All Clients")
                            
                            # Get matching account names
                            matching_accounts = []
                            if search_result > 0:
                                logging.info(f"Found {search_result} matches, extracting account names...")
                                matching_accounts = get_account_names(page)
                                logging.info(f"Extracted account names: {matching_accounts}")
                            
                            results[folder_name]['search_attempts'].append({
                                'type': 'with_additional_info',
                                'query': search_query,
                                'matches': search_result,
                                'matching_accounts': matching_accounts
                            })
                            logging.info(f"Additional info search complete: {search_result} matches")
                            logging.info(f"Stored matching accounts: {matching_accounts}")
                        
                        # Update status if we found any matches
                        if any(attempt['matches'] > 0 for attempt in results[folder_name]['search_attempts']):
                            results[folder_name]['status'] = 'Partial Match'
                            # Add all unique matching accounts to the matches list
                            all_matches = set()
                            for attempt in results[folder_name]['search_attempts']:
                                if attempt['matching_accounts']:
                                    all_matches.update(attempt['matching_accounts'])
                            results[folder_name]['matches'] = list(all_matches)
                            logging.info(f"Found partial matches: {list(all_matches)}")
                
                except TimeoutError as e:
                    logging.error(f"Timeout error processing folder {folder_name}: {str(e)}")
                    continue
                except Exception as e:
                    logging.error(f"Error processing folder {folder_name}: {str(e)}")
                    continue
            
            # Print results summary
            logging.info("\n=== SALESFORCE ACCOUNT MATCHES ===")
            for folder_name, result in results.items():
                logging.info(f"\n📁 Searching for: {folder_name}")
                logging.info(f"📊 Status: {result['status']}")
                
                # Show all unique matches found across all search attempts
                all_matches = set()
                for attempt in result['search_attempts']:
                    if attempt['matching_accounts']:
                        all_matches.update(attempt['matching_accounts'])
                # Also include matches from the main matches list
                all_matches.update(result['matches'])
                
                if all_matches:
                    logging.info("\n✅ All matching accounts found in Salesforce:")
                    for match in sorted(all_matches):
                        logging.info(f"   • {match}")
                else:
                    logging.info("\n❌ No matching accounts found in Salesforce")
                
                logging.info("\n🔍 Search details:")
                for attempt in result['search_attempts']:
                    if attempt['matching_accounts']:
                        logging.info(f"\n   Search type: {attempt['type']}")
                        logging.info(f"   Query used: '{attempt['query']}'")
                        logging.info(f"   Found {attempt['matches']} matches:")
                        for account in sorted(attempt['matching_accounts']):
                            logging.info(f"      - {account}")
                logging.info("=" * 50)
            
        except Exception as e:
            logging.error(f"Test failed with error: {str(e)}")
        finally:
            browser.close()

if __name__ == "__main__":
    test_accounts_fuzzy_find() 