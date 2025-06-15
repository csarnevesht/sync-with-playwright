#!/usr/bin/env python3
"""
start_services.py

This script starts the Supabase stack for the sync-with-playwright project.
It ensures proper initialization and configuration of the Supabase services.
"""

import os
import subprocess
import shutil
import time
import argparse
import platform
import sys
import re
import yaml

def run_command(cmd, cwd=None):
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

def get_supabase_keys():
    """Get both ANON_KEY and SUPABASE_SERVICE_KEY from the environment or container."""
    keys = {}
    
    # Try to get from container - handle different possible container names
    container_names = [
        "sync-with-playwright-kong-1",
        "supabase-kong",
        "kong"
    ]
    
    for container_name in container_names:
        try:
            result = subprocess.run(
                ["docker", "exec", container_name, "env"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Get service role key
                service_match = re.search(r'SUPABASE_SERVICE_KEY=([^\n]+)', result.stdout)
                if service_match:
                    keys['service'] = service_match.group(1)
                
                # Get anon key
                anon_match = re.search(r'ANON_KEY=([^\n]+)', result.stdout)
                if anon_match:
                    keys['anon'] = anon_match.group(1)
                
                if keys:
                    print(f"\nFound Supabase keys in {container_name} container.")
                    return keys
        except Exception:
            continue

    # Try environment variables as fallback
    keys['service'] = os.environ.get('SUPABASE_SERVICE_KEY')
    keys['anon'] = os.environ.get('ANON_KEY')
    
    if not any(keys.values()):
        print("\nNo Supabase keys found. You can get them in one of these ways:")
        print("\n1. From the Supabase Dashboard:")
        print("   a. Go to https://supabase.com/dashboard")
        print("   b. Select your project")
        print("   c. Go to Project Settings > API")
        print("   d. Find 'Project API keys' section")
        print("   e. Copy both the 'anon' and 'service_role' keys")
        
        print("\n2. From your local Supabase setup:")
        print("   a. Check if the Kong container is running:")
        print("      docker ps | grep kong")
        print("   b. Get the keys from the container:")
        print("      docker exec <kong-container-name> env | grep SUPABASE")
        
        print("\n3. Set them in your environment:")
        print("   export ANON_KEY=your-anon-key-here")
        print("   export SUPABASE_SERVICE_KEY=your-service-key-here")
        print("   # Or add them to your .env file:")
        print("   echo 'ANON_KEY=your-anon-key-here' >> .env")
        print("   echo 'SUPABASE_SERVICE_KEY=your-service-key-here' >> .env")
        
        print("\nNote: The service role key has full access to your database.")
        print("      Keep it secure and never commit it to version control.")
    
    return keys

def validate_jwt(token):
    """Validate a JWT token format."""
    try:
        # Split the token into parts
        parts = token.split('.')
        if len(parts) != 3:
            return False, "Invalid JWT format: should have 3 parts"
        
        # Check if each part is base64url encoded
        import base64
        for part in parts:
            try:
                base64.urlsafe_b64decode(part + '=' * (-len(part) % 4))
            except Exception:
                return False, f"Invalid base64url encoding in part: {part}"
        
        return True, "Valid JWT format"
    except Exception as e:
        return False, f"Error validating JWT: {str(e)}"

def prepare_supabase_env():
    """Copy .env to .env in supabase/docker."""
    env_path = os.path.join("supabase", "docker", ".env")
    env_example_path = os.path.join(".env")
    print("Copying .env in root to .env in supabase/docker...")
    shutil.copyfile(env_example_path, env_path)

def clone_supabase_repo():
    """Clone the Supabase repository using sparse checkout if not already present."""
    if not os.path.exists("supabase"):
        print("Cloning the Supabase repository...")
        run_command([
            "git", "clone", "--filter=blob:none", "--no-checkout",
            "https://github.com/supabase/supabase.git"
        ])
        os.chdir("supabase")
        run_command(["git", "sparse-checkout", "init", "--cone"])
        run_command(["git", "sparse-checkout", "set", "docker"])
        run_command(["git", "checkout", "master"])
        os.chdir("..")
    else:
        print("Supabase repository already exists, updating...")
        os.chdir("supabase")
        run_command(["git", "pull"])
        os.chdir("..")

def stop_existing_containers():
    """Stop and remove existing containers for our project ('sync-with-playwright')."""
    print("Stopping and removing existing containers for the project 'sync-with-playwright'...")
    run_command([
        "docker", "compose",
        "-p", "sync-with-playwright",
        "-f", "docker-compose.yml",
        "down"
    ])

def wait_for_container_health(container_name, timeout=30):
    """Wait for a container to be healthy."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Health.Status}}", container_name],
            capture_output=True,
            text=True
        )
        if result.stdout.strip() == "healthy":
            return True
        time.sleep(1)
    return False

def start_supabase():
    """Start Supabase services."""
    # First, ensure vector is running and healthy
    print("Starting vector service first...")
    run_command([
        "docker", "compose", "-p", "sync-with-playwright",
        "-f", "supabase/docker/docker-compose.yml", "up", "-d", "vector"
    ])
    
    # Wait for vector to be healthy
    print("Waiting for vector to be healthy...")
    if not wait_for_container_health("supabase-vector"):
        print("Vector failed to become healthy in time")
        return False
    
    # Now start the rest of the services
    print("Starting remaining Supabase services...")
    run_command([
        "docker", "compose", "-p", "sync-with-playwright",
        "-f", "supabase/docker/docker-compose.yml", "up", "-d"
    ])
    
    return True

def check_supabase_health():
    """Check if Supabase services are healthy."""
    print("Checking Supabase services health...")
    try:
        # Check if Kong is responding
        kong_check = subprocess.run(
            ["curl", "-f", "http://localhost:8000/rest/v1/"],
            capture_output=True,
            timeout=10
        )
        if kong_check.returncode == 0:
            print("Supabase services are healthy!")
            return True
        else:
            print("Supabase services are not fully healthy yet...")
            return False
    except Exception as e:
        print(f"Error checking Supabase health: {e}")
        return False

def wait_for_supabase():
    """Wait for Supabase services to be ready."""
    print("Waiting for Supabase services to be ready...")
    max_attempts = 10
    attempt = 0
    
    while attempt < max_attempts:
        if check_supabase_health():
            return True
        attempt += 1
        print(f"Attempt {attempt}/{max_attempts}...")
        time.sleep(10)
    
    print("Timed out waiting for Supabase services to be ready.")
    return False

def disable_logflare_sinks(vector_yml_path):
    """Remove all logflare_* sinks from the YAML vector.yml file, add a dummy file sink if needed, and print what was removed and the result."""
    with open(vector_yml_path, 'r') as f:
        data = yaml.safe_load(f)

    sinks = data.get('sinks', {})
    removed = []
    new_sinks = {}
    for key, value in sinks.items():
        if key.startswith('logflare_'):
            removed.append(key)
        else:
            new_sinks[key] = value
    if removed:
        print('Removed logflare sinks:', removed)
    else:
        print('No logflare sinks found to remove.')
    # If no sinks remain, add a dummy file sink with encoding and a valid input
    if not new_sinks:
        print('No sinks remain, adding a dummy file sink.')
        new_sinks = {
            'file_sink': {
                'type': 'file',
                'inputs': ['project_logs'],
                'path': '/tmp/vector-dummy.log',
                'encoding': {'codec': 'text'}
            }
        }
    # Force the dummy sink to have the correct input
    if 'file_sink' in new_sinks:
        new_sinks['file_sink']['inputs'] = ['project_logs']
        print(f"file_sink inputs before write: {new_sinks['file_sink']['inputs']}")
    data['sinks'] = new_sinks
    with open(vector_yml_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False)
    print('\nResulting sinks section:')
    print(yaml.dump({'sinks': new_sinks}, default_flow_style=False))

def start_services(force=False):
    """Start all Supabase services.
    
    Args:
        force (bool): If True, force stop existing containers before starting.
    
    Returns:
        bool: True if services started successfully, False otherwise.
    """
    if force:
        stop_existing_containers()
    
    clone_supabase_repo()
    # Disable logflare sinks before starting services
    disable_logflare_sinks(os.path.join("supabase", "docker", "volumes", "logs", "vector.yml"))
    prepare_supabase_env()
    
    if start_supabase():
        print("\nAll services started successfully!")
        
        # Get and display service key information
        keys = get_supabase_keys()
        
        if keys.get('service') or keys.get('anon'):
            print("\nCurrent Supabase key configuration:")
            
            if keys.get('service'):
                is_valid, message = validate_jwt(keys['service'])
                print("\nService Role Key:")
                print(f"Key: {keys['service']}")
                print(f"Status: {'✅ Valid' if is_valid else '❌ Invalid'}")
                if not is_valid:
                    print(f"Error: {message}")
            
            if keys.get('anon'):
                is_valid, message = validate_jwt(keys['anon'])
                print("\nAnon Key:")
                print(f"Key: {keys['anon']}")
                print(f"Status: {'✅ Valid' if is_valid else '❌ Invalid'}")
                if not is_valid:
                    print(f"Error: {message}")
            
            print("\nTo use these keys in your application:")
            print("1. Add them to your .env file:")
            if keys.get('anon'):
                print(f"   ANON_KEY={keys['anon']}")
            if keys.get('service'):
                print(f"   SUPABASE_SERVICE_KEY={keys['service']}")
            print("2. Or set them in your environment:")
            if keys.get('anon'):
                print(f"   export ANON_KEY={keys['anon']}")
            if keys.get('service'):
                print(f"   export SUPABASE_SERVICE_KEY={keys['service']}")
            
            print("\nNote: The service role key has full access to your database.")
            print("      Keep it secure and never commit it to version control.")
        else:
            print("\nWARNING: No Supabase keys found!")
            print("Please set them up as described above.")
            print("\nAfter setting up the keys, you may need to:")
            print("1. Restart your application")
            print("2. Run 'python scripts/setup_env.py' to update your environment")
        
        return True
    else:
        print("Services started but health check failed. Please check the logs.")
        return False

def main():
    """Main function to start the services."""
    parser = argparse.ArgumentParser(description="Start Supabase services for sync-with-playwright")
    parser.add_argument("--force", action="store_true", help="Force stop existing containers before starting")
    args = parser.parse_args()

    if not start_services(args.force):
        sys.exit(1)

if __name__ == "__main__":
    main() 