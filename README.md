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

4. First-time setup: Start Chrome with remote debugging enabled and log in to Salesforce CRM:
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=./chrome-debug-profile
```
Then:
- Log in to Salesforce CRM in this Chrome instance
- Your login session, cookies, and other data will be saved in the `chrome-debug-profile` directory
- You can close this Chrome window after logging in

5. For subsequent runs: Start Chrome with the same user data directory:
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=./chrome-debug-profile
```
The script will use this Chrome instance with your saved session.

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
- `CHROME_USER_DATA_DIR`: Path to Chrome user data directory (default: "./chrome-debug-profile")

#### Logging Configuration
- `LOG_LEVEL`: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

#### Temporary Directory Configuration
- `TEMP_DIR`: Base directory for temporary files

#### Retry Configuration
- `MAX_RETRIES`: Number of retries for failed uploads (default: 3)

#### Batch Processing Configuration
- `MAX_BATCH_SIZE`: Maximum number of files to upload in a single batch (default: 10)

## Usage

1. Start Chrome with remote debugging and your saved profile:
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=./chrome-debug-profile
```
⚠️ Important: Keep this Chrome window running while using the script.

2. In a new terminal window, run the synchronization script:
```bash
python main.py
```

The script will:
- Connect to the running Chrome instance using the debugging port
- Use the saved session data from `./chrome-debug-profile` (cookies, login state, etc.)
- Connect to Dropbox using the provided token
- Process each account folder in the root folder
- Create or update accounts in Salesforce CRM
- Synchronize files between Dropbox and Salesforce

## Troubleshooting

If you see an error like `connect ECONNREFUSED ::1:9222`:
1. Make sure Chrome is running with remote debugging enabled (step 1 above)
2. Verify Chrome is running on port 9222 by visiting `http://localhost:9222` in another browser
3. Check that you're using the correct user data directory path
4. Ensure no other Chrome instances are using the same debugging port

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