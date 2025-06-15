import os
import sys
from pathlib import Path
import logging
import re
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_supabase_service_key():
    """Get the Supabase service key from the running container"""
    try:
        # First try to get from environment
        if os.getenv('SUPABASE_SERVICE_KEY'):
            logger.info("Using SUPABASE_SERVICE_KEY from environment")
            return os.getenv('SUPABASE_SERVICE_KEY')

        # Then try to get from container
        logger.info("Attempting to get service key from Supabase container...")
        result = subprocess.run(
            ['docker', 'exec', 'supabase-kong', 'env', '|', 'grep', 'SUPABASE_SERVICE_KEY'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            # Extract the key from the output
            key = result.stdout.strip().split('=')[1]
            logger.info("Successfully retrieved service key from container")
            return key
        else:
            logger.warning("Could not get service key from container")
            return None
    except Exception as e:
        logger.warning(f"Error getting service key: {e}")
        return None

def update_env_file(env_file: Path, required_vars: dict):
    """Update or create .env file with required variables"""
    env_content = {}
    
    # Read existing .env file if it exists
    if env_file.exists():
        logger.info("Reading existing .env file...")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    env_content[key.strip()] = value.strip()
    
    # Update with required variables
    env_content.update(required_vars)
    
    # Write back to .env file
    logger.info("Updating .env file...")
    with open(env_file, 'w') as f:
        # Write Supabase configuration section
        f.write("# Supabase Configuration\n")
        f.write("# Get your service key from: Project Settings > API > Project API keys > service_role key\n")
        f.write(f"SUPABASE_URL={env_content['SUPABASE_URL']}\n")
        f.write(f"SUPABASE_SERVICE_KEY={env_content['SUPABASE_SERVICE_KEY']}\n\n")
        
        # Write other existing variables
        for key, value in env_content.items():
            if key not in ['SUPABASE_URL', 'SUPABASE_SERVICE_KEY']:
                f.write(f"{key}={value}\n")

def setup_env():
    """Set up environment variables for Supabase"""
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    env_file = project_root / '.env'

    # Get the service key
    service_key = get_supabase_service_key()
    if not service_key:
        logger.error("""
Could not get Supabase service key. Please ensure one of the following:
1. Set SUPABASE_SERVICE_KEY in your environment
2. Supabase is running locally (docker-compose up -d)
3. Get the key from Supabase dashboard: Project Settings > API > Project API keys > service_role key
""")
        sys.exit(1)

    # Required environment variables
    required_vars = {
        'SUPABASE_URL': 'http://localhost:8000',
        'SUPABASE_SERVICE_KEY': service_key,
        'LOG_LEVEL': 'DEBUG'
    }

    # Update or create .env file
    update_env_file(env_file, required_vars)
    logger.info("Environment file has been updated")

    # Verify environment variables
    from dotenv import load_dotenv
    load_dotenv(env_file)

    # Verify all required variables are present
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    logger.info("Environment variables are properly configured")

if __name__ == '__main__':
    setup_env() 