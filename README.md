# Command Launcher Chrome Extension

This project includes a Chrome extension and a Python script to automatically install and run it.

## Prerequisites

1. Python 3.7 or higher
2. Google Chrome browser
3. Required Python packages:
   - websocket-client
   - psutil
   - python-dotenv
   - requests

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Install required Python packages:
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

## Development

The extension is located in the `chrome_extension` directory. To modify the extension:

1. Make your changes to the extension files
2. Run the script again to test your changes

## Support

If you encounter any issues, please:
1. Check the `sync_services.log` file for error messages
2. Make sure Chrome is up to date
3. Try running Chrome with a clean profile 