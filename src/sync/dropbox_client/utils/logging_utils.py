"""Utility functions for logging operations."""

import logging
from typing import Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

def log_dropbox_app_file_info(info: Dict[str, Any], logger_instance: Any = None) -> None:
    """Log detailed information about a file.
    
    Args:
        info: Dictionary containing file information
        logger_instance: Optional logger instance to use (defaults to module logger)
    """
    log = logger_instance or logger

    # print(f"info: {info}")
    # Owner information
    if info.get('owner'):
        owner_data = info['owner']
        if owner_data.get('firstName') and owner_data.get('lastName'):
            log.info(f"    👤 Owner: {owner_data['firstName']} {owner_data['lastName']}")
        if owner_data.get('dateOfBirth'):
            log.info(f"    📅 Owner DOB: {owner_data['dateOfBirth']}")
        if owner_data.get('gender'):
            log.info(f"    👤 Owner Gender: {owner_data['gender']}")
        if owner_data.get('mailingAddressStreet'):
            address = f"{owner_data['mailingAddressStreet']}"
            if owner_data.get('mailingAddressCity'):
                address += f", {owner_data['mailingAddressCity']}"
            if owner_data.get('mailingAddressState'):
                address += f", {owner_data['mailingAddressState']}"
            if owner_data.get('mailingAddressZip'):
                address += f" {owner_data['mailingAddressZip']}"
            log.info(f"    📍 Owner Address: {address}")
        if owner_data.get('phoneNumber'):
            log.info(f"    📞 Owner Phone: {owner_data['phoneNumber']}")
        if owner_data.get('emailAddress'):
            log.info(f"    📧 Owner Email: {owner_data['emailAddress']}")

    # Joint owner information
    if info.get('jointOwner'):
        joint_owner_data = info['jointOwner']
        if joint_owner_data.get('firstName') and joint_owner_data.get('lastName'):
            log.info(f"    👥 Joint Owner: {joint_owner_data['firstName']} {joint_owner_data['lastName']}")
        if joint_owner_data.get('dateOfBirth'):
            log.info(f"    📅 Joint Owner DOB: {joint_owner_data['dateOfBirth']}")
        if joint_owner_data.get('gender'):
            log.info(f"    👤 Joint Owner Gender: {joint_owner_data['gender']}")
        if joint_owner_data.get('mailingAddressStreet'):
            address = f"{joint_owner_data['mailingAddressStreet']}"
            if joint_owner_data.get('mailingAddressCity'):
                address += f", {joint_owner_data['mailingAddressCity']}"
            if joint_owner_data.get('mailingAddressState'):
                address += f", {joint_owner_data['mailingAddressState']}"
            if joint_owner_data.get('mailingAddressZip'):
                address += f" {joint_owner_data['mailingAddressZip']}"
            log.info(f"    📍 Joint Owner Address: {address}")
        if joint_owner_data.get('phoneNumber'):
            log.info(f"    📞 Joint Owner Phone: {joint_owner_data['phoneNumber']}")
        if joint_owner_data.get('emailAddress'):
            log.info(f"    📧 Joint Owner Email: {joint_owner_data['emailAddress']}")

    # Application information
    if info.get('application_type'):
        log.info(f"    📄 Type: {info['application_type']}")
    if info.get('status'):
        log.info(f"    📋 Status: {info['status']}")
    log.info("")  # Add blank line between files 