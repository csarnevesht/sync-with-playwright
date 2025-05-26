import os
import sys
import logging
import subprocess
import platform
import time
import json
import signal
import atexit
import psutil
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

def kill_chrome_processes():
    """Kill any existing Chrome processes using the debug port."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'chrome' in proc.info['name'].lower():
                # Check if this Chrome process is using our debug port
                cmdline = proc.info['cmdline']
                if cmdline and any(f'--remote-debugging-port={CHROME_DEBUG_PORT}' in arg for arg in cmdline):
                    logging.info(f"Killing existing Chrome process (PID: {proc.info['pid']})")
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

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

def cleanup_chrome_process(process):
    """Clean up Chrome process and its profile."""
    if process:
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        except Exception as e:
            logging.error(f"Error cleaning up Chrome process: {e}")

def setup_chrome_preferences(user_data_dir):
    """Set up Chrome preferences to automatically enable the extension."""
    preferences_dir = user_data_dir / 'Default'
    preferences_dir.mkdir(exist_ok=True)
    
    preferences_file = preferences_dir / 'Preferences'
    preferences = {
        "extensions": {
            "settings": {
                "igdglpnaamkkfoojnlkindpbdmjebmhg": {
                    "path": str(get_extension_path()),
                    "state": 1,
                    "installation_mode": "normal_installed",
                    "manifest": {
                        "name": "Command Launcher",
                        "version": "1.0",
                        "manifest_version": 3
                    }
                }
            }
        },
        "browser": {
            "enabled_labs_experiments": [
                "extensions-toolbar-menu@1"
            ]
        }
    }
    
    with open(preferences_file, 'w') as f:
        json.dump(preferences, f)

def start_browser():
    """Launch Chrome with remote debugging and load the extension."""
    # Load environment variables
    load_dotenv()

    # Kill any existing Chrome processes using our debug port
    kill_chrome_processes()

    chrome_path = get_chrome_path()
    extension_path = get_extension_path()
    user_data_dir = Path.cwd() / 'chrome-debug-profile'
    
    # Clean up any existing Chrome debug profile
    if user_data_dir.exists():
        try:
            import shutil
            for item in user_data_dir.iterdir():
                try:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                except Exception as e:
                    logging.warning(f"Could not remove {item}: {e}")
        except Exception as e:
            logging.error(f"Error cleaning up Chrome debug profile: {e}")
            return

    user_data_dir.mkdir(exist_ok=True)

    # Set up native messaging
    setup_native_messaging()
    
    # Set up Chrome preferences
    setup_chrome_preferences(user_data_dir)

    # Start Chrome with remote debugging and extension
    cmd = [
        chrome_path,
        f'--remote-debugging-port={CHROME_DEBUG_PORT}',
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
        '--force-dev-mode-highlighting',
        '--show-component-extension-options',
        '--enable-extensions-http-throttling=false',
        '--disable-extensions-http-throttling',
        '--disable-features=ExtensionsMenu',
        '--enable-features=ExtensionsToolbarMenu',
        '--enable-logging',
        '--v=1',
        '--enable-extension-activity-logging',
        '--enable-extension-activity-ui',
        '--load-extension=' + extension_path,
        SALESFORCE_URL
    ]

    logging.info(f"Starting Chrome with extension from: {extension_path}")
    process = subprocess.Popen(cmd)
    
    # Register cleanup handler
    atexit.register(cleanup_chrome_process, process)
    
    print(f"Opened {SALESFORCE_URL} in a new browser window.")
    print("\nChrome extension installation instructions:")
    print("1. Type 'chrome://extensions' in the address bar")
    print("2. Enable 'Developer mode' (top right)")
    print("3. Click 'Load unpacked'")
    print(f"4. Select this directory: {extension_path}")
    print("\nAfter installing the extension, you can access it from the toolbar.")
    
    try:
        input("\nPress Enter to close the browser...")
    except KeyboardInterrupt:
        print("\nClosing browser...")
    finally:
        cleanup_chrome_process(process)
        atexit.unregister(cleanup_chrome_process)

def main():
    start_browser()

if __name__ == "__main__":
    main() 