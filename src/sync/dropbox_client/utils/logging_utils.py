"""Utility functions for logging operations."""

import logging
from typing import Dict, Any, List

# Configure logging
logger = logging.getLogger(__name__)

def _check_app_file_missing_fields(data: Dict[str, Any], prefix: str = "") -> List[str]:
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

def _check_account_info_missing_fields(data: Dict[str, Any], prefix: str = "") -> List[str]:
    """Check which required fields are missing from account information data.
    
    Args:
        data: Dictionary containing the account data to check
        prefix: Optional prefix for field names
        
    Returns:
        List of missing field names
    """
    required_fields = [
        'name', 'first_name', 'last_name', 'email', 'phone',
        'address', 'city', 'state', 'zip', 'birthdate', 'gender'
    ]
    
    def is_valid_value(value):
        """Check if a value is valid (not None, not empty string, not 'null' string)."""
        return value and value != "null"
    
    return [f"{prefix}{field}" for field in required_fields if not is_valid_value(data.get(field))]

def log_dropbox_account_info(account_search_result: Dict[str, Any], logger_instance: Any = None) -> None:
    """Log detailed information about a Dropbox account.
    
    Args:
        account_search_result: Dictionary containing account search result information
        logger_instance: Optional logger instance to use (defaults to module logger)
    """
    log = logger_instance or logger
    
    # Get account data from the search result
    account_data = account_search_result.get('account_data', {})
    search_info = account_search_result.get('search_info', {})
    match_info = search_info.get('match_info', {})
    drivers_license_info = account_search_result.get('drivers_license_info', {})
    
    # Log account basic information
    if account_data:
        log.info("    📄 **Dropbox Account Information**")
        
        # Name information
        if account_data.get('name'):
            log.info(f"    👤 Account Name: {account_data['name']}")
        if account_data.get('first_name'):
            log.info(f"    👤 First Name: {account_data['first_name']}")
        if account_data.get('last_name'):
            log.info(f"    👤 Last Name: {account_data['last_name']}")
        if account_data.get('middle_name'):
            log.info(f"    👤 Middle Name: {account_data['middle_name']}")
        if account_data.get('additional_info'):
            log.info(f"    ℹ️ Additional Info: {account_data['additional_info']}")
        
        # Contact information
        if account_data.get('email'):
            log.info(f"    📧 Email: {account_data['email']}")
        if account_data.get('phone'):
            log.info(f"    📞 Phone: {account_data['phone']}")
        
        # Address information
        if account_data.get('address'):
            log.info(f"    📍 Address: {account_data['address']}")
        if account_data.get('city'):
            log.info(f"    📍 City: {account_data['city']}")
        if account_data.get('state'):
            log.info(f"    📍 State: {account_data['state']}")
        if account_data.get('zip'):
            log.info(f"    📍 ZIP: {account_data['zip']}")
        
        # Personal information
        if account_data.get('birthdate'):
            log.info(f"    🎂 Birthdate: {account_data['birthdate']}")
        if account_data.get('age'):
            log.info(f"    👶 Age: {account_data['age']}")
        if account_data.get('gender'):
            log.info(f"    👤 Gender: {account_data['gender']}")
        
        # Identification information
        if account_data.get('ssn'):
            log.info(f"    🔒 SSN: {account_data['ssn']}")
        if account_data.get('tax_id'):
            log.info(f"    🔒 Tax ID: {account_data['tax_id']}")
        
        # Driver's license information
        if drivers_license_info:
            dl_status = drivers_license_info.get('status', 'not_found')
            if dl_status == 'found':
                log.info("    🪪 Driver's License: Found")
                drivers_license_data = account_search_result.get('drivers_license', {})
                if drivers_license_data:
                    if drivers_license_data.get('license_number'):
                        log.info(f"    🪪 License Number: {drivers_license_data['license_number']}")
                    if drivers_license_data.get('date_of_birth'):
                        log.info(f"    🪪 DOB from DL: {drivers_license_data['date_of_birth']}")
                    if drivers_license_data.get('expiration_date'):
                        log.info(f"    🪪 Expiration Date: {drivers_license_data['expiration_date']}")
                    if drivers_license_data.get('state'):
                        log.info(f"    🪪 State: {drivers_license_data['state']}")
            else:
                log.info("    🔺 Driver's License: Not Found")
        
        # Search and match information
        if match_info:
            match_status = match_info.get('match_status', 'Unknown')
            log.info(f"    🔍 Match Status: {match_status}")
            
            if match_info.get('search_attempts'):
                log.info("    🔍 Search Attempts:")
                for attempt in match_info['search_attempts']:
                    log.info(f"      • {attempt}")
            
            if match_info.get('exact_matches'):
                log.info(f"    ✅ Exact Matches: {len(match_info['exact_matches'])}")
                for match in match_info['exact_matches']:
                    log.info(f"      • {match}")
            
            if match_info.get('partial_matches'):
                log.info(f"    🔶 Partial Matches: {len(match_info['partial_matches'])}")
                for match in match_info['partial_matches']:
                    log.info(f"      • {match}")
        
        # Check for missing information
        missing_fields = _check_account_info_missing_fields(account_data)
        if missing_fields:
            log.warning("    ⚠️ Missing Account Information:")
            for field in missing_fields:
                log.warning(f"      • {field}")
        
        # Add summary line
        account_name = account_data.get('name', '--')
        match_status = match_info.get('match_status', '--') if match_info else '--'
        log.info(f"    📄 **Summary**: Dropbox Name: {account_name}, Dropbox Match: {match_status}")
        
        log.info("")  # Add blank line after account info
    else:
        log.warning("    ❌ No account data found in search result")

def log_dropbox_app_file_info(info: Dict[str, Any], logger_instance: Any = None, report_logger: Any = None) -> None:
    """Log detailed information about a file.
    
    Args:
        info: Dictionary containing file information
        logger_instance: Optional logger instance to use (defaults to module logger)
        report_logger: Optional report logger instance to use for additional logging
    """
    log = logger_instance or logger
    report_log = report_logger  # Use report_logger if provided

    # Owner information
    if info.get('owner'):
        owner_data = info['owner']
        if owner_data.get('firstName') and owner_data.get('lastName'):
            log.info(f"    👤 Owner: {owner_data['firstName']} {owner_data['lastName']}")
            if report_log:
                report_log.info(f"    👤 Owner: {owner_data['firstName']} {owner_data['lastName']}")
        if owner_data.get('dateOfBirth') and owner_data.get('dateOfBirth') != "null":
            log.info(f"    📅 Owner DOB: {owner_data['dateOfBirth']}")
            if report_log:
                report_log.info(f"    📅 Owner DOB: {owner_data['dateOfBirth']}")
        if owner_data.get('gender') and owner_data.get('gender') != "null":
            log.info(f"    👤 Owner Gender: {owner_data['gender']}")
            if report_log:
                report_log.info(f"    👤 Owner Gender: {owner_data['gender']}")
        if owner_data.get('mailingAddressStreet') and owner_data.get('mailingAddressStreet') != "null":
            address = f"{owner_data['mailingAddressStreet']}"
            if owner_data.get('mailingAddressCity') and owner_data.get('mailingAddressCity') != "null":
                address += f", {owner_data['mailingAddressCity']}"
            if owner_data.get('mailingAddressState') and owner_data.get('mailingAddressState') != "null":
                address += f", {owner_data['mailingAddressState']}"
            if owner_data.get('mailingAddressZip') and owner_data.get('mailingAddressZip') != "null":
                address += f" {owner_data['mailingAddressZip']}"
            log.info(f"    📍 Owner Address: {address}")
            if report_log:
                report_log.info(f"    📍 Owner Address: {address}")
        if owner_data.get('phoneNumber') and owner_data.get('phoneNumber') != "null":
            log.info(f"    📞 Owner Phone: {owner_data['phoneNumber']}")
            if report_log:
                report_log.info(f"    📞 Owner Phone: {owner_data['phoneNumber']}")
        if owner_data.get('emailAddress') and owner_data.get('emailAddress') != "null":
            log.info(f"    📧 Owner Email: {owner_data['emailAddress']}")
            if report_log:
                report_log.info(f"    📧 Owner Email: {owner_data['emailAddress']}")

    # Joint owner information
    if info.get('jointOwner'):
        joint_owner_data = info['jointOwner']
        if joint_owner_data.get('firstName') and joint_owner_data.get('lastName'):
            log.info(f"    👥 Joint Owner: {joint_owner_data['firstName']} {joint_owner_data['lastName']}")
            if report_log:
                report_log.info(f"    👥 Joint Owner: {joint_owner_data['firstName']} {joint_owner_data['lastName']}")
        if joint_owner_data.get('dateOfBirth') and joint_owner_data.get('dateOfBirth') != "null":
            log.info(f"    📅 Joint Owner DOB: {joint_owner_data['dateOfBirth']}")
            if report_log:
                report_log.info(f"    📅 Joint Owner DOB: {joint_owner_data['dateOfBirth']}")
        if joint_owner_data.get('gender') and joint_owner_data.get('gender') != "null":
            log.info(f"    👤 Joint Owner Gender: {joint_owner_data['gender']}")
            if report_log:
                report_log.info(f"    👤 Joint Owner Gender: {joint_owner_data['gender']}")
        if joint_owner_data.get('mailingAddressStreet') and joint_owner_data.get('mailingAddressStreet') != "null":
            address = f"{joint_owner_data['mailingAddressStreet']}"
            if joint_owner_data.get('mailingAddressCity') and joint_owner_data.get('mailingAddressCity') != "null":
                address += f", {joint_owner_data['mailingAddressCity']}"
            if joint_owner_data.get('mailingAddressState') and joint_owner_data.get('mailingAddressState') != "null":
                address += f", {joint_owner_data['mailingAddressState']}"
            if joint_owner_data.get('mailingAddressZip') and joint_owner_data.get('mailingAddressZip') != "null":
                address += f" {joint_owner_data['mailingAddressZip']}"
            log.info(f"    📍 Joint Owner Address: {address}")
            if report_log:
                report_log.info(f"    📍 Joint Owner Address: {address}")
        if joint_owner_data.get('phoneNumber') and joint_owner_data.get('phoneNumber') != "null":
            log.info(f"    📞 Joint Owner Phone: {joint_owner_data['phoneNumber']}")
            if report_log:
                report_log.info(f"    📞 Joint Owner Phone: {joint_owner_data['phoneNumber']}")
        if joint_owner_data.get('emailAddress') and joint_owner_data.get('emailAddress') != "null":
            log.info(f"    📧 Joint Owner Email: {joint_owner_data['emailAddress']}")
            if report_log:
                report_log.info(f"    📧 Joint Owner Email: {joint_owner_data['emailAddress']}")
            
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
        if report_log:
            report_log.info(f"    ❌ Unable to extract complete owner information")
    
    if info.get('jointOwner') and not joint_owner_data_info_not_empty:
        log.info(f"    ❌ Unable to extract complete joint owner information")
        if report_log:
            report_log.info(f"    ❌ Unable to extract complete joint owner information")
    
    # Check for missing information
    missing_info = []
    
    if info.get('owner'):
        missing_owner_fields = _check_app_file_missing_fields(info['owner'])
        if missing_owner_fields:
            missing_info.append(f"Owner missing: {', '.join(missing_owner_fields)}")
    
    if info.get('jointOwner'):
        missing_joint_owner_fields = _check_app_file_missing_fields(info['jointOwner'])
        if missing_joint_owner_fields:
            missing_info.append(f"Joint owner missing: {', '.join(missing_joint_owner_fields)}")
    
    if missing_info:
        log.warning("    ⚠️ Incomplete information detected:")
        if report_log:
            report_log.warning("    ⚠️ Incomplete information detected:")
        for msg in missing_info:
            log.warning(f"    {msg}")
            if report_log:
                report_log.warning(f"    {msg}")
    
    # Log notes if present
    if info.get('notes') and isinstance(info['notes'], list):
        log.info("    📝 Notes:")
        if report_log:
            report_log.info("    📝 Notes:")
        for note in info['notes']:
            log.info(f"      • {note}")
            if report_log:
                report_log.info(f"      • {note}")
    
    log.info("")  # Add blank line between files
    if report_log:
        report_log.info("")  # Add blank line between files 