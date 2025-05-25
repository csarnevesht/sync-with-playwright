# My Chrome Extension

This is a simple Chrome extension that allows you to interact with the current tab in your browser.

## Features

- Execute a script in the current tab with a single click.

## Installation

1. Open Chrome and navigate to `chrome://extensions/`.
2. Enable "Developer mode" in the top right corner.
3. Click "Load unpacked" and select the `chrome_extension` directory.

## Usage

1. Click on the extension icon in the toolbar to open the popup.
2. Click the "Run Script" button to execute the script in the current tab.

## Files

- **manifest.json**: Defines the extension's properties and permissions.
- **popup.html**: A simple HTML file with a button to trigger the script.
- **popup.js**: JavaScript file to handle the button click and execute a script in the current tab.
- **background.js**: A background script that logs a message when the extension is installed.

## Development

Feel free to modify the `popup.js` file to add your own script logic. 