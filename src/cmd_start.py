import os
import sys
import logging
import subprocess
import platform
import time
import json
from pathlib import Path
from dotenv import load_dotenv
from sync.config import SALESFORCE_URL, CHROME_DEBUG_PORT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sync_services.log"),
        logging.StreamHandler()
    ]
)

def get_chrome_path():
    """Get the path to Chrome executable based on the platform."""
    if platform.system() == 'Darwin':  # macOS
        return '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    elif platform.system() == 'Windows':
        return r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    else:  # Linux
        return '/usr/bin/google-chrome'

def get_extension_path():
    """Get the absolute path to the Chrome extension directory."""
    # Get the project root directory (parent of src)
    project_root = Path(__file__).parent.parent
    extension_path = project_root / 'chrome_extension'
    if not extension_path.exists():
        raise FileNotFoundError(f"Chrome extension directory not found at: {extension_path}")
    return str(extension_path)

def setup_native_messaging():
    """Set up the native messaging host for the extension."""
    extension_path = get_extension_path()
    
    # Get Chrome user data directory
    if platform.system() == 'Darwin':  # macOS
        chrome_dir = os.path.expanduser('~/Library/Application Support/Google/Chrome')
    elif platform.system() == 'Windows':
        chrome_dir = os.path.expanduser('~\\AppData\\Local\\Google\\Chrome')
    else:  # Linux
        chrome_dir = os.path.expanduser('~/.config/google-chrome')
    
    # Set up native messaging host
    native_host_dir = os.path.join(chrome_dir, 'NativeMessagingHosts')
    os.makedirs(native_host_dir, exist_ok=True)
    
    # Make native host script executable
    native_host_path = os.path.join(extension_path, 'native_host.py')
    os.chmod(native_host_path, 0o755)
    
    # Create native messaging host manifest
    manifest = {
        "name": "com.command_launcher",
        "description": "Command Launcher Native Host",
        "path": os.path.abspath(native_host_path),
        "type": "stdio",
        "allowed_origins": [
            "chrome-extension://igdglpnaamkkfoojnlkindpbdmjebmhg/"
        ]
    }
    
    # Write manifest file
    manifest_path = os.path.join(native_host_dir, 'com.command_launcher.json')
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    return True

def start_browser():
    """Launch Chrome with remote debugging and load the extension."""
    # Load environment variables
    load_dotenv()

    chrome_path = get_chrome_path()
    extension_path = get_extension_path()
    user_data_dir = Path.cwd() / 'chrome-debug-profile'
    user_data_dir.mkdir(exist_ok=True)

    # Set up native messaging
    setup_native_messaging()

    # Start Chrome with remote debugging and extension
    cmd = [
        chrome_path,
        f'--remote-debugging-port={CHROME_DEBUG_PORT}',
        f'--load-extension={extension_path}',
        f'--user-data-dir={user_data_dir}',
        '--no-first-run',
        '--no-default-browser-check',
        '--enable-extensions',
        '--enable-automation',
        '--disable-extensions-file-access-check',
        '--enable-features=ExtensionsToolbarMenu',
        '--extensions-install-verification=false',
        '--allow-insecure-localhost',
        '--disable-web-security',
        '--allow-file-access-from-files',
        SALESFORCE_URL  # Open Salesforce URL directly
    ]

    logging.info(f"Starting Chrome with extension from: {extension_path}")
    process = subprocess.Popen(cmd)
    
    print(f"Opened {SALESFORCE_URL} in a new browser window.")
    print("Chrome extension should be automatically installed and visible in the toolbar.")
    print("If you don't see the extension icon, please check the extensions page (chrome://extensions)")
    input("Press Enter to close the browser...")
    
    # Terminate Chrome process
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()

def main():
    start_browser()

if __name__ == "__main__":
    main() 