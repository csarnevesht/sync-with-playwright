# Account Analysis System

## Overview

The Account Analysis System provides comprehensive tools for comparing Salesforce and Dropbox account information, identifying data gaps, inconsistencies, and generating detailed migration plans. This system is designed to help organizations understand what data is available in each system, what's missing, and what should be migrated from Dropbox to Salesforce.

## Key Features

- **Comprehensive Data Comparison**: Compare account information between Salesforce and Dropbox
- **Intelligent Name Matching**: Advanced name variation generation and matching logic
- **Account Merging**: Automatic merging of accounts from multiple sources (client_list_file, application_files)
- **Field Precedence Logic**: Smart field selection with client_list_file taking precedence over application_files
- **Data Quality Assessment**: Calculate completeness and consistency scores
- **Migration Planning**: Generate prioritized migration plans with effort estimates
- **Household Structure Analysis**: Analyze household relationships and member structures
- **Multiple Report Formats**: Generate reports in JSON, text, and CSV formats
- **Batch Processing**: Analyze multiple accounts and generate batch reports
- **Report Management**: Save, load, and query analysis reports

## Architecture

### Core Components

1. **Models** (`src/sync/models.py`): Data structures for analysis reports and comparisons
2. **Account Analyzer** (`src/sync/analyzers/account_analyzer.py`): Main analysis engine with advanced matching logic
3. **Analysis Command** (`src/sync/commands/analyze-account-data.py`): Command-line interface
4. **Analysis Utils** (`src/sync/utils/analysis_utils.py`): Report management and export utilities

### Data Flow

```
Salesforce Account Info → Account Analyzer → Analysis Report
Dropbox Account Info   ↗                    ↘
                                      Migration Plans
                                      Data Quality Metrics
                                      Recommendations
```

## Core Analysis Rules

### 1. Name Matching and Variation Generation

The system generates multiple name variations to improve matching accuracy:

#### Name Variation Rules
- **Original Name**: Always included as first variation
- **"Last, First" Format**: For names like "Montesino, Maria"
  - Generates: "Maria Montesino" (swapped)
  - Generates: "Maria Montesino Household" (household variation)
- **"First Last" Format**: For names like "Maria Montesino"
  - Generates: "Montesino, Maria" (swapped)
  - Generates: "Maria Montesino Household" (household variation)
- **Deduplication**: Uses sets to avoid duplicate variations

#### Example Name Variations
```
Input: "Montesino, Maria"
Variations: ['Montesino, Maria', 'Maria Montesino', 'Maria Montesino Household']

Input: "Maria Montesino"
Variations: ['Maria Montesino', 'Montesino, Maria', 'Maria Montesino Household']
```

### 2. Account Merging Logic

The system automatically merges accounts from multiple sources:

#### Merge Conditions
- **Same Normalized Name**: Accounts with the same normalized name are merged
- **Multiple Sources**: Combines data from client_list_file and application_files
- **Field Precedence**: client_list_file data takes precedence over application_files

#### Field Precedence Rules
1. **If field exists in client_list_file**: Use client_list_file value
2. **If field missing in client_list_file but exists in application_files**: Use application_files value
3. **If field missing in both**: Mark as missing

#### Merge Process
1. **Normalize Names**: Convert all names to lowercase for comparison
2. **Group by Normalized Name**: Group accounts with same normalized name
3. **Merge Accounts**: Combine data using precedence rules
4. **Store Original Sources**: Keep track of which accounts were merged

### 3. Account Matching Logic

#### Salesforce to Dropbox Matching
- **Multiple Match Support**: Multiple Salesforce accounts can match the same Dropbox account
- **Household/Contact Matching**: Household and Contact accounts can match the same Dropbox account
- **Name Variation Matching**: Uses all generated name variations for matching
- **First-Come-First-Served**: First Salesforce account gets priority for matching

#### Dropbox Account Processing
- **Skip Already Matched**: If Dropbox account was already matched with Salesforce, skip additional comparisons
- **Field Comparison**: All field comparisons done through Salesforce account matching
- **No Duplicate Work**: Prevents redundant comparisons and suggestions

### 4. Field Mapping and Comparison

#### Field Mapping Structure
| Field | Salesforce | Dropbox Client List | Dropbox Application Files | Priority |
|-------|------------|-------------------|---------------------------|----------|
| first_name | first_name | first_name | firstName | HIGH |
| last_name | last_name | last_name | lastName | HIGH |
| middle_name | middle_name | middle_name | middleName | LOW |
| email | email | email | emailAddress | HIGH |
| phone | phone | phone | phoneNumber | MEDIUM |
| address | mailing_address | address | mailingAddressStreet | MEDIUM |
| birthdate | birthdate | birthdate | dateOfBirth | MEDIUM |
| gender | gender | gender | gender | LOW |
| ssn_tax_id | ssn/tax_id | ssn | ssn | HIGH |

#### Field Status Types
- **PRESENT**: Field has value in both systems
- **MISSING**: Field missing in one or both systems
- **DIFFERENT**: Field has different values between systems
- **PARTIAL**: Field partially populated

#### Migration Priority Levels
- **HIGH**: Essential fields (first_name, last_name, email, ssn_tax_id)
- **MEDIUM**: Important fields (phone, address, birthdate)
- **LOW**: Nice-to-have fields (gender, middle_name)
- **NOT_NEEDED**: Fields that don't require migration

### 5. Data Source Integration

#### Client List File Data
- **Source**: Extracted from Dropbox folder structure and client list files
- **Fields**: Basic contact information (name, phone, address)
- **Precedence**: Takes priority over application_files data

#### Application Files Data
- **Source**: Extracted from PDF application files using AI/ML processing
- **Fields**: Detailed personal information (birthdate, gender, email)
- **Processing**: Uses LM Studio for text extraction and structured data parsing
- **Fallback**: Used when client_list_file data is missing

## Data Structures

### Account Analysis Report

The main output of the analysis system is an `AccountAnalysisReport` that contains:

```python
class AccountAnalysisReport(BaseModel):
    dropbox_account_folder: str
    analysis_timestamp: datetime
    
    # Source data
    salesforce_account_information: Optional[Dict[str, Any]]
    dropbox_account_information: Optional[Dict[str, Any]]
    
    # Analysis results
    account_comparisons: List[AccountComparison]
    household_comparison: Optional[HouseholdComparison]
    data_quality: DataQualityAnalysis
    migration_plans: List[MigrationPlan]
    
    # Statistics
    total_accounts_found: int
    total_accounts_matched: int
    total_migrations_needed: int
    
    # Recommendations
    recommendations: List[str]
    warnings: List[str]
    errors: List[str]
```

### Account Comparison

Each account comparison includes detailed field analysis and merge information:

```python
class AccountComparison(BaseModel):
    account_name: str
    account_type: AccountType
    role: Optional[AccountRole] = None
    source: DataSource
    
    # Field comparisons
    first_name: FieldComparison
    last_name: FieldComparison
    middle_name: FieldComparison
    email: FieldComparison
    phone: FieldComparison
    address: FieldComparison
    birthdate: FieldComparison
    gender: FieldComparison
    ssn_tax_id: FieldComparison
    
    # Additional fields
    stage: Optional[str] = None
    drivers_license: Optional[Dict[str, Any]] = None
    merged_from: Optional[List[Dict[str, Any]]] = None  # For merged accounts
    
    # Migration info
    migration_needed: bool
    migration_priority: MigrationPriority
    migration_notes: Optional[str] = None
```

### Field Comparison

Each field is compared between systems with detailed status information:

```python
class FieldComparison(BaseModel):
    field_name: str
    salesforce_value: Optional[str]
    dropbox_value: Optional[str]
    status: FieldStatus  # present, missing, different, partial
    migration_priority: MigrationPriority  # high, medium, low, not_needed
    notes: Optional[str]
```

### Migration Plan

Detailed migration plans with priorities and effort estimates:

```python
class MigrationPlan(BaseModel):
    account_name: str
    migration_type: str  # create, update, merge
    priority: MigrationPriority
    estimated_effort: str  # low, medium, high
    
    fields_to_create: List[str]
    fields_to_update: List[str]
    fields_to_merge: List[str]
    
    dependencies: List[str]
    validation_rules: List[str]
    notes: Optional[str]
```

## Usage Examples

### Basic Single Account Analysis

```python
from sync.analyzers.account_analyzer import AccountAnalyzer
from sync.models import AccountAnalysisReport

# Initialize analyzer
analyzer = AccountAnalyzer()

# Perform analysis
analysis_report = analyzer.analyze_account(
    dropbox_account_folder="Montesino, Maria",
    salesforce_account_information=salesforce_data,
    dropbox_account_information=dropbox_data
)

# Access results
print(f"Total migrations needed: {analysis_report.total_migrations_needed}")
print(f"Data completeness: {analysis_report.data_quality.data_completeness_score:.1%}")

# Review migration plans
for plan in analysis_report.migration_plans:
    print(f"Plan for {plan.account_name}: {plan.migration_type} ({plan.priority})")
```

### Using the Command Interface

```bash
# Basic analysis
python -m sync.cmd_runner --commands=analyze-account-data --dropbox-account-name="Montesino, Maria"

# Full pipeline with application files extraction and analysis
python -m sync.cmd_runner \
    --commands=extract-dropbox-account-app-files-info,analyze-account-data \
    --dropbox-account-name="Montesino, Maria" \
    --dropbox-account-info \
    --salesforce-accounts \
    --salesforce-account-info
```

### Batch Analysis

```python
from sync.utils.analysis_utils import AnalysisReportManager, create_batch_analysis_report

# Initialize report manager
report_manager = AnalysisReportManager()

# Analyze multiple accounts
account_reports = []
for account_name in account_list:
    analysis_report = analyzer.analyze_account(
        dropbox_account_folder=account_name,
        salesforce_account_information=get_salesforce_data(account_name),
        dropbox_account_information=get_dropbox_data(account_name)
    )
    account_reports.append(analysis_report)
    
    # Save individual report
    report_manager.save_account_report(analysis_report, format="both")

# Create batch report
batch_report = create_batch_analysis_report(account_reports, "batch_20241201")
report_manager.save_batch_report(batch_report, format="both")
```

### Report Management

```python
# List available reports
reports = report_manager.list_reports()
for report in reports:
    print(f"{report['file_name']}: {report['account_name']} ({report['total_migrations']} migrations)")

# Load a specific report
loaded_report = report_manager.load_account_report("path/to/report.json")
if loaded_report:
    print(f"Loaded report for: {loaded_report.dropbox_account_folder}")

# Export to CSV
export_analysis_to_csv(analysis_report, "analysis_export.csv")
```

## Data Quality Metrics

The system calculates two key quality metrics:

### Completeness Score
Measures how much data is present across all fields:
```
completeness = (fields_present_salesforce + fields_present_dropbox) / (total_fields * 2)
```

### Consistency Score
Measures how well data matches between systems:
```
consistency = (total_fields - fields_different) / total_fields
```

## Report Formats

### JSON Format
Complete structured data for programmatic access:
```json
{
  "dropbox_account_folder": "Montesino, Maria",
  "analysis_timestamp": "2024-12-01T10:30:00",
  "total_accounts_found": 2,
  "total_migrations_needed": 3,
  "data_quality": {
    "data_completeness_score": 0.85,
    "data_consistency_score": 0.92
  },
  "account_comparisons": [...],
  "migration_plans": [...]
}
```

### Text Format
Human-readable summary with key findings and merge details:
```
================================================================================
ACCOUNT ANALYSIS REPORT
================================================================================
Account: Montesino, Maria
Analysis Date: 2024-12-01 10:30:00

SUMMARY
----------------------------------------
Total Accounts: 2
Total Migrations Needed: 3
Data Completeness: 85.0%
Data Consistency: 92.0%

ACCOUNT COMPARISONS
----------------------------------------
Maria Montesino Household
  Type: Household
  Role: Household Head
  Source: dropbox_merged
  Dropbox Account Used: Merged from 2 accounts:
    1. Montesino, Maria (source: client_list_file)
    2. Maria Montesino (source: application_files)
  Migration Needed: True
  Priority: high
  Issues: birthdate: missing, gender: missing
```

### CSV Format
Tabular data for spreadsheet analysis:
```csv
Account Name,Account Type,Role,Migration Needed,Priority,First Name Status,Last Name Status,Email Status,Phone Status,Address Status,Birthdate Status,Gender Status
Maria Montesino,Contact,Household Head,True,high,present,present,present,present,present,missing,missing
```

## Integration with Existing System

The analysis system integrates seamlessly with the existing command runner:

1. **Data Collection**: Uses existing `salesforce_account_information` and `dropbox_account_information` structures
2. **Command Integration**: Available as `analyze-account-data` command
3. **Application Files Integration**: Works with `extract-dropbox-account-app-files-info` command
4. **Logging**: Integrates with existing logging system
5. **Error Handling**: Follows existing error handling patterns

### Command Line Usage

```bash
# Basic analysis
python -m sync.cmd_runner --commands=analyze-account-data --dropbox-account-name="Account Name"

# Full pipeline with application files extraction and analysis
python -m sync.cmd_runner \
    --commands=extract-dropbox-account-app-files-info,analyze-account-data \
    --dropbox-account-name="Account Name" \
    --dropbox-account-info \
    --salesforce-accounts \
    --salesforce-account-info
```

## Best Practices

### 1. Data Preparation
- Ensure both Salesforce and Dropbox data are properly extracted
- Run application files extraction before analysis for complete data
- Validate data formats before analysis
- Handle missing or malformed data gracefully

### 2. Analysis Strategy
- Start with single account analysis to understand patterns
- Use batch analysis for large-scale assessments
- Review migration priorities based on business needs
- Check merge details to understand data sources

### 3. Report Management
- Save reports in both JSON and text formats
- Use descriptive file names with timestamps
- Archive old reports for historical analysis
- Review merge information to understand data quality

### 4. Migration Planning
- Prioritize high-priority migrations first
- Consider dependencies between accounts
- Validate data before migration
- Review field precedence rules for data conflicts

## Troubleshooting

### Common Issues

1. **Missing Data**: Check if account information flags are set
2. **Field Mapping Errors**: Verify field names in source data
3. **Report Generation Failures**: Ensure write permissions for output directory
4. **No Application Files Data**: Ensure `extract-dropbox-account-app-files-info` command was run
5. **Duplicate Account Comparisons**: Check if Dropbox accounts are being matched multiple times

### Debug Mode

Enable debug logging to see detailed analysis steps:
```python
import logging
logging.getLogger('sync.analyzers.account_analyzer').setLevel(logging.DEBUG)
```

### Debug Information Available
- Name variation generation
- Account merging process
- Field precedence decisions
- Matching logic decisions
- Skip conditions for already matched accounts

## Future Enhancements

1. **Advanced Matching**: Fuzzy name matching for better account correlation
2. **Data Validation**: Built-in validation rules for common data formats
3. **Migration Automation**: Direct integration with migration tools
4. **Dashboard**: Web-based dashboard for analysis results
5. **Scheduling**: Automated analysis scheduling and reporting
6. **Machine Learning**: Improved name matching using ML models
7. **Data Quality Scoring**: More sophisticated quality metrics

## API Reference

### AccountAnalyzer

```python
class AccountAnalyzer:
    def analyze_account(
        self,
        dropbox_account_folder: str,
        salesforce_account_information: Optional[Dict[str, Any]] = None,
        dropbox_account_information: Optional[Dict[str, Any]] = None
    ) -> AccountAnalysisReport
    
    def _generate_name_variations(self, name: str) -> List[str]
    def _merge_accounts_with_same_name(self, accounts: List[Dict[str, Any]]) -> Dict[str, Any]
    def _accounts_represent_same_person(self, db_account: Dict[str, Any], sf_key: Tuple[str, str]) -> bool
```

### AnalysisReportManager

```python
class AnalysisReportManager:
    def save_account_report(self, report: AccountAnalysisReport, format: str = "json") -> str
    def save_batch_report(self, report: BatchAnalysisReport, format: str = "json") -> str
    def load_account_report(self, file_path: str) -> Optional[AccountAnalysisReport]
    def list_reports(self, report_type: str = "all") -> List[Dict[str, Any]]
```

### Utility Functions

```python
def create_batch_analysis_report(account_reports: List[AccountAnalysisReport], batch_id: str) -> BatchAnalysisReport
def export_analysis_to_csv(report: AccountAnalysisReport, output_path: str) -> str
```

## Conclusion

The Account Analysis System provides a comprehensive solution for understanding data differences between Salesforce and Dropbox, enabling informed migration decisions and data quality improvements. The system's advanced name matching, account merging, and field precedence logic ensure accurate data comparison and meaningful migration recommendations. By following the patterns and best practices outlined in this documentation, organizations can effectively analyze their account data and plan successful migrations. 