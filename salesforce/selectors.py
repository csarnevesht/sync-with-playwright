from typing import Dict, List

class Selectors:
    """Centralized management of selectors used in Salesforce automation."""
    
    # Account page selectors
    ACCOUNT = {
        'search_input': 'input[placeholder="Search this list..."]',
        'account_table': 'table[role="grid"]',
        'account_link': 'a[data-refid="recordId"][data-special-link="true"]',
        'account_name': 'h1.slds-page-header__title',
        'new_button': [
            '(//div[@title="New"])[1]',
            'button:has-text("New")',
            'button.slds-button:has-text("New")',
            'button[title="New"]',
            '//button[contains(text(), "New")]'
        ],
        'save_button': 'button:has-text("Save")',
        'toast_message': 'div.slds-notify_toast'
    }
    
    # Files page selectors
    FILES = {
        'files_tab': 'span[title="Files"]',
        'files_table': 'table.slds-table',
        'file_search': 'input[placeholder="Search Files..."]',
        'file_name': 'span.itemTitle',
        'upload_button': 'button:has-text("Upload Files")',
        'file_input': 'input[type="file"]'
    }
    
    # Form selectors
    FORM = {
        'client_radio': [
            'input[type="radio"][name="RecordType"][value="012000000000000AAA"]',
            'input[type="radio"][name="RecordType"][value="012000000000000"]',
            'input[type="radio"][name="RecordType"]'
        ],
        'next_button': 'button:has-text("Next")',
        'name_fields': {
            'first_name': 'input[placeholder="First Name"]',
            'last_name': 'input[placeholder="Last Name"]',
            'middle_name': 'input[placeholder="Middle Name"]'
        },
        'phone_field': [
            'input[placeholder="Phone"]',
            'input[type="tel"]',
            'input[name="Phone"]'
        ]
    }
    
    @classmethod
    def get_selector(cls, category: str, key: str) -> str:
        """Get a single selector by category and key."""
        if category not in cls.__dict__:
            raise ValueError(f"Invalid selector category: {category}")
        category_dict = getattr(cls, category)
        if key not in category_dict:
            raise ValueError(f"Invalid selector key: {key} in category {category}")
        return category_dict[key]
    
    @classmethod
    def get_selectors(cls, category: str, key: str) -> List[str]:
        """Get a list of selectors by category and key."""
        selector = cls.get_selector(category, key)
        return selector if isinstance(selector, list) else [selector] 