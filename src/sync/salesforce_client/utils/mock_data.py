from typing import List, Dict
from datetime import datetime

def get_mock_accounts() -> List[Dict]:
    """Get mock account data for testing."""
    return [
        {
            'folder_name': 'John Smith',
            'first_name': 'John',
            'last_name': 'Smith',
            'middle_name': None,
            'account_info': {
                'date_of_birth': '01/15/1980',
                'age': '43',
                'sex': 'M',
                'ssn': '123-45-6789',
                'email': 'john.smith@example.com',
                'phone': '555-123-4567',
                'address': '123 Main St',
                'city': 'New York',
                'state': 'NY',
                'zip': '10001'
            },
            'files': [
                {
                    'name': 'John Smith Application.pdf',
                    'content': b'Mock PDF content',
                    'modified': datetime(2024, 3, 15)
                },
                {
                    'name': 'John Smith DL.jpeg',
                    'content': b'Mock JPEG content',
                    'modified': datetime(2024, 3, 15)
                }
            ]
        }
    ] 