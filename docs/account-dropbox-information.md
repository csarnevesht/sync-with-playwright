# Dropbox Account Information Structure

## Overview

The `dropbox_account_information` structure provides comprehensive information about Dropbox accounts from multiple sources. This structure is created when the `--dropbox_account_info` flag is used with the command runner.

## Structure

```python
dropbox_account_information = {
    'names_found': List[str],           # List of all Dropbox account names found
    'client_list_data': Dict or None,   # Account information from Client List File
    'application_data': Dict or None,   # Account information from application files
    'accounts': List[Dict]              # List of all accounts with full details
}
```

## Account Object Structure

Each account object contains the following fields:

```python
account = {
    'account_name': str,                # Account name
    'source': str,                      # Data source ('client_list' or 'application_files')
    'account_type': str,                # Account type ('Primary', 'Joint', etc.)
    'first_name': str,                  # First name
    'middle_name': str,                 # Middle name
    'last_name': str,                   # Last name
    'birthdate': str,                   # Date of birth
    'gender': str,                      # Gender
    'phone': str,                       # Phone number
    'address': str,                     # Address
    'email': str,                       # Email address
    'additional_info': str,             # Additional information
    'match_status': str,                # Match status from search
    'drivers_license': Dict or None     # Driver's license information (if available)
}
```

## Data Sources

### Client List File Data

Information extracted from the Dropbox Client List File Excel file:

```python
client_list_data = {
    'account_name': str,                # Account name from folder
    'search_info': Dict,                # Search and match information
    'account_data': Dict,               # Extracted account data
    'drivers_license_info': Dict        # Driver's license extraction info
}
```

### Application Files Data

Information extracted from application files in the Dropbox account folder:

```python
application_data = {
    'folder_name': str,                 # Dropbox account folder name
    'owner': Dict,                      # Primary account holder information
    'joint_owner': Dict,                # Joint account holder information
    'application_type': str,            # Type of application
    'status': str,                      # Application status
    'notes': List[str]                  # Processing notes
}
```

## Usage Examples

### Accessing the Structure

The `dropbox_account_information` is available in the command runner data:

```python
# In a command
dropbox_account_information = command_runner.get_data('dropbox_account_information')

# Check if data exists
if dropbox_account_information:
    names_found = dropbox_account_information.get('names_found', [])
    print(f"Found {len(names_found)} Dropbox accounts")
```

### Using the Logging Utilities

The analysis logging functionality is available through the `logging_utils.py` module:

```python
from sync.dropbox_client.utils.logging_utils import (
    log_dropbox_account_information,
    log_command_analysis,
    log_json_format,
    DropboxAccountLogger
)

# Log in the main format (used by cmd_runner.py)
log_dropbox_account_information(dropbox_account_information, dropbox_account_folder_name, logger)

# Log in command analysis format
log_command_analysis(dropbox_account_information, logger)

# Log in JSON format
log_json_format(dropbox_account_information, logger)

# Or use the class directly
dropbox_logger = DropboxAccountLogger(logger)
dropbox_logger.log_dropbox_account_information(dropbox_account_information, dropbox_account_folder_name)
```

### Working with Client List File Data

```python
# Get client list file data
client_list_file_data = dropbox_account_information.get('client_list_data')
if client_list_file_data:
    account_data = client_list_file_data.get('account_data', {})
    print(f"Account Name: {account_data.get('name', 'N/A')}")
    print(f"First Name: {account_data.get('first_name', 'N/A')}")
    print(f"Last Name: {account_data.get('last_name', 'N/A')}")
    print(f"Email: {account_data.get('email', 'N/A')}")
    print(f"Phone: {account_data.get('phone', 'N/A')}")
    print(f"Address: {account_data.get('address', 'N/A')}")
    print(f"Birthdate: {account_data.get('birthdate', 'N/A')}")
    print(f"Gender: {account_data.get('gender', 'N/A')}")
    
    # Check match status
    search_info = client_list_file_data.get('search_info', {})
    match_info = search_info.get('match_info', {})
    print(f"Match Status: {match_info.get('match_status', 'N/A')}")
```

### Working with Application Files Data

```python
# Get application files data
application_data = dropbox_account_information.get('application_data')
if application_data:
    # Primary account holder
    owner = application_data.get('owner', {})
    if owner:
        print(f"Primary Account Holder:")
        print(f"  Name: {owner.get('firstName', '')} {owner.get('lastName', '')}")
        print(f"  Birthdate: {owner.get('dateOfBirth', 'N/A')}")
        print(f"  Gender: {owner.get('gender', 'N/A')}")
        print(f"  Phone: {owner.get('phoneNumber', 'N/A')}")
        print(f"  Email: {owner.get('emailAddress', 'N/A')}")
        print(f"  Address: {owner.get('mailingAddressStreet', 'N/A')}")
        if owner.get('mailingAddressCity'):
            print(f"    {owner.get('mailingAddressCity', '')}, {owner.get('mailingAddressState', '')} {owner.get('mailingAddressZip', '')}")
    
    # Joint account holder
    joint_owner = application_data.get('joint_owner', {})
    if joint_owner:
        print(f"Joint Account Holder:")
        print(f"  Name: {joint_owner.get('firstName', '')} {joint_owner.get('lastName', '')}")
        print(f"  Birthdate: {joint_owner.get('dateOfBirth', 'N/A')}")
        print(f"  Gender: {joint_owner.get('gender', 'N/A')}")
        print(f"  Phone: {joint_owner.get('phoneNumber', 'N/A')}")
        print(f"  Email: {joint_owner.get('emailAddress', 'N/A')}")
        print(f"  Address: {joint_owner.get('mailingAddressStreet', 'N/A')}")
        if joint_owner.get('mailingAddressCity'):
            print(f"    {joint_owner.get('mailingAddressCity', '')}, {joint_owner.get('mailingAddressState', '')} {joint_owner.get('mailingAddressZip', '')}")
    
    # Application details
    print(f"Application Type: {application_data.get('application_type', 'N/A')}")
    print(f"Status: {application_data.get('status', 'N/A')}")
```

### Working with All Accounts

```python
# Get all accounts
accounts = dropbox_account_information.get('accounts', [])
if accounts:
    print(f"All Accounts ({len(accounts)}):")
    for i, account in enumerate(accounts, 1):
        print(f"  {i}. {account['account_name']}")
        print(f"     Source: {account['source']}")
        print(f"     Type: {account.get('account_type', 'N/A')}")
        print(f"     First Name: {account.get('first_name', 'N/A')}")
        print(f"     Last Name: {account.get('last_name', 'N/A')}")
        print(f"     Email: {account.get('email', 'N/A')}")
        print(f"     Phone: {account.get('phone', 'N/A')}")
        print(f"     Address: {account.get('address', 'N/A')}")
        print(f"     Birthdate: {account.get('birthdate', 'N/A')}")
        print(f"     Gender: {account.get('gender', 'N/A')}")
        print(f"     Match Status: {account.get('match_status', 'N/A')}")
```

### Working with Driver's License Information

```python
# Get driver's license information
for account in dropbox_account_information.get('accounts', []):
    drivers_license = account.get('drivers_license')
    if drivers_license:
        print(f"Driver's License for {account['account_name']}:")
        print(f"  License Number: {drivers_license.get('license_number', 'N/A')}")
        print(f"  Date of Birth: {drivers_license.get('date_of_birth', 'N/A')}")
        print(f"  Expiration Date: {drivers_license.get('expiration_date', 'N/A')}")
        print(f"  State: {drivers_license.get('state', 'N/A')}")
```

## Command Line Usage

To use this structure, run the command with the `--dropbox_account_info` flag:

```bash
python -m sync.cmd_runner --env_file=.env --commands=your-command --dropbox_accounts --dropbox_account_info --dropbox_account_name="Account Name"
```

## Available Commands

The following commands are available to work with the `dropbox_account_information`:

- `log-dropbox-account-information`: Logs comprehensive account information in a readable format
- `log-dropbox-account-information-json`: Logs account information in JSON format for easy parsing

## Logging Utilities

The logging functionality has been refactored into a dedicated module at `src/sync/dropbox_client/utils/logging_utils.py`:

### Main Functions

- `log_dropbox_account_information()`: Main logging function used by cmd_runner.py
- `log_command_analysis()`: Command analysis format logging
- `log_json_format()`: JSON format logging

### DropboxAccountLogger Class

A class-based approach for more control:

```python
from sync.dropbox_client.utils.logging_utils import DropboxAccountLogger

logger = DropboxAccountLogger(your_logger)
logger.log_dropbox_account_information(dropbox_account_information, dropbox_account_folder_name)
logger.log_command_analysis(dropbox_account_information)
logger.log_json_format(dropbox_account_information)
```

## Example Output

When using the `--dropbox_account_info` flag, you'll see analysis, formatted output like this:

```
================================================================================
📁 **DROPBOX ACCOUNT INFORMATION** 📊
📁 Dropbox Account Folder: Montesino, Maria
================================================================================

📋 **SUMMARY**
🔍 Names found: Maria Montesino
📄 Client List File Data: Available
📄 Application Files Data: Available

📊 **DETAILED ACCOUNT INFORMATION**

────────────────────────────────────────────────────────────
📄 **Account 1: Maria Montesino (Client List File)**
────────────────────────────────────────────────────────────
👤 Source: client_list
✅ Match Status: Match found
👤 First Name: Maria
👤 Last Name: Montesino
📧 Email: jackaron2014@outlook.com
📞 Phone: 786-282-4047
📍 Address: 920 NE 199 ST. Apt. 417
Miami, FL. 33179
🎂 Birthdate: 01/15/1980
♂️♀️ Gender: Female

🪪 **Driver's License**: Found
   🪪 License Number: A1234567890123
   🪪 Date of Birth: 01/15/1980
   🪪 Expiration Date: 01/15/2028
   🪪 State: FL

────────────────────────────────────────────────────────────
📄 **Account 2: Maria Montesino (Application Files)**
────────────────────────────────────────────────────────────
👤 Source: application_files
👤 Account Type: Primary
👤 First Name: Maria
👤 Last Name: Montesino
🎂 Birthdate: 01/15/1980
♂️♀️ Gender: Female
📧 Email: jackaron2014@outlook.com
📞 Phone: 786-282-4047
📍 Address: 920 NE 199 ST. Apt. 417
Miami, FL. 33179

📋 **Application Details**
   📄 Type: New Application
   📊 Status: Pending Review

================================================================================
📈 **STATISTICS SUMMARY**
================================================================================
📊 Total Accounts: 2
📄 Has Client List File Data: ✅ Yes
📄 Has Application Files Data: ✅ Yes
🔍 Total Matches: 1
🪪 Total Driver's Licenses: 1
================================================================================
```

### Command Output Example

When using the `log-dropbox-account-information` command:

```
🎯 === DROPBOX ACCOUNT INFORMATION ANALYSIS ===
📋 **Names found**: Maria Montesino

📄 **Client List File Information**
   📝 Name: Maria Montesino
   🔍 Match Status: Match found
   👤 First Name: Maria
   👤 Last Name: Montesino
   📧 Email: jackaron2014@outlook.com
   📞 Phone: 786-282-4047
   📍 Address: 920 NE 199 ST. Apt. 417
Miami, FL. 33179
   🎂 Birthdate: 01/15/1980
   ♂️♀️ Gender: Female

📄 **Application Files Information**
   👤 Primary Account: Maria Montesino
   🎂 Birthdate: 01/15/1980
   ♂️♀️ Gender: Female
   📧 Email: jackaron2014@outlook.com
   📞 Phone: 786-282-4047
   📍 Address: 920 NE 199 ST. Apt. 417
Miami, FL. 33179

📋 **All Accounts** (2)

────────────────────────────────────────────────────────────
📄 **Account 1: Maria Montesino (Client List File)**
────────────────────────────────────────────────────────────
👤 Source: client_list
✅ Match Status: Match found
👤 First Name: Maria
👤 Last Name: Montesino
📧 Email: jackaron2014@outlook.com
📞 Phone: 786-282-4047
📍 Address: 920 NE 199 ST. Apt. 417
Miami, FL. 33179
🎂 Birthdate: 01/15/1980
♂️♀️ Gender: Female

────────────────────────────────────────────────────────────
📄 **Account 2: Maria Montesino (Application Files)**
────────────────────────────────────────────────────────────
👤 Source: application_files
👤 Account Type: Primary
👤 First Name: Maria
👤 Last Name: Montesino
🎂 Birthdate: 01/15/1980
♂️♀️ Gender: Female
📧 Email: jackaron2014@outlook.com
📞 Phone: 786-282-4047
📍 Address: 920 NE 199 ST. Apt. 417
Miami, FL. 33179

================================================================================
📈 **SUMMARY STATISTICS**
================================================================================
📊 Total names found: 1
📄 Has client list file data: ✅ Yes
📄 Has application files data: ✅ Yes
📊 Total accounts: 2
🔍 Total matches: 1
🪪 Total driver's licenses: 1
================================================================================
```

## Benefits

1. **Comprehensive Data**: All account information from multiple sources is stored in a structured format
2. **Source Tracking**: Clear indication of data source (Client List File vs application files)
3. **Easy Access**: Simple API to access account data in commands
4. **Consistent Structure**: Standardized format across all accounts
5. **Extensible**: Easy to add new fields or modify the structure
6. **Multiple Sources**: Combines data from client list files and application files

## Notes

- The structure is only created when `--dropbox_account_info` flag is used
- All fields are optional and may be empty strings or None if not available
- The structure is stored in the command runner data and can be accessed by any command
- Data from Client List File and application files are kept separate for clarity
- Driver's license information is only included when the `--dl` flag is used 