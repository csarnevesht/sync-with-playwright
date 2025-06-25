"""
Database Object Visualization
============================

This script creates visual representations of the database object relationships
and structure.
"""

from database_models import *
import json
from typing import Dict, Any, List

class DatabaseVisualizer:
    """Creates visual representations of database objects and relationships."""
    
    def __init__(self):
        self.indent = "  "
    
    def visualize_class_hierarchy(self) -> str:
        """Create a visual representation of the class hierarchy."""
        hierarchy = """
Database Object Hierarchy
========================

BaseDatabaseModel (Pydantic BaseModel)
├── DropboxAccountApplicationInfo
├── DropboxAccountApplicationFile
├── DropboxAccountClientListInfo
├── DropboxAccountBestInfo
├── DropboxAccount
│   └── Key Fields:
│       ├── folder: str (unique identifier)
│       ├── first_name, middle_name, last_name: str
│       ├── total_account_application_files: int
│       ├── processed_account_application_files: int
│       ├── failed_account_application_files: int
│       └── salesforce_accounts_found_count: Optional[int]
│           └── Salesforce Search Status:
│               ├── null/None: "Not searched yet"
│               ├── -1: "Search attempted but failed"
│               ├── 0: "Searched - No accounts found"
│               └── >0: "Searched - N accounts found"
├── SalesforceAccount
├── SalesforceHousehold
├── SalesforceHouseholdMember
├── DropboxSalesforceMapping
├── SyncStatus
└── AccountAnalysis

Enums
-----
├── ApplicationStatus (Processed, Failed, Error, Skipped)
├── ApplicationType (Life Insurance, Annuity, EquiTrust Annuity, Security Benefit, Unknown)
├── SalesforceAccountType (Contact, Household, Household_Head, Household_Member)
└── SalesforceSyncStatus (pending, synced, failed, needs_update)
"""
        return hierarchy
    
    def visualize_relationships(self) -> str:
        """Create a visual representation of object relationships."""
        relationships = """
Object Relationships
===================

DropboxAccount (Main Entity)
├── application_files: List[DropboxAccountApplicationFile]
├── client_list_info: DropboxAccountClientListInfo (1:1)
├── best_info: DropboxAccountBestInfo (1:1)
├── salesforce_mappings: List[DropboxSalesforceMapping]
└── sync_statuses: List[SyncStatus]

DropboxAccountApplicationFile
├── owner: DropboxAccountApplicationInfo (Many:1)
├── joint_owner: DropboxAccountApplicationInfo (Many:1)
└── dropbox_account: DropboxAccount (Many:1)

DropboxAccountApplicationInfo
├── owned_files: List[DropboxAccountApplicationFile] (1:Many)
└── joint_owned_files: List[DropboxAccountApplicationFile] (1:Many)

SalesforceAccount
├── household_head: SalesforceHousehold (1:1)
├── household_memberships: List[SalesforceHouseholdMember] (1:Many)
├── dropbox_mappings: List[DropboxSalesforceMapping] (1:Many)
└── sync_statuses: List[SyncStatus] (1:Many)

SalesforceHousehold
├── household_head: SalesforceAccount (1:1)
└── members: List[SalesforceHouseholdMember] (1:Many)

SalesforceHouseholdMember
├── household: SalesforceHousehold (Many:1)
└── member_account: SalesforceAccount (Many:1)

DropboxSalesforceMapping
├── dropbox_account: DropboxAccount (Many:1)
└── salesforce_account: SalesforceAccount (Many:1)

SyncStatus
├── dropbox_account: DropboxAccount (Many:1)
└── salesforce_account: SalesforceAccount (Many:1)

AccountAnalysis
├── dropbox_account: DropboxAccount (Many:1)
└── salesforce_account: SalesforceAccount (Many:1)
"""
        return relationships
    
    def visualize_data_flow(self) -> str:
        """Create a visual representation of data flow."""
        data_flow = """
Data Flow and Processing
========================

1. Dropbox Data Sources
   ┌─────────────────┐    ┌─────────────────────┐
   │ Application     │    │ Client List         │
   │ Files           │    │ Excel Files         │
   └─────────────────┘    └─────────────────────┘
           │                        │
           ▼                        ▼
   ┌─────────────────┐    ┌─────────────────────┐
   │ Application     │    │ Client List         │
   │ Info (OCR)      │    │ Info (Parsed)       │
   └─────────────────┘    └─────────────────────┘
           │                        │
           └────────────┬───────────┘
                        ▼
              ┌─────────────────┐
              │ Best Info       │
              │ (Merged)        │
              └─────────────────┘

2. Salesforce Data Sources
   ┌─────────────────┐
   │ Salesforce CRM  │
   │ System          │
   └─────────────────┘
           │
           ▼
   ┌─────────────────┐    ┌─────────────────────┐
   │ Accounts        │    │ Households          │
   │ (Contacts)      │    │ (Groups)            │
   └─────────────────┘    └─────────────────────┘

3. Mapping and Sync
   ┌─────────────────┐    ┌─────────────────────┐
   │ Dropbox         │◄──►│ Salesforce          │
   │ Accounts        │    │ Accounts            │
   └─────────────────┘    └─────────────────────┘
           │                        │
           ▼                        ▼
   ┌─────────────────┐    ┌─────────────────────┐
   │ Mapping         │    │ Sync Status         │
   │ (Relationships) │    │ (Sync History)      │
   └─────────────────┘    └─────────────────────┘

4. Analysis
   ┌─────────────────┐
   │ Account         │
   │ Analysis        │
   │ (Comparisons)   │
   └─────────────────┘

Salesforce Search Status Tracking
================================
┌─────────────────────────────────────────────────────────────┐
│ DropboxAccount.salesforce_accounts_found_count             │
├─────────────────────────────────────────────────────────────┤
│ null/None: "Not searched yet"                              │
│ -1: "Search attempted but failed"                          │
│ 0: "Searched - No accounts found"                          │
│ >0: "Searched - N accounts found"                          │
└─────────────────────────────────────────────────────────────┘
"""
        return data_flow
    
    def create_sample_object_tree(self) -> Dict[str, Any]:
        """Create a sample object tree showing relationships."""
        # Create sample objects
        dropbox_account = DropboxAccount(
            id=1,
            folder="John Doe",
            first_name="John",
            last_name="Doe",
            total_account_application_files=2,
            processed_account_application_files=2,
            failed_account_application_files=0,
            salesforce_accounts_found_count=1
        )
        
        person_info = DropboxAccountApplicationInfo(
            id=1,
            first_name="John",
            last_name="Doe",
            email_address="john.doe@email.com",
            phone_number="555-123-4567"
        )
        
        app_file = DropboxAccountApplicationFile(
            id=1,
            file_name="life_insurance_app.pdf",
            application_type=ApplicationType.LIFE_INSURANCE,
            status=ApplicationStatus.PROCESSED,
            owner_id=1,
            dropbox_account_id=1
        )
        
        salesforce_account = SalesforceAccount(
            id=1,
            salesforce_account_id="0011234567890ABC",
            account_name="John Doe",
            first_name="John",
            last_name="Doe",
            email="john.doe@email.com",
            phone="555-123-4567"
        )
        
        mapping = DropboxSalesforceMapping(
            id=1,
            dropbox_account_id=1,
            salesforce_account_id="0011234567890ABC",
            mapping_type="Direct",
            confidence_score=0.95
        )
        
        sync_status = SyncStatus(
            id=1,
            dropbox_account_id=1,
            salesforce_account_id="0011234567890ABC",
            sync_status=SalesforceSyncStatus.SYNCED,
            fields_synced=["first_name", "last_name", "email"]
        )
        
        # Create object tree
        object_tree = {
            "dropbox_account": {
                "id": dropbox_account.id,
                "folder": dropbox_account.folder,
                "full_name": dropbox_account.full_name(),
                "processing_stats": dropbox_account.processing_stats(),
                "salesforce_search_status": dropbox_account.get_salesforce_search_status(),
                "relationships": {
                    "application_files": [
                        {
                            "id": app_file.id,
                            "file_name": app_file.file_name,
                            "application_type": app_file.application_type.value,
                            "status": app_file.status.value,
                            "is_processed": app_file.is_processed(),
                            "owner": {
                                "id": person_info.id,
                                "full_name": person_info.full_name(),
                                "email": person_info.email_address,
                                "phone": person_info.phone_number
                            }
                        }
                    ],
                    "salesforce_mappings": [
                        {
                            "id": mapping.id,
                            "mapping_type": mapping.mapping_type,
                            "confidence_score": mapping.confidence_score,
                            "is_high_confidence": mapping.is_high_confidence(),
                            "salesforce_account": {
                                "id": salesforce_account.id,
                                "salesforce_account_id": salesforce_account.salesforce_account_id,
                                "account_name": salesforce_account.account_name,
                                "full_name": salesforce_account.full_name(),
                                "email": salesforce_account.email,
                                "phone": salesforce_account.phone
                            }
                        }
                    ],
                    "sync_statuses": [
                        {
                            "id": sync_status.id,
                            "sync_status": sync_status.sync_status.value,
                            "is_synced": sync_status.is_synced(),
                            "sync_summary": sync_status.sync_summary()
                        }
                    ]
                }
            }
        }
        
        return object_tree
    
    def visualize_sample_tree(self) -> str:
        """Create a visual representation of the sample object tree."""
        tree = """
Sample Object Tree
=================

DropboxAccount (id=1, folder="John Doe")
├── full_name: "John Doe"
├── processing_stats: {"total_files": 2, "processed_files": 2, "failed_files": 0, "success_rate": 100.0}
├── salesforce_accounts_found_count: 1 (Searched - 1 accounts found)
│   └── Status Meanings:
│       ├── null/None: "Not searched yet"
│       ├── -1: "Search attempted but failed"
│       ├── 0: "Searched - No accounts found"
│       └── >0: "Searched - N accounts found"
│
├── application_files:
│   └── DropboxAccountApplicationFile (id=1, "life_insurance_app.pdf")
│       ├── application_type: "Life Insurance"
│       ├── status: "Processed"
│       ├── is_processed: True
│       └── owner: DropboxAccountApplicationInfo (id=1)
│           ├── full_name: "John Doe"
│           ├── email: "john.doe@email.com"
│           └── phone: "555-123-4567"
│
├── salesforce_mappings:
│   └── DropboxSalesforceMapping (id=1)
│       ├── mapping_type: "Direct"
│       ├── confidence_score: 0.95
│       ├── is_high_confidence: True
│       └── salesforce_account: SalesforceAccount (id=1, "0011234567890ABC")
│           ├── account_name: "John Doe"
│           ├── full_name: "John Doe"
│           ├── email: "john.doe@email.com"
│           └── phone: "555-123-4567"
│
└── sync_statuses:
    └── SyncStatus (id=1)
        ├── sync_status: "synced"
        ├── is_synced: True
        └── sync_summary: {"status": "synced", "fields_synced": 3, "fields_failed": 0, "error_count": 0}
"""
        return tree
    
    def get_method_summary(self) -> str:
        """Create a summary of available methods."""
        methods = """
Available Methods
================

DropboxAccount:
├── full_name() -> str
├── processing_stats() -> Dict[str, Any]
├── has_salesforce_search_been_done() -> bool
│   └── Returns True if salesforce_accounts_found_count is not None
├── get_salesforce_search_status() -> str
│   └── Returns human-readable status based on salesforce_accounts_found_count:
│       ├── "Not searched" (null/None)
│       ├── "Searched - No accounts found" (0)
│       └── "Searched - N accounts found" (>0)
└── Salesforce Search Status Field:
    └── salesforce_accounts_found_count: Optional[int]
        ├── null/None: Not searched yet
        ├── -1: Search attempted but failed
        ├── 0: Searched - No accounts found
        └── >0: Searched - N accounts found

DropboxAccountApplicationFile:
├── is_processed() -> bool
├── has_ocr_data() -> bool
└── get_processing_info() -> Dict[str, Any]

DropboxAccountApplicationInfo:
├── full_name() -> str
└── address_string() -> str

DropboxAccountBestInfo:
├── full_name() -> str
├── address_string() -> str
├── get_data_source_for_field(field_name: str) -> Optional[str]
└── get_confidence_for_field(field_name: str) -> Optional[float]

SalesforceAccount:
├── full_name() -> str
├── address_string() -> str
├── is_household_head() -> bool
└── is_household_member() -> bool

SalesforceHousehold:
├── get_all_members() -> List[SalesforceAccount]
└── member_count() -> int

DropboxSalesforceMapping:
├── is_high_confidence() -> bool
└── get_mapping_description() -> str

SyncStatus:
├── is_synced() -> bool
├── has_errors() -> bool
├── get_last_error() -> Optional[Dict[str, Any]]
└── sync_summary() -> Dict[str, Any]

AccountAnalysis:
└── get_analysis_summary() -> Dict[str, Any]

Utility Functions:
├── create_dropbox_account_from_dict(data: Dict[str, Any]) -> DropboxAccount
├── create_salesforce_account_from_dict(data: Dict[str, Any]) -> SalesforceAccount
└── compare_accounts(dropbox_account: DropboxAccount, salesforce_account: SalesforceAccount) -> Dict[str, Any]
"""
        return methods
    
    def generate_full_visualization(self) -> str:
        """Generate a complete visualization of the database objects."""
        visualization = f"""
{self.visualize_class_hierarchy()}

{self.visualize_relationships()}

{self.visualize_data_flow()}

{self.visualize_sample_tree()}

{self.get_method_summary()}
"""
        return visualization

def main():
    """Generate and display the full visualization."""
    visualizer = DatabaseVisualizer()
    
    print("Database Object Visualization")
    print("=" * 50)
    print()
    
    # Generate full visualization
    full_viz = visualizer.generate_full_visualization()
    print(full_viz)
    
    # Generate sample object tree as JSON
    print("Sample Object Tree (JSON):")
    print("=" * 30)
    sample_tree = visualizer.create_sample_object_tree()
    print(json.dumps(sample_tree, indent=2, default=str))

if __name__ == "__main__":
    main() 