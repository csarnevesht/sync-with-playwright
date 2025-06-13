#!/usr/bin/env python3

"""
Dropbox Token Generator

This script helps users get their initial Dropbox access and refresh tokens
through the OAuth2 flow. The tokens will be saved to the .env file.
"""

import os
import logging
from dotenv import load_dotenv
import dropbox

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

def get_initial_tokens(app_key: str, app_secret: str) -> tuple[str, str]:
    """
    Get initial access and refresh tokens through OAuth2 flow.
    
    Args:
        app_key: Dropbox app key
        app_secret: Dropbox app secret
        
    Returns:
        tuple[str, str]: (access_token, refresh_token)
    """
    auth_flow = dropbox.DropboxOAuth2FlowNoRedirect(
        app_key,
        app_secret,
        token_access_type='offline'
    )
    
    # Get the authorization URL
    authorize_url = auth_flow.start()
    print(f"1. Go to: {authorize_url}")
    print("2. Click 'Allow' (you might have to log in first)")
    print("3. Copy the authorization code")
    auth_code = input("Enter the authorization code here: ").strip()
    
    try:
        oauth_result = auth_flow.finish(auth_code)
        return oauth_result.access_token, oauth_result.refresh_token
    except Exception as e:
        logger.error(f"Failed to get initial tokens: {str(e)}")
        raise

def update_env_file(access_token: str, refresh_token: str, env_path: str = '.env'):
    """Update the .env file with new tokens."""
    try:
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
                
    except Exception as e:
        logger.error(f"Failed to update .env file: {str(e)}")
        raise

def main():
    """Main function to handle Dropbox authentication."""
    # Load environment variables
    load_dotenv()
    
    # Get app credentials
    app_key = os.getenv('DROPBOX_APP_KEY')
    app_secret = os.getenv('DROPBOX_APP_SECRET')
    
    if not app_key or not app_secret:
        print("Please set DROPBOX_APP_KEY and DROPBOX_APP_SECRET in your .env file")
        print("You can get these from https://www.dropbox.com/developers/apps")
        return 1
    
    try:
        # Get initial tokens
        access_token, refresh_token = get_initial_tokens(app_key, app_secret)
        
        # Update .env file
        update_env_file(access_token, refresh_token)
        
        logger.info("Successfully saved tokens to .env file")
        logger.info("You can now use the Dropbox client with automatic token refresh")
        
    except Exception as e:
        logger.error(f"Failed to get tokens: {str(e)}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main()) 