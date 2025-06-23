"""
Example Usage of Account Analysis System

This script demonstrates how to use the new account analysis system
to compare Salesforce and Dropbox account information and generate
comprehensive reports for migration planning.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from ..analyzers.account_analyzer import AccountAnalyzer
from ..utils.analysis_utils import AnalysisReportManager, create_batch_analysis_report, export_analysis_to_csv
from ..models import AccountAnalysisReport

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def example_single_account_analysis():
    """Example of analyzing a single account."""
    
    logger.info("🔍 === EXAMPLE: SINGLE ACCOUNT ANALYSIS ===")
    
    # Initialize the analyzer
    analyzer = AccountAnalyzer()
    
    # Example Salesforce account information (based on the log data)
    salesforce_account_information = {
        'names_found': ['Maria Montesino', 'Maria Montesino Household'],
        'household': {
            'account_name': 'Maria Montesino Household',
            'type': 'Household',
            'role': None,
            'stage': 'Client',
            'email': 'jackaron2014@outlook.com',
            'phone': '786-282-4047',
            'mailing_address': '920 NE 199 ST. Apt. 417\nMiami, FL. 33179',
            'ssn/tax_id': '770-20-3101',
            'relationships': []
        },
        'head': {
            'account_name': 'Maria Montesino',
            'type': 'Contact',
            'role': 'Household Head',
            'stage': 'Client',
            'email': 'jackaron2014@outlook.com',
            'phone': '786-282-4047',
            'mailing_address': '920 NE 199 ST. Apt. 417\nMiami, FL. 33179',
            'ssn/tax_id': '770-20-3101',
            'relationships': []
        },
        'members': [],
        'accounts': [
            {
                'account_name': 'Maria Montesino',
                'type': 'Contact',
                'role': 'Household Head',
                'stage': 'Client',
                'email': 'jackaron2014@outlook.com',
                'phone': '786-282-4047',
                'mailing_address': '920 NE 199 ST. Apt. 417\nMiami, FL. 33179',
                'ssn/tax_id': '770-20-3101',
                'relationships': []
            },
            {
                'account_name': 'Maria Montesino Household',
                'type': 'Household',
                'role': None,
                'stage': 'Client',
                'email': 'jackaron2014@outlook.com',
                'phone': '786-282-4047',
                'mailing_address': '920 NE 199 ST. Apt. 417\nMiami, FL. 33179',
                'ssn/tax_id': '770-20-3101',
                'relationships': []
            }
        ]
    }
    
    # Example Dropbox account information (based on the log data)
    dropbox_account_information = {
        'names_found': ['Montesino, Maria'],
        'client_list_data': {
            'account_data': {
                'first_name': 'Maria',
                'last_name': 'Montesino',
                'phone': '786-282-4047',
                'address': '920 NE 199 ST. Apt. 417',
                'email': 'jackaron2014@outlook.com'
            },
            'search_info': {
                'match_info': {
                    'match_status': 'Match found'
                }
            }
        },
        'application_data': {
            'best_available_info': {
                'owner': {
                    'firstName': 'Maria',
                    'lastName': 'Montesino',
                    'dateOfBirth': '1/2/1953',
                    'gender': 'Male',
                    'phoneNumber': '(786) 2-82-404',
                    'emailAddress': 'jackaron2014@outlook.com',
                    'mailingAddressStreet': '920 NE 199 St. Apt. 417',
                    'mailingAddressCity': 'Miami',
                    'mailingAddressState': 'FL',
                    'mailingAddressZip': '33179'
                }
            }
        },
        'accounts': [
            {
                'account_name': 'Montesino, Maria',
                'source': 'client_list_file',
                'account_type': 'Primary',
                'first_name': 'Maria',
                'last_name': 'Montesino',
                'phone': '786-282-4047',
                'address': '920 NE 199 ST. Apt. 417',
                'email': 'jackaron2014@outlook.com',
                'match_status': 'Match found'
            },
            {
                'account_name': 'Maria Montesino',
                'source': 'application_files',
                'account_type': 'Primary',
                'first_name': 'Maria',
                'last_name': 'Montesino',
                'birthdate': '1/2/1953',
                'gender': 'Male',
                'phone': '(786) 2-82-404',
                'address': '920 NE 199 St. Apt. 417, Miami, FL, 33179',
                'email': 'jackaron2014@outlook.com'
            }
        ]
    }
    
    # Perform the analysis
    analysis_report = analyzer.analyze_account(
        dropbox_account_folder="Montesino, Maria",
        salesforce_account_information=salesforce_account_information,
        dropbox_account_information=dropbox_account_information
    )
    
    # Display key results
    logger.info(f"📊 Analysis Results for: {analysis_report.dropbox_account_folder}")
    logger.info(f"📈 Total Accounts Found: {analysis_report.total_accounts_found}")
    logger.info(f"🔄 Total Migrations Needed: {analysis_report.total_migrations_needed}")
    logger.info(f"📊 Data Completeness: {analysis_report.data_quality.data_completeness_score:.1%}")
    logger.info(f"📊 Data Consistency: {analysis_report.data_quality.data_consistency_score:.1%}")
    
    # Show account comparisons
    for comparison in analysis_report.account_comparisons:
        logger.info(f"\n👤 Account: {comparison.account_name}")
        logger.info(f"   Type: {comparison.account_type}")
        logger.info(f"   Migration Needed: {comparison.migration_needed}")
        if comparison.migration_needed:
            logger.info(f"   Priority: {comparison.migration_priority}")
            
            # Show field issues
            issues = []
            for field_name in ['first_name', 'last_name', 'email', 'phone', 'address', 'birthdate', 'gender']:
                field_comparison = getattr(comparison, field_name)
                if field_comparison.status != 'present':
                    issues.append(f"{field_name}: {field_comparison.status}")
            
            if issues:
                logger.info(f"   Issues: {', '.join(issues)}")
    
    # Show migration plans
    if analysis_report.migration_plans:
        logger.info(f"\n🔄 Migration Plans ({len(analysis_report.migration_plans)}):")
        for plan in analysis_report.migration_plans:
            logger.info(f"   📋 {plan.account_name}: {plan.migration_type} ({plan.priority})")
            if plan.fields_to_create:
                logger.info(f"      Create: {', '.join(plan.fields_to_create)}")
            if plan.fields_to_update:
                logger.info(f"      Update: {', '.join(plan.fields_to_update)}")
    
    # Show recommendations
    if analysis_report.recommendations:
        logger.info(f"\n💡 Recommendations:")
        for i, rec in enumerate(analysis_report.recommendations, 1):
            logger.info(f"   {i}. {rec}")
    
    return analysis_report


def example_batch_analysis():
    """Example of batch analysis with multiple accounts."""
    
    logger.info("\n🔍 === EXAMPLE: BATCH ANALYSIS ===")
    
    # Initialize the analyzer and report manager
    analyzer = AccountAnalyzer()
    report_manager = AnalysisReportManager()
    
    # Example accounts to analyze
    example_accounts = [
        {
            'name': 'Montesino, Maria',
            'salesforce_data': {
                'names_found': ['Maria Montesino', 'Maria Montesino Household'],
                'accounts': [
                    {
                        'account_name': 'Maria Montesino',
                        'type': 'Contact',
                        'role': 'Household Head',
                        'stage': 'Client',
                        'email': 'jackaron2014@outlook.com',
                        'phone': '786-282-4047',
                        'mailing_address': '920 NE 199 ST. Apt. 417\nMiami, FL. 33179',
                        'ssn/tax_id': '770-20-3101'
                    }
                ]
            },
            'dropbox_data': {
                'names_found': ['Montesino, Maria'],
                'accounts': [
                    {
                        'account_name': 'Maria Montesino',
                        'source': 'application_files',
                        'account_type': 'Primary',
                        'first_name': 'Maria',
                        'last_name': 'Montesino',
                        'birthdate': '1/2/1953',
                        'gender': 'Male',
                        'phone': '(786) 2-82-404',
                        'address': '920 NE 199 St. Apt. 417, Miami, FL, 33179',
                        'email': 'jackaron2014@outlook.com'
                    }
                ]
            }
        },
        {
            'name': 'Smith, John',
            'salesforce_data': {
                'names_found': ['John Smith'],
                'accounts': [
                    {
                        'account_name': 'John Smith',
                        'type': 'Contact',
                        'role': 'Household Head',
                        'stage': 'Client',
                        'email': 'john.smith@example.com',
                        'phone': '555-123-4567',
                        'mailing_address': '123 Main St\nAnytown, ST 12345'
                    }
                ]
            },
            'dropbox_data': {
                'names_found': ['Smith, John'],
                'accounts': [
                    {
                        'account_name': 'John Smith',
                        'source': 'application_files',
                        'account_type': 'Primary',
                        'first_name': 'John',
                        'last_name': 'Smith',
                        'birthdate': '01/15/1980',
                        'gender': 'Male',
                        'phone': '555-123-4567',
                        'address': '123 Main St, Anytown, ST, 12345',
                        'email': 'john.smith@example.com'
                    }
                ]
            }
        }
    ]
    
    # Analyze each account
    account_reports = []
    for account_info in example_accounts:
        logger.info(f"📁 Analyzing: {account_info['name']}")
        
        try:
            analysis_report = analyzer.analyze_account(
                dropbox_account_folder=account_info['name'],
                salesforce_account_information=account_info['salesforce_data'],
                dropbox_account_information=account_info['dropbox_data']
            )
            account_reports.append(analysis_report)
            
            # Save individual report
            report_path = report_manager.save_account_report(analysis_report, format="both")
            logger.info(f"   ✅ Saved report: {report_path}")
            
        except Exception as e:
            logger.error(f"   ❌ Error analyzing {account_info['name']}: {str(e)}")
    
    # Create batch report
    batch_report = create_batch_analysis_report(account_reports, "example_batch_20241201")
    
    # Save batch report
    batch_path = report_manager.save_batch_report(batch_report, format="both")
    logger.info(f"📊 Saved batch report: {batch_path}")
    
    # Display batch summary
    logger.info(f"\n📈 Batch Analysis Summary:")
    logger.info(f"   Total Accounts: {batch_report.total_accounts_processed}")
    logger.info(f"   Successful: {batch_report.successful_analyses}")
    logger.info(f"   Failed: {batch_report.failed_analyses}")
    logger.info(f"   Total Migrations: {batch_report.total_migrations_needed}")
    logger.info(f"   High Priority: {batch_report.high_priority_migrations}")
    logger.info(f"   Medium Priority: {batch_report.medium_priority_migrations}")
    logger.info(f"   Low Priority: {batch_report.low_priority_migrations}")
    
    return batch_report


def example_report_management():
    """Example of managing and querying saved reports."""
    
    logger.info("\n🔍 === EXAMPLE: REPORT MANAGEMENT ===")
    
    # Initialize report manager
    report_manager = AnalysisReportManager()
    
    # List all reports
    reports = report_manager.list_reports()
    logger.info(f"📋 Found {len(reports)} reports:")
    
    for report in reports[:5]:  # Show first 5
        logger.info(f"   📄 {report['file_name']}")
        logger.info(f"      Type: {report['report_type']}")
        logger.info(f"      Size: {report['file_size']} bytes")
        logger.info(f"      Modified: {report['modified_time']}")
        
        if report['report_type'] == 'account':
            logger.info(f"      Account: {report.get('account_name', 'Unknown')}")
            logger.info(f"      Migrations: {report.get('total_migrations', 0)}")
        else:
            logger.info(f"      Batch ID: {report.get('batch_id', 'Unknown')}")
            logger.info(f"      Accounts: {report.get('total_accounts', 0)}")
    
    # Load a specific report (if available)
    if reports:
        first_report = reports[0]
        logger.info(f"\n📖 Loading report: {first_report['file_name']}")
        
        if first_report['report_type'] == 'account':
            loaded_report = report_manager.load_account_report(first_report['file_path'])
            if loaded_report:
                logger.info(f"   ✅ Loaded account report for: {loaded_report.dropbox_account_folder}")
                logger.info(f"   📊 Migrations needed: {loaded_report.total_migrations_needed}")
        else:
            loaded_report = report_manager.load_batch_report(first_report['file_path'])
            if loaded_report:
                logger.info(f"   ✅ Loaded batch report: {loaded_report.batch_id}")
                logger.info(f"   📊 Total accounts: {loaded_report.total_accounts_processed}")


def example_csv_export():
    """Example of exporting analysis results to CSV."""
    
    logger.info("\n🔍 === EXAMPLE: CSV EXPORT ===")
    
    # Get a sample analysis report
    analysis_report = example_single_account_analysis()
    
    # Export to CSV
    csv_path = export_analysis_to_csv(analysis_report, "example_analysis_export.csv")
    logger.info(f"📊 Exported analysis to CSV: {csv_path}")
    
    # Display CSV content preview
    import csv
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)
        
        logger.info(f"📋 CSV Preview ({len(rows)} rows):")
        for i, row in enumerate(rows[:3]):  # Show first 3 rows
            logger.info(f"   Row {i+1}: {row}")


def main():
    """Main function to run all examples."""
    
    logger.info("🚀 === ACCOUNT ANALYSIS SYSTEM EXAMPLES ===")
    logger.info("This demonstrates the comprehensive account analysis system")
    logger.info("for comparing Salesforce and Dropbox account information.")
    
    try:
        # Run examples
        example_single_account_analysis()
        example_batch_analysis()
        example_report_management()
        example_csv_export()
        
        logger.info("\n✅ All examples completed successfully!")
        logger.info("\n📚 Key Features Demonstrated:")
        logger.info("   • Single account analysis with detailed field comparison")
        logger.info("   • Batch analysis for multiple accounts")
        logger.info("   • Data quality assessment and scoring")
        logger.info("   • Migration planning with priorities")
        logger.info("   • Report generation in multiple formats")
        logger.info("   • Report management and querying")
        logger.info("   • CSV export for further analysis")
        
    except Exception as e:
        logger.error(f"❌ Error running examples: {str(e)}")
        raise


if __name__ == "__main__":
    main() 