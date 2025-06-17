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

class LMStudioProcessor(BaseProcessor):
    def __init__(self, model_name: str = "local-model", base_url: str = "http://localhost:1234/v1"):
        """Initialize the LM Studio processor."""
        super().__init__(model_name, base_url)
        self._check_server_availability()
        self.prompt_creator = PromptCreator()

    def _check_server_availability(self) -> None:
        """Check if the LM Studio server is available."""
        try:
            response = requests.get(f"{self.base_url}/health")
            if response.status_code == 200:
                self.logger.info("Successfully connected to LM Studio server")
            else:
                raise Exception(f"Server returned status code {response.status_code}")
        except Exception as e:
            self.logger.error(f"Could not connect to LM Studio server: {str(e)}")
            self.logger.error("Please ensure the LM Studio server is running at http://localhost:1234")
            raise

    def _make_request(self, prompt: str, temperature: float = 0.0) -> Dict:
        """Make a request to the LM Studio API."""
        cached_response = self._get_cached_response(prompt)
        if cached_response:
            return cached_response

        try:
            request_data = self.prompt_creator.create_chat_prompt(prompt, "lm_studio")
            self._log_curl_command(request_data)

            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                raise Exception(f"API request failed with status code {response.status_code}")

            result = response.json()
            if "choices" not in result or not result["choices"]:
                raise Exception("No choices in response")

            response_text = result["choices"][0]["message"]["content"]
            self._cache_response(prompt, {"response": response_text})
            return {"response": response_text}

        except Exception as e:
            self.logger.error(f"Error making request to LM Studio: {str(e)}")
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