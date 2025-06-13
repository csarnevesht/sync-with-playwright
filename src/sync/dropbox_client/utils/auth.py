"""
Dropbox OAuth2 authentication utilities.
"""

import os
import logging
from typing import Optional, Tuple
from dotenv import load_dotenv
import dropbox

logger = logging.getLogger(__name__)

class DropboxAuth:
    """Handles Dropbox OAuth2 authentication and token refresh."""
    
    def __init__(self):
        """Initialize the auth handler."""
        load_dotenv()
        self.app_key = os.getenv('DROPBOX_APP_KEY')
        self.app_secret = os.getenv('DROPBOX_APP_SECRET')
        self.refresh_token = os.getenv('DROPBOX_REFRESH_TOKEN')
        
        if not all([self.app_key, self.app_secret]):
            raise ValueError("DROPBOX_APP_KEY and DROPBOX_APP_SECRET must be set in environment variables")
    
    def get_initial_tokens(self) -> Tuple[str, str]:
        """
        Get initial access and refresh tokens through OAuth2 flow.
        This should be used only once to get the initial tokens.
        
        Returns:
            Tuple[str, str]: (access_token, refresh_token)
        """
        auth_flow = dropbox.DropboxOAuth2FlowNoRedirect(
            self.app_key,
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
    
    def refresh_access_token(self) -> Optional[str]:
        """
        Refresh the access token using the refresh token.
        
        Returns:
            Optional[str]: New access token if successful, None otherwise
        """
        if not self.refresh_token:
            logger.error("No refresh token available")
            return None
            
        try:
            auth_flow = dropbox.DropboxOAuth2FlowNoRedirect(
                self.app_key,
                token_access_type='offline'
            )
            
            oauth_result = auth_flow.refresh_access_token(self.refresh_token)
            
            # Update environment variables
            os.environ['DROPBOX_TOKEN'] = oauth_result.access_token
            os.environ['DROPBOX_REFRESH_TOKEN'] = oauth_result.refresh_token
            
            # Update .env file
            self._update_env_file(oauth_result)
            
            logger.info("Successfully refreshed access token")
            return oauth_result.access_token
            
        except Exception as e:
            logger.error(f"Failed to refresh access token: {str(e)}")
            return None
    
    def _update_env_file(self, oauth_result):
        """Update the .env file with new tokens."""
        try:
            env_path = '.env'
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    lines = f.readlines()
                
                with open(env_path, 'w') as f:
                    for line in lines:
                        if line.startswith('DROPBOX_TOKEN='):
                            f.write(f'DROPBOX_TOKEN={oauth_result.access_token}\n')
                        elif line.startswith('DROPBOX_REFRESH_TOKEN='):
                            f.write(f'DROPBOX_REFRESH_TOKEN={oauth_result.refresh_token}\n')
                        else:
                            f.write(line)
            else:
                with open(env_path, 'w') as f:
                    f.write(f'DROPBOX_TOKEN={oauth_result.access_token}\n')
                    f.write(f'DROPBOX_REFRESH_TOKEN={oauth_result.refresh_token}\n')
                    
        except Exception as e:
            logger.error(f"Failed to update .env file: {str(e)}") 