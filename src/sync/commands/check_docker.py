import subprocess
import sys
import time
from pathlib import Path

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
        result = subprocess.run(['docker', 'ps', '--filter', 'name=sync-'], capture_output=True, text=True, check=True)
        print("\nChecking Supabase containers:")
        print(result.stdout)
        return 'sync-kong' in result.stdout
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
    """Start Supabase services"""
    print("\nSupabase is not running. Would you like to start it?")
    choice = input("Start Supabase? (y/n): ").lower()
    
    if choice != 'y':
        print("Cannot proceed without Supabase. Exiting...")
        sys.exit(1)
    
    print("\nStarting Supabase...")
    try:
        # Get the project root directory
        project_root = Path(__file__).parent.parent.parent.parent
        
        # Run docker-compose up
        subprocess.run(['docker-compose', 'up', '-d'], cwd=project_root, check=True)
        
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
    except subprocess.CalledProcessError as e:
        print(f"Error starting Supabase: {e}")
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