import json
import logging
import time
from typing import Dict, Any, Optional
import requests
from pathlib import Path
import PyPDF2
import io
import sys

logger = logging.getLogger(__name__)

class OllamaProcessor:
    def __init__(self, base_url: str = "http://localhost:11434", max_retries: int = 3, retry_delay: float = 1.0):
        self.base_url = base_url
        self.model = "mistral"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._check_ollama_server()
        self._check_model_availability()

    def _check_ollama_server(self) -> None:
        """Check if Ollama server is running and accessible."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                logger.error(f"Ollama server returned status code {response.status_code}")
                logger.error("Please ensure Ollama server is running and accessible")
                sys.exit(1)
        except requests.exceptions.ConnectionError:
            logger.error("Could not connect to Ollama server")
            logger.error("Please ensure Ollama server is running at http://localhost:11434")
            logger.error("You can start it by running: ollama serve")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error checking Ollama server: {str(e)}")
            sys.exit(1)

    def _check_model_availability(self) -> None:
        """Check if the Mistral model is available and pull it if needed."""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model.get('name') for model in models]
                
                if self.model not in model_names:
                    logger.info(f"Mistral model not found. Pulling model...")
                    pull_response = requests.post(
                        f"{self.base_url}/api/pull",
                        json={"name": self.model}
                    )
                    if pull_response.status_code != 200:
                        logger.error(f"Failed to pull Mistral model: {pull_response.text}")
                        logger.error("Please pull the model manually by running: ollama pull mistral")
                        sys.exit(1)
                    logger.info("Successfully pulled Mistral model")
        except Exception as e:
            logger.error(f"Error checking model availability: {str(e)}")
            logger.error("Please ensure the Mistral model is available by running: ollama pull mistral")
            sys.exit(1)

    def _extract_text_from_file(self, file_path: Path) -> Optional[str]:
        """Extract text from a file, handling both PDF and text files."""
        try:
            if file_path.suffix.lower() == '.pdf':
                with open(file_path, 'rb') as pdf_file:
                    reader = PyPDF2.PdfReader(pdf_file)
                    content = ''
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            content += page_text + '\n'
                return content
            else:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            return None

    def _chunk_text(self, text: str, max_chunk_size: int = 2000) -> list[str]:
        """Split text into smaller chunks to avoid truncation."""
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0
        
        for word in words:
            word_size = len(word) + 1  # +1 for space
            if current_size + word_size > max_chunk_size:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_size = word_size
            else:
                current_chunk.append(word)
                current_size += word_size
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks

    def _make_ollama_request(self, prompt: str) -> Optional[str]:
        """
        Make a request to Ollama API with retries.
        
        Args:
            prompt (str): The prompt to send to Ollama
            
        Returns:
            Optional[str]: The response text if successful, None otherwise
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,  # Lower temperature for more consistent results
                            "num_predict": 1024,  # Maximum tokens to generate
                        }
                    },
                    timeout=60  # Increased timeout for larger prompts
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get('response', '')
                elif response.status_code == 404:
                    logger.error(f"Model '{self.model}' not found")
                    logger.error("Please pull the model by running: ollama pull mistral")
                    return None
                else:
                    logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed with status {response.status_code}")
                    
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed with error: {str(e)}")
                if attempt == self.max_retries - 1:
                    logger.error("Failed to connect to Ollama server after all retries")
                    logger.error("Please ensure Ollama server is running at http://localhost:11434")
                    logger.error("You can start it by running: ollama serve")
            
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
        
        return None

    def _process_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Process a file using Ollama's Mistral model to extract structured form data.
        
        Args:
            file_path (Path): Path to the file containing the form data
            
        Returns:
            Dict[str, Any]: Structured form data extracted from the text
        """
        try:
            # Extract text from file
            content = self._extract_text_from_file(file_path)
            if not content:
                logger.error(f"Failed to extract text from {file_path}")
                return {}

            # Split content into chunks if it's too large
            chunks = self._chunk_text(content)
            all_results = []

            for chunk in chunks:
                # Prepare the prompt for Mistral
                prompt = f"""You are a form data extraction expert. Extract and structure the following form data into a JSON object.
                Follow these rules:
                1. Identify all key fields and their values
                2. Use null for missing or unclear values
                3. Clean and normalize the extracted values
                4. Group related fields into nested objects when appropriate
                5. Return ONLY valid JSON, no additional text or explanation
                6. Use consistent field names (camelCase)
                7. Include confidence scores (0-1) for each extracted field
                
                Example output format:
                {{
                    "personalInfo": {{
                        "name": {{
                            "value": "John Doe",
                            "confidence": 0.95
                        }},
                        "email": {{
                            "value": "john@example.com",
                            "confidence": 0.98
                        }}
                    }},
                    "address": {{
                        "street": {{
                            "value": "123 Main St",
                            "confidence": 0.9
                        }}
                    }}
                }}
                
                Form content:
                {chunk}"""

                # Get response from Ollama
                extracted_text = self._make_ollama_request(prompt)
                
                if not extracted_text:
                    continue

                # Parse the JSON response
                try:
                    structured_data = json.loads(extracted_text)
                    all_results.append(structured_data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Ollama response as JSON: {e}")
                    # Try to clean the response if it contains non-JSON text
                    try:
                        # Find the first '{' and last '}'
                        start = extracted_text.find('{')
                        end = extracted_text.rfind('}') + 1
                        if start >= 0 and end > start:
                            cleaned_text = extracted_text[start:end]
                            structured_data = json.loads(cleaned_text)
                            all_results.append(structured_data)
                    except:
                        pass

            # Merge all results
            merged_result = {}
            for result in all_results:
                self._merge_results(merged_result, result)

            return merged_result

        except Exception as e:
            logger.error(f"Error processing file with Ollama: {str(e)}")
            return {}

    def _merge_results(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Merge source dictionary into target dictionary, handling nested structures."""
        for key, value in source.items():
            if key in target:
                if isinstance(value, dict) and isinstance(target[key], dict):
                    self._merge_results(target[key], value)
                elif isinstance(value, dict) and "value" in value and "confidence" in value:
                    # If both are value/confidence pairs, keep the one with higher confidence
                    if value["confidence"] > target[key]["confidence"]:
                        target[key] = value
            else:
                target[key] = value 