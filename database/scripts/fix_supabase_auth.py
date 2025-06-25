#!/usr/bin/env python3
"""
Quick fix for Supabase authentication issues.
Run this script to diagnose and fix authentication problems.
"""

import os
import sys

def main():
    """Main function to diagnose and fix Supabase auth issues."""
    print("🔧 Supabase Authentication Fix Tool")
    print("=" * 50)
    
    # Check current environment variables
    print("Current Environment Variables:")
    print("-" * 30)
    
    supabase_vars = {
        'SUPABASE_URL': os.getenv('SUPABASE_URL'),
        'SUPABASE_ANON_KEY': os.getenv('SUPABASE_ANON_KEY'),
        'SUPABASE_SERVICE_ROLE_KEY': os.getenv('SUPABASE_SERVICE_ROLE_KEY'),
        'SUPABASE_SERVICE_KEY': os.getenv('SUPABASE_SERVICE_KEY')
    }
    
    for var, value in supabase_vars.items():
        if value:
            masked_value = value[:10] + "..." if len(value) > 10 else value
            print(f"✅ {var}: {masked_value}")
        else:
            print(f"❌ {var}: NOT SET")
    
    # Provide fix instructions
    print("\n🔧 Fix Instructions:")
    print("=" * 30)
    
    print("1. Go to your Supabase project dashboard")
    print("2. Navigate to Settings > API")
    print("3. Copy these values:")
    print("   - Project URL")
    print("   - anon public key")
    print("   - service_role secret key")
    print()
    print("4. Set the environment variables:")
    print()
    print("   # Option 1: Set in your shell")
    print("   export SUPABASE_URL='https://your-project.supabase.co'")
    print("   export SUPABASE_ANON_KEY='your-anon-key'")
    print("   export SUPABASE_SERVICE_ROLE_KEY='your-service-role-key'")
    print()
    print("   # Option 2: Create/update .env file in project root")
    print("   echo 'SUPABASE_URL=https://your-project.supabase.co' >> .env")
    print("   echo 'SUPABASE_ANON_KEY=your-anon-key' >> .env")
    print("   echo 'SUPABASE_SERVICE_ROLE_KEY=your-service-role-key' >> .env")
    print()
    print("5. Test the fix:")
    print("   python -m src.sync.commands.debug_supabase_auth")
    
    # Check if .env file exists
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        print(f"\n📁 .env file found at: {env_file}")
        print("You can edit this file to add your Supabase credentials.")
    else:
        print(f"\n📁 No .env file found. You can create one at: {env_file}")
    
    print("\n💡 Note: The service_role key has more permissions than the anon key.")
    print("   For this application, the service_role key is recommended.")

if __name__ == '__main__':
    main() 