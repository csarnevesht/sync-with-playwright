# Account Analysis System

## Overview

The Account Analysis System provides comprehensive tools for comparing Salesforce and Dropbox account information, identifying data gaps, inconsistencies, and generating detailed migration plans. This system is designed to help organizations understand what data is available in each system, what's missing, and what should be migrated from Dropbox to Salesforce.

## Key Features

- **Comprehensive Data Comparison**: Compare account information between Salesforce and Dropbox
- **Data Quality Assessment**: Calculate completeness and consistency scores
- **Migration Planning**: Generate prioritized migration plans with effort estimates
- **Household Structure Analysis**: Analyze household relationships and member structures
- **Multiple Report Formats**: Generate reports in JSON, text, and CSV formats
- **Batch Processing**: Analyze multiple accounts and generate batch reports
- **Report Management**: Save, load, and query analysis reports

## Architecture

### Core Components

1. **Models** (`src/sync/models.py`): Data structures for analysis reports and comparisons
2. **Account Analyzer** (`src/sync/analyzers/account_analyzer.py`): Main analysis engine
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

# Full pipeline with analysis
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

## Field Mapping

The system maps fields between Salesforce and Dropbox using the following structure:

| Field | Salesforce | Dropbox Client List | Dropbox Application Files |
|-------|------------|-------------------|---------------------------|
| first_name | first_name | first_name | firstName |
| last_name | last_name | last_name | lastName |
| middle_name | middle_name | middle_name | middleName |
| email | email | email | emailAddress |
| phone | phone | phone | phoneNumber |
| address | mailing_address | address | mailingAddressStreet |
| birthdate | birthdate | birthdate | dateOfBirth |
| gender | gender | gender | gender |
| ssn_tax_id | ssn/tax_id | ssn | ssn |

## Migration Priorities

Fields are assigned migration priorities based on business importance:

### High Priority
- **first_name**: Essential for identification
- **last_name**: Essential for identification  
- **email**: Critical for communication
- **ssn_tax_id**: Required for compliance

### Medium Priority
- **phone**: Important for communication
- **address**: Important for location data
- **birthdate**: Useful for demographics

### Low Priority
- **gender**: Nice to have
- **middle_name**: Nice to have

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
Human-readable summary with key findings:
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
Maria Montesino
  Type: Contact
  Role: Household Head
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
3. **Logging**: Integrates with existing logging system
4. **Error Handling**: Follows existing error handling patterns

### Command Line Usage

```bash
# Basic analysis
python -m sync.cmd_runner --commands=analyze-account-data --dropbox-account-name="Account Name"

# Full pipeline with analysis
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
- Validate data formats before analysis
- Handle missing or malformed data gracefully

### 2. Analysis Strategy
- Start with single account analysis to understand patterns
- Use batch analysis for large-scale assessments
- Review migration priorities based on business needs

### 3. Report Management
- Save reports in both JSON and text formats
- Use descriptive file names with timestamps
- Archive old reports for historical analysis

### 4. Migration Planning
- Prioritize high-priority migrations first
- Consider dependencies between accounts
- Validate data before migration

## Troubleshooting

### Common Issues

1. **Missing Data**: Check if account information flags are set
2. **Field Mapping Errors**: Verify field names in source data
3. **Report Generation Failures**: Ensure write permissions for output directory

### Debug Mode

Enable debug logging to see detailed analysis steps:
```python
import logging
logging.getLogger('sync.analyzers.account_analyzer').setLevel(logging.DEBUG)
```

## Future Enhancements

1. **Advanced Matching**: Fuzzy name matching for better account correlation
2. **Data Validation**: Built-in validation rules for common data formats
3. **Migration Automation**: Direct integration with migration tools
4. **Dashboard**: Web-based dashboard for analysis results
5. **Scheduling**: Automated analysis scheduling and reporting

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

The Account Analysis System provides a comprehensive solution for understanding data differences between Salesforce and Dropbox, enabling informed migration decisions and data quality improvements. By following the patterns and best practices outlined in this documentation, organizations can effectively analyze their account data and plan successful migrations. 