from typing import List, Optional
from datetime import date
from pydantic import BaseModel

# This file defines the schema models for supabase_client package

class Application(BaseModel):
    file_name: str
    first_name: str
    last_name: str
    birthdate: date
    gender: str
    address: str

class HouseholdMember(BaseModel):
    role: str  # "Head" or "Member"
    account_name: str
    stage: str
    email: str
    phone: str
    writing_advisor: str
    prospecting_status: str
    account_record_type: str
    mailing_address: str
    ssn_tax_id: str

class DropboxAccount(BaseModel):
    folder: str
    first_name: str
    middle_name: Optional[str]
    last_name: str
    applications: List[Application]
    household_head: Optional[HouseholdMember]
    household_members: List[HouseholdMember]

def create_schema() -> str:
    """
    Create the database schema
    Returns: SQL for creating the schema
    """
    return """
    -- Create enum for household roles
    CREATE TYPE household_role AS ENUM ('Head', 'Member');

    -- Create applications table
    CREATE TABLE IF NOT EXISTS applications (
        id SERIAL PRIMARY KEY,
        file_name VARCHAR(255) NOT NULL,
        first_name VARCHAR(100) NOT NULL,
        last_name VARCHAR(100) NOT NULL,
        birthdate DATE NOT NULL,
        gender VARCHAR(50) NOT NULL,
        address TEXT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- Create household_members table
    CREATE TABLE IF NOT EXISTS household_members (
        id SERIAL PRIMARY KEY,
        role household_role NOT NULL,
        account_name VARCHAR(255) NOT NULL,
        stage VARCHAR(100) NOT NULL,
        email VARCHAR(255) NOT NULL,
        phone VARCHAR(50) NOT NULL,
        writing_advisor VARCHAR(255) NOT NULL,
        prospecting_status VARCHAR(100) NOT NULL,
        account_record_type VARCHAR(100) NOT NULL,
        mailing_address TEXT NOT NULL,
        ssn_tax_id VARCHAR(50) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- Create dropbox_accounts table
    CREATE TABLE IF NOT EXISTS dropbox_accounts (
        id SERIAL PRIMARY KEY,
        folder VARCHAR(255) NOT NULL,
        first_name VARCHAR(100) NOT NULL,
        middle_name VARCHAR(100),
        last_name VARCHAR(100) NOT NULL,
        household_head_id INTEGER REFERENCES household_members(id),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- Create junction table for dropbox_accounts and applications
    CREATE TABLE IF NOT EXISTS dropbox_account_applications (
        dropbox_account_id INTEGER REFERENCES dropbox_accounts(id),
        application_id INTEGER REFERENCES applications(id),
        PRIMARY KEY (dropbox_account_id, application_id)
    );

    -- Create junction table for dropbox_accounts and household_members
    CREATE TABLE IF NOT EXISTS dropbox_account_household_members (
        dropbox_account_id INTEGER REFERENCES dropbox_accounts(id),
        household_member_id INTEGER REFERENCES household_members(id),
        PRIMARY KEY (dropbox_account_id, household_member_id)
    );
    """

def check_schema_exists() -> bool:
    """
    Check if the schema exists
    Returns: True if schema exists, False otherwise
    """
    # TODO: Implement schema existence check
    # This would typically query the database to check if the tables exist
    return False 