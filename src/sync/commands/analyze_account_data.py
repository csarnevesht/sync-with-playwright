print('[SCRIPT LOAD] analyze_account_data.py loaded')

"""
Analyze Account Data Command

This command provides comprehensive analysis of Salesforce and Dropbox account information,
comparing data between sources, identifying gaps, and generating migration plans.
"""

import json
import logging
import os
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime

from ..analyzers.account_analyzer import AccountAnalyzer
from ..models import AccountAnalysisReport, BatchAnalysisReport

logger = logging.getLogger(__name__)


def analyze_account_data(command_runner) -> Dict[str, Any]:
    """
    Analyze account data by comparing Salesforce and Dropbox information.
    
    This command:
    1. Retrieves Salesforce and Dropbox account information from the command runner
    2. Performs comprehensive analysis comparing data between sources
    3. Identifies data gaps, inconsistencies, and migration needs
    4. Generates detailed reports with recommendations
    5. Creates migration plans for data synchronization
    6. Automatically generates a beautiful summary report
    
    Args:
        command_runner: The command runner instance with access to data
        
    Returns:
        Dict containing the analysis results and reports
    """
    
    logger.info("🎯 === STARTING ACCOUNT DATA ANALYSIS ===")
    
    # Initialize the analyzer
    analyzer = AccountAnalyzer()
    
    # Get account information from command runner
    salesforce_account_information = command_runner.get_data('salesforce_account_information')
    dropbox_account_information = command_runner.get_data('dropbox_account_information')
    dropbox_account_folder_name = command_runner.get_data('dropbox_account_folder_name')
    
    if not dropbox_account_folder_name:
        logger.error("No dropbox_account_folder_name found in command runner data")
        return {
            'status': 'error',
            'message': 'No dropbox account folder name available'
        }
    
    logger.info(f"📁 Analyzing account: {dropbox_account_folder_name}")
    
    # Perform the analysis
    try:
        analysis_report = analyzer.analyze_account(
            dropbox_account_folder=dropbox_account_folder_name,
            salesforce_account_information=salesforce_account_information,
            dropbox_account_information=dropbox_account_information
        )
        
        # Log the analysis results
        _log_analysis_results(analysis_report)
        
        # Generate detailed reports
        reports = _generate_detailed_reports(analysis_report)
        
        # Generate beautiful comprehensive summary and write to summary.log
        beautiful_summary = _generate_beautiful_summary(analysis_report)
        _write_summary_to_log(beautiful_summary, command_runner)
        
        # Store the analysis report in command runner data
        command_runner.set_data('account_analysis_report', analysis_report.model_dump())
        
        logger.info("✅ Account data analysis completed successfully")
        
        return {
            'status': 'success',
            'analysis_report': analysis_report.model_dump(),
            'reports': reports,
            'message': f"Successfully analyzed {dropbox_account_folder_name} with {analysis_report.total_migrations_needed} migrations needed"
        }
        
    except Exception as e:
        logger.error(f"❌ Error during account analysis: {str(e)}")
        return {
            'status': 'error',
            'message': f'Analysis failed: {str(e)}'
        }


def _write_summary_to_log(beautiful_summary: str, command_runner) -> None:
    """Append the beautiful summary to the end of the summary.log file, after all logger output."""
    try:
        # Get the summary log file path from the command runner
        summary_log_path = None
        
        # Try to get the log directory from command runner
        if hasattr(command_runner, 'log_dir') and command_runner.log_dir:
            summary_log_path = os.path.join(command_runner.log_dir, 'summary.log')
        elif hasattr(command_runner, 'summary_log_path') and command_runner.summary_log_path:
            summary_log_path = command_runner.summary_log_path
        elif hasattr(command_runner, 'summary_logger') and hasattr(command_runner.summary_logger, 'handlers'):
            # Try to get the file path from the logger handler
            for handler in command_runner.summary_logger.handlers:
                if hasattr(handler, 'baseFilename'):
                    summary_log_path = handler.baseFilename
                    break
        
        # If still no path found, try to find the most recent summary.log in logs directory
        if not summary_log_path:
            logs_dir = 'logs'
            if os.path.exists(logs_dir):
                # Find the most recent log directory
                log_dirs = [d for d in os.listdir(logs_dir) if os.path.isdir(os.path.join(logs_dir, d))]
                if log_dirs:
                    # Sort by creation time (most recent first)
                    log_dirs.sort(key=lambda x: os.path.getctime(os.path.join(logs_dir, x)), reverse=True)
                    latest_log_dir = log_dirs[0]
                    summary_log_path = os.path.join(logs_dir, latest_log_dir, 'summary.log')
        
        if summary_log_path and os.path.exists(summary_log_path):
            separator = "\n" + "="*80 + "\n"
            separator += "🎯 ACCOUNT ANALYSIS SUMMARY REPORT\n"
            separator += "="*80 + "\n"
            with open(summary_log_path, "a", encoding="utf-8") as f:
                f.write(separator + beautiful_summary + "\n")
            logger.info(f"✅ Beautiful analysis summary appended to end of {summary_log_path}")
        else:
            logger.warning(f"⚠️ Could not determine summary.log file path, beautiful summary not appended. Tried: {summary_log_path}")
    except Exception as e:
        logger.error(f"❌ Error writing beautiful summary to log: {str(e)}")


def _generate_beautiful_summary(report: AccountAnalysisReport) -> str:
    """Generate a beautiful, comprehensive analysis summary."""
    
    # Extract account names for better display
    primary_account_name = report.dropbox_account_folder.split(', ')[-1] if ', ' in report.dropbox_account_folder else report.dropbox_account_folder
    
    # Get the full name for display (first and last name)
    full_display_name = report.dropbox_account_folder
    if ', ' in report.dropbox_account_folder:
        # If it's in "Last, First" format, convert to "First Last"
        parts = report.dropbox_account_folder.split(', ')
        if len(parts) >= 2:
            full_display_name = f"{parts[1]} {parts[0]}"
    
    # Calculate box width and spacing
    box_width = 70  # Total width of the box
    name_line_width = box_width - 2  # Width available for content (minus the side bars)
    
    # Center the name in the available space
    name_padding = max(0, (name_line_width - len(full_display_name)) // 2)
    name_line = " " * name_line_width
    name_line = name_line[:name_padding] + full_display_name + name_line[name_padding + len(full_display_name):]
    
    # Format timestamp to fit in the box
    timestamp = datetime.now().strftime('%B %d, %Y %H:%M:%S')
    if len(timestamp) > name_line_width:
        timestamp = datetime.now().strftime('%b %d, %Y %H:%M')
    
    # Center the timestamp in the available space
    timestamp_padding = max(0, (name_line_width - len(timestamp)) // 2)
    timestamp_line = " " * name_line_width
    timestamp_line = timestamp_line[:timestamp_padding] + timestamp + timestamp_line[timestamp_padding + len(timestamp):]
    
    # Get household name
    household_name = "Unknown Household"
    if report.household_comparison and report.household_comparison.household_name:
        household_name = report.household_comparison.household_name
    
    # Calculate data quality percentage
    completeness_percentage = report.data_quality.data_completeness_score * 100
    consistency_percentage = report.data_quality.data_consistency_score * 100
    
    # Determine data quality status
    if completeness_percentage >= 80:
        quality_status = "Excellent"
    elif completeness_percentage >= 60:
        quality_status = "Good"
    elif completeness_percentage >= 40:
        quality_status = "Fair"
    elif completeness_percentage >= 20:
        quality_status = "Poor"
    else:
        quality_status = "Very Poor"
    
    # Generate field comparison tables
    field_tables = _generate_field_comparison_tables(report)
    
    # Generate migration plans section
    migration_plans = _generate_migration_plans_section(report)
    
    # Generate account details
    account_details = _generate_account_details_section(report)
    
    summary = f"""╔══════════════════════════════════════════════════════════════════════════════╗
║                    📊 ACCOUNT ANALYSIS SUMMARY REPORT                        ║
║{name_line}║
║{timestamp_line}║
╚══════════════════════════════════════════════════════════════════════════════╝

🎯 **EXECUTIVE SUMMARY**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ **Account Status**: Successfully Analyzed
📁 **Dropbox Folder**: {report.dropbox_account_folder}
👤 **Primary Account**: {primary_account_name}
🏠 **Household Structure**: {household_name}
📊 **Data Quality Score**: {completeness_percentage:.1f}% ({quality_status})
🔧 **Migration Priority**: {report.migration_plans[0].priority.upper() if report.migration_plans else 'NONE'} ({len(report.migration_plans)} migrations needed)

📈 **KEY METRICS**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **Account Comparison Overview**
• Total Accounts Found: {report.total_accounts_found} total
• Accounts Matched: {report.total_accounts_matched} accounts need migration
• Missing from Salesforce: {report.total_accounts_missing_in_salesforce} accounts
• Missing from Dropbox: {report.total_accounts_missing_in_dropbox} accounts

📋 **Data Quality Analysis**
• Total Fields Compared: {report.data_quality.total_fields_compared} fields
• Fields Present in Salesforce: {report.data_quality.fields_present_in_salesforce} fields ({report.data_quality.fields_present_in_salesforce/report.data_quality.total_fields_compared*100:.1f}%)
• Fields Present in Dropbox: {report.data_quality.fields_present_in_dropbox} fields ({report.data_quality.fields_present_in_dropbox/report.data_quality.total_fields_compared*100:.1f}%)
• Fields Missing in Salesforce: {report.data_quality.fields_missing_in_salesforce} fields ({report.data_quality.fields_missing_in_salesforce/report.data_quality.total_fields_compared*100:.1f}%)
• Fields Missing in Dropbox: {report.data_quality.fields_missing_in_dropbox} fields ({report.data_quality.fields_missing_in_dropbox/report.data_quality.total_fields_compared*100:.1f}%)
• Fields with Different Values: {report.data_quality.fields_different} fields
• Data Completeness Score: {completeness_percentage:.1f}%
• Data Consistency Score: {consistency_percentage:.1f}%

🏠 **Household Structure Analysis**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Salesforce Household Structure:**
• Household Name: {household_name}
• Household Type: {'Household' if report.household_comparison and report.household_comparison.salesforce_household else 'Not Found'}
• Head of Household: {_get_household_head_name(report)}
• Total Members: {len(report.household_comparison.member_comparisons) if report.household_comparison else 0}
• Structure Status: {'✅ Properly Configured' if report.household_comparison and report.household_comparison.structure_match else '❌ Needs Configuration'}

**Dropbox Account Structure:**
• Account Name: {report.dropbox_account_folder}
• Account Type: {'Primary' if report.dropbox_account_information and report.dropbox_account_information.get('accounts') else 'Unknown'}
• Structure Status: ✅ Single Account

**Structure Comparison:**
• Structure Match: {'✅ Yes' if report.household_comparison and report.household_comparison.structure_match else '❌ No (Different account types)'}
• Missing Members: {', '.join(report.household_comparison.missing_members) if report.household_comparison and report.household_comparison.missing_members else 'None'}
• Extra Members: {', '.join(report.household_comparison.extra_members) if report.household_comparison and report.household_comparison.extra_members else 'None'}
• Migration Needed: {'✅ Yes (High Priority)' if report.household_comparison and report.household_comparison.migration_needed else '❌ No'}

{field_tables}

{migration_plans}

💡 **RECOMMENDATIONS**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ **Immediate Actions Required:**
{_format_recommendations(report.recommendations)}

⚠️ **WARNINGS**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 **Critical Issues:**
{_format_warnings(report.warnings)}

{account_details}

📈 **PERFORMANCE METRICS**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• **Analysis Duration**: {datetime.now().strftime('%H:%M:%S')}
• **Total Accounts Processed**: {report.total_accounts_found}
• **Data Quality Score**: {completeness_percentage:.1f}% ({quality_status})
• **Migration Complexity**: {'High' if len(report.migration_plans) > 3 else 'Medium' if len(report.migration_plans) > 1 else 'Low'} ({len(report.migration_plans)} plans)
• **Risk Level**: {'High' if report.household_comparison and not report.household_comparison.structure_match else 'Medium' if report.data_quality.fields_different > 0 else 'Low'} ({'Structure mismatches' if report.household_comparison and not report.household_comparison.structure_match else 'Data inconsistencies' if report.data_quality.fields_different > 0 else 'Minimal issues'})

🎯 **NEXT STEPS**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **Immediate**: Execute high-priority migrations
2. **Short-term**: Resolve household structure mismatches
3. **Medium-term**: Improve data completeness
4. **Long-term**: Establish data synchronization processes

╔══════════════════════════════════════════════════════════════════════════════╗
║                              END OF REPORT                                   ║
║                        Analysis completed successfully                       ║
╚══════════════════════════════════════════════════════════════════════════════╝"""
    
    return summary


def _get_household_head_name(report: AccountAnalysisReport) -> str:
    """Get the household head name from the report."""
    if report.household_comparison and report.household_comparison.head_comparison:
        return report.household_comparison.head_comparison.account_name
    elif report.household_comparison and report.household_comparison.salesforce_household:
        # Try to get from relationships
        relationships = report.household_comparison.salesforce_household.get('relationships', [])
        for rel in relationships:
            if rel.get('role') == 'Household Head':
                return rel.get('account_name', 'Unknown')
    return 'Not Found'


def _generate_field_comparison_tables(report: AccountAnalysisReport) -> str:
    """Generate field comparison tables for the summary."""
    if not report.account_comparisons:
        return "📊 **FIELD-BY-FIELD COMPARISON**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\nNo account comparisons available."
    
    tables = ["📊 **FIELD-BY-FIELD COMPARISON**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"]
    
    for comparison in report.account_comparisons:
        # Get the actual values for first and last name from dropbox (prefer client list file data)
        first_name_value = comparison.first_name.dropbox_value or comparison.first_name.salesforce_value or "Not specified"
        last_name_value = comparison.last_name.dropbox_value or comparison.last_name.salesforce_value or "Not specified"
        
        # Use the source value directly from the comparison (account analyzer now provides correct source)
        source_info = comparison.source.value
        
        # Create enhanced account header with all requested information
        if comparison.source.value == 'dropbox_merged':
            # For merged accounts, show "Name Found in client_list_file" format
            table = f"\n**Account: {comparison.account_name}** Source: {source_info}, Account Type: {comparison.account_type.value}, Name Found in client_list_file: First Name: {first_name_value}, Last Name: {last_name_value}\n"
        else:
            # For other sources, use the original format
            table = f"\n**Account: {comparison.account_name}** Source: {source_info}, Account Type: {comparison.account_type.value}, Name Found: {comparison.account_name}, First Name: {first_name_value}, Last Name: {last_name_value}\n"
        
        table += "┌─────────────────┬──────────────┬──────────────┬────────────────────────────┬──────────────┐\n"
        table += "│ Field           │ Salesforce   │ Dropbox      │ Status                     │ Priority     │\n"
        table += "├─────────────────┼──────────────┼──────────────┼────────────────────────────┼──────────────┤\n"
        
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'birthdate', 'gender', 'ssn_tax_id']
        for field_name in fields:
            field_comparison = getattr(comparison, field_name)
            sf_status = "✅ Present" if field_comparison.salesforce_value else "❌ Missing"
            db_status = "✅ Present" if field_comparison.dropbox_value else "❌ Missing"
            # Use the new method for the Status column
            status = AccountAnalyzer._format_field_status(AccountAnalyzer, field_comparison)
            priority = field_comparison.migration_priority.upper() if field_comparison.migration_priority != 'not_needed' else '-'
            
            table += f"│ {field_name:<15} │ {sf_status:<12} │ {db_status:<12} │ {status:<26} │ {priority:<11} │\n"
        
        table += "└─────────────────┴──────────────┴──────────────┴────────────────────────────┴──────────────┘\n"
        tables.append(table)
    
    return "\n".join(tables)


def _generate_migration_plans_section(report: AccountAnalysisReport) -> str:
    """Generate migration plans section for the summary."""
    if not report.migration_plans:
        return "🚀 **MIGRATION PLANS**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n✅ No migrations required - all data is synchronized."
    
    plans = ["🚀 **MIGRATION PLANS**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"]
    
    for i, plan in enumerate(report.migration_plans, 1):
        plan_text = f"\n**Plan {i}: {plan.account_name}**\n"
        plan_text += f"• Account: {plan.account_name}\n"
        plan_text += f"• Type: {plan.migration_type.title()}\n"
        plan_text += f"• Priority: {plan.priority.upper()}\n"
        plan_text += f"• Effort: {plan.estimated_effort.title()}\n"
        
        if plan.fields_to_create:
            plan_text += f"• Fields to Create: {', '.join(plan.fields_to_create)}\n"
        if plan.fields_to_update:
            plan_text += f"• Fields to Update: {', '.join(plan.fields_to_update)}\n"
        if plan.fields_to_merge:
            plan_text += f"• Fields to Merge: {', '.join(plan.fields_to_merge)}\n"
        
        plan_text += f"• Notes: {plan.notes}\n"
        plans.append(plan_text)
    
    return "\n".join(plans)


def _generate_account_details_section(report: AccountAnalysisReport) -> str:
    """Generate detailed account information section."""
    details = ["📊 **DETAILED ACCOUNT INFORMATION**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"]
    
    # Salesforce accounts
    if report.salesforce_account_information and report.salesforce_account_information.get('accounts'):
        details.append("**Salesforce Accounts Found:**")
        for i, account in enumerate(report.salesforce_account_information['accounts'], 1):
            details.append(f"{i}. **{account.get('account_name', 'Unknown')}** ({account.get('type', 'Unknown')})")
            details.append(f"   - Type: {account.get('type', 'Unknown')}")
            details.append(f"   - Role: {account.get('role', 'Unknown')}")
            details.append(f"   - Stage: {account.get('stage', 'Not specified')}")
            details.append(f"   - Email: {account.get('email', 'Not specified')}")
            details.append(f"   - Phone: {account.get('phone', 'Not specified')}")
            details.append(f"   - Address: {account.get('mailing_address', 'Not specified')}")
            details.append(f"   - SSN/Tax ID: {account.get('ssn/tax_id', 'Not specified')}\n")
    
    # Dropbox accounts
    if report.dropbox_account_information and report.dropbox_account_information.get('accounts'):
        details.append("**Dropbox Accounts Found:**")
        for i, account in enumerate(report.dropbox_account_information['accounts'], 1):
            details.append(f"{i}. **{account.get('account_name', 'Unknown')}** ({account.get('account_type', 'Unknown')})")
            details.append(f"   - Source: {account.get('source', 'Unknown')}")
            details.append(f"   - Account Type: {account.get('account_type', 'Unknown')}")
            details.append(f"   - First Name: {account.get('first_name', 'Not specified')}")
            details.append(f"   - Last Name: {account.get('last_name', 'Not specified')}")
            details.append(f"   - Phone: {account.get('phone', 'Not specified')}")
            details.append(f"   - Address: {account.get('address', 'Not specified')}")
            details.append(f"   - Email: {account.get('email', 'Not specified')}")
            details.append(f"   - Birthdate: {account.get('birthdate', 'Not specified')}")
            details.append(f"   - Gender: {account.get('gender', 'Not specified')}")
            
            # Show match status for client list accounts
            if account.get('source') == 'client_list_file':
                details.append(f"   - Match Status: {account.get('match_status', 'Not specified')}")
            
            # Show contributing application files for application_files accounts
            if account.get('source') == 'application_files':
                # Get the file information from the app_files_extraction_summary
                app_files_extraction_summary = report.dropbox_account_information.get('app_files_extraction_summary', {})
                if app_files_extraction_summary and 'all_folder_app_files' in app_files_extraction_summary and 'file_info' in app_files_extraction_summary:
                    # Debug logging
                    print(f"DEBUG: Processing account {account.get('account_name')} with first_name='{account.get('first_name')}' last_name='{account.get('last_name')}'")
                    print(f"DEBUG: app_files_extraction_summary keys: {list(app_files_extraction_summary.keys())}")
                    print(f"DEBUG: all_folder_app_files keys: {list(app_files_extraction_summary['all_folder_app_files'].keys())}")
                    print(f"DEBUG: file_info keys: {list(app_files_extraction_summary['file_info'].keys())}")
                    
                    matching_files = []
                    for folder_files in app_files_extraction_summary['all_folder_app_files'].values():
                        for file in folder_files:
                            file_path = getattr(file, 'path_display', None)
                            file_info = app_files_extraction_summary['file_info'].get(file_path, {})
                            print(f"DEBUG: Checking file {file.name} with path {file_path}")
                            print(f"DEBUG: file_info: {file_info}")
                            
                            # Check owner information
                            owner = file_info.get('owner', {})
                            account_first = account.get('first_name', '')
                            account_last = account.get('last_name', '')
                            if owner.get('firstName') and owner.get('lastName'):
                                file_first = owner.get('firstName', '')
                                file_last = owner.get('lastName', '')
                                print(f"DEBUG: Comparing OWNER file_first='{file_first}' vs account_first='{account_first}'")
                                print(f"DEBUG: Comparing OWNER file_last='{file_last}' vs account_last='{account_last}'")
                                if (
                                    file_first.strip().lower() == account_first.strip().lower() and
                                    file_last.strip().lower() == account_last.strip().lower()
                                ):
                                    print(f"DEBUG: MATCH FOUND for OWNER in file {file.name}")
                                    matching_files.append(file)
                            # Check joint owner information
                            joint_owner = file_info.get('jointOwner', {})
                            if joint_owner.get('firstName') and joint_owner.get('lastName'):
                                joint_first = joint_owner.get('firstName', '')
                                joint_last = joint_owner.get('lastName', '')
                                print(f"DEBUG: Comparing JOINT file_first='{joint_first}' vs account_first='{account_first}'")
                                print(f"DEBUG: Comparing JOINT file_last='{joint_last}' vs account_last='{account_last}'")
                                if (
                                    joint_first.strip().lower() == account_first.strip().lower() and
                                    joint_last.strip().lower() == account_last.strip().lower()
                                ):
                                    print(f"DEBUG: MATCH FOUND for JOINT OWNER in file {file.name}")
                                    matching_files.append(file)
                    
                    print(f"DEBUG: Total matching files found: {len(matching_files)}")
                    if matching_files:
                        details.append(f"   - **Contributing Application Files:**")
                        for file in matching_files:
                            details.append(f"     📄 {file.name}")
                    else:
                        details.append(f"   - **Contributing Application Files:** None found")
                else:
                    print(f"DEBUG: Missing required data for account {account.get('account_name')}")
                    print(f"DEBUG: app_files_extraction_summary exists: {app_files_extraction_summary is not None}")
                    print(f"DEBUG: all_folder_app_files exists: {'all_folder_app_files' in app_files_extraction_summary if app_files_extraction_summary else False}")
                    print(f"DEBUG: file_info exists: {'file_info' in app_files_extraction_summary if app_files_extraction_summary else False}")
            
            details.append("")  # Empty line for spacing
    
    # Merged accounts information
    if report.account_comparisons:
        merged_accounts = [comp for comp in report.account_comparisons if comp.source.value == 'dropbox_merged']
        if merged_accounts:
            details.append("**Merged Accounts Information:**")
            for i, comparison in enumerate(merged_accounts, 1):
                details.append(f"{i}. **{comparison.account_name}** (Merged Account)")
                details.append(f"   - Account Type: {comparison.account_type.value}")
                details.append(f"   - Source: {comparison.source.value}")
                
                # Find the original accounts that were merged
                original_accounts = []
                if report.dropbox_account_information and report.dropbox_account_information.get('accounts'):
                    for account in report.dropbox_account_information['accounts']:
                        if account.get('account_name') == comparison.account_name:
                            original_accounts.append(account)
                
                # Show what was merged by looking at the field comparisons
                merged_fields = []
                for field_name in ['first_name', 'last_name', 'email', 'phone', 'address', 'birthdate', 'gender']:
                    field_comparison = getattr(comparison, field_name)
                    if field_comparison.dropbox_value:
                        merged_fields.append(f"{field_name}: {field_comparison.dropbox_value}")
                
                if merged_fields:
                    details.append(f"   - Final Merged Data: {', '.join(merged_fields)}")
                
                # Show the original sources that were merged
                if original_accounts:
                    details.append(f"   - **Merged from {len(original_accounts)} source(s):**")
                    for j, orig_account in enumerate(original_accounts, 1):
                        source = orig_account.get('source', 'Unknown')
                        details.append(f"     {j}. {source.upper()}:")
                        details.append(f"        - First Name: {orig_account.get('first_name', 'Not specified')}")
                        details.append(f"        - Last Name: {orig_account.get('last_name', 'Not specified')}")
                        details.append(f"        - Email: {orig_account.get('email', 'Not specified')}")
                        details.append(f"        - Phone: {orig_account.get('phone', 'Not specified')}")
                        details.append(f"        - Address: {orig_account.get('address', 'Not specified')}")
                        details.append(f"        - Birthdate: {orig_account.get('birthdate', 'Not specified')}")
                        details.append(f"        - Gender: {orig_account.get('gender', 'Not specified')}")
                        
                        # Show match status for client list accounts
                        if source == 'client_list_file':
                            details.append(f"        - Match Status: {orig_account.get('match_status', 'Not specified')}")
                else:
                    details.append(f"   - **Note: Original source accounts not found in report data**")
                
                # Show migration status
                if comparison.migration_needed:
                    details.append(f"   - Migration Status: 🔄 Needed ({comparison.migration_priority.value} priority)")
                else:
                    details.append(f"   - Migration Status: ✅ Not needed")
                
                # Show field status summary
                field_issues = []
                for field_name in ['first_name', 'last_name', 'email', 'phone', 'address', 'birthdate', 'gender']:
                    field_comparison = getattr(comparison, field_name)
                    if field_comparison.status != 'present':
                        field_issues.append(f"{field_name}: {field_comparison.status}")
                
                if field_issues:
                    details.append(f"   - Field Issues: {', '.join(field_issues)}")
                
                # Show contributing application files for accounts that came from application_files
                is_from_application_files = False
                if original_accounts:
                    for orig_account in original_accounts:
                        if orig_account.get('source') == 'application_files':
                            is_from_application_files = True
                            break
                
                if is_from_application_files:
                    # Get the file information from the app_files_extraction_summary
                    app_files_extraction_summary = report.dropbox_account_information.get('app_files_extraction_summary', {})
                    if app_files_extraction_summary and 'all_folder_app_files' in app_files_extraction_summary and 'file_info' in app_files_extraction_summary:
                        # Use the merged account's first and last name for matching
                        merged_first = comparison.first_name.dropbox_value if hasattr(comparison, 'first_name') and hasattr(comparison.first_name, 'dropbox_value') else ''
                        merged_last = comparison.last_name.dropbox_value if hasattr(comparison, 'last_name') and hasattr(comparison.last_name, 'dropbox_value') else ''
                        matching_files = []
                        for folder_files in app_files_extraction_summary['all_folder_app_files'].values():
                            for file in folder_files:
                                file_path = getattr(file, 'path_display', None)
                                file_info = app_files_extraction_summary['file_info'].get(file_path, {})
                                
                                # Check owner information
                                owner = file_info.get('owner', {})
                                account_first = account.get('first_name', '')
                                account_last = account.get('last_name', '')
                                if owner.get('firstName') and owner.get('lastName'):
                                    file_first = owner.get('firstName', '')
                                    file_last = owner.get('lastName', '')
                                    print(f"DEBUG: Comparing OWNER file_first='{file_first}' vs account_first='{account_first}'")
                                    print(f"DEBUG: Comparing OWNER file_last='{file_last}' vs account_last='{account_last}'")
                                    if (
                                        file_first.strip().lower() == account_first.strip().lower() and
                                        file_last.strip().lower() == account_last.strip().lower()
                                    ):
                                        print(f"DEBUG: MATCH FOUND for OWNER in file {file.name}")
                                        matching_files.append(file)
                                # Check joint owner information
                                joint_owner = file_info.get('jointOwner', {})
                                if joint_owner.get('firstName') and joint_owner.get('lastName'):
                                    joint_first = joint_owner.get('firstName', '')
                                    joint_last = joint_owner.get('lastName', '')
                                    print(f"DEBUG: Comparing JOINT file_first='{joint_first}' vs account_first='{account_first}'")
                                    print(f"DEBUG: Comparing JOINT file_last='{joint_last}' vs account_last='{account_last}'")
                                    if (
                                        joint_first.strip().lower() == account_first.strip().lower() and
                                        joint_last.strip().lower() == account_last.strip().lower()
                                    ):
                                        print(f"DEBUG: MATCH FOUND for JOINT OWNER in file {file.name}")
                                        matching_files.append(file)

                        if matching_files:
                            details.append(f"   - **Contributing Application Files:**")
                            for file in matching_files:
                                details.append(f"     📄 {file.name}")
                        else:
                            details.append(f"   - **Contributing Application Files:** None found")
                
                details.append("")  # Empty line for spacing
    
    # Show original source accounts that were merged
    if report.dropbox_account_information and report.dropbox_account_information.get('accounts'):
        original_sources = report.dropbox_account_information['accounts']
        if len(original_sources) > 1:  # Only show if there were multiple sources to merge
            details.append("**Original Source Accounts (Before Merging):**")
            for i, account in enumerate(original_sources, 1):
                details.append(f"{i}. **{account.get('account_name', 'Unknown')}**")
                details.append(f"   - Original Source: {account.get('source', 'Unknown')}")
                details.append(f"   - Account Type: {account.get('account_type', 'Unknown')}")
                details.append(f"   - First Name: {account.get('first_name', 'Not specified')}")
                details.append(f"   - Last Name: {account.get('last_name', 'Not specified')}")
                details.append(f"   - Email: {account.get('email', 'Not specified')}")
                details.append(f"   - Phone: {account.get('phone', 'Not specified')}")
                details.append(f"   - Address: {account.get('address', 'Not specified')}")
                details.append(f"   - Birthdate: {account.get('birthdate', 'Not specified')}")
                details.append(f"   - Gender: {account.get('gender', 'Not specified')}")
                
                # Show match status for client list accounts
                if account.get('source') == 'client_list_file':
                    details.append(f"   - Match Status: {account.get('match_status', 'Not specified')}")
                
                # Show contributing application files for application_files accounts
                if account.get('source') == 'application_files':
                    # Get the file information from the app_files_extraction_summary
                    app_files_extraction_summary = report.dropbox_account_information.get('app_files_extraction_summary', {})
                    if app_files_extraction_summary and 'all_folder_app_files' in app_files_extraction_summary and 'file_info' in app_files_extraction_summary:
                        matching_files = []
                        for folder_files in app_files_extraction_summary['all_folder_app_files'].values():
                            for file in folder_files:
                                file_path = getattr(file, 'path_display', None)
                                file_info = app_files_extraction_summary['file_info'].get(file_path, {})
                                
                                # Check owner information
                                owner = file_info.get('owner', {})
                                account_first = account.get('first_name', '')
                                account_last = account.get('last_name', '')
                                if owner.get('firstName') and owner.get('lastName'):
                                    file_first = owner.get('firstName', '')
                                    file_last = owner.get('lastName', '')
                                    print(f"DEBUG: Comparing OWNER file_first='{file_first}' vs account_first='{account_first}'")
                                    print(f"DEBUG: Comparing OWNER file_last='{file_last}' vs account_last='{account_last}'")
                                    if (
                                        file_first.strip().lower() == account_first.strip().lower() and
                                        file_last.strip().lower() == account_last.strip().lower()
                                    ):
                                        print(f"DEBUG: MATCH FOUND for OWNER in file {file.name}")
                                        matching_files.append(file)
                                # Check joint owner information
                                joint_owner = file_info.get('jointOwner', {})
                                if joint_owner.get('firstName') and joint_owner.get('lastName'):
                                    joint_first = joint_owner.get('firstName', '')
                                    joint_last = joint_owner.get('lastName', '')
                                    print(f"DEBUG: Comparing JOINT file_first='{joint_first}' vs account_first='{account_first}'")
                                    print(f"DEBUG: Comparing JOINT file_last='{joint_last}' vs account_last='{account_last}'")
                                    if (
                                        joint_first.strip().lower() == account_first.strip().lower() and
                                        joint_last.strip().lower() == account_last.strip().lower()
                                    ):
                                        print(f"DEBUG: MATCH FOUND for JOINT OWNER in file {file.name}")
                                        matching_files.append(file)
                                
                                if (
                                    file_first.strip().lower() == account.get('first_name', '').strip().lower() and
                                    file_last.strip().lower() == account.get('last_name', '').strip().lower()
                                ):
                                    matching_files.append(file)
                        if matching_files:
                            details.append(f"   - **Contributing Application Files:**")
                            for file in matching_files:
                                details.append(f"     📄 {file.name}")
                        else:
                            details.append(f"   - **Contributing Application Files:** None found")
                
                details.append("")  # Empty line for spacing
            
            # Show merge summary
            details.append("**Merge Summary:**")
            client_list_accounts = [acc for acc in original_sources if acc.get('source') == 'client_list_file']
            application_accounts = [acc for acc in original_sources if acc.get('source') == 'application_files']
            
            if client_list_accounts:
                details.append(f"   - Client List Accounts: {len(client_list_accounts)}")
                for acc in client_list_accounts:
                    details.append(f"     * {acc.get('account_name', 'Unknown')} ({acc.get('account_type', 'Unknown')})")
            
            if application_accounts:
                details.append(f"   - Application Files Accounts: {len(application_accounts)}")
                for acc in application_accounts:
                    details.append(f"     * {acc.get('account_name', 'Unknown')} ({acc.get('account_type', 'Unknown')})")
            
            details.append(f"   - Total Accounts Merged: {len(original_sources)}")
            details.append("")  # Empty line for spacing
    
    return "\n".join(details)


def _format_recommendations(recommendations: List[str]) -> str:
    """Format recommendations for the summary."""
    if not recommendations:
        return "No specific recommendations at this time."
    
    formatted = []
    for i, rec in enumerate(recommendations, 1):
        formatted.append(f"{i}. **{rec}**")
    
    return "\n".join(formatted)


def _format_warnings(warnings: List[str]) -> str:
    """Format warnings for the summary."""
    if not warnings:
        return "No critical issues identified."
    
    formatted = []
    for warning in warnings:
        formatted.append(f"• {warning}")
    
    return "\n".join(formatted)


def _log_analysis_results(report: AccountAnalysisReport) -> None:
    """Log the analysis results in a structured format."""
    
    logger.info("\n" + "="*80)
    logger.info("📊 **ACCOUNT ANALYSIS RESULTS**")
    logger.info("="*80)
    
    # Basic information
    logger.info(f"📁 Account Folder: {report.dropbox_account_folder}")
    logger.info(f"🕒 Analysis Timestamp: {report.analysis_timestamp}")
    
    # Summary statistics
    logger.info(f"\n📈 **SUMMARY STATISTICS**")
    logger.info(f"📊 Total Accounts Found: {report.total_accounts_found}")
    logger.info(f"✅ Total Accounts Matched: {report.total_accounts_matched}")
    logger.info(f"❌ Missing in Salesforce: {report.total_accounts_missing_in_salesforce}")
    logger.info(f"❌ Missing in Dropbox: {report.total_accounts_missing_in_dropbox}")
    logger.info(f"🔄 Total Migrations Needed: {report.total_migrations_needed}")
    
    # Data quality metrics
    logger.info(f"\n📊 **DATA QUALITY METRICS**")
    logger.info(f"📋 Total Fields Compared: {report.data_quality.total_fields_compared}")
    logger.info(f"✅ Fields Present in Salesforce: {report.data_quality.fields_present_in_salesforce}")
    logger.info(f"✅ Fields Present in Dropbox: {report.data_quality.fields_present_in_dropbox}")
    logger.info(f"❌ Fields Missing in Salesforce: {report.data_quality.fields_missing_in_salesforce}")
    logger.info(f"❌ Fields Missing in Dropbox: {report.data_quality.fields_missing_in_dropbox}")
    logger.info(f"⚠️ Fields with Different Values: {report.data_quality.fields_different}")
    logger.info(f"📊 Data Completeness Score: {report.data_quality.data_completeness_score:.2%}")
    logger.info(f"📊 Data Consistency Score: {report.data_quality.data_consistency_score:.2%}")
    
    # Account comparisons
    if report.account_comparisons:
        logger.info(f"\n👥 **ACCOUNT COMPARISONS** ({len(report.account_comparisons)})")
        for i, comparison in enumerate(report.account_comparisons, 1):
            logger.info(f"\n{'─'*60}")
            logger.info(f"👤 Account {i}: {comparison.account_name}")
            logger.info(f"📋 Type: {comparison.account_type}")
            logger.info(f"👑 Role: {comparison.role or 'N/A'}")
            logger.info(f"📊 Source: {comparison.source}")
            logger.info(f"🔄 Migration Needed: {'✅ Yes' if comparison.migration_needed else '❌ No'}")
            if comparison.migration_needed:
                logger.info(f"🎯 Migration Priority: {comparison.migration_priority}")
            
            # Field status summary
            field_statuses = []
            for field_name in ['first_name', 'last_name', 'email', 'phone', 'address', 'birthdate', 'gender']:
                field_comparison = getattr(comparison, field_name)
                if field_comparison.status != 'present':
                    field_statuses.append(f"{field_name}: {field_comparison.status}")
            
            if field_statuses:
                logger.info(f"⚠️ Issues: {', '.join(field_statuses)}")
    
    # Household analysis
    if report.household_comparison:
        logger.info(f"\n🏠 **HOUSEHOLD ANALYSIS**")
        logger.info(f"🏠 Household Name: {report.household_comparison.household_name}")
        logger.info(f"📊 Structure Match: {'✅ Yes' if report.household_comparison.structure_match else '❌ No'}")
        logger.info(f"🔄 Migration Needed: {'✅ Yes' if report.household_comparison.migration_needed else '❌ No'}")
        
        if report.household_comparison.missing_members:
            logger.info(f"❌ Missing Members: {', '.join(report.household_comparison.missing_members)}")
        
        if report.household_comparison.extra_members:
            logger.info(f"➕ Extra Members: {', '.join(report.household_comparison.extra_members)}")
    
    # Migration plans
    if report.migration_plans:
        logger.info(f"\n🔄 **MIGRATION PLANS** ({len(report.migration_plans)})")
        for i, plan in enumerate(report.migration_plans, 1):
            logger.info(f"\n{'─'*40}")
            logger.info(f"📋 Plan {i}: {plan.account_name}")
            logger.info(f"🔄 Type: {plan.migration_type}")
            logger.info(f"🎯 Priority: {plan.priority}")
            logger.info(f"⏱️ Estimated Effort: {plan.estimated_effort}")
            
            if plan.fields_to_create:
                logger.info(f"➕ Fields to Create: {', '.join(plan.fields_to_create)}")
            if plan.fields_to_update:
                logger.info(f"📝 Fields to Update: {', '.join(plan.fields_to_update)}")
            if plan.fields_to_merge:
                logger.info(f"🔀 Fields to Merge: {', '.join(plan.fields_to_merge)}")
    
    # Recommendations
    if report.recommendations:
        logger.info(f"\n💡 **RECOMMENDATIONS** ({len(report.recommendations)})")
        for i, rec in enumerate(report.recommendations, 1):
            logger.info(f"  {i}. {rec}")
    
    # Warnings
    if report.warnings:
        logger.info(f"\n⚠️ **WARNINGS** ({len(report.warnings)})")
        for i, warning in enumerate(report.warnings, 1):
            logger.info(f"  {i}. {warning}")
    
    # Errors
    if report.errors:
        logger.info(f"\n❌ **ERRORS** ({len(report.errors)})")
        for i, error in enumerate(report.errors, 1):
            logger.info(f"  {i}. {error}")
    
    logger.info("\n" + "="*80)


def _generate_detailed_reports(report: AccountAnalysisReport) -> Dict[str, Any]:
    """Generate detailed reports in various formats."""
    
    reports = {}
    
    # JSON report
    reports['json'] = {
        'format': 'json',
        'content': report.model_dump(),
        'filename': f"account_analysis_{report.dropbox_account_folder.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    }
    
    # Summary report
    summary_report = _generate_summary_report(report)
    reports['summary'] = {
        'format': 'text',
        'content': summary_report,
        'filename': f"account_analysis_summary_{report.dropbox_account_folder.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    }
    
    # Migration plan report
    migration_report = _generate_migration_report(report)
    reports['migration'] = {
        'format': 'text',
        'content': migration_report,
        'filename': f"migration_plan_{report.dropbox_account_folder.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    }
    
    # Data quality report
    quality_report = _generate_data_quality_report(report)
    reports['quality'] = {
        'format': 'text',
        'content': quality_report,
        'filename': f"data_quality_{report.dropbox_account_folder.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    }
    
    return reports


def _generate_summary_report(report: AccountAnalysisReport) -> str:
    """Generate a summary report."""
    
    lines = []
    lines.append("="*80)
    lines.append("ACCOUNT ANALYSIS SUMMARY REPORT")
    lines.append("="*80)
    lines.append(f"Account Folder: {report.dropbox_account_folder}")
    lines.append(f"Analysis Date: {report.analysis_timestamp}")
    lines.append("")
    
    # Executive summary
    lines.append("EXECUTIVE SUMMARY")
    lines.append("-" * 40)
    lines.append(f"Total Accounts: {report.total_accounts_found}")
    lines.append(f"Total Migrations Needed: {report.total_migrations_needed}")
    lines.append(f"Data Completeness: {report.data_quality.data_completeness_score:.1%}")
    lines.append(f"Data Consistency: {report.data_quality.data_consistency_score:.1%}")
    lines.append("")
    
    # Key findings
    lines.append("KEY FINDINGS")
    lines.append("-" * 40)
    
    if report.data_quality.fields_different > 0:
        lines.append(f"⚠️ {report.data_quality.fields_different} fields have conflicting values")
    
    if report.data_quality.fields_missing_in_salesforce > 0:
        lines.append(f"❌ {report.data_quality.fields_missing_in_salesforce} fields missing in Salesforce")
    
    if report.household_comparison and not report.household_comparison.structure_match:
        lines.append("🏠 Household structure mismatch detected")
    
    lines.append("")
    
    # Recommendations
    if report.recommendations:
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 40)
        for i, rec in enumerate(report.recommendations, 1):
            lines.append(f"{i}. {rec}")
        lines.append("")
    
    return "\n".join(lines)


def _generate_migration_report(report: AccountAnalysisReport) -> str:
    """Generate a migration plan report."""
    
    lines = []
    lines.append("="*80)
    lines.append("MIGRATION PLAN REPORT")
    lines.append("="*80)
    lines.append(f"Account Folder: {report.dropbox_account_folder}")
    lines.append(f"Generated: {report.analysis_timestamp}")
    lines.append("")
    
    if not report.migration_plans:
        lines.append("✅ No migrations required - all data is synchronized")
        return "\n".join(lines)
    
    # Migration summary
    lines.append("MIGRATION SUMMARY")
    lines.append("-" * 40)
    lines.append(f"Total Plans: {len(report.migration_plans)}")
    
    high_priority = len([p for p in report.migration_plans if p.priority == 'high'])
    medium_priority = len([p for p in report.migration_plans if p.priority == 'medium'])
    low_priority = len([p for p in report.migration_plans if p.priority == 'low'])
    
    lines.append(f"High Priority: {high_priority}")
    lines.append(f"Medium Priority: {medium_priority}")
    lines.append(f"Low Priority: {low_priority}")
    lines.append("")
    
    # Detailed plans
    lines.append("DETAILED MIGRATION PLANS")
    lines.append("-" * 40)
    
    for i, plan in enumerate(report.migration_plans, 1):
        lines.append(f"\n{i}. {plan.account_name}")
        lines.append(f"   Type: {plan.migration_type}")
        lines.append(f"   Priority: {plan.priority}")
        lines.append(f"   Effort: {plan.estimated_effort}")
        
        if plan.fields_to_create:
            lines.append(f"   Create: {', '.join(plan.fields_to_create)}")
        if plan.fields_to_update:
            lines.append(f"   Update: {', '.join(plan.fields_to_update)}")
        if plan.fields_to_merge:
            lines.append(f"   Merge: {', '.join(plan.fields_to_merge)}")
        
        if plan.validation_rules:
            lines.append(f"   Validation: {', '.join(plan.validation_rules)}")
        
        if plan.notes:
            lines.append(f"   Notes: {plan.notes}")
    
    return "\n".join(lines)


def _generate_data_quality_report(report: AccountAnalysisReport) -> str:
    """Generate a data quality report."""
    
    lines = []
    lines.append("="*80)
    lines.append("DATA QUALITY REPORT")
    lines.append("="*80)
    lines.append(f"Account Folder: {report.dropbox_account_folder}")
    lines.append(f"Generated: {report.analysis_timestamp}")
    lines.append("")
    
    # Quality metrics
    lines.append("QUALITY METRICS")
    lines.append("-" * 40)
    lines.append(f"Completeness Score: {report.data_quality.data_completeness_score:.1%}")
    lines.append(f"Consistency Score: {report.data_quality.data_consistency_score:.1%}")
    lines.append(f"Total Fields: {report.data_quality.total_fields_compared}")
    lines.append("")
    
    # Field analysis
    lines.append("FIELD ANALYSIS")
    lines.append("-" * 40)
    lines.append(f"Present in Salesforce: {report.data_quality.fields_present_in_salesforce}")
    lines.append(f"Present in Dropbox: {report.data_quality.fields_present_in_dropbox}")
    lines.append(f"Missing in Salesforce: {report.data_quality.fields_missing_in_salesforce}")
    lines.append(f"Missing in Dropbox: {report.data_quality.fields_missing_in_dropbox}")
    lines.append(f"Different Values: {report.data_quality.fields_different}")
    lines.append("")
    
    # Detailed field comparisons
    if report.account_comparisons:
        lines.append("DETAILED FIELD COMPARISONS")
        lines.append("-" * 40)
        
        for comparison in report.account_comparisons:
            lines.append(f"\n{comparison.account_name} ({comparison.account_type})")
            
            for field_name in ['first_name', 'last_name', 'email', 'phone', 'address', 'birthdate', 'gender']:
                field_comparison = getattr(comparison, field_name)
                if field_comparison.status != 'present':
                    lines.append(f"  {field_name}: {field_comparison.status}")
                    if field_comparison.notes:
                        lines.append(f"    Note: {field_comparison.notes}")
    
    return "\n".join(lines) 