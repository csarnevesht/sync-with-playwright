#!/usr/bin/env python3
"""
Quick LM Studio Status Check

Usage:
    python check_lm_studio.py          # Quick status check
    python check_lm_studio.py fix      # Show configuration guide
    python check_lm_studio.py test     # Test context length
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sync.utils.lm_studio_config_helper import LMStudioConfigHelper

def main():
    helper = LMStudioConfigHelper()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "fix":
            print("🔧 LM Studio Configuration Guide")
            helper.print_configuration_guide()
        elif command == "test":
            print("🧪 Testing LM Studio Context Length")
            helper.test_context_length()
        elif command == "status":
            print("📊 LM Studio Status Check")
            helper.print_diagnostic_info()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: fix, test, status")
    else:
        # Quick status check
        print("🔍 Quick LM Studio Status Check")
        print("=" * 40)
        
        # Check server
        server_ok = helper.check_server_availability()
        print(f"Server: {'✅ Running' if server_ok else '❌ Not running'}")
        
        if server_ok:
            # Check model
            model_ok = helper.check_model_loaded()
            print(f"Model:  {'✅ Loaded' if model_ok else '❌ Not loaded'}")
            
            # Check context length
            context_length = helper.get_current_context_length()
            if context_length:
                if context_length >= 32768:
                    print(f"Context: ✅ {context_length:,} tokens (OK)")
                else:
                    print(f"Context: ❌ {context_length:,} tokens (Need 32K+)")
                    print("\n💡 Run 'python check_lm_studio.py fix' for configuration guide")
            else:
                print(f"Context: ❓ Unknown")
        else:
            print("\n💡 Please start LM Studio application")

if __name__ == "__main__":
    main() 