import re
import logging
import tempfile
import PyPDF2
from typing import Dict, Any, Set, List, Optional
from dropbox.files import FileMetadata
import dropbox
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import os
import fnmatch
import mimetypes
from pathlib import Path
import json
from .logging_utils import log_dropbox_app_file_info
import time
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Check if OCR is available
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

class SetEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles sets by converting them to lists."""
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return super().default(obj)

class AppFileExtractor:
    def __init__(self, dbx: dropbox.Dropbox):
        self.dbx = dbx
        self.name_parts = None
        self.timing_info = {}

    def _log_dropbox_app_file_info(self, info: Dict[str, Any], logger_instance: Any = None) -> None:
        """Log detailed information about a file.
        
        Args:
            info: Dictionary containing file information
            logger_instance: Optional logger instance to use (defaults to module logger)
        """
        log_dropbox_app_file_info(info, logger_instance)

    def extract_info(self, folder_path: str, extract_fields: set = None, name_parts: Dict[str, Any] = None, file_filter: str = None) -> Dict[str, Any]:
        """Extract information from application files in a Dropbox folder.
        
        Args:
            folder_path: The path to the Dropbox folder containing application files
            extract_fields: Optional set of fields to extract. If None, extracts all fields.
                           Valid fields: 'name', 'address', 'application_type', 'status', 'birthdate', 'gender'
            name_parts: Optional dictionary containing name parts for better name extraction
            file_filter: Optional pattern to filter files by name (e.g. "*Joint*")
            
        Returns:
            Dict containing extracted information
        """
        start_time = time.time()
        self.timing_info = {
            'start_time': datetime.now().isoformat(),
            'operations': {}
        }

        if extract_fields is None:
            extract_fields = {'name', 'address', 'application_type', 'status'}
        
        self.name_parts = name_parts

        summary_data = {
            'total_app_files': 0,
            'processed_folders': set(),
            'files_with_birthdate': set(),
            'file_birthdates': {},
            'file_sexes': {},
            'file_info': {},
            'all_folder_app_files': {},
            'files_with_name': []
        }

        app_files = []
        try:
            # List folder contents
            folder_contents = self._list_folder_contents(folder_path)
            if not folder_contents:
                return summary_data

            # Process each file
            for file in folder_contents:
                if not isinstance(file, FileMetadata):
                    continue
                    
                # First check if it's an application file
                if not self._is_application_file(file.name):
                    continue
                    
                # Then apply file filter if specified
                if file_filter:
                    if not fnmatch.fnmatch(file.name.lower(), file_filter.lower()):
                        logger.debug(f"Skipping file {file.name} - does not match filter pattern {file_filter}")
                        continue
                    logger.info(f"Processing file {file.name} - matches filter pattern {file_filter}")
                            
                summary_data['total_app_files'] += 1
                app_files.append(file)
                file_info = self._process_file(file)
                if file_info:
                    # Store file info in the summary data
                    summary_data['file_info'][file.path_display] = file_info
                    if file_info.get('name'):
                        summary_data['files_with_name'].append(file.path_display)

            summary_data['all_folder_app_files'][folder_path] = app_files
            summary_data['processed_folders'].add(folder_path)

            # Convert sets to lists before JSON serialization
            app_file_info_summary = {
                'total_app_files': summary_data['total_app_files'],
                'processed_folders': list(summary_data['processed_folders']),
                'files_with_birthdate': list(summary_data['files_with_birthdate']),
                'file_birthdates': summary_data['file_birthdates'],
                'file_sexes': summary_data['file_sexes'],
                'file_info': summary_data['file_info'],
                'all_folder_app_files': summary_data['all_folder_app_files'],
                'files_with_name': summary_data['files_with_name'],
                'timing_info': self.timing_info
            }

            # Log timing information
            total_time = time.time() - start_time
            self.timing_info['total_time'] = total_time
            logger.info(f"\nTiming Information:")
            logger.info(f"Total processing time: {total_time:.2f} seconds")
            for operation, duration in self.timing_info['operations'].items():
                logger.info(f"{operation}: {duration:.2f} seconds")

            # Log the summary for this folder
            folder_app_files = summary_data['all_folder_app_files'].get(folder_path, [])
            if folder_app_files:
                logger.info(f"\nFound {len(folder_app_files)} files matching filter '{file_filter}' in {folder_path}:")
                for file in folder_app_files:
                    logger.info(f"  ✅ {file.name}")
                    # Log any additional information found in the file
                    if file.path_display in summary_data.get('file_info', {}):
                        info = summary_data['file_info'][file.path_display]
                        self._log_dropbox_app_file_info(info)
            else:
                if file_filter:
                    logger.info(f"  ❌ No application files found matching filter '{file_filter}' for {folder_path}")
                else:
                    logger.info(f"  ❌ No application files found for {folder_path}")

            return app_file_info_summary

        except Exception as e:
            logger.error(f"Error extracting app files info: {str(e)}")
            return summary_data

    def _list_folder_contents(self, path: str) -> List[FileMetadata]:
        """List contents of a Dropbox folder."""
        try:
            result = self.dbx.files_list_folder(path)
            return result.entries
        except Exception as e:
            logger.error(f"Error listing folder contents: {str(e)}")
            return []

    def _process_file(self, file: FileMetadata) -> Optional[Dict[str, Any]]:
        """Process a single file and extract relevant information using OCR and Qwen model."""
        try:
            logger.info(f"Processing file: {file.name}")
            # Download file to temp location
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as temp_file:
                temp_path = temp_file.name
                self.dbx.files_download_to_file(temp_path, file.path_display)

            # Initialize processor
            from sync.processors.lm_studio_processor import LMStudioProcessor
            processor = LMStudioProcessor(model_name="qwen2-vl-7b-instruct")
            
            # Extract text from PDF
            extracted_text = processor._extract_text_from_file(temp_path)
            if not extracted_text or len(extracted_text.strip()) == 0:
                logger.warning(f"No text could be extracted from file: {file.name}")
            
                
            processor_data = processor.process_text(extracted_text, file.name)
            logger.info(f"processor extraction results: {json.dumps(processor_data, indent=2)}")
            
            # Clean up temp file
            os.unlink(temp_path)

            if not processor_data:
                logger.warning("No data extracted from processor")
                return None

            # Format the extracted data
            file_info = {
                'application_type': self._determine_application_type(file.name),
                'status': 'Processed',
                'owner': {},
                'jointOwner': {}
            }
            logger.info(f"Initial file info: {json.dumps(file_info, indent=2)}")

            # Add owner (primary applicant) information
            if processor_data.get('owner'):
                owner_data = processor_data['owner']
                file_info['owner'] = {
                    'firstName': owner_data.get('firstName'),
                    'lastName': owner_data.get('lastName'),
                    'dateOfBirth': owner_data.get('dateOfBirth'),
                    'gender': owner_data.get('gender'),
                    'mailingAddressStreet': owner_data.get('mailingAddressStreet'),
                    'mailingAddressCity': owner_data.get('mailingAddressCity'),
                    'mailingAddressState': owner_data.get('mailingAddressState'),
                    'mailingAddressZip': owner_data.get('mailingAddressZip'),
                    'phoneNumber': owner_data.get('phoneNumber'),
                    'emailAddress': owner_data.get('emailAddress')
                }

            # Add joint owner information if present
            if processor_data.get('jointOwner'):
                joint_owner_data = processor_data['jointOwner']
                file_info['jointOwner'] = {
                    'firstName': joint_owner_data.get('firstName'),
                    'lastName': joint_owner_data.get('lastName'),
                    'dateOfBirth': joint_owner_data.get('dateOfBirth'),
                    'gender': joint_owner_data.get('gender'),
                    'mailingAddressStreet': joint_owner_data.get('mailingAddressStreet'),
                    'mailingAddressCity': joint_owner_data.get('mailingAddressCity'),
                    'mailingAddressState': joint_owner_data.get('mailingAddressState'),
                    'mailingAddressZip': joint_owner_data.get('mailingAddressZip'),
                    'phoneNumber': joint_owner_data.get('phoneNumber'),
                    'emailAddress': joint_owner_data.get('emailAddress')
                }

            # Validate name if we have name parts
            if self.name_parts and file_info['owner'].get('firstName') and file_info['owner'].get('lastName'):
                if not self._validate_name_against_parts(file_info['owner']['firstName'], file_info['owner']['lastName']):
                    logger.warning(f"Name validation failed for {file_info['owner']['firstName']} {file_info['owner']['lastName']}")
                    file_info['owner']['firstName'] = None
                    file_info['owner']['lastName'] = None
                else:
                    logger.info(f"Name validation passed for {file_info['owner']['firstName']} {file_info['owner']['lastName']}")

            logger.info(f"Final extracted file info: {json.dumps(file_info, indent=2)}")
            return file_info

        except Exception as e:
            logger.error(f"Error processing file {file.name}: {str(e)}")
            return None

    def _validate_name_against_parts(self, first_name: str, last_name: str) -> bool:
        """Validate extracted name against expected name parts.
        
        Args:
            first_name: Extracted first name
            last_name: Extracted last name
            
        Returns:
            bool: True if name matches expected parts, False otherwise
        """
        if not self.name_parts:
            return True
            
        expected_first_name = self.name_parts.get('first_name', '').lower()
        expected_last_name = self.name_parts.get('last_name', '').lower()
        
        extracted_first = first_name.lower()
        extracted_last = last_name.lower()
        
        # Match if either first or last name matches
        matches = (extracted_first == expected_first_name or 
                  extracted_last == expected_last_name)
                  
        if matches:
            logger.info(f"Found matching name: {first_name} {last_name}")
            
        return matches

    def _determine_application_type(self, filename: str) -> str:
        """Determine the type of application based on filename."""
        filename_lower = filename.lower()
        if 'life' in filename_lower:
            return 'Life Insurance'
        elif 'annuity' in filename_lower:
            return 'Annuity'
        elif 'equitrust' in filename_lower:
            return 'EquiTrust Annuity'
        elif 'security benefit' in filename_lower:
            return 'Security Benefit'
        else:
            return 'Unknown'

    def _is_application_file(self, filename: str) -> bool:
        """Check if a file is an application file based on its name."""
        return 'App' in filename or 'Application' in filename

    def _extract_name_from_line(self, line: str, lines: List[str], line_index: int) -> Optional[Dict[str, str]]:
        """Extract name from a line and its surrounding context."""
        # Try to extract name directly from the current line
        name_match = re.search(r'Name\s*:\s*(.+)', line, re.IGNORECASE)
        if name_match:
            name = name_match.group(1).strip()
            name_parts = re.split(r'\s+', name)
            if len(name_parts) >= 2:
                return {
                    'first_name': name_parts[0],
                    'last_name': name_parts[-1]
                }

        # Look at next few lines for name
        for offset in range(1, 10):
            idx = line_index + offset
            if idx < len(lines):
                candidate = lines[idx].strip()
                if self._is_valid_name_candidate(candidate):
                    name_parts = re.split(r'\s+', candidate)
                    return {
                        'first_name': name_parts[0],
                        'last_name': name_parts[-1]
                    }

        return None

    def _is_valid_name_candidate(self, text: str) -> bool:
        """Check if a text line is likely to contain a valid name."""
        if not text:
            return False

        # Skip if contains common non-name patterns
        non_name_patterns = [
            r'\d',  # Contains numbers
            r'[()]',  # Contains parentheses
            r'[#@]',  # Contains special characters
            r'box',  # Contains "box"
            r'address',  # Contains "address"
            r'city',  # Contains "city"
            r'state',  # Contains "state"
            r'zip',  # Contains "zip"
        ]
        if any(re.search(pattern, text.lower()) for pattern in non_name_patterns):
            return False

        # Check if line looks like a real name
        words = re.split(r'\s+', text)
        if len(words) < 2:
            return False

        # Skip if any word is a label
        labels = {'first', 'last', 'mi', 'address', 'city', 'state', 'zip', 'mailing', 
                 'phone', 'number', 'dob', 'date', 'ssn', 'email', 'residence', 'cannot', 
                 'box', 'different', 'than'}
        if any(word.lower() in labels for word in words):
            return False

        # Check if at least one word starts with capital letter
        return any(word[0].isupper() for word in words) 
    
    def _extract_name_with_ocr(self, content: str, file: FileMetadata) -> Optional[Dict[str, str]]:
        """Extract name information from file content using OCR."""
        try:
            # Check if the file is a valid PDF before attempting OCR
            mime_type, _ = mimetypes.guess_type(content)
            logger.info(f"[OCR] File path: {content}, Detected MIME type: {mime_type}")
            if not (mime_type and mime_type.lower() == 'application/pdf'):
                logger.error(f"[OCR] File is not a valid PDF: BEGIN CONTENT {content} END CONTENT. Skipping OCR extraction.")
                return None

            # Convert PDF to images with higher DPI and larger size for better text recognition
            try:
                images = convert_from_path(
                    content,
                    dpi=600,  # Increased DPI for better quality
                    size=(2000, None)  # Wider width to capture longer lines
                )
            except Exception as pdf_exc:
                logger.error(f"[OCR] Failed to convert PDF to images: {pdf_exc}")
                return None

            ocr_lines = []
            for image in images:
                text = pytesseract.image_to_string(image)
                ocr_lines.extend(text.splitlines())

            # First strategy: Look for OWNER section, then 'Name: First MI Last' header, then extract the next line(s) as the name
            for i, line in enumerate(ocr_lines):
                logger.debug(f"[OWNER] Checking line {i}: '{line}'")
                if 'OWNER' in line.upper():
                    # Look for the table header in the next few lines
                    for j in range(i+1, min(i+6, len(ocr_lines))):
                        header = ocr_lines[j]
                        if 'Name:' in header and 'First' in header and 'Last' in header:
                            # The next line(s) should be the actual name row
                            if j+1 < len(ocr_lines):
                                name_row = ocr_lines[j+1].strip()
                                name_parts = name_row.split()
                                # If only one word, check the next line for the last name
                                if len(name_parts) == 1 and (j+2) < len(ocr_lines):
                                    next_row = ocr_lines[j+2].strip()
                                    next_parts = next_row.split()
                                    if len(next_parts) == 1:
                                        result = {
                                            'first_name': name_parts[0],
                                            'last_name': next_parts[0]
                                        }
                                        logger.info(f"[OWNER TABLE] Extracted split name: {result}")
                                        return result
                                elif len(name_parts) >= 2:
                                    result = {
                                        'first_name': name_parts[0],
                                        'last_name': name_parts[-1]
                                    }
                                    if len(name_parts) == 3:
                                        result['middle_initial'] = name_parts[1]
                                    logger.info(f"[OWNER TABLE] Extracted name: {result}")
                                    return result

            # 2. Look for 'Full Name' marker and extract the next non-empty line
            for i, line in enumerate(ocr_lines):
                logger.debug(f"[Full Name] Checking line {i}: '{line}'")
                if 'Full Name' in line:
                    # Look for the next non-empty line
                    for j in range(i+1, min(i+5, len(ocr_lines))):
                        candidate = ocr_lines[j].strip()
                        logger.debug(f"[Full Name] Candidate after marker: '{candidate}'")
                        if candidate and len(candidate.split()) >= 2:
                            name_parts = candidate.split()
                            if self.name_parts and any(part.lower() in self.name_parts.get('last_name', '').lower() for part in name_parts):
                                logger.info(f"[Full Name] Found name after marker: {candidate}")
                                # Find the index of the part containing the last name
                                last_name_index = next(i for i, part in enumerate(name_parts) 
                                                        if part.lower() in self.name_parts.get('last_name', '').lower())
                                # Use all parts up to and including the last name as the last name
                                last_name = ' '.join(name_parts[last_name_index:])
                                first_name = ' '.join(name_parts[:last_name_index])
                                return {
                                    'first_name': first_name,
                                    'last_name': last_name
                                }

            # 3. Fallback: Any line containing the last name and at least two words
            for i, line in enumerate(ocr_lines):
                logger.debug(f"[Last Name Fallback] Checking line {i}: '{line}'")
                if self.name_parts and self.name_parts.get('last_name', '').lower() in line.lower():
                    words = line.strip().split()
                    if len(words) >= 2:
                        logger.info(f"[Last Name Fallback] Found line with last name: {line}")
                        return {
                            'first_name': words[0],
                            'last_name': words[-1]
                        }

            # 4. Try previous patterns
            name_patterns = [
                r'Name\s*:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
                r'Applicant\s*:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
                r'Insured\s*:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
                r'Policyholder\s*:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
                r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s*$',
                r'^([A-Z][a-z]+\s+[A-Z][a-z]+)\s*',
            ]
            for line in ocr_lines:
                logger.debug(f"[Pattern] Checking line for name: '{line}'")
                for pattern in name_patterns:
                    match = re.search(pattern, line)
                    if match:
                        name = match.group(1).strip()
                        logger.info(f"[Pattern] Found potential name match: '{name}'")
                        name_parts = re.split(r'\s+', name)
                        if len(name_parts) >= 2:
                            if self.name_parts and any(part.lower() in self.name_parts.get('last_name', '').lower() for part in name_parts):
                                logger.info(f"[Pattern] Found name with matching last name: {name}")
                                return {
                                    'first_name': name_parts[0],
                                    'last_name': name_parts[-1]
                                }
                            elif all(word[0].isupper() for word in name_parts):
                                logger.info(f"[Pattern] Found name without matching last name: {name}")
                                return {
                                    'first_name': name_parts[0],
                                    'last_name': name_parts[-1]
                                }

            # 5. Fallback: two consecutive capitalized words
            for line in ocr_lines:
                words = re.split(r'\s+', line.strip())
                if len(words) >= 2:
                    for i in range(len(words) - 1):
                        if (words[i][0].isupper() and words[i+1][0].isupper() and
                            len(words[i]) > 1 and len(words[i+1]) > 1):
                            potential_name = f"{words[i]} {words[i+1]}"
                            logger.info(f"[CapWords] Found potential name from capitalized words: '{potential_name}'")
                            if self.name_parts and any(word.lower() in self.name_parts.get('last_name', '').lower() for word in words):
                                logger.info(f"[CapWords] Found name with matching last name: {potential_name}")
                                return {
                                    'first_name': words[i],
                                    'last_name': words[i+1]
                                }

            return None
        except Exception as e:
            import traceback
            logger.error(f"Error during OCR name extraction: {str(e)}\n{traceback.format_exc()}")
            return None

    def _extract_dropbox_account_app_files_info(self, account_name: str, file_filter: str = None) -> Dict[str, Any]:
        """Extract information from application files in a Dropbox account folder."""
        try:
            # Get the account folder path
            account_folder = self._get_account_folder(account_name)
            if not account_folder:
                logger.error(f"Account folder not found for {account_name}")
                return {}

            # Extract information from the account folder
            app_file_info = self.extract_info(account_folder, file_filter=file_filter)
            if not app_file_info:
                logger.error(f"No application files found for {account_name}")
                return {}

            # Convert sets to lists for JSON serialization
            app_file_info_summary = {
                'total_app_files': app_file_info['total_app_files'],
                'processed_folders': list(app_file_info['processed_folders']),
                'files_with_birthdate': list(app_file_info['files_with_birthdate']),
                'file_birthdates': app_file_info['file_birthdates'],
                'file_sexes': app_file_info['file_sexes'],
                'file_info': app_file_info['file_info'],
                'all_folder_app_files': app_file_info['all_folder_app_files'],
                'files_with_name': app_file_info['files_with_name']
            }

            # Log the summary
            logger.info(f"\nSummary for {account_name}:")
            logger.info(f"Total application files: {app_file_info_summary['total_app_files']}")
            logger.info(f"Processed folders: {len(app_file_info_summary['processed_folders'])}")
            logger.info(f"Files with birthdate: {len(app_file_info_summary['files_with_birthdate'])}")
            logger.info(f"Files with name: {len(app_file_info_summary['files_with_name'])}")

            # Log details for each file
            for folder_path, files in app_file_info_summary['all_folder_app_files'].items():
                logger.info(f"\nFolder: {folder_path}")
                for file in files:
                    logger.info(f"  ✅ {file.name}")
                    if file.path_display in app_file_info_summary['file_info']:
                        info = app_file_info_summary['file_info'][file.path_display]
                        self._log_dropbox_app_file_info(info)

            return app_file_info_summary

        except Exception as e:
            logger.error(f"Error extracting app files info: {str(e)}")
            return {}

    