import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Dropbox configuration
DROPBOX_FOLDER = os.getenv('DROPBOX_FOLDER', 'Accounts')
DROPBOX_USERNAME = os.getenv('DROPBOX_USERNAME')
DROPBOX_PASSWORD = os.getenv('DROPBOX_PASSWORD')

# Salesforce configuration
SALESFORCE_URL = os.getenv('SALESFORCE_URL', 'https://capitalprotect.lightning.force.com')
SALESFORCE_USERNAME = os.getenv('SALESFORCE_USERNAME')
SALESFORCE_PASSWORD = os.getenv('SALESFORCE_PASSWORD')

# File patterns
ACCOUNT_INFO_PATTERN = os.getenv('ACCOUNT_INFO_PATTERN', '*App.pdf')
DRIVERS_LICENSE_PATTERN = os.getenv('DRIVERS_LICENSE_PATTERN', '*DL.jpeg')

# Upload configuration
UPLOAD_TIMEOUT = int(os.getenv('UPLOAD_TIMEOUT', '300'))

# Browser configuration
CHROME_DEBUG_PORT = int(os.getenv('CHROME_DEBUG_PORT', '9222'))

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Temporary directory configuration
TEMP_DIR = os.getenv('TEMP_DIR', '/tmp/sync-files')

# Retry configuration
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))

# Batch processing configuration
MAX_BATCH_SIZE = int(os.getenv('MAX_BATCH_SIZE', '10')) 