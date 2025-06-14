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

def start_supabase():
    """Start the Supabase services."""
    print("Starting Supabase services...")
    run_command([
        "docker", "compose", 
        "-p", "sync-with-playwright", 
        "-f", "docker-compose.yml", 
        "up", "-d"
    ])
    # Wait for networks to be created
    time.sleep(5)

def check_supabase_health():
    """Check if Supabase services are healthy."""
    print("Checking Supabase services health...")
    try:
        # Check if Kong is responding
        kong_check = subprocess.run(
            ["curl", "-f", "http://localhost:18000/rest/v1/"],
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
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        if check_supabase_health():
            return True
        attempt += 1
        print(f"Attempt {attempt}/{max_attempts}...")
        time.sleep(10)
    
    print("Timed out waiting for Supabase services to be ready.")
    return False

def main():
    """Main function to start the services."""
    parser = argparse.ArgumentParser(description="Start Supabase services for sync-with-playwright")
    parser.add_argument("--force", action="store_true", help="Force stop existing containers before starting")
    args = parser.parse_args()

    if args.force:
        stop_existing_containers()
    
    clone_supabase_repo()
    prepare_supabase_env()
    start_supabase()
    
    if wait_for_supabase():
        print("All services started successfully!")
    else:
        print("Services started but health check failed. Please check the logs.")
        sys.exit(1)

if __name__ == "__main__":
    main() 