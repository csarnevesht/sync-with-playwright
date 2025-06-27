#!/usr/bin/env python3
"""
Wrapper script for search_dropbox_accounts.py that accepts command-line arguments
"""

import sys
import subprocess
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='Search Dropbox accounts with command-line arguments')
    parser.add_argument('--type', '-t', choices=['exact', 'partial', 'list', 'stats', 'no-client-list'], 
                       default='exact', help='Search type')
    parser.add_argument('--term', '-s', help='Search term (required for exact and partial searches)')
    parser.add_argument('--output', '-o', help='Output file to save results')
    
    args = parser.parse_args()
    
    # Map search types to menu choices
    type_map = {
        'exact': '1',
        'partial': '2', 
        'list': '3',
        'stats': '4',
        'no-client-list': '5'
    }
    
    choice = type_map[args.type]
    
    # Build input string
    inputs = [choice]
    
    if args.type in ['exact', 'partial']:
        if not args.term:
            print("❌ Error: Search term is required for exact and partial searches")
            sys.exit(1)
        inputs.append(args.term)
    
    # Add exit command
    inputs.append('6')
    
    # Convert to newline-separated string
    input_str = '\n'.join(inputs) + '\n'
    
    # Run the search script
    script_path = Path(__file__).parent / 'search_dropbox_accounts.py'
    
    try:
        if args.output:
            # Save output to file
            result = subprocess.run(
                [sys.executable, str(script_path)],
                input=input_str,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent.parent
            )
            with open(args.output, 'w') as f:
                f.write(result.stdout)
                if result.stderr:
                    f.write(f"\nSTDERR:\n{result.stderr}")
            print(f"✅ Results saved to {args.output}")
        else:
            # Display output directly
            result = subprocess.run(
                [sys.executable, str(script_path)],
                input=input_str,
                text=True,
                cwd=Path(__file__).parent.parent.parent
            )
            
    except Exception as e:
        print(f"❌ Error running search script: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 