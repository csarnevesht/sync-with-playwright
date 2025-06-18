"""Utility functions for logging operations."""

import logging
from typing import Dict, Any, List

# Configure logging
logger = logging.getLogger(__name__)

def _check_missing_fields(data: Dict[str, Any], prefix: str = "") -> List[str]:
    """Check which required fields are missing from the data.
    
    Args:
        data: Dictionary containing the data to check
        prefix: Optional prefix for field names
        
    Returns:
        List of missing field names
    """
    required_fields = [
        'firstName', 'lastName', 'dateOfBirth', 'gender',
        'mailingAddressStreet', 'mailingAddressCity',
        'mailingAddressState', 'mailingAddressZip',
        'phoneNumber', 'emailAddress'
    ]
    
    def is_valid_value(value):
        """Check if a value is valid (not None, not empty string, not 'null' string)."""
        return value and value != "null"
    
    return [f"{prefix}{field}" for field in required_fields if not is_valid_value(data.get(field))]

def log_dropbox_app_file_info(info: Dict[str, Any], logger_instance: Any = None) -> None:
    """Log detailed information about a file.
    
    Args:
        info: Dictionary containing file information
        logger_instance: Optional logger instance to use (defaults to module logger)
    """
    log = logger_instance or logger

    # Owner information
    if info.get('owner'):
        owner_data = info['owner']
        if owner_data.get('firstName') and owner_data.get('lastName'):
            log.info(f"    👤 Owner: {owner_data['firstName']} {owner_data['lastName']}")
        if owner_data.get('dateOfBirth') and owner_data.get('dateOfBirth') != "null":
            log.info(f"    📅 Owner DOB: {owner_data['dateOfBirth']}")
        if owner_data.get('gender') and owner_data.get('gender') != "null":
            log.info(f"    👤 Owner Gender: {owner_data['gender']}")
        if owner_data.get('mailingAddressStreet') and owner_data.get('mailingAddressStreet') != "null":
            address = f"{owner_data['mailingAddressStreet']}"
            if owner_data.get('mailingAddressCity') and owner_data.get('mailingAddressCity') != "null":
                address += f", {owner_data['mailingAddressCity']}"
            if owner_data.get('mailingAddressState') and owner_data.get('mailingAddressState') != "null":
                address += f", {owner_data['mailingAddressState']}"
            if owner_data.get('mailingAddressZip') and owner_data.get('mailingAddressZip') != "null":
                address += f" {owner_data['mailingAddressZip']}"
            log.info(f"    📍 Owner Address: {address}")
        if owner_data.get('phoneNumber') and owner_data.get('phoneNumber') != "null":
            log.info(f"    📞 Owner Phone: {owner_data['phoneNumber']}")
        if owner_data.get('emailAddress') and owner_data.get('emailAddress') != "null":
            log.info(f"    📧 Owner Email: {owner_data['emailAddress']}")

    # Joint owner information
    if info.get('jointOwner'):
        joint_owner_data = info['jointOwner']
        if joint_owner_data.get('firstName') and joint_owner_data.get('lastName'):
            log.info(f"    👥 Joint Owner: {joint_owner_data['firstName']} {joint_owner_data['lastName']}")
        if joint_owner_data.get('dateOfBirth') and joint_owner_data.get('dateOfBirth') != "null":
            log.info(f"    📅 Joint Owner DOB: {joint_owner_data['dateOfBirth']}")
        if joint_owner_data.get('gender') and joint_owner_data.get('gender') != "null":
            log.info(f"    👤 Joint Owner Gender: {joint_owner_data['gender']}")
        if joint_owner_data.get('mailingAddressStreet') and joint_owner_data.get('mailingAddressStreet') != "null":
            address = f"{joint_owner_data['mailingAddressStreet']}"
            if joint_owner_data.get('mailingAddressCity') and joint_owner_data.get('mailingAddressCity') != "null":
                address += f", {joint_owner_data['mailingAddressCity']}"
            if joint_owner_data.get('mailingAddressState') and joint_owner_data.get('mailingAddressState') != "null":
                address += f", {joint_owner_data['mailingAddressState']}"
            if joint_owner_data.get('mailingAddressZip') and joint_owner_data.get('mailingAddressZip') != "null":
                address += f" {joint_owner_data['mailingAddressZip']}"
            log.info(f"    📍 Joint Owner Address: {address}")
        if joint_owner_data.get('phoneNumber') and joint_owner_data.get('phoneNumber') != "null":
            log.info(f"    📞 Joint Owner Phone: {joint_owner_data['phoneNumber']}")
        if joint_owner_data.get('emailAddress') and joint_owner_data.get('emailAddress') != "null":
            log.info(f"    📧 Joint Owner Email: {joint_owner_data['emailAddress']}")
            
    # Check for complete information
    owner_data = info.get('owner', {})
    joint_owner_data = info.get('jointOwner', {})
    
    def is_valid_value(value):
        """Check if a value is valid (not None, not empty string, not 'null' string)."""
        return value and value != "null"
    
    data_info_not_empty = (
        is_valid_value(owner_data.get('firstName')) and 
        is_valid_value(owner_data.get('lastName')) and 
        is_valid_value(owner_data.get('dateOfBirth')) and 
        is_valid_value(owner_data.get('gender')) and 
        is_valid_value(owner_data.get('mailingAddressStreet')) and 
        is_valid_value(owner_data.get('mailingAddressCity')) and 
        is_valid_value(owner_data.get('mailingAddressState')) and 
        is_valid_value(owner_data.get('mailingAddressZip')) and 
        is_valid_value(owner_data.get('phoneNumber')) and 
        is_valid_value(owner_data.get('emailAddress'))
    )
    
    joint_owner_data_info_not_empty = (
        is_valid_value(joint_owner_data.get('firstName')) and 
        is_valid_value(joint_owner_data.get('lastName')) and 
        is_valid_value(joint_owner_data.get('dateOfBirth')) and 
        is_valid_value(joint_owner_data.get('gender')) and 
        is_valid_value(joint_owner_data.get('mailingAddressStreet')) and 
        is_valid_value(joint_owner_data.get('mailingAddressCity')) and 
        is_valid_value(joint_owner_data.get('mailingAddressState')) and 
        is_valid_value(joint_owner_data.get('mailingAddressZip')) and 
        is_valid_value(joint_owner_data.get('phoneNumber')) and 
        is_valid_value(joint_owner_data.get('emailAddress'))
    )
    
    if not data_info_not_empty:
        log.info(f"    ❌ Unable to extract complete owner information")
    
    if info.get('jointOwner') and not joint_owner_data_info_not_empty:
        log.info(f"    ❌ Unable to extract complete joint owner information")
    
    # Check for missing information
    missing_info = []
    
    if info.get('owner'):
        missing_owner_fields = _check_missing_fields(info['owner'])
        if missing_owner_fields:
            missing_info.append(f"Owner missing: {', '.join(missing_owner_fields)}")
    
    if info.get('jointOwner'):
        missing_joint_owner_fields = _check_missing_fields(info['jointOwner'])
        if missing_joint_owner_fields:
            missing_info.append(f"Joint owner missing: {', '.join(missing_joint_owner_fields)}")
    
    if missing_info:
        log.warning("    ⚠️ Incomplete information detected:")
        for msg in missing_info:
            log.warning(f"    {msg}")
    
    log.info("")  # Add blank line between files 