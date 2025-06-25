# Supabase Storage for Application Files Data

This document describes the Supabase storage system for caching processed application files data to avoid re-running the slow LM Studio processor.

## Overview

The system now uses a separated approach where data extraction and storage are handled by separate commands. This provides better control and separation of concerns:

- **extract-dropbox-account-app-files-info**: Extracts data and checks for existing cached data
- **store-in-supabase**: Stores the extracted data in Supabase for future use

This approach provides several benefits:

- **Speed**: Avoid re-processing files that have already been analyzed
- **Cost Savings**: Reduce LM Studio API calls and processing time
- **Reliability**: Persistent storage of processed data
- **Scalability**: Handle large volumes of files efficiently
- **Control**: Separate extraction from storage for better workflow control

## Separated Command Approach

### How It Works

The system now uses two separate commands:

1. **extract-dropbox-account-app-files-info**: 
   - Checks if data already exists in Supabase for the folder
   - If found, retrieves and uses the cached data (much faster)
   - If not found, processes files normally
   - Does NOT automatically store results

2. **store-in-supabase**:
   - Stores the extracted data in Supabase for future use
   - Only runs when explicitly included in the command sequence

### Example Workflow

```bash
# First run - processes files and stores in Supabase
python -m src.cmd_runner --dropbox-account-name "John Doe" --commands "extract-dropbox-account-app-files-info,store-in-supabase"

# Second run - retrieves from Supabase (much faster)
python -m src.cmd_runner --dropbox-account-name "John Doe" --commands "extract-dropbox-account-app-files-info"
```

### Batch Processing

For processing multiple accounts:

```bash
clear && python -m sync.cmd_runner \
  --dropbox-account-info \
  --commands=extract-dropbox-account-app-files-info,store-in-supabase \
  --continue-on-error \
  --dropbox-accounts-file='accounts/todo.txt'
```

### Logging

The system provides detailed logging about Supabase operations:

**For cached data retrieval:**
```
✅ Application files data already exists in Supabase for folder: John Doe
Retrieved 3 files from Supabase
[_extract_dropbox_account_app_files_info] ✅ Retrieved 3 application files from Supabase
=== APP FILES EXTRACTION COMPLETED FROM SUPABASE IN 0.5 SECONDS ===
```

**For new processing:**
```
No existing data found in Supabase for folder: John Doe, proceeding with extraction
=== APP FILES EXTRACTION COMPLETED IN 120.5 SECONDS ===
```

**For storage:**
```
=== STORING APPLICATION FILES DATA IN SUPABASE ===
✅ Successfully stored 3 application files in Supabase for folder: John Doe
Account ID: 12345
✅ Successfully completed store-in-supabase operation
```

## Setup

### 1. Environment Variables

Set up your Supabase environment variables:

```bash
export SUPABASE_URL="your-supabase-url"
export SUPABASE_ANON_KEY="your-supabase-anon-key"
export SUPABASE_SERVICE_ROLE_KEY="your-supabase-service-role-key"
```

### 2. Database Schema

Run the schema setup script to create the required tables:

```bash
python -m src.sync.commands.setup_supabase_schema
```

Copy the generated SQL and execute it in your Supabase SQL editor.

### 3. Test Connection

Verify your setup:

```bash
python -m src.sync.commands.test_supabase_connection
```

## Manual Commands

### Store Data from Logs

Store existing processed data from log files:

```bash
python -m src.sync.commands.store_application_files_in_supabase --log-dir "logs/2025-06-21_11-52-51-all-analysis"
```

### Check Data

Check if data exists and get summaries:

```bash
python -m src.sync.commands.check_supabase_data --folder "John Doe"
```

### Delete Data

Remove data for a specific folder:

```bash
python -m src.sync.commands.check_supabase_data --folder "John Doe" --delete
```

## Data Structure

### ApplicationFile

Represents a processed application file:

```python
ApplicationFile(
    file_name="application.pdf",
    file_path="/path/to/file",
    application_type=ApplicationType.LIFE_INSURANCE,
    status=ApplicationStatus.PROCESSED,
    owner=PersonInfo(...),
    joint_owner=PersonInfo(...),
    notes=["Successfully extracted data"],
    extracted_text="Raw OCR text...",
    processing_timestamp=datetime.now(),
    ocr_confidence=85.5,
    lm_studio_model_used="qwen2-vl-7b-instruct",
    processing_duration_seconds=45.2
)
```

### PersonInfo

Represents person information (owner or joint owner):

```python
PersonInfo(
    first_name="John",
    last_name="Doe",
    date_of_birth="1980-05-15",
    gender="Male",
    mailing_address_street="123 Main St",
    mailing_address_city="Anytown",
    mailing_address_state="CA",
    mailing_address_zip="12345",
    phone_number="555-123-4567",
    email_address="john.doe@example.com",
    ocr_method="LM Studio"
)
```

### DropboxAccountWithFiles

Represents a Dropbox account with its processed files:

```python
DropboxAccountWithFiles(
    folder="John Doe",
    application_files=[...],
    total_files=3,
    processed_files=2,
    failed_files=1,
    processing_timestamp=datetime.now()
)
```

## Benefits

### Performance Improvements

- **First run**: Normal processing time (e.g., 2-3 minutes per file)
- **Subsequent runs**: Near-instant retrieval (e.g., 0.5 seconds total)

### Cost Savings

- Reduce LM Studio API calls
- Lower processing costs
- Faster development and testing cycles

### Reliability

- Persistent storage of processed data
- No data loss from temporary files
- Consistent results across runs

### Control

- Separate extraction from storage
- Choose when to store data
- Better workflow management

## Migration from Existing Data

### From Log Files

If you have existing processed data in log files:

1. Use the store command to migrate:
   ```bash
   python -m src.sync.commands.store_application_files_in_supabase --log-dir "path/to/logs"
   ```

2. Verify migration:
   ```bash
   python -m src.sync.commands.check_supabase_data
   ```

### From Other Sources

For data from other sources, use the example script as a template:

```python
from supabase_client import SupabaseClient
from supabase_client.schema import ApplicationFile, PersonInfo, DropboxAccountWithFiles

# Convert your data to the expected format
# Store using the client
```

## Troubleshooting

### Common Issues

1. **Connection Errors**
   - Verify environment variables
   - Check Supabase URL and keys
   - Ensure network connectivity

2. **Schema Errors**
   - Run schema setup script
   - Check table permissions
   - Verify enum types exist

3. **Data Conversion Errors**
   - Check data format compatibility
   - Verify required fields
   - Review error logs

4. **Missing Data**
   - Ensure `extract-dropbox-account-app-files-info` runs before `store-in-supabase`
   - Check that `app_files_extraction_summary` data exists

### Debug Commands

```bash
# Test basic connection
python test_integration.py

# Check schema
python -m src.sync.commands.setup_supabase_schema

# Test data operations
python examples/supabase_storage_example.py
```

## Future Enhancements

### Planned Features

1. **Incremental Updates**: Only process new or modified files
2. **Data Versioning**: Track changes and processing versions
3. **Batch Operations**: Process multiple folders efficiently
4. **Data Analytics**: Query and analyze stored data
5. **Export Functions**: Export data to various formats

### Configuration Options

Future versions may include:

- Configurable storage policies
- Data retention settings
- Processing priority queues
- Integration with other storage backends

## Example Usage

### Basic Workflow

```bash
# 1. Set up environment
export SUPABASE_URL="your-url"
export SUPABASE_ANON_KEY="your-key"

# 2. Set up database schema
python -m src.sync.commands.setup_supabase_schema

# 3. Test connection
python -m src.sync.commands.test_supabase_connection

# 4. Run extraction and storage
python -m src.cmd_runner --dropbox-account-name "John Doe" --commands "extract-dropbox-account-app-files-info,store-in-supabase"

# 5. Check stored data
python -m src.sync.commands.check_supabase_data --folder "John Doe"
```

### Advanced Usage

```bash
# Batch processing with storage
clear && python -m sync.cmd_runner \
  --dropbox-account-info \
  --commands=extract-dropbox-account-app-files-info,store-in-supabase \
  --continue-on-error \
  --dropbox-accounts-file='accounts/todo.txt'

# Store existing log data
python -m src.sync.commands.store_application_files_in_supabase --log-dir "logs/2025-06-21_11-52-51-all-analysis"

# Get data summary
python -m src.sync.commands.check_supabase_data --summary

# Delete specific data
python -m src.sync.commands.check_supabase_data --folder "John Doe" --delete
```

## Integration with Existing Workflows

The Supabase storage is designed to be transparent to existing workflows:

- **Modular**: Extraction and storage are separate concerns
- **Backward Compatible**: Works with existing data formats
- **Fallback**: Continues working even if Supabase is unavailable
- **Logging**: Provides detailed logs for monitoring

The system gracefully handles:
- Missing Supabase configuration
- Network connectivity issues
- Data conversion errors
- Schema mismatches
- Missing data between commands

All errors are logged but don't prevent the main workflow from completing.

## Command Sequence Examples

### New Account Processing
```bash
# Extract and store
python -m src.cmd_runner --dropbox-account-name "New Account" --commands "extract-dropbox-account-app-files-info,store-in-supabase"
```

### Existing Account (Cached)
```bash
# Just extract (will use cached data)
python -m src.cmd_runner --dropbox-account-name "Existing Account" --commands "extract-dropbox-account-app-files-info"
```

### Force Reprocessing
```bash
# Delete cached data first, then extract and store
python -m src.sync.commands.check_supabase_data --folder "Account Name" --delete
python -m src.cmd_runner --dropbox-account-name "Account Name" --commands "extract-dropbox-account-app-files-info,store-in-supabase"
```

### Batch Processing with Error Handling
```bash
# Process multiple accounts with continue-on-error
clear && python -m sync.cmd_runner \
  --dropbox-account-info \
  --commands=extract-dropbox-account-app-files-info,store-in-supabase \
  --continue-on-error \
  --dropbox-accounts-file='accounts/todo.txt'
``` 