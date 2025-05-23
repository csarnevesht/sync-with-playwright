"""Configuration constants for Dropbox operations."""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Dropbox folder configuration
DROPBOX_ROOT_FOLDER = os.getenv('DROPBOX_FOLDER', 'Accounts')

# File patterns
ACCOUNT_INFO_PATTERN = os.getenv('ACCOUNT_INFO_PATTERN', '*App.pdf')
DRIVERS_LICENSE_PATTERN = os.getenv('DRIVERS_LICENSE_PATTERN', '*DL.jpeg') 