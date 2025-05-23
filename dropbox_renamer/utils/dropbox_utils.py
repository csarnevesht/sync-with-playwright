"""Utility functions for Dropbox operations."""

import os
import dropbox
from dropbox.exceptions import ApiError
from dropbox.files import FileMetadata
from typing import List, Tuple, Optional, Dict
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

from .date_utils import has_date_prefix, get_folder_creation_date
from .path_utils import clean_dropbox_path
from .file_utils import log_renamed_file
from .config import DROPBOX_ROOT_FOLDER, ACCOUNT_INFO_PATTERN, DRIVERS_LICENSE_PATTERN

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# Set Dropbox logger level to WARNING to suppress INFO messages
logging.getLogger('dropbox').setLevel(logging.WARNING)

class DropboxClient:
    def __init__(self, token: str, debug_mode: bool = False):
        self.dbx = dropbox.Dropbox(token)
        self.debug_mode = debug_mode
        # Extract just the folder name from the path if it's a full URL
        folder = DROPBOX_ROOT_FOLDER
        if folder.startswith('http'):
            # Extract the last part of the path
            folder = folder.split('/')[-1]
            # URL decode the folder name
            folder = urllib.parse.unquote(folder)
        self.root_folder = folder
        logging.info(f"Initialized DropboxClient with root folder: {self.root_folder}")
        if debug_mode:
            logging.info("Debug mode is enabled")

    def _debug_show_files(self, files: List[FileMetadata], skip_patterns: List[str] = None) -> List[FileMetadata]:
        """
        Show files to be processed and which ones will be skipped.
        Returns the list of files that will be processed.
        """
        if not self.debug_mode:
            return files

        print("\nFiles to be processed:")
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

    def get_account_folders(self) -> List[str]:
        """Get all account folders under the root folder."""
        try:
            result = self.dbx.files_list_folder(f"/{self.root_folder}")
            return [entry.name for entry in result.entries if isinstance(entry, dropbox.files.FolderMetadata)]
        except Exception as e:
            print(f"Error getting account folders: {e}")
            return []

    def parse_account_name(self, folder_name: str) -> Tuple[str, str, Optional[str]]:
        """Parse account name into first, last, and middle names."""
        parts = folder_name.split()
        if len(parts) == 2:
            return parts[0], parts[1], None
        elif len(parts) > 2:
            return parts[0], parts[-1], ' '.join(parts[1:-1])
        return folder_name, '', None

    def get_account_files(self, account_folder: str) -> List[FileMetadata]:
        """Get all files in an account folder."""
        try:
            result = self.dbx.files_list_folder(f"/{self.root_folder}/{account_folder}")
            files = [entry for entry in result.entries if isinstance(entry, dropbox.files.FileMetadata)]
            
            # Show files in debug mode
            skip_patterns = [r'.*\.DS_Store$', r'.*\.tmp$']  # Add any patterns for files to skip
            return self._debug_show_files(files, skip_patterns)
            
        except Exception as e:
            logging.error(f"Error getting account files: {e}")
            return []

    def get_account_info_file(self, account_folder: str) -> Optional[FileMetadata]:
        """Get the account info file (*App.pdf) for an account."""
        files = self.get_account_files(account_folder)
        pattern = ACCOUNT_INFO_PATTERN.replace('*', '.*')
        for file in files:
            if re.match(pattern, file.name):
                return file
        return None

    def get_drivers_license_file(self, account_folder: str) -> Optional[FileMetadata]:
        """Get the driver's license file (*DL.jpeg) for an account."""
        files = self.get_account_files(account_folder)
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

    def extract_account_info(self, account_folder: str) -> Dict[str, str]:
        """Extract account information from the account info file."""
        try:
            # Get the account info file
            info_file = self.get_account_info_file(account_folder)
            if not info_file:
                logging.error(f"No account info file found for {account_folder}")
                return {}

            # Create a temporary directory for file processing
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download the file
                local_path = os.path.join(temp_dir, info_file.name)
                self.dbx.files_download_to_file(local_path, info_file.path_display)
                
                # Extract text from PDF
                text = self._extract_text_from_pdf(local_path)
                
                # Parse the extracted text
                account_info = {}
                
                # Extract Name
                name_match = re.search(r'Name:?\s*([^\n]+)', text, re.IGNORECASE)
                if name_match:
                    account_info['name'] = name_match.group(1).strip()
                
                # Extract Address
                address_match = re.search(r'Address:?\s*([^\n]+)', text, re.IGNORECASE)
                if address_match:
                    account_info['address'] = address_match.group(1).strip()
                
                # Extract Phone
                phone_match = re.search(r'Phone:?\s*([^\n]+)', text, re.IGNORECASE)
                if phone_match:
                    account_info['phone'] = phone_match.group(1).strip()
                
                # Extract Email
                email_match = re.search(r'Email:?\s*([^\n]+)', text, re.IGNORECASE)
                if email_match:
                    account_info['email'] = email_match.group(1).strip()
                
                return account_info

        except Exception as e:
            logging.error(f"Error extracting account info: {e}")
            return {}

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

def list_folder_contents(dbx, path):
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
            logger.info("Token loaded from .env file")
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
        entries = list_folder_contents(dbx, path)
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
        clean_path = clean_dropbox_path(path)
        if not clean_path:
            raise ValueError(f"Invalid path: {path}")
            
        # Get folder contents
        entries = list_folder_contents(dbx, clean_path)
        
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