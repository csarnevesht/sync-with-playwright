from transformers import AutoTokenizer
from transformers.models.qwen2_vl import Qwen2VLConfig, Qwen2VLForCausalLM, Qwen2VLProcessor
import torch
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)

class QwenProcessor:
    def __init__(self, model_name="Qwen/Qwen2-VL-7B-Instruct"):
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.processor = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
    def initialize(self):
        """Initialize the model and tokenizer."""
        try:
            logger.info("Initializing Qwen model and tokenizer...")
            
            # Load config
            config = Qwen2VLConfig.from_pretrained(self.model_name, trust_remote_code=True)
            logger.info("Config loaded successfully")
            
            # Load processor
            self.processor = Qwen2VLProcessor.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            logger.info("Processor loaded successfully")
            
            # Load model
            self.model = Qwen2VLForCausalLM.from_pretrained(
                self.model_name,
                config=config,
                device_map="auto",
                trust_remote_code=True,
                torch_dtype=torch.float16
            )
            logger.info("Model loaded successfully")
            
        except Exception as e:
            logger.error(f"Error initializing model: {str(e)}")
            raise

    def process_image(self, image_data):
        """Process an image and return the model's response."""
        try:
            if self.model is None or self.processor is None:
                self.initialize()

            # Convert image data to PIL Image
            image = Image.open(io.BytesIO(image_data))
            logger.info(f"Image loaded: {image.size}")
            
            # Prepare the prompt
            prompt = "Please analyze this image and extract any relevant information about the document, including names, dates, amounts, and any other important details."
            logger.info(f"Using prompt: {prompt}")
            
            # Process inputs
            inputs = self.processor(
                text=prompt,
                images=image,
                return_tensors="pt"
            ).to(self.device)
            logger.info("Inputs processed")
            
            # Generate response
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=512,
                do_sample=True,
                temperature=0.7,
                top_p=0.9
            )
            logger.info("Generated outputs")
            
            response = self.processor.decode(outputs[0], skip_special_tokens=True)
            logger.info(f"Generated response: {response}")
            return response

        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            raise 