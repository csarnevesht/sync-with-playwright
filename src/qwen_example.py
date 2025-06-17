from transformers.models.qwen2_vl import Qwen2VLForCausalLM
import torch
from PIL import Image
import base64
from io import BytesIO

def load_model():
    """Load the Qwen2-VL-7B-Instruct model and tokenizer."""
    model_name = "Qwen/Qwen2-VL-7B-Instruct"
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    
    # Load model
    model = Qwen2VLForCausalLM.from_pretrained(
        model_name,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.float16  # Use float16 for better memory efficiency
    )
    
    return model, tokenizer

def image_to_base64(image_path):
    """Convert an image to base64 string."""
    with Image.open(image_path) as img:
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize if too large (optional)
        max_size = 1024
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convert to base64
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str

def generate_response(model, tokenizer, prompt, image_path=None, max_length=2048):
    """Generate a response from the model."""
    # Prepare the input
    if image_path:
        # Convert image to base64
        image_base64 = image_to_base64(image_path)
        # Add image to prompt
        prompt = f"<image>{image_base64}</image>\n{prompt}"
    
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    
    # Generate response
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_length=max_length,
            num_return_sequences=1,
            temperature=0.7,
            top_p=0.9,
            do_sample=True
        )
    
    # Decode and return the response
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return response

def main():
    # Load model and tokenizer
    print("Loading model and tokenizer...")
    model, tokenizer = load_model()
    
    # Example usage with an image
    image_path = "path/to/your/image.jpg"  # Replace with your image path
    prompt = "Please describe what you see in this image."
    
    try:
        # Generate response
        print("\nGenerating response...")
        response = generate_response(model, tokenizer, prompt, image_path)
        print("\nResponse:", response)
    except FileNotFoundError:
        print(f"Error: Image file not found at {image_path}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 