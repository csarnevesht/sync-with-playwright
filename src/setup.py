#!/usr/bin/env python3
import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

def get_extension_id():
    """Get the extension ID from the manifest file."""
    manifest_path = os.path.join('chrome_extension', 'manifest.json')
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    return manifest.get('key', '')

def install_dependencies():
    """Install required Python packages."""
    print("Installing required Python packages...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'flask', 'flask-cors', 'requests'])

def setup_native_host():
    """Set up the native messaging host."""
    print("Setting up native messaging host...")
    
    # Make native host script executable
    native_host_path = os.path.join('chrome_extension', 'native_host.py')
    os.chmod(native_host_path, 0o755)
    
    # Get absolute path to native host
    abs_native_host_path = os.path.abspath(native_host_path)
    
    # Create native messaging host manifest
    manifest = {
        "name": "com.command_launcher",
        "description": "Command Launcher Native Host",
        "path": abs_native_host_path,
        "type": "stdio",
        "allowed_origins": [
            f"chrome-extension://{get_extension_id()}/"
        ]
    }
    
    # Create directory for native messaging hosts
    if sys.platform == 'darwin':  # macOS
        host_dir = os.path.expanduser('~/Library/Application Support/Google/Chrome/NativeMessagingHosts')
    elif sys.platform == 'win32':  # Windows
        host_dir = os.path.expanduser('~\\AppData\\Local\\Google\\Chrome\\NativeMessagingHosts')
    else:  # Linux
        host_dir = os.path.expanduser('~/.config/google-chrome/NativeMessagingHosts')
    
    os.makedirs(host_dir, exist_ok=True)
    
    # Write manifest file
    manifest_path = os.path.join(host_dir, 'com.command_launcher.json')
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"Native messaging host manifest installed at: {manifest_path}")

def create_commands_file():
    """Create an empty commands.json file if it doesn't exist."""
    if not os.path.exists('commands.json'):
        print("Creating empty commands.json file...")
        with open('commands.json', 'w') as f:
            json.dump([], f, indent=2)

def main():
    print("Starting Command Launcher setup...")
    
    # Install dependencies
    install_dependencies()
    
    # Set up native host
    setup_native_host()
    
    # Create commands file
    create_commands_file()
    
    print("\nSetup complete! Now you can:")
    print("1. Open Chrome and go to chrome://extensions/")
    print("2. Enable 'Developer mode' in the top right")
    print("3. Click 'Load unpacked' and select the 'chrome_extension' directory")
    print("\nThe extension should now be installed and ready to use!")

if __name__ == '__main__':
    main() 