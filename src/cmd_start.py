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

def read_manifest_file(manifest_path):
    """Read and parse a JSON file."""
    try:
        with open(manifest_path) as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error reading file: {e}")
        return None

def read_manifest():
    """Read the extension's manifest file."""
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
        '--load-extension=' + extension_path,
        '--remote-allow-origins=*',  # Allow all origins for WebSocket connections
        SALESFORCE_URL
    ]

    logging.info(f"Starting Chrome with extension from: {extension_path}")
    logging.info(f"Chrome command: {' '.join(cmd)}")
    logging.info(f"User data directory: {user_data_dir}")

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Register cleanup handler
    atexit.register(cleanup_chrome_process, process)
    
    # Log Chrome output
    def log_output(pipe, prefix):
        for line in pipe:
            print(f"\n{prefix}: {line.strip()}")  # Print to console immediately
            logging.info(f"{prefix}: {line.strip()}")  # Also log to file
    
    import threading
    stdout_thread = threading.Thread(target=log_output, args=(process.stdout, "Chrome stdout"), daemon=True)
    stderr_thread = threading.Thread(target=log_output, args=(process.stderr, "Chrome stderr"), daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    
    # Wait for Chrome to start and check extension status
    import time
    import requests
    import json

    def check_extension_status():
        try:
            # Wait for Chrome to start
            print("\nWaiting for Chrome to start...")
            time.sleep(5)
            
            # Get list of pages from Chrome's debugging port
            print("\nChecking Chrome debugging port...")
            response = requests.get(f'http://localhost:{CHROME_DEBUG_PORT}/json')
            pages = response.json()
            print(f"\nFound {len(pages)} pages in Chrome")
            
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
                            import websocket
                            ext_ws = websocket.create_connection(ws_url)
                            
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
            else:
                print("\nCommand Launcher extension not found")
                print("\nPlease make sure to:")
                print("1. Type 'chrome://extensions' in the address bar")
                print("2. Enable 'Developer mode' (top right)")
                print("3. Click 'Load unpacked'")
                print(f"4. Select this directory: {extension_path}")
                return False
                
        except Exception as e:
            print(f"\nERROR checking extension status: {e}")
            print("\nPlease make sure to:")
            print("1. Type 'chrome://extensions' in the address bar")
            print("2. Enable 'Developer mode' (top right)")
            print("3. Click 'Load unpacked'")
            print(f"4. Select this directory: {extension_path}")
            return False

    # Start extension status check in a separate thread
    status_thread = threading.Thread(target=check_extension_status, daemon=True)
    status_thread.start()
    
    print(f"\nOpened {SALESFORCE_URL} in a new browser window.")
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