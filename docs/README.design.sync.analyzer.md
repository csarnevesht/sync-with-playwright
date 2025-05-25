# Sync Analyzer Design Document

## Overview
The Sync Analyzer is a tool designed to analyze and track the migration status of accounts and their files from Dropbox to Salesforce. It provides comprehensive functionality to list, search, and compare accounts and files between both systems.

## Core Functionality

### 1. Account Management
- List Dropbox accounts
- List Salesforce accounts
- Search for Dropbox accounts in Salesforce
- Batch processing capabilities
- Support for single account analysis

### 2. File Management
- List Dropbox account files with modified dates
- List Salesforce account files
- Compare files between systems
- Track file migration status
- Handle modified date prefixes (YYMMDD format)
- Ensure Salesforce files have proper date prefixes

### 3. Search and Matching
- Fuzzy search for accounts
- Exact matching for files
- Batch processing with configurable size
- Start-from functionality for resuming large operations

## Command Line Interface

### Command Options

#### Account Source Options (Mutually Exclusive)
- `--dropbox-account-name`: Single Dropbox account to analyze
  - Example: `--dropbox-account-name 'Alexander & Armelia Rolle'`
  - When specified: Analyzes only this specific account
  - When not specified: Falls back to `--dropbox-accounts-file` or default behavior

- `--dropbox-accounts-file`: File containing list of Dropbox accounts
  - Example: `--dropbox-accounts-file accounts/fuzzy-small.txt`
  - When specified: Processes all accounts listed in the file
  - When not specified: Falls back to default behavior

- Default Behavior (when neither is specified):
  - Uses `--dropbox-accounts` to list and process all Dropbox accounts
  - No need to specify a file or single account
  - Processes all accounts found in Dropbox

#### Analysis Scope Options
- `--dropbox-accounts`: List Dropbox accounts
  - When specified: Shows all Dropbox accounts
  - When not specified: Only processes accounts from source options
  - Default behavior: This is the default when no account source is specified

- `--dropbox-account-files`: List Dropbox account files
  - When specified: Shows files for each Dropbox account
  - When not specified: Skips file listing

- `--salesforce-accounts`: List Salesforce accounts
  - When specified: Shows all Salesforce accounts
  - When not specified: Only searches for matches to Dropbox accounts

- `--salesforce-account-files`: List Salesforce account files
  - When specified: Shows files for each Salesforce account
  - When not specified: Skips file listing

#### Processing Options
- `--account-batch-size`: Number of accounts to process in each batch
  - Example: `--account-batch-size 5`
  - Default: Process all accounts at once
  - When specified: Processes accounts in batches of specified size

- `--start-from`: Index to start processing from
  - Example: `--start-from 10`
  - Default: Start from the beginning
  - When specified: Skips accounts before this index
  - Useful for resuming interrupted operations

- `--dropbox-accounts-only`: Process only Dropbox accounts
  - When specified: Skips Salesforce operations
  - When not specified: Performs full analysis

### Basic Usage
```bash
# Default behavior (lists all Dropbox accounts)
python -m sync.cmd_analyzer

# Single account analysis
python -m sync.cmd_analyzer --dropbox-account-name 'Account Name'

# Multiple accounts from file
python -m sync.cmd_analyzer --dropbox-accounts-file accounts/fuzzy-small.txt
```

### Advanced Options
```bash
# Full analysis with batching
python -m sync.cmd_analyzer \
    --dropbox-accounts \
    --dropbox-account-files \
    --salesforce-accounts \
    --salesforce-account-files \
    --account-batch-size 5 \
    --start-from 10

# Dropbox accounts only with batching
python -m sync.cmd_analyzer \
    --dropbox-accounts \
    --batch_size 5 \
    --start-from 10 \
    --dropbox-accounts-only
```

### Option Combinations and Effects

1. **Minimal Usage**
   ```bash
   python -m sync.cmd_analyzer
   ```
   - Lists and processes all Dropbox accounts
   - Performs basic account matching
   - No file listing or detailed analysis
   - No need to specify account source

2. **Default with File Analysis**
   ```bash
   python -m sync.cmd_analyzer --dropbox-account-files
   ```
   - Lists all Dropbox accounts (default behavior)
   - Lists files for each Dropbox account
   - Shows modified dates for each file
   - Performs basic account matching

3. **Default with Salesforce Analysis**
   ```bash
   python -m sync.cmd_analyzer --salesforce-accounts --salesforce-account-files
   ```
   - Lists all Dropbox accounts (default behavior)
   - Lists all Salesforce accounts
   - Lists files for each Salesforce account
   - Performs detailed matching and analysis
   - Shows file migration status

4. **Default with Batching**
   ```bash
   python -m sync.cmd_analyzer --account-batch-size 5 --start-from 10
   ```
   - Lists all Dropbox accounts (default behavior)
   - Processes accounts in batches of 5
   - Starts from the 10th account
   - Useful for large account lists

5. **Default with Full Analysis**
   ```bash
   python -m sync.cmd_analyzer --dropbox-account-files --salesforce-accounts --salesforce-account-files
   ```
   - Lists all Dropbox accounts (default behavior)
   - Lists files for each Dropbox account
   - Lists all Salesforce accounts
   - Lists files for each Salesforce account
   - Performs detailed matching and analysis
   - Shows file migration status
   - Tracks date prefix compliance

6. **Account Source Only**
   ```bash
   python -m sync.cmd_analyzer --dropbox-account-name 'Account Name'
   ```
   - Processes single specified account
   - Performs basic account matching
   - No file listing or detailed analysis

7. **File Analysis Only**
   ```bash
   python -m sync.cmd_analyzer --dropbox-account-files --salesforce-account-files
   ```
   - Lists all Dropbox accounts (default behavior)
   - Lists files for each Dropbox account
   - Lists files for each Salesforce account
   - Focuses on file comparison and migration status
   - Tracks date prefix compliance

8. **Batched Full Analysis**
   ```bash
   python -m sync.cmd_analyzer \
       --dropbox-account-files \
       --salesforce-accounts \
       --salesforce-account-files \
       --account-batch-size 5 \
       --start-from 10
   ```
   - Lists all Dropbox accounts (default behavior)
   - Processes accounts in batches of 5
   - Starts from the 10th account
   - Performs full analysis on each batch
   - Shows detailed matching and file status
   - Tracks date prefix compliance

## Architecture

### Components

1. **Account Manager**
   - Handles account listing and searching
   - Manages batch processing
   - Implements fuzzy search logic

2. **File Manager**
   - Handles file listing and comparison
   - Tracks file migration status
   - Manages file metadata
   - Processes modified dates
   - Handles date prefix formatting and validation

3. **Search Engine**
   - Implements fuzzy search algorithms
   - Handles name normalization
   - Manages search results

4. **Batch Processor**
   - Manages batch operations
   - Handles start-from functionality
   - Controls processing flow

### Data Flow
1. Input Processing
   - Parse command line arguments
   - Validate input parameters
   - Initialize required components

2. Account Processing
   - List accounts from source
   - Search for matches in target
   - Store results for analysis

3. File Processing
   - List files for matched accounts
   - Extract and validate modified dates
   - Compare files between systems
   - Track migration status
   - Verify date prefix compliance

4. Result Generation
   - Generate detailed reports
   - Provide summary statistics
   - Output migration status
   - Report on date prefix compliance

## Implementation Details

### Token and Environment Variables

#### Dropbox Tokens
- Environment Variables:
  - `DROPBOX_TOKEN`: Encrypted OAuth2 access token
  - `DROPBOX_REFRESH_TOKEN`: Encrypted OAuth2 refresh token
  - `DROPBOX_APP_KEY`: Your Dropbox app key
- Token Behavior:
  - Uses offline access tokens that persist until user logs out
  - Automatically checks token validity on each use
  - Automatically refreshes invalid tokens
  - Maintains session as long as user is logged into Dropbox
- Security Features:
  - Tokens are encrypted using Fernet symmetric encryption
  - Encryption key is stored securely after first use
  - Key is verified on each use to ensure validity
  - Key files are protected with restrictive permissions (0o600)
  - Tokens are encrypted at rest in .env file
  - Secure password input using getpass (only on first use)
- Source Priority:
  1. System environment variable
  2. `.env` file in project root
- Token Validation:
  - Checks for token presence at startup
  - Validates token format
  - Verifies token validity with Dropbox API
  - Automatically refreshes invalid tokens
  - Provides clear error messages for missing/invalid tokens

#### Environment File
- Default Location: `.env` in project root
- Required Variables:
  ```
  DROPBOX_TOKEN=<encrypted-access-token>
  DROPBOX_REFRESH_TOKEN=<encrypted-refresh-token>
  DROPBOX_APP_KEY=<app-key>
  DROPBOX_FOLDER=<root-folder-path>
  ```
- Security Files:
  ```
  .dropbox_key: Contains the encryption key (protected with 0o600 permissions)
  .dropbox_salt: Contains the salt for key derivation (protected with 0o600 permissions)
  ```
- Optional Variables:
  ```
  DEBUG_MODE=true/false
  TEST_MODE=true/false
  ```

#### Token Error Handling
- Missing Token:
  ```
  ERROR: DROPBOX_TOKEN environment variable is not set
  ```
- Invalid Token:
  ```
  INFO: Token is no longer valid, getting new offline access token...
  Please visit this URL to authorize the app:
  [Authorization URL]
  Enter the authorization code:
  ```
- Token Expired:
  ```
  INFO: Token is no longer valid, getting new offline access token...
  ```
- Refresh Token Missing:
  ```
  WARNING: No refresh token found in .env file or environment
  Please visit this URL to authorize the app:
  [Authorization URL]
  Enter the authorization code:
  ```
- Encryption Password Required:
  ```
  Enter password for Dropbox token encryption:
  ```

#### Security Best Practices
1. **Token Storage**
   - Tokens are encrypted at rest
   - Encryption key is derived from a password
   - Password is never stored
   - Salt is stored separately
   - Secure password input

2. **Access Control**
   - Password required for token decryption
   - Tokens are encrypted in memory
   - Secure password input using getpass
   - No token exposure in logs
   - Automatic token refresh

3. **Key Management**
   - PBKDF2 key derivation
   - 100,000 iterations for key derivation
   - Unique salt per installation
   - Secure key storage

4. **Session Management**
   - Offline access tokens
   - Automatic token validation
   - Automatic token refresh
   - Session persistence until logout

### Current Implementation
The current implementation in `sync/cmd_analyzer.py` provides:
- Basic account fuzzy search
- Single and batch account processing
- Simple result reporting

### Planned Improvements

1. **Enhanced Search**
   - Implement more sophisticated fuzzy search
   - Add support for partial matches
   - Improve name normalization

2. **Batch Processing**
   - Add progress tracking
   - Implement resume functionality
   - Add error recovery

3. **File Management**
   - Add file comparison logic
   - Implement file status tracking
   - Add file metadata handling
   - Implement modified date extraction
   - Add date prefix validation
   - Track prefix compliance status

4. **Reporting**
   - Add detailed migration reports
   - Implement status summaries
   - Add export functionality
   - Report on date prefix compliance
   - Track files needing prefix updates

## File Date Prefix Handling

### Format
- Prefix format: YYMMDD (e.g., "230315" for March 15, 2023)
- Can appear as "YYMMDD filename" or "YYMMDDfilename"
- Required for all Salesforce files
- Optional for Dropbox files

### Processing Rules
1. **Dropbox Files**
   - Extract modified date for each file
   - Store original filename and modified date
   - Generate expected prefix format
   - Track if file already has prefix

2. **Salesforce Files**
   - Validate existing prefixes
   - Track files missing prefixes
   - Compare with Dropbox modified dates
   - Flag inconsistencies

3. **Comparison Logic**
   - Match files with and without prefixes
   - Verify prefix matches modified date
   - Track files needing prefix updates
   - Report on compliance status

### Migration Goals
- All Salesforce files should have correct date prefixes
- Prefixes should match file modified dates
- Consistent format across all files
- Clear tracking of compliance status

## Future Considerations

### Performance Optimization
- Implement caching for frequently accessed data
- Add parallel processing for batch operations
- Optimize search algorithms

### User Experience
- Add interactive mode
- Implement progress bars
- Add detailed logging

### Integration
- Add support for other CRM systems
- Implement webhook notifications
- Add API endpoints

## Usage Examples

### Basic Account Search
```bash
# Search for a single account
python -m sync.cmd_analyzer --dropbox-account-name 'Alexander & Armelia Rolle'
```

### Batch Processing
```bash
# Process accounts in batches
python -m sync.cmd_analyzer \
    --dropbox-accounts \
    --batch_size 5 \
    --start-from 10
```

### Full Analysis
```bash
# Complete analysis with all features
python -m sync.cmd_analyzer \
    --dropbox-accounts \
    --dropbox-account-files \
    --salesforce-accounts \
    --salesforce-account-files \
    --account-batch-size 5 \
    --start-from 10
```

### Complete Analysis Example
```bash
# Full analysis with file comparison and modified date prefix handling
python -m sync.cmd_analyzer \
    --dropbox-accounts \
    --dropbox-account-files \
    --salesforce-accounts \
    --salesforce-account-files \
    --account-batch-size 5 \
    --start-from 0
```

This command will:
1. List all Dropbox accounts
2. For each Dropbox account:
   - List all files with their modified dates
   - Search for the account in Salesforce
   - If found in Salesforce:
     - List all Salesforce account files
     - For each Dropbox file:
       - Extract modified date
       - Generate expected prefix (YYMMDD format)
       - Search for file in Salesforce with:
         a. Original filename
         b. YYMMDD{filename} format
         c. YYMMDD {filename} format
       - Track if file is found and if prefix matches
3. Generate a detailed report showing:
   - Account matches
   - File migration status
   - Date prefix compliance
   - Files needing prefix updates

Example output:
```
Processing Dropbox Account: Alexander & Armelia Rolle
Found in Salesforce: Alexander & Armelia Rolle

Dropbox Files:
- tax_return_2023.pdf (Modified: 2023-03-15)
- bank_statement.pdf (Modified: 2023-02-28)
- investment_summary.pdf (Modified: 2023-01-15)

Salesforce Files:
- 230315 tax_return_2023.pdf
- 230228 bank_statement.pdf
- investment_summary.pdf (Missing prefix)

Migration Status:
✓ tax_return_2023.pdf: Migrated with correct prefix
✓ bank_statement.pdf: Migrated with correct prefix
✗ investment_summary.pdf: Migrated but missing prefix (Should be: 230115)
```

## Development Guidelines

### Code Organization
- Keep components modular and independent
- Implement clear interfaces between components
- Use dependency injection for flexibility

### Error Handling
- Implement comprehensive error handling
- Add detailed error messages
- Provide recovery options

### Testing
- Add unit tests for each component
- Implement integration tests
- Add performance benchmarks

### Documentation
- Keep documentation up to date
- Add inline code comments
- Provide usage examples 