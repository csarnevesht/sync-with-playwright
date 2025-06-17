from sync.processors.ollama_processor import OllamaProcessor
from sync.processors.qwen_processor import QwenProcessor
from pathlib import Path
import logging

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def process_with_ollama(file_path: str):
    """Process a file using Ollama processor."""
    print("\n=== Processing with Ollama ===")
    processor = OllamaProcessor()
    result = processor.process_file(Path(file_path))
    print("Result:", result)
    return result

def process_with_qwen(file_path: str):
    """Process a file using Qwen processor."""
    print("\n=== Processing with Qwen ===")
    processor = QwenProcessor()
    result = processor.process_file(Path(file_path))
    print("Result:", result)
    return result

def main():
    # Set up logging
    setup_logging()
    
    # Example file path
    file_path = "path/to/your/file.pdf"  # Replace with your file path
    
    try:
        # Process with both processors
        ollama_result = process_with_ollama(file_path)
        qwen_result = process_with_qwen(file_path)
        
        # Compare results
        print("\n=== Comparing Results ===")
        print("Ollama Result:", ollama_result)
        print("Qwen Result:", qwen_result)
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 