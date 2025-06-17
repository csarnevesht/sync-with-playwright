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
            # self._log_curl_command(request_data)

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


    