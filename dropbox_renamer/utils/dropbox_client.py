import dropbox
from dropbox.files import FileMetadata
from typing import List, Tuple, Optional, Dict
import os
from datetime import datetime
import re
import pdf2image
import pytesseract
from PIL import Image
import tempfile
import PyPDF2
import logging
import urllib.parse

from .config import DROPBOX_ROOT_FOLDER, ACCOUNT_INFO_PATTERN, DRIVERS_LICENSE_PATTERN
from .path_utils import clean_dropbox_path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dropbox_sync.log'),
        logging.StreamHandler()
    ]
)

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

    def download_file(self, file_path: str, local_path: str) -> str:
        """Download a file from Dropbox and rename it with its modification date."""
        try:
            # Get file metadata
            metadata = self.dbx.files_get_metadata(file_path)
            mod_time = datetime.fromtimestamp(metadata.server_modified.timestamp())
            date_prefix = mod_time.strftime('%Y%m%d')
            
            # Create new filename with date prefix
            filename = os.path.basename(file_path)
            new_filename = f"{date_prefix} {filename}"
            new_path = os.path.join(local_path, new_filename)
            
            # Download the file
            self.dbx.files_download_to_file(new_path, file_path)
            return new_path
        except Exception as e:
            print(f"Error downloading file {file_path}: {e}")
            return ""

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

            # Download the file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_path = temp_file.name
                self.dbx.files_download_to_file(temp_path, info_file.path_display)

            # Extract text from the PDF
            text = self._extract_text_from_pdf(temp_path)
            
            # Clean up the temporary file
            os.unlink(temp_path)

            # Parse the extracted text
            account_info = {}
            
            # Extract Account Number
            account_match = re.search(r'Account\s*#?:?\s*([A-Z0-9-]+)', text, re.IGNORECASE)
            if account_match:
                account_info['account_number'] = account_match.group(1)
            
            # Extract Name
            name_match = re.search(r'Name:?\s*([A-Za-z\s]+)', text, re.IGNORECASE)
            if name_match:
                account_info['name'] = name_match.group(1).strip()
            
            # Extract Address
            address_match = re.search(r'Address:?\s*([A-Za-z0-9\s,.-]+)', text, re.IGNORECASE)
            if address_match:
                account_info['address'] = address_match.group(1).strip()
            
            # Extract Phone
            phone_match = re.search(r'Phone:?\s*(\d{3}[-.]?\d{3}[-.]?\d{4})', text, re.IGNORECASE)
            if phone_match:
                account_info['phone'] = phone_match.group(1)
            
            # Extract Email
            email_match = re.search(r'Email:?\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})', text, re.IGNORECASE)
            if email_match:
                account_info['email'] = email_match.group(1)
            
            return account_info

        except Exception as e:
            logging.error(f"Error extracting account info: {e}")
            return {} 