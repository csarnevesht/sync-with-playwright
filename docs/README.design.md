# Dropbox to Salesforce CRM Synchronization - Design Document

## Overview
This document explains the design and implementation details of the Dropbox to Salesforce CRM synchronization system. The system automates the process of synchronizing files from Dropbox folders to Salesforce CRM accounts, handling both new and existing accounts.

## Architecture

### 1. Core Components

#### 1.1 Dropbox Integration (`dropbox_client.py`)
```python
class DropboxClient:
    def __init__(self, token: str):
        self.dbx = dropbox.Dropbox(token)
        self.root_folder = DROPBOX_ROOT_FOLDER
```
- **Purpose**: Manages all Dropbox API interactions
- **Key Features**:
  - Folder and file listing
  - File downloading with date prefixes
  - Account name parsing
  - Pattern-based file searching

#### 1.2 Salesforce Integration (`salesforce/pages/accounts_page.py`)
```python
class AccountsPage:
    def __init__(self, page: Page):
        self.page = page
```
- **Purpose**: Handles Salesforce UI interactions using Playwright
- **Key Features**:
  - Account creation and search
  - File management
  - File upload handling
  - Upload verification

### 2. File Upload Implementation

#### 2.1 Upload Process
```python
def upload_files(self, file_paths: List[str]) -> bool:
    # 1. Click Add Files button
    self.add_files()
    
    # 2. Wait for file input
    file_input = self.page.locator('input[type="file"]')
    expect(file_input).to_be_visible()
    
    # 3. Set files to upload
    file_input.set_input_files(file_paths)
    
    # 4. Wait for completion
    self._wait_for_upload_completion()
```
- **Steps**:
  1. Trigger file upload dialog
  2. Wait for file input element
  3. Set files to upload
  4. Monitor upload progress
  5. Verify completion

#### 2.2 Upload Monitoring
```python
def _wait_for_upload_completion(self, timeout: int = 300):
    start_time = time.time()
    while time.time() - start_time < timeout:
        progress_visible = self.page.locator('text=Uploading...').is_visible()
        if not progress_visible:
            success_visible = self.page.locator('text=Upload Complete').is_visible()
            if success_visible:
                return
        time.sleep(1)
```
- **Features**:
  - Progress indicator monitoring
  - Success message verification
  - Timeout handling
  - Configurable timeout period

#### 2.3 Upload Verification
```python
def verify_files_uploaded(self, file_names: List[str]) -> bool:
    for file_name in file_names:
        if not self.search_file(file_name):
            return False
    return True
```
- **Purpose**: Ensures all files were uploaded successfully
- **Process**:
  1. Search for each file
  2. Verify file presence
  3. Report missing files

### 3. File Processing Flow

#### 3.1 New Accounts
1. Create account in Salesforce
2. Download all files from Dropbox
3. Upload files to Salesforce
4. Verify uploads

#### 3.2 Existing Accounts
1. Search for existing files
2. Identify new files
3. Download new files
4. Upload new files
5. Verify uploads

### 4. Error Handling

#### 4.1 Upload Errors
- File input not found
- Upload timeout
- Upload failure
- Verification failure

#### 4.2 Recovery Mechanisms
- Retry logic for failed uploads
- Detailed error reporting
- Graceful failure handling

### 5. Security Considerations

#### 5.1 Authentication
- Dropbox token management
- Salesforce session handling
- Secure token storage

#### 5.2 File Handling
- Temporary file management
- Secure file cleanup
- Access control

### 6. Performance Considerations

#### 6.1 Optimization Techniques
- Batch file uploads
- Parallel processing potential
- Efficient file searching

#### 6.2 Resource Management
- Memory usage optimization
- Temporary file cleanup
- Browser session management

### 7. Configuration

#### 7.1 Environment Variables
```python
DROPBOX_ROOT_FOLDER = os.getenv('DROPBOX_ROOT_FOLDER', 'Wealth Management')
ACCOUNT_INFO_PATTERN = os.getenv('ACCOUNT_INFO_PATTERN', '*App.pdf')
DRIVERS_LICENSE_PATTERN = os.getenv('DRIVERS_LICENSE_PATTERN', '*DL.jpeg')
```
- Configurable patterns
- Default values
- Environment-based configuration

### 8. Future Improvements

#### 8.1 Potential Enhancements
- Parallel file processing
- Advanced error recovery
- Upload progress reporting
- File type validation
- Content verification

#### 8.2 Scalability Considerations
- Large file handling
- Multiple account processing
- Resource optimization

## Usage Example

```python
# Initialize clients
dbx = DropboxClient(token)
accounts_page = AccountsPage(page)

# Process files
with tempfile.TemporaryDirectory() as temp_dir:
    # Download files
    local_files = []
    for file in dbx.get_account_files(account_folder):
        local_path = dbx.download_file(file_path, temp_dir)
        if local_path:
            local_files.append(local_path)
    
    # Upload files
    if local_files:
        if accounts_page.upload_files(local_files):
            accounts_page.verify_files_uploaded(
                [os.path.basename(f) for f in local_files]
            )
```

## Dependencies
- Playwright: Browser automation
- Dropbox SDK: Dropbox API integration
- Python-dotenv: Environment configuration
- pytesseract: OCR capabilities
- pdf2image: PDF processing
- Pillow: Image processing 