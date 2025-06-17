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

    def create_owner_extraction_prompt(self, text: str, processor_type: str = "default") -> str:
        """
        Create a prompt for extracting owner information from text.
        
        Args:
            text (str): The text to analyze
            processor_type (str): The type of processor ("ollama", "qwen", "lm_studio", or "default")
            
        Returns:
            str: The formatted prompt
        """
        self.logger.info("=== [PROMPT CREATION START] ===")
        self.logger.info(f"Text length: {len(text)} characters")
        self.logger.info(f"Text first 200 chars: {text[:200]}")
        self.logger.info(f"Processor type: {processor_type}")

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
        main_prompt = (
            "Analyze the following text and extract key information about the owner. "
            "Return ONLY a JSON object with the following structure, using the specified types (use null if not found):\n"
            "{{\n"
            "  \"owner\": {{\n"
            "    \"firstName\": \"string or null\",\n"
            "    \"middleInitial\": \"string or null\",\n"
            "    \"lastName\": \"string or null\",\n"
            # "    \"SSN\": \"string or null\",\n"
            "    \"dateOfBirth\": \"string (YYYY-MM-DD) or null\",\n"
            "    \"gender\": \"string or null\",\n"
            "    \"mailingAddressStreet\": \"string or null\",\n"
            "    \"mailingAddressCity\": \"string or null\",\n"
            "    \"mailingAddressState\": \"string or null\",\n"
            "    \"mailingAddressZip\": \"string or null\",\n"
            "    \"residentialAddressStreet\": \"string or null\",\n"
            "    \"residentialAddressCity\": \"string or null\",\n"
            "    \"residentialAddressState\": \"string or null\",\n"
            "    \"residentialAddressZip\": \"string or null\",\n"
            "    \"phoneNumber\": \"string or null\",\n"
            "    \"emailAddress\": \"string or null\"\n"
            "  }}\n"
            "}}\n\n"
            "Text to analyze:\n{text}\n\n"
            "YOUR RESPONSE MUST BE A SINGLE JSON OBJECT WITH NO ADDITIONAL TEXT OR FORMATTING. DO NOT INCLUDE ANY EXPLANATORY TEXT, MARKDOWN, OR CODE BLOCKS. JUST THE JSON OBJECT. If a field is not found, use null."
        )

        # Processor-specific formatting
        if processor_type == "ollama":
            # Ollama-specific formatting
            formatted_main_prompt = main_prompt.format(text=text)
            final_prompt = f"{system_message}\n\n{formatted_main_prompt}"
        elif processor_type == "qwen":
            # Qwen-specific formatting
            formatted_main_prompt = main_prompt.format(text=text)
            final_prompt = f"{system_message}\n\n{formatted_main_prompt}"
        elif processor_type == "lm_studio":
            # LM Studio-specific formatting
            formatted_main_prompt = main_prompt.format(text=text)
            final_prompt = f"{system_message}\n\n{formatted_main_prompt}"
        else:
            # Default formatting
            formatted_main_prompt = main_prompt.format(text=text)
            final_prompt = f"{system_message}\n\n{formatted_main_prompt}"

        self.logger.info("\n=== [PROMPT GENERATED] ===")
        self.logger.info(f"Prompt length: {len(final_prompt)} characters")
        self.logger.info(f"Final Prompt: {final_prompt}")
        
        return final_prompt

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