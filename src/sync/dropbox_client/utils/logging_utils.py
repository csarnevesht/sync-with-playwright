"""Utility functions for logging operations."""

import logging
from typing import Dict, Any, List, Optional

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
    
    # summary = f"📁 **Dropbox Folder** Name: {account_search_result.get('folder_name', 'Unknown')}"
    # log.info(summary)
    # if report_log:
    #     report_log.info(summary)

    account_name = account_search_result.get('folder_name', 'Unknown')
    log.info(f"📊 Dropbox Account Information 'from Client List File'  - [📁Dropbox Account Folder Name: '{account_search_result.get('folder_name', 'Unknown')}']**")
    report_log.info(f"📊 Dropbox Account Information 'from Client List File'  - [📁Dropbox Account Folder Name: '{account_search_result.get('folder_name', 'Unknown')}']**")

    # Log account basic information
    if account_data:
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
            log.info(f"    ♂️♀️ Gender: {account_data['gender']}")
            if report_log:
                report_log.info(f"    ♂️♀️ Gender: {account_data['gender']}")
        
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
        log.warning(f"    ❌ No account information found 'in Client List File - [📁Dropbox Account Folder Name: '{account_name}']'")
        if report_log:
            report_log.warning(f"    ❌ No account information found 'in Client List File - [📁Dropbox Account Folder Name: '{account_name}']'")

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
            log.info(f"👤 Name: {owner_data['firstName']} {owner_data['lastName']}")
            if report_log:
                report_log.info(f"👤 Name: {owner_data['firstName']} {owner_data['lastName']}")
        if owner_data.get('dateOfBirth') and owner_data.get('dateOfBirth') != "null":
            log.info(f"    🎂 Date of Birth: {owner_data['dateOfBirth']}")
            if report_log:
                report_log.info(f"    🎂 Date of Birth: {owner_data['dateOfBirth']}")
        if owner_data.get('gender') and owner_data.get('gender') != "null":
            log.info(f"    ♂️♀️ Gender: {owner_data['gender']}")
            if report_log:
                report_log.info(f"    ♂️♀️ Gender: {owner_data['gender']}")
        if owner_data.get('mailingAddressStreet') and owner_data.get('mailingAddressStreet') != "null":
            address = f"{owner_data['mailingAddressStreet']}"
            if owner_data.get('mailingAddressCity') and owner_data.get('mailingAddressCity') != "null":
                address += f", {owner_data['mailingAddressCity']}"
            if owner_data.get('mailingAddressState') and owner_data.get('mailingAddressState') != "null":
                address += f", {owner_data['mailingAddressState']}"
            if owner_data.get('mailingAddressZip') and owner_data.get('mailingAddressZip') != "null":
                address += f" {owner_data['mailingAddressZip']}"
            log.info(f"    📍 Address: {address}")
            if report_log:
                report_log.info(f"    📍 Address: {address}")
        if owner_data.get('phoneNumber') and owner_data.get('phoneNumber') != "null":
            log.info(f"    📞 Phone: {owner_data['phoneNumber']}")
            if report_log:
                report_log.info(f"    📞 Phone: {owner_data['phoneNumber']}")
        if owner_data.get('emailAddress') and owner_data.get('emailAddress') != "null":
            log.info(f"    📧 Email: {owner_data['emailAddress']}")
            if report_log:
                report_log.info(f"    📧 Email: {owner_data['emailAddress']}")

    # Joint owner information
    if info.get('jointOwner'):
        joint_owner_data = info['jointOwner']
        if joint_owner_data.get('firstName') and joint_owner_data.get('lastName'):
            log.info(f"👤👤 [Joint] Name: {joint_owner_data['firstName']} {joint_owner_data['lastName']}")
            if report_log:
                report_log.info(f"👤👤 [Joint] Name: {joint_owner_data['firstName']} {joint_owner_data['lastName']}")
        if joint_owner_data.get('dateOfBirth') and joint_owner_data.get('dateOfBirth') != "null":
            log.info(f"    🎂 Date of Birth: {joint_owner_data['dateOfBirth']}")
            if report_log:
                report_log.info(f"    🎂 Date of Birth: {joint_owner_data['dateOfBirth']}")
        if joint_owner_data.get('gender') and joint_owner_data.get('gender') != "null":
            log.info(f"    ♂️♀️ Gender: {joint_owner_data['gender']}")
            if report_log:
                report_log.info(f"    ♂️♀️ Gender: {joint_owner_data['gender']}")
        if joint_owner_data.get('mailingAddressStreet') and joint_owner_data.get('mailingAddressStreet') != "null":
            address = f"{joint_owner_data['mailingAddressStreet']}"
            if joint_owner_data.get('mailingAddressCity') and joint_owner_data.get('mailingAddressCity') != "null":
                address += f", {joint_owner_data['mailingAddressCity']}"
            if joint_owner_data.get('mailingAddressState') and joint_owner_data.get('mailingAddressState') != "null":
                address += f", {joint_owner_data['mailingAddressState']}"
            if joint_owner_data.get('mailingAddressZip') and joint_owner_data.get('mailingAddressZip') != "null":
                address += f" {joint_owner_data['mailingAddressZip']}"
            log.info(f"    📍 Address: {address}")
            if report_log:
                report_log.info(f"    📍 Address: {address}")
        if joint_owner_data.get('phoneNumber') and joint_owner_data.get('phoneNumber') != "null":
            log.info(f"    📞 Phone: {joint_owner_data['phoneNumber']}")
            if report_log:
                report_log.info(f"    📞 Phone: {joint_owner_data['phoneNumber']}")
        if joint_owner_data.get('emailAddress') and joint_owner_data.get('emailAddress') != "null":
            log.info(f"    📧 Email: {joint_owner_data['emailAddress']}")
            if report_log:
                report_log.info(f"    📧 Email: {joint_owner_data['emailAddress']}")
            
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
        log.info(f"    ❌ Unable to extract complete account information for Dropbox Account Folder '{folder_name}'")
        if report_log:
            report_log.info(f"    ❌ Unable to extract complete account information for Dropbox Account Folder '{folder_name}'")
    
    if info.get('jointOwner') and not joint_owner_data_info_not_empty:
        log.info(f"    ❌ Unable to extract complete joint owner information")
        if report_log:
            report_log.info(f"    ❌ Unable to extract complete joint owner information")
    
    # Check for missing information
    missing_info = []
    
    if info.get('owner'):
        missing_owner_fields = _check_app_file_missing_fields(info['owner'])
        if missing_owner_fields:
            missing_info.append(f"⚠️ Missing Account Information:")
            for field in missing_owner_fields:
                missing_info.append(f"      • {field}")
    
    if info.get('jointOwner'):
        missing_joint_owner_fields = _check_app_file_missing_fields(info['jointOwner'])
        if missing_joint_owner_fields:
            missing_info.append(f"⚠️ Missing Joint Account Information:")
            for field in missing_joint_owner_fields:
                missing_info.append(f"      • {field}")
    
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

def log_dropbox_account_app_files_info(info: Dict[str, Any], logger_instance: Any = None, report_logger: Any = None, title: str = f"Dropbox Account Information 'from application files'", folder_name: str = None) -> None:
    """Log the best available account information from app files.
    
    Args:
        info: Dictionary containing the best available account information
        logger_instance: Optional logger instance to use (defaults to module logger)
        report_logger: Optional report logger instance to use for additional logging
        title: Optional title for the log section
        folder_name: Optional folder name to display in error messages
    """
    log = logger_instance or logger
    report_log = report_logger  # Use report_logger if provided

    # Log method name at the beginning
    log.info("[log_dropbox_account_app_files_info]")
    if report_log:
        report_log.info("[log_dropbox_account_app_files_info]")

    # Check if account information is available
    has_account_info = False
    if info:
        # Check for owner information
        if info.get('owner'):
            owner_data = info['owner']
            if (owner_data.get('firstName') and owner_data.get('lastName') and 
                owner_data.get('dateOfBirth') and owner_data.get('gender')):
                has_account_info = True
        
        # Check for joint owner information
        if info.get('jointOwner'):
            joint_owner_data = info['jointOwner']
            if (joint_owner_data.get('firstName') and joint_owner_data.get('lastName') and 
                joint_owner_data.get('dateOfBirth') and joint_owner_data.get('gender')):
                has_account_info = True

    # Log title
    log.info(f"📄📄 {title} ")
    if report_log:
        report_log.info(f"📄📄 {title}")

    if not info:
        # If info is None/empty, use the folder_name parameter or extract from title
        if folder_name:
            error_msg = f"❌ No account information found 'in application files' - [📁Dropbox Account Folder: Dropbox Account Folder Name: '{folder_name}']"
        else:
            # Try to extract folder name from title as fallback
            if 'Dropbox Account Folder Name:' in title:
                extracted_folder = title.split("Dropbox Account Folder Name: '")[-1].split("'")[0]
                error_msg = f"❌ No account information found 'in application files' - [📁Dropbox Account Folder: Dropbox Account Folder Name: '{extracted_folder}']"
            else:
                error_msg = f"❌ No account information found 'in application files' - {title}"
        
        log.info(error_msg)
        if report_log:
            report_log.info(error_msg)
        return

    # Get folder name from info if available, otherwise use title
    folder_name = info.get('folder_name', 'Unknown')
    if folder_name == 'Unknown':
        # Try to extract folder name from title as fallback
        if 'Dropbox Account Folder Name:' in title:
            folder_name = title.split("Dropbox Account Folder Name: '")[-1].split("'")[0]
        else:
            folder_name = title

    # Owner information
    if info.get('owner'):
        owner_data = info['owner']
        
        if owner_data.get('firstName') and owner_data.get('lastName'):
            log.info(f"👤 Name: {owner_data['firstName']} {owner_data['lastName']}")
            if report_log:
                report_log.info(f"👤 Name: {owner_data['firstName']} {owner_data['lastName']}")
        
        if owner_data.get('dateOfBirth'):
            log.info(f"    🎂 Date of Birth: {owner_data['dateOfBirth']}")
            if report_log:
                report_log.info(f"    🎂 Date of Birth: {owner_data['dateOfBirth']}")
        
        if owner_data.get('gender'):
            log.info(f"    ♂️♀️ Gender: {owner_data['gender']}")
            if report_log:
                report_log.info(f"    ♂️♀️ Gender: {owner_data['gender']}")
        
        if owner_data.get('mailingAddressStreet'):
            address = f"{owner_data['mailingAddressStreet']}"
            if owner_data.get('mailingAddressCity'):
                address += f", {owner_data['mailingAddressCity']}"
            if owner_data.get('mailingAddressState'):
                address += f", {owner_data['mailingAddressState']}"
            if owner_data.get('mailingAddressZip'):
                address += f" {owner_data['mailingAddressZip']}"
            log.info(f"    📍 Address: {address}")
            if report_log:
                report_log.info(f"    📍 Address: {address}")
        
        if owner_data.get('phoneNumber'):
            log.info(f"    📞 Phone: {owner_data['phoneNumber']}")
            if report_log:
                report_log.info(f"    📞 Phone: {owner_data['phoneNumber']}")
        
        if owner_data.get('emailAddress'):
            log.info(f"    📧 Email: {owner_data['emailAddress']}")
            if report_log:
                report_log.info(f"    📧 Email: {owner_data['emailAddress']}")
        
        if owner_data.get('ocrMethod'):
            log.info(f"    🔍 OCR Method: {owner_data['ocrMethod']}")
            if report_log:
                report_log.info(f"    🔍 OCR Method: {owner_data['ocrMethod']}")

    # Joint owner information
    if info.get('jointOwner'):
        joint_owner_data = info['jointOwner']
        
        if joint_owner_data.get('firstName') and joint_owner_data.get('lastName'):
            log.info(f"👤👤 [Joint] Name: {joint_owner_data['firstName']} {joint_owner_data['lastName']}")
            if report_log:
                report_log.info(f"👤👤 [Joint] Name: {joint_owner_data['firstName']} {joint_owner_data['lastName']}")
        
        if joint_owner_data.get('dateOfBirth') and joint_owner_data.get('dateOfBirth') != "null":
            log.info(f"    🎂 Date of Birth: {joint_owner_data['dateOfBirth']}")
            if report_log:
                report_log.info(f"    🎂 Date of Birth: {joint_owner_data['dateOfBirth']}")
        
        if joint_owner_data.get('gender'):
            log.info(f"    ♂️♀️ Gender: {joint_owner_data['gender']}")
            if report_log:
                report_log.info(f"    ♂️♀️ Gender: {joint_owner_data['gender']}")
        
        if joint_owner_data.get('mailingAddressStreet'):
            address = f"{joint_owner_data['mailingAddressStreet']}"
            if joint_owner_data.get('mailingAddressCity'):
                address += f", {joint_owner_data['mailingAddressCity']}"
            if joint_owner_data.get('mailingAddressState'):
                address += f", {joint_owner_data['mailingAddressState']}"
            if joint_owner_data.get('mailingAddressZip'):
                address += f" {joint_owner_data['mailingAddressZip']}"
            log.info(f"📍 Address: {address}", summary_logger, report_logger)
        
        if joint_owner_data.get('phoneNumber'):
            log.info(f"    📞 Phone: {joint_owner_data['phoneNumber']}")
            if report_log:
                report_log.info(f"    📞 Phone: {joint_owner_data['phoneNumber']}")
        
        if joint_owner_data.get('emailAddress'):
            log.info(f"    📧 Email: {joint_owner_data['emailAddress']}")
            if report_log:
                report_log.info(f"    📧 Email: {joint_owner_data['emailAddress']}")
        
        if joint_owner_data.get('ocrMethod'):
            log.info(f"    🔍 OCR Method: {joint_owner_data['ocrMethod']}")
            if report_log:
                report_log.info(f"    🔍 OCR Method: {joint_owner_data['ocrMethod']}")

    # Notes
    if info.get('notes') and isinstance(info['notes'], list) and info['notes']:
        log.info("📝 Notes:")
        if report_log:
            report_log.info("📝 Notes:")
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
    
    # Count files with actual extracted information (not just notes about skipping)
    files_with_info = 0
    files_without_info = 0
    
    for info in file_info.values():
        if not info:
            files_without_info += 1
            continue
            
        # Check if the file has actual extracted account information
        has_owner_info = False
        has_joint_owner_info = False
        
        # Check for owner information
        if info.get('owner'):
            owner_data = info['owner']
            if (owner_data.get('firstName') and owner_data.get('lastName') and 
                owner_data.get('dateOfBirth') and owner_data.get('gender')):
                has_owner_info = True
        
        # Check for joint owner information
        if info.get('jointOwner'):
            joint_owner_data = info['jointOwner']
            if (joint_owner_data.get('firstName') and joint_owner_data.get('lastName') and 
                joint_owner_data.get('dateOfBirth') and joint_owner_data.get('gender')):
                has_joint_owner_info = True
        
        # File has info if it has either owner or joint owner information
        if has_owner_info or has_joint_owner_info:
            files_with_info += 1
        else:
            files_without_info += 1
    
    log.info(f"\n=== APP FILES PROCESSING SUMMARY ===")
    log.info(f"📊 Total files processed: {total_files}")
    log.info(f"✅ Files with extracted info: {files_with_info}")
    log.info(f"❌ Files without info: {files_without_info}")
    
    if report_log:
        report_log.info(f"\n=== APP FILES PROCESSING SUMMARY ===")
        report_log.info(f"📊 Total files processed: {total_files}")
        report_log.info(f"✅ Files with extracted info: {files_with_info}")
        report_log.info(f"❌ Files without info: {files_without_info}")

    # Log detailed information for each file using log_dropbox_app_file_info
    log.info(f"\n📋 DETAILED APP FILE INFORMATION:")
    if report_log:
        report_log.info(f"\n📋 DETAILED APP FILE INFORMATION:")
    
    for file_path, info in file_info.items():
        file_name = file_path.split('/')[-1] if '/' in file_path else file_path
        
        # Extract folder name from path for better context
        folder_name = None
        if '/' in file_path:
            # Get the folder name from the path (second to last part)
            path_parts = file_path.split('/')
            if len(path_parts) >= 2:
                folder_name = path_parts[-2]  # Second to last part is the folder name
        
        # Use log_dropbox_app_file_info for detailed logging of each file
        log_dropbox_app_file_info(
            info, 
            log, 
            report_log, 
            file_name, 
            folder_name
        )

    log.info("")  # Add blank line at the end
    if report_log:
        report_log.info("")  # Add blank line at the end 

def log_icon_legend(logger_instance: Any = None, report_logger: Any = None) -> None:
    """Log the icon legend for account information display.
    
    Args:
        logger_instance: Optional logger instance to use (defaults to module logger)
        report_logger: Optional report logger instance to use for additional logging
    """
    log = logger_instance or logger
    report_log = report_logger
    
    legend = """
Icon Legend:
📁 - Dropbox Folder
🪪 - Driver's License Found
🔺 - No Driver's License
📄 - Dropbox Account Match Found
🔴 - No Dropbox Account Match
👤 - Salesforce Account
🟥 - No Salesforce Account

Additional Account Information:
📧 - Email
📞 - Phone
📍 - Address
🔒 - SSN/Tax ID
🎂 - Birthdate
👶 - Age
"""
    log.info(legend)
    if report_log:
        report_log.info(legend)
    
    separator = "\n" + "="*50 + "\n"
    log.info(separator)
    if report_log:
        report_log.info(separator)


class DropboxAccountLogger:
    """Utility class for logging Dropbox Account Information with analysis formatting."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the Dropbox Account Logger.
        
        Args:
            logger: Optional logger instance. If not provided, uses the root logger.
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def _log(self, message: str, summary_logger: Optional[logging.Logger] = None, report_logger: Optional[logging.Logger] = None):
        self.logger.info(message)  # analyzer.log
        if summary_logger:
            summary_logger.info(message)  # summary.log
        if report_logger:
            report_logger.info(message)  # report.log
    
    def log_dropbox_account_information(self, 
                                      dropbox_account_information: Dict[str, Any], 
                                      dropbox_account_folder_name: str,
                                      summary_logger: Optional[logging.Logger] = None,
                                      report_logger: Optional[logging.Logger] = None) -> None:
        """Log Dropbox Account Information in a structured format."""
        self._log("[log_dropbox_account_information]", summary_logger, report_logger)
        self._log(f"\n{'='*80}", summary_logger, report_logger)
        self._log(f"📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦📦", summary_logger, report_logger)
        self._log(f"📦 **DROPBOX ACCOUNT INFORMATION** 📊", summary_logger, report_logger)
        self._log(f"📁 Dropbox Account Folder: {dropbox_account_folder_name}", summary_logger, report_logger)
        self._log(f"{'='*80}", summary_logger, report_logger)
        
        # Log summary section
        self._log_summary_section(dropbox_account_information, summary_logger, report_logger)
        
        # Log detailed account information
        self._log_detailed_account_information(dropbox_account_information, summary_logger, report_logger)
        
        # Log statistics summary
        self._log_statistics_summary(dropbox_account_information, summary_logger, report_logger)
    
    def _log_summary_section(self, dropbox_account_information: Dict[str, Any], summary_logger: Optional[logging.Logger] = None, report_logger: Optional[logging.Logger] = None) -> None:
        """Log the summary section with names found and data availability."""
        self._log("[_log_summary_section]", summary_logger, report_logger)
        self._log(f"\n📋 **SUMMARY**", summary_logger, report_logger)
        
        # Names found
        names_found = dropbox_account_information.get('names_found', [])
        if names_found:
            self._log(f"🔍 Names found: {', '.join(names_found)}", summary_logger, report_logger)
        else:
            self._log(f"🔍 Names found: None", summary_logger, report_logger)
        
        # Client list file data availability
        client_list_data = dropbox_account_information.get('client_list_data')
        if client_list_data:
            self._log(f"📄 Client List File Information: Available", summary_logger, report_logger)
        else:
            self._log(f"📄 Client List File Information: Not available", summary_logger, report_logger)
        
        # Application files data availability
        application_data = dropbox_account_information.get('application_data')
        if application_data and application_data.get('best_available_info') is not None:
            self._log(f"📄 Application Files Data: Available", summary_logger, report_logger)
        else:
            self._log(f"📄 Application Files Data: Not available", summary_logger, report_logger)
    
    def _log_detailed_account_information(self, dropbox_account_information: Dict[str, Any], summary_logger: Optional[logging.Logger] = None, report_logger: Optional[logging.Logger] = None) -> None:
        """Log detailed information for each account."""
        self._log("[_log_detailed_account_information]", summary_logger, report_logger)
        accounts = dropbox_account_information.get('accounts', [])
        
        self._log(f"\n📊 **DETAILED ACCOUNT INFORMATION**", summary_logger, report_logger)
        
        # Log structured accounts
        if accounts:
            for i, account in enumerate(accounts, 1):
                self._log_single_account(account, i, summary_logger, report_logger)
        
        # Log raw application files data if available
        application_data = dropbox_account_information.get('application_data')
        if application_data and application_data.get('best_available_info') is not None:
            self._log_application_files_data(application_data, summary_logger, report_logger)
    
    def _log_application_files_data(self, application_data: Dict[str, Any], summary_logger: Optional[logging.Logger] = None, report_logger: Optional[logging.Logger] = None) -> None:
        """Log raw application files data in a analysis format."""
        self._log("[_log_application_files_data]", summary_logger, report_logger)
        best_info = application_data.get('best_available_info', {})
        if not best_info:
            return
        
        self._log(f"\n{'─'*60}", summary_logger, report_logger)
        self._log(f"📄 **Application Files Data**", summary_logger, report_logger)
        self._log(f"{'─'*60}", summary_logger, report_logger)
        
        # Application details
        if application_data.get('application_type'):
            self._log(f"📋 Application Type: {application_data['application_type']}", summary_logger, report_logger)
        
        if application_data.get('status'):
            self._log(f"📊 Status: {application_data['status']}", summary_logger, report_logger)
        
        # Primary account holder
        owner = best_info.get('owner', {})
        if owner:
            self._log(f"\n👤 **Primary Account Holder**", summary_logger, report_logger)
            self._log(f"{'─'*40}", summary_logger, report_logger)
            
            if owner.get('firstName') or owner.get('lastName'):
                name = f"{owner.get('firstName', '')} {owner.get('lastName', '')}".strip()
                self._log(f"👤 Name: {name}", summary_logger, report_logger)
            
            if owner.get('dateOfBirth'):
                self._log(f"🎂 Date of Birth: {owner['dateOfBirth']}", summary_logger, report_logger)
            
            if owner.get('gender'):
                self._log(f"♂️♀️ Gender: {owner['gender']}", summary_logger, report_logger)
            
            if owner.get('emailAddress'):
                self._log(f"📧 Email: {owner['emailAddress']}", summary_logger, report_logger)
            
            if owner.get('phoneNumber'):
                self._log(f"📞 Phone: {owner['phoneNumber']}", summary_logger, report_logger)
            
            # Build address
            if owner.get('mailingAddressStreet'):
                address_parts = [owner['mailingAddressStreet']]
                if owner.get('mailingAddressCity'):
                    address_parts.append(owner['mailingAddressCity'])
                if owner.get('mailingAddressState'):
                    address_parts.append(owner['mailingAddressState'])
                if owner.get('mailingAddressZip'):
                    address_parts.append(owner['mailingAddressZip'])
                address = ', '.join(address_parts)
                self._log(f"📍 Address: {address}", summary_logger, report_logger)
        
        # Joint account holder
        joint_owner = best_info.get('jointOwner', {})
        if joint_owner:
            self._log(f"\n👥 **Joint Account Holder**", summary_logger, report_logger)
            self._log(f"{'─'*40}", summary_logger, report_logger)
            
            if joint_owner.get('firstName') or joint_owner.get('lastName'):
                name = f"{joint_owner.get('firstName', '')} {joint_owner.get('lastName', '')}".strip()
                self._log(f"👤 Name: {name}", summary_logger, report_logger)
            
            if joint_owner.get('dateOfBirth'):
                self._log(f"🎂 Date of Birth: {joint_owner['dateOfBirth']}", summary_logger, report_logger)
            
            if joint_owner.get('gender'):
                self._log(f"♂️♀️ Gender: {joint_owner['gender']}", summary_logger, report_logger)
            
            if joint_owner.get('emailAddress'):
                self._log(f"📧 Email: {joint_owner['emailAddress']}", summary_logger, report_logger)
            
            if joint_owner.get('phoneNumber'):
                self._log(f"📞 Phone: {joint_owner['phoneNumber']}", summary_logger, report_logger)
            
            # Build address
            if joint_owner.get('mailingAddressStreet'):
                address_parts = [joint_owner['mailingAddressStreet']]
                if joint_owner.get('mailingAddressCity'):
                    address_parts.append(joint_owner['mailingAddressCity'])
                if joint_owner.get('mailingAddressState'):
                    address_parts.append(joint_owner['mailingAddressState'])
                if joint_owner.get('mailingAddressZip'):
                    address_parts.append(joint_owner['mailingAddressZip'])
                address = ', '.join(address_parts)
                self._log(f"📍 Address: {address}", summary_logger, report_logger)
        
        # Processing notes
        notes = application_data.get('notes', [])
        if notes:
            self._log(f"\n📝 **Processing Notes**", summary_logger, report_logger)
            self._log(f"{'─'*40}", summary_logger, report_logger)
            for note in notes:
                self._log(f"   • {note}", summary_logger, report_logger)
        
        # File processing statistics
        total_files = application_data.get('total_files_processed', 0)
        complete_files = application_data.get('files_with_complete_info', 0)
        partial_files = application_data.get('files_with_partial_info', 0)
        no_info_files = application_data.get('files_with_no_info', 0)
        
        if total_files > 0:
            self._log(f"\n📊 **File Processing Statistics**", summary_logger, report_logger)
            self._log(f"{'─'*40}", summary_logger, report_logger)
            self._log(f"📄 Total Files Processed: {total_files}", summary_logger, report_logger)
            self._log(f"✅ Files with Complete Info: {complete_files}", summary_logger, report_logger)
            self._log(f"⚠️ Files with Partial Info: {partial_files}", summary_logger, report_logger)
            self._log(f"❌ Files with No Info: {no_info_files}", summary_logger, report_logger)
    
    def _log_single_account(self, account: Dict[str, Any], account_number: int, summary_logger: Optional[logging.Logger] = None, report_logger: Optional[logging.Logger] = None) -> None:
        """Log information for a single account."""
        self._log("[_log_single_account]", summary_logger, report_logger)
        self._log(f"\n{'─'*60}", summary_logger, report_logger)
        source_icon = "📄" if account['source'] == 'client_list_file' else "📄"
        self._log(f"{source_icon} **Account {account_number}: {account['account_name']} ({account['source'].replace('_', ' ').title()})**", summary_logger, report_logger)
        self._log(f"{'─'*60}", summary_logger, report_logger)
        
        # Account source and type
        self._log(f"👤 Source: {account['source']}", summary_logger, report_logger)
        self._log(f"👤 Account Type: {account['account_type']}", summary_logger, report_logger)
        
        # Log account details
        self._log_account_details(account, summary_logger, report_logger)
    
    def _log_account_details(self, account: Dict[str, Any], summary_logger: Optional[logging.Logger] = None, report_logger: Optional[logging.Logger] = None) -> None:
        """Log detailed account information."""
        self._log("[_log_account_details]", summary_logger, report_logger)
        
        # Match status
        if account.get('match_status'):
            self._log(f"✅ Match Status: {account['match_status']}", summary_logger, report_logger)
        
        # Personal information
        if account.get('first_name'):
            self._log(f"👤 First Name: {account['first_name']}", summary_logger, report_logger)
        
        if account.get('last_name'):
            self._log(f"👤 Last Name: {account['last_name']}", summary_logger, report_logger)
        
        if account.get('middle_name'):
            self._log(f"👤 Middle Name: {account['middle_name']}", summary_logger, report_logger)
        
        if account.get('birthdate'):
            self._log(f"🎂 Birthdate: {account['birthdate']}", summary_logger, report_logger)
        
        if account.get('gender'):
            self._log(f"♂️♀️ Gender: {account['gender']}", summary_logger, report_logger)
        
        # Contact information
        if account.get('phone'):
            self._log(f"📞 Phone: {account['phone']}", summary_logger, report_logger)
        
        if account.get('email'):
            self._log(f"📧 Email: {account['email']}", summary_logger, report_logger)
        
        # Address information
        if account.get('address'):
            self._log(f"📍 Address: {account['address']}", summary_logger, report_logger)
        
        # Driver's license information
        self._log_drivers_license_info(account, summary_logger, report_logger)
    
    def _log_drivers_license_info(self, account: Dict[str, Any], summary_logger: Optional[logging.Logger] = None, report_logger: Optional[logging.Logger] = None) -> None:
        """Log driver's license information."""
        self._log("[_log_drivers_license_info]", summary_logger, report_logger)
        drivers_license = account.get('drivers_license', {})
        
        if drivers_license and any(drivers_license.values()):
            self._log(f"\n🪪 **Driver's License**", summary_logger, report_logger)
            if drivers_license.get('number'):
                self._log(f"   🪪 Number: {drivers_license['number']}", summary_logger, report_logger)
            if drivers_license.get('state'):
                self._log(f"   🏛️ State: {drivers_license['state']}", summary_logger, report_logger)
            if drivers_license.get('expiration'):
                self._log(f"   📅 Expiration: {drivers_license['expiration']}", summary_logger, report_logger)
        else:
            self._log(f"\n🪪 **Driver's License**: Not found", summary_logger, report_logger)
    
    def _log_statistics_summary(self, dropbox_account_information: Dict[str, Any], summary_logger: Optional[logging.Logger] = None, report_logger: Optional[logging.Logger] = None) -> None:
        """Log the final statistics summary."""
        self._log("[_log_statistics_summary]", summary_logger, report_logger)
        total_accounts = len(dropbox_account_information.get('accounts', []))
        client_list_data_available = dropbox_account_information.get('client_list_data') is not None
        application_data_available = dropbox_account_information.get('application_data') is not None
        total_matches = sum(1 for account in dropbox_account_information.get('accounts', []) if account.get('match_status') == 'Match found')
        total_drivers_licenses = sum(1 for account in dropbox_account_information.get('accounts', []) if account.get('drivers_license'))
        
        self._log(f"\n📊 **STATISTICS SUMMARY**", summary_logger, report_logger)
        self._log(f"{'─'*60}", summary_logger, report_logger)
        self._log(f"📁 Total Accounts: {total_accounts}", summary_logger, report_logger)
        self._log(f"📄 Client List File Data: {'✅ Available' if client_list_data_available else '❌ Not Available'}", summary_logger, report_logger)
        self._log(f"📄 Application Files Data: {'✅ Available' if application_data_available else '❌ Not Available'}", summary_logger, report_logger)
        self._log(f"🔍 Total Matches: {total_matches}", summary_logger, report_logger)
        self._log(f"🪪 Total Driver's Licenses: {total_drivers_licenses}", summary_logger, report_logger)


def log_dropbox_account_information(dropbox_account_information: Dict[str, Any], 
                                  dropbox_account_folder_name: str,
                                  logger: Optional[logging.Logger] = None,
                                  summary_logger: Optional[logging.Logger] = None,
                                  report_logger: Optional[logging.Logger] = None) -> None:
    """
    Log comprehensive Dropbox Account Information with analysis formatting.
    
    Args:
        dropbox_account_information: The structured account information
        dropbox_account_folder_name: Name of the Dropbox account folder
        logger: Optional logger instance to use (defaults to module logger)
        summary_logger: Optional logger for summary log output
        report_logger: Optional logger for report log output
    """
    dropbox_logger = DropboxAccountLogger(logger)
    dropbox_logger.log_dropbox_account_information(
        dropbox_account_information, 
        dropbox_account_folder_name,
        summary_logger,
        report_logger
    )


def log_command_analysis(dropbox_account_information: Dict[str, Any],
                        logger: Optional[logging.Logger] = None) -> None:
    """
    Log Dropbox Account Information in command analysis format.
    
    Args:
        dropbox_account_information: The structured account information
        logger: Optional logger instance to use (defaults to module logger)
    """
    dropbox_logger = DropboxAccountLogger(logger)
    dropbox_logger.log_command_analysis(dropbox_account_information)


def log_json_format(dropbox_account_information: Dict[str, Any],
                   logger: Optional[logging.Logger] = None) -> None:
    """
    Log Dropbox Account Information in JSON format for easy parsing.
    
    Args:
        dropbox_account_information: The structured account information
        logger: Optional logger instance to use (defaults to module logger)
    """
    dropbox_logger = DropboxAccountLogger(logger)
    dropbox_logger.log_json_format(dropbox_account_information) 