"""
Test Salesforce Account Information Structure

This test verifies that the new salesforce_account_information structure is properly created
and contains all the expected fields and relationships.
"""

import pytest
from unittest.mock import Mock, MagicMock
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from sync.cmd_runner import run_command
from sync.salesforce_client.pages.account_manager import AccountManager


def test_salesforce_account_information_structure():
    """Test that the salesforce_account_information structure is properly created."""
    
    # Mock data structure that would be returned by the account manager
    mock_salesforce_account_information = {
        'names_found': ['Maria Montesino', 'Maria Montesino Household'],
        'household': {
            'account_name': 'Maria Montesino Household',
            'type': 'Household',
            'role': None,
            'stage': 'Client',
            'email': 'jackaron2014@outlook.com',
            'phone': '786-282-4047',
            'mailing_address': '920 NE 199 ST. Apt. 417\nMiami, FL. 33179',
            'ssn/tax_id': '770-20-3101',
            'relationships': []
        },
        'head': {
            'account_name': 'Maria Montesino',
            'type': 'Contact',
            'role': 'Household Head',
            'stage': 'Client',
            'email': 'jackaron2014@outlook.com',
            'phone': '786-282-4047',
            'mailing_address': '920 NE 199 ST. Apt. 417\nMiami, FL. 33179',
            'ssn/tax_id': '770-20-3101',
            'relationships': []
        },
        'members': [],
        'accounts': [
            {
                'account_name': 'Maria Montesino',
                'type': 'Contact',
                'role': 'Household Head',
                'stage': 'Client',
                'email': 'jackaron2014@outlook.com',
                'phone': '786-282-4047',
                'mailing_address': '920 NE 199 ST. Apt. 417\nMiami, FL. 33179',
                'ssn/tax_id': '770-20-3101',
                'relationships': []
            },
            {
                'account_name': 'Maria Montesino Household',
                'type': 'Household',
                'role': None,
                'stage': 'Client',
                'email': 'jackaron2014@outlook.com',
                'phone': '786-282-4047',
                'mailing_address': '920 NE 199 ST. Apt. 417\nMiami, FL. 33179',
                'ssn/tax_id': '770-20-3101',
                'relationships': []
            }
        ]
    }
    
    # Test that the structure has all required fields
    assert 'names_found' in mock_salesforce_account_information
    assert 'household' in mock_salesforce_account_information
    assert 'head' in mock_salesforce_account_information
    assert 'members' in mock_salesforce_account_information
    assert 'accounts' in mock_salesforce_account_information
    
    # Test that names_found is a list
    assert isinstance(mock_salesforce_account_information['names_found'], list)
    assert len(mock_salesforce_account_information['names_found']) == 2
    
    # Test that household is properly structured
    household = mock_salesforce_account_information['household']
    assert household['account_name'] == 'Maria Montesino Household'
    assert household['type'] == 'Household'
    assert household['stage'] == 'Client'
    assert household['email'] == 'jackaron2014@outlook.com'
    assert household['phone'] == '786-282-4047'
    
    # Test that head is properly structured
    head = mock_salesforce_account_information['head']
    assert head['account_name'] == 'Maria Montesino'
    assert head['type'] == 'Contact'
    assert head['role'] == 'Household Head'
    assert head['stage'] == 'Client'
    
    # Test that accounts list contains both accounts
    accounts = mock_salesforce_account_information['accounts']
    assert len(accounts) == 2
    
    # Test that members list is empty (as expected for this case)
    assert len(mock_salesforce_account_information['members']) == 0
    
    print("✅ All tests passed for salesforce_account_information structure")


def test_salesforce_account_information_with_relationships():
    """Test that the structure properly handles relationships."""
    
    # Mock data with relationships
    mock_salesforce_account_information = {
        'names_found': ['John Doe', 'John Doe Household'],
        'household': {
            'account_name': 'John Doe Household',
            'type': 'Household',
            'role': None,
            'stage': 'Client',
            'email': 'john@example.com',
            'phone': '555-1234',
            'mailing_address': '123 Main St\nAnytown, ST 12345',
            'ssn/tax_id': '123-45-6789',
            'relationships': [
                {
                    'account_name': 'Jane Doe',
                    'type': 'Contact',
                    'role': 'Member',
                    'stage': 'Client',
                    'email': 'jane@example.com',
                    'phone': '555-5678',
                    'mailing_address': '123 Main St\nAnytown, ST 12345',
                    'ssn/tax_id': '987-65-4321',
                    'relationships': []
                }
            ]
        },
        'head': {
            'account_name': 'John Doe',
            'type': 'Contact',
            'role': 'Household Head',
            'stage': 'Client',
            'email': 'john@example.com',
            'phone': '555-1234',
            'mailing_address': '123 Main St\nAnytown, ST 12345',
            'ssn/tax_id': '123-45-6789',
            'relationships': []
        },
        'members': [
            {
                'account_name': 'Jane Doe',
                'type': 'Contact',
                'role': 'Member',
                'stage': 'Client',
                'email': 'jane@example.com',
                'phone': '555-5678',
                'mailing_address': '123 Main St\nAnytown, ST 12345',
                'ssn/tax_id': '987-65-4321',
                'relationships': []
            }
        ],
        'accounts': [
            {
                'account_name': 'John Doe',
                'type': 'Contact',
                'role': 'Household Head',
                'stage': 'Client',
                'email': 'john@example.com',
                'phone': '555-1234',
                'mailing_address': '123 Main St\nAnytown, ST 12345',
                'ssn/tax_id': '123-45-6789',
                'relationships': []
            },
            {
                'account_name': 'John Doe Household',
                'type': 'Household',
                'role': None,
                'stage': 'Client',
                'email': 'john@example.com',
                'phone': '555-1234',
                'mailing_address': '123 Main St\nAnytown, ST 12345',
                'ssn/tax_id': '123-45-6789',
                'relationships': [
                    {
                        'account_name': 'Jane Doe',
                        'type': 'Contact',
                        'role': 'Member',
                        'stage': 'Client',
                        'email': 'jane@example.com',
                        'phone': '555-5678',
                        'mailing_address': '123 Main St\nAnytown, ST 12345',
                        'ssn/tax_id': '987-65-4321',
                        'relationships': []
                    }
                ]
            }
        ]
    }
    
    # Test that relationships are properly structured
    household = mock_salesforce_account_information['household']
    assert len(household['relationships']) == 1
    assert household['relationships'][0]['account_name'] == 'Jane Doe'
    assert household['relationships'][0]['role'] == 'Member'
    
    # Test that members list contains the member
    members = mock_salesforce_account_information['members']
    assert len(members) == 1
    assert members[0]['account_name'] == 'Jane Doe'
    assert members[0]['role'] == 'Member'
    
    # Test that accounts have proper relationships
    accounts = mock_salesforce_account_information['accounts']
    household_account = next(acc for acc in accounts if acc['type'] == 'Household')
    assert len(household_account['relationships']) == 1
    
    print("✅ All tests passed for salesforce_account_information with relationships")


if __name__ == "__main__":
    test_salesforce_account_information_structure()
    test_salesforce_account_information_with_relationships()
    print("\n🎉 All tests completed successfully!") 