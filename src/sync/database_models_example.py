"""
Example Usage of Database Models
================================

This script demonstrates how to use the object-oriented database models
to represent and work with database entities.
"""

from database_models import (
    DropboxAccount, DropboxAccountApplicationFile, DropboxAccountApplicationInfo,
    SalesforceAccount, SalesforceHousehold, SalesforceHouseholdMember,
    DropboxSalesforceMapping, SyncStatus, AccountAnalysis,
    ApplicationStatus, ApplicationType, SalesforceAccountType, SalesforceSyncStatus,
    compare_accounts, create_dropbox_account_from_dict, create_salesforce_account_from_dict
)

def example_dropbox_account_creation():
    """Example of creating a Dropbox account with related data."""
    print("=== Dropbox Account Creation Example ===")
    
    # Create person information
    person_info = DropboxAccountApplicationInfo(
        first_name="John",
        last_name="Doe",
        date_of_birth="1980-05-15",
        gender="Male",
        mailing_address_street="123 Main St",
        mailing_address_city="Anytown",
        mailing_address_state="CA",
        mailing_address_zip="90210",
        phone_number="555-123-4567",
        email_address="john.doe@email.com"
    )
    
    # Create application file
    app_file = DropboxAccountApplicationFile(
        file_name="life_insurance_application.pdf",
        file_path="/Dropbox/Accounts/John Doe/life_insurance_application.pdf",
        application_type=ApplicationType.LIFE_INSURANCE,
        status=ApplicationStatus.PROCESSED,
        extracted_text="John Doe, 123 Main St, Anytown, CA 90210...",
        ocr_confidence=0.95,
        processing_duration_seconds=2.5
    )
    
    # Create Dropbox account
    dropbox_account = DropboxAccount(
        folder="John Doe",
        first_name="John",
        last_name="Doe",
        total_account_application_files=1,
        processed_account_application_files=1,
        failed_account_application_files=0,
        salesforce_accounts_found_count=2
    )
    
    # Link relationships
    app_file.owner = person_info
    app_file.dropbox_account = dropbox_account
    dropbox_account.application_files = [app_file]
    
    print(f"Created Dropbox account: {dropbox_account.folder}")
    print(f"Full name: {dropbox_account.full_name()}")
    print(f"Processing stats: {dropbox_account.processing_stats()}")
    print(f"Salesforce search status: {dropbox_account.get_salesforce_search_status()}")
    print(f"Application file: {app_file.file_name}")
    print(f"File processed: {app_file.is_processed()}")
    print(f"OCR confidence: {app_file.ocr_confidence}")
    print()

def example_salesforce_account_creation():
    """Example of creating Salesforce accounts with household relationships."""
    print("=== Salesforce Account Creation Example ===")
    
    # Create household head
    household_head = SalesforceAccount(
        salesforce_account_id="0011234567890ABC",
        account_name="John Doe Household",
        account_type=SalesforceAccountType.HOUSEHOLD_HEAD,
        first_name="John",
        last_name="Doe",
        email="john.doe@email.com",
        phone="555-123-4567",
        stage="Prospect",
        writing_advisor="Jane Smith"
    )
    
    # Create household member
    household_member = SalesforceAccount(
        salesforce_account_id="0011234567890DEF",
        account_name="Jane Doe",
        account_type=SalesforceAccountType.HOUSEHOLD_MEMBER,
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@email.com",
        phone="555-123-4568"
    )
    
    # Create household
    household = SalesforceHousehold(
        salesforce_household_id="0011234567890GHI",
        household_name="Doe Household",
        household_head_id=household_head.salesforce_account_id
    )
    
    # Create household member relationship
    household_member_rel = SalesforceHouseholdMember(
        household_id=household.salesforce_household_id,
        member_id=household_member.salesforce_account_id,
        role="Spouse"
    )
    
    # Link relationships
    household.household_head = household_head
    household.members = [household_member_rel]
    household_member_rel.household = household
    household_member_rel.member_account = household_member
    
    print(f"Created household: {household.household_name}")
    print(f"Household head: {household_head.full_name()}")
    print(f"Household member: {household_member.full_name()}")
    print(f"Total members: {household.member_count()}")
    print(f"All members: {[member.full_name() for member in household.get_all_members()]}")
    print()

def example_mapping_and_sync():
    """Example of creating mappings and sync status."""
    print("=== Mapping and Sync Example ===")
    
    # Create a mapping
    mapping = DropboxSalesforceMapping(
        dropbox_account_id=1,
        salesforce_account_id="0011234567890ABC",
        mapping_type="Direct",
        confidence_score=0.95,
        mapping_rules={"name_match": True, "email_match": True}
    )
    
    # Create sync status
    sync_status = SyncStatus(
        dropbox_account_id=1,
        salesforce_account_id="0011234567890ABC",
        sync_status=SalesforceSyncStatus.SYNCED,
        sync_direction="bidirectional",
        fields_synced=["first_name", "last_name", "email", "phone"],
        fields_failed=[],
        sync_errors=[]
    )
    
    print(f"Mapping: {mapping.get_mapping_description()}")
    print(f"High confidence: {mapping.is_high_confidence()}")
    print(f"Sync status: {sync_status.sync_status}")
    print(f"Sync summary: {sync_status.sync_summary()}")
    print(f"Is synced: {sync_status.is_synced()}")
    print(f"Has errors: {sync_status.has_errors()}")
    print()

def example_account_comparison():
    """Example of comparing Dropbox and Salesforce accounts."""
    print("=== Account Comparison Example ===")
    
    # Create Dropbox account with best info
    dropbox_account = DropboxAccount(
        folder="John Doe",
        first_name="John",
        last_name="Doe"
    )
    
    dropbox_account.best_info = dropbox_account.__class__.best_info.model_validate({
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@email.com",
        "phone": "555-123-4567",
        "address": "123 Main St",
        "city": "Anytown",
        "state": "CA",
        "zip_code": "90210"
    })
    
    # Create Salesforce account
    salesforce_account = SalesforceAccount(
        salesforce_account_id="0011234567890ABC",
        first_name="John",
        last_name="Doe",
        email="john.doe@email.com",
        phone="555-123-4567",
        address="123 Main St",
        city="Anytown",
        state="CA",
        zip_code="90210"
    )
    
    # Compare accounts
    comparison = compare_accounts(dropbox_account, salesforce_account)
    
    print(f"Comparing: {dropbox_account.full_name()} vs {salesforce_account.full_name()}")
    print(f"Name match: {comparison['name_match']}")
    print(f"Email match: {comparison['email_match']}")
    print(f"Phone match: {comparison['phone_match']}")
    print(f"Address match: {comparison['address_match']}")
    print(f"Missing in Salesforce: {comparison['missing_in_salesforce']}")
    print(f"Missing in Dropbox: {comparison['missing_in_dropbox']}")
    print()

def example_from_dict_creation():
    """Example of creating objects from dictionaries."""
    print("=== Dictionary Creation Example ===")
    
    # Sample data from database
    dropbox_data = {
        "id": 1,
        "folder": "Jane Smith",
        "first_name": "Jane",
        "last_name": "Smith",
        "total_account_application_files": 3,
        "processed_account_application_files": 2,
        "failed_account_application_files": 1,
        "salesforce_accounts_found_count": 1,
        "created_at": "2024-01-15T10:30:00Z"
    }
    
    salesforce_data = {
        "id": 1,
        "salesforce_account_id": "0011234567890XYZ",
        "account_name": "Jane Smith",
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane.smith@email.com",
        "stage": "Customer",
        "created_at": "2024-01-15T10:30:00Z"
    }
    
    # Create objects from dictionaries
    dropbox_account = create_dropbox_account_from_dict(dropbox_data)
    salesforce_account = create_salesforce_account_from_dict(salesforce_data)
    
    print(f"Created from dict - Dropbox: {dropbox_account.folder}")
    print(f"Created from dict - Salesforce: {salesforce_account.account_name}")
    print(f"Dropbox processing stats: {dropbox_account.processing_stats()}")
    print(f"Salesforce account type: {salesforce_account.account_type}")
    print()

def example_analysis_creation():
    """Example of creating account analysis."""
    print("=== Account Analysis Example ===")
    
    analysis = AccountAnalysis(
        dropbox_account_id=1,
        salesforce_account_id="0011234567890ABC",
        analysis_type="data_comparison",
        analysis_data={
            "field_comparisons": {
                "name": {"match": True, "confidence": 0.95},
                "email": {"match": True, "confidence": 0.90},
                "phone": {"match": False, "confidence": 0.30}
            },
            "overall_confidence": 0.72
        },
        recommendations=[
            "Update phone number in Salesforce",
            "Verify email address format",
            "Consider merging duplicate records"
        ],
        missing_fields=["ssn_tax_id", "drivers_license"]
    )
    
    print(f"Analysis type: {analysis.analysis_type}")
    print(f"Analysis summary: {analysis.get_analysis_summary()}")
    print(f"Recommendations: {len(analysis.recommendations)}")
    print(f"Missing fields: {len(analysis.missing_fields)}")
    print(f"Overall confidence: {analysis.analysis_data.get('overall_confidence', 'N/A')}")
    print()

def main():
    """Run all examples."""
    print("Object-Oriented Database Models Examples")
    print("=" * 50)
    print()
    
    example_dropbox_account_creation()
    example_salesforce_account_creation()
    example_mapping_and_sync()
    example_account_comparison()
    example_from_dict_creation()
    example_analysis_creation()
    
    print("All examples completed!")

if __name__ == "__main__":
    main() 