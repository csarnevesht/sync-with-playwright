from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime, date

class Application(BaseModel):
    """Model for an application."""
    file_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birthdate: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    application_type: str = "Insurance"
    status: str = "Pending"
    dropbox_account_id: Optional[int] = None
    
    model_config = {
        'json_encoders': {
            date: lambda v: v.isoformat() if v else None
        }
    }

class DataSource(str, Enum):
    """Enumeration of data sources."""
    SALESFORCE = "salesforce"
    DROPBOX_CLIENT_LIST = "dropbox_client_list"
    DROPBOX_APPLICATION_FILES = "dropbox_application_files"
    DROPBOX_MERGED = "dropbox_merged"

class FieldStatus(str, Enum):
    """Enumeration of field statuses."""
    PRESENT = "present"
    MISSING = "missing"
    DIFFERENT = "different"
    PARTIAL = "partial"

class MigrationPriority(str, Enum):
    """Enumeration of migration priorities."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NOT_NEEDED = "not_needed"

class AccountType(str, Enum):
    """Enumeration of account types."""
    CONTACT = "Contact"
    HOUSEHOLD = "Household"
    PRIMARY = "Primary"
    JOINT = "Joint"
    HOUSEHOLD_HEAD = "Household Head"
    MEMBER = "Member"

class AccountRole(str, Enum):
    """Enumeration of account roles."""
    HOUSEHOLD_HEAD = "Household Head"
    MEMBER = "Member"
    NONE = "None"

class FieldComparison(BaseModel):
    """Model for comparing a single field between sources."""
    field_name: str
    salesforce_value: Optional[str] = None
    dropbox_value: Optional[str] = None
    status: FieldStatus
    migration_priority: MigrationPriority
    notes: Optional[str] = None

class AccountComparison(BaseModel):
    """Model for comparing a single account between Salesforce and Dropbox."""
    account_name: str
    account_type: AccountType
    role: Optional[AccountRole] = None
    source: DataSource
    
    # Field comparisons
    first_name: FieldComparison
    last_name: FieldComparison
    middle_name: FieldComparison
    email: FieldComparison
    phone: FieldComparison
    address: FieldComparison
    birthdate: FieldComparison
    gender: FieldComparison
    ssn_tax_id: FieldComparison
    
    # Additional fields
    stage: Optional[str] = None  # Salesforce specific
    drivers_license: Optional[Dict[str, Any]] = None  # Dropbox specific
    
    # Migration information
    migration_needed: bool = False
    migration_priority: MigrationPriority = MigrationPriority.LOW
    migration_notes: Optional[str] = None

class HouseholdComparison(BaseModel):
    """Model for comparing household structures between Salesforce and Dropbox."""
    household_name: str
    salesforce_household: Optional[Dict[str, Any]] = None
    dropbox_household: Optional[Dict[str, Any]] = None
    
    # Member comparisons
    head_comparison: Optional[AccountComparison] = None
    member_comparisons: List[AccountComparison] = []
    
    # Household-level analysis
    structure_match: bool = False
    missing_members: List[str] = []
    extra_members: List[str] = []
    migration_needed: bool = False
    migration_priority: MigrationPriority = MigrationPriority.LOW

class DataQualityAnalysis(BaseModel):
    """Model for analyzing data quality across sources."""
    total_fields_compared: int
    fields_present_in_salesforce: int
    fields_present_in_dropbox: int
    fields_missing_in_salesforce: int
    fields_missing_in_dropbox: int
    fields_different: int
    data_completeness_score: float  # 0.0 to 1.0
    data_consistency_score: float   # 0.0 to 1.0

class MigrationPlan(BaseModel):
    """Model for planning data migration from Dropbox to Salesforce."""
    account_name: str
    migration_type: str  # "create", "update", "merge"
    priority: MigrationPriority
    estimated_effort: str  # "low", "medium", "high"
    
    # Fields to migrate
    fields_to_create: List[str] = []
    fields_to_update: List[str] = []
    fields_to_merge: List[str] = []
    
    # Dependencies
    dependencies: List[str] = []
    
    # Validation rules
    validation_rules: List[str] = []
    
    # Notes
    notes: Optional[str] = None

class AccountAnalysisReport(BaseModel):
    """Comprehensive model for account analysis and migration planning."""
    dropbox_account_folder: str
    analysis_timestamp: datetime = Field(default_factory=datetime.now)
    
    # Source data
    salesforce_account_information: Optional[Dict[str, Any]] = None
    dropbox_account_information: Optional[Dict[str, Any]] = None
    
    # Enhanced analysis fields
    dropbox_folder_analysis: Optional[Dict[str, Any]] = None
    expected_salesforce_mapping: Optional[Dict[str, Any]] = None
    field_mapping_analysis: Optional[Dict[str, Any]] = None
    
    # Comparisons
    account_comparisons: List[AccountComparison] = []
    household_comparison: Optional[HouseholdComparison] = None
    
    # Analysis results
    data_quality: Optional[DataQualityAnalysis] = None
    migration_plans: List[MigrationPlan] = []
    
    # Summary statistics
    total_accounts_found: int = 0
    total_accounts_matched: int = 0
    total_accounts_missing_in_salesforce: int = 0
    total_accounts_missing_in_dropbox: int = 0
    total_migrations_needed: int = 0
    
    # Recommendations
    recommendations: List[str] = []
    warnings: List[str] = []
    errors: List[str] = []

class BatchAnalysisReport(BaseModel):
    """Model for batch analysis of multiple accounts."""
    batch_id: str
    analysis_timestamp: datetime = Field(default_factory=datetime.now)
    total_accounts_processed: int = 0
    successful_analyses: int = 0
    failed_analyses: int = 0
    
    # Individual reports
    account_reports: List[AccountAnalysisReport] = []
    
    # Batch-level statistics
    total_migrations_needed: int = 0
    high_priority_migrations: int = 0
    medium_priority_migrations: int = 0
    low_priority_migrations: int = 0
    
    # Batch-level recommendations
    batch_recommendations: List[str] = []
    batch_warnings: List[str] = []
    batch_errors: List[str] = [] 