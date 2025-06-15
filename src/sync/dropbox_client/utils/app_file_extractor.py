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
        """Process a single file and extract relevant information."""
        try:
            # Download file to temp location
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as temp_file:
                temp_path = temp_file.name
                self.dbx.files_download_to_file(temp_path, file.path_display)

            # Extract text from file
            text = self._extract_text_from_file(temp_path, file)
            if not text:
                return None

            # Extract name
            name_info = self._extract_name(text)
            if not name_info:
                # Try OCR as fallback
                name_info = self._extract_name_with_ocr(temp_path, file)

            # Clean up temp file
            os.unlink(temp_path)

            # Format the name for display
            display_name = None
            if name_info:
                display_name = f"{name_info['first_name']} {name_info['last_name']}"
                logger.info(f"Extracted name: {display_name}")

            # Return file info with extracted information
            return {
                'name': display_name,
                'application_type': self._determine_application_type(file.name),
                'status': 'Processed' if name_info else 'Failed to extract name'
            }

        except Exception as e:
            logger.error(f"Error processing file {file.name}: {str(e)}")
            return None

    def _extract_text_from_file(self, file_path: str, file: FileMetadata) -> Optional[str]:
        """Extract text from a PDF or text file."""
        try:
            if file.name.lower().endswith('.pdf'):
                with open(file_path, 'rb') as pdf_file:
                    reader = PyPDF2.PdfReader(pdf_file)
                    content = ''
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            content += page_text + '\n'
            else:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            return content
        except Exception as e:
            logger.error(f"Error extracting text from {file.name}: {str(e)}")
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

    def _extract_name(self, content: str) -> Optional[Dict[str, str]]:
        """Extract name information from file content."""
        lines = content.splitlines()
        found_name = False
        is_joint_file = 'joint' in content.lower()

        # If we have name_parts, use them to validate extracted names
        if self.name_parts:
            expected_first_name = self.name_parts.get('first_name', '').lower()
            expected_last_name = self.name_parts.get('last_name', '').lower()
            logger.info(f"Using name parts for validation - First: {expected_first_name}, Last: {expected_last_name}")

        # Look for OWNER and JOINT OWNER sections
        owner_section = False
        joint_owner_section = False
        current_section = None
        owner_name = None
        joint_owner_name = None

        for i, line in enumerate(lines):
            line = line.strip()
            
            # Check for section headers - be more precise
            if re.search(r'^\s*1\.\s*OWNER\s*\(Owner is the Annuitant unless otherwise noted\)', line, re.IGNORECASE):
                owner_section = True
                joint_owner_section = False
                current_section = 'owner'
                logger.info("Found OWNER section")
                continue
            elif re.search(r'^\s*2\.\s*JOINT\s+OWNER\s+INFORMATION\s*\(Must be legal spouse', line, re.IGNORECASE):
                owner_section = False
                joint_owner_section = True
                current_section = 'joint_owner'
                logger.info("Found JOINT OWNER section")
                continue

            # Look for name markers within sections - be more specific
            if (owner_section or joint_owner_section):
                # Look for specific name patterns
                name_patterns = [
                    r'^\s*Name\s*:\s*First\s+MI\s+Last\s*$',  # "Name: First MI Last"
                ]
                
                if any(re.match(pattern, line, re.IGNORECASE) for pattern in name_patterns):
                    # Look at next line for the actual name
                    if i + 1 < len(lines):
                        name_line = lines[i + 1].strip()
                        logger.info(f"Found name line in {current_section} section: {name_line}")
                        
                        # Skip if the next line looks like a header or label
                        if any(skip in name_line.lower() for skip in ['address', 'city', 'state', 'zip', 'phone', 'email', 'website']):
                            continue
                            
                        # Extract name parts
                        name_parts = name_line.split()
                        if len(name_parts) >= 2:
                            first_name = name_parts[0]
                            last_name = name_parts[-1]
                            middle_initial = name_parts[1] if len(name_parts) > 2 and len(name_parts[1]) == 1 else None
                            
                            # Validate name against expected parts
                            if self._validate_name_against_parts(first_name, last_name):
                                # Store name based on section
                                name_dict = {
                                    'first_name': first_name,
                                    'last_name': last_name
                                }
                                if middle_initial:
                                    name_dict['middle_initial'] = middle_initial

                                if current_section == 'owner':
                                    owner_name = name_dict
                                elif current_section == 'joint_owner':
                                    joint_owner_name = name_dict
                                    
                                found_name = True

        # If name not found and OCR is available, try OCR
        if not found_name and OCR_AVAILABLE:
            ocr_result = self._extract_name_with_ocr(content, None)
            if ocr_result:
                # Validate OCR result
                if self._validate_name_against_parts(ocr_result['first_name'], ocr_result['last_name']):
                    if not owner_name:
                        owner_name = ocr_result
                    elif not joint_owner_name and is_joint_file:
                        joint_owner_name = ocr_result

        # Return appropriate name info based on what was found
        if is_joint_file and owner_name and joint_owner_name:
            return {
                'owner': owner_name,
                'joint_owner': joint_owner_name
            }
        elif owner_name:
            return owner_name
        elif joint_owner_name:
            return joint_owner_name

        return None

    def _extract_name_with_ocr(self, content: str, file: FileMetadata) -> Optional[Dict[str, str]]:
        """Extract name information from file content using OCR."""
        try:
            # Convert PDF to images with higher DPI and larger size for better text recognition
            images = convert_from_path(
                content,
                dpi=600,  # Increased DPI for better quality
                size=(2000, None)  # Wider width to capture longer lines
            )
            ocr_lines = []
            for image in images:
                text = pytesseract.image_to_string(image)
                ocr_lines.extend(text.splitlines())

            # 1. Look for 'Full Name' marker and extract the next non-empty line
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

            # 2. Fallback: Any line containing the last name and at least two words
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

            # 3. Try previous patterns
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

            # 4. Fallback: two consecutive capitalized words
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
            logger.error(f"Error during OCR name extraction: {str(e)}")
            return None

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