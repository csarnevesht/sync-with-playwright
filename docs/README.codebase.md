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

### Search Capabilities

#### Dropbox Search
The system implements sophisticated Dropbox account search functionality:
- Searches through Excel files for account information
- Handles complex name formats and variations
- Supports multiple search strategies:
  - Last name-based search
  - Full name matching
  - Normalized name variations
  - Swapped name combinations
- Provides detailed search results including:
  - Exact matches
  - Partial matches
  - Match confidence levels
  - Search timing information

#### Salesforce Search
The Salesforce search implementation includes:
- Multi-strategy search approach:
  1. Primary search by last name
  2. Secondary search by full name
  3. Additional search with normalized variations
- Support for different Salesforce views (e.g., "All Clients", "Recent")
- Comprehensive match analysis:
  - Exact matches
  - Partial matches with similarity scoring
  - Match status tracking
  - View-specific results
- Detailed result structure including:
  - Match status
  - View information
  - Search timing
  - Match confidence levels

### Special Cases Handling

The system maintains a special cases registry to handle non-standard naming patterns and ensure accurate matching between Dropbox and Salesforce. This is particularly important because:

1. **Dropbox Naming Flexibility**
   - Dropbox folders can use various naming patterns for better organization
   - Common patterns include:
     * Family groupings (e.g., "Bauer Glenn and Brenda")
     * Parent-child relationships (e.g., "Gabriel Armand and son Dave")
     * Multiple family members (e.g., "Mason Patricia daughter Cheryl and Donna")
     * Nicknames and aliases (e.g., "Dell Aglio, Elena (Mike)")

2. **Salesforce Standardization**
   - Salesforce requires consistent naming conventions
   - Each special case maps to specific Salesforce account formats:
     * Individual accounts (e.g., "Alexander Rolle")
     * Household accounts (e.g., "Bauer Household")

3. **Mapping Structure**
   Each special case entry includes:
   - Original folder name
   - Last name and first name
   - Additional information
   - Expected Salesforce matches
   - Expected Dropbox matches (if applicable)

4. **Common Special Case Patterns**
   - Family units with multiple members
   - Parent-child relationships
   - Married couples
   - Households with multiple generations
   - Cases with nicknames or aliases
   - Compound last names
   - Multiple surname variations

5. **Implementation Details**
   - Special cases are stored in a dedicated configuration file
   - The system automatically checks for special cases during search
   - Multiple match possibilities are considered for each case
   - Results are weighted based on match confidence
   - Clear documentation of expected matches in both systems

### Account Management
- Advanced search capabilities for account matching
- Support for complex name formats including:
  - Names with commas
  - Names with ampersands
  - Names with parentheses
  - Multiple name variations
- Batch processing with configurable batch sizes
- Detailed account status reporting
- Comprehensive match tracking and analysis

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