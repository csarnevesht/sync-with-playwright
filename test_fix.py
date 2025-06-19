#!/usr/bin/env python3
"""
Test script to verify the account_info_from_app_files fix.
"""

import sys
import os
sys.path.append('src')

from sync.command_runner import CommandRunner
from unittest.mock import Mock

def test_account_info_from_app_files_fix():
    """Test that account_info_from_app_files is always available."""
    
    # Create a mock args object
    args = Mock()
    args.commands = None
    args.dropbox_accounts = False
    args.dropbox_account_files = False
    args.salesforce_accounts = False
    args.salesforce_account_files = False
    args.dropbox_account_info = False
    args.salesforce_account_info = False
    args.dropbox_account_name = None
    args.dropbox_accounts_file = None
    args.salesforce_account_name = None
    args.salesforce_accounts_file = None
    args.account_batch_size = None
    args.start_from = None
    args.file_filter = None
    args.dl = False
    args.env_file = None
    args.birthdate = None
    args.gender = None
    args.application_type = None
    args.log_file = None
    
    # Create command runner
    runner = CommandRunner(args)
    
    # Set required data
    runner.set_data('dropbox_account_folder_name', 'Test Account')
    
    # Test that _build_dropbox_account_information works without account_info_from_app_files
    result = runner._build_dropbox_account_information()
    
    # Verify the structure is correct
    assert 'names_found' in result
    assert 'client_list_data' in result
    assert 'application_data' in result
    assert 'accounts' in result
    
    # Verify application_data is set (even if empty)
    assert result['application_data'] is not None
    assert 'status' in result['application_data']
    
    print("✅ Test passed: account_info_from_app_files fix works correctly!")
    print(f"Application data status: {result['application_data']['status']}")
    
    return True

if __name__ == "__main__":
    try:
        test_account_info_from_app_files_fix()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1) 