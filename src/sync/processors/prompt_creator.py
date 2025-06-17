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
        # self.logger.info(f"Text first 200 chars: {text[:200]}")
        self.logger.info(f"Processor type: {processor_type}")
        self.logger.info(f"Owner type: {owner_type}")

        # Base system message that works for all processors
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

        # Base prompt template that works for all processors
        main_prompt = f"""Analyze the following text and extract key information about the {owner_type}. 
Return ONLY a JSON object with the following structure, using the specified types (use null if not found):
{{
  "{owner_type}": {{
    "firstName": "string or null",
    "middleInitial": "string or null",
    "lastName": "string or null",
    "dateOfBirth": "string (YYYY-MM-DD) or null",
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

Text to analyze:
{text}

YOUR RESPONSE MUST BE A SINGLE JSON OBJECT WITH NO ADDITIONAL TEXT OR FORMATTING. DO NOT INCLUDE ANY EXPLANATORY TEXT, MARKDOWN, OR CODE BLOCKS. JUST THE JSON OBJECT. If a field is not found, use null."""

        self.logger.info(f"_create_extraction_prompt: Final prompt: {text}")
        self.logger.info(f"_create_extraction_prompt: owner_type: {owner_type}")
        self.logger.info(f"_create_extraction_prompt: processor_type: {processor_type}")
        self.logger.info(f"_create_extraction_prompt: main_prompt: {main_prompt}")
        
        final_prompt = f"{system_message}\n\n{main_prompt}"

        self.logger.info("\n=== [PROMPT GENERATED] ===")
        self.logger.info(f"_create_extraction_prompt: Prompt length: {len(final_prompt)} characters")
        self.logger.info(f"_create_extraction_prompt: Final Prompt: {final_prompt}")
        
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
        prompt = self.create_owner_extraction_prompt(text, processor_type)
        
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