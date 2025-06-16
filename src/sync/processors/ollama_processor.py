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

logger = logging.getLogger(__name__)

class OllamaProcessor:
    def __init__(self, model_name: str = "mistral"):
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
                logger.debug("Using cached response")
                return self.response_cache[cache_key]
        return None

    def _cache_response(self, prompt: str, response: str):
        """Cache a response with timestamp."""
        cache_key = self._get_cache_key(prompt)
        self.response_cache[cache_key] = response
        self.cache_timestamps[cache_key] = datetime.now()

    def _check_ollama_server(self) -> None:
        """Check if Ollama server is running and accessible."""
        logger.info("Checking Ollama server availability...")
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=self.server_check_timeout)
            if response.status_code != 200:
                logger.error(f"Ollama server returned status code {response.status_code}")
                logger.error("Please ensure Ollama server is running and accessible")
                sys.exit(1)
            logger.info("Ollama server is running and accessible")
        except requests.exceptions.ConnectionError:
            logger.error("Could not connect to Ollama server")
            logger.error("Please ensure Ollama server is running at http://localhost:11434")
            logger.error("You can start it by running: ollama serve")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error checking Ollama server: {str(e)}")
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
            logger.debug(f"Available models: {model_names}")
            
            if self.model_name not in model_names:
                logger.info(f"Mistral model not found. Pulling model...")
                pull_response = requests.post(
                    f"{self.base_url}/api/pull",
                    json={"name": self.model_name}
                )
                if pull_response.status_code != 200:
                    raise Exception(f"Failed to pull model: {pull_response.text}")
                logger.info("Model pulled successfully")
            else:
                logger.info(f"Model {self.model_name} is available")
                
        except Exception as e:
            logger.error(f"Error checking model availability: {str(e)}")
            raise

    def _extract_text_from_file(self, file_path: str) -> str:
        """Extract text from a PDF file."""
        try:
            if not file_path.lower().endswith('.pdf'):
                logger.warning(f"File is not a PDF: {file_path}")
                return ""
                
            with pdfplumber.open(file_path) as pdf:
                # Process only the first page
                try:
                    page = pdf.pages[0]
                    text = page.extract_text()
                    if text:
                        # Clean up the text
                        text = re.sub(r'\n+', ' ', text)  # Replace multiple newlines with space
                        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
                        text = text.strip()
                        return text
                except Exception as e:
                    logger.warning(f"Error processing first page: {str(e)}")
                    return ""
                
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            return ""

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
            logger.warning(f"Too many chunks ({len(chunks)}), limiting to first 10")
            chunks = chunks[:10]
            
        return chunks

    def _process_chunk(self, chunk: str) -> Optional[Dict[str, Any]]:
        """Process a chunk of text using the Ollama model."""
        try:
            # Create prompt for the chunk
            prompt = self._create_prompt(chunk)
            
            # Make request to Ollama
            response = self._make_ollama_request(prompt)
            
            # Parse and validate response
            result = self._parse_ollama_response(response)
            if result:
                return result
                
            return None
            
        except Exception as e:
            logger.error(f"Error processing chunk: {str(e)}")
            return None

    def _process_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Process a single file and extract information using Ollama with improved parallel processing."""
        try:
            logger.info(f"Processing file: {file_path}")
            
            # Extract text from file
            text = self._extract_text_from_file(str(file_path))
            if not text:
                return None
                
            # Split text into chunks
            chunks = self._split_text_into_chunks(text)
            logger.info(f"Split text into {len(chunks)} chunks")
            logger.debug(f"Chunk sizes: {[len(chunk) for chunk in chunks]}")
            
            # Process chunks in parallel using ThreadPoolExecutor
            all_data = {}
            max_workers = min(4, len(chunks))  # Limit parallel processing
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all chunk processing tasks
                future_to_chunk = {
                    executor.submit(self._process_chunk, chunk): i 
                    for i, chunk in enumerate(chunks)
                }
                
                # Process results as they complete
                for future in as_completed(future_to_chunk):
                    try:
                        chunk_data = future.result(timeout=self.base_timeout)
                        if chunk_data:
                            all_data = self._merge_chunk_data(all_data, chunk_data)
                    except TimeoutError:
                        logger.error(f"Chunk processing timed out after {self.base_timeout} seconds")
                    except Exception as e:
                        logger.error(f"Error processing chunk: {str(e)}")
                        
            return all_data
            
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            return None

    def _make_ollama_request(self, prompt: str) -> str:
        """Make a request to the Ollama API with improved error handling and retry logic."""
        session = requests.Session()
        max_retries = 5
        base_timeout = 180  # 3 minutes base timeout
        
        for attempt in range(max_retries):
            try:
                current_timeout = base_timeout * (2 ** attempt)  # Exponential backoff
                
                # Create a system message to guide the model
                system_message = """You are a precise information extraction assistant. Your task is to extract ONLY personal information from text. You must:
1. Extract ONLY information that is EXPLICITLY stated in the text
2. DO NOT make assumptions or inferences
3. DO NOT combine or modify information
4. Use null for any information not explicitly found
5. Return a complete, valid JSON object
6. Follow the exact structure provided
7. Never add explanations or markdown
8. Never add fields not in the structure
9. Never include monetary amounts, policy numbers, dates, or status information
10. If you are not 100% certain about any information, use null
11. For names, extract ONLY the actual name as written in the text, do not add titles or prefixes
12. For names, do not combine or modify parts of the name
13. For names, if you see a full name like 'Martin Amaran', use exactly that, do not add or remove parts"""

                response = session.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": "mistral",
                        "prompt": f"{system_message}\n\n{prompt}",
                        "stream": False,
                        "options": {
                            "temperature": 0.0,  # Zero temperature for deterministic output
                            "top_k": 1,  # Only most likely token
                            "top_p": 0.1,  # Very focused sampling
                            "repeat_penalty": 1.1,
                            "num_ctx": 4096,  # Reduced context window
                            "num_predict": 1024,  # Reduced response length
                            "stop": ["}"],  # Stop at JSON object completion
                        }
                    },
                    timeout=current_timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if "response" in result:
                        return result["response"]
                    else:
                        logger.warning(f"Unexpected response format: {result}")
                        continue
                else:
                    logger.warning(f"Request failed with status code {response.status_code}")
                    continue
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Request timed out after {current_timeout} seconds")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                raise
                
        raise Exception("Failed to get valid response after all retries")

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
        """Create a prompt for the Ollama model."""
        return f"""Extract ONLY personal information that is EXPLICITLY stated in the text. Use this exact structure:

{{
    "primaryApplicant": {{
        "fullName": "string",  // Full name as written in the text, e.g. "Martin Amaran"
        "address": {{
            "street": "string",  // Street address as written
            "city": "string",    // City name as written
            "state": "string",   // State abbreviation or name as written
            "zip": "string"      // ZIP code as written
        }},
        "email": "string",      // Email address as written
        "phone": "string"       // Phone number as written
    }},
    "spouse": {{
        "fullName": "string",  // Spouse's full name as written, look for "Spouse:", "Co-Applicant:", "JOINT OWNER", or similar labels
        "address": {{
            "street": "string",  // Spouse's street address if different from primary applicant
            "city": "string",    // Spouse's city if different from primary applicant
            "state": "string",   // Spouse's state if different from primary applicant
            "zip": "string"      // Spouse's ZIP if different from primary applicant
        }},
        "email": "string",      // Spouse's email if provided
        "phone": "string"       // Spouse's phone if provided
    }}
}}

Rules:
1. Extract ONLY information that is EXPLICITLY stated in the text
2. DO NOT make assumptions or inferences
3. DO NOT combine or modify information
4. Use null for any information not explicitly found
5. DO NOT include any other information
6. DO NOT add any fields not in the structure above
7. If you are not 100% certain about any information, use null
8. Look for information in the first page only
9. DO NOT extract information from headers or footers
10. DO NOT extract information from form fields or checkboxes
11. For names, extract ONLY the actual name as written in the text
12. For names, do not add titles, prefixes, or suffixes
13. For names, do not combine or modify parts of the name
14. For names, if you see a full name like 'Martin Amaran', use exactly that
15. For spouse information, look for sections labeled with:
    - "Spouse:"
    - "Co-Applicant:"
    - "Joint Applicant:"
    - "Secondary Applicant:"
    - "Additional Applicant:"
    - "JOINT OWNER"
    - "Joint Owner"
16. If spouse information is found, extract it even if it's the same as primary applicant
17. If no spouse information is found, use null for all spouse fields

Text to process:
{text}"""

    def _parse_ollama_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse the Ollama response into a structured format."""
        try:
            # Clean the response text
            cleaned_text = response_text.strip()
            
            # Remove any markdown formatting
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            
            # Remove any explanatory text before or after the JSON
            json_start = cleaned_text.find("{")
            json_end = cleaned_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                cleaned_text = cleaned_text[json_start:json_end]
            
            # Check if the JSON is complete
            if cleaned_text.count("{") != cleaned_text.count("}"):
                # Try to complete the JSON structure
                missing_braces = cleaned_text.count("{") - cleaned_text.count("}")
                cleaned_text = cleaned_text + "}" * missing_braces
            
            # Parse the JSON
            data = json.loads(cleaned_text)
            
            # Validate required fields
            if "primaryApplicant" not in data:
                logger.warning("Missing required field: primaryApplicant")
                return None
                
            # Validate primary applicant fields
            required_fields = ["fullName", "address", "email", "phone"]
            for field in required_fields:
                if field not in data["primaryApplicant"]:
                    data["primaryApplicant"][field] = None
            
            # Validate address fields
            if "address" not in data["primaryApplicant"]:
                data["primaryApplicant"]["address"] = {}
            
            address_fields = ["street", "city", "state", "zip"]
            for field in address_fields:
                if field not in data["primaryApplicant"]["address"]:
                    data["primaryApplicant"]["address"][field] = None
            
            # Add spouse if missing
            if "spouse" not in data:
                data["spouse"] = {
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
            for person in ["primaryApplicant", "spouse"]:
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
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error processing response: {str(e)}")
            return None 