import logging
import os
from typing import Dict, Any, Optional
import datetime

class PromptCreator:
    """A unified class for creating prompts across different LLM processors."""
    
    def __init__(self, log_dir: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.hasHandlers():
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.log_dir = log_dir
        self.last_prompt_path = None  # Store the path of the last written prompt

    def _write_prompt_to_file(self, prompt: str, owner_type: str, filename: str = None, dropbox_folder_name: str = None) -> str:
        """Write the prompt content to a file in the log directory.
        
        Args:
            prompt: The prompt content to write
            owner_type: The type of owner (owner, joint_owner, etc.)
            filename: Optional filename being processed
            dropbox_folder_name: Optional Dropbox folder name for organization
            
        Returns:
            str: The path to the written prompt file (for response file matching)
        """
        if not self.log_dir:
            self.logger.warning("No log directory available, skipping prompt file write")
            return None
            
        try:
            # Create app_files directory structure
            app_files_dir = os.path.join(self.log_dir, 'app_files')
            if dropbox_folder_name:
                # Clean the folder name for use as a directory name
                clean_folder_name = dropbox_folder_name.replace('/', '_').replace('\\', '_').replace(':', '_')
                folder_dir = os.path.join(app_files_dir, clean_folder_name)
            else:
                folder_dir = os.path.join(app_files_dir, 'unknown_folder')
            
            os.makedirs(folder_dir, exist_ok=True)
            
            # Create filename based on app file name and owner type
            if filename:
                # Clean the filename for use as a file name
                clean_filename = filename.replace('/', '_').replace('\\', '_').replace(':', '_').replace('.', '_')
                prompt_filename = f"prompt_{owner_type}_{clean_filename}.txt"
            else:
                # Fallback to timestamp if no filename provided
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                prompt_filename = f"prompt_{owner_type}_{timestamp}.txt"
            
            prompt_path = os.path.join(folder_dir, prompt_filename)
            
            # Add filename information to the prompt content
            enhanced_prompt = prompt
            if filename:
                enhanced_prompt = f"Processing file: {filename}\n\n{enhanced_prompt}"
            
            # Write the prompt to file
            with open(prompt_path, 'w', encoding='utf-8') as f:
                f.write(enhanced_prompt)
            
            # Store the prompt path for response file matching
            self.last_prompt_path = prompt_path
            
            self.logger.info(f"Prompt written to file: {prompt_path}")
            return prompt_path
            
        except Exception as e:
            self.logger.error(f"Error writing prompt to file: {str(e)}")
            return None

    def _write_response_to_file(self, response: str, owner_type: str, filename: str = None, dropbox_folder_name: str = None, prompt_path: str = None) -> None:
        """Write the processor response to a file in the log directory.
        
        Args:
            response: The processor response content to write
            owner_type: The type of owner (owner, joint_owner, etc.)
            filename: Optional filename being processed
            dropbox_folder_name: Optional Dropbox folder name for organization
            prompt_path: Optional path to the corresponding prompt file (for matching)
        """
        if not self.log_dir:
            self.logger.warning("No log directory available, skipping response file write")
            return
            
        try:
            # Create app_files directory structure
            app_files_dir = os.path.join(self.log_dir, 'app_files')
            if dropbox_folder_name:
                # Clean the folder name for use as a directory name
                clean_folder_name = dropbox_folder_name.replace('/', '_').replace('\\', '_').replace(':', '_')
                folder_dir = os.path.join(app_files_dir, clean_folder_name)
            else:
                folder_dir = os.path.join(app_files_dir, 'unknown_folder')
            
            os.makedirs(folder_dir, exist_ok=True)
            
            # Determine the response filename
            if prompt_path:
                # Extract the filename from the prompt path and create matching response filename
                prompt_filename = os.path.basename(prompt_path)
                response_filename = prompt_filename.replace('prompt_', 'response_')
            elif filename:
                # Create filename based on app file name and owner type
                clean_filename = filename.replace('/', '_').replace('\\', '_').replace(':', '_').replace('.', '_')
                response_filename = f"response_{owner_type}_{clean_filename}.txt"
            elif self.last_prompt_path:
                # Use the last written prompt path
                prompt_filename = os.path.basename(self.last_prompt_path)
                response_filename = prompt_filename.replace('prompt_', 'response_')
            else:
                # Create timestamp for filename (fallback)
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
                response_filename = f"response_{owner_type}_{timestamp}.txt"
            
            response_path = os.path.join(folder_dir, response_filename)
            
            # Add filename information to the response content
            enhanced_response = response
            if filename:
                enhanced_response = f"Processing file: {filename}\n\n{enhanced_response}"
            
            # Write the response to file
            with open(response_path, 'w', encoding='utf-8') as f:
                f.write(enhanced_response)
            
            self.logger.info(f"Response written to file: {response_path}")
            
        except Exception as e:
            self.logger.error(f"Error writing response to file: {str(e)}")

    def _create_extraction_prompt(self, text: str, owner_type: str = "owner", processor_type: str = "default") -> str:
        """
        Create a prompt for extracting owner information from text.
        
        Args:
            text (str): The text to analyze
            owner_type (str): The type of owner to extract ("owner" or "jointOwner")
            processor_type (str): The type of processor ("ollama", "qwen", "lm_studio", or "default")
            
        Returns:
            str: The formatted prompt
        """
        self.logger.info("=== [PROMPT CREATION START] ===")
        self.logger.info(f"Text length: {len(text)} characters")
        self.logger.info(f"Text first 200 chars: {text[:200]}")
        self.logger.info(f"Processor type: {processor_type}")
        self.logger.info(f"Owner type: {owner_type}")

        # Base system message that works for all processors
        system_message = (
            "Extract owner or annuitant information and return ONLY a JSON object.\n"
            "Rules:\n"
            "1. Return ONLY the JSON object\n"
            "2. Use null for missing fields\n"
            "3. No explanatory text\n"
            "4. No markdown/code blocks\n"
            "5. Use camelCase keys\n"
            "6. Only extract listed fields\n"
            "7. Never guess information\n"
            "8. For dateOfBirth: Convert MM/DD/YYYY or MM/DD/YY to YYYY-MM-DD format\n"
            "9. Look for DOB, Date of Birth, Birth Date, or similar terms\n"
        )

        # Base prompt template that works for all processors
        main_prompt = f"""Extract {owner_type} information into this JSON structure:
{{
  "{owner_type}": {{
    "firstName": "string or null",
    "middleInitial": "string or null",
    "lastName": "string or null",
    "dateOfBirth": "string (YYYY-MM-DD) or null - Convert MM/DD/YYYY to YYYY-MM-DD",
    "gender": "string or null",
    "mailingAddressStreet": "string or null",
    "mailingAddressCity": "string or null",
    "mailingAddressState": "string or null",
    "mailingAddressZip": "string or null",
    "residentialAddressStreet": "string or null",
    "residentialAddressCity": "string or null",
    "residentialAddressState": "string or null",
    "residentialAddressZip": "string or null",
    "phoneNumber": "string or null",
    "emailAddress": "string or null"
  }}
}}

FORM STRUCTURE UNDERSTANDING:
This is an insurance application form with multiple sections. Look for:
1. Annuitant section (usually first)
2. Owner section (may be same as annuitant or different)
3. Each section contains: Name, Gender, Address, Birth Date, etc.

IMPORTANT EXTRACTION GUIDELINES:

For dateOfBirth field:
- Look for patterns like: "Date of Birth (MM/DD/YY)", "DOB", "Birth Date", etc.
- If you find a date like "04/11/1961", convert it to "1961-04-11"
- If you find a date like "04/11/61", convert it to "1961-04-11" (assume 19xx for 2-digit years)
- If no date is found, use null

For gender field:
- Look for "Gender:" followed by "X Male Female" or similar patterns
- If "X" appears next to "Male", extract "Male"
- If "X" appears next to "Female", extract "Female"
- Look for gender options with "X" or "£X" indicating the selected option
- The "X" or "£X" indicates which option is SELECTED
- Examples:
  - "£ Male £X Female" → gender: "Female" (X is next to Female)
  - "£X Male £ Female" → gender: "Male" (X is next to Male)
  - "Male X Female" → gender: "Female" (X is next to Female)
  - "X Male Female" → gender: "Male" (X is next to Male)
  - "Male Female X" → gender: "Female" (X is next to Female)
- Look in both Annuitant and Owner sections

For address fields (CRITICAL):
- Look for "Street Address" or "Address" sections
- Extract the street address, city, state, and zip code
- Look for patterns like "City State Zip" followed by the actual values
- Check both Annuitant and Owner sections for address information
- IMPORTANT: In forms, address information is often structured as:
  * Street address on one line (e.g., "2217 Blue Springs Road")
  * City, State, Zip on the next line (e.g., "West Palm Beach FL 33411")
- Extract each component separately into the appropriate fields
- DO NOT skip address extraction - this is required information

For phone and email:
- Look for "Phone" and "Email Address" fields
- Extract the actual phone number and email address values

EXAMPLES OF WHAT TO EXTRACT:
- If you see: "2217 Blue Springs Road" → mailingAddressStreet: "2217 Blue Springs Road"
- If you see: "West Palm Beach FL 33411" → 
  * mailingAddressCity: "West Palm Beach"
  * mailingAddressState: "FL" 
  * mailingAddressZip: "33411"
- If you see: "£ Male £X Female" → gender: "Female"
- If you see: "Birth Date (mm/dd/yyyy) 04/05/1946" → dateOfBirth: "1946-04-05"

REQUIRED: You MUST extract ALL available information including addresses. Do not leave address fields as null if the information is present in the text.

Text to analyze:
{text}

Return ONLY the JSON object. Use null for missing fields."""

        self.logger.info(f"_create_extraction_prompt: owner_type: {owner_type}")
        self.logger.info(f"_create_extraction_prompt: processor_type: {processor_type}")
        
        final_prompt = f"{system_message}\n\n{main_prompt}"

        self.logger.info("\n=== [PROMPT GENERATED] ===")
        self.logger.info(f"_create_extraction_prompt: Prompt length: {len(final_prompt)} characters")
        self.logger.info(f"_create_extraction_prompt: Final Prompt BEGIN PROMPT: \n{final_prompt}\nEND OF PROMPT")
        self.logger.info(f"\n{'='*80}\n{'='*80}\n{'='*80}\n{'='*80}")

        return final_prompt

    def _create_short_extraction_prompt(self, text: str, owner_type: str, processor_type: str = "lm_studio", filename: str = None, dropbox_folder_name: str = None) -> str:
        """Create a short extraction prompt for LM Studio to avoid context overflow."""
        self.logger.info(f"_create_short_extraction_prompt: {owner_type}")
        
        # Truncate text to first 2000 characters to fit in context window
        max_text_length = 2000
        if len(text) > max_text_length:
            self.logger.info(f"Truncating text from {len(text)} to {max_text_length} characters for LM Studio")
            text = text[:max_text_length]
        
        # Short prompt template
        prompt = f"""Extract {owner_type} information and return ONLY a JSON object.

JSON structure:
{{
  "{owner_type}": {{
    "firstName": "string or null",
    "lastName": "string or null", 
    "dateOfBirth": "string (YYYY-MM-DD) or null",
    "gender": "string or null",
    "mailingAddressStreet": "string or null",
    "mailingAddressCity": "string or null",
    "mailingAddressState": "string or null",
    "mailingAddressZip": "string or null",
    "phoneNumber": "string or null",
    "emailAddress": "string or null"
  }}
}}

IMPORTANT EXTRACTION GUIDELINES:

For gender field:
- Look for "Gender:" followed by "X Male Female" or similar patterns
- If "X" appears next to "Male", extract "Male"
- If "X" appears next to "Female", extract "Female"
- Look for gender options with "X" or "£X" indicating the selected option
- The "X" or "£X" indicates which option is SELECTED
- Examples:
  - "£ Male £X Female" → gender: "Female" (X is next to Female)
  - "£X Male £ Female" → gender: "Male" (X is next to Male)
  - "Male X Female" → gender: "Female" (X is next to Female)
  - "X Male Female" → gender: "Male" (X is next to Male)
  - "Male Female X" → gender: "Female" (X is next to Female)
- Look in both Annuitant and Owner sections

Text to analyze:
{text}

Return ONLY the JSON object."""
        
        self.logger.info(f"_create_short_extraction_prompt: Final Prompt BEGIN PROMPT: \n{prompt}\nEND OF PROMPT")
        self.logger.info(f"\n{'='*80}\n{'='*80}\n{'='*80}\n{'='*80}")
        
        # Write prompt to file in log directory and store the path for later use
        self._write_prompt_to_file(prompt, owner_type, filename, dropbox_folder_name)
        
        return prompt

    def create_owner_extraction_prompt(self, text: str, processor_type: str = "default", filename: str = None, dropbox_folder_name: str = None) -> str:
        """Create a prompt for extracting owner information."""
        self.logger.info(f"create_owner_extraction_prompt: Creating owner extraction prompt")
        self.logger.info(f"=== [PROMPT CREATION START] ===")
        self.logger.info(f"create_owner_extraction_prompt: Text length: {len(text)} characters")
        self.logger.info(f"create_owner_extraction_prompt: Processor type: {processor_type}")
        
        # For LM Studio, create a shorter prompt to avoid context overflow
        if processor_type == "lm_studio":
            return self._create_short_extraction_prompt(text, "owner", processor_type, filename, dropbox_folder_name)
        else:
            return self._create_extraction_prompt(text, "owner", processor_type)

    def create_joint_owner_extraction_prompt(self, text: str, processor_type: str = "default", filename: str = None, dropbox_folder_name: str = None) -> str:
        """Create a prompt for extracting joint owner information."""
        self.logger.info(f"create_joint_owner_extraction_prompt: Creating joint owner extraction prompt")
        
        # For LM Studio, create a shorter prompt to avoid context overflow
        if processor_type == "lm_studio":
            return self._create_short_extraction_prompt(text, "jointOwner", processor_type, filename, dropbox_folder_name)
        else:
            return self._create_extraction_prompt(text, "jointOwner", processor_type)

    def create_chat_prompt(self, text: str, processor_type: str = "default") -> Dict[str, Any]:
        """
        Create a chat prompt for processors that use chat completion format.
        
        Args:
            text (str): The text to analyze
            processor_type (str): The type of processor ("ollama", "qwen", "lm_studio", or "default")
            
        Returns:
            Dict[str, Any]: The formatted chat prompt
        """
        self.logger.info(f"create_chat_prompt: Creating chat prompt")
        # CAROLINA HERE 
        prompt = text
        # prompt = self.create_owner_extraction_prompt(text, processor_type)
        
        if processor_type == "lm_studio":
            return {
                "model": "Element Labs Inc",  # This should be configurable
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a precise JSON extraction tool. Your task is to extract owner information from text and return it in a specific JSON format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.0,
                "max_tokens": 1000
            }
        elif processor_type == "ollama":
            return {
                "model": "llama2",  # This should be configurable
                "prompt": prompt,
                "stream": False
            }
        elif processor_type == "qwen":
            return {
                "model": "Qwen2-VL-7B-Instruct",  # This should be configurable
                "prompt": prompt,
                "temperature": 0.0,
                "max_tokens": 1000
            }
        else:
            return {
                "prompt": prompt,
                "temperature": 0.0,
                "max_tokens": 1000
            } 