"""
Test Account Analysis System

This test file verifies that the account analysis system works correctly
with the existing Salesforce and Dropbox data structures.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, MagicMock

from sync.analyzers.account_analyzer import AccountAnalyzer
from sync.models import (
    AccountAnalysisReport, AccountComparison, FieldComparison,
    FieldStatus, MigrationPriority, DataSource, AccountType, AccountRole
)
from sync.utils.analysis_utils import AnalysisReportManager, create_batch_analysis_report


class TestAccountAnalyzer:
    """Test the AccountAnalyzer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = AccountAnalyzer()
        
        # Sample Salesforce data based on the log
        self.sample_salesforce_data = {
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
        
        # Sample Dropbox data based on the log
        self.sample_dropbox_data = {
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
    
    def test_analyze_account_basic(self):
        """Test basic account analysis functionality."""
        
        # Perform analysis
        report = self.analyzer.analyze_account(
            dropbox_account_folder="Montesino, Maria",
            salesforce_account_information=self.sample_salesforce_data,
            dropbox_account_information=self.sample_dropbox_data
        )
        
        # Verify basic structure
        assert isinstance(report, AccountAnalysisReport)
        assert report.dropbox_account_folder == "Montesino, Maria"
        assert report.analysis_timestamp is not None
        assert report.total_accounts_found > 0
        assert report.data_quality is not None
        
        # Verify data quality metrics
        assert 0.0 <= report.data_quality.data_completeness_score <= 1.0
        assert 0.0 <= report.data_quality.data_consistency_score <= 1.0
        assert report.data_quality.total_fields_compared > 0
    
    def test_field_comparison(self):
        """Test field comparison functionality."""
        
        report = self.analyzer.analyze_account(
            dropbox_account_folder="Montesino, Maria",
            salesforce_account_information=self.sample_salesforce_data,
            dropbox_account_information=self.sample_dropbox_data
        )
        
        # Check that we have account comparisons
        assert len(report.account_comparisons) > 0
        
        # Check field comparisons for the first account
        comparison = report.account_comparisons[0]
        assert isinstance(comparison, AccountComparison)
        
        # Verify field comparison structure
        for field_name in ['first_name', 'last_name', 'email', 'phone', 'address', 'birthdate', 'gender']:
            field_comparison = getattr(comparison, field_name)
            assert isinstance(field_comparison, FieldComparison)
            assert field_comparison.field_name == field_name
            assert field_comparison.status in [FieldStatus.PRESENT, FieldStatus.MISSING, FieldStatus.DIFFERENT, FieldStatus.PARTIAL]
            assert field_comparison.migration_priority in [MigrationPriority.HIGH, MigrationPriority.MEDIUM, MigrationPriority.LOW, MigrationPriority.NOT_NEEDED]
    
    def test_migration_plan_generation(self):
        """Test migration plan generation."""
        
        report = self.analyzer.analyze_account(
            dropbox_account_folder="Montesino, Maria",
            salesforce_account_information=self.sample_salesforce_data,
            dropbox_account_information=self.sample_dropbox_data
        )
        
        # Check that migration plans are generated
        assert isinstance(report.migration_plans, list)
        
        # If there are migration plans, verify their structure
        for plan in report.migration_plans:
            assert plan.account_name is not None
            assert plan.migration_type in ['create', 'update', 'merge']
            assert plan.priority in [MigrationPriority.HIGH, MigrationPriority.MEDIUM, MigrationPriority.LOW]
            assert plan.estimated_effort in ['low', 'medium', 'high']
            assert isinstance(plan.fields_to_create, list)
            assert isinstance(plan.fields_to_update, list)
            assert isinstance(plan.fields_to_merge, list)
    
    def test_household_analysis(self):
        """Test household structure analysis."""
        
        report = self.analyzer.analyze_account(
            dropbox_account_folder="Montesino, Maria",
            salesforce_account_information=self.sample_salesforce_data,
            dropbox_account_information=self.sample_dropbox_data
        )
        
        # Check household comparison
        if report.household_comparison:
            household = report.household_comparison
            assert household.household_name is not None
            assert isinstance(household.structure_match, bool)
            assert isinstance(household.missing_members, list)
            assert isinstance(household.extra_members, list)
            assert isinstance(household.migration_needed, bool)
    
    def test_recommendations_and_warnings(self):
        """Test that recommendations and warnings are generated."""
        
        report = self.analyzer.analyze_account(
            dropbox_account_folder="Montesino, Maria",
            salesforce_account_information=self.sample_salesforce_data,
            dropbox_account_information=self.sample_dropbox_data
        )
        
        # Check that recommendations and warnings are lists
        assert isinstance(report.recommendations, list)
        assert isinstance(report.warnings, list)
        assert isinstance(report.errors, list)
    
    def test_empty_data_handling(self):
        """Test handling of empty or missing data."""
        
        # Test with no Salesforce data
        report = self.analyzer.analyze_account(
            dropbox_account_folder="Test Account",
            salesforce_account_information=None,
            dropbox_account_information=self.sample_dropbox_data
        )
        
        assert report.total_accounts_missing_in_salesforce > 0
        
        # Test with no Dropbox data
        report = self.analyzer.analyze_account(
            dropbox_account_folder="Test Account",
            salesforce_account_information=self.sample_salesforce_data,
            dropbox_account_information=None
        )
        
        assert report.total_accounts_missing_in_dropbox > 0


class TestAnalysisReportManager:
    """Test the AnalysisReportManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.report_manager = AnalysisReportManager("test_reports")
        
        # Create a sample report
        self.sample_report = AccountAnalysisReport(
            dropbox_account_folder="Test Account",
            data_quality={
                'total_fields_compared': 10,
                'fields_present_in_salesforce': 8,
                'fields_present_in_dropbox': 7,
                'fields_missing_in_salesforce': 2,
                'fields_missing_in_dropbox': 3,
                'fields_different': 1,
                'data_completeness_score': 0.75,
                'data_consistency_score': 0.9
            },
            account_comparisons=[],
            migration_plans=[],
            recommendations=[],
            warnings=[],
            errors=[]
        )
    
    def test_save_and_load_account_report(self):
        """Test saving and loading account reports."""
        
        # Save report
        saved_path = self.report_manager.save_account_report(self.sample_report, format="json")
        assert saved_path is not None
        
        # Load report
        loaded_report = self.report_manager.load_account_report(saved_path)
        assert loaded_report is not None
        assert loaded_report.dropbox_account_folder == self.sample_report.dropbox_account_folder
        assert loaded_report.data_quality.data_completeness_score == self.sample_report.data_quality.data_completeness_score
    
    def test_list_reports(self):
        """Test listing available reports."""
        
        # Save a report first
        self.report_manager.save_account_report(self.sample_report, format="json")
        
        # List reports
        reports = self.report_manager.list_reports()
        assert isinstance(reports, list)
        
        if reports:
            report = reports[0]
            assert 'file_path' in report
            assert 'file_name' in report
            assert 'report_type' in report
            assert report['report_type'] == 'account'


class TestBatchAnalysis:
    """Test batch analysis functionality."""
    
    def test_create_batch_report(self):
        """Test creating batch analysis reports."""
        
        # Create sample account reports
        account_reports = []
        for i in range(3):
            report = AccountAnalysisReport(
                dropbox_account_folder=f"Account {i}",
                data_quality={
                    'total_fields_compared': 10,
                    'fields_present_in_salesforce': 8,
                    'fields_present_in_dropbox': 7,
                    'fields_missing_in_salesforce': 2,
                    'fields_missing_in_dropbox': 3,
                    'fields_different': 1,
                    'data_completeness_score': 0.75,
                    'data_consistency_score': 0.9
                },
                account_comparisons=[],
                migration_plans=[],
                recommendations=[f"Recommendation {i}"],
                warnings=[f"Warning {i}"],
                errors=[]
            )
            account_reports.append(report)
        
        # Create batch report
        batch_report = create_batch_analysis_report(account_reports, "test_batch")
        
        # Verify batch report structure
        assert batch_report.batch_id == "test_batch"
        assert batch_report.total_accounts_processed == 3
        assert batch_report.successful_analyses == 3
        assert batch_report.failed_analyses == 0
        assert len(batch_report.account_reports) == 3
        assert len(batch_report.batch_recommendations) == 3
        assert len(batch_report.batch_warnings) == 3


def test_field_mapping():
    """Test that field mappings are correctly defined."""
    
    analyzer = AccountAnalyzer()
    
    # Check that all required fields are mapped
    required_fields = ['first_name', 'last_name', 'middle_name', 'email', 'phone', 'address', 'birthdate', 'gender', 'ssn_tax_id']
    
    for field in required_fields:
        assert field in analyzer.field_mappings
        mapping = analyzer.field_mappings[field]
        assert 'salesforce' in mapping
        assert 'dropbox_client_list' in mapping
        assert 'dropbox_application_files' in mapping
    
    # Check that priorities are defined for all fields
    for field in required_fields:
        assert field in analyzer.field_priorities
        priority = analyzer.field_priorities[field]
        assert priority in [MigrationPriority.HIGH, MigrationPriority.MEDIUM, MigrationPriority.LOW]


def test_data_quality_calculation():
    """Test data quality calculation logic."""
    
    analyzer = AccountAnalyzer()
    
    # Test with sample data
    report = analyzer.analyze_account(
        dropbox_account_folder="Test Account",
        salesforce_account_information={
            'names_found': ['Test Account'],
            'accounts': [{
                'account_name': 'Test Account',
                'type': 'Contact',
                'email': 'test@example.com',
                'phone': '555-1234'
            }]
        },
        dropbox_account_information={
            'names_found': ['Test Account'],
            'accounts': [{
                'account_name': 'Test Account',
                'source': 'application_files',
                'account_type': 'Primary',
                'email': 'test@example.com',
                'phone': '555-1234'
            }]
        }
    )
    
    # Verify quality metrics are calculated
    assert report.data_quality.data_completeness_score > 0
    assert report.data_quality.data_consistency_score > 0
    assert report.data_quality.total_fields_compared > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 