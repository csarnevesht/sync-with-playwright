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
            self.app_secret,
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