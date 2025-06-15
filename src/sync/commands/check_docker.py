import subprocess
import sys
import time
from pathlib import Path
import os
import logging

# Add the project root to Python path to import start_services
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))
from start_services import start_services

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def check_docker_running() -> bool:
    """Check if Docker daemon is running"""
    try:
        subprocess.run(['docker', 'info'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def check_supabase_running() -> bool:
    """Check if our Supabase instance is running"""
    try:
        result = subprocess.run(['docker', 'ps', '--filter', 'name=supabase-'], capture_output=True, text=True, check=True)
        print("\nChecking Supabase containers:")
        print(result.stdout)
        return 'supabase-kong' in result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error checking Supabase containers: {e}")
        return False

def start_docker():
    """Start Docker daemon"""
    print("\nDocker is not running. Would you like to start it?")
    choice = input("Start Docker? (y/n): ").lower()
    
    if choice != 'y':
        print("Cannot proceed without Docker. Exiting...")
        sys.exit(1)
    
    print("\nStarting Docker...")
    try:
        # On macOS, we can use the 'open' command to start Docker Desktop
        subprocess.run(['open', '-a', 'Docker'], check=True)
        
        # Wait for Docker to start
        print("Waiting for Docker to start...")
        for _ in range(30):  # Wait up to 30 seconds
            if check_docker_running():
                print("Docker started successfully!")
                return True
            time.sleep(1)
        
        print("Timed out waiting for Docker to start.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Error starting Docker: {e}")
        return False

def start_supabase():
    """Start Supabase services using start_services.py"""
     # Log current directory before changing
    print(f"Current directory before changing: {os.getcwd()}")
    print(f"Project root path: {project_root}")
    print("\nSupabase is not running. Would you like to start it?")
    choice = input("Start Supabase? (y/n): ").lower()
    
    if choice != 'y':
        print("Cannot proceed without Supabase. Exiting...")
        sys.exit(1)
    
    print("\nStarting Supabase...")
    try:
        # Log current directory before changing
        print(f"Current directory before changing: {os.getcwd()}")
        print(f"Project root path: {project_root}")
        
        # Change to project root directory
        os.chdir(project_root)
        
        # Log current directory after changing
        logger.debug(f"Current directory after changing: {os.getcwd()}")
        
        # Use start_services.py to start Supabase
        start_services()
        
        # Wait for Supabase to start
        print("Waiting for Supabase to start...")
        for i in range(120):  # Wait up to 120 seconds
            if check_supabase_running():
                print("Supabase started successfully!")
                return True
            if i % 10 == 0:  # Print status every 10 seconds
                print(f"Still waiting for Supabase to start... ({i}s elapsed)")
            time.sleep(1)
        
        print("Timed out waiting for Supabase to start.")
        return False
    except Exception as e:
        logger.error(f"Error starting Supabase: {e}", exc_info=True)
        return False

def ensure_docker_and_supabase():
    """Ensure Docker and Supabase are running"""
    # Check Docker
    if not check_docker_running():
        if not start_docker():
            sys.exit(1)
    
    # Check Supabase
    if not check_supabase_running():
        if not start_supabase():
            sys.exit(1)
    
    return True

if __name__ == "__main__":
    ensure_docker_and_supabase() 