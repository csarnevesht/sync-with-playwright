import json
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
import requests
from pathlib import Path
import PyPDF2
import io
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import hashlib
from datetime import datetime, timedelta
import pdfplumber
import re
import os
import glob

class LMStudioProcessor:
    def __init__(self, model_name: str = "Element Labs Inc"):
        """Initialize the LM Studio processor."""
        self.model_name = model_name
        self.base_url = "http://localhost:1234/v1"  # Default LM Studio API endpoint
        self.max_chunk_size = 2000
        self.max_retries = 5
        self.retry_delay = 1
        self.base_timeout = 180
        self.server_check_timeout = 10
        self.cache_duration = timedelta(hours=24)  # Cache results for 24 hours
        
        # Configure logging for pdfplumber
        logging.getLogger('pdfplumber').setLevel(logging.WARNING)
        logging.getLogger('PIL').setLevel(logging.WARNING)  # Also suppress PIL logging
        
        # Configure logging for other PDF-related libraries
        logging.getLogger('pdfminer').setLevel(logging.WARNING)
        logging.getLogger('pdfminer.pdfparser').setLevel(logging.WARNING)
        logging.getLogger('pdfminer.pdfdocument').setLevel(logging.WARNING)
        logging.getLogger('pdfminer.pdfpage').setLevel(logging.WARNING)
        logging.getLogger('pdfminer.pdfinterp').setLevel(logging.WARNING)
        logging.getLogger('pdfminer.converter').setLevel(logging.WARNING)
        logging.getLogger('pdfminer.cmapdb').setLevel(logging.WARNING)

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.hasHandlers():
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self._check_server_availability()
        self._initialize_cache()

    def _initialize_cache(self):
        """Initialize the response cache."""
        self.response_cache = {}
        self.cache_timestamps = {}

    def _get_cache_key(self, prompt: str) -> str:
        """Generate a cache key for a prompt."""
        return hashlib.md5(prompt.encode()).hexdigest()

    def _get_cached_response(self, prompt: str) -> Optional[str]:
        """Get a cached response if available and not expired."""
        cache_key = self._get_cache_key(prompt)
        if cache_key in self.response_cache:
            timestamp = self.cache_timestamps.get(cache_key)
            if timestamp and datetime.now() - timestamp < self.cache_duration:
                self.logger.debug("Using cached response")
                return self.response_cache[cache_key]
        return None

    def _cache_response(self, prompt: str, response: str):
        """Cache a response with timestamp."""
        cache_key = self._get_cache_key(prompt)
        self.response_cache[cache_key] = response
        self.cache_timestamps[cache_key] = datetime.now()

    def _check_server_availability(self) -> None:
        """Check if LM Studio server is running and accessible."""
        self.logger.info("Checking LM Studio server availability...")
        try:
            response = requests.get(f"{self.base_url}/models", timeout=self.server_check_timeout)
            if response.status_code != 200:
                self.logger.error(f"LM Studio server returned status code {response.status_code}")
                self.logger.error("Please ensure LM Studio server is running and accessible")
                sys.exit(1)
            self.logger.info("LM Studio server is running and accessible")
        except requests.exceptions.ConnectionError:
            self.logger.error("Could not connect to LM Studio server")
            self.logger.error("Please ensure LM Studio server is running at http://localhost:1234")
            self.logger.error("You can start it by running LM Studio and enabling the local server")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Error checking LM Studio server: {str(e)}")
            sys.exit(1)

    def _extract_text_from_file(self, file_path: str) -> str:
        """Extract text from the first 5 pages of a PDF file with OCR fallback."""
        try:
            if not file_path.lower().endswith('.pdf'):
                self.logger.warning(f"File is not a PDF: {file_path}")
                return ""

            with pdfplumber.open(file_path) as pdf:
                num_pages = min(5, len(pdf.pages))
                all_text = []
                for i in range(num_pages):
                    try:
                        page = pdf.pages[i]
                        # Try normal text extraction first
                        text = page.extract_text()

                        # If text is too short or empty, try OCR
                        if not text or len(text.strip()) < 50:  # Arbitrary threshold
                            self.logger.info(f"Page {i+1}: Normal text extraction yielded minimal text, trying OCR...")
                            text = page.extract_text(x_tolerance=3, y_tolerance=3)
                            if text:
                                text = self._clean_ocr_text(text)

                        if text:
                            # Replace underscore followed by a letter with space and that letter
                            text = re.sub(r'_(\w)', r' \1', text)
                            # Remove all remaining underscores
                            text = text.replace('_', '')
                            # Optionally, normalize whitespace
                            text = re.sub(r'\s+', ' ', text).strip()
                            all_text.append(text)
                            self.logger.info(f"\n\033[92m=== BEGIN EXTRACTED TEXT FOR LM STUDIO PAGE {i+1} ===\033[0m")
                            self.logger.info(text)
                            self.logger.info(f"\n\033[92m=== END OF EXTRACTED TEXT FOR LM STUDIO PAGE {i+1} ===\033[0m")
                        else:
                            self.logger.info(f"Page {i+1}: No text extracted.")
                    except Exception as e:
                        self.logger.error(f"Error extracting text from page {i+1}: {str(e)}")
                        continue

                return "\n\n".join(all_text)

        except Exception as e:
            self.logger.error(f"Error extracting text from file: {str(e)}")
            return ""

    def _clean_ocr_text(self, text: str) -> str:
        """Clean OCR-extracted text."""
        # Remove common OCR artifacts
        text = re.sub(r'[^\w\s.,;:!?@#$%^&*()\-_=+\[\]{}|\\/"\'<>]', '', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _make_lm_studio_request(self, prompt: str, temperature: float = 0.0) -> Dict:
        """Make a request to LM Studio API with retries and error handling."""
        self.logger.critical("!!! LM STUDIO REQUEST ENTRY POINT REACHED !!!")
        self.logger.info("\n=== [LM STUDIO REQUEST START] ===")
        self.logger.info(f"Temperature: {temperature}")
        self.logger.info(f"Prompt length: {len(prompt)} characters")
        
        request_data = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a precise JSON extraction tool. Your task is to extract owner information from text and return it in a specific JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": temperature,
            "max_tokens": 1000
        }
        
        self._save_curl_to_file(request_data, "lm_studio_request")
        # Log the curl command for debugging
        self._log_curl_command(request_data, {})
        
        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"\n=== [ATTEMPT {attempt + 1}/{max_retries}] ===")
                self.logger.info(f"Timeout: {self.base_timeout} seconds")
                
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    json=request_data,
                    timeout=self.base_timeout
                )
                
                self.logger.info(f"API Response Status: {response.status_code}")
                
                if response.status_code == 200:
                    self.logger.info("\n=== [RESPONSE PARSING START] ===")
                    response_text = response.text
                    self.logger.info(f"Raw response length: {len(response_text)} characters")
                    self.logger.info(f"Raw response: {response_text}")
                    
                    # Save raw response to file for debugging
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    debug_file = f"debug_raw_response_{timestamp}.txt"
                    with open(debug_file, "w") as f:
                        f.write(response_text)
                    self.logger.info(f"Saved raw response to {debug_file}")
                    
                    # Parse the response JSON
                    try:
                        response_json = json.loads(response_text)
                        self.logger.info("Successfully parsed response JSON")
                        
                        # Extract the actual response text from the LM Studio response
                        if "choices" not in response_json or not response_json["choices"]:
                            self.logger.error("No 'choices' field in LM Studio response")
                            raise ValueError("No 'choices' field in LM Studio response")
                            
                        actual_response = response_json["choices"][0]["message"]["content"]
                        self.logger.info(f"Actual response length: {len(actual_response)} characters")
                        self.logger.info(f"Actual response: {actual_response}")
                        
                        # Save actual response to file for debugging
                        actual_response_file = f"debug_actual_response_{timestamp}.txt"
                        with open(actual_response_file, "w") as f:
                            f.write(actual_response)
                        self.logger.info(f"Saved actual response to {actual_response_file}")
                        
                        # Find the first { and last }
                        start_idx = actual_response.find('{')
                        end_idx = actual_response.rfind('}')
                        
                        if start_idx == -1 or end_idx == -1:
                            self.logger.error("No JSON object found in response")
                            self.logger.error(f"Response text: {actual_response}")
                            raise ValueError("No JSON object found in response")
                        
                        self.logger.info(f"JSON start index: {start_idx}")
                        self.logger.info(f"JSON end index: {end_idx}")
                        
                        # Extract just the JSON part
                        json_text = actual_response[start_idx:end_idx + 1]
                        self.logger.info(f"Extracted JSON text: {json_text}")
                        
                        try:
                            # Try to parse the JSON
                            parsed_json = json.loads(json_text)
                            self.logger.info("Successfully parsed JSON")
                            
                            # Validate the structure
                            if not isinstance(parsed_json, dict):
                                self.logger.error(f"Parsed JSON is not a dictionary: {type(parsed_json)}")
                                raise ValueError("Parsed JSON is not a dictionary")
                            
                            required_fields = ["owner"]
                            missing_fields = [field for field in required_fields if field not in parsed_json]
                            
                            if missing_fields:
                                self.logger.error(f"Missing required fields: {missing_fields}")
                                self.logger.error(f"Available fields: {list(parsed_json.keys())}")
                                raise ValueError(f"Missing required fields: {missing_fields}")
                            
                            # Save validated JSON to file for debugging
                            validated_json_file = f"debug_validated_json_{timestamp}.json"
                            with open(validated_json_file, "w") as f:
                                json.dump(parsed_json, f, indent=2)
                            self.logger.info(f"Saved validated JSON to {validated_json_file}")
                            
                            self.logger.info("JSON structure validation passed")
                            self.logger.info("\n=== [LM STUDIO REQUEST SUCCESS] ===")
                            return parsed_json
                            
                        except json.JSONDecodeError as e:
                            self.logger.error(f"JSON parsing error: {str(e)}")
                            self.logger.error(f"Problematic JSON text: {json_text}")
                            # Save the problematic JSON for debugging
                            error_json_file = f"debug_error_json_{timestamp}.txt"
                            with open(error_json_file, "w") as f:
                                f.write(json_text)
                            self.logger.info(f"Saved problematic JSON to {error_json_file}")
                            raise
                            
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Error parsing LM Studio response JSON: {str(e)}")
                        raise
                        
                else:
                    self.logger.error(f"API request failed with status {response.status_code}")
                    self.logger.error(f"Response text: {response.text}")
                    
            except (requests.exceptions.RequestException, ValueError, json.JSONDecodeError) as e:
                self.logger.error(f"Error on attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    self.logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    self.logger.error("Max retries reached")
                    raise
        
        self.logger.error("All retry attempts failed")
        raise Exception("Failed to get valid response from LM Studio after all retries")

    def _save_curl_to_file(self, data: dict, prefix: str) -> str:
        """Save data to a JSON file with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.json"
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.info(f"Saved {prefix} data to {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"Failed to save {prefix} data to file: {str(e)}")
            return None

    def _log_curl_command(self, request_data: Dict[str, Any], response_data: Dict[str, Any]) -> None:
        """Log the curl command for debugging purposes."""
        try:
            # Get the current timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Clean up old request files
            request_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs", "requests")
            if os.path.exists(request_dir):
                # Remove LM Studio request files
                for old_file in glob.glob(os.path.join(request_dir, "lm_studio_request_*.json")):
                    try:
                        os.remove(old_file)
                        self.logger.debug(f"Deleted old request file: {old_file}")
                    except Exception as e:
                        self.logger.warning(f"Failed to delete old request file {old_file}: {str(e)}")
                
                # Remove debug files
                for old_file in glob.glob(os.path.join(request_dir, "debug_*")):
                    try:
                        os.remove(old_file)
                        self.logger.debug(f"Deleted old debug file: {old_file}")
                    except Exception as e:
                        self.logger.warning(f"Failed to delete old debug file {old_file}: {str(e)}")
            
            # Create the request directory if it doesn't exist
            os.makedirs(request_dir, exist_ok=True)
            
            # Create the request file path
            request_file = os.path.join(request_dir, f"lm_studio_request_{timestamp}.json")
            
            # Create the curl command without debug prefixes
            curl_command = f"""curl -X POST http://localhost:1234/v1/chat/completions -d '{json.dumps(request_data)}'"""
            
            # Save the request data, response data, and curl command
            with open(request_file, "w") as f:
                json.dump({
                    "timestamp": timestamp,
                    "request": request_data,
                    "response": response_data,
                    "curl_command": curl_command
                }, f, indent=2)
            
            self.logger.info(f"Saved request data to: {request_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to log curl command: {str(e)}")
            # Don't raise the exception - this is just for debugging

    def _create_prompt(self, text: str) -> str:
        """Create a prompt for LM Studio to extract owner information in a specific JSON format."""
        self.logger.info("=== [PROMPT CREATION START] ===")
        self.logger.info(f"Text length: {len(text)} characters")
        self.logger.info(f"Text first 200 chars: {text[:200]}")

        main_prompt = (
            "Analyze the following text and extract key information about the owner. "
            "Return ONLY a JSON object with the following structure, using the specified types (use null if not found):\n"
            "{{\n"
            "  \"owner\": {{\n"
            "    \"firstName\": \"string or null\",\n"
            "    \"middleInitial\": \"string or null\",\n"
            "    \"lastName\": \"string or null\",\n"
            "    \"SSN\": \"string or null\",\n"
            "    \"dateOfBirth\": \"string (YYYY-MM-DD) or null\",\n"
            "    \"gender\": \"string or null\",\n"
            "    \"mailingAddressCity\": \"string or null\",\n"
            "    \"mailingAddressState\": \"string or null\",\n"
            "    \"mailingAddressZip\": \"string or null\",\n"
            "    \"residentialAddressCity\": \"string or null\",\n"
            "    \"residentialAddressState\": \"string or null\",\n"
            "    \"residentialAddressZip\": \"string or null\",\n"
            "    \"phoneNumber\": \"string or null\",\n"
            "    \"emailAddress\": \"string or null\"\n"
            "  }}\n"
            "}}\n\n"
            "Text to analyze:\n{text}\n\n"
            "YOUR RESPONSE MUST BE A SINGLE JSON OBJECT WITH NO ADDITIONAL TEXT OR FORMATTING. DO NOT INCLUDE ANY EXPLANATORY TEXT, MARKDOWN, OR CODE BLOCKS. JUST THE JSON OBJECT. If a field is not found, use null."
        )

        system_message = (
            "You are a precise JSON extraction tool. Your task is to extract owner information from text and return it in a specific JSON format.\n"
            "IMPORTANT RULES:\n"
            "1. Return ONLY the JSON object, no other text\n"
            "2. If a field is not found, use null\n"
            "3. Do not include any explanatory text\n"
            "4. Do not include any markdown formatting\n"
            "5. Do not include any code blocks\n"
            "6. The response must be a single, valid JSON object\n"
            "7. Do not include any extra fields in the response\n"
            "8. All keys in the JSON object must be in camelCase\n"
            "9. Only extract fields listed below — do not add any others.\n"
            "10. Never fabricate or guess information; only extract what is clearly present in the input text.\n"
            "11. Ignore placeholder labels like 'First', 'Last', and 'MI' in field labels such as 'Name: First MI Last'. These are not real values and should not be included in the output.\n"
            "12. Extract only the actual names that appear after these labels.\n"
            "13. Here is the required JSON structure:\n"
        )

        try:
            formatted_main_prompt = main_prompt.format(text=text)
            final_prompt = f"{system_message}\n\n{formatted_main_prompt}"
            self.logger.info("\n=== [PROMPT GENERATED] ===")
            self.logger.info(f"Prompt length: {len(final_prompt)} characters")
            self.logger.info(f"Final Prompt: {final_prompt}")
            return final_prompt
        except KeyError as e:
            self.logger.error(f"Error formatting prompt: Missing key in format string - {str(e)}")
            self.logger.error(f"Text being formatted: {text[:200]}...")
            raise ValueError(f"Failed to format prompt: Missing key {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error formatting prompt: {str(e)}")
            self.logger.error(f"Text being formatted: {text[:200]}...")
            raise ValueError(f"Failed to format prompt: {str(e)}")

    def process_text(self, text: str) -> Dict[str, Any]:
        """Process text with LM Studio to extract information."""
        self.logger.info("!!! PROCESS_TEXT CALLED !!!")
        try:
            self.logger.info(f"process_text TEXT: {text[:200]}")
            
            # Process each chunk
            all_results = []
            
            try:
                self.logger.info(f"calling make_lm_studio_request")
                result_raw = self._make_lm_studio_request(self._create_prompt(text))
                self.logger.info(f"result raw: {result_raw}")
                self.logger.info(f"Type of result_raw: {type(result_raw)}")
                if isinstance(result_raw, str):
                    chunk_result = json.loads(result_raw)
                elif isinstance(result_raw, dict):
                    result = result_raw
                else:
                    self.logger.error(f"Unexpected type for result_raw: {type(result_raw)}")
                    result = {}
            except Exception as e:
                self.logger.error(f"Failed to parse owner JSON: {e}\nRaw: {result_raw if 'result_raw' in locals() else ''}")
                result = {}
            if result:
                all_results.append(result)

            # Combine results
            info = {
                'application_type': 'Life Insurance',  # Default type
                'status': 'Processed'  # Default status
            }
            # Owner extraction (primary applicant)
            owner_extracted = False
            for result in all_results:
                if result.get('owner'):
                    owner = result['owner']
                    if owner.get('firstName') or owner.get('lastName'):
                        owner_extracted = True
                        # Combine first, middle, and last names
                        name_parts = []
                        if owner.get('firstName'):
                            name_parts.append(owner['firstName'])
                        if owner.get('middleInitial'):
                            name_parts.append(owner['middleInitial'])
                        if owner.get('lastName'):
                            name_parts.append(owner['lastName'])
                        info['owner_name'] = ' '.join(name_parts)
                        
                        # Combine address parts
                        address_parts = []
                        if owner.get('mailingAddressCity'):
                            address_parts.append(owner['mailingAddressCity'])
                        if owner.get('mailingAddressState'):
                            address_parts.append(owner['mailingAddressState'])
                        if owner.get('mailingAddressZip'):
                            address_parts.append(owner['mailingAddressZip'])
                        if address_parts:
                            info['owner_address'] = ', '.join(address_parts)
                            
                        if owner.get('phoneNumber'):
                            info['owner_phone'] = owner['phoneNumber']
                        if owner.get('emailAddress'):
                            info['owner_email'] = owner['emailAddress']

            # Regex fallback for owner if not extracted
            if not owner_extracted:
                self.logger.info("[REGEX] Running regex-based owner extraction for debugging.")
                owner_regex = self._extract_owner_info_regex(text)
                self.logger.info(f"[REGEX] Regex owner extraction result: {json.dumps(owner_regex, indent=2)}")
                if owner_regex.get('fullName'):
                    info['owner_name'] = owner_regex['fullName']
                addr = owner_regex.get('address', {})
                address_parts = []
                if addr.get('street'): address_parts.append(addr['street'])
                if addr.get('city'): address_parts.append(addr['city'])
                if addr.get('state'): address_parts.append(addr['state'])
                if addr.get('zip'): address_parts.append(addr['zip'])
                if address_parts:
                    info['owner_address'] = ', '.join(address_parts)
                if owner_regex.get('phone'):
                    info['owner_phone'] = owner_regex['phone']
                if owner_regex.get('email'):
                    info['owner_email'] = owner_regex['email']
            
            self.logger.info(f"Final extracted file info: {json.dumps(info, indent=2)}")
            return info
            
        except Exception as e:
            self.logger.error(f"Error processing text with LM Studio: {e}")
            return {}

    def _extract_owner_info_regex(self, text: str) -> Dict[str, Any]:
        """Extract owner information using regex patterns."""
        info = {
            'fullName': None,
            'address': {
                'street': None,
                'city': None,
                'state': None,
                'zip': None
            },
            'phone': None,
            'email': None
        }
        
        # Extract name
        name_patterns = [
            r'Name\s*:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'Applicant\s*:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'Insured\s*:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'Policyholder\s*:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                info['fullName'] = match.group(1).strip()
                break
        
        # Extract address
        address_patterns = {
            'street': r'Address\s*:\s*([^\n]+)',
            'city': r'City\s*:\s*([^\n]+)',
            'state': r'State\s*:\s*([A-Z]{2})',
            'zip': r'Zip\s*:\s*(\d{5}(?:-\d{4})?)'
        }
        
        for field, pattern in address_patterns.items():
            match = re.search(pattern, text)
            if match:
                info['address'][field] = match.group(1).strip()
        
        # Extract phone
        phone_match = re.search(r'Phone\s*:\s*(\d{3}[-.]?\d{3}[-.]?\d{4})', text)
        if phone_match:
            info['phone'] = phone_match.group(1)
        
        # Extract email
        email_match = re.search(r'Email\s*:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text)
        if email_match:
            info['email'] = email_match.group(1)
        
        return info 