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

def log_dropbox_account_info(account_search_result: Dict[str, Any], logger_instance: Any = None, args: Any = None, report_logger: Any = None) -> None:
    """Log detailed information about a Dropbox account.
    
    Args:
        account_search_result: Dictionary containing account search result information
        logger_instance: Optional logger instance to use (defaults to module logger)
        args: Optional argparse.Namespace to check for --dl flag
        report_logger: Optional report logger instance to use for additional logging
    """
    log = logger_instance or logger
    report_log = report_logger  # Use report_logger if provided
    
    # Log method name at the beginning
    log.info("[log_dropbox_account_info]")
    if report_log:
        report_log.info("[log_dropbox_account_info]")
    
    # Get account data from the search result
    account_data = account_search_result.get('account_data', {})
    search_info = account_search_result.get('search_info', {})
    match_info = search_info.get('match_info', {})
    drivers_license_info = account_search_result.get('drivers_license_info', {})
    
    summary = f"📁 **Dropbox Folder** Name: {account_search_result.get('folder_name', 'Unknown')}"
    log.info(summary)
    if report_log:
        report_log.info(summary)

    # Log account basic information
    if account_data:
        log.info("    📄 **Dropbox Account Information from client list search **")
        if report_log:
            report_log.info("    📄 **Dropbox Account Information from client list search **")
        
        # Name information
        if account_data.get('name'):
            log.info(f"    👤 Account Name: {account_data['name']}")
            if report_log:
                report_log.info(f"    👤 Account Name: {account_data['name']}")
        if account_data.get('first_name'):
            log.info(f"    👤 First Name: {account_data['first_name']}")
            if report_log:
                report_log.info(f"    👤 First Name: {account_data['first_name']}")
        if account_data.get('last_name'):
            log.info(f"    👤 Last Name: {account_data['last_name']}")
            if report_log:
                report_log.info(f"    👤 Last Name: {account_data['last_name']}")
        if account_data.get('middle_name'):
            log.info(f"    👤 Middle Name: {account_data['middle_name']}")
            if report_log:
                report_log.info(f"    👤 Middle Name: {account_data['middle_name']}")
        if account_data.get('additional_info'):
            log.info(f"    ℹ️ Additional Info: {account_data['additional_info']}")
            if report_log:
                report_log.info(f"    ℹ️ Additional Info: {account_data['additional_info']}")
        
        # Contact information
        if account_data.get('email'):
            log.info(f"    📧 Email: {account_data['email']}")
            if report_log:
                report_log.info(f"    📧 Email: {account_data['email']}")
        if account_data.get('phone'):
            log.info(f"    📞 Phone: {account_data['phone']}")
            if report_log:
                report_log.info(f"    📞 Phone: {account_data['phone']}")
        
        # Address information
        if account_data.get('address'):
            log.info(f"    📍 Address: {account_data['address']}")
            if report_log:
                report_log.info(f"    📍 Address: {account_data['address']}")
        if account_data.get('city'):
            log.info(f"    📍 City: {account_data['city']}")
            if report_log:
                report_log.info(f"    📍 City: {account_data['city']}")
        if account_data.get('state'):
            log.info(f"    📍 State: {account_data['state']}")
            if report_log:
                report_log.info(f"    📍 State: {account_data['state']}")
        if account_data.get('zip'):
            log.info(f"    📍 ZIP: {account_data['zip']}")
            if report_log:
                report_log.info(f"    📍 ZIP: {account_data['zip']}")
        
        # Personal information
        if account_data.get('birthdate'):
            log.info(f"    🎂 Birthdate: {account_data['birthdate']}")
            if report_log:
                report_log.info(f"    🎂 Birthdate: {account_data['birthdate']}")
        if account_data.get('age'):
            log.info(f"    👶 Age: {account_data['age']}")
            if report_log:
                report_log.info(f"    👶 Age: {account_data['age']}")
        if account_data.get('gender'):
            log.info(f"    👤 Gender: {account_data['gender']}")
            if report_log:
                report_log.info(f"    👤 Gender: {account_data['gender']}")
        
        # Identification information
        if account_data.get('ssn'):
            log.info(f"    🔒 SSN: {account_data['ssn']}")
            if report_log:
                report_log.info(f"    🔒 SSN: {account_data['ssn']}")
        if account_data.get('tax_id'):
            log.info(f"    🔒 Tax ID: {account_data['tax_id']}")
            if report_log:
                report_log.info(f"    🔒 Tax ID: {account_data['tax_id']}")
        
        # Driver's license information - only log if --dl flag is set
        if args and hasattr(args, 'dl') and args.dl and drivers_license_info:
            dl_status = drivers_license_info.get('status', 'not_found')
            if dl_status == 'found':
                log.info("    🪪 Driver's License: Found")
                if report_log:
                    report_log.info("    🪪 Driver's License: Found")
                drivers_license_data = account_search_result.get('drivers_license', {})
                if drivers_license_data:
                    if drivers_license_data.get('license_number'):
                        log.info(f"    🪪 License Number: {drivers_license_data['license_number']}")
                        if report_log:
                            report_log.info(f"    🪪 License Number: {drivers_license_data['license_number']}")
                    if drivers_license_data.get('date_of_birth'):
                        log.info(f"    🪪 DOB from DL: {drivers_license_data['date_of_birth']}")
                        if report_log:
                            report_log.info(f"    🪪 DOB from DL: {drivers_license_data['date_of_birth']}")
                    if drivers_license_data.get('expiration_date'):
                        log.info(f"    🪪 Expiration Date: {drivers_license_data['expiration_date']}")
                        if report_log:
                            report_log.info(f"    🪪 Expiration Date: {drivers_license_data['expiration_date']}")
                    if drivers_license_data.get('state'):
                        log.info(f"    🪪 State: {drivers_license_data['state']}")
                        if report_log:
                            report_log.info(f"    🪪 State: {drivers_license_data['state']}")
            else:
                if drivers_license_info.get('status') == 'not_found':
                    log.info("    🔺 Driver's License: Not Found")
                    if report_log:
                        report_log.info("    🔺 Driver's License: Not Found")
        
        # Search and match information
        if match_info:
            match_status = match_info.get('match_status', 'Unknown')
            log.info(f"    🔍 Match Status: {match_status}")
            if report_log:
                report_log.info(f"    🔍 Match Status: {match_status}")
            
            if match_info.get('search_attempts'):
                log.info("    🔍 Search Attempts:")
                if report_log:
                    report_log.info("    🔍 Search Attempts:")
                for attempt in match_info['search_attempts']:
                    log.info(f"      • {attempt}")
                    if report_log:
                        report_log.info(f"      • {attempt}")
            
            if match_info.get('exact_matches'):
                log.info(f"    ✅ Exact Matches: {len(match_info['exact_matches'])}")
                if report_log:
                    report_log.info(f"    ✅ Exact Matches: {len(match_info['exact_matches'])}")
                for match in match_info['exact_matches']:
                    log.info(f"      • {match}")
                    if report_log:
                        report_log.info(f"      • {match}")
            
            if match_info.get('partial_matches'):
                log.info(f"    🔶 Partial Matches: {len(match_info['partial_matches'])}")
                if report_log:
                    report_log.info(f"    🔶 Partial Matches: {len(match_info['partial_matches'])}")
                for match in match_info['partial_matches']:
                    log.info(f"      • {match}")
                    if report_log:
                        report_log.info(f"      • {match}")
        
        # Check for missing information
        missing_fields = _check_account_info_missing_fields(account_data)
        if missing_fields:
            log.warning("    ⚠️ Missing Account Information:")
            if report_log:
                report_log.warning("    ⚠️ Missing Account Information:")
            for field in missing_fields:
                log.warning(f"      • {field}")
                if report_log:
                    report_log.warning(f"      • {field}")
        
        # Add summary line
        account_name = account_data.get('name', '--')
        match_status = match_info.get('match_status', '--') if match_info else '--'
        log.info(f"    📄 **Summary**: Dropbox Name: {account_name}, Dropbox Match: {match_status}")
        if report_log:
            report_log.info(f"    📄 **Summary**: Dropbox Name: {account_name}, Dropbox Match: {match_status}")
        
        log.info("")  # Add blank line after account info
        if report_log:
            report_log.info("")  # Add blank line after account info
    else:
        log.warning("    ❌ No account data found in search result")
        if report_log:
            report_log.warning("    ❌ No account data found in search result")

def log_dropbox_app_file_info(info: Dict[str, Any], logger_instance: Any = None, report_logger: Any = None, file_name: str = None, folder_name: str = None) -> None:
    """Log detailed information about a file.
    
    Args:
        info: Dictionary containing file information
        logger_instance: Optional logger instance to use (defaults to module logger)
        report_logger: Optional report logger instance to use for additional logging
        file_name: Optional file name to display at the beginning
        folder_name: Optional folder name to display along with file name
    """
    log = logger_instance or logger
    report_log = report_logger  # Use report_logger if provided

    # Log method name at the beginning
    log.info("[log_dropbox_app_file_info]")
    if report_log:
        report_log.info("[log_dropbox_app_file_info]")

    # Log file name and folder name if provided
    if file_name:
        if folder_name:
            log.info(f"📁 **{folder_name}** / 📄 **{file_name}**:")
            if report_log:
                report_log.info(f"📁 **{folder_name}** / 📄 **{file_name}**:")
        else:
            log.info(f"📄 **{file_name}**:")
            if report_log:
                report_log.info(f"📄 **{file_name}**:")

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

def log_best_dropbox_account_app_info(info: Dict[str, Any], logger_instance: Any = None, report_logger: Any = None, title: str = "BEST ACCOUNT INFO FROM APP FILES") -> None:
    """Log the best available account information from app files.
    
    Args:
        info: Dictionary containing the best available account information
        logger_instance: Optional logger instance to use (defaults to module logger)
        report_logger: Optional report logger instance to use for additional logging
        title: Optional title for the log section
    """
    log = logger_instance or logger
    report_log = report_logger  # Use report_logger if provided

    # Log method name at the beginning
    log.info("[log_best_dropbox_account_app_info]")
    if report_log:
        report_log.info("[log_best_dropbox_account_app_info]")

    # Log title
    log.info(f"\n=== {title} ===")
    if report_log:
        report_log.info(f"\n=== {title} ===")

    if not info:
        log.info("❌ No account information available")
        if report_log:
            report_log.info("❌ No account information available")
        return

    # Application type and status
    if info.get('application_type'):
        log.info(f"📋 Application Type: {info['application_type']}")
        if report_log:
            report_log.info(f"📋 Application Type: {info['application_type']}")
    
    if info.get('status'):
        log.info(f"📊 Status: {info['status']}")
        if report_log:
            report_log.info(f"📊 Status: {info['status']}")

    # Owner information
    if info.get('owner'):
        owner_data = info['owner']
        log.info("\n👤 **OWNER INFORMATION:**")
        if report_log:
            report_log.info("\n👤 **OWNER INFORMATION:**")
        
        if owner_data.get('firstName') and owner_data.get('lastName'):
            log.info(f"    Name: {owner_data['firstName']} {owner_data['lastName']}")
            if report_log:
                report_log.info(f"    Name: {owner_data['firstName']} {owner_data['lastName']}")
        
        if owner_data.get('dateOfBirth'):
            log.info(f"    Date of Birth: {owner_data['dateOfBirth']}")
            if report_log:
                report_log.info(f"    Date of Birth: {owner_data['dateOfBirth']}")
        
        if owner_data.get('gender'):
            log.info(f"    Gender: {owner_data['gender']}")
            if report_log:
                report_log.info(f"    Gender: {owner_data['gender']}")
        
        if owner_data.get('mailingAddressStreet'):
            address = f"{owner_data['mailingAddressStreet']}"
            if owner_data.get('mailingAddressCity'):
                address += f", {owner_data['mailingAddressCity']}"
            if owner_data.get('mailingAddressState'):
                address += f", {owner_data['mailingAddressState']}"
            if owner_data.get('mailingAddressZip'):
                address += f" {owner_data['mailingAddressZip']}"
            log.info(f"    Address: {address}")
            if report_log:
                report_log.info(f"    Address: {address}")
        
        if owner_data.get('phoneNumber'):
            log.info(f"    Phone: {owner_data['phoneNumber']}")
            if report_log:
                report_log.info(f"    Phone: {owner_data['phoneNumber']}")
        
        if owner_data.get('emailAddress'):
            log.info(f"    Email: {owner_data['emailAddress']}")
            if report_log:
                report_log.info(f"    Email: {owner_data['emailAddress']}")
        
        if owner_data.get('ocrMethod'):
            log.info(f"    OCR Method: {owner_data['ocrMethod']}")
            if report_log:
                report_log.info(f"    OCR Method: {owner_data['ocrMethod']}")

    # Joint owner information
    if info.get('jointOwner'):
        joint_owner_data = info['jointOwner']
        log.info("\n👥 **JOINT OWNER INFORMATION:**")
        if report_log:
            report_log.info("\n👥 **JOINT OWNER INFORMATION:**")
        
        if joint_owner_data.get('firstName') and joint_owner_data.get('lastName'):
            log.info(f"    Name: {joint_owner_data['firstName']} {joint_owner_data['lastName']}")
            if report_log:
                report_log.info(f"    Name: {joint_owner_data['firstName']} {joint_owner_data['lastName']}")
        
        if joint_owner_data.get('dateOfBirth'):
            log.info(f"    Date of Birth: {joint_owner_data['dateOfBirth']}")
            if report_log:
                report_log.info(f"    Date of Birth: {joint_owner_data['dateOfBirth']}")
        
        if joint_owner_data.get('gender'):
            log.info(f"    Gender: {joint_owner_data['gender']}")
            if report_log:
                report_log.info(f"    Gender: {joint_owner_data['gender']}")
        
        if joint_owner_data.get('mailingAddressStreet'):
            address = f"{joint_owner_data['mailingAddressStreet']}"
            if joint_owner_data.get('mailingAddressCity'):
                address += f", {joint_owner_data['mailingAddressCity']}"
            if joint_owner_data.get('mailingAddressState'):
                address += f", {joint_owner_data['mailingAddressState']}"
            if joint_owner_data.get('mailingAddressZip'):
                address += f" {joint_owner_data['mailingAddressZip']}"
            log.info(f"    Address: {address}")
            if report_log:
                report_log.info(f"    Address: {address}")
        
        if joint_owner_data.get('phoneNumber'):
            log.info(f"    Phone: {joint_owner_data['phoneNumber']}")
            if report_log:
                report_log.info(f"    Phone: {joint_owner_data['phoneNumber']}")
        
        if joint_owner_data.get('emailAddress'):
            log.info(f"    Email: {joint_owner_data['emailAddress']}")
            if report_log:
                report_log.info(f"    Email: {joint_owner_data['emailAddress']}")
        
        if joint_owner_data.get('ocrMethod'):
            log.info(f"    OCR Method: {joint_owner_data['ocrMethod']}")
            if report_log:
                report_log.info(f"    OCR Method: {joint_owner_data['ocrMethod']}")

    # Notes
    if info.get('notes') and isinstance(info['notes'], list) and info['notes']:
        log.info("\n📝 **NOTES:**")
        if report_log:
            report_log.info("\n📝 **NOTES:**")
        for note in info['notes']:
            log.info(f"    • {note}")
            if report_log:
                report_log.info(f"    • {note}")

    log.info("")  # Add blank line at the end
    if report_log:
        report_log.info("")  # Add blank line at the end

def log_app_files_notes_summary(file_info_dict: Dict[str, Any], logger_instance: Any = None, report_logger: Any = None) -> None:
    """Log a summary of notes for all app files in a prominent way.
    
    Args:
        file_info_dict: Dictionary containing file info with file paths as keys
        logger_instance: Optional logger instance to use (defaults to module logger)
        report_logger: Optional report logger instance to use for additional logging
    """
    log = logger_instance or logger
    report_log = report_logger
    
    if not file_info_dict:
        log.info("📝 No app files processed - no notes to display")
        if report_log:
            report_log.info("📝 No app files processed - no notes to display")
        return
    
    log.info("\n" + "="*60)
    log.info("📝 APP FILES PROCESSING NOTES SUMMARY")
    log.info("="*60)
    if report_log:
        report_log.info("\n" + "="*60)
        report_log.info("📝 APP FILES PROCESSING NOTES SUMMARY")
        report_log.info("="*60)
    
    files_with_notes = 0
    total_notes = 0
    
    for file_path, info in file_info_dict.items():
        if not info:
            continue
            
        # Extract filename from path
        filename = file_path.split('/')[-1] if '/' in file_path else file_path
        
        notes = info.get('notes', [])
        if notes:
            files_with_notes += 1
            total_notes += len(notes)
            
            log.info(f"\n📄 {filename}:")
            if report_log:
                report_log.info(f"\n📄 {filename}:")
            
            for i, note in enumerate(notes, 1):
                log.info(f"   {i}. {note}")
                if report_log:
                    report_log.info(f"   {i}. {note}")
        else:
            log.info(f"\n📄 {filename}: No processing notes")
            if report_log:
                report_log.info(f"\n📄 {filename}: No processing notes")
    
    # Summary
    log.info(f"\n📊 SUMMARY:")
    log.info(f"   • Total files processed: {len(file_info_dict)}")
    log.info(f"   • Files with notes: {files_with_notes}")
    log.info(f"   • Total notes: {total_notes}")
    if report_log:
        report_log.info(f"\n📊 SUMMARY:")
        report_log.info(f"   • Total files processed: {len(file_info_dict)}")
        report_log.info(f"   • Files with notes: {files_with_notes}")
        report_log.info(f"   • Total notes: {total_notes}")
    
    log.info("="*60)
    if report_log:
        report_log.info("="*60) 

def log_app_files_processing_summary(summary_data: Dict[str, Any], logger_instance: Any = None, report_logger: Any = None) -> None:
    """Log a summary of app files processing results.
    
    Args:
        summary_data: Dictionary containing summary data from app file processing
        logger_instance: Optional logger instance to use (defaults to module logger)
        report_logger: Optional report logger instance to use for additional logging
    """
    log = logger_instance or logger
    report_log = report_logger  # Use report_logger if provided

    # Log method name at the beginning
    log.info("[log_app_files_processing_summary]")
    if report_log:
        report_log.info("[log_app_files_processing_summary]")

    if not summary_data or 'file_info' not in summary_data:
        log.info("❌ No file processing summary data available")
        if report_log:
            report_log.info("❌ No file processing summary data available")
        return

    file_info = summary_data['file_info']
    
    if not file_info:
        log.info("❌ No files were processed")
        if report_log:
            report_log.info("❌ No files were processed")
        return

    # Log summary statistics
    total_files = len(file_info)
    files_with_info = sum(1 for info in file_info.values() if info)
    files_without_info = total_files - files_with_info
    
    log.info(f"\n=== APP FILES PROCESSING SUMMARY ===")
    log.info(f"📊 Total files processed: {total_files}")
    log.info(f"✅ Files with extracted info: {files_with_info}")
    log.info(f"❌ Files without info: {files_without_info}")
    
    if report_log:
        report_log.info(f"\n=== APP FILES PROCESSING SUMMARY ===")
        report_log.info(f"📊 Total files processed: {total_files}")
        report_log.info(f"✅ Files with extracted info: {files_with_info}")
        report_log.info(f"❌ Files without info: {files_without_info}")

    # Log detailed information for each file
    log.info(f"\n📋 DETAILED FILE INFORMATION:")
    if report_log:
        report_log.info(f"\n📋 DETAILED FILE INFORMATION:")
    
    for file_path, info in file_info.items():
        file_name = file_path.split('/')[-1] if '/' in file_path else file_path
        
        if info:
            # File has extracted information
            log.info(f"\n📄 **{file_name}** - ✅ Info extracted")
            if report_log:
                report_log.info(f"\n📄 **{file_name}** - ✅ Info extracted")
            
            # Log owner info if present
            if info.get('owner'):
                owner = info['owner']
                if owner.get('firstName') and owner.get('lastName'):
                    log.info(f"    👤 Owner: {owner['firstName']} {owner['lastName']}")
                    if report_log:
                        report_log.info(f"    👤 Owner: {owner['firstName']} {owner['lastName']}")
            
            # Log joint owner info if present
            if info.get('jointOwner'):
                joint_owner = info['jointOwner']
                if joint_owner.get('firstName') and joint_owner.get('lastName'):
                    log.info(f"    👥 Joint Owner: {joint_owner['firstName']} {joint_owner['lastName']}")
                    if report_log:
                        report_log.info(f"    👥 Joint Owner: {joint_owner['firstName']} {joint_owner['lastName']}")
            
            # Log application type and status
            if info.get('application_type'):
                log.info(f"    📋 Type: {info['application_type']}")
                if report_log:
                    report_log.info(f"    📋 Type: {info['application_type']}")
            
            if info.get('status'):
                log.info(f"    📊 Status: {info['status']}")
                if report_log:
                    report_log.info(f"    📊 Status: {info['status']}")
            
            # Log notes if present
            if info.get('notes') and isinstance(info['notes'], list) and info['notes']:
                log.info(f"    📝 Notes: {', '.join(info['notes'])}")
                if report_log:
                    report_log.info(f"    📝 Notes: {', '.join(info['notes'])}")
        else:
            # File has no extracted information
            log.info(f"\n📄 **{file_name}** - ❌ No info extracted")
            if report_log:
                report_log.info(f"\n📄 **{file_name}** - ❌ No info extracted")

    log.info("")  # Add blank line at the end
    if report_log:
        report_log.info("")  # Add blank line at the end 