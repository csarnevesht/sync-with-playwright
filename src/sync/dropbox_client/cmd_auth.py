#!/usr/bin/env python3

"""
Dropbox Authentication Helper

This script helps users get their initial Dropbox access and refresh tokens
through the OAuth2 flow. The tokens will be saved to the .env file.
"""

import argparse
import logging
from dotenv import load_dotenv
import os

from sync.dropbox_client.utils.auth import DropboxAuth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

def main():
    """Main function to handle Dropbox authentication."""
    parser = argparse.ArgumentParser(description='Get Dropbox OAuth2 tokens')
    parser.add_argument('--env-file', '-e', default='.env',
                      help='Path to .env file (default: .env)')
    args = parser.parse_args()
    
    try:
        # Initialize auth handler
        auth = DropboxAuth()
        
        # Get initial tokens
        access_token, refresh_token = auth.get_initial_tokens()
        
        # Update .env file
        env_path = args.env_file
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                lines = f.readlines()
            
            with open(env_path, 'w') as f:
                for line in lines:
                    if line.startswith('DROPBOX_TOKEN='):
                        f.write(f'DROPBOX_TOKEN={access_token}\n')
                    elif line.startswith('DROPBOX_REFRESH_TOKEN='):
                        f.write(f'DROPBOX_REFRESH_TOKEN={refresh_token}\n')
                    else:
                        f.write(line)
        else:
            with open(env_path, 'w') as f:
                f.write(f'DROPBOX_TOKEN={access_token}\n')
                f.write(f'DROPBOX_REFRESH_TOKEN={refresh_token}\n')
        
        logger.info("Successfully saved tokens to .env file")
        logger.info("You can now use the Dropbox client with automatic token refresh")
        
    except Exception as e:
        logger.error(f"Failed to get tokens: {str(e)}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main()) 