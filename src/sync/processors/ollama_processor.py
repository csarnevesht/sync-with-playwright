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
from .prompt_creator import PromptCreator
from .base_processor import BaseProcessor, SetEncoder

class OllamaProcessor(BaseProcessor):
    def __init__(self, model_name: str = "mistral", base_url: str = "http://localhost:11434"):
        """Initialize the Ollama processor."""
        super().__init__(model_name, base_url)
        self._check_server_availability()
        self.prompt_creator = PromptCreator()

    def _check_server_availability(self) -> None:
        """Check if the Ollama server is available."""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                self.logger.info("Successfully connected to Ollama server")
            else:
                raise Exception(f"Server returned status code {response.status_code}")
        except Exception as e:
            self.logger.error(f"Could not connect to Ollama server: {str(e)}")
            self.logger.error("Please ensure the Ollama server is running at http://localhost:11434")
            raise

    def _make_request(self, prompt: str, temperature: float = 0.0) -> Dict:
        """Make a request to the Ollama API."""
        cached_response = self._get_cached_response(prompt)
        if cached_response:
            return cached_response

        try:
            request_data = self.prompt_creator.create_chat_prompt(prompt, "ollama")
            self._log_curl_command(request_data)

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                raise Exception(f"API request failed with status code {response.status_code}")

            result = response.json()
            if "response" not in result:
                raise Exception("No response in result")

            response_text = result["response"]
            self._cache_response(prompt, {"response": response_text})
            return {"response": response_text}

        except Exception as e:
            self.logger.error(f"Error making request to Ollama: {str(e)}")
            raise

    def process_text(self, text: str) -> Dict[str, Any]:
        """Process text to extract owner information."""
        try:
            # First try regex-based extraction
            regex_info = self._extract_owner_info_regex(text)
            
            # If we have complete information from regex, return it
            if all([
                regex_info['fullName'],
                regex_info['address']['street'],
                regex_info['address']['city'],
                regex_info['address']['state'],
                regex_info['address']['zip']
            ]):
                self.logger.info("Successfully extracted information using regex")
                return regex_info
            
            # Otherwise, use the model
            prompt = self.prompt_creator.create_owner_extraction_prompt(text)
            response = self._make_request(prompt)
            
            if not response or "response" not in response:
                self.logger.error("No response from model")
                return regex_info
            
            try:
                # Try to parse the response as JSON
                model_info = json.loads(response["response"])
                
                # Merge with regex info, preferring model info
                merged_info = regex_info.copy()
                for key, value in model_info.items():
                    if value:  # Only update if the model provided a value
                        if key == 'address' and isinstance(value, dict):
                            merged_info['address'].update(value)
                        else:
                            merged_info[key] = value
                
                return merged_info
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse model response as JSON: {str(e)}")
                return regex_info
                
        except Exception as e:
            self.logger.error(f"Error processing text: {str(e)}")
            return {
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
                            self.logger.info(f"\n\033[92m=== BEGIN EXTRACTED TEXT FOR OLLAMA PAGE {i+1} ===\033[0m")
                            self.logger.info(text)
                            self.logger.info(f"\n\033[92m=== END OF EXTRACTED TEXT FOR OLLAMA PAGE {i+1} ===\033[0m")
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

    def _log_curl_command(self, request_data: Dict[str, Any]) -> None:
        """Log the curl command for debugging purposes."""
        try:
            # Get the current timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Clean up old request files
            request_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs", "requests")
            if os.path.exists(request_dir):
                # Remove Ollama request files
                for old_file in glob.glob(os.path.join(request_dir, "ollama_request_*.json")):
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
            request_file = os.path.join(request_dir, f"ollama_request_{timestamp}.json")
            
            # Create the curl command without debug prefixes
            curl_command = f"""curl -X POST {self.base_url}/api/generate -d '{json.dumps(request_data)}'"""
            
            # Save the request data and curl command
            with open(request_file, "w") as f:
                json.dump({
                    "timestamp": timestamp,
                    "request": request_data,
                    "curl_command": curl_command
                }, f, indent=2)
            
            self.logger.info(f"Saved request data to: {request_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to log curl command: {str(e)}")
            # Don't raise the exception - this is just for debugging

    def _initialize_cache(self):
        """Initialize the response cache."""
        self.response_cache = {}
        self.cache_timestamps = {}

    def _get_cache_key(self, prompt: str) -> str:
        """Generate a cache key for a prompt."""
        return hashlib.md5(prompt.encode()).hexdigest()

    def _get_cached_response(self, prompt: str) -> Optional[Dict]:
        """Get a cached response if available and not expired."""
        cache_key = self._get_cache_key(prompt)
        if cache_key in self.response_cache:
            timestamp = self.cache_timestamps.get(cache_key)
            if timestamp and datetime.now() - timestamp < self.cache_duration:
                self.logger.debug("Using cached response")
                return self.response_cache[cache_key]
        return None

    def _cache_response(self, prompt: str, response: Dict):
        """Cache a response with timestamp."""
        cache_key = self._get_cache_key(prompt)
        self.response_cache[cache_key] = response
        self.cache_timestamps[cache_key] = datetime.now()

    def _create_prompt(self, text: str) -> str:
        """Create a prompt for the model."""
        # Implementation of _create_prompt method
        pass

    def _create_owner_extraction_prompt(self, text: str) -> str:
        """Create a prompt for owner extraction."""
        # Implementation of _create_owner_extraction_prompt method
        pass

    def _check_ollama_server(self) -> None:
        """Check if Ollama server is running and accessible."""
        self.logger.info("Checking Ollama server availability...")
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=self.server_check_timeout)
            if response.status_code != 200:
                self.logger.error(f"Ollama server returned status code {response.status_code}")
                self.logger.error("Please ensure Ollama server is running and accessible")
                sys.exit(1)
            self.logger.info("Ollama server is running and accessible")
        except requests.exceptions.ConnectionError:
            self.logger.error("Could not connect to Ollama server")
            self.logger.error(f"Please ensure Ollama server is running at {self.base_url}")
            self.logger.error("You can start it by running 'ollama serve' in a terminal")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Error checking Ollama server: {str(e)}")
            sys.exit(1)

    def process_text(self, text: str) -> Dict[str, Any]:
        """Process text with Ollama to extract information."""
        self.logger.info("!!! PROCESS_TEXT CALLED !!!")
        try:
            self.logger.info(f"process_text TEXT: {text[:200]}")
            
            # Process each chunk
            all_results = []
            
            try:
                self.logger.info(f"calling make_ollama_request")
                result_raw = self._make_request(self._create_prompt(text))
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
            if all_results:
                combined_result = all_results[0]  # For now, just use the first result
                self.logger.info(f"Ollama extraction results: {json.dumps(combined_result, indent=2)}")
                # Add primary applicant information
                if 'owner' in combined_result:
                    primary = combined_result['owner']
                    if primary.get('fullName'):
                        info['owner_name'] = primary['fullName']
                    if primary.get('address'):
                        addr = primary['address']
                        address_parts = []
                        if addr.get('street'): address_parts.append(addr['street'])
                        if addr.get('city'): address_parts.append(addr['city'])
                        if addr.get('state'): address_parts.append(addr['state'])
                        if addr.get('zip'): address_parts.append(addr['zip'])
                        if address_parts:
                            info['owner_address'] = ', '.join(address_parts)
                    if primary.get('phone'):
                        info['owner_phone'] = primary['phone']
                    if primary.get('email'):
                        info['owner_email'] = primary['email']
                    owner_extracted = True
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
            self.logger.error(f"Error processing text with Ollama: {e}")
            return {} 
