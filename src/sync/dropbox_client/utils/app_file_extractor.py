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
from .ocr_utils import extract_name_with_ocr_with_conf, extract_text_with_trocr

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
    def __init__(self, dbx: dropbox.Dropbox, report_logger: Any = None):
        """Initialize the AppFileExtractor.
        
        Args:
            dbx: Dropbox client instance
            report_logger: Optional report logger instance for additional logging
        """
        self.dbx = dbx
        self.report_logger = report_logger
        self.name_parts = None
        self.timing_info = {}


    def extract_info(self, folder_path: str, extract_fields: set = None, name_parts: Dict[str, Any] = None, file_filter: str = None, skip_zero_length_if_account_info_exists: bool = False, report_logger: Any = None) -> Dict[str, Any]:
        """Extract information from application files in a Dropbox folder.
        
        Args:
            folder_path: The path to the Dropbox folder containing application files
            extract_fields: Optional set of fields to extract. If None, extracts all fields.
                           Valid fields: 'name', 'address', 'application_type', 'status', 'birthdate', 'gender'
            name_parts: Optional dictionary containing name parts for better name extraction
            file_filter: Optional pattern to filter files by name (e.g. "*Joint*")
            skip_zero_length_if_account_info_exists: If True, skip processing files with 0 extracted text when account info already exists
            report_logger: Optional report logger instance for additional logging
            
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
        self.skip_zero_length_if_account_info_exists = skip_zero_length_if_account_info_exists

        summary_data = {
            'total_app_files': 0,
            'processed_folders': set(),
            'files_with_birthdate': set(),
            'file_birthdates': {},
            'file_sexes': {},
            'file_info': {},
            'all_folder_app_files': {},
            'files_with_name': [],
            'skipped_zero_length_files': 0
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
                else:
                    # Check if this was a skipped zero-length file
                    if hasattr(self, 'skip_zero_length_if_account_info_exists') and self.skip_zero_length_if_account_info_exists:
                        summary_data['skipped_zero_length_files'] += 1

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
                'skipped_zero_length_files': summary_data['skipped_zero_length_files'],
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
                        log_dropbox_app_file_info(info, logger, self.report_logger, file.name)
                
                # Log skipped files info
                if summary_data['skipped_zero_length_files'] > 0:
                    logger.info(f"  ⏭️ Skipped {summary_data['skipped_zero_length_files']} zero-length files (account info already exists)")
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

            # Check for special case: force TrOCR for handwritten files
            force_trocr = False
            ocr_attempted = False
            try:
                with open('accounts/special_cases.json', 'r') as f:
                    special_cases = json.load(f)
                folder_name = file.path_display.split('/')[-2] if '/' in file.path_display else None
                for case in special_cases.get('special_cases', []):
                    if case.get('folder_name') == folder_name:
                        handwritten_files = case.get('handwritten_app_files', [])
                        matched_patterns = [pattern for pattern in handwritten_files if fnmatch.fnmatch(file.name, pattern)]
                        if matched_patterns:
                            force_trocr = True
                            logger.info(f"[SPECIAL CASE] Forcing TrOCR for handwritten file: {file.name} in folder: {folder_name} (matched patterns: {matched_patterns})")
                            break
            except Exception as e:
                logger.warning(f"Could not check special_cases.json for handwritten directive: {e}")

            # Initialize processor
            from sync.processors.lm_studio_processor import LMStudioProcessor
            processor = LMStudioProcessor(model_name="qwen2-vl-7b-instruct")
            
            # Extract text from PDF
            extracted_text = processor._extract_text_from_file(temp_path)
            ocr_owner_data = None
            ocr_avg_conf = None
            ocr_method = None
            special_case_applied = False
            
            # Check if we have zero-length extracted text
            if not extracted_text or len(extracted_text.strip()) == 0:
                logger.warning(f"No text could be extracted from file: {file.name}")
                
                # If we should skip zero-length files when account info exists, create file info with notes
                if hasattr(self, 'skip_zero_length_if_account_info_exists') and self.skip_zero_length_if_account_info_exists:
                    logger.info(f"Skipping zero-length file {file.name} - account info already exists from app files")
                    # Clean up temp file
                    os.unlink(temp_path)
                    
                    # Create file info object with notes explaining why it was skipped
                    file_info = {
                        'application_type': self._determine_application_type(file.name),
                        'status': 'Skipped',
                        'owner': {},
                        'jointOwner': {},
                        'notes': [
                            "File skipped due to zero-length text extraction",
                            "Account info already exists from other app files",
                            "No text could be extracted from any page"
                        ]
                    }
                    return file_info
                
                if force_trocr:
                    # Only run TrOCR
                    logger.info(f"[OCR] Running TrOCR only due to special_cases directive.")
                    special_case_applied = True
                    ocr_attempted = True
                    from pdf2image import convert_from_path
                    images = convert_from_path(temp_path, dpi=300)
                    images = images[:5]
                    logger.info(f"[TrOCR] Number of images/pages to process: {len(images)}")
                    trocr_texts = []
                    for i, image in enumerate(images):
                        text = extract_text_with_trocr(image)
                        logger.info(f"[TrOCR] Page {i+1} text: {text}")
                        trocr_texts.append(text)
                    import re
                    found_name = False
                    for page_num, text in enumerate(trocr_texts):
                        words = re.findall(r'\b[A-Z][a-z]+\b', text)
                        logger.info(f"[TrOCR] Page {page_num+1} candidate words: {words}")
                        if len(words) >= 2:
                            trocr_owner_data = {'first_name': words[0], 'last_name': words[1]}
                            logger.info(f"[TrOCR] Extracted owner data: {trocr_owner_data} from page {page_num+1}")
                            ocr_owner_data = trocr_owner_data
                            ocr_method = 'TrOCR'
                            found_name = True
                            break
                    if not found_name:
                        logger.warning(f"[TrOCR] No valid name found in any page for file: {file.name}")
                else:
                    # Hybrid: EasyOCR first, fallback to TrOCR if needed
                    logger.info(f"Trying EasyOCR extraction for name fields")
                    ocr_attempted = True
                    ocr_result = extract_name_with_ocr_with_conf(temp_path, name_parts=self.name_parts, file_name=file.name, logger=logger)
                    if ocr_result:
                        ocr_owner_data = ocr_result.get('owner_data')
                        ocr_avg_conf = ocr_result.get('avg_conf')
                        logger.info(f"[OCR] Extracted owner data (EasyOCR): {ocr_owner_data}")
                        if ocr_avg_conf is not None:
                            if ocr_avg_conf < 60 or not ocr_owner_data or not ocr_owner_data.get('first_name') or not ocr_owner_data.get('last_name'):
                                logger.info(f"[OCR] EasyOCR confidence low or no valid name found, trying TrOCR for handwritten text.")
                                ocr_attempted = True
                                images = convert_from_path(temp_path, dpi=300)
                                images = images[:5]
                                trocr_texts = []
                                for i, image in enumerate(images):
                                    text = extract_text_with_trocr(image)
                                    logger.info(f"[TrOCR] Page {i+1} text: {text}")
                                    trocr_texts.append(text)
                                import re
                                for page_num, text in enumerate(trocr_texts):
                                    words = re.findall(r'\b[A-Z][a-z]+\b', text)
                                    if len(words) >= 2:
                                        trocr_owner_data = {'first_name': words[0], 'last_name': words[1]}
                                        logger.info(f"[TrOCR] Extracted owner data: {trocr_owner_data} from page {page_num+1}")
                                        ocr_owner_data = trocr_owner_data
                                        ocr_method = 'TrOCR'
                                        break
                            else:
                                ocr_method = 'EasyOCR'
                        else:
                            ocr_method = 'EasyOCR'
                    else:
                        logger.warning(f"[OCR] No owner data could be extracted from file: {file.name}")
                        ocr_attempted = True
                        images = convert_from_path(temp_path, dpi=300)
                        images = images[:5]
                        trocr_texts = []
                        for i, image in enumerate(images):
                            text = extract_text_with_trocr(image)
                            logger.info(f"[TrOCR] Page {i+1} text: {text}")
                            trocr_texts.append(text)
                        import re
                        for page_num, text in enumerate(trocr_texts):
                            words = re.findall(r'\b[A-Z][a-z]+\b', text)
                            if len(words) >= 2:
                                trocr_owner_data = {'first_name': words[0], 'last_name': words[1]}
                                logger.info(f"[TrOCR] Extracted owner data: {trocr_owner_data} from page {page_num+1}")
                                ocr_owner_data = trocr_owner_data
                                ocr_method = 'TrOCR'
                                break
            
            logger.info(f"process extracted_text: {extracted_text}")
            processor_data = processor.process_text(extracted_text, file.name)
            logger.info(f"processor extraction results: {json.dumps(processor_data, indent=2)}")
            
            # Clean up temp file
            os.unlink(temp_path)

            if not processor_data and not ocr_owner_data:
                logger.warning("No data extracted from processor or OCR")
                
                # Create file info object with notes explaining why no data was extracted
                file_info = {
                    'application_type': self._determine_application_type(file.name),
                    'status': 'Failed',
                    'owner': {},
                    'jointOwner': {},
                    'notes': [
                        "No data could be extracted from file",
                        "Both processor and OCR extraction failed",
                        "File may be corrupted, password-protected, or contain no readable text"
                    ]
                }
                return file_info

            # Format the extracted data
            file_info = {
                'application_type': self._determine_application_type(file.name),
                'status': 'Processed',
                'owner': {},
                'jointOwner': {},
                'notes': []
            }
            logger.info(f"Initial file info: {json.dumps(file_info, indent=2)}")

            # Add owner (primary applicant) information
            if processor_data and processor_data.get('owner'):
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
            elif ocr_owner_data:
                # Use OCR result for owner name if processor_data is missing or empty
                file_info['owner'] = {
                    'firstName': ocr_owner_data.get('first_name'),
                    'lastName': ocr_owner_data.get('last_name'),
                    'dateOfBirth': None,
                    'gender': None,
                    'mailingAddressStreet': None,
                    'mailingAddressCity': None,
                    'mailingAddressState': None,
                    'mailingAddressZip': None,
                    'phoneNumber': None,
                    'emailAddress': None,
                    'ocrMethod': ocr_method
                }
                
                # Add note about OCR usage
                if ocr_method:
                    file_info['notes'].append(f"Used {ocr_method} for text extraction")
                    
                # Add note about handwritten detection
                if force_trocr:
                    file_info['notes'].append("Detected as handwritten file (forced TrOCR processing)")
                    if special_case_applied:
                        file_info['notes'].append("Special case processing applied (from special_cases.json)")
                elif ocr_method == 'TrOCR':
                    file_info['notes'].append("Detected as handwritten file (TrOCR used)")
                    
                # Add OCR confidence information if available
                if ocr_avg_conf is not None:
                    file_info['notes'].append(f"OCR confidence: {ocr_avg_conf:.1f}%")
                    if ocr_avg_conf < 60:
                        file_info['notes'].append("Low OCR confidence detected")

            # Add joint owner information if present
            if processor_data and processor_data.get('jointOwner'):
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
                
                # Add note about joint owner presence
                file_info['notes'].append("Joint owner information detected")

            # Validate name if we have name parts
            if self.name_parts and file_info['owner'].get('firstName') and file_info['owner'].get('lastName'):
                if not self._validate_name_against_parts(file_info['owner']['firstName'], file_info['owner']['lastName']):
                    logger.warning(f"Name validation failed for {file_info['owner']['firstName']} {file_info['owner']['lastName']}")
                    file_info['owner']['firstName'] = None
                    file_info['owner']['lastName'] = None
                    file_info['notes'].append("Name validation failed against expected name parts")
                else:
                    logger.info(f"Name validation passed for {file_info['owner']['firstName']} {file_info['owner']['lastName']}")
                    file_info['notes'].append("Name validation passed against expected name parts")

            # Add notes about data completeness
            if not processor_data and not ocr_owner_data:
                file_info['notes'].append("No data could be extracted from file")
            elif not processor_data and ocr_owner_data:
                file_info['notes'].append("Only OCR data available - no structured data extracted")
            elif processor_data and not processor_data.get('owner') and not processor_data.get('jointOwner'):
                file_info['notes'].append("Processor ran but no owner/joint owner data found")
            elif processor_data and (
                (processor_data.get('owner') and all([
                    processor_data['owner'].get('firstName'),
                    processor_data['owner'].get('lastName'),
                    processor_data['owner'].get('dateOfBirth'),
                    processor_data['owner'].get('gender')
                ])) or
                (processor_data.get('jointOwner') and all([
                    processor_data['jointOwner'].get('firstName'),
                    processor_data['jointOwner'].get('lastName'),
                    processor_data['jointOwner'].get('dateOfBirth'),
                    processor_data['jointOwner'].get('gender')
                ]))
            ):
                file_info['notes'].append("Successfully extracted structured data using Qwen2-VL processor")

            # Add note about application type detection
            app_type = file_info['application_type']
            if app_type != 'Unknown':
                file_info['notes'].append(f"Application type detected: {app_type}")

            if ocr_attempted and not any('OCR' in note for note in file_info['notes']):
                file_info['notes'].append("OCR extraction attempted but no valid name found")

            logger.info(f"Final extracted file info: {json.dumps(file_info, indent=2)}")
            return file_info

        except Exception as e:
            logger.error(f"Error processing file {file.name}: {str(e)}")
            
            # Create file info object with notes explaining the error
            file_info = {
                'application_type': self._determine_application_type(file.name),
                'status': 'Error',
                'owner': {},
                'jointOwner': {},
                'notes': [
                    f"Error processing file: {str(e)}",
                    "File processing failed due to an exception",
                    "Check file format and accessibility"
                ]
            }
            return file_info

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
                        log_dropbox_app_file_info(info, logger, self.report_logger, file.name)

            return app_file_info_summary

        except Exception as e:
            logger.error(f"Error extracting app files info: {str(e)}")
            return {}

    