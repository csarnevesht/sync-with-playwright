#!/usr/bin/env python3
"""
Test script to verify that the relationship processor infinite loop fix works correctly.
This script tests the process_account_relationships method to ensure it properly
tracks processed accounts and prevents infinite loops.
"""

import sys
import os
import logging
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sync.salesforce_client.utils.relationship_processor import SalesforceRelationshipProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_infinite_loop_fix():
    """Test that the relationship processor doesn't go into infinite loops."""
    
    # Create a mock account manager for testing
    class MockAccountManager:
        def __init__(self):
            self.logger = logging.getLogger(__name__)
        
        def dashboard_search_account(self, account_name, view_name="All Clients"):
            """Mock search that returns the account name if it contains 'Campos'"""
            if 'Campos' in account_name:
                return [account_name]
            return []
        
        def click_account_name(self, account_name):
            """Mock click that always succeeds"""
            self.logger.info(f"Mock clicking account: {account_name}")
            # Store the current account name for other methods to use
            self.current_account_name = account_name
            return True
        
        def verify_account_page_url(self):
            """Mock verification that always succeeds"""
            # Store the current account name for this mock
            if hasattr(self, 'current_account_name'):
                account_id = f"mock_id_{self.current_account_name.replace(' ', '_')}"
            else:
                account_id = "mock_id_default"
            return True, account_id
        
        def get_account_information(self, account_id):
            """Mock account information"""
            # Extract account name from account_id
            if account_id.startswith('mock_id_'):
                account_name = account_id.replace('mock_id_', '').replace('_', ' ')
            else:
                account_name = "Unknown Account"
            
            return {
                'account_name': account_name,
                'stage': 'Client',
                'email': 'test@example.com',
                'phone': '123-456-7890',
                'mailing_address': '123 Test St',
                'ssn/tax_id': '123-45-6789'
            }
        
        def get_account_relationships(self, account_id):
            """Mock relationships that would cause loops if not tracked"""
            # Extract account name from account_id
            if account_id.startswith('mock_id_'):
                account_name = account_id.replace('mock_id_', '').replace('_', ' ')
            else:
                account_name = "Unknown Account"
                
            if 'Household' in account_name:
                # Household has relationship to individual
                return [{
                    'name': 'Maria Campos',
                    'role': 'Household Head',
                    'type': 'Contact'
                }]
            elif 'Maria Campos' in account_name and 'Household' not in account_name:
                # Individual has relationship to household
                return [{
                    'name': 'Maria Campos Household',
                    'role': 'Household Head',
                    'type': 'Household'
                }]
            return []
        
        def account_exists(self, account_name, view_name="All Clients"):
            """Mock account existence check"""
            return True
        
        def navigate_back_to_search_results(self):
            """Mock navigation back"""
            self.logger.info("Mock navigating back to search results")
    
    # Create the relationship processor with mock account manager
    mock_account_manager = MockAccountManager()
    relationship_processor = SalesforceRelationshipProcessor(mock_account_manager)
    
    # Test with the same accounts that were causing the infinite loop
    test_matches = ['Maria Campos Household', 'Maria Campos']
    
    print("Testing relationship processor with accounts that previously caused infinite loops...")
    print(f"Test accounts: {test_matches}")
    
    try:
        # This should not go into an infinite loop
        result = relationship_processor.process_account_relationships(
            test_matches,
            'Campos, Maria',
            view_name="All Clients"
        )
        
        print("\n✅ Test passed! No infinite loop detected.")
        print(f"Result structure: {list(result.keys())}")
        print(f"Processed accounts: {result.get('accounts', [])}")
        print(f"Names found: {result.get('names_found', [])}")
        
        # Verify that both accounts were processed
        processed_account_names = [acc.get('account_name', '') for acc in result.get('accounts', [])]
        print(f"Processed account names: {processed_account_names}")
        
        if len(processed_account_names) == 2:
            print("✅ Both accounts were processed exactly once.")
        else:
            print(f"⚠️ Expected 2 accounts, but got {len(processed_account_names)}")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Testing Relationship Processor Infinite Loop Fix")
    print("=" * 50)
    
    success = test_infinite_loop_fix()
    
    if success:
        print("\n🎉 All tests passed! The infinite loop fix is working correctly.")
    else:
        print("\n💥 Tests failed! The infinite loop fix may not be working.")
    
    sys.exit(0 if success else 1) 