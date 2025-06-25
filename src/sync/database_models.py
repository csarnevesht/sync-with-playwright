"""
Object-Oriented Database Models
==============================

This module provides Python classes that represent the database schema
in an object-oriented way, including relationships, enums, and database operations.
"""

from typing import Optional, List, Dict, Any, Union, ForwardRef
from datetime import datetime, date
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
import json

# ============================================================================
# ENUMS
# ============================================================================

class ApplicationStatus(str, Enum):
    """Enum for application processing status."""
    PROCESSED = "Processed"
    FAILED = "Failed"
    ERROR = "Error"
    SKIPPED = "Skipped"

class ApplicationType(str, Enum):
    """Enum for application types."""
    LIFE_INSURANCE = "Life Insurance"
    ANNUITY = "Annuity"
    EQUITRUST_ANNUITY = "EquiTrust Annuity"
    SECURITY_BENEFIT = "Security Benefit"
    UNKNOWN = "Unknown"

class SalesforceAccountType(str, Enum):
    """Enum for Salesforce account types."""
    CONTACT = "Contact"
    HOUSEHOLD = "Household"
    HOUSEHOLD_HEAD = "Household_Head"
    HOUSEHOLD_MEMBER = "Household_Member"

class SalesforceSyncStatus(str, Enum):
    """Enum for Salesforce sync status."""
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"
    NEEDS_UPDATE = "needs_update"

# ============================================================================
# BASE MODELS
# ============================================================================

class BaseDatabaseModel(BaseModel):
    """Base model for all database entities."""
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None
        }

# ============================================================================
# DROPBOX SYSTEM MODELS
# ============================================================================

class DropboxAccountApplicationInfo(BaseDatabaseModel):
    """Represents person information extracted from Dropbox application files."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    mailing_address_street: Optional[str] = None
    mailing_address_city: Optional[str] = None
    mailing_address_state: Optional[str] = None
    mailing_address_zip: Optional[str] = None
    phone_number: Optional[str] = None
    email_address: Optional[str] = None
    ocr_method: Optional[str] = None
    
    # Relationships (will be populated by database operations)
    owned_files: List['DropboxAccountApplicationFile'] = []
    joint_owned_files: List['DropboxAccountApplicationFile'] = []
    
    def full_name(self) -> str:
        """Get the full name of the person."""
        parts = [self.first_name, self.last_name]
        return " ".join(filter(None, parts)) or "Unknown"
    
    def address_string(self) -> str:
        """Get the full address as a string."""
        parts = [
            self.mailing_address_street,
            self.mailing_address_city,
            self.mailing_address_state,
            self.mailing_address_zip
        ]
        return ", ".join(filter(None, parts)) or "No address"

class DropboxAccountApplicationFile(BaseDatabaseModel):
    """Represents application files stored in Dropbox."""
    file_name: str
    file_path: Optional[str] = None
    application_type: ApplicationType = ApplicationType.UNKNOWN
    status: ApplicationStatus = ApplicationStatus.PROCESSED
    owner_id: Optional[int] = None
    joint_owner_id: Optional[int] = None
    notes: List[Dict[str, Any]] = Field(default_factory=list)
    extracted_text: Optional[str] = None
    processing_timestamp: Optional[datetime] = None
    ocr_confidence: Optional[float] = None
    lm_studio_model_used: Optional[str] = None
    processing_duration_seconds: Optional[float] = None
    dropbox_account_id: Optional[int] = None
    
    # Relationships (will be populated by database operations)
    owner: Optional[DropboxAccountApplicationInfo] = None
    joint_owner: Optional[DropboxAccountApplicationInfo] = None
    dropbox_account: Optional['DropboxAccount'] = None
    
    def is_processed(self) -> bool:
        """Check if the file has been successfully processed."""
        return self.status == ApplicationStatus.PROCESSED
    
    def has_ocr_data(self) -> bool:
        """Check if the file has OCR extracted text."""
        return bool(self.extracted_text and self.ocr_confidence)
    
    def get_processing_info(self) -> Dict[str, Any]:
        """Get processing information as a dictionary."""
        return {
            "status": self.status,
            "processing_timestamp": self.processing_timestamp,
            "ocr_confidence": self.ocr_confidence,
            "processing_duration": self.processing_duration_seconds,
            "model_used": self.lm_studio_model_used
        }

class DropboxAccountClientListInfo(BaseDatabaseModel):
    """Represents account information from client list Excel files."""
    dropbox_account_id: Optional[int] = None
    account_name: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    birthdate: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    email: Optional[str] = None
    additional_info: Optional[str] = None
    match_status: Optional[str] = None
    drivers_license_data: Dict[str, Any] = Field(default_factory=dict)
    search_info: Dict[str, Any] = Field(default_factory=dict)
    
    # Relationships (will be populated by database operations)
    dropbox_account: Optional['DropboxAccount'] = None
    
    def full_name(self) -> str:
        """Get the full name including middle name."""
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(filter(None, parts)) or "Unknown"
    
    def address_string(self) -> str:
        """Get the full address as a string."""
        parts = [self.address, self.city, self.state, self.zip_code]
        return ", ".join(filter(None, parts)) or "No address"

class DropboxAccountBestInfo(BaseDatabaseModel):
    """Represents the best available information from all Dropbox sources."""
    dropbox_account_id: Optional[int] = None
    account_name: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    birthdate: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    email: Optional[str] = None
    additional_info: Optional[str] = None
    ssn_tax_id: Optional[str] = None
    data_sources: Dict[str, Any] = Field(default_factory=dict)
    field_precedence: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: Optional[float] = None
    
    # Relationships (will be populated by database operations)
    dropbox_account: Optional['DropboxAccount'] = None
    
    def full_name(self) -> str:
        """Get the full name including middle name."""
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(filter(None, parts)) or "Unknown"
    
    def address_string(self) -> str:
        """Get the full address as a string."""
        parts = [self.address, self.city, self.state, self.zip_code]
        return ", ".join(filter(None, parts)) or "No address"
    
    def get_data_source_for_field(self, field_name: str) -> Optional[str]:
        """Get which data source was used for a specific field."""
        return self.field_precedence.get(field_name)
    
    def get_confidence_for_field(self, field_name: str) -> Optional[float]:
        """Get confidence score for a specific field."""
        return self.data_sources.get(field_name, {}).get('confidence')

class DropboxAccount(BaseDatabaseModel):
    """Represents a Dropbox account folder and its metadata."""
    folder: str
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    total_account_application_files: int = 0
    processed_account_application_files: int = 0
    failed_account_application_files: int = 0
    processing_timestamp: Optional[datetime] = None
    salesforce_accounts_found_count: Optional[int] = None  # -1 = no search, 0 = no results, >0 = count
    
    # Relationships (will be populated by database operations)
    application_files: List[DropboxAccountApplicationFile] = []
    client_list_info: Optional[DropboxAccountClientListInfo] = None
    best_info: Optional[DropboxAccountBestInfo] = None
    salesforce_mappings: List['DropboxSalesforceMapping'] = []
    sync_statuses: List['SyncStatus'] = []
    
    def full_name(self) -> str:
        """Get the full name from the account."""
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(filter(None, parts)) or "Unknown"
    
    def processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            "total_files": self.total_account_application_files,
            "processed_files": self.processed_account_application_files,
            "failed_files": self.failed_account_application_files,
            "success_rate": (self.processed_account_application_files / self.total_account_application_files * 100) if self.total_account_application_files > 0 else 0
        }
    
    def has_salesforce_search_been_done(self) -> bool:
        """Check if Salesforce search has been performed."""
        return self.salesforce_accounts_found_count is not None
    
    def get_salesforce_search_status(self) -> str:
        """Get the Salesforce search status."""
        if self.salesforce_accounts_found_count is None:
            return "Not searched"
        elif self.salesforce_accounts_found_count == 0:
            return "Searched - No accounts found"
        else:
            return f"Searched - {self.salesforce_accounts_found_count} accounts found"

# ============================================================================
# SALESFORCE SYSTEM MODELS
# ============================================================================

class SalesforceAccount(BaseDatabaseModel):
    """Represents a Salesforce account."""
    salesforce_account_id: str
    account_name: Optional[str] = None
    account_type: SalesforceAccountType = SalesforceAccountType.CONTACT
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    birthdate: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    email: Optional[str] = None
    ssn_tax_id: Optional[str] = None
    stage: Optional[str] = None
    writing_advisor: Optional[str] = None
    prospecting_status: Optional[str] = None
    account_record_type: Optional[str] = None
    
    # Relationships (will be populated by database operations)
    household_head: Optional['SalesforceHousehold'] = None
    household_memberships: List['SalesforceHouseholdMember'] = []
    dropbox_mappings: List['DropboxSalesforceMapping'] = []
    sync_statuses: List['SyncStatus'] = []
    
    def full_name(self) -> str:
        """Get the full name from the account."""
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(filter(None, parts)) or "Unknown"
    
    def address_string(self) -> str:
        """Get the full address as a string."""
        parts = [self.address, self.city, self.state, self.zip_code]
        return ", ".join(filter(None, parts)) or "No address"
    
    def is_household_head(self) -> bool:
        """Check if this account is a household head."""
        return self.account_type == SalesforceAccountType.HOUSEHOLD_HEAD
    
    def is_household_member(self) -> bool:
        """Check if this account is a household member."""
        return self.account_type == SalesforceAccountType.HOUSEHOLD_MEMBER

class SalesforceHousehold(BaseDatabaseModel):
    """Represents a Salesforce household."""
    salesforce_household_id: str
    household_name: Optional[str] = None
    household_head_id: Optional[str] = None
    
    # Relationships (will be populated by database operations)
    household_head: Optional[SalesforceAccount] = None
    members: List['SalesforceHouseholdMember'] = []
    
    def get_all_members(self) -> List[SalesforceAccount]:
        """Get all members including the head."""
        members = []
        if self.household_head:
            members.append(self.household_head)
        for member in self.members:
            if member.member_account:
                members.append(member.member_account)
        return members
    
    def member_count(self) -> int:
        """Get the total number of members including the head."""
        count = 1 if self.household_head else 0  # Head counts as 1
        count += len(self.members)
        return count

class SalesforceHouseholdMember(BaseDatabaseModel):
    """Represents a member of a Salesforce household."""
    household_id: str
    member_id: str
    role: Optional[str] = None
    
    # Relationships (will be populated by database operations)
    household: Optional[SalesforceHousehold] = None
    member_account: Optional[SalesforceAccount] = None

# ============================================================================
# MAPPING AND SYNC MODELS
# ============================================================================

class DropboxSalesforceMapping(BaseDatabaseModel):
    """Maps Dropbox accounts to Salesforce accounts."""
    dropbox_account_id: Optional[int] = None
    salesforce_account_id: str
    mapping_type: Optional[str] = None  # 'Household_Head', 'Household_Member', 'Direct'
    confidence_score: Optional[float] = None
    mapping_rules: Dict[str, Any] = Field(default_factory=dict)
    
    # Relationships (will be populated by database operations)
    dropbox_account: Optional[DropboxAccount] = None
    salesforce_account: Optional[SalesforceAccount] = None
    
    def is_high_confidence(self) -> bool:
        """Check if the mapping has high confidence."""
        return self.confidence_score is not None and self.confidence_score >= 0.8
    
    def get_mapping_description(self) -> str:
        """Get a human-readable description of the mapping."""
        base = f"Dropbox '{self.dropbox_account.folder if self.dropbox_account else 'Unknown'}' → Salesforce '{self.salesforce_account.account_name if self.salesforce_account else 'Unknown'}'"
        if self.mapping_type:
            base += f" ({self.mapping_type})"
        if self.confidence_score is not None:
            base += f" [Confidence: {self.confidence_score:.2f}]"
        return base

class SyncStatus(BaseDatabaseModel):
    """Tracks synchronization status between Dropbox and Salesforce."""
    dropbox_account_id: Optional[int] = None
    salesforce_account_id: str
    sync_status: SalesforceSyncStatus = SalesforceSyncStatus.PENDING
    sync_direction: Optional[str] = None  # 'dropbox_to_salesforce', 'salesforce_to_dropbox', 'bidirectional'
    last_sync_timestamp: Optional[datetime] = None
    sync_errors: List[Dict[str, Any]] = Field(default_factory=list)
    fields_synced: List[str] = Field(default_factory=list)
    fields_failed: List[str] = Field(default_factory=list)
    
    # Relationships (will be populated by database operations)
    dropbox_account: Optional[DropboxAccount] = None
    salesforce_account: Optional[SalesforceAccount] = None
    
    def is_synced(self) -> bool:
        """Check if the sync is successful."""
        return self.sync_status == SalesforceSyncStatus.SYNCED
    
    def has_errors(self) -> bool:
        """Check if there are sync errors."""
        return len(self.sync_errors) > 0
    
    def get_last_error(self) -> Optional[Dict[str, Any]]:
        """Get the most recent sync error."""
        return self.sync_errors[-1] if self.sync_errors else None
    
    def sync_summary(self) -> Dict[str, Any]:
        """Get a summary of the sync status."""
        return {
            "status": self.sync_status,
            "direction": self.sync_direction,
            "last_sync": self.last_sync_timestamp,
            "fields_synced": len(self.fields_synced),
            "fields_failed": len(self.fields_failed),
            "error_count": len(self.sync_errors)
        }

# ============================================================================
# ANALYSIS MODELS
# ============================================================================

class AccountAnalysis(BaseDatabaseModel):
    """Stores analysis results comparing Dropbox and Salesforce data."""
    dropbox_account_id: Optional[int] = None
    salesforce_account_id: Optional[str] = None
    analysis_type: Optional[str] = None  # 'data_comparison', 'mapping_validation', 'sync_recommendations'
    analysis_data: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    
    # Relationships (will be populated by database operations)
    dropbox_account: Optional[DropboxAccount] = None
    salesforce_account: Optional[SalesforceAccount] = None
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get a summary of the analysis."""
        return {
            "analysis_type": self.analysis_type,
            "recommendations_count": len(self.recommendations),
            "missing_fields_count": len(self.missing_fields),
            "has_data": bool(self.analysis_data)
        }

# ============================================================================
# DATABASE MANAGER CLASS
# ============================================================================

class DatabaseManager:
    """Manages database operations and relationships."""
    
    def __init__(self, supabase_client=None):
        self.supabase_client = supabase_client
    
    def get_dropbox_account_with_files(self, folder_name: str) -> Optional[DropboxAccount]:
        """Get a Dropbox account with all its application files."""
        # This would be implemented with actual database queries
        pass
    
    def get_salesforce_accounts_by_name(self, name: str) -> List[SalesforceAccount]:
        """Get Salesforce accounts by name (partial match)."""
        # This would be implemented with actual database queries
        pass
    
    def create_mapping(self, dropbox_account: DropboxAccount, 
                      salesforce_account: SalesforceAccount, 
                      mapping_type: str, 
                      confidence: float) -> DropboxSalesforceMapping:
        """Create a mapping between Dropbox and Salesforce accounts."""
        # This would be implemented with actual database operations
        pass
    
    def get_sync_status(self, dropbox_account_id: int, 
                       salesforce_account_id: str) -> Optional[SyncStatus]:
        """Get sync status for a specific mapping."""
        # This would be implemented with actual database queries
        pass

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_dropbox_account_from_dict(data: Dict[str, Any]) -> DropboxAccount:
    """Create a DropboxAccount instance from a dictionary."""
    return DropboxAccount(**data)

def create_salesforce_account_from_dict(data: Dict[str, Any]) -> SalesforceAccount:
    """Create a SalesforceAccount instance from a dictionary."""
    return SalesforceAccount(**data)

def compare_accounts(dropbox_account: DropboxAccount, 
                    salesforce_account: SalesforceAccount) -> Dict[str, Any]:
    """Compare two accounts and return differences."""
    comparison = {
        "name_match": dropbox_account.full_name() == salesforce_account.full_name(),
        "email_match": dropbox_account.best_info.email == salesforce_account.email if dropbox_account.best_info else False,
        "phone_match": dropbox_account.best_info.phone == salesforce_account.phone if dropbox_account.best_info else False,
        "address_match": dropbox_account.best_info.address_string() == salesforce_account.address_string() if dropbox_account.best_info else False,
        "missing_in_salesforce": [],
        "missing_in_dropbox": [],
        "different_values": {}
    }
    
    # Check for missing fields
    if dropbox_account.best_info:
        if dropbox_account.best_info.email and not salesforce_account.email:
            comparison["missing_in_salesforce"].append("email")
        if dropbox_account.best_info.phone and not salesforce_account.phone:
            comparison["missing_in_salesforce"].append("phone")
    
    if salesforce_account.email and not (dropbox_account.best_info and dropbox_account.best_info.email):
        comparison["missing_in_dropbox"].append("email")
    if salesforce_account.phone and not (dropbox_account.best_info and dropbox_account.best_info.phone):
        comparison["missing_in_dropbox"].append("phone")
    
    return comparison

# ============================================================================
# RELATIONSHIP RESOLUTION
# ============================================================================

# Update forward references
DropboxAccountApplicationFile.model_rebuild()
DropboxAccount.model_rebuild()
SalesforceAccount.model_rebuild()
SalesforceHousehold.model_rebuild()
SalesforceHouseholdMember.model_rebuild()
DropboxSalesforceMapping.model_rebuild()
SyncStatus.model_rebuild()
AccountAnalysis.model_rebuild() 