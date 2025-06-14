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

def main():
    """Main function to start the services."""
    parser = argparse.ArgumentParser(description="Start Supabase services for sync-with-playwright")
    parser.add_argument("--force", action="store_true", help="Force stop existing containers before starting")
    args = parser.parse_args()


    if args.force:
        stop_existing_containers()
    
    clone_supabase_repo()
     # Disable logflare sinks before starting services
    disable_logflare_sinks(os.path.join("supabase", "docker", "volumes", "logs", "vector.yml"))
    prepare_supabase_env()
    if start_supabase():
        print("All services started successfully!")
    else:
        print("Services started but health check failed. Please check the logs.")
        sys.exit(1)

if __name__ == "__main__":
    main() 