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
- List Dropbox account files
- List Salesforce account files
- Compare files between systems
- Track file migration status

### 3. Search and Matching
- Fuzzy search for accounts
- Exact matching for files
- Batch processing with configurable size
- Start-from functionality for resuming large operations

## Command Line Interface

### Basic Usage
```bash
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
   - Compare files between systems
   - Track migration status

4. Result Generation
   - Generate detailed reports
   - Provide summary statistics
   - Output migration status

## Implementation Details

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

4. **Reporting**
   - Add detailed migration reports
   - Implement status summaries
   - Add export functionality

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