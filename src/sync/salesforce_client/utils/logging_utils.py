"""
Salesforce Account Information Logging Utilities

This module provides beautiful, formatted logging utilities for Salesforce Account Information
with icons, better formatting, and visual appeal.
"""

import logging
from typing import Dict, List, Any, Optional


class SalesforceAccountLogger:
    """Utility class for logging Salesforce Account Information with beautiful formatting."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the Salesforce Account Logger.
        
        Args:
            logger: Optional logger instance. If not provided, uses the root logger.
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def log_salesforce_account_information(self, 
                                         salesforce_account_information: Dict[str, Any], 
                                         dropbox_account_folder_name: str) -> None:
        """
        Log comprehensive Salesforce Account Information with beautiful formatting.
        
        Args:
            salesforce_account_information: The structured account information
            dropbox_account_folder_name: Name of the Dropbox account folder
        """
        # Header section
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"👤 **SALESFORCE ACCOUNT INFORMATION** 📊")
        self.logger.info(f"📁 Dropbox Account Folder: {dropbox_account_folder_name}")
        self.logger.info(f"{'='*80}")
        
        # Summary section
        self._log_summary_section(salesforce_account_information)
        
        # Detailed account information
        self._log_detailed_account_information(salesforce_account_information)
        
        # Statistics summary
        self._log_statistics_summary(salesforce_account_information)
    
    def _log_summary_section(self, salesforce_account_information: Dict[str, Any]) -> None:
        """Log the summary section with key information."""
        self.logger.info(f"\n📋 **SUMMARY**")
        
        names_found = salesforce_account_information.get('names_found', [])
        self.logger.info(f"🔍 Names found: {', '.join(names_found) if names_found else '--'}")
        
        household = salesforce_account_information.get('household')
        if household:
            self.logger.info(f"🏠 Household: {household['account_name']}")
        
        head = salesforce_account_information.get('head')
        if head:
            self.logger.info(f"👑 Head: {head['account_name']}")
        
        members = salesforce_account_information.get('members', [])
        if members:
            member_names = [member['account_name'] for member in members]
            self.logger.info(f"👥 Members: {', '.join(member_names)}")
    
    def _log_detailed_account_information(self, salesforce_account_information: Dict[str, Any]) -> None:
        """Log detailed information for each account."""
        accounts = salesforce_account_information.get('accounts', [])
        if not accounts:
            return
        
        self.logger.info(f"\n📊 **DETAILED ACCOUNT INFORMATION**")
        
        for i, account in enumerate(accounts, 1):
            self._log_single_account(account, i)
    
    def _log_single_account(self, account: Dict[str, Any], account_number: int) -> None:
        """Log information for a single account."""
        self.logger.info(f"\n{'─'*60}")
        self.logger.info(f"🏢 **Account {account_number}: {account['account_name']}**")
        self.logger.info(f"{'─'*60}")
        
        # Account type and role
        type_icon = "🏠" if account['type'] == 'Household' else "👤"
        self.logger.info(f"{type_icon} Type: {account['type']}")
        
        if account.get('role'):
            role_icon = "👑" if account['role'] == 'Household Head' else "👥"
            self.logger.info(f"{role_icon} Role: {account['role']}")
        
        # Account details
        self._log_account_details(account)
        
        # Relationships
        self._log_account_relationships(account)
    
    def _log_account_details(self, account: Dict[str, Any]) -> None:
        """Log account details like stage, email, phone, etc."""
        if account.get('stage'):
            stage_icon = self._get_stage_icon(account['stage'])
            self.logger.info(f"{stage_icon} Stage: {account['stage']}")
        
        if account.get('email'):
            self.logger.info(f"📧 Email: {account['email']}")
        
        if account.get('phone'):
            self.logger.info(f"📞 Phone: {account['phone']}")
        
        if account.get('mailing_address'):
            self.logger.info(f"📍 Address: {account['mailing_address']}")
        
        if account.get('ssn/tax_id'):
            self.logger.info(f"🔒 SSN/Tax ID: {account['ssn/tax_id']}")
    
    def _log_account_relationships(self, account: Dict[str, Any]) -> None:
        """Log relationships for an account."""
        relationships = account.get('relationships', [])
        if relationships:
            self.logger.info(f"\n🔗 **Relationships ({len(relationships)})**")
            for j, rel in enumerate(relationships, 1):
                self._log_single_relationship(rel, j)
        else:
            self.logger.info(f"\n🔗 **Relationships**: None")
    
    def _log_single_relationship(self, rel: Dict[str, Any], rel_number: int) -> None:
        """Log information for a single relationship."""
        rel_type_icon = "🏠" if rel['type'] == 'Household' else "👤"
        rel_role_icon = self._get_role_icon(rel.get('role'))
        
        self.logger.info(f"   {rel_number}. 📝 {rel['account_name']}")
        self.logger.info(f"      {rel_type_icon} Type: {rel['type']}")
        
        if rel.get('role'):
            self.logger.info(f"      {rel_role_icon} Role: {rel['role']}")
        
        if rel.get('stage'):
            self.logger.info(f"      📋 Stage: {rel['stage']}")
        
        if rel.get('email'):
            self.logger.info(f"      📧 Email: {rel['email']}")
        
        if rel.get('phone'):
            self.logger.info(f"      📞 Phone: {rel['phone']}")
    
    def _log_statistics_summary(self, salesforce_account_information: Dict[str, Any]) -> None:
        """Log the final statistics summary."""
        total_accounts = len(salesforce_account_information.get('accounts', []))
        total_relationships = sum(len(acc.get('relationships', [])) for acc in salesforce_account_information.get('accounts', []))
        has_household = salesforce_account_information.get('household') is not None
        has_head = salesforce_account_information.get('head') is not None
        total_members = len(salesforce_account_information.get('members', []))
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"📈 **STATISTICS SUMMARY**")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"📊 Total Accounts: {total_accounts}")
        self.logger.info(f"🔗 Total Relationships: {total_relationships}")
        self.logger.info(f"🏠 Has Household: {'✅ Yes' if has_household else '❌ No'}")
        self.logger.info(f"👑 Has Head: {'✅ Yes' if has_head else '❌ No'}")
        self.logger.info(f"👥 Total Members: {total_members}")
        self.logger.info(f"{'='*80}")
    
    def _get_stage_icon(self, stage: str) -> str:
        """Get the appropriate icon for a stage."""
        if stage == 'Client':
            return "✅"
        elif stage == 'Prospect':
            return "🔄"
        else:
            return "📋"
    
    def _get_role_icon(self, role: Optional[str]) -> str:
        """Get the appropriate icon for a role."""
        if role == 'Household Head':
            return "👑"
        elif role == 'Member':
            return "👥"
        else:
            return "🔗"
    
    def log_command_analysis(self, salesforce_account_information: Dict[str, Any]) -> None:
        """
        Log Salesforce Account Information in command analysis format.
        
        Args:
            salesforce_account_information: The structured account information
        """
        self.logger.info("🎯 === SALESFORCE ACCOUNT INFORMATION ANALYSIS ===")
        
        # Log basic information
        names_found = salesforce_account_information.get('names_found', [])
        self.logger.info(f"📋 **Names found**: {', '.join(names_found) if names_found else 'None'}")
        
        # Log household information
        self._log_command_household_info(salesforce_account_information)
        
        # Log head information
        self._log_command_head_info(salesforce_account_information)
        
        # Log members information
        self._log_command_members_info(salesforce_account_information)
        
        # Log all accounts information
        self._log_command_accounts_info(salesforce_account_information)
        
        # Log summary statistics
        self._log_command_summary_statistics(salesforce_account_information)
    
    def _log_command_household_info(self, salesforce_account_information: Dict[str, Any]) -> None:
        """Log household information in command format."""
        household = salesforce_account_information.get('household')
        if household:
            self.logger.info(f"\n🏠 **Household Information**")
            self.logger.info(f"   📝 Name: {household['account_name']}")
            self.logger.info(f"   🏢 Type: {household['type']}")
            self.logger.info(f"   📊 Stage: {household.get('stage', 'N/A')}")
            self.logger.info(f"   📧 Email: {household.get('email', 'N/A')}")
            self.logger.info(f"   📞 Phone: {household.get('phone', 'N/A')}")
            self.logger.info(f"   📍 Address: {household.get('mailing_address', 'N/A')}")
            self.logger.info(f"   🔒 SSN/Tax ID: {household.get('ssn/tax_id', 'N/A')}")
            self.logger.info(f"   🔗 Relationships: {len(household.get('relationships', []))}")
        else:
            self.logger.info(f"\n🏠 **Household**: None")
    
    def _log_command_head_info(self, salesforce_account_information: Dict[str, Any]) -> None:
        """Log head information in command format."""
        head = salesforce_account_information.get('head')
        if head:
            self.logger.info(f"\n👑 **Head of Household**")
            self.logger.info(f"   📝 Name: {head['account_name']}")
            self.logger.info(f"   🏢 Type: {head['type']}")
            self.logger.info(f"   👑 Role: {head.get('role', 'N/A')}")
            self.logger.info(f"   📊 Stage: {head.get('stage', 'N/A')}")
            self.logger.info(f"   📧 Email: {head.get('email', 'N/A')}")
            self.logger.info(f"   📞 Phone: {head.get('phone', 'N/A')}")
            self.logger.info(f"   📍 Address: {head.get('mailing_address', 'N/A')}")
            self.logger.info(f"   🔒 SSN/Tax ID: {head.get('ssn/tax_id', 'N/A')}")
        else:
            self.logger.info(f"\n👑 **Head**: None")
    
    def _log_command_members_info(self, salesforce_account_information: Dict[str, Any]) -> None:
        """Log members information in command format."""
        members = salesforce_account_information.get('members', [])
        if members:
            self.logger.info(f"\n👥 **Household Members** ({len(members)})")
            for i, member in enumerate(members, 1):
                self.logger.info(f"   {i}. 📝 {member['account_name']}")
                self.logger.info(f"      🏢 Type: {member['type']}")
                self.logger.info(f"      👥 Role: {member.get('role', 'N/A')}")
                self.logger.info(f"      📊 Stage: {member.get('stage', 'N/A')}")
                self.logger.info(f"      📧 Email: {member.get('email', 'N/A')}")
                self.logger.info(f"      📞 Phone: {member.get('phone', 'N/A')}")
        else:
            self.logger.info(f"\n👥 **Members**: None")
    
    def _log_command_accounts_info(self, salesforce_account_information: Dict[str, Any]) -> None:
        """Log all accounts information in command format."""
        accounts = salesforce_account_information.get('accounts', [])
        if accounts:
            self.logger.info(f"\n📊 **All Accounts** ({len(accounts)})")
            for i, account in enumerate(accounts, 1):
                self.logger.info(f"\n{'─'*60}")
                self.logger.info(f"🏢 **Account {i}: {account['account_name']}**")
                self.logger.info(f"{'─'*60}")
                
                # Account type and role
                type_icon = "🏠" if account['type'] == 'Household' else "👤"
                self.logger.info(f"{type_icon} Type: {account['type']}")
                if account.get('role'):
                    role_icon = "👑" if account['role'] == 'Household Head' else "👥"
                    self.logger.info(f"{role_icon} Role: {account['role']}")
                
                # Account details
                self._log_account_details(account)
                
                # Relationships
                self._log_account_relationships(account)
        else:
            self.logger.info(f"\n📊 **All Accounts**: None")
    
    def _log_command_summary_statistics(self, salesforce_account_information: Dict[str, Any]) -> None:
        """Log summary statistics in command format."""
        names_found = salesforce_account_information.get('names_found', [])
        household = salesforce_account_information.get('household')
        head = salesforce_account_information.get('head')
        members = salesforce_account_information.get('members', [])
        accounts = salesforce_account_information.get('accounts', [])
        
        summary = {
            'total_names_found': len(names_found),
            'has_household': household is not None,
            'has_head': head is not None,
            'total_members': len(members),
            'total_accounts': len(accounts),
            'total_relationships': sum(len(acc.get('relationships', [])) for acc in accounts)
        }
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"📈 **SUMMARY STATISTICS**")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"📊 Total names found: {summary['total_names_found']}")
        self.logger.info(f"🏠 Has household: {'✅ Yes' if summary['has_household'] else '❌ No'}")
        self.logger.info(f"👑 Has head: {'✅ Yes' if summary['has_head'] else '❌ No'}")
        self.logger.info(f"👥 Total members: {summary['total_members']}")
        self.logger.info(f"📊 Total accounts: {summary['total_accounts']}")
        self.logger.info(f"🔗 Total relationships: {summary['total_relationships']}")
        self.logger.info(f"{'='*80}")
    
    def log_json_format(self, salesforce_account_information: Dict[str, Any]) -> None:
        """
        Log Salesforce Account Information in JSON format with summary.
        
        Args:
            salesforce_account_information: The structured account information
        """
        self.logger.info("🎯 === SALESFORCE ACCOUNT INFORMATION (JSON FORMAT) ===")
        self.logger.info("📄 **Complete Data Structure**")
        self.logger.info("="*80)
        
        import json
        json_str = json.dumps(salesforce_account_information, indent=2, default=str)
        self.logger.info(json_str)
        self.logger.info("="*80)
        
        # Log a summary of the JSON structure
        self.logger.info("\n📊 **JSON Structure Summary**")
        self.logger.info(f"📋 Names found: {len(salesforce_account_information.get('names_found', []))}")
        self.logger.info(f"🏠 Household: {'✅ Present' if salesforce_account_information.get('household') else '❌ Not present'}")
        self.logger.info(f"👑 Head: {'✅ Present' if salesforce_account_information.get('head') else '❌ Not present'}")
        self.logger.info(f"👥 Members: {len(salesforce_account_information.get('members', []))}")
        self.logger.info(f"📊 Accounts: {len(salesforce_account_information.get('accounts', []))}")
        
        total_relationships = sum(len(acc.get('relationships', [])) for acc in salesforce_account_information.get('accounts', []))
        self.logger.info(f"🔗 Total Relationships: {total_relationships}")


# Convenience functions for easy usage
def log_salesforce_account_information(salesforce_account_information: Dict[str, Any], 
                                     dropbox_account_folder_name: str,
                                     logger: Optional[logging.Logger] = None) -> None:
    """
    Convenience function to log Salesforce Account Information.
    
    Args:
        salesforce_account_information: The structured account information
        dropbox_account_folder_name: Name of the Dropbox account folder
        logger: Optional logger instance
    """
    salesforce_logger = SalesforceAccountLogger(logger)
    salesforce_logger.log_salesforce_account_information(salesforce_account_information, dropbox_account_folder_name)


def log_command_analysis(salesforce_account_information: Dict[str, Any],
                        logger: Optional[logging.Logger] = None) -> None:
    """
    Convenience function to log command analysis format.
    
    Args:
        salesforce_account_information: The structured account information
        logger: Optional logger instance
    """
    salesforce_logger = SalesforceAccountLogger(logger)
    salesforce_logger.log_command_analysis(salesforce_account_information)


def log_json_format(salesforce_account_information: Dict[str, Any],
                   logger: Optional[logging.Logger] = None) -> None:
    """
    Convenience function to log JSON format.
    
    Args:
        salesforce_account_information: The structured account information
        logger: Optional logger instance
    """
    salesforce_logger = SalesforceAccountLogger(logger)
    salesforce_logger.log_json_format(salesforce_account_information) 