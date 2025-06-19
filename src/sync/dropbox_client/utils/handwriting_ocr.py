import torch
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
import os

def extract_handwritten_text(image_path: str, model_name: str = 'microsoft/trocr-base-handwritten') -> str:
    """
    Extract handwritten text from an image using the TrOCR model.
    Args:
        image_path (str): Path to the image file (PNG, JPG, etc.)
        model_name (str): HuggingFace model name for TrOCR (default: 'microsoft/trocr-base-handwritten')
    Returns:
        str: The extracted text
    """
    # Load model and processor only when needed
    processor = TrOCRProcessor.from_pretrained(model_name, use_fast=True)
    model = VisionEncoderDecoderModel.from_pretrained(model_name)

    # Load and preprocess image
    image = Image.open(image_path).convert('RGB')
    pixel_values = processor(images=image, return_tensors="pt").pixel_values

    # Move to GPU if available
    if torch.cuda.is_available():
        model = model.to('cuda')
        pixel_values = pixel_values.to('cuda')

    # Generate text
    generated_ids = model.generate(pixel_values)
    text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return text

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python handwriting_ocr.py <image_path>")
        exit(1)
    image_path = sys.argv[1]
    if not os.path.exists(image_path):
        print(f"File not found: {image_path}")
        exit(1)
    result = extract_handwritten_text(image_path)
    print("Extracted text:\n", result) 