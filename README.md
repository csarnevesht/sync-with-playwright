# Dropbox to Salesforce CRM Synchronization

This project synchronizes files from Dropbox to Salesforce CRM using Playwright for browser automation.

## Prerequisites

- Python 3.8 or higher
- Chrome browser
- Dropbox API token
- Salesforce CRM access

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:
```bash
playwright install chromium
```

3. Create a `token.txt` file with your Dropbox API token, or the script will prompt you for it.

4. Start Chrome with remote debugging enabled:
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
```

5. Log in to Salesforce CRM in the Chrome browser that was just started.

## Configuration

Copy `env.example` to `.env` and modify the values as needed:

```bash
cp env.example .env
```

### Environment Variables

#### Dropbox Configuration
- `DROPBOX_ROOT_FOLDER`: The root folder in Dropbox containing account folders (default: "Wealth Management")

#### Salesforce Configuration
- `SALESFORCE_URL`: The URL of your Salesforce CRM instance

#### File Pattern Configuration
- `ACCOUNT_INFO_PATTERN`: Pattern for account info files (default: "*App.pdf")
- `DRIVERS_LICENSE_PATTERN`: Pattern for driver's license files (default: "*DL.jpeg")

#### Upload Configuration
- `UPLOAD_TIMEOUT`: Maximum time to wait for file upload in seconds (default: 300)

#### Browser Configuration
- `CHROME_DEBUG_PORT`: Chrome debugging port (default: 9222)

#### Logging Configuration
- `LOG_LEVEL`: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

#### Temporary Directory Configuration
- `TEMP_DIR`: Base directory for temporary files

#### Retry Configuration
- `MAX_RETRIES`: Number of retries for failed uploads (default: 3)

#### Batch Processing Configuration
- `MAX_BATCH_SIZE`: Maximum number of files to upload in a single batch (default: 10)

## Usage

1. Make sure Chrome is running with remote debugging enabled and you're logged into Salesforce CRM.

2. Run the synchronization script:
```bash
python main.py
```

The script will:
- Connect to Dropbox using the provided token
- Process each account folder in the root folder
- Create or update accounts in Salesforce CRM
- Synchronize files between Dropbox and Salesforce

## File Structure

- `main.py`: Main script that orchestrates the synchronization process
- `dropbox_client.py`: Dropbox API integration
- `salesforce/pages/accounts_page.py`: Salesforce page objects
- `config.py`: Configuration settings
- `requirements.txt`: Python dependencies
- `env.example`: Example environment variables
- `README.design.md`: Detailed design documentation

## Notes

- The script uses the existing Chrome browser session where you're already logged into Salesforce CRM
- Files are downloaded from Dropbox with their modification date as a prefix
- The script handles both new accounts and existing accounts
- File upload dialog handling is implemented with progress monitoring and verification 