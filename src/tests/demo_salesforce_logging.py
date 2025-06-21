"""
Demo Salesforce Account Information Logging

This script demonstrates the new analysis logging format for Salesforce Account Information
with icons, better formatting, and visual appeal.
"""

import logging
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from sync.salesforce_client.utils.logging_utils import log_command_analysis

# Configure logging to show the analysis format
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def demo_salesforce_logging():
    """Demonstrate the new analysis Salesforce Account Information logging format."""
    
    # Mock salesforce_account_information data
    salesforce_account_information = {
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
            'relationships': [
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
                }
            ]
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
                'relationships': [
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
                    }
                ]
            }
        ]
    }
    
    # Demo the analysis logging format using the new utility
    log_command_analysis(salesforce_account_information, logger)
    
    logger.info("\n🎉 Demo completed! This shows the new analysis logging format.")


if __name__ == "__main__":
    demo_salesforce_logging() 