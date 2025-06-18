import json
import logging
import time
from typing import Dict, Any, Optional, List, Tuple, Set
import requests
from pathlib import Path
import sys
from datetime import datetime, timedelta
import pdfplumber
import re
import os
import glob
import hashlib
from abc import ABC, abstractmethod
from .prompt_creator import PromptCreator

class SetEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles sets by converting them to lists."""
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return super().default(obj)

class BaseProcessor(ABC):
    def __init__(self, model_name: str, base_url: str = None):
        """Initialize the base processor."""
        self.model_name = model_name
        self.base_url = base_url
        self.max_chunk_size = 2000
        self.max_retries = 5
        self.retry_delay = 1
        self.base_timeout = 180
        self.server_check_timeout = 10
        self.cache_duration = timedelta(hours=24)
        
        # Common logging setup
        self._setup_logging()
        self._initialize_cache()
        self.prompt_creator = PromptCreator()

    def _setup_logging(self):
        """Common logging setup for all processors."""
        # Configure logging for PDF-related libraries
        for logger_name in ['pdfplumber', 'PIL', 'pdfminer', 'pdfminer.pdfparser', 
                          'pdfminer.pdfdocument', 'pdfminer.pdfpage', 
                          'pdfminer.pdfinterp', 'pdfminer.converter', 'pdfminer.cmapdb']:
            logging.getLogger(logger_name).setLevel(logging.WARNING)

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.hasHandlers():
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _initialize_cache(self):
        """Common cache initialization."""
        self.response_cache = {}
        self.cache_timestamps = {}

    def _get_cache_key(self, prompt: str) -> str:
        """Common cache key generation."""
        return hashlib.md5(prompt.encode()).hexdigest()

    def _get_cached_response(self, prompt: str) -> Optional[Dict]:
        """Common cached response retrieval."""
        cache_key = self._get_cache_key(prompt)
        if cache_key in self.response_cache:
            timestamp = self.cache_timestamps.get(cache_key)
            if timestamp and datetime.now() - timestamp < self.cache_duration:
                self.logger.debug("Using cached response")
                return self.response_cache[cache_key]
        return None

    def _cache_response(self, prompt: str, response: Dict):
        """Common response caching."""
        cache_key = self._get_cache_key(prompt)
        self.response_cache[cache_key] = response
        self.cache_timestamps[cache_key] = datetime.now()

    def _extract_text_from_file(self, file_path: str) -> str:
        """Common text extraction from PDF files."""
        try:
            self.logger.info(f"Starting text extraction from file: {file_path}")
            if not file_path.lower().endswith('.pdf'):
                self.logger.warning(f"File is not a PDF: {file_path}")
                return ""

            with pdfplumber.open(file_path) as pdf:
                # extract text from first 5 pages
                num_pages = min(5, len(pdf.pages))
                self.logger.info(f"PDF has {len(pdf.pages)} pages, will process first {num_pages} pages")
                all_text = []
                total_length = 0
                max_tokens = 3000  # Reduced to leave more room for the prompt
                
                for i in range(num_pages):
                    try:
                        page = pdf.pages[i]
                        self.logger.info(f"Processing page {i+1}")
                        text = page.extract_text()
                        self.logger.info(f"Initial text extraction from page {i+1} length: {len(text) if text else 0}")
                        
                        if not text or len(text.strip()) < 50:
                            self.logger.info(f"Initial text extraction from page {i+1} yielded minimal text, trying with tolerance")
                            text = page.extract_text(x_tolerance=3, y_tolerance=3)
                            if text:
                                self.logger.info(f"Text extracted with tolerance from page {i+1} length: {len(text)}")
                                text = self._clean_ocr_text(text)
                                self.logger.info(f"Cleaned OCR text from page {i+1} length: {len(text)}")
                        
                        if text:
                            # Check if this page contains cover sheet followed by application
                            processed_text = self._process_cover_sheet_and_application(text)
                            
                            # Estimate tokens (rough estimate: 1 token ≈ 4 characters)
                            estimated_tokens = len(processed_text) // 4
                            if total_length + estimated_tokens > max_tokens:
                                self.logger.warning(f"Reached token limit after page {i+1}, truncating text")
                                # Truncate text to fit within remaining tokens
                                remaining_chars = (max_tokens - total_length) * 4
                                processed_text = processed_text[:remaining_chars]
                            
                            all_text.append(processed_text)
                            total_length += estimated_tokens
                            self.logger.info(f"Successfully extracted text from page {i+1}, total estimated tokens: {total_length}")
                            
                            if total_length >= max_tokens:
                                self.logger.info("Reached maximum token limit, stopping extraction")
                                break
                        else:
                            self.logger.warning(f"No text could be extracted from page {i+1}")
                    except Exception as e:
                        self.logger.error(f"Error extracting text from page {i+1}: {str(e)}")
                        continue
                
                final_text = "\n\n".join(all_text)
                self.logger.info(f"Final extracted text length: {len(final_text)}")
                if not final_text:
                    self.logger.warning("No text was extracted from any page")
                return final_text
        except Exception as e:
            self.logger.error(f"Error extracting text from file: {str(e)}")
            return ""

    def _process_cover_sheet_and_application(self, text: str) -> str:
        """Process text to skip cover sheet sections when Application section follows."""
        try:
            # Look for cover sheet patterns followed by application patterns
            cover_sheet_patterns = [
                r'COVER\s+SHEET',
                r'COVER\s+PAGE',
                r'SUMMARY\s+SHEET',
                r'INFORMATION\s+SHEET',
                r'DETAILS\s+SHEET'
            ]
            
            application_patterns = [
                r'^APPLICATION\s+FOR',  # Application for Individual...
                r'^APPLICATION\s+FORM',  # Application Form
                r'^OWNER\s+INFORMATION',  # Owner Information
                r'^APPLICANT\s+INFORMATION',  # Applicant Information
                r'APPLICATION\s+FOR\s+INDIVIDUAL',  # Application for Individual
                r'APPLICATION\s+FOR\s+INDEXED',  # Application for Indexed
                r'APPLICATION\s+FOR\s+DEFERRED',  # Application for Deferred
                r'^APPLICATION$',  # Standalone "Application"
                r'\nAPPLICATION\s+FOR',  # Application for on new line
                r'\nAPPLICATION\s+FORM',  # Application Form on new line
                r'\nOWNER\s+INFORMATION',  # Owner Information on new line
                r'\nAPPLICANT\s+INFORMATION',  # Applicant Information on new line
                r'APPLICATION\s+FOR',  # More general Application for
                r'APPLICATION',  # Fallback to any Application
                r'OWNER\s+INFORMATION',  # More general Owner Information
                r'APPLICANT\s+INFORMATION'  # More general Applicant Information
            ]
            
            # Check if text contains both cover sheet and application sections
            has_cover_sheet = False
            matched_cover_pattern = None
            for pattern in cover_sheet_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    has_cover_sheet = True
                    matched_cover_pattern = pattern
                    self.logger.info(f"Found cover sheet pattern: '{pattern}' at position {match.start()}")
                    break
            
            # Check for application patterns with detailed logging
            has_application = False
            matched_application_pattern = None
            for pattern in application_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    has_application = True
                    matched_application_pattern = pattern
                    self.logger.info(f"Found application pattern: '{pattern}' at position {match.start()}")
                    break
            
            if not has_application:
                self.logger.info("No application patterns found. Available patterns checked:")
                for pattern in application_patterns:
                    self.logger.info(f"  - {pattern}")
                self.logger.info(f"Text sample (first 500 chars): {text[:500]}")
            
            if has_cover_sheet and has_application:
                self.logger.info("Detected cover sheet followed by application section, skipping cover sheet")
                
                # Find the start of the application section
                application_start = -1
                for pattern in application_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        application_start = match.start()
                        break
                
                if application_start != -1:
                    # Extract text from the application section onwards
                    application_text = text[application_start:]
                    self.logger.info(f"Extracted application section starting at position {application_start}")
                    return application_text
                else:
                    self.logger.warning("Could not find start of application section, returning full text")
                    return text
            else:
                # No cover sheet detected or no application section, return full text
                if has_cover_sheet:
                    self.logger.info(f"Cover sheet detected (pattern: {matched_cover_pattern}) but no application section found, returning full text")
                elif has_application:
                    self.logger.info(f"Application section detected (pattern: {matched_application_pattern}) but no cover sheet found, returning full text")
                else:
                    self.logger.info("No cover sheet or application patterns detected, returning full text")
                return text
                
        except Exception as e:
            self.logger.error(f"Error processing cover sheet and application: {str(e)}")
            return text

    def _clean_ocr_text(self, text: str) -> str:
        """Common OCR text cleaning."""
        text = re.sub(r'[^\w\s.,;:!?@#$%^&*()\-_=+\[\]{}|\\/"\'<>]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _extract_owner_info_regex(self, text: str) -> Dict[str, Any]:
        """Extract owner information using regex patterns."""
        try:
            # Patterns for owner information
            full_name_pattern = r"Name\s*\(First\)\s*\(Middle\)\s*\(Last\)\s*\(Suffix\)\s*(\w+)\s+(\w+)"
            address_pattern = r"Mailing Address\s*City\s*State\s*Zip\s*([^\n]+)\s+([^\n]+)\s+([A-Z]{2})\s+(\d{5})"
            phone_pattern = r"Phone Number\s*([\d\-\(\)]+)"
            email_pattern = r"Email Address\s*([^\n]+)"
            dob_pattern = r"DOB\s*\(mm/dd/yyyy\)\s*(\d{2}/\d{2}/\d{4})"
            gender_pattern = r"(\w+)\s*Male\s*Female"

            # Extract information
            full_name_match = re.search(full_name_pattern, text)
            address_match = re.search(address_pattern, text)
            phone_match = re.search(phone_pattern, text)
            email_match = re.search(email_pattern, text)
            dob_match = re.search(dob_pattern, text)
            gender_match = re.search(gender_pattern, text)

            # Parse name parts
            first_name = full_name_match.group(1) if full_name_match else None
            last_name = full_name_match.group(2) if full_name_match else None

            # Parse address parts
            street = address_match.group(1).strip() if address_match else None
            city = address_match.group(2).strip() if address_match else None
            state = address_match.group(3) if address_match else None
            zip_code = address_match.group(4) if address_match else None

            # Parse other fields
            phone = phone_match.group(1) if phone_match else None
            email = email_match.group(1).strip() if email_match else None
            dob = dob_match.group(1) if dob_match else None
            gender = gender_match.group(1) if gender_match else None

            return {
                'firstName': first_name,
                'lastName': last_name,
                'dateOfBirth': dob,
                'gender': gender,
                'mailingAddressStreet': street,
                'mailingAddressCity': city,
                'mailingAddressState': state,
                'mailingAddressZip': zip_code,
                'phoneNumber': phone,
                'emailAddress': email
            }
        except Exception as e:
            self.logger.error(f"Error in regex extraction for owner: {str(e)}")
            return {
                'firstName': None,
                'lastName': None,
                'dateOfBirth': None,
                'gender': None,
                'mailingAddressStreet': None,
                'mailingAddressCity': None,
                'mailingAddressState': None,
                'mailingAddressZip': None,
                'phoneNumber': None,
                'emailAddress': None
            }

    def _extract_joint_owner_info_regex(self, text: str) -> Dict[str, Any]:
        """Extract joint owner information using regex patterns."""
        try:
            # Patterns for joint owner information
            full_name_pattern = r"JOINT OWNER INFORMATION.*?Name\s*\(First\)\s*\(Middle\)\s*\(Last\)\s*\(Suffix\)\s*(\w+)\s+(\w+)\s+(\w+)"
            address_pattern = r"JOINT OWNER INFORMATION.*?Mailing Address\s*City\s*State\s*Zip\s*([^\n]+)\s+([^\n]+)\s+([A-Z]{2})\s+(\d{5})"
            phone_pattern = r"JOINT OWNER INFORMATION.*?Phone Number\s*([\d\-\(\)]+)"
            email_pattern = r"JOINT OWNER INFORMATION.*?Email Address\s*([^\n]+)"
            dob_pattern = r"JOINT OWNER INFORMATION.*?DOB\s*\(mm/dd/yyyy\)\s*(\d{2}/\d{2}/\d{4})"
            gender_pattern = r"JOINT OWNER INFORMATION.*?(\w+)\s*Male\s*Female"

            # Extract information
            full_name_match = re.search(full_name_pattern, text, re.DOTALL)
            address_match = re.search(address_pattern, text, re.DOTALL)
            phone_match = re.search(phone_pattern, text, re.DOTALL)
            email_match = re.search(email_pattern, text, re.DOTALL)
            dob_match = re.search(dob_pattern, text, re.DOTALL)
            gender_match = re.search(gender_pattern, text, re.DOTALL)

            # Parse name parts
            first_name = full_name_match.group(1) if full_name_match else None
            middle_name = full_name_match.group(2) if full_name_match else None
            last_name = full_name_match.group(3) if full_name_match else None

            # Parse address parts
            street = address_match.group(1).strip() if address_match else None
            city = address_match.group(2).strip() if address_match else None
            state = address_match.group(3) if address_match else None
            zip_code = address_match.group(4) if address_match else None

            # Parse other fields
            phone = phone_match.group(1) if phone_match else None
            email = email_match.group(1).strip() if email_match else None
            dob = dob_match.group(1) if dob_match else None
            gender = gender_match.group(1) if gender_match else None

            return {
                'firstName': first_name,
                'middleName': middle_name,
                'lastName': last_name,
                'dateOfBirth': dob,
                'gender': gender,
                'mailingAddressStreet': street,
                'mailingAddressCity': city,
                'mailingAddressState': state,
                'mailingAddressZip': zip_code,
                'phoneNumber': phone,
                'emailAddress': email
            }
        except Exception as e:
            self.logger.error(f"Error in regex extraction for joint owner: {str(e)}")
            return {
                'firstName': None,
                'middleName': None,
                'lastName': None,
                'dateOfBirth': None,
                'gender': None,
                'mailingAddressStreet': None,
                'mailingAddressCity': None,
                'mailingAddressState': None,
                'mailingAddressZip': None,
                'phoneNumber': None,
                'emailAddress': None
            }

    def _save_curl_to_file(self, request_data: Dict, response_data: Optional[Dict] = None) -> None:
        """Common curl command saving."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"lm_studio_request_{timestamp}.json"
            
            data = {
                "request": request_data,
                "response": response_data
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2, cls=SetEncoder)
                
            self.logger.info(f"Saved request/response to {filename}")
        except Exception as e:
            self.logger.error(f"Failed to save curl command: {str(e)}")

    def _log_curl_command(self, request_data: Dict, response_data: Optional[Dict] = None) -> None:
        """Common curl command logging."""
        try:
            self.logger.info("Request data:")
            self.logger.info(json.dumps(request_data, indent=2, cls=SetEncoder))
            
            if response_data:
                self.logger.info("Response data:")
                self.logger.info(json.dumps(response_data, indent=2, cls=SetEncoder))
                
            self._save_curl_to_file(request_data, response_data)
        except Exception as e:
            self.logger.error(f"Failed to log curl command: {str(e)}")

    @abstractmethod
    def _check_server_availability(self) -> None:
        """Check if the server is available."""
        pass

    @abstractmethod
    def _make_request(self, prompt: str, temperature: float = 0.0) -> Dict:
        """Make a request to the model API."""
        pass

    def process_text(self, text: str, filename: str = None) -> Dict[str, Any]:
        """Process text to extract both owner and joint owner information."""
        try:
            self.logger.info(f"_process_text: Processing text to extract owner and joint owner information")
            # Extract owner information first
            owner_info = self._process_owner(text)
            
            # Check if this is a joint application based on filename
            is_joint_application = filename and 'joint' in filename.lower()
            self.logger.info(f"File {filename} is {'a joint' if is_joint_application else 'not a joint'} application")
            
            # Initialize result with owner info
            result = {
                "owner": owner_info
            }
            
            # For joint applications, always include both owner and jointOwner
            if is_joint_application:
                joint_owner_info = self._process_joint_owner(text)
                result["jointOwner"] = joint_owner_info
            
            return result
                
        except Exception as e:
            self.logger.error(f"Error processing text: {str(e)}")
            return {
                "owner": {
                    'firstName': None,
                    'lastName': None,
                    'dateOfBirth': None,
                    'gender': None,
                    'mailingAddressStreet': None,
                    'mailingAddressCity': None,
                    'mailingAddressState': None,
                    'mailingAddressZip': None,
                    'phoneNumber': None,
                    'emailAddress': None
                }
            }

    def _process_owner(self, text: str) -> Dict[str, Any]:
        """Process text to extract owner information."""
        try:
            self.logger.info(f"_process_owner: Processing owner information")
            # Use the model to extract owner information
            owner_prompt = self.prompt_creator.create_owner_extraction_prompt(text)
            self.logger.info(f"owner_prompt: {owner_prompt}")
            owner_response = self._make_request(owner_prompt)
            self.logger.info(f"owner_response: {owner_response}")
            
            if not owner_response or "response" not in owner_response:
                self.logger.error("No response from model for owner")
                return self._get_default_owner_info()
            
            try:
                owner_model_info = json.loads(owner_response["response"])
                if not isinstance(owner_model_info, dict):
                    self.logger.error("Model response is not a dictionary")
                    return self._get_default_owner_info()
                
                if not owner_model_info.get('owner'):
                    self.logger.error("Model response does not contain owner information")
                    return self._get_default_owner_info()
                
                return owner_model_info['owner']
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse owner model response as JSON: {str(e)}")
                return self._get_default_owner_info()
                
        except Exception as e:
            self.logger.error(f"Error processing owner text: {str(e)}")
            return self._get_default_owner_info()

    def _get_default_owner_info(self) -> Dict[str, Any]:
        """Return default owner information structure."""
        return {
            'firstName': None,
            'lastName': None,
            'dateOfBirth': None,
            'gender': None,
            'mailingAddressStreet': None,
            'mailingAddressCity': None,
            'mailingAddressState': None,
            'mailingAddressZip': None,
            'phoneNumber': None,
            'emailAddress': None
        }

    def _process_joint_owner(self, text: str) -> Dict[str, Any]:
        """Process text to extract joint owner information."""
        try:
            self.logger.info(f"_process_joint_owner: Processing joint owner information")
            # Use the model to extract joint owner information
            joint_owner_prompt = self.prompt_creator.create_joint_owner_extraction_prompt(text)
            self.logger.info(f"joint_owner_prompt: {joint_owner_prompt}")
            joint_owner_response = self._make_request(joint_owner_prompt)
            self.logger.info(f"joint_owner_response: {joint_owner_response}")
            
            if not joint_owner_response or "response" not in joint_owner_response:
                self.logger.error("No response from model for joint owner")
                return self._get_default_joint_owner_info()
            
            try:
                joint_owner_model_info = json.loads(joint_owner_response["response"])
                if not isinstance(joint_owner_model_info, dict):
                    self.logger.error("Model response is not a dictionary")
                    return self._get_default_joint_owner_info()
                
                if not joint_owner_model_info.get('jointOwner'):
                    self.logger.error("Model response does not contain joint owner information")
                    return self._get_default_joint_owner_info()
                
                return joint_owner_model_info['jointOwner']
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse joint owner model response as JSON: {str(e)}")
                return self._get_default_joint_owner_info()
                
        except Exception as e:
            self.logger.error(f"Error processing joint owner text: {str(e)}")
            return self._get_default_joint_owner_info()

    def _get_default_joint_owner_info(self) -> Dict[str, Any]:
        """Return default joint owner information structure."""
        return {
            'firstName': None,
            'middleName': None,
            'lastName': None,
            'dateOfBirth': None,
            'gender': None,
            'mailingAddressStreet': None,
            'mailingAddressCity': None,
            'mailingAddressState': None,
            'mailingAddressZip': None,
            'phoneNumber': None,
            'emailAddress': None
        } 