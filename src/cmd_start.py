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
    """Get the path to Chrome executable based on the platform."""
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
    """Get the absolute path to the Chrome extension directory."""
    # Get the project root directory (parent of src)
    project_root = Path(__file__).parent.parent
    extension_path = project_root / 'chrome_extension'
    if not extension_path.exists():
        raise FileNotFoundError(f"Chrome extension directory not found at: {extension_path}")
    return str(extension_path)

def get_user_data_dir():
    """Get the user data directory path."""
    # Allow override via environment variable
    custom_dir = os.getenv('CHROME_USER_DATA_DIR')
    if custom_dir:
        return Path(custom_dir)
        
    # Create a separate debug profile directory
    debug_dir = Path.home() / '.chrome-debug-profile'
    if debug_dir.exists():
        # Remove existing debug profile to ensure clean state
        import shutil
        shutil.rmtree(debug_dir)
    debug_dir.mkdir(exist_ok=True)
    return debug_dir

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
    
    # Get the extension path
    extension_path = get_extension_path()
    logging.info(f"Setting up Chrome preferences with extension path: {extension_path}")
    
    # Read the manifest to get extension details
    manifest = read_manifest()
    if not manifest:
        raise Exception("Could not read manifest.json")
    
    logging.info(f"Manifest contents: {json.dumps(manifest, indent=2)}")
    
    # Generate a unique extension ID (this is a simplified version)
    extension_id = "igdglpnaamkkfoojnlkindpbdmjebmhg"  # You might want to generate this dynamically
    
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
        "path": extension_path,
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
    
    # Add extension to toolbar
    if 'extensions' not in existing_preferences:
        existing_preferences['extensions'] = {}
    if 'toolbar' not in existing_preferences['extensions']:
        existing_preferences['extensions']['toolbar'] = {}
    if 'visible' not in existing_preferences['extensions']['toolbar']:
        existing_preferences['extensions']['toolbar']['visible'] = True
    
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
    """Continuously check for the extension until it's found or timeout."""
    max_attempts = 30  # Try for 30 seconds
    attempt = 0
    
    # Get extension path
    extension_path = get_extension_path()
    
    while attempt < max_attempts:
        try:
            print(f"\nChecking for extension (attempt {attempt + 1}/{max_attempts})...")
            
            # Get list of pages from Chrome's debugging port
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
    """Ensure the extension is properly installed and enabled."""
    extension_path = get_extension_path()
    logging.info(f"Ensuring extension is installed from: {extension_path}")
    
    # Create the Extensions directory if it doesn't exist
    extensions_dir = user_data_dir / 'Default' / 'Extensions'
    extensions_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a unique ID for our extension
    extension_id = "igdglpnaamkkfoojnlkindpbdmjebmhg"
    extension_dir = extensions_dir / extension_id
    extension_dir.mkdir(exist_ok=True)
    
    # Copy the extension files
    import shutil
    if extension_dir.exists():
        shutil.rmtree(extension_dir)
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
    
    logging.info(f"Extension files copied to: {extension_dir}")
    return extension_id

def start_browser():
    """Launch Chrome with remote debugging and load the extension."""
    # Load environment variables
    load_dotenv()

    # Kill any existing Chrome processes
    kill_chrome_processes()

    chrome_path = get_chrome_path()
    extension_path = get_extension_path()
    user_data_dir = get_user_data_dir()
    
    logging.info(f"Chrome path: {chrome_path}")
    logging.info(f"Extension path: {extension_path}")
    logging.info(f"User data directory: {user_data_dir}")
    
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
        '--load-extension=' + extension_path,
        '--remote-allow-origins=*',  # Allow all origins for WebSocket connections
        '--enable-extensions-toolbar-menu',  # Ensure extensions toolbar is visible
        '--show-extensions-toolbar',  # Show extensions toolbar
        '--enable-extensions-toolbar-menu',  # Enable extensions toolbar menu
        '--enable-extensions-toolbar-menu-button',  # Enable extensions toolbar menu button
        '--enable-extensions-toolbar-menu-button-icon',  # Enable extensions toolbar menu button icon
        '--enable-extensions-toolbar-menu-button-text',  # Enable extensions toolbar menu button text
        '--enable-extensions-toolbar-menu-button-tooltip',  # Enable extensions toolbar menu button tooltip
        '--enable-extensions-toolbar-menu-button-badge',  # Enable extensions toolbar menu button badge
        '--enable-extensions-toolbar-menu-button-badge-text',  # Enable extensions toolbar menu button badge text
        '--enable-extensions-toolbar-menu-button-badge-background',  # Enable extensions toolbar menu button badge background
        '--enable-extensions-toolbar-menu-button-badge-border',  # Enable extensions toolbar menu button badge border
        '--enable-extensions-toolbar-menu-button-badge-shadow',  # Enable extensions toolbar menu button badge shadow
        '--enable-extensions-toolbar-menu-button-badge-text-shadow',  # Enable extensions toolbar menu button badge text shadow
        '--enable-extensions-toolbar-menu-button-badge-text-color',  # Enable extensions toolbar menu button badge text color
        '--enable-extensions-toolbar-menu-button-badge-background-color',  # Enable extensions toolbar menu button badge background color
        '--enable-extensions-toolbar-menu-button-badge-border-color',  # Enable extensions toolbar menu button badge border color
        '--enable-extensions-toolbar-menu-button-badge-shadow-color',  # Enable extensions toolbar menu button badge shadow color
        '--enable-extensions-toolbar-menu-button-badge-text-shadow-color',  # Enable extensions toolbar menu button badge text shadow color
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
    print(f"\nOpened {SALESFORCE_URL} in a new browser window.")
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