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
    def __init__(self, base_url: str = "http://localhost:11434", max_retries: int = 5, retry_delay: float = 1.0):
        self.base_url = base_url
        self.model = "mistral"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        logger.info(f"Initializing OllamaProcessor with model: {self.model}")
        self._check_ollama_server()
        self._check_model_availability()

    def _check_ollama_server(self) -> None:
        """Check if Ollama server is running and accessible."""
        logger.info("Checking Ollama server availability...")
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
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
        """Check if the Mistral model is available and pull it if needed."""
        logger.info("Checking Mistral model availability...")
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model.get('name') for model in models]
                logger.debug(f"Available models: {model_names}")
                
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
                else:
                    logger.info("Mistral model is already available")
        except Exception as e:
            logger.error(f"Error checking model availability: {str(e)}")
            logger.error("Please ensure the Mistral model is available by running: ollama pull mistral")
            sys.exit(1)

    def _extract_text_from_file(self, file_path: Path) -> Optional[str]:
        """Extract text from a file, handling both PDF and text files."""
        logger.info(f"Extracting text from file: {file_path}")
        try:
            if file_path.suffix.lower() == '.pdf':
                logger.debug("Processing PDF file")
                with open(file_path, 'rb') as pdf_file:
                    reader = PyPDF2.PdfReader(pdf_file)
                    content = ''
                    total_pages = len(reader.pages)
                    logger.debug(f"PDF has {total_pages} pages")
                    # Limit to first 1 pages
                    pages_to_process = min(1, total_pages)
                    logger.info(f"Processing first {pages_to_process} pages out of {total_pages} total pages")
                    for i, page in enumerate(reader.pages[:pages_to_process], 1):
                        page_text = page.extract_text()
                        if page_text:
                            content += page_text + '\n'
                        logger.debug(f"Processed page {i}/{pages_to_process}")
                logger.info(f"Successfully extracted {len(content)} characters from PDF")
                return content
            else:
                logger.debug("Processing text file")
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                logger.info(f"Successfully read {len(content)} characters from text file")
                return content
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            return None

    def _chunk_text(self, text: str, max_chunk_size: int = 500) -> list[str]:
        """Split text into smaller chunks to avoid truncation."""
        logger.info(f"Splitting text into chunks (max size: {max_chunk_size} characters)")
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
        
        logger.info(f"Split text into {len(chunks)} chunks")
        logger.debug(f"Chunk sizes: {[len(chunk) for chunk in chunks]}")
        return chunks

    def _make_ollama_request(self, prompt: str) -> Optional[str]:
        """
        Make a request to Ollama API with retries.
        
        Args:
            prompt (str): The prompt to send to Ollama
            
        Returns:
            Optional[str]: The response text if successful, None otherwise
        """
        logger.info(f"Making Ollama request (prompt length: {len(prompt)} characters)")
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Attempt {attempt + 1}/{self.max_retries}")
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,  # Lower temperature for more consistent results
                            "num_predict": 1024,  # Increased to ensure complete JSON
                            "num_ctx": 4096,  # Increased context window
                            "num_thread": 4,  # Number of CPU threads to use
                            "repeat_penalty": 1.1,  # Penalty for repeating tokens
                            "top_k": 40,  # Number of tokens to consider for each prediction
                            "top_p": 0.9,  # Nucleus sampling parameter
                            "stop": ["\n\n", "```"],  # Stop at double newline or code block end
                        }
                    },
                    timeout=60  # Increased timeout for larger responses
                )
                
                if response.status_code == 200:
                    result = response.json()
                    response_text = result.get('response', '')
                    logger.info(f"Successfully got response (length: {len(response_text)} characters)")
                    logger.debug(f"Raw response content: {response_text[:200]}...")  # Log first 200 chars
                    
                    # Try to clean and validate the JSON response
                    try:
                        # Find the first '{' and last '}'
                        start = response_text.find('{')
                        end = response_text.rfind('}') + 1
                        if start >= 0 and end > start:
                            json_str = response_text[start:end]
                            # Validate JSON by parsing and re-encoding
                            json_obj = json.loads(json_str)
                            cleaned_json = json.dumps(json_obj)
                            logger.debug(f"Successfully cleaned and validated JSON")
                            return cleaned_json
                        else:
                            logger.warning("No valid JSON structure found in response")
                            logger.debug(f"Raw response: {response_text}")
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse response as JSON: {e}")
                        logger.debug(f"Raw response: {response_text}")
                    
                    return response_text
                elif response.status_code == 404:
                    logger.error(f"Model '{self.model}' not found")
                    logger.error("Please pull the model by running: ollama pull mistral")
                    return None
                else:
                    logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed with status {response.status_code}")
                    logger.debug(f"Response content: {response.text}")
                    
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed with error: {str(e)}")
                if attempt == self.max_retries - 1:
                    logger.error("Failed to connect to Ollama server after all retries")
                    logger.error("Please ensure Ollama server is running at http://localhost:11434")
                    logger.error("You can start it by running: ollama serve")
            
            if attempt < self.max_retries - 1:
                logger.debug(f"Waiting {self.retry_delay} seconds before next attempt")
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
        logger.info(f"Processing file: {file_path}")
        try:
            # Extract text from file
            content = self._extract_text_from_file(file_path)
            if not content:
                logger.error(f"Failed to extract text from {file_path}")
                return {}

            # Split content into chunks if it's too large
            chunks = self._chunk_text(content)
            all_results = []

            for i, chunk in enumerate(chunks, 1):
                logger.info(f"Processing chunk {i}/{len(chunks)}")
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
                8. Ensure the response is a complete, valid JSON object
                9. Do not include any text before or after the JSON object
                10. Always close all JSON objects and arrays
                11. Use double quotes for all keys and string values
                12. Do not use trailing commas
                13. Ensure all numbers are not quoted
                14. Ensure all boolean values are true/false (not quoted)
                15. Ensure all null values are not quoted
                16. Make sure to close all objects with }} and arrays with ]
                17. Do not leave any unclosed brackets or braces
                18. Return the complete JSON object in a single response
                
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
                    logger.warning(f"No response received for chunk {i}")
                    continue

                # Parse the JSON response
                try:
                    structured_data = json.loads(extracted_text)
                    logger.info(f"Successfully parsed JSON from chunk {i}")
                    logger.info(f"Chunk {i} extracted data: {json.dumps(structured_data, indent=2)}")
                    all_results.append(structured_data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Ollama response as JSON for chunk {i}: {e}")
                    logger.debug(f"Raw response: {extracted_text[:200]}...")  # Log first 200 chars

                # Add a small delay between chunks to avoid overwhelming the server
                if i < len(chunks):
                    logger.debug("Waiting 1 second before processing next chunk...")
                    time.sleep(1)

            # Merge all results
            logger.info(f"Merging results from {len(all_results)} chunks")
            merged_result = {}
            for i, result in enumerate(all_results, 1):
                logger.info(f"Merging chunk {i} result: {json.dumps(result, indent=2)}")
                self._merge_results(merged_result, result)

            logger.info(f"Successfully processed file: {file_path}")
            logger.info(f"Final merged result: {json.dumps(merged_result, indent=2)}")
            return merged_result

        except Exception as e:
            logger.error(f"Error processing file with Ollama: {str(e)}")
            return {}

    def _merge_results(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Merge source dictionary into target dictionary, handling nested structures."""
        logger.debug("Merging results")
        for key, value in source.items():
            if key in target:
                if isinstance(value, dict) and isinstance(target[key], dict):
                    if "value" in value and "confidence" in value:
                        # If both are value/confidence pairs, keep the one with higher confidence
                        if value["confidence"] > target[key]["confidence"]:
                            logger.debug(f"Replacing {key} with higher confidence value: {value['confidence']} > {target[key]['confidence']}")
                            logger.debug(f"Old value: {json.dumps(target[key], indent=2)}")
                            logger.debug(f"New value: {json.dumps(value, indent=2)}")
                            target[key] = value
                    else:
                        self._merge_results(target[key], value)
            else:
                logger.debug(f"Adding new key: {key}")
                logger.debug(f"New value: {json.dumps(value, indent=2)}")
                target[key] = value 