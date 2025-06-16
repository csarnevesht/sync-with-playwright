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

logger = logging.getLogger(__name__)

# Check if OCR is available
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

class AppFileExtractor:
    def __init__(self, dbx: dropbox.Dropbox):
        self.dbx = dbx
        self.name_parts = None

    def extract_info(self, folder_path: str, extract_fields: set = None, name_parts: Dict[str, Any] = None, file_filter: str = None) -> Dict[str, Any]:
        """Extract information from application files in a Dropbox folder.
        
        Args:
            folder_path: The path to the Dropbox folder containing application files
            extract_fields: Optional set of fields to extract. If None, extracts all fields.
                           Valid fields: 'name', 'address', 'application_type', 'status', 'birthdate', 'gender'
            name_parts: Optional dictionary containing name parts for better name extraction
            file_filter: Optional pattern to filter files by name (e.g. "*Life*")
            
        Returns:
            Dict containing extracted information
        """
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
                if self._is_application_file(file.name):
                    # Apply file filter if specified
                    if file_filter:
                        if not fnmatch.fnmatch(file.name, file_filter):
                            continue
                            
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
            return summary_data

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
        """Process a single file and extract relevant information using OCR and Ollama's Mistral model."""
        try:
            logger.info(f"Processing file: {file.name}")
            # Download file to temp location
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as temp_file:
                temp_path = temp_file.name
                self.dbx.files_download_to_file(temp_path, file.path_display)

            from sync.processors.ollama_processor import OllamaProcessor
            ollama_processor = OllamaProcessor()
            
            # Then process with Ollama
            logger.info("Processing with Ollama")
            ollama_data = ollama_processor._process_file(Path(temp_path))
            logger.info(f"Ollama extraction results: {json.dumps(ollama_data, indent=2)}")
            
            # Clean up temp file
            os.unlink(temp_path)

            if not ocr_data and not ollama_data:
                logger.warning("No data extracted from either OCR or Ollama")
                return None

            # Format the extracted data
            file_info = {
                'application_type': self._determine_application_type(file.name),
                'status': 'Processed'
            }
            logger.info(f"Initial file info: {json.dumps(file_info, indent=2)}")

            # Merge OCR and Ollama results, preferring Ollama for high confidence matches
            if ollama_data and 'personalInfo' in ollama_data:
                personal_info = ollama_data['personalInfo']
                if 'name' in personal_info:
                    name_info = personal_info['name']
                    if name_info['confidence'] >= 0.7:  # Only use high confidence matches
                        logger.info(f"Using Ollama name with confidence {name_info['confidence']}: {name_info['value']}")
                        file_info['name'] = name_info['value']
                        file_info['name_confidence'] = name_info['confidence']
                    elif 'name' in ocr_data:  # Fall back to OCR if Ollama confidence is low
                        logger.info(f"Falling back to OCR name: {ocr_data['name']}")
                        file_info['name'] = ocr_data['name']
                        file_info['name_confidence'] = 0.5  # OCR confidence is lower

            # Extract address information
            if ollama_data and 'address' in ollama_data:
                address_parts = []
                for field, info in ollama_data['address'].items():
                    if info['confidence'] >= 0.7:  # Only use high confidence matches
                        logger.info(f"Using Ollama address part with confidence {info['confidence']}: {info['value']}")
                        address_parts.append(info['value'])
                if address_parts:
                    file_info['address'] = ' '.join(address_parts)
                    logger.info(f"Final address from Ollama: {file_info['address']}")
                elif 'address' in ocr_data:  # Fall back to OCR if Ollama confidence is low
                    logger.info(f"Falling back to OCR address: {ocr_data['address']}")
                    file_info['address'] = ocr_data['address']

            # Extract application information
            if ollama_data and 'applicationInfo' in ollama_data:
                for field, info in ollama_data['applicationInfo'].items():
                    if info['confidence'] >= 0.7:  # Only use high confidence matches
                        logger.info(f"Using Ollama application info for {field} with confidence {info['confidence']}: {info['value']}")
                        file_info[field] = info['value']

            # Add any additional fields from OCR that weren't found by Ollama
            for field in ['date_of_birth', 'phone', 'email']:
                if field in ocr_data and field not in file_info:
                    logger.info(f"Adding OCR field {field}: {ocr_data[field]}")
                    file_info[field] = ocr_data[field]

            # Validate name if we have name parts
            if self.name_parts and 'name' in file_info:
                name_parts = file_info['name'].split()
                if len(name_parts) >= 2:
                    first_name = name_parts[0]
                    last_name = name_parts[-1]
                    if not self._validate_name_against_parts(first_name, last_name):
                        logger.warning(f"Name validation failed for {first_name} {last_name}")
                        file_info['name'] = None
                        file_info['name_confidence'] = 0.0
                    else:
                        logger.info(f"Name validation passed for {first_name} {last_name}")

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