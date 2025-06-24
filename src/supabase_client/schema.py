from typing import List, Optional, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, Field
from enum import Enum

# This file defines the schema models for supabase_client package

class ApplicationStatus(str, Enum):
    PROCESSED = "Processed"
    FAILED = "Failed"
    ERROR = "Error"
    SKIPPED = "Skipped"

class ApplicationType(str, Enum):
    LIFE_INSURANCE = "Life Insurance"
    ANNUITY = "Annuity"
    EQUITRUST_ANNUITY = "EquiTrust Annuity"
    SECURITY_BENEFIT = "Security Benefit"
    UNKNOWN = "Unknown"

class DropboxAccountApplicationInfo(BaseModel):
    """Model for person information (owner or joint owner)"""
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
    ocr_method: Optional[str] = None  # For OCR-extracted data

class DropboxAccountClientListInfo(BaseModel):
    """Model for client list file information"""
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
    
    model_config = {
        'json_encoders': {
            date: lambda v: v.isoformat() if v else None,
            datetime: lambda v: v.isoformat() if v else None
        }
    }

class DropboxAccountApplicationFile(BaseModel):
    """Model for application file data extracted by LM Studio processor"""
    file_name: str
    file_path: Optional[str] = None
    application_type: ApplicationType = ApplicationType.UNKNOWN
    status: ApplicationStatus = ApplicationStatus.PROCESSED
    owner: DropboxAccountApplicationInfo = Field(default_factory=DropboxAccountApplicationInfo)
    joint_owner: DropboxAccountApplicationInfo = Field(default_factory=DropboxAccountApplicationInfo)
    notes: List[str] = Field(default_factory=list)
    extracted_text: Optional[str] = None  # Raw extracted text
    processing_timestamp: Optional[datetime] = None
    ocr_confidence: Optional[float] = None
    lm_studio_model_used: Optional[str] = None
    processing_duration_seconds: Optional[float] = None
    
    model_config = {
        'json_encoders': {
            date: lambda v: v.isoformat() if v else None,
            datetime: lambda v: v.isoformat() if v else None
        }
    }

class DropboxAccountWithFiles(BaseModel):
    """Enhanced model for Dropbox accounts with application files"""
    folder: str
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    application_files: List[DropboxAccountApplicationFile] = Field(default_factory=list)
    client_list_info: Optional[DropboxAccountClientListInfo] = None
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    processing_timestamp: Optional[datetime] = None
    
    model_config = {
        'json_encoders': {
            date: lambda v: v.isoformat() if v else None,
            datetime: lambda v: v.isoformat() if v else None
        }
    }

def create_schema() -> str:
    """
    Create the database schema
    Returns: SQL for creating the schema
    """
    return """
    -- Create enums
    CREATE TYPE application_status AS ENUM ('Processed', 'Failed', 'Error', 'Skipped');
    CREATE TYPE application_type AS ENUM ('Life Insurance', 'Annuity', 'EquiTrust Annuity', 'Security Benefit', 'Unknown');

    -- Create dropbox_account_application_info table for owner and joint owner data
    CREATE TABLE IF NOT EXISTS dropbox_account_application_info (
        id SERIAL PRIMARY KEY,
        first_name VARCHAR(100),
        last_name VARCHAR(100),
        date_of_birth DATE,
        gender VARCHAR(50),
        mailing_address_street TEXT,
        mailing_address_city VARCHAR(100),
        mailing_address_state VARCHAR(50),
        mailing_address_zip VARCHAR(20),
        phone_number VARCHAR(50),
        email_address VARCHAR(255),
        ocr_method VARCHAR(50),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- Create dropbox_account_application_files table for comprehensive file data
    CREATE TABLE IF NOT EXISTS dropbox_account_application_files (
        id SERIAL PRIMARY KEY,
        file_name VARCHAR(255) NOT NULL,
        file_path TEXT,
        application_type application_type DEFAULT 'Unknown',
        status application_status DEFAULT 'Processed',
        owner_id INTEGER REFERENCES dropbox_account_application_info(id),
        joint_owner_id INTEGER REFERENCES dropbox_account_application_info(id),
        notes JSONB DEFAULT '[]',
        extracted_text TEXT,
        processing_timestamp TIMESTAMP WITH TIME ZONE,
        ocr_confidence DECIMAL(5,2),
        lm_studio_model_used VARCHAR(100),
        processing_duration_seconds DECIMAL(10,3),
        dropbox_account_id INTEGER,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- Create dropbox_accounts table
    CREATE TABLE IF NOT EXISTS dropbox_accounts (
        id SERIAL PRIMARY KEY,
        folder VARCHAR(255) NOT NULL UNIQUE,
        first_name VARCHAR(100),
        middle_name VARCHAR(100),
        last_name VARCHAR(100),
        total_files INTEGER DEFAULT 0,
        processed_files INTEGER DEFAULT 0,
        failed_files INTEGER DEFAULT 0,
        processing_timestamp TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- Add foreign key constraint for dropbox_account_application_files
    ALTER TABLE dropbox_account_application_files 
    ADD CONSTRAINT fk_dropbox_account_application_files_dropbox_account 
    FOREIGN KEY (dropbox_account_id) REFERENCES dropbox_accounts(id);

    -- Create indexes for better performance
    CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_files_file_name ON dropbox_account_application_files(file_name);
    CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_files_dropbox_account_id ON dropbox_account_application_files(dropbox_account_id);
    CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_files_status ON dropbox_account_application_files(status);
    CREATE INDEX IF NOT EXISTS idx_dropbox_accounts_folder ON dropbox_accounts(folder);
    CREATE INDEX IF NOT EXISTS idx_dropbox_account_application_info_names ON dropbox_account_application_info(first_name, last_name);
    """

def check_schema_exists() -> bool:
    """
    Check if the schema exists
    Returns: True if schema exists, False otherwise
    """
    # TODO: Implement schema existence check
    # This would typically query the database to check if the tables exist
    return False 