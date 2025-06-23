#!/usr/bin/env python3
"""
LM Studio Configuration Helper

This script helps detect and configure LM Studio context length settings.
Since LM Studio doesn't provide programmatic server configuration,
this script guides users through manual configuration.
"""

import json
import requests
import subprocess
import sys
import time
from typing import Optional, Dict, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LMStudioConfigHelper:
    def __init__(self, base_url: str = "http://localhost:1234/v1"):
        self.base_url = base_url
        self.required_context_length = 32768  # 32K tokens
        
    def check_server_availability(self) -> bool:
        """Check if LM Studio server is running."""
        try:
            response = requests.get(f"{self.base_url}/models", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"LM Studio server not available: {e}")
            return False
    
    def get_current_context_length(self) -> Optional[int]:
        """
        Attempt to determine the current context length by making a test request
        with a known large prompt and checking the error message.
        """
        try:
            # Create a test prompt that's larger than 4096 tokens
            large_prompt = "Test text " * 10000  # This should be > 4096 tokens
            
            test_request = {
                "model": "qwen2-vl-7b-instruct",
                "messages": [
                    {"role": "user", "content": large_prompt}
                ],
                "max_tokens": 100
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=test_request,
                timeout=30
            )
            
            if response.status_code == 400:
                error_text = response.text.lower()
                if "context length of only" in error_text:
                    # Extract the context length from error message
                    import re
                    match = re.search(r'context length of only (\d+) tokens', error_text)
                    if match:
                        return int(match.group(1))
            
            # If we get a successful response, context length is sufficient
            if response.status_code == 200:
                return self.required_context_length  # Assume it's working
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking context length: {e}")
            return None
    
    def check_model_loaded(self) -> bool:
        """Check if the required model is loaded."""
        try:
            response = requests.get(f"{self.base_url}/models")
            if response.status_code == 200:
                models_data = response.json()
                if isinstance(models_data, dict) and 'data' in models_data:
                    models = models_data['data']
                else:
                    models = models_data
                
                for model in models:
                    if isinstance(model, dict) and model.get('id') == 'qwen2-vl-7b-instruct':
                        return True
            return False
        except Exception as e:
            logger.error(f"Error checking model status: {e}")
            return False
    
    def get_lm_studio_process_info(self) -> Dict[str, Any]:
        """Get information about the LM Studio process."""
        try:
            # Find LM Studio process
            result = subprocess.run(
                ['ps', 'aux'], 
                capture_output=True, 
                text=True
            )
            
            lm_studio_lines = [
                line for line in result.stdout.split('\n') 
                if 'LM Studio' in line and 'grep' not in line
            ]
            
            if lm_studio_lines:
                # Parse the first LM Studio process
                parts = lm_studio_lines[0].split()
                if len(parts) >= 2:
                    return {
                        'pid': parts[1],
                        'command': ' '.join(parts[10:]),
                        'running': True
                    }
            
            return {'running': False}
            
        except Exception as e:
            logger.error(f"Error getting process info: {e}")
            return {'running': False, 'error': str(e)}
    
    def get_model_file_info(self) -> Dict[str, Any]:
        """Get information about the model files."""
        try:
            model_path = "/Users/carolinasarneveshtair/.lmstudio/models/lmstudio-community/Qwen2-VL-7B-Instruct-GGUF"
            result = subprocess.run(
                ['ls', '-la', model_path],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                files = result.stdout.strip().split('\n')[1:]  # Skip header
                return {
                    'path': model_path,
                    'files': files,
                    'exists': True
                }
            else:
                return {'exists': False, 'error': result.stderr}
                
        except Exception as e:
            logger.error(f"Error getting model file info: {e}")
            return {'exists': False, 'error': str(e)}
    
    def print_diagnostic_info(self):
        """Print comprehensive diagnostic information."""
        print("\n" + "="*60)
        print("LM STUDIO CONFIGURATION DIAGNOSTIC")
        print("="*60)
        
        # Check server availability
        print(f"\n1. Server Status:")
        server_available = self.check_server_availability()
        print(f"   LM Studio server running: {'✅ Yes' if server_available else '❌ No'}")
        
        if not server_available:
            print("   → Please start LM Studio application")
            return
        
        # Check model status
        print(f"\n2. Model Status:")
        model_loaded = self.check_model_loaded()
        print(f"   qwen2-vl-7b-instruct loaded: {'✅ Yes' if model_loaded else '❌ No'}")
        
        # Check context length
        print(f"\n3. Context Length:")
        current_context = self.get_current_context_length()
        if current_context:
            print(f"   Current context length: {current_context:,} tokens")
            if current_context >= self.required_context_length:
                print(f"   Status: ✅ Sufficient ({current_context:,} >= {self.required_context_length:,})")
            else:
                print(f"   Status: ❌ Insufficient ({current_context:,} < {self.required_context_length:,})")
        else:
            print(f"   Current context length: Unknown")
            print(f"   Required: {self.required_context_length:,} tokens")
        
        # Process information
        print(f"\n4. Process Information:")
        process_info = self.get_lm_studio_process_info()
        if process_info.get('running'):
            print(f"   LM Studio PID: {process_info.get('pid', 'Unknown')}")
            print(f"   Status: ✅ Running")
        else:
            print(f"   Status: ❌ Not running")
        
        # Model files
        print(f"\n5. Model Files:")
        model_info = self.get_model_file_info()
        if model_info.get('exists'):
            print(f"   Model path: {model_info['path']}")
            print(f"   Status: ✅ Found")
            for file in model_info.get('files', [])[:3]:  # Show first 3 files
                print(f"     {file}")
        else:
            print(f"   Status: ❌ Not found")
            if 'error' in model_info:
                print(f"   Error: {model_info['error']}")
    
    def print_configuration_guide(self):
        """Print step-by-step configuration guide."""
        print("\n" + "="*60)
        print("CONFIGURATION GUIDE")
        print("="*60)
        
        print("\nTo fix context length issues, follow these steps:")
        print("\n1. Open LM Studio Application")
        print("   - Launch LM Studio from Applications folder")
        print("   - Wait for the application to fully load")
        
        print("\n2. Load the Model with Correct Context Length")
        print("   - Go to 'My Models' tab")
        print("   - Find 'qwen2-vl-7b-instruct' model")
        print("   - Click the gear icon (⚙️) next to the model")
        print("   - Set 'Context Length' to 32768 (32K)")
        print("   - Click 'Load' button")
        
        print("\n3. Verify Configuration")
        print("   - Wait for model to load completely")
        print("   - Check that the model shows as 'Loaded'")
        print("   - Run this script again to verify context length")
        
        print("\n4. Alternative: Use Different Model")
        print("   - If context length cannot be changed, consider:")
        print("     • Using a different model variant")
        print("     • Using a smaller context window")
        print("     • Processing text in smaller chunks")
        
        print("\n5. Keep Model Loaded")
        print("   - Once configured, keep the model loaded")
        print("   - Don't close LM Studio during processing")
        print("   - The model will remain available for API calls")
    
    def run_interactive_diagnostic(self):
        """Run an interactive diagnostic session."""
        print("🔍 LM Studio Configuration Helper")
        print("This tool will help you diagnose and fix context length issues.\n")
        
        # Run diagnostic
        self.print_diagnostic_info()
        
        # Check if configuration is needed
        current_context = self.get_current_context_length()
        needs_config = (
            not current_context or 
            current_context < self.required_context_length
        )
        
        if needs_config:
            print(f"\n⚠️  CONFIGURATION NEEDED")
            print(f"Current context length ({current_context or 'Unknown'}) is insufficient.")
            print(f"Required: {self.required_context_length:,} tokens")
            
            self.print_configuration_guide()
            
            # Offer to run diagnostic again
            while True:
                response = input(f"\nWould you like to run the diagnostic again after configuration? (y/n): ").lower().strip()
                if response in ['y', 'yes']:
                    print("\nPlease configure LM Studio as described above, then press Enter to continue...")
                    input()
                    print("\nRunning diagnostic again...")
                    self.print_diagnostic_info()
                    break
                elif response in ['n', 'no']:
                    break
                else:
                    print("Please enter 'y' or 'n'")
        else:
            print(f"\n✅ CONFIGURATION OK")
            print(f"Context length is sufficient ({current_context:,} tokens)")
            print(f"No configuration changes needed.")
    
    def test_context_length(self, test_text: str = None) -> bool:
        """Test if the current configuration can handle a given text."""
        if not test_text:
            test_text = "Test text " * 5000  # Create a moderately large test
        
        try:
            from src.sync.processors.lm_studio_processor import LMStudioProcessor
            processor = LMStudioProcessor()
            
            print(f"\n🧪 Testing context length with {len(test_text):,} characters...")
            
            result = processor._process_owner(test_text, 'test_file.pdf', 'test_folder')
            
            if result is not None:
                print("✅ Test successful - context length is sufficient")
                return True
            else:
                print("❌ Test failed - context length may be insufficient")
                return False
                
        except Exception as e:
            print(f"❌ Test error: {e}")
            return False

def main():
    """Main function to run the configuration helper."""
    helper = LMStudioConfigHelper()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "diagnostic":
            helper.print_diagnostic_info()
        elif command == "guide":
            helper.print_configuration_guide()
        elif command == "test":
            helper.test_context_length()
        elif command == "interactive":
            helper.run_interactive_diagnostic()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: diagnostic, guide, test, interactive")
    else:
        # Default to interactive mode
        helper.run_interactive_diagnostic()

if __name__ == "__main__":
    main() 