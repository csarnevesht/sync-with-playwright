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

from .date_utils import has_date_prefix, get_folder_creation_date
from .path_utils import clean_dropbox_folder_name
from .file_utils import log_renamed_file
from src.config import DROPBOX_FOLDER, ACCOUNT_INFO_PATTERN, DRIVERS_LICENSE_PATTERN, DROPBOX_HOLIDAY_FOLDER, DROPBOX_SALESFORCE_FOLDER

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

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
        

    def get_dropbox_accounts(self) -> List[dropbox.files.FolderMetadata]:
        """Get all account folders under the root folder."""
        try:
            entries = list_dropbox_folder_contents(self.dbx,self.root_folder)
            all_account_folders = [entry.name for entry in entries if isinstance(entry, dropbox.files.FolderMetadata)]
            return all_account_folders
        except Exception as e:
            print(f"Error getting account folders: {e}")
            return []
            

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
    
    def get_dropbox_holiday_file(self, holiday_file: str = 'HOLIDAY CLIENT LIST.xlsx') -> Optional[FileMetadata]:
        """Get the specified holiday file from the holiday folder."""
        if not self.dropbox_holiday_path:
            logging.warning("Dropbox holiday folder path is not set.")
            return None
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

    def get_dropbox_account_info(self, account_name: str, dropbox_account_name_parts: Dict[str, Any]) -> Dict[str, Any]:
        """Get account information from the holiday Excel file.
        
        This method:
        1. Checks for special cases in accounts/special_cases.json
        2. Locates the holiday account info file
        3. Downloads and reads the Excel file
        4. Searches for the account in all sheets
        5. Extracts available information
        
        Args:
            account_name (str): The name of the account to search for (used for logging)
            dropbox_account_name_parts (Dict[str, Any]): Dictionary containing:
                - folder_name (str): Original folder name
                - last_name (str): Last name to search for
                - full_name (str): Full name to search for
                - normalized_names (List[str]): List of normalized name variations
                - swapped_names (List[str]): List of name variations with swapped first/last
                - expected_matches (List[str]): List of expected matches for special cases
                
        Returns:
            Dict[str, Any]: Dictionary containing:
                - name_parts (Dict[str, Any]): Original name parts and search info
                - search_info (Dict[str, Any]): Information about the search process
                - account_data (Dict[str, Any]): Extracted account information
        """
        logger = logging.getLogger('dropbox_utils')
        
        logger.info(f"\n=== Starting account info search for: {account_name} ===")
        
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
                    'total_exact_matches': 0,
                    'total_partial_matches': 0,
                    'total_no_matches': 1
                }
            },
            'account_data': {}
        }
        
        try:
            # Log search parameters
            logger.info("Search parameters:")
            logger.info(f"  - Last name: {dropbox_account_name_parts['last_name']}")
            logger.info(f"  - Full name: {dropbox_account_name_parts['full_name']}")
            logger.info(f"  - Normalized names: {dropbox_account_name_parts['normalized_names']}")
            logger.info(f"  - Swapped names: {dropbox_account_name_parts['swapped_names']}")
            logger.info(f"  - Expected Dropbox matches: {dropbox_account_name_parts['expected_dropbox_matches']}")
            logger.info("")
            
            # Step 1: Locate holiday file
            logger.info("Step 1: Locating holiday file...")
            holiday_file = self.get_dropbox_holiday_file()
            if not holiday_file:
                logger.error("Could not find holiday file")
                return dropbox_account_info
                
            # Step 2: Download holiday file
            logger.info("\nStep 2: Downloading holiday file...")
            temp_path = self._download_holiday_file(holiday_file)
            if not temp_path:
                logger.error("Could not download holiday file")
                return dropbox_account_info
            
            try:
                # Step 3: Read Excel file
                logger.info("\nStep 3: Reading Excel file...")
                excel_file = pd.ExcelFile(temp_path)
                sheets = excel_file.sheet_names
                logger.info(f"Found {len(sheets)} sheets in the Excel file: {sheets}")
                
                # Initialize variables for tracking matches
                account_row = None
                match_found = False
                match_sheet = None
                sheet_search_info = []  # Store search info for each sheet

                last_name = dropbox_account_name_parts['last_name'].lower()
                first_name = dropbox_account_name_parts['first_name'].lower()
                
                # Search through each sheet
                for sheet_name in sheets:
                    logger.info(f"\nSearching in sheet: {sheet_name}")
                    df = pd.read_excel(temp_path, sheet_name=sheet_name)
                    logger.info(f"Sheet dimensions: {df.shape[0]} rows x {df.shape[1]} columns")
                    logger.info(f"df: {df}")

                    # Search for the last name in any column
                    logger.info(f"Searching for last name: {last_name} in any column of sheet: {sheet_name}")
                    # Convert all columns to string, clean values, and handle NaN values
                    df_str = df.astype(str).apply(lambda x: x.apply(self._clean_cell_value).str.lower())
                    # Create a mask for rows containing the last name
                    mask = df_str.apply(lambda row: any(last_name in str(cell) for cell in row), axis=1)
                    # Get all matching rows
                    matching_rows = df[mask]
                    logger.info(f"Found {len(matching_rows)} matching rows")
                    if not matching_rows.empty:
                        logger.info("Matching rows:")
                        for idx, row in matching_rows.iterrows():
                            # Convert row to list of values with their indices, cleaning each value
                            row_data = {f"Column {i}": self._clean_cell_value(str(val)) for i, val in enumerate(row)}
                            logger.info(f"Row {idx}: {row_data}")
                    
                    if matching_rows.empty:
                        # Search for the first name in any column
                        logger.info(f"No matching rows found in sheet {sheet_name} for last name: {last_name}...")

                    if not matching_rows.empty:
                        # Check for multiple matches
                        if len(matching_rows) > 1:
                            logger.warning(f"Found {len(matching_rows)} matches in {sheet_name} for last name: {last_name}")
                            # Update search info to indicate multiple matches
                            dropbox_account_info['search_info']['status'] = 'multiple_matches'
                            dropbox_account_info['search_info']['match_info']['match_status'] = f"Found {len(matching_rows)} matches"
                            dropbox_account_info['search_info']['match_info']['total_exact_matches'] = len(matching_rows)
                            dropbox_account_info['search_info']['match_info']['total_no_matches'] = 0
                            # Store all matching rows for reference
                            dropbox_account_info['search_info']['matches'] = [
                                {f"Column {i}": self._clean_cell_value(str(val)) for i, val in enumerate(row)}
                                for _, row in matching_rows.iterrows()
                            ]
                            # Still use the first match for account data
                            account_row = matching_rows.iloc[0]
                        else:
                            account_row = matching_rows.iloc[0]
                            dropbox_account_info['search_info']['status'] = 'found'
                            dropbox_account_info['search_info']['match_info']['match_status'] = "Match found"
                            dropbox_account_info['search_info']['match_info']['total_exact_matches'] = 1
                            dropbox_account_info['search_info']['match_info']['total_no_matches'] = 0
                        
                        match_found = True
                        match_sheet = sheet_name
                        logger.info(f"Found matches in {sheet_name} by last name in any column")
                        break
                
                
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
                    
                    # Update match status
                    dropbox_account_info['search_info']['status'] = 'found'
                    dropbox_account_info['search_info']['match_info']['match_status'] = "Match found"
                    dropbox_account_info['search_info']['match_info']['total_exact_matches'] = 1
                    dropbox_account_info['search_info']['match_info']['total_no_matches'] = 0
                    logger.info(f"Successfully extracted account data from {match_sheet}")
                else:
                    logger.info("No match found in any sheet")

                # If no match found, log detailed explanation
                if not dropbox_account_info['account_data']:
                    # Log to analyzer.log
                    logging.info("\n=== NO MATCH EXPLANATION ===")
                    logging.info(f"Account: {account_name}")
                    logging.info(f"Last name searched: {dropbox_account_name_parts.get('last_name', '')}")
                    logging.info("\nSearch process:")
                    for sheet_name in sheets:
                        df = pd.read_excel(temp_path, sheet_name=sheet_name)
                        logging.info(f"\nSheet: {sheet_name}")
                        logging.info(f"  - Dimensions: {df.shape[0]} rows x {df.shape[1]} columns")
                        logging.info(f"  - Columns: {list(df.columns)}")
                        logging.info(f"  - First row values: {[str(val) for val in df.iloc[0].values]}")
                        logging.info(f"  - Search method: Searched for last name '{last_name}' in all columns")
                        logging.info(f"  - Result: No matches found")
                    logging.info("=== END NO MATCH EXPLANATION ===\n")

                    # Log to report.log
                    report_logger = logging.getLogger('report')
                    report_logger.info("\n=== NO MATCH EXPLANATION ===")
                    report_logger.info(f"Account: {account_name}")
                    report_logger.info(f"Last name searched: {dropbox_account_name_parts.get('last_name', '')}")
                    report_logger.info("\nSearch process:")
                    for sheet_name in sheets:
                        df = pd.read_excel(temp_path, sheet_name=sheet_name)
                        report_logger.info(f"\nSheet: {sheet_name}")
                        report_logger.info(f"  - Dimensions: {df.shape[0]} rows x {df.shape[1]} columns")
                        report_logger.info(f"  - Columns: {list(df.columns)}")
                        report_logger.info(f"  - First row values: {[str(val) for val in df.iloc[0].values]}")
                        report_logger.info(f"  - Search method: Searched for last name '{last_name}' in all columns")
                        report_logger.info(f"  - Result: No matches found")
                    report_logger.info("=== END NO MATCH EXPLANATION ===\n")

            finally:
                # Clean up temporary file
                try:
                    os.remove(temp_path)
                    logger.info("Temporary file cleaned up successfully")
                except Exception as e:
                    logger.error(f"Error cleaning up temporary file: {e}")
            
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
        """Get the driver's license file (*DL.jpeg) for an account."""
        files = self.list_folder_contents(account_folder)
        pattern = DRIVERS_LICENSE_PATTERN.replace('*', '.*')
        for file in files:
            if re.match(pattern, file.name):
                return file
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
        """
        Extract information from driver's license image using OCR.
        Returns a dictionary with driver's license details.
        """
        try:
            logging.info(f"Extracting information from driver's license: {image_path}")
            # Read the image
            image = Image.open(image_path)
            
            # Extract text using OCR
            text = pytesseract.image_to_string(image)
            logging.info("Successfully performed OCR on driver's license")
            
            # Parse the extracted text
            dl_info = {}
            
            # Extract License Number
            license_match = re.search(r'License\s*#?:?\s*([A-Z0-9]+)', text, re.IGNORECASE)
            if license_match:
                dl_info['license_number'] = license_match.group(1)
                logging.info(f"Found license number: {dl_info['license_number']}")
            
            # Extract Expiration Date
            exp_match = re.search(r'Exp(?:iration)?:?\s*(\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE)
            if exp_match:
                dl_info['expiration_date'] = exp_match.group(1)
                logging.info(f"Found expiration date: {dl_info['expiration_date']}")
            
            # Extract Date of Birth
            dob_match = re.search(r'DOB:?\s*(\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE)
            if dob_match:
                dl_info['date_of_birth'] = dob_match.group(1)
                logging.info(f"Found date of birth: {dl_info['date_of_birth']}")
            
            return dl_info

        except Exception as e:
            logging.error(f"Error extracting driver's license info: {e}")
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
            logger = logging.getLogger('dropbox_utils')
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

def list_dropbox_folder_contents(dbx, path) -> List[FileMetadata]:
    """List the contents of a Dropbox folder, handling pagination."""
    try:
        result = dbx.files_list_folder(path)
        entries = result.entries
        while result.has_more:
            result = dbx.files_list_folder_continue(result.cursor)
            entries.extend(result.entries)
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