"""
Chrome Extension Launcher and Server Manager

This module provides functionality to:
1. Launch Chrome with a custom extension
2. Manage a Flask server for command execution
3. Handle native messaging between Chrome and Python
4. Monitor and maintain server health
5. Clean up processes on exit

The module implements a watchdog system that ensures the server stays running
and automatically restarts it if it crashes. It also handles the installation
and configuration of the Chrome extension and its native messaging host.

Key Features:
- Automatic server monitoring and recovery
- Chrome extension installation and configuration
- Native messaging host setup
- Process cleanup and resource management
- Comprehensive logging

Usage:
    python -m src.cmd_start

Dependencies:
    - psutil: For process management
    - requests: For HTTP requests
    - websocket-client: For Chrome DevTools Protocol
    - python-dotenv: For environment variable management
"""

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
import requests
import websocket
import threading
import shutil
from pathlib import Path
from dotenv import load_dotenv
from sync.config import (
    SALESFORCE_URL, 
    CHROME_DEBUG_PORT, 
    SALESFORCE_USERNAME, 
    SALESFORCE_PASSWORD,
    DROPBOX_ROOT_FOLDER
)

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
    """
    Kill any existing Chrome processes using the debug port.
    
    This function:
    1. Iterates through all running processes
    2. Identifies Chrome processes using our debug port
    3. Terminates them to ensure a clean state
    
    Returns:
        None
    """
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'chrome' in proc.info['name'].lower():
                # Only kill Chrome processes using our debug port
                cmdline = proc.info['cmdline']
                if cmdline and any(f'--remote-debugging-port={CHROME_DEBUG_PORT}' in arg for arg in cmdline):
                    logging.info(f"Killing Chrome process (PID: {proc.info['pid']})")
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    # Wait a moment for processes to be killed
    time.sleep(2)

def get_chrome_path():
    """
    Get the path to Chrome executable based on the platform.
    
    This function:
    1. Checks for a custom path in environment variables
    2. Falls back to platform-specific default paths
    3. Supports macOS, Windows, and Linux
    
    Returns:
        str: Path to Chrome executable
    """
    # Allow override via environment variable
    custom_path = os.getenv('CHROME_PATH')
    if custom_path:
        return custom_path
        
    if platform.system() == 'Darwin':  # macOS
        return '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    elif platform.system() == 'Windows':
        return r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    else:  # Linux
        return '/usr/bin/google-chrome'

def get_extension_path():
    """
    Get the absolute path to the Chrome extension directory.
    
    This function:
    1. Determines the project root directory
    2. Locates the chrome_extension directory
    3. Verifies its existence
    
    Returns:
        str: Absolute path to the extension directory
        
    Raises:
        FileNotFoundError: If the extension directory doesn't exist
    """
    # Get the project root directory (parent of src)
    project_root = Path(__file__).parent.parent
    extension_path = project_root / 'chrome_extension'
    if not extension_path.exists():
        raise FileNotFoundError(f"Chrome extension directory not found at: {extension_path}")
    return str(extension_path)

def get_user_data_dir():
    """
    Get the user data directory path for Chrome.
    
    This function:
    1. Checks for a custom directory in environment variables
    2. Uses existing debug profile directory if it exists
    3. Creates a new debug profile directory only if needed
    
    Returns:
        Path: Path object for the user data directory
    """
    # Allow override via environment variable
    custom_dir = os.getenv('CHROME_USER_DATA_DIR')
    if custom_dir:
        return Path(custom_dir)
        
    # Use existing debug profile directory or create a new one
    debug_dir = Path.home() / '.chrome-debug-profile'
    debug_dir.mkdir(exist_ok=True)
    return debug_dir

def read_manifest_file(manifest_path):
    """
    Read and parse a JSON manifest file.
    
    Args:
        manifest_path (str): Path to the manifest file
        
    Returns:
        dict: Parsed JSON content or None if error
    """
    try:
        with open(manifest_path) as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error reading file: {e}")
        return None

def read_manifest():
    """
    Read the extension's manifest file.
    
    This function:
    1. Locates the manifest.json file
    2. Reads and parses its contents
    3. Logs the manifest contents
    
    Returns:
        dict: Manifest contents
        
    Raises:
        FileNotFoundError: If manifest.json doesn't exist
    """
    extension_path = get_extension_path()
    manifest_path = Path(extension_path) / 'manifest.json'
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found at: {manifest_path}")
    
    manifest = read_manifest_file(manifest_path)
    if manifest:
        logging.info(f"Manifest contents: {json.dumps(manifest, indent=2)}")
    return manifest

def setup_native_messaging():
    """Set up the native messaging host for the extension."""
    extension_path = get_extension_path()
    logging.info(f"Setting up native messaging host from: {extension_path}")
    
    # Get Chrome user data directory
    if platform.system() == 'Darwin':  # macOS
        chrome_dir = os.path.expanduser('~/Library/Application Support/Google/Chrome')
        native_host_dir = os.path.join(chrome_dir, 'NativeMessagingHosts')
    elif platform.system() == 'Windows':
        chrome_dir = os.path.expanduser('~\\AppData\\Local\\Google\\Chrome')
        native_host_dir = os.path.join(chrome_dir, 'NativeMessagingHosts')
    else:  # Linux
        chrome_dir = os.path.expanduser('~/.config/google-chrome')
        native_host_dir = os.path.join(chrome_dir, 'NativeMessagingHosts')
    
    # Create native messaging host directory
    os.makedirs(native_host_dir, exist_ok=True)
    logging.info(f"Created native messaging host directory: {native_host_dir}")
    
    # Create native host script if it doesn't exist
    native_host_path = os.path.join(extension_path, 'native_host.py')
    if not os.path.exists(native_host_path):
        logging.info(f"Creating native host script at: {native_host_path}")
        native_host_content = '''#!/usr/bin/env python3
import sys
import json
import struct
import logging
import subprocess
import os
import signal
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='native_host.log',
    filemode='a'
)

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_SCRIPT = os.path.join(os.path.dirname(SCRIPT_DIR), 'server.py')

server_process = None

def send_message(message):
    """Send a message to Chrome."""
    sys.stdout.buffer.write(struct.pack('I', len(message)))
    sys.stdout.buffer.write(message.encode('utf-8'))
    sys.stdout.buffer.flush()

def read_message():
    """Read a message from Chrome."""
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        return None
    message_length = struct.unpack('I', raw_length)[0]
    message = sys.stdin.buffer.read(message_length).decode('utf-8')
    return json.loads(message)

def is_server_running():
    try:
        import requests
        requests.get('http://localhost:5001/api/commands', timeout=1)
        return True
    except:
        return False

def start_server():
    global server_process
    if is_server_running():
        return True
    try:
        server_process = subprocess.Popen(
            [sys.executable, SERVER_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        # Wait for server to start
        for _ in range(10):
            if is_server_running():
                return True
            time.sleep(0.5)
        return False
    except Exception as e:
        logging.error(f"Error starting server: {e}")
        return False

def stop_server():
    global server_process
    # Try to stop by process if we started it
    if server_process and server_process.poll() is None:
        server_process.terminate()
        try:
            server_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            server_process.kill()
        server_process = None
        return True
    # Try to stop by finding the process (if started elsewhere)
    # (Optional: implement with psutil if needed)
    return False

def restart_server():
    stop_server()
    return start_server()

def main():
    try:
        while True:
            message = read_message()
            if message is None:
                break
            
            logging.info(f"Received message: {message}")
            action = message.get('action')
            
            if action == 'start_server':
                success = start_server()
                send_message(json.dumps({
                    'status': 'success' if success else 'error',
                    'message': 'Server started' if success else 'Failed to start server'
                }))
            elif action == 'stop_server':
                success = stop_server()
                send_message(json.dumps({
                    'status': 'success' if success else 'error',
                    'message': 'Server stopped' if success else 'Failed to stop server'
                }))
            elif action == 'restart_server':
                success = restart_server()
                send_message(json.dumps({
                    'status': 'success' if success else 'error',
                    'message': 'Server restarted' if success else 'Failed to restart server'
                }))
            elif action == 'runCommand':
                try:
                    # Execute the command
                    result = subprocess.run(
                        message.get('command', '').split(),
                        capture_output=True,
                        text=True
                    )
                    
                    # Send response back to Chrome
                    response = {
                        'status': 'success' if result.returncode == 0 else 'error',
                        'output': result.stdout,
                        'error': result.stderr
                    }
                except Exception as e:
                    response = {
                        'status': 'error',
                        'error': str(e)
                    }
                
                logging.info(f"Sending response: {response}")
                send_message(json.dumps(response))
    
    except Exception as e:
        logging.error(f"Error in native host: {e}")
        send_message(json.dumps({
            'status': 'error',
            'error': str(e)
        }))

if __name__ == '__main__':
    main()
'''
        with open(native_host_path, 'w') as f:
            f.write(native_host_content)
    
    # Make native host script executable
    os.chmod(native_host_path, 0o755)
    logging.info(f"Made native host script executable: {native_host_path}")
    
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
    logging.info(f"Writing native messaging host manifest to: {manifest_path}")
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    # Also install in the system-wide location for macOS
    if platform.system() == 'Darwin':
        system_manifest_dir = '/Library/Google/Chrome/NativeMessagingHosts'
        if os.path.exists(system_manifest_dir):
            system_manifest_path = os.path.join(system_manifest_dir, 'com.command_launcher.json')
            logging.info(f"Writing system-wide native messaging host manifest to: {system_manifest_path}")
            try:
                with open(system_manifest_path, 'w') as f:
                    json.dump(manifest, f, indent=2)
            except PermissionError:
                logging.warning("Could not write to system-wide location. Using user-specific location only.")
    
    logging.info("Native messaging host setup complete")
    return True

def cleanup_chrome_process(process):
    """
    Clean up Chrome process and its profile.
    
    This function:
    1. Terminates the Chrome process gracefully
    2. Falls back to force kill if necessary
    3. Handles cleanup errors gracefully
    
    Args:
        process (subprocess.Popen): The Chrome process to clean up
    """
    if process:
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        except Exception as e:
            logging.error(f"Error cleaning up Chrome process: {e}")

def setup_chrome_preferences(user_data_dir):
    """
    Set up Chrome preferences to automatically enable the extension.
    
    This function:
    1. Creates necessary directories
    2. Configures extension settings
    3. Enables developer mode
    4. Sets up toolbar visibility
    
    Args:
        user_data_dir (Path): Path to Chrome user data directory
    """
    preferences_dir = user_data_dir / 'Default'
    preferences_dir.mkdir(exist_ok=True)
    
    # Get the extension path
    extension_path = get_extension_path()
    logging.info(f"Setting up Chrome preferences with extension path: {extension_path}")
    
    # Read the manifest to get extension details
    manifest = read_manifest()
    if not manifest:
        raise Exception("Could not read manifest.json")
    
    logging.info(f"Manifest contents: {json.dumps(manifest, indent=2)}")
    
    # Use the extension ID from the manifest key
    extension_id = "igdglpnaamkkfoojnlkindpbdmjebmhg"
    
    # Read existing preferences if they exist
    preferences_file = preferences_dir / 'Preferences'
    existing_preferences = {}
    if preferences_file.exists():
        try:
            with open(preferences_file, 'r') as f:
                existing_preferences = json.load(f)
            logging.info("Loaded existing Chrome preferences")
        except Exception as e:
            logging.warning(f"Could not read existing preferences: {e}")
    
    # Update only the extension-related preferences
    if 'extensions' not in existing_preferences:
        existing_preferences['extensions'] = {}
    if 'settings' not in existing_preferences['extensions']:
        existing_preferences['extensions']['settings'] = {}
    
    # Add or update our extension settings
    existing_preferences['extensions']['settings'][extension_id] = {
        "path": str(extension_path),
        "state": 1,  # 1 = enabled
        "installation_mode": "normal_installed",
        "manifest": manifest,
        "location": 1,  # 1 = local
        "preferences": {
            "extensions": {
                "toolbar": {
                    "visible": True
                }
            }
        }
    }
    
    # Ensure developer mode is enabled
    if 'extensions' not in existing_preferences:
        existing_preferences['extensions'] = {}
    existing_preferences['extensions']['ui'] = {
        "developer_mode": True
    }
    
    # Add extension to toolbar
    if 'browser' not in existing_preferences:
        existing_preferences['browser'] = {}
    if 'enabled_labs_experiments' not in existing_preferences['browser']:
        existing_preferences['browser']['enabled_labs_experiments'] = []
    if 'extensions_toolbar_visible' not in existing_preferences['browser']:
        existing_preferences['browser']['extensions_toolbar_visible'] = True
    
    # Add extension to toolbar
    if 'extensions' not in existing_preferences:
        existing_preferences['extensions'] = {}
    if 'toolbar' not in existing_preferences['extensions']:
        existing_preferences['extensions']['toolbar'] = {}
    if 'visible' not in existing_preferences['extensions']['toolbar']:
        existing_preferences['extensions']['toolbar']['visible'] = True
    
    # Write back the updated preferences
    with open(preferences_file, 'w') as f:
        json.dump(existing_preferences, f)
    logging.info(f"Updated preferences file at: {preferences_file}")
    
    # Also update the Local State file to ensure extension is enabled
    local_state_file = user_data_dir / 'Local State'
    local_state = {}
    if local_state_file.exists():
        try:
            with open(local_state_file, 'r') as f:
                local_state = json.load(f)
        except Exception as e:
            logging.warning(f"Could not read Local State file: {e}")
    
    if 'profile' not in local_state:
        local_state['profile'] = {}
    if 'default_content_setting_values' not in local_state['profile']:
        local_state['profile']['default_content_setting_values'] = {}
    local_state['profile']['default_content_setting_values']['extensions'] = 1
    
    with open(local_state_file, 'w') as f:
        json.dump(local_state, f)
    logging.info(f"Updated Local State file at: {local_state_file}")

def check_extension_status():
    """
    Continuously check for the extension until it's found or timeout.
    
    This function:
    1. Polls Chrome's debugging port for extension pages
    2. Verifies extension installation and status
    3. Provides user feedback and troubleshooting steps
    
    Returns:
        bool: True if extension is found and loaded, False otherwise
    """
    max_attempts = 30  # Try for 30 seconds
    attempt = 0
    
    # Get extension path
    extension_path = get_extension_path()
    
    while attempt < max_attempts:
        try:
            print(f"\nChecking for extension (attempt {attempt + 1}/{max_attempts})...")
            
            # Wait for Chrome to start and debugging port to be available
            time.sleep(2)  # Give Chrome time to start
            
            # Get list of pages from Chrome's debugging port
            try:
                response = requests.get(f'http://localhost:{CHROME_DEBUG_PORT}/json', timeout=5)
                pages = response.json()
                print(f"\nFound {len(pages)} pages in Chrome")
            except requests.exceptions.ConnectionError:
                print("\nWaiting for Chrome to start...")
                time.sleep(1)
                attempt += 1
                continue
            except requests.exceptions.Timeout:
                print("\nTimeout waiting for Chrome response...")
                time.sleep(1)
                attempt += 1
                continue
            
            # Look for our extension's pages
            extension_pages = []
            for page in pages:
                url = page.get('url', '')
                if 'chrome-extension://' in url:
                    print(f"\nFound extension page: {url}")
                    extension_pages.append(page)
            
            if extension_pages:
                print(f"\nFound {len(extension_pages)} extension pages")
                for page in extension_pages:
                    print(f"- {page.get('url')}")
                    
                    # Try to connect to each extension page
                    ws_url = page.get('webSocketDebuggerUrl')
                    if ws_url:
                        try:
                            print(f"\nConnecting to extension page: {ws_url}")
                            ext_ws = websocket.create_connection(ws_url, timeout=5)
                            
                            try:
                                # Try to get extension info
                                ext_ws.send(json.dumps({
                                    "id": 1,
                                    "method": "Runtime.evaluate",
                                    "params": {
                                        "expression": """
                                        (function() {
                                            try {
                                                if (chrome && chrome.runtime) {
                                                    const manifest = chrome.runtime.getManifest();
                                                    console.log('Extension manifest:', manifest);
                                                    return {
                                                        id: chrome.runtime.id,
                                                        manifest: manifest,
                                                        lastError: chrome.runtime.lastError ? chrome.runtime.lastError.message : null
                                                    };
                                                }
                                                return { error: 'Chrome runtime API not available' };
                                            } catch (e) {
                                                console.error('Error getting extension info:', e);
                                                return { error: e.toString() };
                                            }
                                        })()
                                        """
                                    }
                                }))
                                
                                response = json.loads(ext_ws.recv())
                                print(f"\nExtension info response: {json.dumps(response, indent=2)}")
                                
                                if 'result' in response and 'result' in response['result']:
                                    # Get the object ID
                                    object_id = response['result']['result'].get('objectId')
                                    if object_id:
                                        # Request the object properties
                                        ext_ws.send(json.dumps({
                                            "id": 2,
                                            "method": "Runtime.getProperties",
                                            "params": {
                                                "objectId": object_id,
                                                "ownProperties": True
                                            }
                                        }))
                                        
                                        props_response = json.loads(ext_ws.recv())
                                        print(f"\nProperties response: {json.dumps(props_response, indent=2)}")
                                        
                                        if 'result' in props_response and 'result' in props_response['result']:
                                            properties = props_response['result']['result']
                                            extension_id = None
                                            manifest_obj_id = None
                                            
                                            for prop in properties:
                                                if prop['name'] == 'id' and 'value' in prop:
                                                    extension_id = prop['value'].get('value')
                                                elif prop['name'] == 'manifest' and 'value' in prop:
                                                    manifest_obj_id = prop['value'].get('objectId')
                                            
                                            if manifest_obj_id:
                                                # Get manifest properties
                                                ext_ws.send(json.dumps({
                                                    "id": 3,
                                                    "method": "Runtime.getProperties",
                                                    "params": {
                                                        "objectId": manifest_obj_id,
                                                        "ownProperties": True
                                                    }
                                                }))
                                                
                                                manifest_response = json.loads(ext_ws.recv())
                                                print(f"\nManifest properties: {json.dumps(manifest_response, indent=2)}")
                                                
                                                if 'result' in manifest_response and 'result' in manifest_response['result']:
                                                    manifest_props = manifest_response['result']['result']
                                                    manifest_data = {}
                                                    for manifest_prop in manifest_props:
                                                        if 'value' in manifest_prop:
                                                            manifest_data[manifest_prop['name']] = manifest_prop['value'].get('value')
                                                    
                                                    print("\nFound extension manifest:")
                                                    print(f"- ID: {extension_id}")
                                                    print(f"- Name: {manifest_data.get('name')}")
                                                    print(f"- Version: {manifest_data.get('version')}")
                                                    
                                                    if manifest_data.get('name') == "Command Launcher":
                                                        print("\nCommand Launcher extension is loaded!")
                                                        print(f"Extension ID: {extension_id}")
                                                        return True
                            finally:
                                ext_ws.close()
                        except Exception as e:
                            print(f"\nError connecting to extension page: {e}")
            
            print("\nCommand Launcher extension not found yet...")
            print("\nPlease check the following:")
            print("1. Open chrome://extensions in the browser")
            print("2. Make sure 'Developer mode' is enabled (top right)")
            print("3. Look for any error messages related to the extension")
            print("4. Try clicking 'Load unpacked' and select:")
            print(f"   {extension_path}")
            
            # Wait before next attempt
            time.sleep(1)
            attempt += 1
                
        except Exception as e:
            print(f"\nERROR checking extension status: {e}")
            print("\nPlease check the following:")
            print("1. Open chrome://extensions in the browser")
            print("2. Make sure 'Developer mode' is enabled (top right)")
            print("3. Look for any error messages related to the extension")
            print("4. Try clicking 'Load unpacked' and select:")
            print(f"   {extension_path}")
            
            # Wait before next attempt
            time.sleep(1)
            attempt += 1
    
    print("\nTimed out waiting for extension to load.")
    return False

def ensure_extension_installed(user_data_dir):
    """
    Ensure the extension is properly installed and enabled.
    
    This function:
    1. Checks if extension is already installed
    2. Only copies extension files if not already present
    3. Sets up extension metadata if needed
    
    Args:
        user_data_dir (Path): Path to Chrome user data directory
        
    Returns:
        str: Extension ID
    """
    extension_path = get_extension_path()
    logging.info(f"Checking extension installation from: {extension_path}")
    
    # Create the Extensions directory if it doesn't exist
    extensions_dir = user_data_dir / 'Default' / 'Extensions'
    extensions_dir.mkdir(parents=True, exist_ok=True)
    
    # Use the extension ID from the manifest key
    extension_id = "igdglpnaamkkfoojnlkindpbdmjebmhg"
    extension_dir = extensions_dir / extension_id
    
    # Check if extension is already installed
    if extension_dir.exists():
        logging.info(f"Extension already installed at: {extension_dir}")
        return extension_id
    
    # Copy the extension files only if not already installed
    logging.info(f"Installing extension from {extension_path} to {extension_dir}")
    shutil.copytree(extension_path, extension_dir)
    
    # Create the _metadata directory
    metadata_dir = extension_dir / '_metadata'
    metadata_dir.mkdir(exist_ok=True)
    
    # Create the verified_contents.json file
    verified_contents = {
        "version": 1,
        "content_verifications": {
            extension_id: {
                "version": 1,
                "hash": "sha256",
                "content_hash": "sha256"
            }
        }
    }
    
    with open(metadata_dir / 'verified_contents.json', 'w') as f:
        json.dump(verified_contents, f)
    
    # Create the manifest.json file in the extension directory
    manifest = read_manifest()
    if manifest:
        logging.info(f"Writing manifest.json to {extension_dir}")
        with open(extension_dir / 'manifest.json', 'w') as f:
            json.dump(manifest, f, indent=2)
    
    # Create the background.js file if it doesn't exist
    background_js = extension_dir / 'background.js'
    if not background_js.exists():
        logging.info(f"Creating background.js in {extension_dir}")
        with open(background_js, 'w') as f:
            f.write("""
// Listen for extension installation
chrome.runtime.onInstalled.addListener(() => {
    console.log('Command Launcher extension installed');
    startServer();
});

// Listen for extension startup
chrome.runtime.onStartup.addListener(() => {
    console.log('Command Launcher extension started');
    startServer();
});

// Function to start the server
function startServer() {
    try {
        const port = chrome.runtime.connectNative('com.command_launcher');
        
        port.onMessage.addListener((response) => {
            console.log('Server start response:', response);
            if (response.status === 'success') {
                console.log('Server started successfully');
            } else {
                console.error('Failed to start server:', response.message);
            }
        });
        
        port.onDisconnect.addListener(() => {
            const error = chrome.runtime.lastError;
            console.log('Native host disconnected:', error);
        });
        
        port.postMessage({ action: 'start_server' });
    } catch (error) {
        console.error('Error starting server:', error);
    }
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('Received message:', request);
    if (request.action === 'runCommand') {
        try {
            // Connect to native host
            const port = chrome.runtime.connectNative('com.command_launcher');
            
            // Set up message handler
            port.onMessage.addListener((response) => {
                console.log('Native host response:', response);
                sendResponse(response);
            });
            
            // Set up disconnect handler
            port.onDisconnect.addListener(() => {
                const error = chrome.runtime.lastError;
                console.log('Native host disconnected:', error);
                sendResponse({ 
                    status: 'error', 
                    message: error ? error.message : 'Native host disconnected' 
                });
            });
            
            // Send the command to the native host
            port.postMessage({ 
                action: 'runCommand',
                command: request.command || 'echo "No command specified"'
            });
            
            return true;  // Keep the message channel open for async response
        } catch (error) {
            console.error('Error connecting to native host:', error);
            sendResponse({ 
                status: 'error', 
                message: error.message || 'Failed to connect to native host' 
            });
        }
    }
});
            """.strip())
    
    # Create the popup.html file if it doesn't exist
    popup_html = extension_dir / 'popup.html'
    if not popup_html.exists():
        logging.info(f"Creating popup.html in {extension_dir}")
        with open(popup_html, 'w') as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Command Launcher</title>
    <style>
        body { width: 300px; padding: 10px; }
        button { width: 100%; margin: 5px 0; padding: 8px; }
        #output { margin-top: 10px; padding: 5px; border: 1px solid #ccc; }
    </style>
</head>
<body>
    <h2>Command Launcher</h2>
    <button id="runCommand">Run Command</button>
    <div id="output"></div>
    <script src="popup.js"></script>
</body>
</html>
            """.strip())
    
    # Create the popup.js file if it doesn't exist
    popup_js = extension_dir / 'popup.js'
    if not popup_js.exists():
        logging.info(f"Creating popup.js in {extension_dir}")
        with open(popup_js, 'w') as f:
            f.write("""
function showOutput(message) {
    const output = document.getElementById('output');
    output.textContent = message;
}

document.getElementById('runCommand').addEventListener('click', () => {
    showOutput('Running command...');
    chrome.runtime.sendMessage({ 
        action: 'runCommand',
        command: 'echo "Hello from native host!"'
    }, response => {
        console.log('Command response:', response);
        if (response && response.status === 'success') {
            showOutput(response.output || 'Command executed successfully!');
        } else {
            showOutput('Error: ' + (response ? response.message : 'Unknown error'));
        }
    });
});
            """.strip())
    
    # Create icons directory and copy icons
    icons_dir = extension_dir / 'icons'
    icons_dir.mkdir(exist_ok=True)
    
    # Create a simple icon for testing
    for size in [16, 32, 48, 128]:
        icon_path = icons_dir / f'icon{size}.png'
        if not icon_path.exists():
            logging.info(f"Creating icon{size}.png in {icons_dir}")
            # Create a simple colored square as an icon
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (size, size), color='blue')
            draw = ImageDraw.Draw(img)
            draw.rectangle([0, 0, size-1, size-1], outline='white')
            img.save(icon_path)
    
    logging.info(f"Extension files copied to: {extension_dir}")
    
    # Verify the extension files
    required_files = ['manifest.json', 'background.js', 'popup.html', 'popup.js']
    for file in required_files:
        file_path = extension_dir / file
        if not file_path.exists():
            logging.error(f"Required file {file} is missing from {extension_dir}")
            raise FileNotFoundError(f"Required file {file} is missing")
        logging.info(f"Verified {file} exists in {extension_dir}")
    
    return extension_id

def is_server_running():
    """
    Check if the server is already running.
    
    This function:
    1. Attempts to connect to the server's API endpoint
    2. Handles various connection errors gracefully
    3. Uses a reasonable timeout to prevent hanging
    
    Returns:
        bool: True if server is running and responding, False otherwise
    """
    try:
        response = requests.get('http://localhost:5001/api/commands', timeout=2)
        return response.status_code == 200
    except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
        return False
    except Exception as e:
        logging.error(f"Error checking server status: {e}")
        return False

def start_server_watchdog(server_script):
    """
    Start the server with a watchdog process that restarts it if it crashes.
    
    This function:
    1. Creates a daemon thread to monitor the server
    2. Implements exponential backoff for restarts
    3. Logs all server output
    4. Handles various failure scenarios
    
    Args:
        server_script (str): Path to the server script
        
    Returns:
        Thread: The watchdog thread object
    """
    def run_server():
        consecutive_failures = 0
        max_consecutive_failures = 3
        restart_delay = 1  # Initial delay in seconds
        
        while True:
            try:
                logging.info("Starting server process...")
                process = subprocess.Popen(
                    [sys.executable, server_script],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Log server output
                def log_output(pipe, prefix):
                    for line in pipe:
                        logging.info(f"{prefix}: {line.strip()}")
                
                stdout_thread = threading.Thread(target=log_output, args=(process.stdout, "Server stdout"), daemon=True)
                stderr_thread = threading.Thread(target=log_output, args=(process.stderr, "Server stderr"), daemon=True)
                stdout_thread.start()
                stderr_thread.start()
                
                # Wait for server to start with exponential backoff
                max_attempts = 10
                for attempt in range(max_attempts):
                    if is_server_running():
                        logging.info("Server started successfully")
                        consecutive_failures = 0  # Reset failure counter on success
                        restart_delay = 1  # Reset delay on success
                        break
                    if attempt < max_attempts - 1:
                        time.sleep(1)
                        continue
                    else:
                        logging.error("Failed to start server")
                        process.kill()
                        consecutive_failures += 1
                        break
                
                # Wait for process to finish
                return_code = process.wait()
                
                if return_code == 0:
                    logging.info("Server exited normally")
                    break
                else:
                    logging.error(f"Server crashed with return code {return_code}")
                    consecutive_failures += 1
                    
                    # Implement exponential backoff for restarts
                    if consecutive_failures >= max_consecutive_failures:
                        logging.error(f"Server failed {consecutive_failures} times consecutively. Waiting longer before next attempt.")
                        restart_delay = min(restart_delay * 2, 30)  # Cap at 30 seconds
                    
                    logging.info(f"Waiting {restart_delay} seconds before restarting server...")
                    time.sleep(restart_delay)
                    
            except Exception as e:
                logging.error(f"Error in server process: {e}")
                consecutive_failures += 1
                restart_delay = min(restart_delay * 2, 30)  # Cap at 30 seconds
                logging.info(f"Waiting {restart_delay} seconds before restarting server...")
                time.sleep(restart_delay)
    
    # Start watchdog in a separate thread
    watchdog_thread = threading.Thread(target=run_server, daemon=True)
    watchdog_thread.start()
    return watchdog_thread

def kill_flask_server():
    """
    Kill any existing Flask server process running on port 5001.
    
    This function:
    1. Finds processes using port 5001
    2. Identifies the Flask server process
    3. Terminates it gracefully
    """
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline'] and 'python' in proc.info['name'].lower():
                cmdline = ' '.join(proc.info['cmdline'])
                if 'server.py' in cmdline:
                    logging.info(f"Found existing Flask server process (PID: {proc.info['pid']})")
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                        logging.info("Flask server process terminated")
                    except psutil.TimeoutExpired:
                        proc.kill()
                        logging.info("Flask server process killed")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    # Wait a moment for the port to be released
    time.sleep(1)

def check_required_env_vars():
    """
    Check if all required environment variables are set.
    
    Returns:
        bool: True if all required variables are set, False otherwise
    """
    required_vars = {
        'SALESFORCE_USERNAME': SALESFORCE_USERNAME,
        'SALESFORCE_PASSWORD': SALESFORCE_PASSWORD,
        'DROPBOX_FOLDER': DROPBOX_ROOT_FOLDER
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    
    if missing_vars:
        logging.error("Missing required environment variables:")
        for var in missing_vars:
            logging.error(f"- {var}")
        return False
    
    return True

def start_browser():
    """
    Launch Chrome with remote debugging and load the extension.
    
    This function:
    1. Sets up the environment
    2. Starts the server with watchdog
    3. Configures Chrome preferences
    4. Launches Chrome with the extension
    5. Monitors extension status
    6. Opens multiple tabs and handles login
    """
    # Load environment variables
    load_dotenv()
    
    # Check required environment variables
    if not check_required_env_vars():
        logging.error("Missing required environment variables. Please check your .env file.")
        return

    # Kill any existing Chrome processes
    kill_chrome_processes()
    
    # Kill any existing Flask server
    kill_flask_server()

    chrome_path = get_chrome_path()
    extension_path = get_extension_path()
    user_data_dir = get_user_data_dir()
    
    logging.info(f"Chrome path: {chrome_path}")
    logging.info(f"Extension path: {extension_path}")
    logging.info(f"User data directory: {user_data_dir}")
    
    # First check if server is running
    if is_server_running():
        logging.info("Server is already running")
    else:
        # Start server with watchdog
        server_script = os.path.join(os.path.dirname(__file__), 'server.py')
        logging.info(f"Starting server with watchdog from: {server_script}")
        server_watchdog = start_server_watchdog(server_script)
        # Wait a bit for server to start
        time.sleep(2)
    
    # Set up native messaging
    setup_native_messaging()
    
    # Ensure extension is installed
    extension_id = ensure_extension_installed(user_data_dir)
    
    # Set up Chrome preferences
    setup_chrome_preferences(user_data_dir)

    # Read manifest file
    manifest = read_manifest()
    if manifest:
        extension_name = manifest.get('name')
        extension_version = manifest.get('version')
        logging.info(f"Extension name: {extension_name}")
        logging.info(f"Extension version: {extension_version}")
    else:
        logging.error("Could not read manifest.json")
        return

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
        f'--load-extension={extension_path}',
        '--remote-allow-origins=*',
        '--enable-extensions-toolbar-menu',
        '--show-extensions-toolbar',
        '--enable-extensions-toolbar-menu-button',
        '--enable-extensions-toolbar-menu-button-icon',
        '--enable-extensions-toolbar-menu-button-text',
        '--enable-extensions-toolbar-menu-button-tooltip',
        '--enable-extensions-toolbar-menu-button-badge',
        '--enable-extensions-toolbar-menu-button-badge-text',
        '--enable-extensions-toolbar-menu-button-badge-background',
        '--enable-extensions-toolbar-menu-button-badge-border',
        '--enable-extensions-toolbar-menu-button-badge-shadow',
        '--enable-extensions-toolbar-menu-button-badge-text-shadow',
        '--enable-extensions-toolbar-menu-button-badge-text-color',
        '--enable-extensions-toolbar-menu-button-badge-background-color',
        '--enable-extensions-toolbar-menu-button-badge-border-color',
        '--enable-extensions-toolbar-menu-button-badge-shadow-color',
        '--enable-extensions-toolbar-menu-button-badge-text-shadow-color',
        SALESFORCE_URL
    ]

    logging.info(f"Starting Chrome with extension from: {extension_path}")
    logging.info(f"Chrome command: {' '.join(cmd)}")
    logging.info(f"User data directory: {user_data_dir}")

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Log Chrome output
    def log_output(pipe, prefix):
        for line in pipe:
            print(f"\n{prefix}: {line.strip()}")  # Print to console immediately
            logging.info(f"{prefix}: {line.strip()}")  # Also log to file
    
    stdout_thread = threading.Thread(target=log_output, args=(process.stdout, "Chrome stdout"), daemon=True)
    stderr_thread = threading.Thread(target=log_output, args=(process.stderr, "Chrome stderr"), daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    
    # Wait for Chrome to start
    time.sleep(5)
    
    # Get list of pages from Chrome's debugging port
    try:
        response = requests.get(f'http://localhost:{CHROME_DEBUG_PORT}/json', timeout=5)
        pages = response.json()
        
        # Find the first tab
        first_tab = next((page for page in pages if page.get('type') == 'page'), None)
        if first_tab:
            # Get WebSocket URL for the first tab
            ws_url = first_tab.get('webSocketDebuggerUrl')
            if ws_url:
                # Connect to the first tab
                ws = websocket.create_connection(ws_url)
                
                try:
                    # Wait for Salesforce login page to load
                    ws.send(json.dumps({
                        "id": 1,
                        "method": "Runtime.evaluate",
                        "params": {
                            "expression": """
                            (function() {
                                return new Promise((resolve) => {
                                    const checkLogin = () => {
                                        const username = document.querySelector('input[name="username"]');
                                        const password = document.querySelector('input[name="pw"]');
                                        if (username && password) {
                                            username.value = arguments[0];
                                            password.value = arguments[1];
                                            document.querySelector('input[name="Login"]').click();
                                            resolve(true);
                                        } else {
                                            setTimeout(checkLogin, 1000);
                                        }
                                    };
                                    checkLogin();
                                });
                            }
                            """,
                            "arguments": [SALESFORCE_USERNAME, SALESFORCE_PASSWORD]
                        }
                    }))
                    
                    # Wait for login to complete
                    time.sleep(5)
                    
                    # Open Dropbox in a new tab
                    ws.send(json.dumps({
                        "id": 2,
                        "method": "Target.createTarget",
                        "params": {
                            "url": f"https://www.dropbox.com/home/{DROPBOX_ROOT_FOLDER.lstrip('/')}",
                            "newWindow": False
                        }
                    }))
                    
                    # Get the new tab's target ID
                    response = json.loads(ws.recv())
                    if 'result' in response and 'targetId' in response['result']:
                        target_id = response['result']['targetId']
                        
                        # Create a new WebSocket connection for the new tab
                        ws2 = websocket.create_connection(f"ws://localhost:{CHROME_DEBUG_PORT}/devtools/page/{target_id}")
                        
                        try:
                            # Wait for Dropbox page to load
                            time.sleep(5)
                            
                            # Handle Dropbox login if needed
                            ws2.send(json.dumps({
                                "id": 1,
                                "method": "Runtime.evaluate",
                                "params": {
                                    "expression": """
                                    (function() {
                                        return new Promise((resolve) => {
                                            const checkLogin = () => {
                                                const email = document.querySelector('input[name="login_email"]');
                                                const password = document.querySelector('input[name="login_password"]');
                                                if (email && password) {
                                                    email.value = arguments[0];
                                                    password.value = arguments[1];
                                                    document.querySelector('button[type="submit"]').click();
                                                    resolve(true);
                                                } else {
                                                    setTimeout(checkLogin, 1000);
                                                }
                                            };
                                            checkLogin();
                                        });
                                    }
                                    """,
                                    "arguments": [os.getenv('DROPBOX_USERNAME'), os.getenv('DROPBOX_PASSWORD')]
                                }
                            }))
                        finally:
                            ws2.close()
                finally:
                    ws.close()
    
    except Exception as e:
        logging.error(f"Error handling browser tabs: {e}")
    
    print(f"\nOpened {SALESFORCE_URL} in a new browser window.")
    print(f"Opened Dropbox folder {DROPBOX_ROOT_FOLDER} in a new tab.")
    print("\nThe Command Launcher extension should be automatically installed and enabled.")
    print("If you don't see the extension:")
    print("1. Open chrome://extensions in the browser")
    print("2. Make sure 'Developer mode' is enabled (top right)")
    print("3. Look for any error messages related to the extension")
    print("4. Try clicking 'Load unpacked' and select:")
    print(f"   {extension_path}")
    
    # Start extension status check in a separate thread
    status_thread = threading.Thread(target=check_extension_status, daemon=True)
    status_thread.start()
    
    try:
        while True:
            print("\nCommands:")
            print("  q - Quit (browser and server will keep running)")
            print("  r - Restart server")
            print("  s - Check server status")
            print("  h - Show this help")
            
            cmd = input("\nEnter command (h for help): ").strip().lower()
            
            if cmd == 'q':
                print("\nExiting script. Browser and server will continue running.")
                break
            elif cmd == 'r':
                print("\nRestarting server...")
                kill_flask_server()
                server_script = os.path.join(os.path.dirname(__file__), 'server.py')
                server_watchdog = start_server_watchdog(server_script)
                time.sleep(2)
                if is_server_running():
                    print("Server restarted successfully")
                else:
                    print("Failed to restart server")
            elif cmd == 's':
                if is_server_running():
                    print("Server is running")
                else:
                    print("Server is not running")
            elif cmd == 'h':
                continue
            else:
                print("Unknown command. Type 'h' for help.")
            
    except KeyboardInterrupt:
        print("\nExiting script. Browser and server will continue running.")
    finally:
        # Don't clean up processes - let them keep running
        pass

def main():
    """Main entry point for the script."""
    start_browser()

if __name__ == "__main__":
    main() 