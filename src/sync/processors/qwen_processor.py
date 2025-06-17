import json
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
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
import torch
from transformers import AutoTokenizer, AutoModelForVision2Seq
from PIL import Image
import base64
from io import BytesIO

class QwenProcessor:
    def __init__(self, model_name: str = "Qwen/Qwen2-VL-7B-Instruct"):
        """Initialize the Qwen processor."""
        self.model_name = model_name
        self.max_chunk_size = 2000
        self.max_retries = 5
        self.retry_delay = 1
        self.base_timeout = 180
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

        self._initialize_cache()
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the Qwen model and tokenizer."""
        try:
            self.logger.info("Initializing Qwen model and tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
            self.model = AutoModelForVision2Seq.from_pretrained(
                self.model_name,
                device_map="auto",
                trust_remote_code=True,
                torch_dtype=torch.float16
            )
            self.logger.info("Model and tokenizer initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing model: {str(e)}")
            raise

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
                        text = page.extract_text()

                        if not text or len(text.strip()) < 50:
                            self.logger.info(f"Page {i+1}: Normal text extraction yielded minimal text, trying OCR...")
                            text = page.extract_text(x_tolerance=3, y_tolerance=3)
                            if text:
                                text = self._clean_ocr_text(text)

                        if text:
                            text = re.sub(r'_(\w)', r' \1', text)
                            text = text.replace('_', '')
                            text = re.sub(r'\s+', ' ', text).strip()
                            all_text.append(text)
                            self.logger.info(f"\n\033[92m=== BEGIN EXTRACTED TEXT FOR QWEN PAGE {i+1} ===\033[0m")
                            self.logger.info(text)
                            self.logger.info(f"\n\033[92m=== END OF EXTRACTED TEXT FOR QWEN PAGE {i+1} ===\033[0m")
                        else:
                            self.logger.info(f"Page {i+1}: No text extracted.")
                    except Exception as e:
                        self.logger.error(f"Error processing page {i+1}: {str(e)}")
                        continue

                return "\n\n".join(all_text)

        except Exception as e:
            self.logger.error(f"Error extracting text from file: {str(e)}")
            return ""

    def _clean_ocr_text(self, text: str) -> str:
        """Clean OCR text by removing common artifacts."""
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters that might be OCR artifacts
        text = re.sub(r'[^\w\s.,;:!?()-]', '', text)
        return text.strip()

    def _split_text_into_chunks(self, text: str) -> List[str]:
        """Split text into chunks of maximum size with improved handling."""
        if not text:
            return []
            
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_size = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            if len(paragraph) > self.max_chunk_size:
                sentences = paragraph.split('. ')
                for sentence in sentences:
                    if current_size + len(sentence) > self.max_chunk_size:
                        if current_chunk:
                            chunks.append(' '.join(current_chunk))
                            current_chunk = []
                            current_size = 0
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
            
        if len(chunks) > 10:
            self.logger.warning(f"Too many chunks ({len(chunks)}), limiting to first 10")
            chunks = chunks[:10]
            
        return chunks

    def _create_prompt(self, text: str) -> str:
        """Create a prompt for Qwen to extract owner information in a specific JSON format."""
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
        except Exception as e:
            self.logger.error(f"Error formatting prompt: {str(e)}")
            raise

    def _make_model_request(self, prompt: str, max_length: int = 2048) -> Dict:
        """Make a request to the Qwen model with retries and error handling."""
        self.logger.info("=== [QWEN REQUEST START] ===")
        self.logger.info(f"Prompt length: {len(prompt)} characters")
        
        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"\n=== [ATTEMPT {attempt + 1}/{max_retries}] ===")
                
                # Prepare the input
                inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
                
                # Generate response
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_length=max_length,
                        num_return_sequences=1,
                        temperature=0.7,
                        top_p=0.9,
                        do_sample=True
                    )
                
                # Decode the response
                response_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                
                # Extract JSON from response
                json_text, error = self._extract_json_from_response(response_text)
                if error:
                    raise ValueError(error)
                
                # Parse and validate JSON
                result = json.loads(json_text)
                if not self._validate_json_structure(result):
                    raise ValueError("Invalid JSON structure")
                
                self.logger.info("=== [QWEN REQUEST SUCCESS] ===")
                return result
                
            except Exception as e:
                self.logger.error(f"Error on attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    self.logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    self.logger.error("Max retries reached")
                    raise
        
        self.logger.error("All retry attempts failed")
        raise Exception("Failed to get valid response from Qwen after all retries")

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

    def _validate_json_structure(self, json_data: dict) -> bool:
        """Validate JSON structure and required fields."""
        try:
            # Validate it's an object
            if not isinstance(json_data, dict):
                return False
            
            # Validate required fields
            required_fields = ["owner"]
            if not all(field in json_data for field in required_fields):
                return False
            
            # Validate owner fields
            owner_fields = [
                "firstName", "middleInitial", "lastName", "SSN",
                "dateOfBirth", "gender", "mailingAddressCity",
                "mailingAddressState", "mailingAddressZip",
                "residentialAddressCity", "residentialAddressState",
                "residentialAddressZip", "phoneNumber", "emailAddress"
            ]
            
            if not all(field in json_data["owner"] for field in owner_fields):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating JSON structure: {str(e)}")
            return False

    def process_text(self, text: str) -> Dict[str, Any]:
        """Process text with Qwen to extract information."""
        self.logger.info("!!! PROCESS_TEXT CALLED !!!")
        try:
            self.logger.info(f"process_text TEXT: {text[:200]}")
            
            # Check cache first
            cached_response = self._get_cached_response(text)
            if cached_response:
                return cached_response
            
            # Process the text
            try:
                self.logger.info("Calling make_model_request")
                result = self._make_model_request(self._create_prompt(text))
                self.logger.info(f"Result: {result}")
                
                # Cache the result
                self._cache_response(text, result)
                
                return result
                
            except Exception as e:
                self.logger.error(f"Failed to process text: {str(e)}")
                return {}
                
        except Exception as e:
            self.logger.error(f"Error in process_text: {str(e)}")
            return {}

    def process_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Process a single file and extract information using Qwen."""
        try:
            self.logger.info(f"Processing file: {file_path}")
            
            # Extract text from file
            text = self._extract_text_from_file(str(file_path))
            if not text:
                return None
                
            # Process the text
            return self.process_text(text)
                
        except Exception as e:
            self.logger.error(f"Error processing file: {str(e)}")
            return None 