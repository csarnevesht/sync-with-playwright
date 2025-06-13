# Command Launcher Chrome Extension

This project includes a Chrome extension and a Python script to automatically install and run it.

## Prerequisites

1. Python 3.7 or higher
2. Google Chrome browser
3. Required system dependencies:
   - poppler (for PDF processing)
   - tesseract (for OCR)
4. Required Python packages:
   - websocket-client
   - psutil
   - python-dotenv
   - requests
   - pdf2image
   - pytesseract
   - Pillow
   - PyPDF2

## Dropbox Authentication

To use the Dropbox integration, you need to set up authentication:

1. Create a Dropbox app at https://www.dropbox.com/developers/apps
   - Choose "Scoped access"
   - Select "Full Dropbox" access type
   - Name your app and create it

2. Get your app credentials:
   - Copy the "App key" and "App secret" from your app's settings
   - Create a `.env` file in the project root if it doesn't exist
   - Add these lines to your `.env` file:
     ```
     DROPBOX_APP_KEY=your_app_key
     DROPBOX_APP_SECRET=your_app_secret
     ```

3. Get your access tokens:
   ```bash
   PYTHONPATH=src python -m sync.dropbox_client.get_tokens
   ```
   - Follow the prompts to authorize the app
   - The script will save your tokens to the `.env` file

4. Verify your `.env` file now contains:
   ```
   DROPBOX_APP_KEY=your_app_key
   DROPBOX_APP_SECRET=your_app_secret
   DROPBOX_TOKEN=your_access_token
   DROPBOX_REFRESH_TOKEN=your_refresh_token
   ```

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Install system dependencies:

For macOS:
```bash
brew install poppler tesseract
```

For Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils tesseract-ocr
```

For Windows:
- Download and install poppler from: https://github.com/oschwartz10612/poppler-windows/releases/
- Download and install tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
- Add both to your system PATH

3. Install required Python packages:
```bash
pip install -r requirements.txt
```

## Running the Extension

1. Simply run:
```bash
python -m src.cmd_start
```

The script will:
- Start Chrome with the extension automatically installed
- Open the Salesforce URL
- The extension will be available in the Chrome toolbar

## Troubleshooting

If you encounter any issues:

1. Make sure Chrome is installed in the default location for your operating system:
   - macOS: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
   - Windows: `C:\Program Files\Google\Chrome\Application\chrome.exe`
   - Linux: `/usr/bin/google-chrome`

2. If Chrome is installed in a different location, you can set the `CHROME_PATH` environment variable:
```bash
# macOS/Linux
export CHROME_PATH="/path/to/your/chrome"

# Windows
set CHROME_PATH=C:\path\to\your\chrome.exe
```

3. If you want to use a different user data directory, set the `CHROME_USER_DATA_DIR` environment variable:
```bash
# macOS/Linux
export CHROME_USER_DATA_DIR="/path/to/your/chrome/profile"

# Windows
set CHROME_USER_DATA_DIR=C:\path\to\your\chrome\profile
```

4. If you encounter PDF or OCR related issues:
   - Verify poppler is installed and in PATH: `poppler --version`
   - Verify tesseract is installed and in PATH: `tesseract --version`
   - Check if the required Python packages are installed: `pip list | grep -E "pdf2image|pytesseract|Pillow|PyPDF2"`

## Development

The extension is located in the `chrome_extension` directory. To modify the extension:

1. Make your changes to the extension files
2. Run the script again to test your changes

## Support

If you encounter any issues, please:
1. Check the `sync_services.log` file for error messages
2. Make sure Chrome is up to date
3. Try running Chrome with a clean profile
4. Verify all system dependencies are properly installed 