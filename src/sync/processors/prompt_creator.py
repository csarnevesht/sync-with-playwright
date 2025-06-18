import logging
from typing import Dict, Any, Optional

class PromptCreator:
    """A unified class for creating prompts across different LLM processors."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.hasHandlers():
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

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

IMPORTANT: For dateOfBirth field:
- Look for patterns like: "Date of Birth (MM/DD/YY)", "DOB", "Birth Date", etc.
- If you find a date like "04/11/1961", convert it to "1961-04-11"
- If you find a date like "04/11/61", convert it to "1961-04-11" (assume 19xx for 2-digit years)
- If no date is found, use null

Text to analyze:
{text}

Return ONLY the JSON object. Use null for missing fields."""

        self.logger.info(f"_create_extraction_prompt: owner_type: {owner_type}")
        self.logger.info(f"_create_extraction_prompt: processor_type: {processor_type}")
        
        final_prompt = f"{system_message}\n\n{main_prompt}"

        self.logger.info("\n=== [PROMPT GENERATED] ===")
        self.logger.info(f"_create_extraction_prompt: Prompt length: {len(final_prompt)} characters")
        self.logger.info(f"_create_extraction_prompt: Final Prompt BEGIN PROMPT: \n{final_prompt}\nEND OF PROMPT")
        
        return final_prompt

    def create_owner_extraction_prompt(self, text: str, processor_type: str = "default") -> str:
        """
        Create a prompt for extracting primary owner information from text.
        
        Args:
            text (str): The text to analyze
            processor_type (str): The type of processor ("ollama", "qwen", "lm_studio", or "default")
            
        Returns:
            str: The formatted prompt
        """
        self.logger.info(f"create_owner_extraction_prompt: Creating owner extraction prompt")
        return self._create_extraction_prompt(text, "owner", processor_type)

    def create_joint_owner_extraction_prompt(self, text: str, processor_type: str = "default") -> str:
        """
        Create a prompt for extracting joint owner information from text.
        
        Args:
            text (str): The text to analyze
            processor_type (str): The type of processor ("ollama", "qwen", "lm_studio", or "default")
            
        Returns:
            str: The formatted prompt
        """
        self.logger.info(f"create_joint_owner_extraction_prompt: Creating joint owner extraction prompt")
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