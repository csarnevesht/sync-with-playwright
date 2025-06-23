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
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig, AutoModelForVision2Seq
from transformers import Qwen2VLConfig, Qwen2VLForCausalLM, Qwen2VLProcessor
from PIL import Image
import base64
from io import BytesIO
from .prompt_creator import PromptCreator
import numpy as np
from .base_processor import BaseProcessor, SetEncoder

class QwenProcessor(BaseProcessor):
    def __init__(self, model_name: str = "Qwen/Qwen2-VL", base_url: str = None, log_dir: str = None):
        """Initialize the Qwen processor."""
        super().__init__(model_name, base_url, log_dir)
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
        # Clear cache to ensure updated prompts take effect
        self.clear_cache()

    def _initialize_model(self) -> None:
        """Initialize the Qwen model and tokenizer."""
        try:
            self.logger.info("Initializing Qwen model...")
            self.model = AutoModelForVision2Seq.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            self.logger.info("Successfully initialized Qwen model")
        except Exception as e:
            self.logger.error(f"Failed to initialize Qwen model: {str(e)}")
            raise

    def _check_server_availability(self) -> None:
        """Check if the model is available."""
        try:
            if not hasattr(self, 'model') or not hasattr(self, 'tokenizer'):
                raise Exception("Model or tokenizer not initialized")
            self.logger.info("Successfully verified Qwen model availability")
        except Exception as e:
            self.logger.error(f"Could not verify Qwen model availability: {str(e)}")
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


    def _make_request(self, prompt: str, temperature: float = 0.0) -> Dict:
        """Make a request to the Qwen model."""
        cached_response = self._get_cached_response(prompt)
        if cached_response:
            return cached_response

        try:
            # Prepare inputs
            inputs = self.tokenizer(prompt, return_tensors="pt")
            
            # Generate response
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=temperature,
                do_sample=temperature > 0
            )
            
            # Decode response
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            self._cache_response(prompt, {"response": response})
            return {"response": response}
            
        except Exception as e:
            self.logger.error(f"Error generating response: {str(e)}")
            raise

    

   

   