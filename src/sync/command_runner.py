"""
Command Runner for Sync Operations

This module provides a CommandRunner class that executes various sync operations
between Dropbox and Salesforce, such as renaming files, creating/deleting accounts,
and managing account files.
"""

import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import dropbox
import os

from sync.dropbox_client.utils.dropbox_utils import get_renamed_path, list_folder_contents
from sync.dropbox_client.utils.file_utils import log_renamed_file

class CommandRunner:
    """Handles execution of sync commands between Dropbox and Salesforce."""
    
    def __init__(self, args):
        """Initialize the command runner with parsed arguments.
        
        Args:
            args: Command line arguments containing all options
        """
        self.args = args
        self.logger = logging.getLogger(__name__)
        self.report_logger = logging.getLogger('report')
        
        # Initialize context and data storage
        self._context: Dict[str, Any] = {}
        self._data: Dict[str, Any] = {}
        
        # Log initialization
        self.logger.info("Initializing CommandRunner")
        self.report_logger.info("\n=== COMMAND RUNNER INITIALIZED ===")
        
        # Log command source
        if args.commands:
            self.logger.info(f"Commands specified via --commands: {args.commands}")
            self.report_logger.info(f"Commands from --commands: {args.commands}")
        elif args.commands_file:
            self.logger.info(f"Commands file specified: {args.commands_file}")
            self.report_logger.info(f"Commands from file: {args.commands_file}")
        
        # Log account name if specified
        if args.dropbox_account_name:
            self.logger.info(f"Target Dropbox account: {args.dropbox_account_name}")
            self.report_logger.info(f"Target Dropbox account: {args.dropbox_account_name}")
    
    def set_context(self, key: str, value: Any) -> None:
        """Set a context value.
        
        Args:
            key: The context key
            value: The context value
        """
        self._context[key] = value
        self.logger.debug(f"Set context '{key}'")
    
    def get_context(self, key: str) -> Any:
        """Get a context value.
        
        Args:
            key: The context key to retrieve
            
        Returns:
            The context value
            
        Raises:
            KeyError: If the context key doesn't exist
        """
        if key not in self._context:
            raise KeyError(f"Context key '{key}' not found")
        return self._context[key]
    
    def set_data(self, key: str, value: Any) -> None:
        """Set a data value.
        
        Args:
            key: The data key
            value: The data value
        """
        self._data[key] = value
        self.logger.debug(f"Set data '{key}'")
    
    def get_data(self, key: str) -> Any:
        """Get a data value.
        
        Args:
            key: The data key to retrieve
            
        Returns:
            The data value
            
        Raises:
            KeyError: If the data key doesn't exist
        """
        if key not in self._data:
            raise KeyError(f"Data key '{key}' not found")
        return self._data[key]
    
    def _get_commands(self) -> List[str]:
        """Get the list of commands to execute from either --commands or --commands-file.
        
        Returns:
            List[str]: List of commands to execute
        """
        commands = []
        if self.args.commands:
            commands = [cmd.strip() for cmd in self.args.commands.split(',')]
            self.logger.info(f"Parsed {len(commands)} commands from --commands argument")
        elif self.args.commands_file:
            try:
                with open(self.args.commands_file, 'r') as f:
                    commands = [line.strip() for line in f if line.strip()]
                self.logger.info(f"Successfully read {len(commands)} commands from file: {self.args.commands_file}")
            except Exception as e:
                self.logger.error(f"Error reading commands file {self.args.commands_file}: {str(e)}")
                self.report_logger.info(f"Error reading commands file {self.args.commands_file}: {str(e)}")
                raise
        
        if not commands:
            self.logger.warning("No commands found to execute")
            self.report_logger.info("No commands found to execute")
        else:
            self.logger.info("Commands to execute:")
            self.report_logger.info("\nCommands to execute:")
            for i, cmd in enumerate(commands, 1):
                self.logger.info(f"  {i}. {cmd}")
                self.report_logger.info(f"  {i}. {cmd}")
        
        return commands
    
    def execute_commands(self) -> None:
        """Execute all specified commands in sequence."""
        start_time = datetime.now()
        self.logger.info("Starting command execution")
        self.report_logger.info("\n=== STARTING COMMAND EXECUTION ===")
        
        commands = self._get_commands()
        if not commands:
            self.logger.warning("No commands specified to execute")
            self.report_logger.info("No commands specified to execute")
            return
        
        total_commands = len(commands)
        successful_commands = 0
        failed_commands = 0
        
        for index, command in enumerate(commands, 1):
            try:
                self.logger.info(f"[{index}/{total_commands}] Executing command: {command}")
                self.report_logger.info(f"\n[{index}/{total_commands}] Executing command: {command}")
                
                command_start_time = datetime.now()
                self._execute_single_command(command)
                command_duration = datetime.now() - command_start_time
                
                self.logger.info(f"Command completed successfully in {command_duration}")
                self.report_logger.info(f"Command completed successfully in {command_duration}")
                successful_commands += 1
                
            except Exception as e:
                self.logger.error(f"Error executing command {command}: {str(e)}")
                self.report_logger.info(f"Error executing command {command}: {str(e)}")
                failed_commands += 1
                
                if not self.args.continue_on_error:
                    self.logger.error("Stopping execution due to error (--continue-on-error not specified)")
                    self.report_logger.info("Stopping execution due to error (--continue-on-error not specified)")
                    raise
        
        # Log execution summary
        total_duration = datetime.now() - start_time
        self.logger.info("\n=== COMMAND EXECUTION SUMMARY ===")
        self.logger.info(f"Total commands: {total_commands}")
        self.logger.info(f"Successful: {successful_commands}")
        self.logger.info(f"Failed: {failed_commands}")
        self.logger.info(f"Total duration: {total_duration}")
        
        self.report_logger.info("\n=== COMMAND EXECUTION SUMMARY ===")
        self.report_logger.info(f"Total commands: {total_commands}")
        self.report_logger.info(f"Successful: {successful_commands}")
        self.report_logger.info(f"Failed: {failed_commands}")
        self.report_logger.info(f"Total duration: {total_duration}")
    
    def _execute_single_command(self, command: str) -> None:
        """Execute a single command.
        
        Args:
            command: The command to execute
        """
        command_map = {
            'prefix-dropbox-account-files': self._prefix_dropbox_account_files,
            'prefix-dropbox-account-file': self._prefix_dropbox_account_file,
            'delete-salesforce-account': self._delete_salesforce_account,
            'create-salesforce-account': self._create_salesforce_account,
            'delete-salesforce-account-file': self._delete_salesforce_account_file,
            'upload-salesforce-account-file': self._upload_salesforce_account_file,
            'upload-salesforce-account-files': self._upload_salesforce_account_files,
            'download-salesforce-account-file': self._download_salesforce_account_file,
            'delete-salesforce-account-files': self._delete_salesforce_account_files
        }
        
        if command not in command_map:
            error_msg = f"Unknown command: {command}"
            self.logger.error(error_msg)
            self.report_logger.info(error_msg)
            raise ValueError(error_msg)
        
        self.logger.info(f"Executing command handler: {command}")
        command_map[command]()
    
    def _prefix_dropbox_account_files(self) -> None:
        """Prefix files in Dropbox account folder with date."""
        self.logger.info("Starting prefix-dropbox-account-files operation")
        self.report_logger.info("\n=== PREFIXING DROPBOX ACCOUNT FILES ===")
        
        # Get required context
        try:
            dropbox_client = self.get_context('dropbox_client')
            dropbox_root_folder = self.get_context('dropbox_root_folder')
            dropbox_account_info = self.get_data('dropbox_account_info')
            dropbox_account_folder_name = self.get_data('dropbox_account_folder_name')
            dropbox_salesforce_folder = dropbox_client.get_dropbox_salesforce_folder()
            
            self.logger.info(f"dropbox_client: {dropbox_client}")
            self.logger.info(f"dropbox_account_info: {dropbox_account_info}")
            self.logger.info(f"dropbox_account_folder_name: {dropbox_account_folder_name}")
            self.logger.info(f"dropbox_salesforce_folder: {dropbox_salesforce_folder}")

            # Verify account folder exists in Dropbox
            account_folders = dropbox_client.get_dropbox_account_names()
            if dropbox_account_folder_name not in account_folders:
                error_msg = f"Account folder '{dropbox_account_folder_name}' not found in Dropbox"
                self.logger.error(error_msg)
                self.report_logger.error(f"\n{error_msg}")
                return

            # Construct source and destination paths
            source_path = f"/{dropbox_root_folder}/{dropbox_account_folder_name}"
            dest_path = f"/{dropbox_salesforce_folder}/{dropbox_account_folder_name}"

            # Clean paths for Dropbox API
            source_path = source_path.replace('//', '/')
            dest_path = dest_path.replace('//', '/')

            self.logger.info(f"Source path: {source_path}")
            self.logger.info(f"Destination path: {dest_path}")

            # Check if folder already exists in Salesforce folder
            try:
                dropbox_client.dbx.files_get_metadata(dest_path)
                # Folder exists, prompt for deletion
                self.logger.info(f"Folder already exists in Salesforce folder: {dest_path}")
                self.report_logger.info(f"\nFolder already exists in Salesforce folder: {dest_path}")
                
                response = input(f"\nDo you want to delete the existing folder at {dest_path}? (y/N): ").strip().lower()
                if response != 'y':
                    self.logger.info("Operation cancelled by user")
                    self.report_logger.info("\nOperation cancelled by user")
                    return
                
                # Delete existing folder
                self.logger.info(f"Deleting existing folder: {dest_path}")
                self.report_logger.info(f"\nDeleting existing folder: {dest_path}")
                dropbox_client.dbx.files_delete_v2(dest_path)
                
            except dropbox.exceptions.ApiError as e:
                if not e.error.is_path() or not e.error.get_path().is_not_found():
                    # Re-raise if it's not a "not found" error
                    raise

            # Copy folder to Salesforce folder
            self.logger.info(f"Copying folder from {source_path} to {dest_path}")
            self.report_logger.info(f"\nCopying folder from {source_path} to {dest_path}")
            
            # Use the Dropbox API to copy the folder
            dropbox_client.dbx.files_copy_v2(source_path, dest_path)

            # List all files in the source folder to get original modified dates
            source_files = list_folder_contents(dropbox_client.dbx, source_path)
            source_file_dates = {}
            for file in source_files:
                if isinstance(file, dropbox.files.FileMetadata):
                    source_file_dates[file.name] = file.server_modified

            # List all files in the copied folder
            dest_files = list_folder_contents(dropbox_client.dbx, dest_path)
            
            # Process each file
            for file in dest_files:
                if isinstance(file, dropbox.files.FileMetadata):
                    # Check if file already has a date prefix (with or without space)
                    if len(file.name) >= 6 and file.name[:6].isdigit():
                        # Check if there's a space after the prefix or if the prefix is at the start
                        if len(file.name) == 6 or file.name[6] == ' ':
                            self.logger.info(f"Skipping already prefixed file: {file.name}")
                            self.report_logger.info(f"\nSkipping already prefixed file: {file.name}")
                            continue

                    # Get the original file's modified date
                    original_date = source_file_dates.get(file.name)
                    if original_date:
                        # Create date prefix from original file's modified date
                        date_prefix = original_date.strftime('%y%m%d')
                        
                        # Create new name with date prefix
                        new_name = f"{date_prefix} {file.name}"
                        
                        if new_name != file.name:
                            # Construct new path
                            new_path = f"{os.path.dirname(file.path_display)}/{new_name}"
                            new_path = new_path.replace('//', '/')
                            
                            # Move/rename the file
                            self.logger.info(f"Renaming file: {file.path_display} -> {new_path}")
                            self.report_logger.info(f"\nRenaming file: {file.path_display} -> {new_path}")
                            dropbox_client.dbx.files_move_v2(file.path_display, new_path)
                            
                            # Log the renamed file to the report logger
                            self.report_logger.info(f"Renamed file: {file.path_display} -> {new_path}")

            self.logger.info("Successfully completed prefix-dropbox-account-files operation")
            self.report_logger.info("\nSuccessfully completed prefix-dropbox-account-files operation")

        except Exception as e:
            error_msg = f"Error in prefix-dropbox-account-files operation: {str(e)}"
            self.logger.error(error_msg)
            self.report_logger.error(f"\n{error_msg}")
            raise
    
    def _prefix_dropbox_account_file(self) -> None:
        """Prefix a single file in Dropbox account folder with date."""
        self.logger.info("Starting prefix-dropbox-account-file operation")
        self.report_logger.info("\n=== PREFIXING SINGLE DROPBOX ACCOUNT FILE ===")
        # TODO: Implement single file prefixing logic
        self.logger.info("prefix-dropbox-account-file operation completed")
    
    def _delete_salesforce_account(self) -> None:
        """Delete an account from Salesforce."""
        self.logger.info("Starting delete-salesforce-account operation")
        self.report_logger.info("\n=== DELETING SALESFORCE ACCOUNT ===")
        # TODO: Implement account deletion logic
        self.logger.info("delete-salesforce-account operation completed")
    
    def _create_salesforce_account(self) -> None:
        """Create a new account in Salesforce."""
        self.logger.info("Starting create-salesforce-account operation")
        self.report_logger.info("\n=== CREATING SALESFORCE ACCOUNT ===")
        # TODO: Implement account creation logic
        self.logger.info("create-salesforce-account operation completed")
    
    def _delete_salesforce_account_file(self) -> None:
        """Delete a file from Salesforce account."""
        self.logger.info("Starting delete-salesforce-account-file operation")
        self.report_logger.info("\n=== DELETING SALESFORCE ACCOUNT FILE ===")
        # TODO: Implement file deletion logic
        self.logger.info("delete-salesforce-account-file operation completed")
    
    def _upload_salesforce_account_file(self) -> None:
        """Upload a single file to Salesforce account."""
        self.logger.info("Starting upload-salesforce-account-file operation")
        self.report_logger.info("\n=== UPLOADING SINGLE FILE TO SALESFORCE ===")
        # TODO: Implement single file upload logic
        self.logger.info("upload-salesforce-account-file operation completed")
    
    def _upload_salesforce_account_files(self) -> None:
        """Upload all files from Dropbox account to Salesforce."""
        self.logger.info("Starting upload-salesforce-account-files operation")
        self.report_logger.info("\n=== UPLOADING FILES TO SALESFORCE ===")
        
        try:
            # Get required context
            dropbox_client = self.get_context('dropbox_client')
            dropbox_root_folder = self.get_context('dropbox_root_folder')
            dropbox_account_folder_name = self.get_data('dropbox_account_folder_name')
            dropbox_salesforce_folder = dropbox_client.get_dropbox_salesforce_folder()
            
            # Construct source and destination paths
            source_path = f"/{dropbox_root_folder}/{dropbox_account_folder_name}"
            dest_path = f"/{dropbox_salesforce_folder}/{dropbox_account_folder_name}"
            
            # Clean paths for Dropbox API
            source_path = source_path.replace('//', '/')
            dest_path = dest_path.replace('//', '/')
            
            self.logger.info(f"Source path: {source_path}")
            self.logger.info(f"Destination path: {dest_path}")
            
            # Check if source folder exists
            try:
                dropbox_client.dbx.files_get_metadata(source_path)
            except dropbox.exceptions.ApiError as e:
                if e.error.is_path() and e.error.get_path().is_not_found():
                    error_msg = f"Source folder not found: {source_path}"
                    self.logger.error(error_msg)
                    self.report_logger.error(f"\n{error_msg}")
                    return
                raise
            
            # List all files in source folder
            files = list_folder_contents(dropbox_client.dbx, source_path)
            
            if not files:
                self.logger.info("No files found to upload")
                self.report_logger.info("\nNo files found to upload")
                return
            
            # Check if destination folder exists
            try:
                dropbox_client.dbx.files_get_metadata(dest_path)
                # Folder exists, prompt for deletion
                self.logger.info(f"Folder already exists in Salesforce: {dest_path}")
                self.report_logger.info(f"\nFolder already exists in Salesforce: {dest_path}")
                
                response = input(f"\nDo you want to delete the existing folder at {dest_path}? (y/N): ").strip().lower()
                if response != 'y':
                    self.logger.info("Operation cancelled by user")
                    self.report_logger.info("\nOperation cancelled by user")
                    return
                
                # Delete existing folder
                self.logger.info(f"Deleting existing folder: {dest_path}")
                self.report_logger.info(f"\nDeleting existing folder: {dest_path}")
                dropbox_client.dbx.files_delete_v2(dest_path)
                
            except dropbox.exceptions.ApiError as e:
                if not e.error.is_path() or not e.error.get_path().is_not_found():
                    # Re-raise if it's not a "not found" error
                    raise
            
            # Copy folder to Salesforce
            self.logger.info(f"Copying folder from {source_path} to {dest_path}")
            self.report_logger.info(f"\nCopying folder from {source_path} to {dest_path}")
            
            # Use the Dropbox API to copy the folder
            dropbox_client.dbx.files_copy_v2(source_path, dest_path)
            
            self.logger.info("Successfully completed upload-salesforce-account-files operation")
            self.report_logger.info("\nSuccessfully completed upload-salesforce-account-files operation")
            
        except Exception as e:
            error_msg = f"Error in upload-salesforce-account-files operation: {str(e)}"
            self.logger.error(error_msg)
            self.report_logger.error(f"\n{error_msg}")
            raise
    
    def _download_salesforce_account_file(self) -> None:
        """Download a file from Salesforce account."""
        self.logger.info("Starting download-salesforce-account-file operation")
        self.report_logger.info("\n=== DOWNLOADING FILE FROM SALESFORCE ===")
        # TODO: Implement file download logic
        self.logger.info("download-salesforce-account-file operation completed")
    
    def _delete_salesforce_account_files(self) -> None:
        """Delete all files from Salesforce account."""
        self.logger.info("Starting delete-salesforce-account-files operation")
        self.report_logger.info("\n=== DELETING SALESFORCE ACCOUNT FILES ===")
        
        try:
            # Get required context
            salesforce_client = self.get_context('salesforce_client')
            salesforce_account_id = self.get_data('salesforce_account_id')
            salesforce_acount_file_names = self.get_data('salesforce_acount_file_names')

            
            if not salesforce_account_id:
                error_msg = "No Salesforce account ID found"
                self.logger.error(error_msg)
                self.report_logger.error(f"\n{error_msg}")
                return
            
            self.logger.info(f"Salesforce account ID: {salesforce_account_id}")
            
            # Get all files associated with the account
            files = salesforce_acount_file_names
            
            if not files:
                self.logger.info("No files found to delete")
                self.report_logger.info("\nNo files found to delete")
                return
            
            # Prompt for confirmation
            self.logger.info(f"Found {len(files)} files to delete")
            self.report_logger.info(f"\nFound {len(files)} files to delete:")
            for file in files:
                self.report_logger.info(f"  - {file['Title']}")
            
            response = input(f"\nDo you want to delete all {len(files)} files? (y/N): ").strip().lower()
            if response != 'y':
                self.logger.info("Operation cancelled by user")
                self.report_logger.info("\nOperation cancelled by user")
                return
            
            # Delete each file
            for file in files:
                try:
                    self.logger.info(f"Deleting file: {file['Title']}")
                    self.report_logger.info(f"\nDeleting file: {file['Title']}")
                    salesforce_client.delete_file(file['Id'])
                except Exception as e:
                    error_msg = f"Error deleting file {file['Title']}: {str(e)}"
                    self.logger.error(error_msg)
                    self.report_logger.error(f"\n{error_msg}")
                    if not self.args.continue_on_error:
                        raise
            
            self.logger.info("Successfully completed delete-salesforce-account-files operation")
            self.report_logger.info("\nSuccessfully completed delete-salesforce-account-files operation")
            
        except Exception as e:
            error_msg = f"Error in delete-salesforce-account-files operation: {str(e)}"
            self.logger.error(error_msg)
            self.report_logger.error(f"\n{error_msg}")
            raise 