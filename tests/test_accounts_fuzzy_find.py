"""
Test Account Fuzzy Search

This test verifies the fuzzy search functionality for accounts in Salesforce. It:
1. Takes a list of account folder names
2. Extracts the last name from each folder name
3. Searches for accounts in Salesforce CRM using the last name
4. Verifies the search results
"""

import os
import sys
from playwright.sync_api import sync_playwright
import logging
from salesforce.pages.account_manager import AccountManager
from get_salesforce_page import get_salesforce_page
from salesforce.pages.accounts_page import AccountsPage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# List of account folder names
ACCOUNT_FOLDERS = [
    "Alexander & Armelia Rolle",
    "Alvarez, Vilma (Medicaid Mike)",
    "Amaran Martin & Teresita",
    "Andrews, Kathleen",
    "Ayers, Charles nephew Wes Myers",
    "Barnett, Audrey daughter Susan Stewart",
    "Bauer Glenn and Brenda",
    "Bishop, Sonia (Mike)",
    "Brundage, Arnold (Mike)",
    "Busto Pina, Rosa Daughter Carolina (Medicaid Mike)",
    "Campos, Maria",
    "Cohen, Beverly",
    "Colon, Noel (Medicaid Mike)",
    "Dilts, Suetta",
    "Fitzgerald Bridget daughter Elizabeth Robbert",
    "Frost, Theresia (Mike)",
    "Garica, Nicolas & Daughter Marie Chavarri (Medicaid Mike)",
    "Jones, Elisa son Charles Byron Jones IIIII",
    "Kazakian, George (Mike)",
    "Matalon, Dennis",
    "McNabb, Frances daughter Pam Murphy",
    "Montesino, Maria",
    "Strinko Mary sons Greg and Steve",
    "Whitfield, Paul  daughter Musibay",
    "Yi, Francisco (Medicaid Mike)"
]

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
            result['last_name'] = name_parts[-1]
            result['first_name'] = name_parts[0]
            if len(name_parts) > 2:
                result['middle_name'] = ' '.join(name_parts[1:-1])
        else:
            result['last_name'] = main_name
    
    return result

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
                
                # Select "All Clients" view
                logging.info("Selecting 'All Clients' view...")
                accounts_page.select_list_view("All Clients")
                
                # Search by last name first
                logging.info(f"Attempt 1/3: Searching by last name '{name_parts['last_name']}'...")
                search_result = account_manager.search_account(name_parts['last_name'], view_name="All Clients")
                
                # Get matching account names
                matching_accounts = []
                if search_result > 0:
                    logging.info(f"Found {search_result} matches, extracting account names...")
                    # Get all account rows
                    account_rows = page.locator('table[role="grid"] tr').all()
                    for row in account_rows:
                        try:
                            name_cell = row.locator('td:first-child a').first
                            if name_cell:
                                account_name = name_cell.text_content().strip()
                                matching_accounts.append(account_name)
                        except Exception as e:
                            logging.warning(f"Error getting account name: {str(e)}")
                
                results[folder_name]['search_attempts'].append({
                    'type': 'last_name',
                    'query': name_parts['last_name'],
                    'matches': search_result,
                    'matching_accounts': matching_accounts
                })
                logging.info(f"Last name search complete: {search_result} matches")
                
                if search_result > 0:
                    # If we found matches, try to find the exact account
                    if name_parts['first_name']:
                        full_name = f"{name_parts['first_name']} {name_parts['last_name']}"
                        logging.info(f"Attempt 2/3: Checking for exact match '{full_name}'...")
                        if account_manager.account_exists(full_name, view_name="All Clients"):
                            logging.info(f"Found exact match: {full_name}")
                            results[folder_name]['status'] = 'Exact Match'
                            results[folder_name]['matches'].append(full_name)
                            continue
                    
                    # If no exact match, try searching with first name
                    if name_parts['first_name']:
                        logging.info(f"Attempt 2/3: Searching with full name '{name_parts['first_name']} {name_parts['last_name']}'...")
                        search_result = account_manager.search_account(f"{name_parts['first_name']} {name_parts['last_name']}", view_name="All Clients")
                        
                        # Get matching account names
                        matching_accounts = []
                        if search_result > 0:
                            logging.info(f"Found {search_result} matches, extracting account names...")
                            account_rows = page.locator('table[role="grid"] tr').all()
                            for row in account_rows:
                                try:
                                    name_cell = row.locator('td:first-child a').first
                                    if name_cell:
                                        account_name = name_cell.text_content().strip()
                                        matching_accounts.append(account_name)
                                except Exception as e:
                                    logging.warning(f"Error getting account name: {str(e)}")
                        
                        results[folder_name]['search_attempts'].append({
                            'type': 'full_name',
                            'query': f"{name_parts['first_name']} {name_parts['last_name']}",
                            'matches': search_result,
                            'matching_accounts': matching_accounts
                        })
                        logging.info(f"Full name search complete: {search_result} matches")
                    
                    # If still no match, try searching with additional info
                    if name_parts['additional_info']:
                        search_query = f"{name_parts['last_name']} {name_parts['additional_info']}"
                        logging.info(f"Attempt 3/3: Searching with additional info '{search_query}'...")
                        search_result = account_manager.search_account(search_query, view_name="All Clients")
                        
                        # Get matching account names
                        matching_accounts = []
                        if search_result > 0:
                            logging.info(f"Found {search_result} matches, extracting account names...")
                            account_rows = page.locator('table[role="grid"] tr').all()
                            for row in account_rows:
                                try:
                                    name_cell = row.locator('td:first-child a').first
                                    if name_cell:
                                        account_name = name_cell.text_content().strip()
                                        matching_accounts.append(account_name)
                                except Exception as e:
                                    logging.warning(f"Error getting account name: {str(e)}")
                        
                        results[folder_name]['search_attempts'].append({
                            'type': 'with_additional_info',
                            'query': search_query,
                            'matches': search_result,
                            'matching_accounts': matching_accounts
                        })
                        logging.info(f"Additional info search complete: {search_result} matches")
                    
                    # Update status if we found any matches
                    if any(attempt['matches'] > 0 for attempt in results[folder_name]['search_attempts']):
                        results[folder_name]['status'] = 'Partial Match'
                        # Add all unique matching accounts to the matches list
                        all_matches = set()
                        for attempt in results[folder_name]['search_attempts']:
                            all_matches.update(attempt['matching_accounts'])
                        results[folder_name]['matches'] = sorted(list(all_matches))
                else:
                    logging.info(f"No matches found for {name_parts['last_name']}")
                
                logging.info(f"Completed processing folder {index}/{total_folders}")
            
            # Print summary report
            logging.info("\n" + "="*80)
            logging.info("SUMMARY REPORT")
            logging.info("="*80)
            
            # Count statistics
            exact_matches = sum(1 for r in results.values() if r['status'] == 'Exact Match')
            partial_matches = sum(1 for r in results.values() if r['status'] == 'Partial Match')
            not_found = sum(1 for r in results.values() if r['status'] == 'Not Found')
            
            logging.info(f"\nTotal folders processed: {total_folders}")
            logging.info(f"Exact matches found: {exact_matches}")
            logging.info(f"Partial matches found: {partial_matches}")
            logging.info(f"No matches found: {not_found}")
            
            # Print detailed results
            logging.info("\nDetailed Results:")
            logging.info("-"*80)
            
            for index, (folder_name, result) in enumerate(results.items(), 1):
                logging.info(f"\n[{index}/{total_folders}] Folder: {folder_name}")
                logging.info(f"Status: {result['status']}")
                if result['matches']:
                    logging.info("Matching accounts found:")
                    for match in result['matches']:
                        logging.info(f"  - {match}")
                logging.info("Search attempts:")
                for attempt in result['search_attempts']:
                    logging.info(f"  - {attempt['type']}: '{attempt['query']}' -> {attempt['matches']} matches")
                    if attempt['matching_accounts']:
                        logging.info("    Matching accounts:")
                        for account in attempt['matching_accounts']:
                            logging.info(f"      * {account}")
            
            logging.info("\n" + "="*80)
                
        except Exception as e:
            logging.error(f"Test failed: {str(e)}")
            page.screenshot(path="test-failure.png")
            raise
        finally:
            browser.close()

def main():
    """Run the fuzzy search test."""
    test_accounts_fuzzy_find()

if __name__ == "__main__":
    main() 