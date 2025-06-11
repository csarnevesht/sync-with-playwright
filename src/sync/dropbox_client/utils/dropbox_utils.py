"""Utility functions for Dropbox operations."""

import os
import sys
import dropbox
from dropbox.exceptions import ApiError
from dropbox.files import FileMetadata
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
import re
import pdf2image
import pytesseract
from PIL import Image
import tempfile
import PyPDF2
import logging
import urllib.parse
from dotenv import load_dotenv
import pandas as pd
from sync.salesforce_client.pages.account_manager import LoggingHelper
import json
from PIL import ImageEnhance
import numpy as np
import cv2
import difflib

from .date_utils import has_date_prefix, get_folder_creation_date
from .path_utils import clean_dropbox_folder_name
from .file_utils import log_renamed_file
from src.config import DROPBOX_FOLDER, ACCOUNT_INFO_PATTERN, DRIVERS_LICENSE_PATTERN, DROPBOX_HOLIDAY_FOLDER, DROPBOX_SALESFORCE_FOLDER, DROPBOX_HOLIDAY_FILE

# Configure logging
# Get the logger for this module
logger = logging.getLogger(__name__)

# Set Dropbox logger level to WARNING to suppress INFO messages
logging.getLogger('dropbox').setLevel(logging.WARNING)

def construct_dropbox_path(account_folder: str, root_folder: str) -> Optional[str]:
    """
    Construct and validate a Dropbox folder from the root folder and account folder.
    
    Args:
        account_folder (str): The account folder path to append to root folder
        root_folder (str): The root folder path
            
    Returns:
        Optional[str]: The cleaned and validated Dropbox folder, or None if invalid
    """
    try:
        clean_account_folder = account_folder.strip()
        if not clean_account_folder:
            logging.error("Account folder cannot be empty")
            return None
            
        full_path = os.path.join(root_folder, clean_account_folder)
        clean_path = clean_dropbox_folder_name(full_path)
        
        if not clean_path:
            logging.error(f"Invalid path constructed: {full_path}")
            return None
            
        logging.debug(f"Constructed Dropbox folder: {clean_path}")
        return clean_path
        
    except Exception as e:
        logging.error(f"Error constructing Dropbox folder: {str(e)}")
        return None

class DropboxClient:
    def __init__(self, token: str, debug_mode: bool = False):
        self.token = token
        self.debug_mode = debug_mode
        self.dbx = dropbox.Dropbox(token)
        
        # Get the root folder from environment
        folder = DROPBOX_FOLDER
        if folder.startswith('http'):
            # Extract the path from the URL
            parsed_url = urllib.parse.urlparse(folder)
            # Get the path and remove 'home' from the start
            path = parsed_url.path.lstrip('/')
            if path.startswith('home/'):
                path = path[5:]  # Remove 'home/'
            # URL decode the path
            folder = urllib.parse.unquote(path)
        
        self.root_folder = folder
        self.root_folder = clean_dropbox_folder_name(folder)

        # Get the holiday folder from environment
        dropbox_holiday_folder = DROPBOX_HOLIDAY_FOLDER
        if dropbox_holiday_folder and dropbox_holiday_folder.startswith('http'):
            parsed_url = urllib.parse.urlparse(dropbox_holiday_folder)
            path = parsed_url.path.lstrip('/')
            if path.startswith('home/'):
                path = path[5:]
            dropbox_holiday_folder = urllib.parse.unquote(path)
        
        self.dropbox_holiday_folder = dropbox_holiday_folder
        logging.info(f"Dropbox holiday folder: {dropbox_holiday_folder}")
        self.dropbox_holiday_path = clean_dropbox_folder_name(dropbox_holiday_folder) if dropbox_holiday_folder else None
        logging.info(f"Dropbox holiday path: {self.dropbox_holiday_path}")

        # Get the Salesforce folder from environment
        dropbox_salesforce_folder = DROPBOX_SALESFORCE_FOLDER
        if dropbox_salesforce_folder and dropbox_salesforce_folder.startswith('http'):
            parsed_url = urllib.parse.urlparse(dropbox_salesforce_folder)
            path = parsed_url.path.lstrip('/')
            if path.startswith('home/'):
                path = path[5:]
            dropbox_salesforce_folder = urllib.parse.unquote(path)
        
        self.dropbox_salesforce_folder = dropbox_salesforce_folder
        logging.info(f"Dropbox Salesforce folder: {dropbox_salesforce_folder}")
        self.dropbox_salesforce_path = clean_dropbox_folder_name(dropbox_salesforce_folder) if dropbox_salesforce_folder else None
        logging.info(f"Dropbox Salesforce path: {self.dropbox_salesforce_path}")

        logging.info(f"Initialized DropboxClient with root folder: {self.root_folder}")
        if self.dropbox_holiday_folder:
            logging.info(f"Holiday folder: {self.dropbox_holiday_folder}")
        if self.dropbox_salesforce_folder:
            logging.info(f"Salesforce folder: {self.dropbox_salesforce_folder}")
        if debug_mode:
            logging.info("Debug mode is enabled")

    def _handle_token_expiration(self):
        """Handle token expiration by refreshing the token."""
        try:
            new_token = refresh_access_token()
            self.token = new_token
            self.dbx = dropbox.Dropbox(new_token)
            logger.info("Successfully refreshed token and reinitialized client")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh token: {str(e)}")
            return False

    def _make_request(self, func, *args, **kwargs):
        """
        Make a request to Dropbox API with automatic token refresh.
        
        Args:
            func: The Dropbox API function to call
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the API call
        """
        try:
            return func(*args, **kwargs)
        except ApiError as e:
            if e.error.is_expired_access_token():
                logger.info("Access token expired, attempting to refresh...")
                if self._handle_token_expiration():
                    # Retry the request with the new token
                    return func(*args, **kwargs)
            raise

    def _debug_show_files(self, account_name: str, files: List[FileMetadata], skip_patterns: List[str] = None) -> List[FileMetadata]:
        """
        Show files to be processed and which ones will be skipped.
        Returns the list of files that will be processed.
        """
        if not self.debug_mode:
            return files

        print(f"\nDropbox account files to be processed for {account_name}:")
        files_to_process = []
        for file in files:
            should_skip = False
            if skip_patterns:
                for pattern in skip_patterns:
                    if re.match(pattern, file.name):
                        should_skip = True
                        print(f"  - {file.name} (will be skipped - matches pattern: {pattern})")
                        break
            
            if not should_skip:
                files_to_process.append(file)
                print(f"  + {file.name} (will be processed)")

        return files_to_process
            

    def get_dropbox_account_names(self) -> List[str]:
        """Get all account folders under the root folder."""
        try:
            entries = list_dropbox_folder_contents(self.dbx, self.root_folder)
            result = [entry.name for entry in entries if isinstance(entry, dropbox.files.FolderMetadata)]            
            return result
        except Exception as e:
            print(f"Error getting account folders: {e}")
            return []
        
    def get_dropbox_account_files(self, account_folder: str) -> List[FileMetadata]:
        """Get all files under the account folder."""
        try:
            dropbox_path = construct_dropbox_path(account_folder, self.root_folder)
            return list_dropbox_folder_contents(self.dbx, dropbox_path)
        except Exception as e:
            print(f"Error getting account files: {e}")
            return []
        
    def get_dropbox_holiday_folder(self) -> Optional[str]:
        """Get the configured Dropbox holiday folder path."""
        return self.dropbox_holiday_path
    
    def get_dropbox_holiday_file(self, holiday_file: str = None) -> Optional[FileMetadata]:
        """Get the specified holiday file from the holiday folder."""
        if not self.dropbox_holiday_path:
            logging.warning("Dropbox holiday folder path is not set.")
            return None
            
        # Use the provided holiday_file or the default from environment
        holiday_file = holiday_file or DROPBOX_HOLIDAY_FILE
        logging.info(f"Getting holiday file: {holiday_file} from {self.dropbox_holiday_path}")

        # Check if we already have the file info cached
        if hasattr(self, 'dropbox_holiday_file_metadata') and \
           self.dropbox_holiday_file_metadata and \
           self.dropbox_holiday_file_metadata.name == holiday_file:
            return self.dropbox_holiday_file_metadata

        try:
            entries = list_dropbox_folder_contents(self.dbx, self.dropbox_holiday_path)
            # log the entries' names
            logging.info(f"Entries in holiday folder: {[entry.name for entry in entries]}")
            for entry in entries:
                if isinstance(entry, FileMetadata) and entry.name == holiday_file:
                    self.dropbox_holiday_file_metadata = entry # Cache the file metadata
                    logging.info(f"Found holiday file: {entry.name} in {self.dropbox_holiday_path}")
                    return entry
            logging.warning(f"Holiday file '{holiday_file}' not found in {self.dropbox_holiday_path}")
            return None
        except Exception as e:
            logging.error(f"Error getting holiday file '{holiday_file}' from {self.dropbox_holiday_path}: {e}")
            return None
        
    

    def _clean_cell_value(self, value: str) -> str:
        """Clean cell value by removing parenthetical content and extra whitespace."""
        if pd.isna(value):
            return ''
        # Convert to string and remove anything after and including '('
        cleaned = str(value).split('(')[0].strip()
        # if cleaned != value: 
        #     logging.info(f"Cleaned cell value: {cleaned} original: {value}")
        return cleaned
    
    def _check_row_for_sequential_words(self, row_values: List[str], expected_words: List[str]) -> bool:
        """
        Check if a sequence of words appears in order across row values.
            
        Args:
            row_values: List of cell values from a row
            expected_words: List of words to find in sequence
                
        Returns:
            bool: True if all words are found in sequence, False otherwise
        """
        word_index = 0
        for cell_value in row_values:
            if word_index < len(expected_words):
                if expected_words[word_index] in cell_value:
                    word_index += 1
                    if word_index == len(expected_words):
                        return True
        return False

    def search_rows_for_sequential_word_matches(self, df: pd.DataFrame, expected_words: List[str]) -> pd.DataFrame:
        """
        Search through DataFrame rows for a sequence of words appearing in order.
        
        Args:
            df: DataFrame to search in
            expected_words: List of words to find in sequence
            
        Returns:
            pd.DataFrame: DataFrame containing the first matching row, or empty DataFrame if no match found
        """
        for _, row in df.iterrows():
            # Convert row to list of lowercase strings
            row_values = [str(val).lower() for val in row.values]
            # logger.info(f"  row_values: {row_values}")
            
            if self._check_row_for_sequential_words(row_values, expected_words):
                logger.info(f"  Found sequence match in row: {row_values}")
                return pd.DataFrame([row])
        
        return pd.DataFrame()

    def _update_match_status(self, dropbox_account_info: Dict[str, Any], match_type: str, match_name: str, expected_matches: List[str], account_name: str) -> None:
        """
        Update the match status in the account info dictionary.
        
        Args:
            dropbox_account_info: Dictionary containing account info and search results
            match_type: Type of match found ('expected', 'normalized', or 'swapped')
            match_name: The name that was matched
            expected_matches: List of expected matches to validate against
            account_name: Name of the account being searched
        """
        if match_type == 'expected':
            logger.info(f"Found expected Dropbox matches for {account_name}")
            dropbox_account_info['search_info']['status'] = 'found'
            dropbox_account_info['search_info']['match_info']['match_status'] = "Match found in expected matches"
        else:
            if len(expected_matches) > 0:
                logger.warning(f"Found {match_type} name match {match_name} but not in expected matches [{expected_matches}] for {account_name}")
                dropbox_account_info['search_info']['status'] = 'unexpected_matches'
                dropbox_account_info['search_info']['match_info']['match_status'] = f"Match found in {match_type} names but not in expected matches"
            else:
                dropbox_account_info['search_info']['status'] = 'found'
                dropbox_account_info['search_info']['match_info']['match_status'] = f"Match found in {match_type} names"

    def _store_matching_rows(self, dropbox_account_info: Dict[str, Any], matching_rows: pd.DataFrame, sheet_name: str, last_name: str) -> None:
        """
        Store matching rows in the account info dictionary and handle multiple matches.
        
        Args:
            dropbox_account_info: Dictionary containing account info and search results
            matching_rows: DataFrame containing matching rows
            sheet_name: Name of the sheet being searched
            last_name: Last name being searched for
        """
        # Store all matching rows for reference
        dropbox_account_info['search_info']['matches'] = [
            {f"Column {i}": self._clean_cell_value(str(val)) for i, val in enumerate(row) 
             if str(val).lower() != 'nan' and not pd.isna(val)}
            for _, row in matching_rows.iterrows()
        ]
        
        # If we have multiple matches but none in expected matches, log warning
        if len(matching_rows) > 1 and dropbox_account_info['search_info']['status'] == 'unexpected_matches':
            logger.warning(f"Found multiple {len(matching_rows)} matches in {sheet_name} for last name: {last_name}")
            dropbox_account_info['search_info']['status'] = 'multiple_matches'

    def _split_words(self, text: str) -> List[str]:
        """
        Split text into words while removing commas and parentheses.
        
        Args:
            text (str): The text to split
            
        Returns:
            List[str]: List of cleaned words
        """
        # Remove parentheses and their contents
        text = re.sub(r'\([^)]*\)', '', text)
        # Replace comma with space to handle cases with no space after comma
        text = text.replace(',', ' ')
        # Split on whitespace and filter out empty strings
        return [word.strip() for word in text.split() if word.strip()]

    def _is_family_pattern_match(self, row_values: List[str], last_name: str) -> bool:
        """
        Check if a row matches the pattern of 'last_name Family' or 'Family last_name'.
        
        Args:
            row_values: List of cell values from a row
            last_name: The last name to check for
            
        Returns:
            bool: True if the row matches the family pattern, False otherwise
        """
        # Convert all values to lowercase strings and clean them
        cleaned_values = [self._clean_cell_value(str(val)).lower() for val in row_values]
        
        # Look for the pattern in consecutive cells
        for i in range(len(cleaned_values) - 1):
            # Check for "last_name Family" pattern
            if cleaned_values[i] == last_name.lower() and cleaned_values[i + 1] == 'family':
                return True
            # Check for "Family last_name" pattern
            if cleaned_values[i] == 'family' and cleaned_values[i + 1] == last_name.lower():
                return True
        return False

    def _search_for_matches(self, df: pd.DataFrame, names_to_search: List[str], match_type: str, 
                          dropbox_account_info: Dict[str, Any], expected_matches: List[str], 
                          account_name: str, sheet_name: str) -> Tuple[pd.DataFrame, bool, str, pd.Series]:
        """
        Search for matches of a specific type in the DataFrame.
        
        Args:
            df: DataFrame to search in
            names_to_search: List of names to search for
            match_type: Type of match ('expected', 'normalized', or 'swapped')
            dropbox_account_info: Dictionary containing account info and search results
            expected_matches: List of expected matches to validate against
            account_name: Name of the account being searched
            sheet_name: Name of the sheet being searched
            
        Returns:
            Tuple containing:
            - DataFrame with matching rows (empty if no match)
            - Whether a match was found
            - Name of the sheet where match was found
            - The matching row (None if no match)
        """
        logger.info(f"\n=== Starting {match_type} name search in sheet: {sheet_name} ===")
        logger.info(f"Searching for {len(names_to_search)} {match_type} names")
        
        # Get the last name from the account info
        last_name = dropbox_account_info['name_parts'].get('last_name', '').lower()
        logger.info(f"Using last name: {last_name}")
        
        # Initialize match_found to False
        match_found = False
        
        # First check for family pattern matches
        logger.info("Checking for family pattern matches...")
        for _, row in df.iterrows():
            row_values = [str(val) for val in row.values]
            if self._is_family_pattern_match(row_values, last_name):
                logger.info(f"  ✓ Found family pattern match in row: {row_values}")
                match_found = True
                self._update_match_status(dropbox_account_info, 'family_pattern', f"{last_name} Family", expected_matches, account_name)
                logger.info(f"  ✓ Updated match status for family pattern match")
                return pd.DataFrame([row]), match_found, sheet_name, row
        
        logger.info("No family pattern matches found, proceeding with name search...")
        
        # If no family pattern match, continue with normal search
        for name in names_to_search:
            logger.info(f"\n  Checking {match_type} name: {name}")
            expected_words = self._split_words(name.lower())
            logger.info(f"  Split into words: {expected_words}")
            
            match_found = False
            matching_rows = self.search_rows_for_sequential_word_matches(df, expected_words)
            if not matching_rows.empty:
                logger.info(f"  ✓ Found {len(matching_rows)} matching rows for name: {name}")
                account_row = matching_rows.iloc[0]
                match_found = True
                self._update_match_status(dropbox_account_info, match_type, name, expected_matches, account_name)
                logger.info(f"  ✓ Updated match status for {match_type} match")
                return matching_rows, match_found, sheet_name, account_row
            else:
                logger.info(f"  ✗ No matches found for name: {name}")

        
        logger.info(f"=== No {match_type} matches found in sheet: {sheet_name} ===\n")
        return pd.DataFrame(), False, "", None

    def _search_for_matches_in_matching_rows(self, matching_rows: pd.DataFrame, names_to_search: List[str], match_type: str, 
                                           dropbox_account_info: Dict[str, Any], expected_matches: List[str], 
                                           account_name: str, sheet_name: str) -> Tuple[pd.DataFrame, bool, str, pd.Series]:
        """
        Search for matches of a specific type in pre-filtered matching rows.
        
        Args:
            matching_rows: DataFrame containing pre-filtered matching rows
            names_to_search: List of names to search for
            match_type: Type of match ('expected', 'normalized', or 'swapped')
            dropbox_account_info: Dictionary containing account info and search results
            expected_matches: List of expected matches to validate against
            account_name: Name of the account being searched
            sheet_name: Name of the sheet being searched
            
        Returns:
            Tuple containing:
            - DataFrame with matching rows (empty if no match)
            - Whether a match was found
            - Name of the sheet where match was found
            - The matching row (None if no match)
        """
        logger.info(f"\n=== Searching for {match_type} names in matching rows: {names_to_search} ===")
        
        # Get the last name from the account info
        last_name = dropbox_account_info['name_parts'].get('last_name', '').lower()
        
        # First check for family pattern matches
        for _, row in matching_rows.iterrows():
            row_values = [str(val) for val in row.values]
            if self._is_family_pattern_match(row_values, last_name):
                logger.info(f"  Found family pattern match in row: {row_values}")
                match_found = True
                self._update_match_status(dropbox_account_info, 'family_pattern', f"{last_name} Family", expected_matches, account_name)
                return pd.DataFrame([row]), match_found, sheet_name, row
        
        # If no family pattern match, continue with normal search
        for name in names_to_search:
            logger.info(f"  {match_type}_name: {name}")
            expected_words = self._split_words(name.lower())
            logger.info(f"*expected_words {expected_words}")
            
            # Search through each matching row
            for _, row in matching_rows.iterrows():
                # Convert row to list of lowercase strings
                row_values = [str(val).lower() for val in row.values]
                
                # Check if this row contains the expected words in sequence
                if self._check_row_for_sequential_words(row_values, expected_words):
                    logger.info(f"  ***Found matching row with {match_type} name: {name}")
                    account_row = row
                    match_found = True
                    self._update_match_status(dropbox_account_info, match_type, name, expected_matches, account_name)
                    return pd.DataFrame([row]), match_found, sheet_name, account_row
        
        return pd.DataFrame(), False, "", None

    def dropbox_search_account(self, account_name: str, dropbox_account_name_parts: Dict[str, Any], excel_file: pd.ExcelFile = None) -> Dict[str, Any]:
        """Get account information from the holiday Excel file.
        
        This method:
        1. Checks for special cases in accounts/special_cases.json
        2. Locates the holiday account info file
        3. Downloads and reads the Excel file
        4. Searches for the account in all sheets
        5. If expected_dropbox_matches is provided:
           - Validates found matches against expected matches
           - Updates status based on whether matches are expected
        6. Extracts available information
        7. Extracts driver's license information if available
        
        Args:
            account_name (str): The name of the account to search for (used for logging)
            dropbox_account_name_parts (Dict[str, Any]): Dictionary containing:
                - folder_name (str): Original folder name
                - last_name (str): Last name to search for
                - full_name (str): Full name to search for
                - normalized_names (List[str]): List of normalized name variations
                - swapped_names (List[str]): List of name variations with swapped first/last
                - expected_dropbox_matches (List[str]): List of expected matches for validation
            excel_file (pd.ExcelFile, optional): The Excel file object to search in. If not provided, will return empty results.
                
        Returns:
            Dict[str, Any]: Dictionary containing:
                - name_parts (Dict[str, Any]): Original name parts and search info
                - search_info (Dict[str, Any]): Information about the search process including:
                    - status: 'found', 'multiple_matches', 'unexpected_matches', or 'not_found'
                    - matches: List of found matches
                    - match_info: Details about match status and counts
                - account_data (Dict[str, Any]): Extracted account information
                - drivers_license (Dict[str, Any]): Extracted driver's license information
        """
        logger.info(f"\n=== Starting Dropbox account info search for: {account_name} ===")
        folder_name = account_name
        
        # Initialize result structure
        dropbox_account_info = {
            'name_parts': dropbox_account_name_parts,
            'search_info': {
                'status': 'not_found',
                'matches': [],
                'search_attempts': [],
                'timing': {},
                'match_info': {
                    'match_status': "No match found",
                    'total_matches': 0,
                    'total_partial_matches': 0,
                    'total_no_matches': 1
                }
            },
            'account_data': {},
            'drivers_license': {},
            'drivers_license_info': {
                'status': 'not_found',
                'reason': None,
                'file_path': None,
                'extraction_errors': []
            }
        }

        try:
            # First, try to get driver's license information
            logger.info(f"\n=== Getting driver's license information for {account_name} ===")
            dl_file = self.get_drivers_license_file(account_name)
            if dl_file:
                logger.info(f"Found driver's license file: {dl_file.name}")
                dropbox_account_info['drivers_license_info']['status'] = 'found'
                dropbox_account_info['drivers_license_info']['file_path'] = dl_file.path_display
                try:
                    # Create a temporary file with the correct extension
                    file_ext = os.path.splitext(dl_file.name)[1].lower()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                        temp_path = temp_file.name
                        # Download the driver's license file
                        self.dbx.files_download_to_file(temp_path, dl_file.path_display)
                        logger.info(f"Downloaded driver's license to: {temp_path}")
                        # Always use _extract_dl_info for both PDF and image files
                        dl_info = self._extract_dl_info(temp_path)
                        if dl_info:
                            dropbox_account_info['drivers_license'] = dl_info
                            logger.info(f"Successfully extracted driver's license information: {dl_info}")
                        else:
                            logger.warning("No information could be extracted from driver's license")
                            dropbox_account_info['drivers_license_info']['status'] = 'extraction_failed'
                            dropbox_account_info['drivers_license_info']['reason'] = 'No information could be extracted from the file'
                        # Clean up the temporary file
                        os.unlink(temp_path)
                except Exception as e:
                    logger.error(f"Error processing driver's license: {str(e)}")
                    dropbox_account_info['drivers_license_info']['status'] = 'processing_error'
                    dropbox_account_info['drivers_license_info']['reason'] = f'Error processing file: {str(e)}'
                    dropbox_account_info['drivers_license_info']['extraction_errors'].append(str(e))
            else:
                logger.info("No driver's license file found")
                dropbox_account_info['drivers_license_info']['status'] = 'not_found'
                dropbox_account_info['drivers_license_info']['reason'] = 'No driver\'s license file found in the account folder'

            # Log search parameters
            logger.info("Search parameters:")
            logger.info(f"  - Last name: {dropbox_account_name_parts['last_name']}")
            logger.info(f"  - Full name: {dropbox_account_name_parts['full_name']}")
            logger.info(f"  - Normalized names: {dropbox_account_name_parts['normalized_names']}")
            logger.info(f"  - Swapped names: {dropbox_account_name_parts['swapped_names']}")
            logger.info(f"  - Expected Dropbox matches: {dropbox_account_name_parts['expected_dropbox_matches']}")
            logger.info("")
            
            if not excel_file:
                logger.error("No Excel file provided")
                return dropbox_account_info
            
            sheets = excel_file.sheet_names
            
            try:
                # Initialize variables for tracking matches
                account_row = None
                match_found = False
                match_sheet = None
                sheet_search_info = []  # Store search info for each sheet

                # Use the last_name directly from dropbox_account_name_parts
                last_name = dropbox_account_name_parts.get('last_name', '').lower()
                expected_matches = dropbox_account_name_parts.get('expected_dropbox_matches', [])
                
                logger.info(f"Using last name from dropbox_account_name_parts: {last_name}")
                
                # Search through each sheet
                for sheet_name in sheets:
                    logger.info(f"\nSearching in sheet: {sheet_name}")
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    logger.info(f"Sheet dimensions: {df.shape[0]} rows x {df.shape[1]} columns")

                    # Search for the last name in any column
                    logger.info(f"Searching for last name: {last_name} in any column of sheet: {sheet_name}")
                    # Convert all columns to string, clean values, and handle NaN values
                    df_str = df.astype(str).apply(lambda x: x.apply(self._clean_cell_value).str.lower())
                    # Create a mask for rows containing the last name
                    mask = df_str.apply(lambda row: any(last_name in str(cell) for cell in row), axis=1)
                    # Get all matching rows
                    original_matching_rows = df[mask]
                    matching_rows = original_matching_rows
                    logger.info(f"Found last name in rows... {last_name} in {len(matching_rows)} rows")
                    logger.info(f"Found {len(matching_rows)} matching rows for last name {last_name} in sheet: {sheet_name}")
                    if not matching_rows.empty:
                        logger.info("Matching rows found:")
                        for _, row in matching_rows.iterrows():
                            row_values = [str(val) for val in row.values if not pd.isna(val)]
                            logger.info(f"  - {row_values}")
                    
                    if not matching_rows.empty:
                        # If we have exactly one matching row for the last name, consider it a valid match
                        if len(matching_rows) == 1 and not match_found:
                            logger.info(f"Found exactly one matching row for last name {last_name} in sheet: {sheet_name}")
                            account_row = matching_rows.iloc[0]
                            match_found = True
                            match_sheet = sheet_name
                            self._update_match_status(dropbox_account_info, 'exact_last_name', last_name, expected_matches, account_name)
                            logger.info(f"  ✓ Updated match status for exact last name match")
                            break

                        # Search for expected matches
                        matching_rows, match_found, match_sheet, account_row = self._search_for_matches_in_matching_rows(
                            matching_rows, expected_matches, 'expected',
                            dropbox_account_info, expected_matches, account_name, sheet_name
                        )
                        if match_found:
                            break
                        # Search for normalized names
                        matching_rows, match_found, match_sheet, account_row = self._search_for_matches_in_matching_rows(
                            matching_rows, dropbox_account_name_parts.get('normalized_names', []), 'normalized',
                            dropbox_account_info, expected_matches, account_name, sheet_name
                        )
                        if match_found:
                            break

                        # Search for swapped names
                        matching_rows, match_found, match_sheet, account_row = self._search_for_matches_in_matching_rows(
                            matching_rows, dropbox_account_name_parts.get('swapped_names', []), 'swapped',
                            dropbox_account_info, expected_matches, account_name, sheet_name
                        )
                        if match_found:
                            break

                        # If we found rows with last name but no match in expected_dropbox_matches, log warning
                        if expected_matches and not match_found:
                            logger.warning(f"\n=== WARNING: Found rows with last name '{last_name}' but expected_dropbox_matches not working ===")
                            logger.warning(f"Account: {account_name}")
                            logger.warning(f"Sheet: {sheet_name}")
                            logger.warning(f"*Expected matches: {expected_matches}")
                            logger.warning("Matching rows found:")
                            row_values_list = []
                            for _, row in original_matching_rows.iterrows():
                                row_values = [str(val) for val in row.values if not pd.isna(val)]
                                logger.warning(f"  - {row_values}")
                                row_values_list.append(row_values)
                            if len(row_values_list) > 0:
                                logger.warning(f"\n=== WARNING: Found rows with last name '{last_name}' expected_dropbox_matches: {expected_matches} row_values_list: {row_values_list} ===")

                            logger.warning("=== END WARNING ===\n")

                    if matching_rows.empty:
                        logger.info(f"No matching rows found for last name: {last_name} in sheet: {sheet_name}, doing more sophisticated search...")

                        # Search for expected matches
                        logger.info(f"Searching for expected matches: {expected_matches}")
                        matching_rows, match_found, match_sheet, account_row = self._search_for_matches(
                            df, expected_matches, 'expected',
                            dropbox_account_info, expected_matches, account_name, sheet_name
                        )
                        if match_found:
                            break
                            
                        logger.info(f"Searching for reversed expected matches: {expected_matches}")
                        reversed_expected_matches = []
                        for name in expected_matches:
                            logger.info(f"name: {name}")
                            reversed_name_list = self._split_words(name)[::-1]
                            reversed_name = ' '.join(reversed_name_list)
                            logger.info(f"reversed_name: {reversed_name}")
                            reversed_expected_matches.append(reversed_name)
                        logger.info(f"reversed_expected_matches: {reversed_expected_matches}")

                        matching_rows, match_found, match_sheet, account_row = self._search_for_matches(
                            df, reversed_expected_matches, 'expected',
                            dropbox_account_info, expected_matches, account_name, sheet_name
                        )
                        if match_found:
                            break

                        # Search for swapped names
                        logger.info(f"Searching for swapped names: {dropbox_account_name_parts.get('swapped_names', [])}")
                        matching_rows, match_found, match_sheet, account_row = self._search_for_matches(
                            df, dropbox_account_name_parts.get('swapped_names', []), 'swapped',
                            dropbox_account_info, expected_matches, account_name, sheet_name
                        )
                        if match_found:
                            break

                        # Search for normalized names
                        logger.info(f"Searching for normalized names: {dropbox_account_name_parts.get('normalized_names', [])}")
                        matching_rows, match_found, match_sheet, account_row = self._search_for_matches(
                            df, dropbox_account_name_parts.get('normalized_names', []), 'normalized',
                            dropbox_account_info, expected_matches, account_name, sheet_name
                        )
                        if match_found:
                            break

                        
                    # Store matching rows and handle multiple matches
                    if not matching_rows.empty:
                        self._store_matching_rows(dropbox_account_info, matching_rows, sheet_name, last_name)

                # Extract data if match found
                if match_found and account_row is not None:
                    logger.info(f"\nExtracting data from {match_sheet} sheet")
                    if match_sheet == "Client full info":
                        # Extract data from specific columns in "Client full info" sheet
                        dropbox_account_info['account_data'] = {
                            'name': f"{account_row.iloc[0]} {account_row.iloc[1]}",  # First name + Last name
                            'first_name': str(account_row.iloc[0]),
                            'last_name': str(account_row.iloc[1]),
                            'address': str(account_row.iloc[3]),  # Column D
                            'city': str(account_row.iloc[6]),     # Column G
                            'state': str(account_row.iloc[7]),    # Column H
                            'zip': str(account_row.iloc[8])       # Column I
                        }
                        if dropbox_account_info['drivers_license']:
                            dropbox_account_info['account_data']['drivers_license'] = dropbox_account_info['drivers_license']
                        # Update match status
                        dropbox_account_info['search_info']['status'] = 'found'
                        dropbox_account_info['search_info']['match_info']['match_status'] = "Match found"
                        dropbox_account_info['search_info']['match_info']['total_matches'] = 1
                        dropbox_account_info['search_info']['match_info']['total_no_matches'] = 0
                    elif match_sheet == "Client Mailing List":
                        # Extract data from Client Mailing List sheet using row values directly
                        row_values = [str(val) for val in account_row.values if not pd.isna(val)]
                        dropbox_account_info['account_data'] = {
                            'name': f"{row_values[1]} {row_values[0]}",  # First name + Last name
                            'first_name': str(row_values[1]),
                            'last_name': str(row_values[0]),
                            'address': str(row_values[2]),
                            'city': str(row_values[3]),
                            'state': str(row_values[4]),
                            'zip': str(row_values[5]),
                            'email': str(row_values[6]),
                            'phone': str(row_values[7])
                        }
                        if dropbox_account_info['drivers_license']:
                            dropbox_account_info['account_data']['drivers_license'] = dropbox_account_info['drivers_license']
                        # Update match status
                        dropbox_account_info['search_info']['status'] = 'found'
                        dropbox_account_info['search_info']['match_info']['match_status'] = "Match found"
                        dropbox_account_info['search_info']['match_info']['total_matches'] = 1
                        dropbox_account_info['search_info']['match_info']['total_no_matches'] = 0
                    else:
                        # Extract data from standard sheet format
                        dropbox_account_info['account_data'] = {
                            'name': str(account_row.get('Name', '')),
                            'first_name': str(account_row.get('First Name', '')),
                            'last_name': str(account_row.get('Last Name', '')),
                            'address': str(account_row.get('Address', '')),
                            'city': str(account_row.get('City', '')),
                            'state': str(account_row.get('State', '')),
                            'zip': str(account_row.get('Zip', '')),
                            'email': str(account_row.get('Email', '')),
                            'phone': str(account_row.get('Phone', ''))
                        }
                        if dropbox_account_info['drivers_license']:
                            dropbox_account_info['account_data']['drivers_license'] = dropbox_account_info['drivers_license']
                        # Update match status
                        dropbox_account_info['search_info']['status'] = 'found'
                        dropbox_account_info['search_info']['match_info']['match_status'] = "Match found"
                        dropbox_account_info['search_info']['match_info']['total_matches'] = 1
                        dropbox_account_info['search_info']['match_info']['total_no_matches'] = 0

                # If no match found, log detailed explanation
                if not dropbox_account_info['account_data']:
                    # Log to analyzer.log
                    logger.info("\n*=== DROPBOX SEARCH - NO MATCH EXPLANATION ===")
                    logger.info(f"Account: {account_name}")
                    logger.info(f"Last name searched: {dropbox_account_name_parts.get('last_name', '')}")
                    logger.info(f"Normalized names: {dropbox_account_name_parts.get('normalized_names', [])}")
                    logger.info(f"**Expected matches: {dropbox_account_name_parts.get('expected_dropbox_matches', [])}")
                    logger.info(f"Found matches: {dropbox_account_info['search_info']['matches']}")
                    logger.info("\nSearch process:")
                    for sheet_name in sheets:
                        df = pd.read_excel(excel_file, sheet_name=sheet_name)
                        logger.info(f"\nSheet: {sheet_name}")
                        logger.info(f"  - Dimensions: {df.shape[0]} rows x {df.shape[1]} columns")
                        # logger.info(f"  - Columns: {list(df.columns)}")
                        # logger.info(f"  - First row values: {[str(val) for val in df.iloc[0].values]}")
                        logger.info(f"  - Search method: Searched for last name '{last_name}' in all columns")
                        # Search for the last name in this sheet
                        df_str = df.astype(str).apply(lambda x: x.apply(self._clean_cell_value).str.lower())
                        mask = df_str.apply(lambda row: any(last_name in str(cell) for cell in row), axis=1)
                        matching_rows = df[mask]
                        if not matching_rows.empty:
                            logger.info(f"  - Found {len(matching_rows)} matching rows:")
                            for _, row in matching_rows.iterrows():
                                row_values = [str(val) for val in row.values if not pd.isna(val)]
                                logger.info(f"    * {row_values}")
                        else:
                            logger.info(f"  - Result: No matches found")
                    logger.info("=== END NO MATCH EXPLANATION ===\n")

                    # Log to report.log (without the detailed search process)
                    report_logger = logging.getLogger('report')
                    report_logger.info("\n=== DROPBOX SEARCH - NO MATCH EXPLANATION ===")
                    report_logger.info(f"Account: {account_name}")
                    report_logger.info(f"Last name searched: {dropbox_account_name_parts.get('last_name', '')}")
                    report_logger.info(f"Normalized names: {dropbox_account_name_parts.get('normalized_names', [])}")
                    report_logger.info(f"***Expected matches: {dropbox_account_name_parts.get('expected_dropbox_matches', [])}")
                    report_logger.info(f"Found matches: {dropbox_account_info['search_info']['matches']}")
                    report_logger.info("=== END NO MATCH EXPLANATION ===\n")

            finally:
                # No need to clean up temporary file since we're using the excel_file object directly
                pass
            
            # Merge driver's license info into account_data if present
            if dropbox_account_info['drivers_license']:
                dropbox_account_info['account_data']['drivers_license'] = dropbox_account_info['drivers_license']
                logger.info(f"DEBUG: driver's_license info: {dropbox_account_info['drivers_license']}")
            else:
                logger.info("DEBUG: No driver's_license info extracted.")
            
            # Log driver's license information to report.log
            report_logger = logging.getLogger('report')
            if dropbox_account_info['drivers_license_info']['status'] == 'found':
                if dropbox_account_info['drivers_license']:
                    report_logger.info("\n📄 **Driver's License Information**")
                    report_logger.info(f"   + Status: Found and extracted")
                    report_logger.info(f"   + File: {dropbox_account_info['drivers_license_info']['file_path']}")
                    for key, value in dropbox_account_info['drivers_license'].items():
                        report_logger.info(f"   + {key}: {value}")
                else:
                    report_logger.info("\n📄 **Driver's License Information**")
                    report_logger.info(f"   + Status: Found but no information extracted")
                    report_logger.info(f"   + File: {dropbox_account_info['drivers_license_info']['file_path']}")
            else:
                report_logger.info("\n📄 **Driver's License Information**")
                report_logger.info(f"   + Status: {dropbox_account_info['drivers_license_info']['status']}")
                if dropbox_account_info['drivers_license_info']['reason']:
                    report_logger.info(f"   + Reason: {dropbox_account_info['drivers_license_info']['reason']}")
                if dropbox_account_info['drivers_license_info']['extraction_errors']:
                    report_logger.info("   + Errors:")
                    for error in dropbox_account_info['drivers_license_info']['extraction_errors']:
                        report_logger.info(f"     - {error}")
            
            return dropbox_account_info
            
        except Exception as e:
            logger.error(f"Error getting account info for {account_name}: {str(e)}")
            logger.error("Stack trace:", exc_info=True)
            return dropbox_account_info

    def parse_account_name(self, folder_name: str) -> Tuple[str, str, Optional[str]]:
        """Parse account name into first, last, and middle names."""
        parts = folder_name.split()
        if len(parts) == 2:
            return parts[0], parts[1], None
        elif len(parts) > 2:
            return parts[0], parts[-1], ' '.join(parts[1:-1])
        return folder_name, '', None

    def deprecated_list_files(self, account_folder: str) -> list:
        """
        List files in the specified Dropbox account folder.
        
        Args:
            account_folder (str): The account folder path to list files from
            
        Returns:
            list: List of files in the specified path
        """
        logging.info(f"Listing files in account folder: {account_folder}")
        dropbox_path = self.construct_dropbox_path(account_folder, self.root_folder)
        if not dropbox_path:
            return []
            
        logging.info(f"Listing files in Dropbox folder: {dropbox_path}")
        try:
            logger.info('list_files')
            # Clean the account folder name to ensure it's properly formatted
            clean_account_folder = account_folder.strip()
            
            # Construct the full path by joining the root folder with the account folder
            full_path = os.path.join(self.root_folder, clean_account_folder)
            
            # Clean the full path to ensure it's in the correct format for Dropbox API
            dropbox_path = clean_dropbox_folder_name(full_path)
            
            if not dropbox_path:
                logging.error(f"Invalid path constructed: {full_path}")
                return []
                
            logging.info(f"Listing files in path: {dropbox_path}")
            logging.info(f"Full Dropbox folder being used: {dropbox_path}")
            
            # Initialize list to store all files
            all_files = []
            page_num = 1
            
            # Get first page of results
            try:
                result = self._make_request(self.dbx.files_list_folder, f"/{dropbox_path}")
                files = [entry for entry in result.entries if isinstance(entry, dropbox.files.FileMetadata)]
                all_files.extend(files)
                logging.info(f"Page {page_num}: Found {len(files)} files")
                
                # Continue getting more pages if there are more results
                while result.has_more:
                    page_num += 1
                    result = self._make_request(self.dbx.files_list_folder_continue, result.cursor)
                    files = [entry for entry in result.entries if isinstance(entry, dropbox.files.FileMetadata)]
                    all_files.extend(files)
                    logging.info(f"Page {page_num}: Found {len(files)} files")
                
                logging.info(f"Total files found across all pages: {len(all_files)}")
                
                # Try alternative path if we didn't find enough files
                if len(all_files) < 23:  # We expect 23 files
                    alt_path = f"/A Work Documents/A WORK Documents/Principal Protection/{clean_account_folder}"
                    logging.info(f"Trying alternative path: {alt_path}")
                    
                    result = self._make_request(self.dbx.files_list_folder, alt_path)
                    alt_files = [entry for entry in result.entries if isinstance(entry, dropbox.files.FileMetadata)]
                    all_files.extend(alt_files)
                    logging.info(f"Alternative path: Found {len(alt_files)} files")
                    
                    while result.has_more:
                        result = self._make_request(self.dbx.files_list_folder_continue, result.cursor)
                        alt_files = [entry for entry in result.entries if isinstance(entry, dropbox.files.FileMetadata)]
                        all_files.extend(alt_files)
                        logging.info(f"Alternative path additional page: Found {len(alt_files)} files")
                    
                    # Remove duplicates
                    all_files = list({f.path_display: f for f in all_files}.values())
                    logging.info(f"Total unique files after trying alternative path: {len(all_files)}")
            
            except ApiError as e:
                if e.error.is_path() and e.error.get_path().is_not_found():
                    logging.error(f"Path not found: /{dropbox_path}")
                    logging.error("Trying alternative path...")
                    alt_path = f"/A Work Documents/A WORK Documents/Principal Protection/{clean_account_folder}"
                    result = self._make_request(self.dbx.files_list_folder, alt_path)
                    files = [entry for entry in result.entries if isinstance(entry, dropbox.files.FileMetadata)]
                    all_files.extend(files)
                    logging.info(f"Alternative path: Found {len(files)} files")
                else:
                    raise
            
            # Show files in debug mode
            skip_patterns = [r'.*\.DS_Store$', r'.*\.tmp$']  # Add any patterns for files to skip
            return self._debug_show_files(account_folder, all_files, skip_patterns)
            
        except Exception as e:
            logging.error(f"Error getting account files: {e}")
            sys.exit(1)
            return []

    def get_account_info_file(self, account_folder: str) -> Optional[FileMetadata]:
        """Get the account info file (*App.pdf) for an account."""
        files = self.list_folder_contents(account_folder)
        pattern = ACCOUNT_INFO_PATTERN.replace('*', '.*')
        for file in files:
            if re.match(pattern, file.name):
                return file
        return None

    def get_drivers_license_file(self, account_folder: str) -> Optional[FileMetadata]:
        """Get the driver's license file (*DL.jpeg or *DL.pdf) for an account."""
        try:
            dropbox_path = construct_dropbox_path(account_folder, self.root_folder)
            if not dropbox_path:
                logger.error(f"Invalid path constructed for account folder: {account_folder}")
                return None
                
            files = list_dropbox_folder_contents(self.dbx, dropbox_path)
            logger.info(f"Files found in {dropbox_path}:")
            for file in files:
                if isinstance(file, FileMetadata):
                    logger.info(f"  - {file.name}")
            
            # Pattern to match both .jpeg and .pdf extensions, and files containing variations of "driver(s) license"
            patterns = [
                r'.*DL\.(?:jpeg|pdf|jpg|png)$',  # Basic DL pattern with common extensions
                r'.*DL\s*\.(?:jpeg|pdf|jpg|png)$',  # DL with optional space before extension
                r'.*DL\s*[-_]?\d*\.(?:jpeg|pdf|jpg|png)$',  # DL with optional number or separator
                r'.*driver[s]?\s*licen[cs]e?.*\.(?:jpeg|pdf|jpg|png)$',  # Full text variations
                r'.*divers?\s*licen[cs]e?.*\.(?:jpeg|pdf|jpg|png)$',  # French variations
                r'.*DL.*\.(?:jpeg|pdf|jpg|png)$',  # Any file with DL in the name
                r'.*ID\s*card.*\.(?:jpeg|pdf|jpg|png)$',  # ID card variations
                r'.*identification.*\.(?:jpeg|pdf|jpg|png)$'  # Identification variations
            ]
            
            for file in files:
                if isinstance(file, FileMetadata):
                    logger.info(f"Checking file: {file.name}")
                    for pattern in patterns:
                        if re.match(pattern, file.name, re.IGNORECASE):
                            logger.info(f"Found driver's license file: {file.name} matching pattern: {pattern}")
                            return file
                        else:
                            logger.info(f"File {file.name} did not match pattern: {pattern}")
            logger.info(f"No driver's license file found in {dropbox_path}")
            return None
        except Exception as e:
            logger.error(f"Error getting driver's license file: {str(e)}")
            return None

    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Try to extract text directly from PDF first, fall back to OCR if needed.
        """
        try:
            logging.info(f"Attempting to extract text from PDF: {pdf_path}")
            # First try direct text extraction
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                
                # If we got meaningful text, return it
                if text.strip():
                    logging.info("Successfully extracted text directly from PDF")
                    return text

            logging.info("Direct text extraction failed, attempting OCR")
            # If direct extraction didn't work, try OCR
            images = pdf2image.convert_from_path(pdf_path)
            text = ""
            for image in images:
                text += pytesseract.image_to_string(image)
            logging.info("Completed OCR text extraction")
            return text

        except Exception as e:
            logging.error(f"Error extracting text from PDF: {e}")
            return ""

    def _extract_dl_info(self, image_path: str) -> Dict[str, str]:
        try:
            if not os.path.exists(image_path):
                logger.error(f"Driver's license file not found: {image_path}")
                return {}
            _, ext = os.path.splitext(image_path)
            ext = ext.lower()
            text = ''
            debug_image_saved = False

            def binarize(image, threshold=160):
                # Convert to grayscale if not already
                if image.mode != 'L':
                    image = image.convert('L')
                # Apply adaptive thresholding
                return image.point(lambda p: 255 if p > threshold else 0)

            def preprocess_image(image, save_debug=True, crop_band=None, use_opencv=True):
                # Convert to grayscale if not already
                if image.mode != 'L':
                    image = image.convert('L')
                
                # Optionally crop to a horizontal band
                if crop_band is not None:
                    width, height = image.size
                    band_height = height // 3
                    top = band_height * crop_band
                    bottom = top + band_height
                    image = image.crop((0, top, width, bottom))
                    logger.info(f"Cropped image to band {crop_band}: (0, {top}, {width}, {bottom})")
                
                # Convert to OpenCV image for advanced processing
                if use_opencv:
                    img_np = np.array(image)
                    # Denoise
                    img_np = cv2.fastNlMeansDenoising(img_np, None, 30, 7, 21)
                    # Adaptive thresholding
                    img_np = cv2.adaptiveThreshold(img_np, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11)
                    # Deskew (optional, only if needed)
                    def deskew(img):
                        coords = np.column_stack(np.where(img > 0))
                        angle = 0.0
                        if coords.shape[0] > 0:
                            rect = cv2.minAreaRect(coords)
                            angle = rect[-1]
                            if angle < -45:
                                angle = -(90 + angle)
                            else:
                                angle = -angle
                        (h, w) = img.shape[:2]
                        center = (w // 2, h // 2)
                        M = cv2.getRotationMatrix2D(center, angle, 1.0)
                        img = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                        return img
                    img_np = deskew(img_np)
                    image = Image.fromarray(img_np)
                else:
                    # Enhance contrast
                    image = ImageEnhance.Contrast(image).enhance(2.0)
                    # Enhance sharpness
                    image = ImageEnhance.Sharpness(image).enhance(2.0)
                    # Apply binarization
                    image = binarize(image)
                
                # Save debug image
                if save_debug:
                    debug_path = os.path.join(tempfile.gettempdir(), f'debug_dl_preprocessed_band{crop_band if crop_band is not None else "full"}.png')
                    image.save(debug_path, 'PNG')
                    logger.info(f"Saved preprocessed debug image: {debug_path}")
                
                return image

            def try_psm_modes(image, image_path=None):
                import io
                logger.info("Entered try_psm_modes")
                best_text = ''
                best_mode = ''
                psm_modes = [6, 3, 11, 7, 12]
                
                # Enhanced OCR configurations (removed config with single quote)
                configs = [
                    lambda psm: f'--psm {psm} --oem 3',
                    lambda psm: f'--psm {psm} --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- ',
                    lambda psm: f'--psm {psm} --oem 3 -c tessedit_char_whitelist=0123456789- '
                ]

                logger.info(f"Running OCR on image: {image_path if image_path else '<in-memory>'}, mode={image.mode}, size={image.size}")
                
                # Save image for debugging
                debug_path = os.path.join(tempfile.gettempdir(), 'debug_dl_ocr_input.png')
                image.save(debug_path, 'PNG')
                logger.info(f"Saved OCR input image: {debug_path}")

                all_ocr_outputs = []
                for psm in psm_modes:
                    for config_fn in configs:
                        config = config_fn(psm)
                        try:
                            logger.info(f"Calling pytesseract with config: {config}")
                            ocr_text = pytesseract.image_to_string(image, config=config)
                            logger.info(f"OCR output for PSM {psm} ({config}): {repr(ocr_text)}")
                            all_ocr_outputs.append((config, ocr_text))
                            # Validate license number format
                            if re.search(r'[A-Z]\d{3}-\d{3}-\d{2}-\d{3}-\d', ocr_text):
                                logger.info(f"Found valid license number format in PSM {psm}")
                                # Save raw OCR output for manual inspection
                                raw_ocr_path = os.path.join(tempfile.gettempdir(), 'debug_dl_raw_ocr.txt')
                                with open(raw_ocr_path, 'w') as f:
                                    f.write(ocr_text)
                                logger.info(f"Saved raw OCR output: {raw_ocr_path}")
                                return ocr_text
                            if len(ocr_text.strip()) > len(best_text.strip()):
                                best_text = ocr_text
                                best_mode = f'psm {psm} {config}'
                        except Exception as ocr_exc:
                            logger.error(f"Tesseract error for config {config}: {ocr_exc}")
                # Save the best raw OCR output for manual inspection
                raw_ocr_path = os.path.join(tempfile.gettempdir(), 'debug_dl_raw_ocr.txt')
                with open(raw_ocr_path, 'w') as f:
                    for config, ocr_text in all_ocr_outputs:
                        f.write(f'Config: {config}\n{ocr_text}\n---\n')
                logger.info(f"Saved all raw OCR outputs: {raw_ocr_path}")
                logger.info(f"Best OCR mode: {best_mode}")
                logger.info("Exiting try_psm_modes")
                return best_text

            def crop_license_number_region(image):
                width, height = image.size
                # These values are tuned for typical Florida DL images
                left = int(width * 0.45)
                top = int(height * 0.10)
                right = int(width * 0.95)
                bottom = int(height * 0.25)
                cropped = image.crop((left, top, right, bottom))
                logger.info(f"Cropped license number region: ({left}, {top}, {right}, {bottom})")
                # Save debug crop
                debug_path = os.path.join(tempfile.gettempdir(), 'debug_dl_license_number_crop.png')
                cropped.save(debug_path, 'PNG')
                logger.info(f"Saved cropped license number region: {debug_path}")
                return cropped

            def crop_dob_region(image):
                width, height = image.size
                # These values are tuned for typical Florida DL images (DOB is mid-right)
                left = int(width * 0.45)
                top = int(height * 0.32)
                right = int(width * 0.80)
                bottom = int(height * 0.40)
                cropped = image.crop((left, top, right, bottom))
                logger.info(f"Cropped DOB region: ({left}, {top}, {right}, {bottom})")
                # Save debug crop
                debug_path = os.path.join(tempfile.gettempdir(), 'debug_dl_dob_crop.png')
                cropped.save(debug_path, 'PNG')
                logger.info(f"Saved cropped DOB region: {debug_path}")
                return cropped

            if ext == '.pdf':
                try:
                    text = self._extract_text_from_pdf(image_path)
                    if not text.strip():
                        logger.info("Direct text extraction failed, attempting OCR")
                        images = pdf2image.convert_from_path(
                            image_path,
                            dpi=600,  # Higher DPI for better quality
                            grayscale=True,
                            thread_count=4
                        )
                        logger.info(f"Extracted {len(images)} image(s) from PDF for OCR.")
                        if not images:
                            logger.error("Failed to convert PDF to images")
                            return {}
                        
                        all_text = []
                        found_license = False
                        for i, image in enumerate(images):
                            logger.debug(f"Processing page {i+1} of {len(images)}; mode={image.mode}, size={image.size}")
                            # Try all three horizontal bands
                            for band in [0, 1, 2]:
                                band_image = preprocess_image(image, save_debug=(i == 0 and band == 1), crop_band=band)
                                ocr_text = try_psm_modes(band_image, image_path=image_path)
                                if ocr_text.strip():
                                    all_text.append(ocr_text)
                                    logger.debug(f"Extracted text from page {i+1}, band {band}: {ocr_text}")
                                    # If a valid license number is found, use this band
                                    if re.search(r'[A-Z]\d{3}-\d{3}-\d{2}-\d{3}-\d', ocr_text):
                                        text = ocr_text
                                        found_license = True
                                        break
                            if found_license:
                                break
                        if not found_license:
                            # Fallback: try the full image
                            full_image = preprocess_image(image, save_debug=(i == 0), crop_band=None)
                            ocr_text = try_psm_modes(full_image, image_path=image_path)
                            if ocr_text.strip():
                                all_text.append(ocr_text)
                            text = ' '.join(all_text)
                except Exception as e:
                    logger.error(f"Error processing PDF: {str(e)}")
                    return {}
            else:
                try:
                    image = Image.open(image_path)
                    logger.debug(f"Image mode: {image.mode}, size: {image.size}")
                    found_license = False
                    all_text = []
                    # --- Try region crop for license number ---
                    license_crop = crop_license_number_region(image)
                    ocr_text = try_psm_modes(license_crop, image_path=image_path)
                    if ocr_text.strip():
                        all_text.append(ocr_text)
                        if re.search(r'[A-Z]\d{3}-\d{3}-\d{2}-\d{3}-\d', ocr_text):
                            text = ocr_text
                            found_license = True
                    # --- Try region crop for DOB ---
                    dob_crop = crop_dob_region(image)
                    dob_ocr_text = try_psm_modes(dob_crop, image_path=image_path)
                    if dob_ocr_text.strip():
                        all_text.append(dob_ocr_text)
                    # If not found, try the usual band approach
                    if not found_license:
                        for band in [0, 1, 2]:
                            band_image = preprocess_image(image, save_debug=(band == 1), crop_band=band)
                            ocr_text = try_psm_modes(band_image, image_path=image_path)
                            if ocr_text.strip():
                                all_text.append(ocr_text)
                                if re.search(r'[A-Z]\d{3}-\d{3}-\d{2}-\d{3}-\d', ocr_text):
                                    text = ocr_text
                                    found_license = True
                                    break
                    if not found_license:
                        # Fallback: try the full image
                        full_image = preprocess_image(image, save_debug=True, crop_band=None)
                        ocr_text = try_psm_modes(full_image, image_path=image_path)
                        if ocr_text.strip():
                            all_text.append(ocr_text)
                        text = ' '.join(all_text)
                except Exception as e:
                    logger.error(f"Error processing image: {str(e)}")
                    return {}

            # Clean and normalize text
            text = text.replace('\n', ' ').replace('\r', ' ')
            text = ' '.join(text.split())
            
            if not text.strip():
                logger.warning("No text extracted from driver's license (after all PSM modes)")
                return {}
            
            logger.debug(f"Extracted text: {text}")
            
            # Parse the text and validate the license number
            result = self._parse_dl_text(text)
            
            # --- Improved license number extraction ---
            import difflib
            def normalize_license_candidate(s):
                # Remove spaces and non-alphanum, replace common OCR errors
                s = re.sub(r'[^A-Z0-9]', '', s.upper())
                # Common OCR errors
                replacements = {
                    'S': '5', 'O': '0', 'I': '1', 'L': '1',
                    'B': '8', 'G': '6', 'Z': '2', 'Q': '0',
                    'D': '0', 'T': '7', 'A': '4'
                }
                for wrong, correct in replacements.items():
                    s = s.replace(wrong, correct)
                return s

            # Relaxed pattern: allow any non-alphanum between groups, require 1 letter + 14 digits
            candidates = re.findall(r'([A-Z5S][^A-Z0-9]?[0-9OIl]{3}[^A-Z0-9]?[0-9OIl]{3}[^A-Z0-9]?[0-9OIl]{2}[^A-Z0-9]?[0-9OIl]{3}[^A-Z0-9]?[0-9OIl])', text, re.IGNORECASE)
            normalized_candidates = [normalize_license_candidate(c) for c in candidates]
            logger.info(f"License number candidates: {normalized_candidates}")

            # Score by similarity to expected format (M532558539650)
            expected_format = 'M532558539650'
            def score(candidate):
                # Base score from sequence matcher
                base_score = difflib.SequenceMatcher(None, candidate, expected_format).ratio()
                
                # Additional scoring factors
                length_score = 1.0 if len(candidate) == 13 else 0.5  # Perfect length gets full points
                format_score = 1.0 if re.match(r'^[A-Z]\d{12}$', candidate) else 0.5  # Perfect format gets full points
                
                # Weight the scores
                final_score = (base_score * 0.4) + (length_score * 0.3) + (format_score * 0.3)
                return final_score

            if normalized_candidates:
                best = max(normalized_candidates, key=score)
                logger.info(f"Best license number candidate: {best}")
                # Try to reformat to expected pattern
                if len(best) == 13 or len(best) == 14 or len(best) == 15:
                    # Try to insert dashes at the right places
                    reformatted = f"{best[0]}{best[1:4]}-{best[4:7]}-{best[7:9]}-{best[9:12]}-{best[12]}"
                    result['license_number'] = reformatted
                    logger.info(f"Reformatted license number: {reformatted}")
                else:
                    result['license_number'] = best
                    logger.info(f"Used best candidate as license number: {best}")
            
            # --- DOB extraction from cropped region ---
            dob_text = ''
            try:
                if 'dob_ocr_text' in locals() and dob_ocr_text.strip():
                    dob_text = dob_ocr_text.replace('\n', ' ').replace('\r', ' ')
                    dob_text = ' '.join(dob_text.split())
                    # Try to extract DOB from this region
                    dob_match = re.search(r'(?:DOB|BIRTH|DATE OF BIRTH)?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})', dob_text)
                    if dob_match:
                        result['date_of_birth'] = dob_match.group(1)
                        logger.info(f"DOB extracted from cropped region: {result['date_of_birth']}")
            except Exception as e:
                logger.error(f"Error extracting DOB from cropped region: {str(e)}")
            
            # --- Expiration Date Extraction ---
            exp_match = re.search(r'(?:EXP|EXPIRATION|EXPIRES|EXP DATE|EXPIRATION DATE)[^0-9]*([0-9]{2}/[0-9]{2}/[0-9]{4})', text)
            if exp_match:
                result['expiration_date'] = exp_match.group(1)
            else:
                # Fallback: any MM/DD/YYYY after 'EXP'
                exp_idx = text.find('EXP')
                if exp_idx != -1:
                    after_exp = text[exp_idx:exp_idx+30]  # look ahead 30 chars
                    m2 = re.search(r'([0-9]{2}/[0-9]{2}/[0-9]{4})', after_exp)
                    if m2:
                        result['expiration_date'] = m2.group(1)

            return result
        except Exception as e:
            logger.error(f"Error extracting driver's license info: {str(e)}")
            return {}

    def get_dropbox_salesforce_folder(self) -> Optional[str]:
        """Get the configured Dropbox Salesforce folder path."""
        return self.dropbox_salesforce_path

    def _download_holiday_file(self, holiday_file: FileMetadata) -> Optional[str]:
        """Download the holiday file to a temporary location.
        
        Args:
            holiday_file (FileMetadata): The holiday file metadata
            
        Returns:
            Optional[str]: Path to the downloaded file, or None if download failed
        """
        try:
            logger.info(f"Downloading holiday file: {holiday_file.name}")
            
            # Create a temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
            temp_path = temp_file.name
            temp_file.close()
            
            # Download the file
            with open(temp_path, 'wb') as f:
                self.dbx.files_download_to_file(temp_path, holiday_file.path_display)
            
            logger.info(f"Successfully downloaded holiday file to: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Error downloading holiday file: {str(e)}")
            return None

    def _process_holiday_file(self, holiday_file: str = 'HOLIDAY CLIENT LIST 2025.xlsx') -> Tuple[Optional[FileMetadata], Optional[str], Optional[pd.ExcelFile], Optional[List[str]]]:
        """Process the holiday file by locating, downloading, and reading it.
        
        Args:
            holiday_file (str): Name of the holiday file to process
            
        Returns:
            Tuple containing:
            - FileMetadata: The holiday file metadata
            - str: Path to the temporary file
            - pd.ExcelFile: The Excel file object
            - List[str]: List of sheet names
        """
        try:
            logger.info(f"Processing holiday file: {holiday_file}")
            
            # Get the holiday file metadata
            holiday_file_metadata = self.get_dropbox_holiday_file(holiday_file)
            if not holiday_file_metadata:
                logger.error(f"Holiday file '{holiday_file}' not found")
                return None, None, None, None
            
            # Download the file
            temp_path = self._download_holiday_file(holiday_file_metadata)
            if not temp_path:
                logger.error("Failed to download holiday file")
                return None, None, None, None
            
            # Read the Excel file
            try:
                excel_file = pd.ExcelFile(temp_path)
                sheets = excel_file.sheet_names
                logger.info(f"Successfully read Excel file with sheets: {sheets}")
                return holiday_file_metadata, temp_path, excel_file, sheets
            except Exception as e:
                logger.error(f"Error reading Excel file: {str(e)}")
                return None, None, None, None
                
        except Exception as e:
            logger.error(f"Error processing holiday file: {str(e)}")
            return None, None, None, None

    def update_flatfile_with_account_info(self, account_info: Dict[str, Any], flatfile_excel: pd.ExcelFile = None, template_path: str = None, output_path: str = None) -> bool:
        """Update the FlatFile Excel with Dropbox account information.
        
        Args:
            account_info (Dict[str, Any]): Dictionary containing account information
            flatfile_excel (pd.ExcelFile): The Excel file object for the template
            template_path (str): Path to the template file
            output_path (str): Path to the output file
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            account_name = account_info.get('name_parts', {}).get('folder_name', '')
            logger.info(f"\n=== Starting FlatFile update for account: {account_name} ===")
            
            if not all([flatfile_excel, template_path, output_path]):
                logger.error("Missing required parameters for FlatFile update")
                return False
                
            # Get account data
            account_data = account_info.get('account_data', {})
            if not account_data:
                logger.warning("No account data found to update")
                return False
                
            # Map account data fields to Clients sheet columns
            mapped_data = {
                'First Name': account_data.get('first_name', ''),
                'Last Name': account_data.get('last_name', ''),
                'Address 1: Street': account_data.get('address', ''),
                'Address 1: City': account_data.get('city', ''),
                'Address 1: State/Province': account_data.get('state', ''),
                'Address 1: ZIP/Postal Code': account_data.get('zip', ''),
                'Email': account_data.get('email', ''),  # Ensure capital E in Email
                'Phone': account_data.get('phone', ''),
                'Birthday': account_data.get('drivers_license', {}).get('date_of_birth', ''),
                'Gender': account_data.get('drivers_license', {}).get('sex', ''),
                "Driver's License Number": account_data.get('drivers_license', {}).get('license_number', '')
            }
            logger.info(f"DEBUG: mapped_data before writing: {mapped_data}")
                
            # Debug: Log mapped data
            logger.info("\nMapped account data to Clients sheet columns:")
            for key, value in mapped_data.items():
                logger.info(f"  {key}: {value}")
                
            # Create a dictionary to store the updated dataframes
            updated_dfs = {}
            
            # Process only the Clients sheet
            sheet_name = "Clients"
            logger.info(f"\nProcessing sheet: {sheet_name}")
            df = pd.read_excel(flatfile_excel, sheet_name=sheet_name)
            
            # Debug: Log current sheet data
            logger.info(f"Current sheet data shape: {df.shape}")
            logger.info("Columns in sheet:")
            for col in df.columns:
                logger.info(f"  - {col}")
            
            # Check if this is a new entry or update
            last_name = mapped_data['Last Name'].lower()
            first_name = mapped_data['First Name'].lower()
            
            logger.info(f"\nSearching for matches with first_name: {first_name}, last_name: {last_name}")
            
            # Create a mask for matching rows
            mask = df.apply(lambda row: any(
                str(val).lower() == last_name or str(val).lower() == first_name 
                for val in row.values
            ), axis=1)
            
            matching_rows = df[mask]
            
            if not matching_rows.empty:
                # Update existing entry
                logger.info(f"\n=== Updating existing entry ===")
                logger.info(f"Found {len(matching_rows)} matching rows in sheet: {sheet_name}")
                for idx in matching_rows.index:
                    logger.info(f"\nUpdating row at index {idx}")
                    logger.info("Current row data:")
                    for col in df.columns:
                        logger.info(f"  {col}: {df.at[idx, col]}")
                    
                    # Update the row with new data
                    logger.info("\nUpdating with new data:")
                    for col in df.columns:
                        if col in mapped_data:
                            old_value = df.at[idx, col]
                            new_value = mapped_data[col]
                            if str(old_value).lower() != str(new_value).lower():
                                df.at[idx, col] = new_value
                                logger.info(f"  {col}: {old_value} -> {new_value}")
                            else:
                                logger.info(f"  {col}: No change (already matches)")
            else:
                # Add new entry
                logger.info(f"\n=== Adding new entry ===")
                logger.info(f"No matching rows found, adding new entry to sheet: {sheet_name}")
                # Create a new row with the same columns as the DataFrame
                new_row = pd.DataFrame([{col: mapped_data.get(col, '') for col in df.columns}])
                df = pd.concat([df, new_row], ignore_index=True)
                logger.info("\nNew row data:")
                for col in df.columns:
                    if col in mapped_data:
                        logger.info(f"  {col}: {mapped_data[col]}")
                    else:
                        logger.info(f"  {col}: <empty>")
            
            updated_dfs[sheet_name] = df
            
            # Read all other sheets without modification
            for other_sheet in flatfile_excel.sheet_names:
                if other_sheet != sheet_name:
                    logger.info(f"Reading unchanged sheet: {other_sheet}")
                    updated_dfs[other_sheet] = pd.read_excel(flatfile_excel, sheet_name=other_sheet)
            
            # Write the updated data to both Excel and CSV files
            excel_output_path = output_path.replace('docs/', 'accounts/')
            csv_output_path = output_path.replace('docs/', 'accounts/').replace('.xlsx', '.csv')
            
            # Write Excel file
            logger.info(f"\nWriting Excel file to: {excel_output_path}")
            
            # Read existing Excel file if it exists
            if os.path.exists(excel_output_path):
                existing_excel = pd.ExcelFile(excel_output_path)
                existing_dfs = {}
                for sheet_name in existing_excel.sheet_names:
                    existing_dfs[sheet_name] = pd.read_excel(existing_excel, sheet_name=sheet_name)
                
                # Combine existing data with new data
                for sheet_name in updated_dfs:
                    if sheet_name in existing_dfs:
                        # Concatenate existing and new data
                        combined_df = pd.concat([existing_dfs[sheet_name], updated_dfs[sheet_name]], ignore_index=True)
                        # Remove any duplicates based on all columns
                        combined_df = combined_df.drop_duplicates()
                        updated_dfs[sheet_name] = combined_df
            
            # Write the combined data
            with pd.ExcelWriter(excel_output_path, engine='openpyxl', mode='w') as writer:
                for sheet_name, df in updated_dfs.items():
                    logger.info(f"Writing sheet {sheet_name} with {len(df)} rows")
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Write CSV file with only Clients sheet data
            logger.info(f"\nWriting CSV file to: {csv_output_path}")
            
            # Read existing CSV file if it exists
            if os.path.exists(csv_output_path):
                existing_df = pd.read_csv(csv_output_path)
                # Combine with new data
                combined_df = pd.concat([existing_df, updated_dfs["Clients"]], ignore_index=True)
                # Remove any duplicates
                combined_df = combined_df.drop_duplicates()
                # Write the combined data
                combined_df.to_csv(csv_output_path, index=False)
            else:
                # Write new data with header
                updated_dfs["Clients"].to_csv(csv_output_path, index=False)
            
            logger.info(f"\n=== Successfully completed FlatFile update ===")
            logger.info(f"  Excel: {excel_output_path}")
            logger.info(f"  CSV: {csv_output_path}")
            logger.info(f"  Account: {account_name}")
            logger.info("=== End FlatFile update ===\n")
            return True
            
        except Exception as e:
            logger.error(f"Error updating FlatFile: {str(e)}")
            logger.error("Stack trace:", exc_info=True)
            return False

    def _parse_dl_text(self, text: str) -> Dict[str, str]:
        """
        Parse text extracted from driver's license to extract relevant information.
        Enhanced for Florida licenses: robustly extract license number, DOB, and sex.
        """
        result = {}
        text = text.replace('\n', ' ').replace('\r', ' ')
        text = ' '.join(text.split())

        # --- License Number Extraction ---
        # Fix common OCR errors
        ocr_replacements = {
            '¢': '0', '|': '1', '§': '5', '©': '0', '®': '0', '“': '1', '”': '1', '‘': '1', '’': '1',
            'S': '5', 'O': '0', 'I': '1', 'L': '1', 'B': '8', 'G': '6', 'Z': '2', 'Q': '0', 'D': '0', 'T': '7', 'A': '4',
            '(': '0', ')': '0', '{': '0', '}': '0', '[': '0', ']': '0', 'o': '0', 's': '5', 'l': '1', 'i': '1', 'a': '4',
            'b': '6', 'g': '9', 'z': '2', 'q': '0', 'd': '0', 't': '7', 'e': '6', 'E': '6', 'B': '8', 'G': '6', 'Z': '2', 'Q': '0', 'D': '0', 'T': '7', 'A': '4'
        }
        clean_text = text
        for wrong, correct in ocr_replacements.items():
            clean_text = clean_text.replace(wrong, correct)

        # Remove all whitespace and newlines for aggressive search
        clean_text_no_space = re.sub(r'\s+', '', clean_text)

        # Try to find license number with or without dashes, possibly missing leading M
        lic_patterns = [
            r'([A-Z][0-9]{3}-[0-9]{3}-[0-9]{2}-[0-9]{3}-[0-9])',
            r'([0-9]{3}-[0-9]{3}-[0-9]{2}-[0-9]{3}-[0-9])',
            r'([A-Z][0-9]{12})',
            r'([0-9]{12})',
            r'([A-Z][0-9]{3}[0-9]{3}[0-9]{2}[0-9]{3}[0-9])',
            r'([0-9]{3}[0-9]{3}[0-9]{2}[0-9]{3}[0-9])'
        ]
        license_number = None
        for pat in lic_patterns:
            m = re.search(pat, clean_text)
            if m:
                license_number = m.group(1)
                break
        # If not found, try on the whitespace-stripped version
        if not license_number:
            for pat in lic_patterns:
                m = re.search(pat, clean_text_no_space)
                if m:
                    license_number = m.group(1)
                    break
        # If still not found, try to join split fragments
        if not license_number:
            # Find all fragments that look like part of the license number
            frags = re.findall(r'[A-Z0-9]{2,}', clean_text_no_space)
            joined = ''.join(frags)
            for pat in lic_patterns:
                m = re.search(pat, joined)
                if m:
                    license_number = m.group(1)
                    break
        # Post-process: if missing leading M, add it
        if license_number:
            if re.match(r'^[0-9]', license_number):
                license_number = 'M' + license_number
            # Remove dashes for normalization
            lic_digits = re.sub(r'[^A-Z0-9]', '', license_number)
            # Reformat to M###-###-##-###-#
            if len(lic_digits) == 13:
                license_number = f"{lic_digits[0]}{lic_digits[1:4]}-{lic_digits[4:7]}-{lic_digits[7:9]}-{lic_digits[9:12]}-{lic_digits[12]}"
            result['license_number'] = license_number

        # --- DOB Extraction ---
        dob_match = re.search(r'(?:DOB|BIRTH|DATE OF BIRTH)?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})', clean_text)
        if dob_match:
            result['date_of_birth'] = dob_match.group(1)
        else:
            # Fallback: any MM/DD/YYYY
            dob_match = re.search(r'([0-9]{2}/[0-9]{2}/[0-9]{4})', clean_text)
            if dob_match:
                result['date_of_birth'] = dob_match.group(1)

        # --- Sex Extraction ---
        # Try to find 'SEX' label first
        sex_match = re.search(r'SEX[:=\-~ ]*([MF])', clean_text)
        if sex_match:
            result['sex'] = sex_match.group(1)
        else:
            # Fallback: look for F or M after DOB
            if 'date_of_birth' in result:
                dob_idx = clean_text.find(result['date_of_birth'])
                if dob_idx != -1:
                    after_dob = clean_text[dob_idx+len(result['date_of_birth']):dob_idx+len(result['date_of_birth'])+10]
                    m2 = re.search(r'([MF])', after_dob)
                    if m2:
                        result['sex'] = m2.group(1)

        # Optionally: log the extracted information
        if result:
            logger.info("Extracted driver's license information (enhanced):")
            for field, value in result.items():
                logger.info(f"  {field}: {value}")
        else:
            logger.warning("No information could be extracted from driver's license (enhanced)")
            logger.debug(f"Raw OCR text: {text}")
        return result

def update_env_file(env_file, token=None, root_folder=None, directory=None):
    """Update the .env file with new values."""
    try:
        # Read existing content
        existing_content = {}
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        existing_content[key] = value
        
        # Update values
        if token:
            existing_content['DROPBOX_TOKEN'] = token
        if root_folder:
            existing_content['DROPBOX_FOLDER'] = root_folder
        if directory:
            existing_content['DATA_DIRECTORY'] = directory
        
        # Write back to file
        with open(env_file, 'w') as f:
            for key, value in existing_content.items():
                f.write(f"{key}={value}\n")
        
        if token:
            print(f"✓ Access token saved to {env_file}")
        if root_folder:
            print(f"✓ Root folder saved to {env_file}")
        if directory:
            print(f"✓ Directory saved to {env_file}")
    except Exception as e:
        print(f"✗ Error saving to {env_file}: {e}")
        raise

def get_renamed_path(metadata, path, is_folder=False, dbx=None):
    """Get the renamed path with date prefix."""
    try:
        # Get the original name
        original_name = os.path.basename(path)
        
        # If the name already has a date prefix, don't modify it
        if has_date_prefix(original_name):
            print(f"File/folder already has date prefix: {original_name}")
            return original_name
        
        # Get date for prefix
        if is_folder:
            # For folders, try to get creation date
            if dbx:
                date_obj = get_folder_creation_date(dbx, path)
                date_prefix = date_obj.strftime("%y%m%d")
                print(f"Using folder creation date for {path}: {date_prefix}")
            else:
                # Fallback to current date if dbx not provided
                date_prefix = datetime.datetime.now().strftime("%y%m%d")
        else:
            # For files, use modification date from metadata
            date_prefix = metadata.server_modified.strftime("%y%m%d")
        
        # Create new name with date prefix
        new_name = f"{date_prefix} {original_name}"
        
        # If it's a folder, ensure it ends with a slash
        if is_folder and not new_name.endswith('/'):
            new_name += '/'
            
        return new_name
    except Exception as e:
        print(f"Error generating renamed path for {path}: {e}")
        return os.path.basename(path)

def download_and_rename_file(dbx, dropbox_path, local_dir):
    """Download a file from Dropbox and rename it with its modification date if it doesn't already have a date prefix."""
    try:
        # Get file metadata
        metadata = dbx.files_get_metadata(dropbox_path)
        
        # Get the original name
        original_name = os.path.basename(dropbox_path)
        
        # Check if file already has a date prefix
        if has_date_prefix(original_name):
            print(f"File already has date prefix, downloading with original name: {original_name}")
            local_path = os.path.join(local_dir, original_name)
        else:
            # Generate new filename with date prefix
            new_name = get_renamed_path(metadata, dropbox_path)
            local_path = os.path.join(local_dir, new_name)
            # Log the renamed file
            log_renamed_file(dropbox_path, new_name, os.path.dirname(local_dir))
        
        # Download the file
        print(f"Downloading: {dropbox_path} -> {local_path}")
        dbx.files_download_to_file(local_path, dropbox_path)
        
    except Exception as e:
        print(f"Error processing file {dropbox_path}: {e}")

def list_dropbox_folder_contents(dbx, path, sort_by_recency: bool = False) -> List[FileMetadata]:
    """
    List the contents of a Dropbox folder, handling pagination.
    
    Args:
        dbx: Dropbox client instance
        path: Path to list contents from
        sort_by_recency: If True, sorts folders by their recency (most recent first)
        
    Returns:
        List[FileMetadata]: List of folder contents, optionally sorted by recency
    """
    try:
        result = dbx.files_list_folder(path)
        entries = result.entries
        while result.has_more:
            result = dbx.files_list_folder_continue(result.cursor)
            entries.extend(result.entries)
            
        if sort_by_recency:
            # Separate folders and files
            folders = []
            files = []
            for entry in entries:
                if isinstance(entry, dropbox.files.FolderMetadata):
                    folders.append(entry)
                else:
                    files.append(entry)
            
            # Sort folders by their creation time
            folders.sort(key=lambda x: x.server_created, reverse=True)
            
            # Sort files by their modification time
            files.sort(key=lambda x: x.server_modified, reverse=True)
            
            # Combine sorted folders and files
            entries = folders + files
            
        return entries
    except ApiError as e:
        print(f"Error listing folder {path}: {e}")
        return []

def find_folder_path(dbx, target_folder):
    """Find the full path of a folder in Dropbox."""
    try:
        # Start from root
        result = dbx.files_list_folder('')
        
        # Check each entry
        for entry in result.entries:
            if isinstance(entry, dropbox.files.FolderMetadata):
                if entry.name == target_folder:
                    return entry.path_display
                
                # Recursively check subfolders
                sub_path = find_folder_path(dbx, target_folder)
                if sub_path:
                    return sub_path
    except ApiError as e:
        print(f"Error finding folder {target_folder}: {e}")
    
    return None

def get_access_token() -> str:
    """
    Get Dropbox access token from .env file or environment variable.
    If not found, prompt user to enter it.
    
    Returns:
        str: Dropbox access token
    """
    # First try to load from .env file
    try:
        load_dotenv()
        token = os.getenv('DROPBOX_TOKEN')
        if token:
            logger.info("Token loaded from .env file (DROPBOX_TOKEN)")
            return token
    except Exception as e:
        logger.warning(f"Failed to load .env file: {str(e)}")
    
    # If not in .env, try environment variable
    token = os.getenv('DROPBOX_TOKEN')
    if token:
        logger.info("Token loaded from environment variable DROPBOX_TOKEN")
        return token
    
    # If still not found, prompt user
    logger.warning("No token found in .env file or environment")
    token = input("Please enter your Dropbox access token: ").strip()
    if not token:
        raise ValueError("No access token provided")
    return token

def get_DROPBOX_FOLDER(env_file):
    """Get the Dropbox root folder from environment or prompt user."""
    # Load environment variables
    load_dotenv(env_file)
    
    # Try to get folder from environment
    folder = os.getenv('DROPBOX_FOLDER')
    
    # If no folder found, prompt user
    if not folder:
        print("\nDROPBOX_FOLDER not found in .env file.")
        print("Please enter the root folder path in Dropbox:")
        folder = input().strip()
        
        if not folder:
            print("Error: No folder path provided")
            return None
        
        # Update .env file with the new folder
        update_env_file(env_file, root_folder=folder)
    
    return folder

def count_account_folders(dbx, path, allowed_folders=None, ignored_folders=None):
    """Count the number of account folders in the given path."""
    try:
        entries = list_dropbox_folder_contents(dbx, path)
        count = 0
        
        for entry in entries:
            if isinstance(entry, dropbox.files.FolderMetadata):
                # Skip ignored folders
                if ignored_folders and entry.name in ignored_folders:
                    continue
                
                # Check if folder is allowed
                if allowed_folders and entry.name not in allowed_folders:
                    continue
                
                count += 1
        
        return count
    except ApiError as e:
        print(f"Error counting folders in {path}: {e}")
        return 0

def get_DATA_DIRECTORY(env_file):
    """Get the data directory from environment or prompt user."""
    # Load environment variables
    load_dotenv(env_file)
    
    # Try to get directory from environment
    directory = os.getenv('DATA_DIRECTORY')
    
    # If no directory found, prompt user
    if not directory:
        print("\nDATA_DIRECTORY not found in .env file.")
        print("Please enter the base directory to save files (default: ./data):")
        directory = input().strip()
        
        if not directory:
            directory = './data'
            print(f"Using default directory: {directory}")
        
        # Update .env file with the new directory
        update_env_file(env_file, directory=directory)
    
    return directory

def get_dropbox_root_folder(env_file, report_logger) -> str:
    """Get the root path from environment or prompt user."""
    # Load environment variables
    load_dotenv(env_file)
    
    # Try to get root path from environment
    root_folder = os.getenv('root_folder')
    # Get the root folder from environment
    root_folder = get_DROPBOX_FOLDER(env_file)
    if not root_folder:
        logger.error("Could not get DROPBOX_FOLDER from environment")
        report_logger.info("\nCould not get DROPBOX_FOLDER from environment")
        return ''
        
    logger.info(f"Raw root folder from environment: {root_folder}")

    # Clean and validate the path
    try:
        root_folder = clean_dropbox_folder_name(root_folder)
        logger.info(f"Cleaned Dropbox folder name: {root_folder}")
    except ValueError as e:
        logger.error(f"Invalid path format: {str(e)}")
        report_logger.info(f"\nInvalid path format: {str(e)}")
        return ''
        
    if not root_folder:
        logger.error(f"Invalid path: {root_folder}")
        report_logger.info(f"\nInvalid path: {root_folder}")
        return ''
    
    return root_folder


def get_folder_structure(dbx, path=None):
    """
    Get the folder structure from Dropbox.
    
    Args:
        dbx: Dropbox client instance
        path: Optional path to start from. If None, uses root folder.
        
    Returns:
        dict: Dictionary containing folder structure information
    """
    try:
        if path is None:
            path = get_DROPBOX_FOLDER('.env')
            if not path:
                raise ValueError("No Dropbox folder path specified")
        
        # Clean and validate the path
        clean_path = clean_dropbox_folder_name(path)
        if not clean_path:
            raise ValueError(f"Invalid path: {path}")
            
        # Get folder contents
        entries = list_dropbox_folder_contents(dbx, clean_path)
        
        # Initialize counts
        counts = {
            'total': 0,
            'allowed': 0,
            'ignored': 0,
            'not_allowed': 0,
            'files': 0
        }
        
        # Process entries
        for entry in entries:
            if isinstance(entry, dropbox.files.FolderMetadata):
                counts['total'] += 1
                counts['allowed'] += 1  # For now, count all folders as allowed
            else:
                counts['files'] += 1
                
        return counts
        
    except Exception as e:
        logger.error(f"Error getting folder structure: {str(e)}")
        return {
            'total': 0,
            'allowed': 0,
            'ignored': 0,
            'not_allowed': 0,
            'files': 0
        }
    

def get_folder_metadata(dropbox_client, folder_path):
    """Get the metadata of a folder in Dropbox."""
    try:
        logger.info(f"get_folder_metadata: {folder_path}")
        return dropbox_client.dbx.files_get_metadata(folder_path)
    except ApiError as e:
        if e.error.is_path() and e.error.get_path().is_not_found():
            # Path doesn't exist
            print(f"Path not found: {folder_path}")
        else:
            # Other error (permissions, network, etc.)
            print(f"Error accessing path: {e}")

def display_summary(counts, folders_only=False, ignored_folders=None, account_folders=None):
    """
    Display a summary of the analysis results.
    
    Args:
        counts (dict): Dictionary containing folder and file counts
        folders_only (bool): Whether only folders were analyzed
        ignored_folders (list): List of ignored folders
        account_folders (list): List of account folders
    """
    print("\n=== Summary ===")
    if not folders_only:
        print(f"Total Dropbox account files: {counts['files']}")
    if counts['allowed'] > 0:
        print(f"Dropbox account folders: {counts['allowed']}")
    ignored_account_folders = []
    if ignored_folders and account_folders:
        ignored_account_folders = [folder for folder in account_folders if folder in ignored_folders]
    print(f"Ignored Dropbox account folders: {len(ignored_account_folders)}")
    if ignored_account_folders:
        print("Ignored Dropbox account folders list:")
        for folder in ignored_account_folders:
            print(f"  - {folder}")

def get_refresh_token() -> str:
    """
    Get Dropbox refresh token from .env file or environment variable.
    If not found, prompt user to enter it.
    
    Returns:
        str: Dropbox refresh token
    """
    # First try to load from .env file
    try:
        load_dotenv()
        token = os.getenv('DROPBOX_REFRESH_TOKEN')
        if token:
            logger.info("Refresh token loaded from .env file (DROPBOX_REFRESH_TOKEN)")
            return token
    except Exception as e:
        logger.warning(f"Failed to load .env file: {str(e)}")
    
    # If not in .env, try environment variable
    token = os.getenv('DROPBOX_REFRESH_TOKEN')
    if token:
        logger.info("Refresh token loaded from environment variable DROPBOX_REFRESH_TOKEN")
        return token
    
    # If still not found, prompt user
    logger.warning("No refresh token found in .env file or environment")
    token = input("Please enter your Dropbox refresh token: ").strip()
    if not token:
        raise ValueError("No refresh token provided")
    return token

def get_app_key() -> str:
    """
    Get Dropbox app key from .env file or environment variable.
    If not found, prompt user to enter it.
    
    Returns:
        str: Dropbox app key
    """
    # First try to load from .env file
    try:
        load_dotenv()
        key = os.getenv('DROPBOX_APP_KEY')
        if key:
            logger.info("App key loaded from .env file (DROPBOX_APP_KEY)")
            return key
    except Exception as e:
        logger.warning(f"Failed to load .env file: {str(e)}")
    
    # If not in .env, try environment variable
    key = os.getenv('DROPBOX_APP_KEY')
    if key:
        logger.info("App key loaded from environment variable DROPBOX_APP_KEY")
        return key
    
    # If still not found, prompt user
    logger.warning("No app key found in .env file or environment")
    key = input("Please enter your Dropbox app key: ").strip()
    if not key:
        raise ValueError("No app key provided")
    return key

def refresh_access_token() -> str:
    """
    Refresh the Dropbox access token using the refresh token and app key.
    
    Returns:
        str: New access token
    """
    try:
        refresh_token = get_refresh_token()
        app_key = get_app_key()
        
        # Create OAuth2 refresh flow
        auth_flow = dropbox.DropboxOAuth2FlowNoRedirect(
            app_key,
            token_access_type='offline'
        )
        
        # Get new access token
        new_token = auth_flow.refresh_access_token(refresh_token)
        
        # Update .env file with new token
        update_env_file('.env', token=new_token.access_token)
        
        logger.info("Successfully refreshed access token")
        return new_token.access_token
        
    except Exception as e:
        logger.error(f"Failed to refresh access token: {str(e)}")
        raise 