import subprocess
import os
import sys
from typing import Tuple

def check_supabase_installation() -> Tuple[bool, str]:
    """
    Check if Supabase CLI is installed
    Returns: (is_installed, message)
    """
    try:
        result = subprocess.run(['supabase', '--version'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return True, "Supabase CLI is installed"
        else:
            return False, "Supabase CLI is not installed"
    except Exception as e:
        return False, f"Supabase CLI is not installed: {str(e)}"

def install_supabase() -> Tuple[bool, str]:
    """
    Install Supabase CLI
    Returns: (success, message)
    """
    try:
        if sys.platform == "darwin":  # macOS
            subprocess.run(['brew', 'install', 'supabase/tap/supabase'], 
                         check=True)
        elif sys.platform == "linux":
            subprocess.run(['curl', '-fsSL', 'https://cli.supabase.com/install.sh', '|', 'sh'], 
                         shell=True, 
                         check=True)
        else:
            return False, "Unsupported operating system"
        return True, "Supabase CLI installed successfully"
    except subprocess.CalledProcessError as e:
        return False, f"Failed to install Supabase CLI: {str(e)}"

def ensure_supabase_running() -> Tuple[bool, str]:
    """
    Ensure Supabase is running, start if not
    Returns: (is_running, message)
    """
    # Check if Docker is running
    try:
        subprocess.run(['docker', 'info'], 
                      capture_output=True, 
                      check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False, "Docker is not running. Please start Docker first."

    # Check if Supabase is running
    try:
        result = subprocess.run(['docker', 'ps', '--filter', 'name=supabase'], 
                              capture_output=True, 
                              text=True)
        if 'supabase' in result.stdout:
            return True, "Supabase is already running"
    except subprocess.CalledProcessError:
        pass

    # Start Supabase
    try:
        subprocess.run(['docker-compose', 'up', '-d'], 
                      check=True)
        return True, "Supabase started successfully"
    except subprocess.CalledProcessError as e:
        return False, f"Failed to start Supabase: {str(e)}"

def check_and_setup_supabase() -> Tuple[bool, str]:
    """
    Check Supabase installation and running status, setup if needed
    Returns: (success, message)
    """
    # Check installation
    is_installed, install_msg = check_supabase_installation()
    if not is_installed:
        success, msg = install_supabase()
        if not success:
            return False, msg

    # Ensure Supabase is running
    is_running, run_msg = ensure_supabase_running()
    if not is_running:
        return False, run_msg

    return True, "Supabase is ready to use" 