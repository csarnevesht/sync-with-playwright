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

    def list_available_models(self) -> List[Dict[str, Any]]:
        """List all available models in LM Studio.
        
        Returns:
            List of model information dictionaries
        """
        try:
            response = requests.get(f"{self.base_url}/models")
            if response.status_code == 200:
                models = response.json()
                self.logger.info(f"Found {len(models)} available models")
                return models
            else:
                self.logger.error(f"Failed to list models: {response.status_code}")
                return []
        except Exception as e:
            self.logger.error(f"Error listing models: {str(e)}")
            return []

    def load_model(self, model_id: str) -> bool:
        """Load a specific model in LM Studio.
        
        Args:
            model_id: The ID of the model to load
            
        Returns:
            bool: True if model was loaded successfully, False otherwise
        """
        try:
            self.logger.info(f"Loading model: {model_id}")
            
            # First, check if the model is already loaded
            current_models = self.list_available_models()
            for model in current_models:
                if model.get('id') == model_id and model.get('object') == 'model':
                    self.logger.info(f"Model {model_id} is already loaded")
                    return True
            
            # Load the model
            response = requests.post(
                f"{self.base_url}/models/load",
                json={"model_id": model_id},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                self.logger.info(f"Successfully loaded model: {model_id}")
                return True
            else:
                self.logger.error(f"Failed to load model {model_id}: {response.status_code}")
                try:
                    error_response = response.json()
                    self.logger.error(f"Error response: {json.dumps(error_response, indent=2)}")
                except:
                    self.logger.error(f"Raw error response: {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error loading model {model_id}: {str(e)}")
            return False

    def unload_model(self, model_id: str) -> bool:
        """Unload a specific model in LM Studio.
        
        Args:
            model_id: The ID of the model to unload
            
        Returns:
            bool: True if model was unloaded successfully, False otherwise
        """
        try:
            self.logger.info(f"Unloading model: {model_id}")
            
            response = requests.post(
                f"{self.base_url}/models/unload",
                json={"model_id": model_id},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                self.logger.info(f"Successfully unloaded model: {model_id}")
                return True
            else:
                self.logger.error(f"Failed to unload model {model_id}: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error unloading model {model_id}: {str(e)}")
            return False

    def get_loaded_model(self) -> Optional[Dict[str, Any]]:
        """Get information about the currently loaded model.
        
        Returns:
            Model information dictionary or None if no model is loaded
        """
        try:
            models = self.list_available_models()
            for model in models:
                if model.get('object') == 'model':
                    return model
            return None
        except Exception as e:
            self.logger.error(f"Error getting loaded model: {str(e)}")
            return None

    def auto_load_model(self, preferred_model_id: str = None) -> bool:
        """Automatically load a model, trying preferred model first, then any available model.
        
        Args:
            preferred_model_id: The preferred model ID to load
            
        Returns:
            bool: True if a model was loaded successfully, False otherwise
        """
        try:
            # First, check if any model is already loaded
            current_model = self.get_loaded_model()
            if current_model:
                self.logger.info(f"Model already loaded: {current_model.get('id')}")
                return True
            
            # Get available models
            available_models = self.list_available_models()
            if not available_models:
                self.logger.error("No models available in LM Studio")
                return False
            
            # Try to load preferred model first
            if preferred_model_id:
                for model in available_models:
                    if model.get('id') == preferred_model_id:
                        if self.load_model(preferred_model_id):
                            return True
                        break
            
            # If preferred model failed or not found, try the first available model
            for model in available_models:
                model_id = model.get('id')
                if model_id and model.get('object') == 'model':
                    self.logger.info(f"Trying to load model: {model_id}")
                    if self.load_model(model_id):
                        return True
            
            self.logger.error("Failed to load any model")
            return False
            
        except Exception as e:
            self.logger.error(f"Error in auto_load_model: {str(e)}")
            return False

    def _truncate_prompt_for_context(self, prompt: str, max_tokens: int = 3500) -> str:
        """Truncate prompt to fit within model's context window."""
        # Rough estimate: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        
        if len(prompt) <= max_chars:
            return prompt
        
        self.logger.warning(f"Prompt too long ({len(prompt)} chars), truncating to {max_chars} chars")
        
        # Find the text to analyze section and truncate from there
        text_marker = "Text to analyze:"
        if text_marker in prompt:
            # Split at the text marker
            prompt_parts = prompt.split(text_marker)
            if len(prompt_parts) >= 2:
                instructions = prompt_parts[0] + text_marker
                text_to_analyze = prompt_parts[1]
                
                # Calculate how much text we can keep
                available_chars = max_chars - len(instructions)
                
                if available_chars > 0:
                    # Truncate the text to analyze part
                    truncated_text = text_to_analyze[:available_chars]
                    # Try to truncate at a word boundary
                    last_space = truncated_text.rfind(' ')
                    if last_space > available_chars * 0.8:  # If we can find a space in the last 20%
                        truncated_text = truncated_text[:last_space]
                    
                    final_prompt = instructions + truncated_text
                    self.logger.info(f"Truncated prompt from {len(prompt)} to {len(final_prompt)} characters")
                    return final_prompt
        
        # Fallback: simple truncation
        truncated = prompt[:max_chars]
        # Try to truncate at a word boundary
        last_space = truncated.rfind(' ')
        if last_space > max_chars * 0.8:
            truncated = truncated[:last_space]
        
        self.logger.info(f"Fallback truncation: {len(prompt)} to {len(truncated)} characters")
        return truncated

    def _make_request(self, prompt: str, temperature: float = 0.0) -> Dict:
        """Make a request to the LM Studio API."""
        cached_response = self._get_cached_response(prompt)
        if cached_response:
            return cached_response

        try:
            prompt = self._truncate_prompt_for_context(prompt)
            request_data = self.prompt_creator.create_chat_prompt(prompt, "lm_studio")
            # self._log_curl_command(request_data)
            
            # Log request data for debugging
            self.logger.info(f"Request data being sent to LM Studio:")
            self.logger.info(f"URL: {self.base_url}/chat/completions")
            self.logger.info(f"Request data: {json.dumps(request_data, indent=2)}")

            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                # Log detailed error information
                self.logger.error(f"API request failed with status code {response.status_code}")
                self.logger.error(f"Response headers: {dict(response.headers)}")
                try:
                    error_response = response.json()
                    self.logger.error(f"Error response body: {json.dumps(error_response, indent=2)}")
                    
                    # Check if this is the "no models loaded" error
                    if (response.status_code == 404 and 
                        error_response.get('error', {}).get('code') == 'model_not_found' and
                        'No models loaded' in error_response.get('error', {}).get('message', '')):
                        
                        self.logger.warning("LM Studio is running but no models are loaded. Attempting to auto-load a model...")
                        
                        # Try to auto-load a model
                        if self.auto_load_model():
                            self.logger.info("Successfully loaded a model, retrying request...")
                            # Retry the request
                            response = requests.post(
                                f"{self.base_url}/chat/completions",
                                json=request_data,
                                headers={"Content-Type": "application/json"}
                            )
                            
                            if response.status_code == 200:
                                result = response.json()
                                if "choices" not in result or not result["choices"]:
                                    raise Exception("No choices in response")
                                
                                response_text = result["choices"][0]["message"]["content"]
                                self._cache_response(prompt, {"response": response_text})
                                return {"response": response_text}
                            else:
                                self.logger.error(f"Request still failed after loading model: {response.status_code}")
                        
                        self.logger.warning("Falling back to basic text extraction without AI processing.")
                        
                        # Return a fallback response that indicates no AI processing was done
                        return {
                            "response": "No AI processing available - LM Studio has no models loaded. Please load a model in LM Studio to enable AI-powered text extraction.",
                            "fallback": True,
                            "error": "no_models_loaded"
                        }
                        
                except Exception as e:
                    self.logger.error(f"Could not parse error response as JSON: {str(e)}")
                    self.logger.error(f"Raw error response: {response.text}")
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


    