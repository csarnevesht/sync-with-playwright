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
                            text = page.extract_text(x_tolerance=3, y_tolerance=3)
                            if text:
                                text = self._clean_ocr_text(text)
                        if text:
                            all_text.append(text)
                    except Exception as e:
                        self.logger.error(f"Error extracting text from page {i+1}: {str(e)}")
                        continue
                return "\n\n".join(all_text)
        except Exception as e:
            self.logger.error(f"Error extracting text from file: {str(e)}")
            return ""

    def _clean_ocr_text(self, text: str) -> str:
        """Common OCR text cleaning."""
        text = re.sub(r'[^\w\s.,;:!?@#$%^&*()\-_=+\[\]{}|\\/"\'<>]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _extract_owner_info_regex(self, text: str) -> Dict[str, Any]:
        """Common regex-based owner information extraction."""
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
        
        # Extract phone and email
        phone_match = re.search(r'Phone\s*:\s*(\d{3}[-.]?\d{3}[-.]?\d{4})', text)
        if phone_match:
            info['phone'] = phone_match.group(1)
        
        email_match = re.search(r'Email\s*:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text)
        if email_match:
            info['email'] = email_match.group(1)
        
        return info

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

    @abstractmethod
    def process_text(self, text: str) -> Dict[str, Any]:
        """Process text to extract information."""
        pass 