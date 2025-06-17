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

class OllamaProcessor:
    def __init__(self, model_name: str = "mistral:latest"):
        """Initialize the Ollama processor."""
        self.model_name = model_name
        self.base_url = "http://localhost:11434"
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
        self._check_model_availability()
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
            self.logger.error("Please ensure Ollama server is running at http://localhost:11434")
            self.logger.error("You can start it by running: ollama serve")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Error checking Ollama server: {str(e)}")
            sys.exit(1)

    def _check_model_availability(self) -> None:
        """Check if the model is available and pull it if necessary."""
        try:
            # Check if Ollama server is running
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code != 200:
                raise Exception("Ollama server is not running")
                
            # Check if model is available
            model_names = [model['name'] for model in response.json()['models']]
            self.logger.debug(f"Available models: {model_names}")
            
            if self.model_name not in model_names:
                self.logger.info(f"Mistral model not found. Pulling model...")
                pull_response = requests.post(
                    f"{self.base_url}/api/pull",
                    json={"name": self.model_name}
                )
                if pull_response.status_code != 200:
                    raise Exception(f"Failed to pull model: {pull_response.text}")
                self.logger.info("Model pulled successfully")
            else:
                self.logger.info(f"Model {self.model_name} is available")
                
        except Exception as e:
            self.logger.error(f"Error checking model availability: {str(e)}")
            raise

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
                        self.logger.warning(f"Error processing page {i+1}: {str(e)}")
                        continue
                combined_text = '\n'.join(all_text)
                return combined_text
        except Exception as e:
            self.logger.error(f"Error extracting text from PDF: {str(e)}")
            return ""

    def _clean_ocr_text(self, text: str) -> str:
        """Clean and normalize OCR text."""
        if not text:
            return text
            
        # Replace common OCR errors
        replacements = {
            'l': '1',  # lowercase L to 1
            'O': '0',  # uppercase O to 0
            '|': '1',  # vertical bar to 1
            '[': '(',  # square bracket to parenthesis
            ']': ')',
            '}{': '{}',  # Fix reversed braces
            '}{': '{}',
            ')(': '()',  # Fix reversed parentheses
            ')(': '()',
            ',,': ',',  # Fix double punctuation
            '..': '.',
            '  ': ' ',  # Fix double spaces
        }
        
        # Apply replacements
        for old, new in replacements.items():
            text = text.replace(old, new)
            
        # Fix common OCR spacing issues
        text = re.sub(r'(\d)\s*-\s*(\d)', r'\1-\2', text)  # Fix phone numbers
        text = re.sub(r'(\d)\s*/\s*(\d)', r'\1/\2', text)  # Fix dates
        text = re.sub(r'(\w)\s*:\s*(\w)', r'\1: \2', text)  # Fix colons
        text = re.sub(r'(\w)\s*,\s*(\w)', r'\1, \2', text)  # Fix commas
        
        # Fix extra spaces in names (e.g., "A lb e rt" -> "Albert")
        text = re.sub(r'([A-Za-z])\s+([A-Za-z])', r'\1\2', text)
        
        # Remove any remaining non-printable characters
        text = ''.join(char for char in text if char.isprintable())
        
        return text

    def _split_text_into_chunks(self, text: str) -> List[str]:
        """Split text into chunks of maximum size with improved handling."""
        if not text:
            return []
            
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_size = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            # If a single paragraph is larger than max_chunk_size, split it by sentences
            if len(paragraph) > self.max_chunk_size:
                sentences = paragraph.split('. ')
                for sentence in sentences:
                    if current_size + len(sentence) > self.max_chunk_size:
                        if current_chunk:
                            chunks.append(' '.join(current_chunk))
                            current_chunk = []
                            current_size = 0
                        # If a single sentence is too long, split it by words
                        if len(sentence) > self.max_chunk_size:
                            words = sentence.split()
                            temp_chunk = []
                            temp_size = 0
                            for word in words:
                                if temp_size + len(word) + 1 > self.max_chunk_size:
                                    if temp_chunk:
                                        chunks.append(' '.join(temp_chunk))
                                        temp_chunk = []
                                        temp_size = 0
                                temp_chunk.append(word)
                                temp_size += len(word) + 1
                            if temp_chunk:
                                current_chunk.extend(temp_chunk)
                                current_size += temp_size
                        else:
                            current_chunk.append(sentence)
                            current_size += len(sentence) + 2
                    else:
                        current_chunk.append(sentence)
                        current_size += len(sentence) + 2
            else:
                if current_size + len(paragraph) > self.max_chunk_size:
                    if current_chunk:
                        chunks.append(' '.join(current_chunk))
                        current_chunk = []
                        current_size = 0
                current_chunk.append(paragraph)
                current_size += len(paragraph) + 2
                
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            
        # Limit the number of chunks to prevent excessive processing
        if len(chunks) > 10:  # Increased from 5 to 10 to handle more content
            self.logger.warning(f"Too many chunks ({len(chunks)}), limiting to first 10")
            chunks = chunks[:10]
            
        return chunks


    def _process_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Process a single file and extract information using Ollama."""
        try:
            self.logger.info(f"Processing file: {file_path}")
            
            # Extract text from file
            text = self._extract_text_from_file(str(file_path))
            if not text:
                return None
                
            # Process the entire text directly
            try:
                # Create prompt for the text
                prompt = self._create_prompt(text)
                
                # Make request to Ollama
                response = self._make_ollama_request(prompt)
                
                # Parse and validate response
                result = self._parse_ollama_response(response)
                if result:
                    return result
                    
                return None
                
            except Exception as e:
                self.logger.error(f"Error processing text: {str(e)}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error processing file: {str(e)}")
            return None

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

    def _extract_json_from_response(self, response_text: str) -> tuple[Optional[str], Optional[str]]:
        """Extract and clean JSON from response text."""
        try:
            # Find the JSON object in the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start < 0 or json_end <= json_start:
                return None, "No JSON object found in response"
            
            # Extract just the JSON part
            json_text = response_text[json_start:json_end]
            self.logger.info(f"Extracted JSON text: {json_text}")
            
            # Clean the JSON text
            json_text = (json_text
                .replace('```json', '')
                .replace('```', '')
                .replace('\n', ' ')
                .replace('\r', '')
            )
            json_text = re.sub(r'\s+', ' ', json_text).strip()
            
            # Validate basic JSON structure
            if not json_text.startswith('{') or not json_text.endswith('}'):
                return None, "Invalid JSON structure: missing braces"
            
            return json_text, None
            
        except Exception as e:
            return None, f"Error extracting JSON: {str(e)}"

    def _validate_json_structure(self, json_text: str) -> tuple[Optional[dict], Optional[str]]:
        """Validate JSON structure and required fields."""
        try:
            # First try to parse the JSON
            try:
                parsed_json = json.loads(json_text)
            except json.JSONDecodeError as e:
                return None, f"Invalid JSON format: {str(e)}"
            
            # Validate it's an object
            if not isinstance(parsed_json, dict):
                return None, "Response is not a JSON object"
            
            # Validate required fields
            required_fields = ["owner", "jointOwner"]
            missing_fields = [field for field in required_fields if field not in parsed_json]
            
            if missing_fields:
                return None, f"Missing required fields: {', '.join(missing_fields)}"
            
            # Validate nested structure
            for person in ["owner", "jointOwner"]:
                if not isinstance(parsed_json[person], dict):
                    return None, f"Invalid structure: {person} must be an object"
                
                required_person_fields = ["fullName", "address", "email", "phone"]
                missing_person_fields = [field for field in required_person_fields if field not in parsed_json[person]]
                
                if missing_person_fields:
                    return None, f"Missing fields in {person}: {', '.join(missing_person_fields)}"
                
                if not isinstance(parsed_json[person]["address"], dict):
                    return None, f"Invalid structure: {person}.address must be an object"
                
                required_address_fields = ["street", "city", "state", "zip"]
                missing_address_fields = [field for field in required_address_fields if field not in parsed_json[person]["address"]]
                
                if missing_address_fields:
                    return None, f"Missing fields in {person}.address: {', '.join(missing_address_fields)}"
            
            return parsed_json, None
            
        except Exception as e:
            return None, f"Error validating JSON: {str(e)}"

    def _log_curl_command(self, request_data: Dict[str, Any], response_data: Dict[str, Any]) -> None:
        """Log the curl command for debugging purposes."""
        try:
            # Get the current timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Clean up old request files
            request_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs", "requests")
            if os.path.exists(request_dir):
                # Remove ollama request files
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
            curl_command = f"""curl -X POST http://localhost:11434/api/generate -d '{json.dumps(request_data)}'"""
            
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

    def _make_ollama_request(self, prompt: str, model: str = "mistral:latest", temperature: float = 0.0) -> Dict:
        """Make a request to Ollama API with retries and error handling."""
        self.logger.critical("!!! OLLAMA REQUEST ENTRY POINT REACHED !!!")
        self.logger.info("\n=== [OLLAMA REQUEST START] ===")
        self.logger.info(f"Model: {model}")
        self.logger.info(f"Temperature: {temperature}")
        self.logger.info(f"Prompt length: {len(prompt)} characters")
        
        request_data = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "stream": False
        }
        
        self._save_curl_to_file(request_data, "ollama_request")
        # Log the curl command for debugging
        self._log_curl_command(request_data, {})
        
        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"\n=== [ATTEMPT {attempt + 1}/{max_retries}] ===")
                self.logger.info(f"Timeout: {self.base_timeout} seconds")
                
                response = requests.post(
                    f"{self.base_url}/api/generate",
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
                        
                        # Extract the actual response text from the Ollama response
                        if "response" not in response_json:
                            self.logger.error("No 'response' field in Ollama response")
                            raise ValueError("No 'response' field in Ollama response")
                            
                        actual_response = response_json["response"]
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
                        
                        json_text = actual_response[start_idx:end_idx + 1]
                        self.logger.info(f"Extracted JSON length: {len(json_text)} characters")
                        self.logger.info(f"Extracted JSON: {json_text}")
                        
                        # Save extracted JSON to file for debugging
                        json_debug_file = f"debug_extracted_json_{timestamp}.json"
                        with open(json_debug_file, "w") as f:
                            f.write(json_text)
                        self.logger.info(f"Saved extracted JSON to {json_debug_file}")
                        
                        # Remove any markdown formatting
                        json_text = json_text.replace('```json', '').replace('```', '')
                        self.logger.info("Removed markdown formatting")
                        
                        try:
                            # Try to parse the JSON
                            parsed_json = json.loads(json_text)
                            self.logger.info("Successfully parsed JSON")
                            
                            # Validate the structure
                            if not isinstance(parsed_json, dict):
                                self.logger.error(f"Parsed JSON is not a dictionary: {type(parsed_json)}")
                                raise ValueError("Parsed JSON is not a dictionary")
                            
                            required_fields = ["owner", "jointOwner"]
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
                            self.logger.info("\n=== [OLLAMA REQUEST SUCCESS] ===")
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
                        self.logger.error(f"Error parsing Ollama response JSON: {str(e)}")
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
        raise Exception("Failed to get valid response from Ollama after all retries")

    def _merge_chunk_data(self, target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
        """Merge source dictionary into target dictionary, handling nested structures and confidence scores."""
        if not source:
            return target
            
        for key, value in source.items():
            if key not in target:
                # If key doesn't exist in target, add it
                target[key] = value
            elif isinstance(value, dict) and isinstance(target[key], dict):
                # If both are dictionaries, merge them recursively
                if 'value' in value and 'confidence' in value:
                    # If it's a value/confidence pair, keep the one with higher confidence
                    if value['confidence'] > target[key]['confidence']:
                        target[key] = value
                else:
                    # Otherwise merge the dictionaries
                    self._merge_chunk_data(target[key], value)
            elif isinstance(value, list) and isinstance(target[key], list):
                # If both are lists, extend the target list
                target[key].extend(value)
            else:
                # For other types, keep the source value
                target[key] = value
                
        return target

    def _merge_results(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Merge source dictionary into target dictionary, handling nested structures."""
        for key, value in source.items():
            if key not in target:
                target[key] = value
            elif isinstance(value, dict) and isinstance(target[key], dict):
                self._merge_results(target[key], value)
            elif isinstance(value, list) and isinstance(target[key], list):
                target[key].extend(value)
            else:
                target[key] = value

    def _create_prompt(self, text: str) -> str:
        """Create a prompt for Ollama to extract owner and joint owner information in a specific JSON format (without the 'prefix' field)."""
        self.logger.info("=== [PROMPT CREATION START] ===")
        self.logger.info(f"Text length: {len(text)} characters")
        self.logger.info(f"Text first 200 chars: {text[:200]}")

        main_prompt = (
            "Analyze the following text and extract key information about the owner and joint owner (if present). "
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
            "  }},\n"
            "  \"jointOwner\": {{\n"
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
            "YOUR RESPONSE MUST BE A SINGLE JSON OBJECT WITH NO ADDITIONAL TEXT OR FORMATTING. DO NOT INCLUDE ANY EXPLANATORY TEXT, MARKDOWN, OR CODE BLOCKS. JUST THE JSON OBJECT. If a field is not found, use null. If there is no joint owner, set all joint owner fields to null."
        )

        system_message = (
            "You are a precise JSON extraction tool. Your task is to extract owner and joint owner information from text and return it in a specific JSON format.\n"
            "IMPORTANT RULES:\n"
            "1. Return ONLY the JSON object, no other text\n"
            "2. If a field is not found, use null\n"
            "3. If there is no joint owner, set all joint owner fields to null\n"
            "4. Do not include any explanatory text\n"
            "5. Do not include any markdown formatting\n"
            "6. Do not include any code blocks\n"
            "7. The response must be a single, valid JSON object\n"
            "8. The prefix field is not needed in the response\n"
            "9. The prefix is always null\n"
            "10. Do not include any extra fields in the response\n"
            "11. All keys in the JSON object must be in camelCase\n"
            "12. Only extract fields listed below — do not add any others.\n"
            "13. Never fabricate or guess information; only extract what is clearly present in the input text.\n"
            "14. Ignore placeholder labels like 'First', 'Last', and 'MI' in field labels such as 'Name: First MI Last'. These are not real values and should not be included in the output.\n"
            "15. Extract only the actual names that appear after these labels.\n"
            "16. Here is the required JSON structure:\n"

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

    def _parse_ollama_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse the Ollama response into a structured format."""
        try:
            # Clean the response text
            cleaned_text = response_text.strip()
            
            # Find the JSON object in the response
            json_start = cleaned_text.find('{')
            json_end = cleaned_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                # Extract just the JSON part
                json_text = cleaned_text[json_start:json_end]
                
                # Remove any markdown formatting
                json_text = json_text.replace('```json', '').replace('```', '')
                
                # Parse the JSON
                data = json.loads(json_text)
                
                # Validate required fields
                if "owner" not in data:
                    self.logger.warning("Missing required field: owner")
                    return None
                    
                # Validate primary applicant fields
                required_fields = ["fullName", "address", "email", "phone"]
                for field in required_fields:
                    if field not in data["owner"]:
                        data["owner"][field] = None
                
                # Validate address fields
                if "address" not in data["owner"]:
                    data["owner"]["address"] = {}
                
                address_fields = ["street", "city", "state", "zip"]
                for field in address_fields:
                    if field not in data["owner"]["address"]:
                        data["owner"]["address"][field] = None
                
                # Add jointOwner if missing
                if "jointOwner" not in data:
                    data["jointOwner"] = {
                        "fullName": None,
                        "address": {
                            "street": None,
                            "city": None,
                            "state": None,
                            "zip": None
                        },
                        "email": None,
                        "phone": None
                    }
                
                # Normalize field values
                for person in ["owner", "jointOwner"]:
                    if person in data:
                        # Normalize name
                        if "fullName" in data[person]:
                            name = data[person]["fullName"]
                            if name:
                                # Remove extra spaces and normalize case
                                name = " ".join(name.split())
                                data[person]["fullName"] = name
                        
                        # Normalize address
                        if "address" in data[person]:
                            for field in ["street", "city", "state", "zip"]:
                                if field in data[person]["address"]:
                                    value = data[person]["address"][field]
                                    if value:
                                        # Clean up address fields
                                        value = " ".join(value.split())
                                        if field == "state":
                                            value = value.upper()
                                        elif field == "zip":
                                            value = value.replace("-", "").strip()
                                        data[person]["address"][field] = value
                        
                        # Normalize email
                        if "email" in data[person]:
                            email = data[person]["email"]
                            if email:
                                email = email.lower().strip()
                                data[person]["email"] = email
                        
                        # Normalize phone
                        if "phone" in data[person]:
                            phone = data[person]["phone"]
                            if phone:
                                # Remove non-numeric characters except for + at start
                                phone = re.sub(r'[^\d+]', '', phone)
                                data[person]["phone"] = phone
                
                return data
            else:
                self.logger.error("No JSON object found in response")
                return None
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing JSON response: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Error processing response: {str(e)}")
            return None

    def _extract_jointOwner_section(self, text: str) -> str:
        """Extract the jointOwner/joint owner section from the text."""
        self.logger.info(f"[DEBUG] Full text for jointOwner section extraction:\n{text}")
        # Updated pattern to match '2.JOINT OWNER INFORMATION ...' up to the next section or end
        match = re.search(r'2\.JOINT OWNER INFORMATION[\s\S]+?(?=\n\d+\.|\nTRUST/|$)', text, re.IGNORECASE)
        jointOwner_section = match.group(0) if match else None
        self.logger.info(f"[DEBUG] Extracted jointOwner section:\n{jointOwner_section}")
        return jointOwner_section

    def _create_jointOwner_prompt(self, section: str) -> str:
        return (
            "Extract the following fields from the text below. Return only valid JSON. Use null for any missing fields.\n"
            "Fields: fullName, address (with street, city, state, zip), phone, email.\n\n"
            f"Text:\n{section}"
        )

    def _extract_jointOwner_info_regex(self, section: str) -> dict:
        """Extract jointOwner/joint owner info using regex as a fallback."""
        self.logger.info(f"[REGEX] jointOwner section for regex extraction:\n{section}")
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
        # Name
        name_match = re.search(r'(?:First MI Last|Name:)[^\n\r]*?([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)', section)
        self.logger.info(f"[REGEX] Name match: {name_match.group(1) if name_match else None}")
        if name_match:
            info['fullName'] = name_match.group(1).strip()
        # Address
        addr_match = re.search(r'(?:Address|Mailing Address)[^\n\r]*?([\d]+[^,\n]+),?\s*([A-Za-z ]+),?\s*([A-Z]{2})\s*(\d{5})', section)
        self.logger.info(f"[REGEX] Address match: {addr_match.groups() if addr_match else None}")
        if addr_match:
            info['address']['street'] = addr_match.group(1).strip()
            info['address']['city'] = addr_match.group(2).strip()
            info['address']['state'] = addr_match.group(3).strip()
            info['address']['zip'] = addr_match.group(4).strip()
        # Phone
        phone_match = re.search(r'Phone[^\d]*(\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{4})', section)
        self.logger.info(f"[REGEX] Phone match: {phone_match.group(1) if phone_match else None}")
        if phone_match:
            info['phone'] = phone_match.group(1).strip()
        # Email
        email_match = re.search(r'Email[^\s:]*[:\s]*([\w\.-]+@[\w\.-]+)', section)
        self.logger.info(f"[REGEX] Email match: {email_match.group(1) if email_match else None}")
        if email_match:
            info['email'] = email_match.group(1).strip()
        return info

    def _extract_owner_info_regex(self, text: str) -> dict:
        """Extract owner info using regex as a fallback."""
        self.logger.info(f"[REGEX] Owner section for regex extraction:\n{text}")
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
        # Name
        name_match = re.search(r'Name: (?:First MI Last )?([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)', text)
        self.logger.info(f"[REGEX] Owner Name match: {name_match.group(1) if name_match else None}")
        if name_match:
            info['fullName'] = name_match.group(1).strip()
        # Address
        addr_match = re.search(r'Residence Address.*?(\d+[^,\n]+),?\s*([A-Za-z ]+),?\s*([A-Z]{2})\s*(\d{5})', text)
        self.logger.info(f"[REGEX] Owner Address match: {addr_match.groups() if addr_match else None}")
        if addr_match:
            info['address']['street'] = addr_match.group(1).strip()
            info['address']['city'] = addr_match.group(2).strip()
            info['address']['state'] = addr_match.group(3).strip()
            info['address']['zip'] = addr_match.group(4).strip()
        # Phone
        phone_match = re.search(r'Phone Number[\D]*(\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{4})', text)
        self.logger.info(f"[REGEX] Owner Phone match: {phone_match.group(1) if phone_match else None}")
        if phone_match:
            info['phone'] = phone_match.group(1).strip()
        # Email
        email_match = re.search(r'Email Address[\s:]*([\w\.-]+@[\w\.-]+)', text)
        self.logger.info(f"[REGEX] Owner Email match: {email_match.group(1) if email_match else None}")
        if email_match:
            info['email'] = email_match.group(1).strip()
        return info

        
    def process_text(self, text: str) -> Dict[str, Any]:
        """Process text with Ollama to extract information."""
        self.logger.info("!!! PROCESS_TEXT CALLED !!!")
        try:
            self.logger.info(f"process_text TEXT: {text[:200]}")
            
            
            # Process each chunk
            all_results = []
            
            try:
                self.logger.info(f"calling make_ollama_request")
                result_raw = self._make_ollama_request(self._create_prompt(text))
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
