# Codebase Documentation

## Overview
This codebase implements a synchronization system between Dropbox and Salesforce, with a focus on account management and file handling. The system provides robust functionality for searching, creating, updating, and managing accounts and their associated files across both platforms.

## Core Components

### Command Runner (`src/sync/cmd_runner.py`)
The command runner is the main entry point for the application, providing a CLI interface for various operations. Key features include:

- Account search and analysis
- Batch processing capabilities
- File migration status tracking
- Detailed logging and reporting
- Color-coded console output
- Comprehensive error handling

The command runner supports multiple operation modes:
- Single account search
- Batch processing from file
- Full analysis with file comparison
- Account creation and management
- File synchronization

### Testing Suite (`src/tests/`)
The codebase includes a comprehensive test suite covering all major functionality:

1. **Account Management Tests**
   - `test_account_creation.py`: Tests account creation workflows
   - `test_account_search.py`: Tests account search functionality
   - `test_account_filter.py`: Tests account filtering capabilities
   - `test_account_deletion.py`: Tests account deletion workflows

2. **File Management Tests**
   - `test_account_file_upload.py`: Tests file upload functionality
   - `test_account_file_deletion.py`: Tests file deletion workflows
   - `test_account_file_retrieval.py`: Tests file retrieval operations

3. **Integration Tests**
   - `test_dropbox_connection.py`: Tests Dropbox connectivity
   - `test_all.py`: Runs all test suites

## Key Features

### Account Management
- Search capabilities for account matching
- Support for complex name formats
- Batch processing with configurable batch sizes
- Detailed account status reporting

### File Management
- File migration status tracking
- Date prefix compliance verification
- File comparison between systems
- Batch file operations

### Logging and Reporting
- Timestamped log directories
- Separate log files for main operations and reports
- Color-coded console output
- Detailed error tracking and reporting

## Usage Examples

### Basic Account Search
```bash
python -m sync.cmd_runner --dropbox-account-name="Account Name"
```

### Batch Processing
```bash
python -m sync.cmd_runner --dropbox-accounts --account-batch-size 5 --start-from 10
```

### Full Analysis
```bash
python -m sync.cmd_runner --dropbox-accounts --dropbox-account-files --salesforce-accounts --salesforce-account-files
```

## Testing Strategy

The test suite follows a comprehensive approach:

1. **Unit Tests**
   - Individual component testing
   - Mocked external dependencies
   - Edge case coverage

2. **Integration Tests**
   - End-to-end workflow testing
   - Real system integration
   - Error condition handling

3. **Test Organization**
   - Modular test structure
   - Clear test naming conventions
   - Comprehensive test coverage

## Best Practices

1. **Error Handling**
   - Comprehensive error catching
   - Detailed error reporting
   - Graceful failure handling

2. **Logging**
   - Multiple log levels
   - Separate log files for different purposes
   - Color-coded console output

3. **Code Organization**
   - Clear module separation
   - Consistent naming conventions
   - Comprehensive documentation

## Future Improvements

1. **Performance Optimization**
   - Batch processing enhancements
   - Parallel processing capabilities
   - Caching mechanisms

2. **Feature Additions**
   - Additional search strategies
   - Enhanced reporting capabilities
   - Extended file management features

3. **Testing Enhancements**
   - Additional test coverage
   - Performance testing
   - Load testing capabilities 