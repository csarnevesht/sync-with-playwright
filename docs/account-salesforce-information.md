# Salesforce Account Information Structure

## Overview

The `salesforce_account_information` structure provides comprehensive information about Salesforce accounts and their relationships. This structure is created when the `--salesforce_account_info` flag is used with the command runner.

## Structure

```python
salesforce_account_information = {
    'names_found': List[str],           # List of all Salesforce account names found
    'household': Dict or None,          # Household account information (if exists)
    'head': Dict or None,               # Head of household account information (if exists)
    'members': List[Dict],              # List of household member accounts
    'accounts': List[Dict]              # List of all accounts with full details
}
```

## Account Object Structure

Each account object contains the following fields:

```python
account = {
    'account_name': str,                # Account name
    'type': str,                        # Account type (Contact, Household, etc.)
    'role': str or None,                # Role in household (Household Head, Member, etc.)
    'stage': str,                       # Account stage (Client, Prospect, etc.)
    'email': str,                       # Email address
    'phone': str,                       # Phone number
    'mailing_address': str,             # Mailing address
    'ssn/tax_id': str,                  # SSN or Tax ID
    'relationships': List[Dict]         # List of related accounts
}
```

## Usage Examples

### Accessing the Structure

The `salesforce_account_information` is available in the command runner data:

```python
# In a command
salesforce_account_information = command_runner.get_data('salesforce_account_information')

# Check if data exists
if salesforce_account_information:
    names_found = salesforce_account_information.get('names_found', [])
    print(f"Found {len(names_found)} Salesforce accounts")
```

### Using the Logging Utilities

The beautiful logging functionality is now available through the `logging_utils.py` module:

```python
from sync.salesforce_client.utils.logging_utils import (
    log_salesforce_account_information,
    log_command_analysis,
    log_json_format,
    SalesforceAccountLogger
)

# Log in the main format (used by cmd_runner.py)
log_salesforce_account_information(salesforce_account_information, dropbox_account_folder_name, logger)

# Log in command analysis format
log_command_analysis(salesforce_account_information, logger)

# Log in JSON format
log_json_format(salesforce_account_information, logger)

# Or use the class directly
salesforce_logger = SalesforceAccountLogger(logger)
salesforce_logger.log_salesforce_account_information(salesforce_account_information, dropbox_account_folder_name)
```

### Working with Household Information

```python
# Get household information
household = salesforce_account_information.get('household')
if household:
    print(f"Household: {household['account_name']}")
    print(f"Type: {household['type']}")
    print(f"Stage: {household.get('stage', 'N/A')}")
    print(f"Email: {household.get('email', 'N/A')}")
    print(f"Phone: {household.get('phone', 'N/A')}")
    print(f"Address: {household.get('mailing_address', 'N/A')}")
    print(f"SSN/Tax ID: {household.get('ssn/tax_id', 'N/A')}")
```

### Working with Head of Household

```python
# Get head of household information
head = salesforce_account_information.get('head')
if head:
    print(f"Head: {head['account_name']}")
    print(f"Type: {head['type']}")
    print(f"Role: {head.get('role', 'N/A')}")
    print(f"Stage: {head.get('stage', 'N/A')}")
```

### Working with Members

```python
# Get household members
members = salesforce_account_information.get('members', [])
if members:
    print(f"Members ({len(members)}):")
    for i, member in enumerate(members, 1):
        print(f"  {i}. {member['account_name']}")
        print(f"     Type: {member['type']}")
        print(f"     Role: {member.get('role', 'N/A')}")
        print(f"     Stage: {member.get('stage', 'N/A')}")
        print(f"     Email: {member.get('email', 'N/A')}")
        print(f"     Phone: {member.get('phone', 'N/A')}")
```

### Working with All Accounts

```python
# Get all accounts
accounts = salesforce_account_information.get('accounts', [])
if accounts:
    print(f"All Accounts ({len(accounts)}):")
    for i, account in enumerate(accounts, 1):
        print(f"  {i}. {account['account_name']}")
        print(f"     Type: {account['type']}")
        print(f"     Role: {account.get('role', 'N/A')}")
        print(f"     Stage: {account.get('stage', 'N/A')}")
        print(f"     Email: {account.get('email', 'N/A')}")
        print(f"     Phone: {account.get('phone', 'N/A')}")
        print(f"     Address: {account.get('mailing_address', 'N/A')}")
        print(f"     SSN/Tax ID: {account.get('ssn/tax_id', 'N/A')}")
        
        # Show relationships
        relationships = account.get('relationships', [])
        if relationships:
            print(f"     Relationships ({len(relationships)}):")
            for rel in relationships:
                print(f"       - {rel['account_name']} ({rel['type']}, {rel.get('role', 'N/A')})")
```

### Working with Relationships

```python
# Get relationships for a specific account
for account in salesforce_account_information.get('accounts', []):
    relationships = account.get('relationships', [])
    if relationships:
        print(f"Relationships for {account['account_name']}:")
        for rel in relationships:
            print(f"  - {rel['account_name']}")
            print(f"    Type: {rel['type']}")
            print(f"    Role: {rel.get('role', 'N/A')}")
            print(f"    Stage: {rel.get('stage', 'N/A')}")
            print(f"    Email: {rel.get('email', 'N/A')}")
            print(f"    Phone: {rel.get('phone', 'N/A')}")
```

## Command Line Usage

To use this structure, run the command with the `--salesforce_account_info` flag:

```bash
python -m sync.cmd_runner --env_file=.env --commands=your-command --salesforce_accounts --salesforce_account_info --dropbox_account_name="Account Name"
```

## Available Commands

The following commands are available to work with the `salesforce_account_information`:

- `log-salesforce-account-information`: Logs comprehensive account information in a readable format
- `log-salesforce-account-information-json`: Logs account information in JSON format for easy parsing

## Logging Utilities

The logging functionality has been refactored into a dedicated module at `src/sync/salesforce_client/utils/logging_utils.py`:

### Main Functions

- `log_salesforce_account_information()`: Main logging function used by cmd_runner.py
- `log_command_analysis()`: Command analysis format logging
- `log_json_format()`: JSON format logging

### SalesforceAccountLogger Class

A class-based approach for more control:

```python
from sync.salesforce_client.utils.logging_utils import SalesforceAccountLogger

logger = SalesforceAccountLogger(your_logger)
logger.log_salesforce_account_information(salesforce_account_information, dropbox_account_folder_name)
logger.log_command_analysis(salesforce_account_information)
logger.log_json_format(salesforce_account_information)
```

## Example Output

When using the `--salesforce_account_info` flag, you'll see beautiful, formatted output like this:

```
================================================================================
👤 **SALESFORCE ACCOUNT INFORMATION** 📊
📁 Dropbox Account Folder: Montesino, Maria
================================================================================

📋 **SUMMARY**
🔍 Names found: Maria Montesino, Maria Montesino Household
🏠 Household: Maria Montesino Household
👑 Head: Maria Montesino

📊 **DETAILED ACCOUNT INFORMATION**

────────────────────────────────────────────────────────────
🏢 **Account 1: Maria Montesino**
────────────────────────────────────────────────────────────
👤 Type: Contact
👑 Role: Household Head
✅ Stage: Client
📧 Email: jackaron2014@outlook.com
📞 Phone: 786-282-4047
📍 Address: 920 NE 199 ST. Apt. 417
Miami, FL. 33179
🔒 SSN/Tax ID: 770-20-3101

🔗 **Relationships**: None

────────────────────────────────────────────────────────────
🏢 **Account 2: Maria Montesino Household**
────────────────────────────────────────────────────────────
🏠 Type: Household
✅ Stage: Client
📧 Email: jackaron2014@outlook.com
📞 Phone: 786-282-4047
📍 Address: 920 NE 199 ST. Apt. 417
Miami, FL. 33179
🔒 SSN/Tax ID: 770-20-3101

🔗 **Relationships (1)**
   1. 📝 Maria Montesino
      👤 Type: Contact
      👑 Role: Household Head
      📋 Stage: Client
      📧 Email: jackaron2014@outlook.com
      📞 Phone: 786-282-4047

================================================================================
📈 **STATISTICS SUMMARY**
================================================================================
📊 Total Accounts: 2
🔗 Total Relationships: 1
🏠 Has Household: ✅ Yes
👑 Has Head: ✅ Yes
👥 Total Members: 0
================================================================================
```

### Command Output Example

When using the `log-salesforce-account-information` command:

```
🎯 === SALESFORCE ACCOUNT INFORMATION ANALYSIS ===
📋 **Names found**: Maria Montesino, Maria Montesino Household

🏠 **Household Information**
   📝 Name: Maria Montesino Household
   🏢 Type: Household
   📊 Stage: Client
   📧 Email: jackaron2014@outlook.com
   📞 Phone: 786-282-4047
   📍 Address: 920 NE 199 ST. Apt. 417
Miami, FL. 33179
   🔒 SSN/Tax ID: 770-20-3101
   🔗 Relationships: 1

👑 **Head of Household**
   📝 Name: Maria Montesino
   🏢 Type: Contact
   👑 Role: Household Head
   📊 Stage: Client
   📧 Email: jackaron2014@outlook.com
   📞 Phone: 786-282-4047
   📍 Address: 920 NE 199 ST. Apt. 417
Miami, FL. 33179
   🔒 SSN/Tax ID: 770-20-3101

👥 **Members**: None

📊 **All Accounts** (2)

────────────────────────────────────────────────────────────
🏢 **Account 1: Maria Montesino**
────────────────────────────────────────────────────────────
👤 Type: Contact
👑 Role: Household Head
✅ Stage: Client
📧 Email: jackaron2014@outlook.com
📞 Phone: 786-282-4047
📍 Address: 920 NE 199 ST. Apt. 417
Miami, FL. 33179
🔒 SSN/Tax ID: 770-20-3101

🔗 **Relationships**: None

────────────────────────────────────────────────────────────
🏢 **Account 2: Maria Montesino Household**
────────────────────────────────────────────────────────────
🏠 Type: Household
✅ Stage: Client
📧 Email: jackaron2014@outlook.com
📞 Phone: 786-282-4047
📍 Address: 920 NE 199 ST. Apt. 417
Miami, FL. 33179
🔒 SSN/Tax ID: 770-20-3101

🔗 **Relationships (1)**
   1. 📝 Maria Montesino
      👤 Type: Contact
      👑 Role: Household Head
      📋 Stage: Client
      📧 Email: jackaron2014@outlook.com
      📞 Phone: 786-282-4047

================================================================================
📈 **SUMMARY STATISTICS**
================================================================================
📊 Total names found: 2
🏠 Has household: ✅ Yes
👑 Has head: ✅ Yes
👥 Total members: 0
📊 Total accounts: 2
🔗 Total relationships: 1
================================================================================
```

## Benefits

1. **Comprehensive Data**: All account information is stored in a structured format
2. **Relationship Mapping**: Clear mapping of relationships between accounts
3. **Easy Access**: Simple API to access account data in commands
4. **Consistent Structure**: Standardized format across all accounts
5. **Extensible**: Easy to add new fields or modify the structure

## Notes

- The structure is only created when `--salesforce_account_info` flag is used
- All fields are optional and may be empty strings or None if not available
- The structure is stored in the command runner data and can be accessed by any command
- Relationships are deduplicated to avoid processing the same relationship multiple times 