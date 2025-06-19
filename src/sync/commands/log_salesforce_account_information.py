"""
Log Salesforce Account Information Command

This command demonstrates how to use the new salesforce_account_information structure
that contains comprehensive information about Salesforce accounts and their relationships.
"""

import json
import logging
from typing import Dict, Any, List

from sync.salesforce_client.utils.logging_utils import log_command_analysis, log_json_format

logger = logging.getLogger(__name__)


def log_salesforce_account_information(command_runner) -> Dict[str, Any]:
    """
    Log comprehensive Salesforce account information using the new structure.
    
    This command demonstrates how to access and use the salesforce_account_information
    that contains detailed information about Salesforce accounts, including:
    - Names found
    - Household information
    - Head of household
    - Members
    - All accounts with their details
    - Relationships between accounts
    
    Args:
        command_runner: The command runner instance with access to data
        
    Returns:
        Dict containing the processing results
    """
    
    # Get the salesforce_account_information from the command runner
    salesforce_account_information = command_runner.get_data('salesforce_account_information')
    
    if not salesforce_account_information:
        logger.warning("No salesforce_account_information found in command runner data")
        return {
            'status': 'no_data',
            'message': 'No salesforce_account_information available'
        }
    
    # Use the new logging utility
    log_command_analysis(salesforce_account_information, logger)
    
    # Create a summary
    names_found = salesforce_account_information.get('names_found', [])
    household = salesforce_account_information.get('household')
    head = salesforce_account_information.get('head')
    members = salesforce_account_information.get('members', [])
    accounts = salesforce_account_information.get('accounts', [])
    
    summary = {
        'total_names_found': len(names_found),
        'has_household': household is not None,
        'has_head': head is not None,
        'total_members': len(members),
        'total_accounts': len(accounts),
        'total_relationships': sum(len(acc.get('relationships', [])) for acc in accounts)
    }
    
    # Return the results
    return {
        'status': 'success',
        'salesforce_account_information': salesforce_account_information,
        'summary': summary,
        'message': f"Successfully analyzed {len(accounts)} Salesforce accounts with {summary['total_relationships']} relationships"
    }


def log_salesforce_account_information_json(command_runner) -> Dict[str, Any]:
    """
    Log Salesforce account information in JSON format for easy parsing.
    
    Args:
        command_runner: The command runner instance with access to data
        
    Returns:
        Dict containing the JSON-formatted results
    """
    
    # Get the salesforce_account_information from the command runner
    salesforce_account_information = command_runner.get_data('salesforce_account_information')
    
    if not salesforce_account_information:
        logger.warning("No salesforce_account_information found in command runner data")
        return {
            'status': 'no_data',
            'message': 'No salesforce_account_information available'
        }
    
    # Use the new logging utility
    log_json_format(salesforce_account_information, logger)
    
    return {
        'status': 'success',
        'json_data': salesforce_account_information,
        'message': 'Successfully logged Salesforce account information in JSON format'
    }


# Command registration
COMMANDS = {
    'log-salesforce-account-information': log_salesforce_account_information,
    'log-salesforce-account-information-json': log_salesforce_account_information_json
} 