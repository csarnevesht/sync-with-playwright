"""
Analysis Utilities

This module provides utilities for saving, loading, and managing account analysis reports.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import os

from ..models import AccountAnalysisReport, BatchAnalysisReport

logger = logging.getLogger(__name__)


class AnalysisReportManager:
    """Manager for saving and loading analysis reports."""
    
    def __init__(self, base_directory: str = "analysis_reports", log_directory: Optional[str] = None):
        """
        Initialize the report manager.
        
        Args:
            base_directory: Base directory for storing reports (used when log_directory is None)
            log_directory: Optional log directory to save reports in (overrides base_directory)
        """
        if log_directory:
            self.base_directory = Path(log_directory)
        else:
            self.base_directory = Path(base_directory)
        self.base_directory.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def save_account_report(self, report: AccountAnalysisReport, 
                          format: str = "json") -> str:
        """
        Save an account analysis report to disk.
        
        Args:
            report: The account analysis report to save
            format: Output format ("json", "txt", or "both")
            
        Returns:
            Path to the saved report file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        account_name = report.dropbox_account_folder.replace(" ", "_").replace(",", "")
        
        if format in ["json", "both"]:
            json_path = self.base_directory / f"account_analysis_{account_name}_{timestamp}.json"
            with open(json_path, 'w') as f:
                json.dump(report.model_dump(), f, indent=2, default=str)
            self.logger.info(f"Saved JSON report: {json_path}")
        
        if format in ["txt", "both"]:
            txt_path = self.base_directory / f"account_analysis_{account_name}_{timestamp}.txt"
            self._save_text_report(report, txt_path)
            self.logger.info(f"Saved text report: {txt_path}")
        
        return str(json_path if format == "json" else txt_path)
    
    def save_batch_report(self, report: BatchAnalysisReport, 
                         format: str = "json") -> str:
        """
        Save a batch analysis report to disk.
        
        Args:
            report: The batch analysis report to save
            format: Output format ("json", "txt", or "both")
            
        Returns:
            Path to the saved report file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_id = report.batch_id.replace(" ", "_").replace(",", "")
        
        if format in ["json", "both"]:
            json_path = self.base_directory / f"batch_analysis_{batch_id}_{timestamp}.json"
            with open(json_path, 'w') as f:
                json.dump(report.model_dump(), f, indent=2, default=str)
            self.logger.info(f"Saved batch JSON report: {json_path}")
        
        if format in ["txt", "both"]:
            txt_path = self.base_directory / f"batch_analysis_{batch_id}_{timestamp}.txt"
            self._save_batch_text_report(report, txt_path)
            self.logger.info(f"Saved batch text report: {txt_path}")
        
        return str(json_path if format == "json" else txt_path)
    
    def load_account_report(self, file_path: str) -> Optional[AccountAnalysisReport]:
        """
        Load an account analysis report from disk.
        
        Args:
            file_path: Path to the report file
            
        Returns:
            AccountAnalysisReport if successful, None otherwise
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return AccountAnalysisReport(**data)
        except Exception as e:
            self.logger.error(f"Error loading account report {file_path}: {str(e)}")
            return None
    
    def load_batch_report(self, file_path: str) -> Optional[BatchAnalysisReport]:
        """
        Load a batch analysis report from disk.
        
        Args:
            file_path: Path to the report file
            
        Returns:
            BatchAnalysisReport if successful, None otherwise
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return BatchAnalysisReport(**data)
        except Exception as e:
            self.logger.error(f"Error loading batch report {file_path}: {str(e)}")
            return None
    
    def list_reports(self, report_type: str = "all") -> List[Dict[str, Any]]:
        """
        List available reports.
        
        Args:
            report_type: Type of reports to list ("account", "batch", or "all")
            
        Returns:
            List of report information dictionaries
        """
        reports = []
        
        for file_path in self.base_directory.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                report_info = {
                    'file_path': str(file_path),
                    'file_name': file_path.name,
                    'file_size': file_path.stat().st_size,
                    'modified_time': datetime.fromtimestamp(file_path.stat().st_mtime),
                    'report_type': 'account' if 'account_analysis' in file_path.name else 'batch'
                }
                
                # Add report-specific information
                if report_info['report_type'] == 'account':
                    report_info['account_name'] = data.get('dropbox_account_folder', 'Unknown')
                    report_info['total_migrations'] = data.get('total_migrations_needed', 0)
                else:
                    report_info['batch_id'] = data.get('batch_id', 'Unknown')
                    report_info['total_accounts'] = data.get('total_accounts_processed', 0)
                
                if report_type == "all" or report_info['report_type'] == report_type:
                    reports.append(report_info)
                    
            except Exception as e:
                self.logger.warning(f"Error reading report {file_path}: {str(e)}")
        
        # Sort by modified time (newest first)
        reports.sort(key=lambda x: x['modified_time'], reverse=True)
        
        return reports
    
    def _save_text_report(self, report: AccountAnalysisReport, file_path: Path) -> None:
        """Save a text version of the account analysis report."""
        lines = []
        
        # Header
        lines.append("="*80)
        lines.append("ACCOUNT ANALYSIS REPORT")
        lines.append("="*80)
        lines.append(f"Account: {report.dropbox_account_folder}")
        lines.append(f"Analysis Date: {report.analysis_timestamp}")
        lines.append("")
        
        # Summary
        lines.append("SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Total Accounts: {report.total_accounts_found}")
        lines.append(f"Total Migrations Needed: {report.total_migrations_needed}")
        lines.append(f"Data Completeness: {report.data_quality.data_completeness_score:.1%}")
        lines.append(f"Data Consistency: {report.data_quality.data_consistency_score:.1%}")
        lines.append("")
        
        # Account comparisons
        if report.account_comparisons:
            lines.append("ACCOUNT COMPARISONS")
            lines.append("-" * 40)
            for comparison in report.account_comparisons:
                lines.append(f"\n{comparison.account_name}")
                lines.append(f"  Type: {comparison.account_type}")
                lines.append(f"  Role: {comparison.role or 'N/A'}")
                lines.append(f"  Migration Needed: {comparison.migration_needed}")
                if comparison.migration_needed:
                    lines.append(f"  Priority: {comparison.migration_priority}")
                
                # Field issues
                issues = []
                for field_name in ['first_name', 'last_name', 'email', 'phone', 'address', 'birthdate', 'gender']:
                    field_comparison = getattr(comparison, field_name)
                    if field_comparison.status != 'present':
                        issues.append(f"{field_name}: {field_comparison.status}")
                
                if issues:
                    lines.append(f"  Issues: {', '.join(issues)}")
        
        # Migration plans
        if report.migration_plans:
            lines.append("\nMIGRATION PLANS")
            lines.append("-" * 40)
            for plan in report.migration_plans:
                lines.append(f"\n{plan.account_name}")
                lines.append(f"  Type: {plan.migration_type}")
                lines.append(f"  Priority: {plan.priority}")
                lines.append(f"  Effort: {plan.estimated_effort}")
                
                if plan.fields_to_create:
                    lines.append(f"  Create: {', '.join(plan.fields_to_create)}")
                if plan.fields_to_update:
                    lines.append(f"  Update: {', '.join(plan.fields_to_update)}")
                if plan.fields_to_merge:
                    lines.append(f"  Merge: {', '.join(plan.fields_to_merge)}")
        
        # Recommendations
        if report.recommendations:
            lines.append("\nRECOMMENDATIONS")
            lines.append("-" * 40)
            for i, rec in enumerate(report.recommendations, 1):
                lines.append(f"{i}. {rec}")
        
        # Warnings
        if report.warnings:
            lines.append("\nWARNINGS")
            lines.append("-" * 40)
            for i, warning in enumerate(report.warnings, 1):
                lines.append(f"{i}. {warning}")
        
        # Write to file
        with open(file_path, 'w') as f:
            f.write('\n'.join(lines))
    
    def _save_batch_text_report(self, report: BatchAnalysisReport, file_path: Path) -> None:
        """Save a text version of the batch analysis report."""
        lines = []
        
        # Header
        lines.append("="*80)
        lines.append("BATCH ANALYSIS REPORT")
        lines.append("="*80)
        lines.append(f"Batch ID: {report.batch_id}")
        lines.append(f"Analysis Date: {report.analysis_timestamp}")
        lines.append("")
        
        # Summary
        lines.append("SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Total Accounts Processed: {report.total_accounts_processed}")
        lines.append(f"Successful Analyses: {report.successful_analyses}")
        lines.append(f"Failed Analyses: {report.failed_analyses}")
        lines.append(f"Total Migrations Needed: {report.total_migrations_needed}")
        lines.append("")
        
        # Migration breakdown
        lines.append("MIGRATION BREAKDOWN")
        lines.append("-" * 40)
        lines.append(f"High Priority: {report.high_priority_migrations}")
        lines.append(f"Medium Priority: {report.medium_priority_migrations}")
        lines.append(f"Low Priority: {report.low_priority_migrations}")
        lines.append("")
        
        # Individual account summaries
        if report.account_reports:
            lines.append("INDIVIDUAL ACCOUNT SUMMARIES")
            lines.append("-" * 40)
            for account_report in report.account_reports:
                lines.append(f"\n{account_report.dropbox_account_folder}")
                lines.append(f"  Migrations Needed: {account_report.total_migrations_needed}")
                lines.append(f"  Data Completeness: {account_report.data_quality.data_completeness_score:.1%}")
                lines.append(f"  Data Consistency: {account_report.data_quality.data_consistency_score:.1%}")
        
        # Batch recommendations
        if report.batch_recommendations:
            lines.append("\nBATCH RECOMMENDATIONS")
            lines.append("-" * 40)
            for i, rec in enumerate(report.batch_recommendations, 1):
                lines.append(f"{i}. {rec}")
        
        # Batch warnings
        if report.batch_warnings:
            lines.append("\nBATCH WARNINGS")
            lines.append("-" * 40)
            for i, warning in enumerate(report.batch_warnings, 1):
                lines.append(f"{i}. {warning}")
        
        # Write to file
        with open(file_path, 'w') as f:
            f.write('\n'.join(lines))


def create_batch_analysis_report(account_reports: List[AccountAnalysisReport], 
                                batch_id: str) -> BatchAnalysisReport:
    """
    Create a batch analysis report from multiple account reports.
    
    Args:
        account_reports: List of account analysis reports
        batch_id: Unique identifier for the batch
        
    Returns:
        BatchAnalysisReport with aggregated information
    """
    total_accounts = len(account_reports)
    successful_analyses = len([r for r in account_reports if not r.errors])
    failed_analyses = total_accounts - successful_analyses
    
    total_migrations = sum(r.total_migrations_needed for r in account_reports)
    high_priority = sum(1 for r in account_reports 
                       for p in r.migration_plans if p.priority == 'high')
    medium_priority = sum(1 for r in account_reports 
                         for p in r.migration_plans if p.priority == 'medium')
    low_priority = sum(1 for r in account_reports 
                      for p in r.migration_plans if p.priority == 'low')
    
    # Aggregate recommendations and warnings
    all_recommendations = []
    all_warnings = []
    all_errors = []
    
    for report in account_reports:
        all_recommendations.extend(report.recommendations)
        all_warnings.extend(report.warnings)
        all_errors.extend(report.errors)
    
    # Remove duplicates while preserving order
    batch_recommendations = list(dict.fromkeys(all_recommendations))
    batch_warnings = list(dict.fromkeys(all_warnings))
    batch_errors = list(dict.fromkeys(all_errors))
    
    return BatchAnalysisReport(
        batch_id=batch_id,
        total_accounts_processed=total_accounts,
        successful_analyses=successful_analyses,
        failed_analyses=failed_analyses,
        account_reports=account_reports,
        total_migrations_needed=total_migrations,
        high_priority_migrations=high_priority,
        medium_priority_migrations=medium_priority,
        low_priority_migrations=low_priority,
        batch_recommendations=batch_recommendations,
        batch_warnings=batch_warnings,
        batch_errors=batch_errors
    )


def export_analysis_to_csv(report: AccountAnalysisReport, output_path: str) -> str:
    """
    Export analysis results to CSV format.
    
    Args:
        report: Account analysis report
        output_path: Path for the CSV file
        
    Returns:
        Path to the created CSV file
    """
    import csv
    
    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow([
            'Account Name', 'Account Type', 'Role', 'Migration Needed', 'Priority',
            'First Name Status', 'Last Name Status', 'Email Status', 'Phone Status',
            'Address Status', 'Birthdate Status', 'Gender Status'
        ])
        
        # Write data
        for comparison in report.account_comparisons:
            writer.writerow([
                comparison.account_name,
                comparison.account_type,
                comparison.role or 'N/A',
                comparison.migration_needed,
                comparison.migration_priority,
                comparison.first_name.status,
                comparison.last_name.status,
                comparison.email.status,
                comparison.phone.status,
                comparison.address.status,
                comparison.birthdate.status,
                comparison.gender.status
            ])
    
    return output_path 