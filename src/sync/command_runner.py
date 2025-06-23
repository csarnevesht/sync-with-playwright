"""
Command Runner for Sync Operations

This module provides a CommandRunner class that executes various sync operations
between Dropbox and Salesforce, such as renaming files, creating/deleting accounts,
and managing account files.
"""

import glob
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import dropbox
import os
import tempfile
import re
import fnmatch
import time

from sync.dropbox_client.utils.dropbox_utils import get_renamed_path, list_dropbox_folder_contents
from sync.dropbox_client.utils.file_utils import log_renamed_file
from sync.dropbox_client.utils.logging_utils import log_dropbox_app_file_info, log_dropbox_account_app_files_info, log_app_files_notes_summary, log_app_files_processing_summary
from sync.salesforce_client.utils.file_upload import upload_account_file, upload_account_file_with_retries

class CommandRunner:
    """Handles execution of sync commands between Dropbox and Salesforce."""
    
    def __init__(self, args, log_dir: str = None):
        """Initialize the command runner with parsed arguments.
        
        Args:
            args: Command line arguments containing all options
            log_dir: Optional log directory path for saving analysis reports
        """
        self.args = args
        self.log_dir = log_dir
        self.logger = logging.getLogger(__name__)
        self.report_logger = logging.getLogger('report')
        self.summary_logger = logging.getLogger('summary')
        
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
        self.logger.debug(f"Set data {key}: {value}")
    
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
        # Check if this command should be skipped for the current account
        dropbox_account_name = getattr(self.args, 'dropbox_account_name', None)
        if dropbox_account_name:
            from sync.utils.name_utils import should_skip_command_for_account
            if should_skip_command_for_account(dropbox_account_name, command):
                self.logger.info(f"Skipping command '{command}' for account '{dropbox_account_name}' due to special case rule")
                self.report_logger.info(f"Skipping command '{command}' for account '{dropbox_account_name}' due to special case rule")
                return
        
        command_map = {
            'prefix-dropbox-account-files': self._prefix_dropbox_account_files,
            'prefix-dropbox-account-file': self._prefix_dropbox_account_file,
            'delete-salesforce-account': self._delete_salesforce_account,
            'create-salesforce-account': self._create_salesforce_account,
            'delete-salesforce-account-file': self._delete_salesforce_account_file,
            'upload-salesforce-account-file': self._upload_salesforce_account_file,
            'upload-salesforce-account-files': self._upload_salesforce_account_files,
            'download-salesforce-account-file': self._download_salesforce_account_file,
            'delete-salesforce-account-files': self._delete_salesforce_account_files,
            'force-delete-salesforce-account-files': self._force_delete_salesforce_account_files,
            'extract-dropbox-account-app-files-info': self._handle_extract_dropbox_account_app_files_info,
            'store-in-supabase': self._store_in_supabase,
            'search-supabase': self._search_supabase,
            'list-dropbox-account-app-files': self._list_dropbox_account_app_files,
            'log-dropbox-account-information': self._handle_log_dropbox_account_information,
            'log-dropbox-account-information-json': self._handle_log_dropbox_account_information_json,
            'analyze-account-data': self._handle_analyze_account_data,
            'copy-dropbox-account-files-preserve-dates': self._copy_dropbox_account_files_preserve_dates
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
            file_manager = self.get_context('file_manager')
            dropbox_client = self.get_context('dropbox_client')
            dropbox_root_folder = self.get_context('dropbox_root_folder')
            dropbox_account_info = self.get_data('dropbox_account_info')
            dropbox_account_folder_name = self.get_data('dropbox_account_folder_name')
            dropbox_salesforce_folder = dropbox_client.get_dropbox_salesforce_folder()
        

            self.logger.info(f"file_manager: {file_manager}")
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
                
                # response = input(f"\nDo you want to delete the existing Dropbox folder at {dest_path}? (y/N): ").strip().lower()
                # if response != 'y':
                #     self.logger.info("Operation cancelled by user")
                #     self.report_logger.info("\nOperation cancelled by user")
                #     return
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
            source_files = list_dropbox_folder_contents(dropbox_client.dbx, source_path)
            source_file_dates = {}
            for file in source_files:
                if isinstance(file, dropbox.files.FileMetadata):
                    source_file_dates[file.name] = file.server_modified

            # List all files in the copied folder
            dest_files = list_dropbox_folder_contents(dropbox_client.dbx, dest_path)
            
            # Process each file
            for file in dest_files:
                if isinstance(file, dropbox.files.FileMetadata):
                    # Check if file already has a date prefix (with or without space)
                    if len(file.name) >= 6 and file.name[:6].isdigit():
                        # Validate that the 6 digits form a valid date (YYMMDD)
                        prefix = file.name[:6]
                        year = int(prefix[:2])
                        month = int(prefix[2:4])
                        day = int(prefix[4:6])
                        
                        # Check if it's a valid date
                        try:
                            # Convert YY to YYYY (assuming 20xx for years < 50, 19xx for years >= 50)
                            full_year = 2000 + year if year < 50 else 1900 + year
                            datetime.datetime(full_year, month, day)
                            # If we get here, it's a valid date
                            self.logger.info(f"Skipping already prefixed file: {file.name}")
                            self.report_logger.info(f"\nSkipping already prefixed file: {file.name}")
                            continue
                        except ValueError:
                            # Not a valid date, continue with renaming
                            pass

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
            browser = self.get_context('browser')
            page = self.get_context('page')
            dropbox_client = self.get_context('dropbox_client')
            dropbox_root_folder = self.get_context('dropbox_root_folder')
            dropbox_account_folder_name = self.get_data('dropbox_account_folder_name')
            dropbox_salesforce_folder = dropbox_client.get_dropbox_salesforce_folder()
            file_manager = self.get_context('file_manager')
            account_manager = self.get_context('account_manager')

            # Construct source path
            source_path = f"/{dropbox_salesforce_folder}/{dropbox_account_folder_name}"
            
            # Clean paths for Dropbox API
            source_path = source_path.replace('//', '/')
            
            self.logger.info(f"Source path: {source_path}")
            
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
            files = list_dropbox_folder_contents(dropbox_client.dbx, source_path)
            
            if not files:
                self.logger.info("No files found to upload to Salesforce")
                self.report_logger.info("\nNo files found to upload to Salesforce")
                return
            
            # Create a temporary directory for downloads
            temp_dir = os.path.join(os.getcwd(), 'temp_downloads')
            os.makedirs(temp_dir, exist_ok=True)
            
            try:
                # Download and upload each file
                self.logger.info(f"Download and upload {len(files)} files")
                for file in files:
                    if isinstance(file, dropbox.files.FileMetadata):
                        self.logger.info(f"Processing file: {file.name}")
                        self.report_logger.info(f"\nProcessing file: {file.name}")
                        
                        # Download file from Dropbox
                        logging.info(f"Downloading file: {file.name}")
                        local_path = os.path.join(temp_dir, file.name)
                        self.logger.info(f"Downloading to: {local_path}")
                        dropbox_client.dbx.files_download_to_file(local_path, file.path_display)
                        
                        account_manager.navigate_back_to_account_page()

                        # Navigate to files section
                        logging.info("Navigating to files section")
                        num_files = file_manager.navigate_to_account_files_click_on_files_card_to_facilitate_file_operation()
                        if num_files == -1:
                            logging.error("Failed to navigate to Files")
                            return

                        # Check if file already exists in Salesforce
                        file_name = os.path.splitext(file.name)[0]  # Remove extension for comparison
                        logging.info(f'checking if file {file_name} exists in salesforce')
                        if file_manager.search_salesforce_file(file_name):
                            self.logger.info(f"File {file_name} already exists in Salesforce, skipping upload")
                            self.report_logger.info(f"\nFile {file_name} already exists in Salesforce, skipping upload")
                            # Clean up the downloaded file since we won't be using it
                            os.remove(local_path)
                            self.logger.info(f"Cleaned up temporary file: {local_path}")
                            continue
        
                        # Upload file to Salesforce via browser with retries
                        self.logger.info(f"Uploading to Salesforce: {file.name}")
                        self.logger.info(f"Uploading file: {local_path}")
                        self.logger.info("current url: {page.url}")
                        if not upload_account_file_with_retries(page, local_path, expected_items=num_files+1):
                            logging.error(f"Failed to upload file after all retries: {local_path}")
                            if not self.args.continue_on_error:
                                raise Exception(f"Failed to upload file: {local_path}")
                        
                        # Clean up the downloaded file
                        os.remove(local_path)
                        self.logger.info(f"Cleaned up temporary file: {local_path}")
                
            except Exception as e:
                self.logger.error(f"Error processing files: {str(e)}")
                raise
            finally:
                # Clean up temporary directory
                try:
                    os.rmdir(temp_dir)
                    self.logger.info(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    self.logger.warning(f"Could not remove temporary directory {temp_dir}: {str(e)}")
            
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
    
    def _delete_salesforce_account_files(self, force: bool = False) -> None:
        """Delete all files from Salesforce account.
        
        Args:
            force: If True, skip the confirmation prompt
        """
        self.logger.info("Starting delete-salesforce-account-files operation")
        self.report_logger.info("\n=== DELETING SALESFORCE ACCOUNT FILES ===")
        
        try:
            # Get required context
            salesforce_account_id = self.get_data('salesforce_account_id')
            salesforce_acount_file_names = self.get_data('salesforce_acount_file_names')
            file_manager = self.get_context('file_manager')
            
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
            
            # Prompt for confirmation unless force is True
            self.logger.info(f"Found {len(files)} files to delete")
            self.report_logger.info(f"\nFound {len(files)} files to delete:")
            for file in files:
                self.report_logger.info(f"  - {file}")
            
            if not force:
                response = input(f"\nDo you want to delete all {len(files)} Salesforce account files? (y/N): ").strip().lower()
                if response != 'y':
                    self.logger.info("Operation cancelled by user")
                    self.report_logger.info("\nOperation cancelled by user")
                    return
            
            # Delete each file
            for file in files:
                try:
                    self.logger.info(f"Deleting file: {file}")
                    self.report_logger.info(f"\nDeleting file: {file}")
                    logging.info(f"Attempting to delete first file: {file}")
        
                    if not file_manager.delete_salesforce_file(file):
                        logging.error(f"Failed to delete file: {file}")
                        return
                except Exception as e:
                    error_msg = f"Error deleting file {file}: {str(e)}"
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

    def _force_delete_salesforce_account_files(self) -> None:
        """Force delete all files from Salesforce account without confirmation prompt."""
        self.logger.info("Starting force-delete-salesforce-account-files operation")
        self.report_logger.info("\n=== FORCE DELETING SALESFORCE ACCOUNT FILES ===")
        self._delete_salesforce_account_files(force=True)

    def _handle_extract_dropbox_account_app_files_info(self) -> None:
        """Handle the extract-dropbox-account-app-files-info command."""
        self.logger.info("Executing command handler: extract-dropbox-account-app-files-info")
        self.logger.info("Starting extract-dropbox-account-app-files-info operation")
        
        # Get the folder name and file filter from data and args
        dropbox_account_folder_name = self.get_data('dropbox_account_folder_name')
        file_filter = self.args.file_filter
        
        # Call the implementation method with required arguments
        self._extract_dropbox_account_app_files_info(dropbox_account_folder_name, file_filter)

    def _has_complete_account_info(self, dropbox_account_search_result: Dict[str, Any]) -> bool:
        """Check if the dropbox account search result has complete account info including birthdate and gender.
        
        Args:
            dropbox_account_search_result: Dictionary containing account search result
            
        Returns:
            bool: True if complete account info is present (including birthdate and gender), False otherwise
        """
        account_data = dropbox_account_search_result.get('account_data', {})
        
        # Required fields for complete account info (email is optional)
        required_fields = {
            'name', 'first_name', 'last_name', 'address', 'city', 'state', 'zip', 'phone', 'birthdate', 'gender'
        }
        
        # Check if all required fields are present and not empty
        for field in required_fields:
            value = account_data.get(field, '')
            if not value or str(value).strip() == '' or str(value).lower() in ['nan', 'none', 'null']:
                return False
        
        # Check if we have a match found
        search_info = dropbox_account_search_result.get('search_info', {})
        match_info = search_info.get('match_info', {})
        match_status = match_info.get('match_status', '')
        
        # Only consider it complete if we found a match
        if 'match found' not in match_status.lower():
            return False
        
        return True

    def _extract_dropbox_account_app_files_info(self, dropbox_account_folder_name: str, file_filter: Optional[str] = None) -> None:
        """Extract information from application files in the specified Dropbox account folder."""
        start_time = time.time()
        self.logger.info("\n=== GETTING DROPBOX APPLICATION INFORMATION ===")
        self.logger.info(f"dropbox_account_folder_name: {dropbox_account_folder_name}")
        self.logger.info(f"dropbox_account_name_parts: {self._data.get('dropbox_account_name_parts')}")
        
        # Check if we already have complete account info from dropbox search
        try:
            dropbox_account_search_result = self.get_data('dropbox_account_info')
            if dropbox_account_search_result and self._has_complete_account_info(dropbox_account_search_result):
                info = f"Skipped app files extraction for Dropbox Account Folder '{dropbox_account_folder_name}' - complete account info already available from Dropbox Client List File\n"
                self.logger.info(info)
                self.report_logger.info(info)
                self.summary_logger.info(info)
                
                # Set empty app files data since we skipped extraction
                self.set_data('account_info_from_app_files', {
                    'total_files_processed': 0,
                    'files_with_complete_info': 0,
                    'files_with_partial_info': 0,
                    'files_with_no_info': 0,
                    'best_available_info': {},
                    'file_details': {},
                    'has_complete_account_info': False,
                    'owner': {},
                    'jointOwner': {},
                    'application_type': 'N/A',
                    'status': 'Skipped - Complete info from Client List File',
                    'notes': ['App files extraction skipped due to complete account info from Client List File']
                })
                return
        except KeyError:
            # No dropbox_account_info found, continue with app files extraction
            pass
        
        if file_filter:
            self.logger.info(f"Using file filter: {file_filter} (only files matching this pattern will be processed)")
            self.logger.info(f"\nUsing file filter: {file_filter} (only files matching this pattern will be processed)")
        
        try:
            # Get Dropbox client and folder names from context
            dropbox_client = self.get_context('dropbox_client')
            dropbox_root_folder = self.get_context('dropbox_root_folder')
            
            # Construct folder path
            folder_path = f"/{dropbox_root_folder}/{dropbox_account_folder_name}"
            folder_path = folder_path.replace('//', '/')
            
            # First pass: Extract all fields except birthdate and gender, skipping 0-length files
            extract_start = time.time()
            
            # Always skip zero-length files during initial processing
            summary_data = dropbox_client.extract_app_files_info(
                folder_path, 
                extract_fields={'name', 'address'}, 
                file_filter=file_filter,
                skip_zero_length_if_account_info_exists=True,  # Always skip 0-length files initially
                report_logger=self.report_logger,
                log_dir=self.log_dir,
                dropbox_account_folder_name=dropbox_account_folder_name
            )
            extract_time = time.time() - extract_start
            self.logger.info(f"Extraction completed in {extract_time:.2f} seconds")
            
            # Log if we skipped any zero-length files
            if summary_data and 'skipped_zero_length_files' in summary_data and summary_data['skipped_zero_length_files'] > 0:
                self.logger.info(f"Skipped {summary_data['skipped_zero_length_files']} zero-length files during initial processing")
                self.report_logger.info(f"Skipped {summary_data['skipped_zero_length_files']} zero-length files during initial processing")
            
            # Store the aggregated account info from app files
            if summary_data:
                # Get the list of files that were processed
                # The app file extractor returns files in all_folder_app_files
                folder_path_key = folder_path
                files = summary_data.get('all_folder_app_files', {}).get(folder_path_key, [])
                
                # Log if no application files were found
                no_files_msg = f"  🚫 No application files found for {folder_path}"
                self.logger.info(no_files_msg)
                self.report_logger.info(no_files_msg)
                self.summary_logger.info(no_files_msg)
                
                # Aggregate the account info
                aggregated_info = self._aggregate_account_info_from_app_files(summary_data, files, dropbox_account_folder_name)
                
                # Store the aggregated info
                self.set_data('account_info_from_app_files', aggregated_info)
                
                # Log the results
                self.logger.info(f"[_extract_dropbox_account_app_files_info] ✅ Successfully extracted information from {len(files)} application files")
                self.logger.info(f"[_extract_dropbox_account_app_files_info] Files with complete info: {aggregated_info.get('files_with_complete_info', 0)}")
                self.logger.info(f"[_extract_dropbox_account_app_files_info] Files with partial info: {aggregated_info.get('files_with_partial_info', 0)}")
                self.logger.info(f"[_extract_dropbox_account_app_files_info] Files with no info: {aggregated_info.get('files_with_no_info', 0)}")
                
                # Also log to summary_logger
                self.summary_logger.info(f"[_extract_dropbox_account_app_files_info] ✅ Successfully extracted information from {len(files)} application files")
                self.summary_logger.info(f"[_extract_dropbox_account_app_files_info] Files with complete info: {aggregated_info.get('files_with_complete_info', 0)}")
                self.summary_logger.info(f"[_extract_dropbox_account_app_files_info] Files with partial info: {aggregated_info.get('files_with_partial_info', 0)}")
                self.summary_logger.info(f"[_extract_dropbox_account_app_files_info] Files with no info: {aggregated_info.get('files_with_no_info', 0)}")
                
                # Log detailed notes for each app file
                if summary_data and 'file_info' in summary_data:
                    log_app_files_processing_summary(
                        summary_data,
                        self.report_logger
                    )
                
                # Check if we have complete account info from app files
                has_complete_account_info = aggregated_info.get('has_complete_account_info', False)
                
                if has_complete_account_info:
                    self.logger.info("[_extract_dropbox_account_app_files_info] ✅ Complete account information found from app files")
                    self.report_logger.info("[_extract_dropbox_account_app_files_info] ✅ Complete account information found from app files")
                    self.summary_logger.info("[_extract_dropbox_account_app_files_info] ✅ Complete account information found from app files")
                else:
                    self.logger.info("[_extract_dropbox_account_app_files_info] ⚠️ Incomplete account information from app files")
                    self.report_logger.info("[_extract_dropbox_account_app_files_info] ⚠️ Incomplete account information from app files")
                    self.summary_logger.info("[_extract_dropbox_account_app_files_info] ⚠️ Incomplete account information from app files")
                    
                    # If we don't have complete account info, process the 0-length files
                    if summary_data and 'skipped_zero_length_files' in summary_data and summary_data['skipped_zero_length_files'] > 0:
                        self.logger.info(f"[_extract_dropbox_account_app_files_info] Processing {summary_data['skipped_zero_length_files']} zero-length files to try to get complete account info")
                        self.report_logger.info(f"[_extract_dropbox_account_app_files_info] Processing {summary_data['skipped_zero_length_files']} zero-length files to try to get complete account info")
                        self.summary_logger.info(f"[_extract_dropbox_account_app_files_info] Processing {summary_data['skipped_zero_length_files']} zero-length files to try to get complete account info")
                        
                        # Second pass: Process 0-length files to try to get complete account info
                        zero_length_summary = dropbox_client.extract_app_files_info(
                            folder_path, 
                            extract_fields={'name', 'address'}, 
                            file_filter=file_filter,
                            skip_zero_length_if_account_info_exists=False,  # Process 0-length files
                            report_logger=self.report_logger,
                            log_dir=self.log_dir,
                            dropbox_account_folder_name=dropbox_account_folder_name
                        )
                        
                        if zero_length_summary:
                            # Get the additional files that were processed
                            additional_files = zero_length_summary.get('files', [])
                            
                            # Combine the results
                            combined_files = files + additional_files
                            combined_summary = {
                                'files': combined_files,
                                'extracted_info': summary_data.get('extracted_info', []) + zero_length_summary.get('extracted_info', []),
                                'total_files_processed': len(combined_files),
                                'skipped_zero_length_files': 0  # All files processed now
                            }
                            
                            # Re-aggregate with all files
                            updated_aggregated_info = self._aggregate_account_info_from_app_files(combined_summary, combined_files, dropbox_account_folder_name)
                            
                            # Update the stored info
                            self.set_data('account_info_from_app_files', updated_aggregated_info)
                            
                            # Log the updated results
                            self.logger.info(f"[_extract_dropbox_account_app_files_info] ✅ After processing zero-length files: {len(combined_files)} total files processed")
                            self.logger.info(f"[_extract_dropbox_account_app_files_info] Files with complete info: {updated_aggregated_info.get('files_with_complete_info', 0)}")
                            self.logger.info(f"[_extract_dropbox_account_app_files_info] Files with partial info: {updated_aggregated_info.get('files_with_partial_info', 0)}")
                            self.logger.info(f"[_extract_dropbox_account_app_files_info] Files with no info: {updated_aggregated_info.get('files_with_no_info', 0)}")
                            
                            # Also log to summary_logger
                            self.summary_logger.info(f"[_extract_dropbox_account_app_files_info] ✅ After processing zero-length files: {len(combined_files)} total files processed")
                            self.summary_logger.info(f"[_extract_dropbox_account_app_files_info] Files with complete info: {updated_aggregated_info.get('files_with_complete_info', 0)}")
                            self.summary_logger.info(f"[_extract_dropbox_account_app_files_info] Files with partial info: {updated_aggregated_info.get('files_with_partial_info', 0)}")
                            self.summary_logger.info(f"[_extract_dropbox_account_app_files_info] Files with no info: {updated_aggregated_info.get('files_with_no_info', 0)}")
                            
                            if updated_aggregated_info.get('has_complete_account_info', False):
                                self.logger.info("[_extract_dropbox_account_app_files_info] ✅ Complete account information now found after processing zero-length files")
                                self.report_logger.info("[_extract_dropbox_account_app_files_info] ✅ Complete account information now found after processing zero-length files")
                                self.summary_logger.info("[_extract_dropbox_account_app_files_info] ✅ Complete account information now found after processing zero-length files")
                            else:
                                self.logger.info("[_extract_dropbox_account_app_files_info] ⚠️ Still incomplete account information after processing zero-length files")
                                self.report_logger.info("[_extract_dropbox_account_app_files_info] ⚠️ Still incomplete account information after processing zero-length files")
                                self.summary_logger.info("[_extract_dropbox_account_app_files_info] ⚠️ Still incomplete account information after processing zero-length files")
                
                # Store the summary data for reporting
                self.set_data('app_files_extraction_summary', summary_data)
                
                # Create individual account report file
                self._create_account_report_file(dropbox_account_folder_name, aggregated_info, summary_data)
                
            else:
                no_summary_msg = "❌ No summary data returned from app files extraction"
                self.logger.warning(no_summary_msg)
                self.report_logger.warning(no_summary_msg)
                self.summary_logger.warning(no_summary_msg)
                
                # Set empty app files data since extraction failed
                self.set_data('account_info_from_app_files', {
                    'total_files_processed': 0,
                    'files_with_complete_info': 0,
                    'files_with_partial_info': 0,
                    'files_with_no_info': 0,
                    'best_available_info': {},
                    'file_details': {},
                    'has_complete_account_info': False,
                    'owner': {},
                    'jointOwner': {},
                    'application_type': 'N/A',
                    'status': 'Failed - No summary data returned',
                    'notes': ['App files extraction failed - no summary data returned']
                })
                
                # Create individual account report file even for failed extraction
                self._create_account_report_file(dropbox_account_folder_name, {
                    'total_files_processed': 0,
                    'files_with_complete_info': 0,
                    'files_with_partial_info': 0,
                    'files_with_no_info': 0,
                    'best_available_info': {},
                    'file_details': {},
                    'has_complete_account_info': False,
                    'status': 'Failed - No summary data returned'
                }, {})
                
        except Exception as e:
            error_msg = f"❌ Error extracting app files info: {str(e)}"
            self.logger.error(error_msg)
            self.report_logger.error(error_msg)
            self.summary_logger.error(error_msg)
            
            # Set empty app files data since extraction failed with exception
            self.set_data('account_info_from_app_files', {
                'total_files_processed': 0,
                'files_with_complete_info': 0,
                'files_with_partial_info': 0,
                'files_with_no_info': 0,
                'best_available_info': {},
                'file_details': {},
                'has_complete_account_info': False,
                'owner': {},
                'jointOwner': {},
                'application_type': 'N/A',
                'status': f'Failed - Exception: {str(e)}',
                'notes': [f'App files extraction failed with exception: {str(e)}']
            })
            
            # Create individual account report file even for failed extraction
            self._create_account_report_file(dropbox_account_folder_name, {
                'total_files_processed': 0,
                'files_with_complete_info': 0,
                'files_with_partial_info': 0,
                'files_with_no_info': 0,
                'best_available_info': {},
                'file_details': {},
                'has_complete_account_info': False,
                'status': f'Failed - Exception: {str(e)}'
            }, {})
            
            raise
        
        total_time = time.time() - start_time
        self.logger.info(f"=== APP FILES EXTRACTION COMPLETED IN {total_time:.2f} SECONDS ===")
        self.report_logger.info(f"=== APP FILES EXTRACTION COMPLETED IN {total_time:.2f} SECONDS ===")

    def _aggregate_account_info_from_app_files(self, summary_data: Dict[str, Any], files: List[dropbox.files.FileMetadata], dropbox_account_folder_name: str) -> Dict[str, Any]:
        """Aggregate account information from multiple app files into a single structure.
        
        Args:
            summary_data: The summary data from app file extraction
            files: List of files that were processed
            dropbox_account_folder_name: The name of the Dropbox account folder
            
        Returns:
            Dict containing aggregated account information
        """
        aggregated_info = {
            'total_files_processed': len(files),
            'files_with_complete_info': 0,
            'files_with_partial_info': 0,
            'files_with_no_info': 0,
            'best_available_info': {},
            'file_details': {},
            'has_complete_account_info': False
        }
        
        if not summary_data or 'file_info' not in summary_data:
            aggregated_info['files_with_no_info'] = len(files)
            return aggregated_info
        
        file_info = summary_data['file_info']
        best_info = {}
        best_completeness_score = 0
        
        # Process each file's information
        for file_path, info in file_info.items():
            if not info:
                aggregated_info['files_with_no_info'] += 1
                continue
            
            # Calculate completeness score for this file
            completeness_score = 0
            has_owner_info = False
            has_joint_owner_info = False
            
            # Check for owner information
            if info.get('owner'):
                owner_data = info['owner']
                owner_fields = [
                    'firstName', 'lastName', 'dateOfBirth', 'gender',
                    'mailingAddressStreet', 'mailingAddressCity',
                    'mailingAddressState', 'mailingAddressZip',
                    'phoneNumber', 'emailAddress'
                ]
                owner_score = sum(1 for field in owner_fields if owner_data.get(field))
                if owner_score >= 4:  # At least 4 fields including name and DOB
                    has_owner_info = True
                    completeness_score += owner_score
            
            # Check for joint owner information
            if info.get('jointOwner'):
                joint_owner_data = info['jointOwner']
                joint_owner_fields = [
                    'firstName', 'lastName', 'dateOfBirth', 'gender',
                    'mailingAddressStreet', 'mailingAddressCity',
                    'mailingAddressState', 'mailingAddressZip',
                    'phoneNumber', 'emailAddress'
                ]
                joint_owner_score = sum(1 for field in joint_owner_fields if joint_owner_data.get(field))
                if joint_owner_score >= 4:  # At least 4 fields including name and DOB
                    has_joint_owner_info = True
                    completeness_score += joint_owner_score
            
            # Update file details
            aggregated_info['file_details'][file_path] = {
                'has_owner_info': has_owner_info,
                'has_joint_owner_info': has_joint_owner_info,
                'completeness_score': completeness_score,
                'info': info
            }
            
            # Update best available info if this file has better information
            if completeness_score > best_completeness_score:
                best_completeness_score = completeness_score
                best_info = info.copy()
            
            # Update statistics
            if has_owner_info or has_joint_owner_info:
                if completeness_score >= 8:  # High completeness
                    aggregated_info['files_with_complete_info'] += 1
                else:
                    aggregated_info['files_with_partial_info'] += 1
            else:
                aggregated_info['files_with_no_info'] += 1
        
        # Store the best available info
        aggregated_info['best_available_info'] = best_info
        aggregated_info['has_complete_account_info'] = best_completeness_score >= 8
        
        return aggregated_info

    def _build_dropbox_account_information(self) -> Dict[str, Any]:
        """Build the dropbox_account_information structure from available data.
        
        Returns:
            Dict containing the structured dropbox account information
        """
        dropbox_account_information = {
            'names_found': [],
            'client_list_data': None,
            'application_data': None,
            'app_files_extraction_summary': None,
            'accounts': []
        }
        
        # Get the account folder name
        dropbox_account_folder_name = self.get_data('dropbox_account_folder_name')
        if dropbox_account_folder_name:
            dropbox_account_information['names_found'].append(dropbox_account_folder_name)
        
        # Get client list file data
        try:
            client_list_file_data = self.get_data('dropbox_account_info')
        except KeyError:
            client_list_file_data = None
        if client_list_file_data:
            dropbox_account_information['client_list_data'] = client_list_file_data
            # Create account object from client list file data
            account_data = client_list_file_data.get('account_data', {})
            search_info = client_list_file_data.get('search_info', {})
            match_info = search_info.get('match_info', {})
            if account_data:
                # Add the actual name found in client list file to names_found
                client_list_name = account_data.get('name', '')
                if client_list_name and client_list_name not in dropbox_account_information['names_found']:
                    dropbox_account_information['names_found'].append(client_list_name)
                
                client_list_account = {
                    'account_name': dropbox_account_folder_name,
                    'source': 'dropbox_client_list',
                    'account_type': 'Primary',
                    'first_name': account_data.get('first_name', ''),
                    'middle_name': account_data.get('middle_name', ''),
                    'last_name': account_data.get('last_name', ''),
                    'birthdate': account_data.get('birthdate', ''),
                    'gender': account_data.get('gender', ''),
                    'phone': account_data.get('phone', ''),
                    'address': account_data.get('address', ''),
                    'email': account_data.get('email', ''),
                    'additional_info': account_data.get('additional_info', ''),
                    'match_status': match_info.get('match_status', ''),
                    'drivers_license': client_list_file_data.get('drivers_license')
                }
                dropbox_account_information['accounts'].append(client_list_account)
        
        # Get application files data
        try:
            account_info_from_app_files = self.get_data('account_info_from_app_files')
        except KeyError:
            account_info_from_app_files = None
        if not account_info_from_app_files:
            # Set default empty structure if not available
            account_info_from_app_files = {
                'total_files_processed': 0,
                'files_with_complete_info': 0,
                'files_with_partial_info': 0,
                'files_with_no_info': 0,
                'best_available_info': {},
                'file_details': {},
                'has_complete_account_info': False,
                'owner': {},
                'jointOwner': {},
                'application_type': 'N/A',
                'status': 'Not available',
                'notes': ['Application files data not available']
            }
            self.set_data('account_info_from_app_files', account_info_from_app_files)
        
        dropbox_account_information['application_data'] = account_info_from_app_files
        
        # Get app files extraction summary data
        try:
            app_files_extraction_summary = self.get_data('app_files_extraction_summary')
        except KeyError:
            app_files_extraction_summary = None
        dropbox_account_information['app_files_extraction_summary'] = app_files_extraction_summary
        
        # Create account objects from application files data
        best_available_info = account_info_from_app_files.get('best_available_info', {})
        owner = best_available_info.get('owner', {})
        joint_owner = best_available_info.get('jointOwner', {})
        
        self.logger.debug(f"Application files owner data: {owner}")
        self.logger.debug(f"Owner firstName: {owner.get('firstName', '')}")
        self.logger.debug(f"Owner lastName: {owner.get('lastName', '')}")
        self.logger.debug(f"Owner condition check: {owner and (owner.get('firstName') or owner.get('lastName'))}")
        
        # Primary account holder
        if owner and (owner.get('firstName') or owner.get('lastName')):
            self.logger.debug("Creating primary account holder from application files")
            # Build address string
            address_parts = []
            if owner.get('mailingAddressStreet'):
                address_parts.append(owner['mailingAddressStreet'])
            if owner.get('mailingAddressCity'):
                address_parts.append(owner['mailingAddressCity'])
            if owner.get('mailingAddressState'):
                address_parts.append(owner['mailingAddressState'])
            if owner.get('mailingAddressZip'):
                address_parts.append(owner['mailingAddressZip'])
            
            address = ', '.join(address_parts) if address_parts else ''
            
            # Build name
            first_name = owner.get('firstName', '')
            last_name = owner.get('lastName', '')
            account_name = f"{first_name} {last_name}".strip()
            if not account_name:
                account_name = dropbox_account_folder_name
            
            # Add application files name to names_found if not already present
            if account_name and account_name not in dropbox_account_information['names_found']:
                dropbox_account_information['names_found'].append(account_name)
            
            owner_account = {
                'account_name': account_name,
                'source': 'dropbox_application_files',
                'account_type': 'Primary',
                'first_name': first_name,
                'middle_name': '',  # Not typically available in app files
                'last_name': last_name,
                'birthdate': owner.get('dateOfBirth', ''),
                'gender': owner.get('gender', ''),
                'phone': owner.get('phoneNumber', ''),
                'address': address,
                'email': owner.get('emailAddress', ''),
                'additional_info': '',
                'match_status': 'N/A',  # Not applicable for app files
                'drivers_license': None
            }
            self.logger.debug(f"Created application files account: {owner_account}")
            dropbox_account_information['accounts'].append(owner_account)
        else:
            self.logger.debug("No primary account holder found in application files")
        
        # Joint account holder
        if joint_owner and (joint_owner.get('firstName') or joint_owner.get('lastName')):
            # Build address string
            address_parts = []
            if joint_owner.get('mailingAddressStreet'):
                address_parts.append(joint_owner['mailingAddressStreet'])
            if joint_owner.get('mailingAddressCity'):
                address_parts.append(joint_owner['mailingAddressCity'])
            if joint_owner.get('mailingAddressState'):
                address_parts.append(joint_owner['mailingAddressState'])
            if joint_owner.get('mailingAddressZip'):
                address_parts.append(joint_owner['mailingAddressZip'])
            
            address = ', '.join(address_parts) if address_parts else ''
            
            # Build name
            first_name = joint_owner.get('firstName', '')
            last_name = joint_owner.get('lastName', '')
            account_name = f"{first_name} {last_name}".strip()
            if not account_name:
                account_name = f"{dropbox_account_folder_name} (Joint)"
            
            # Add joint account name to names_found if not already present
            if account_name and account_name not in dropbox_account_information['names_found']:
                dropbox_account_information['names_found'].append(account_name)
            
            joint_account = {
                'account_name': account_name,
                'source': 'dropbox_application_files',
                'account_type': 'Joint',
                'first_name': first_name,
                'middle_name': '',  # Not typically available in app files
                'last_name': last_name,
                'birthdate': joint_owner.get('dateOfBirth', ''),
                'gender': joint_owner.get('gender', ''),
                'phone': joint_owner.get('phoneNumber', ''),
                'address': address,
                'email': joint_owner.get('emailAddress', ''),
                'additional_info': '',
                'match_status': 'N/A',  # Not applicable for app files
                'drivers_license': None
            }
            dropbox_account_information['accounts'].append(joint_account)
        
        return dropbox_account_information

    def _handle_log_dropbox_account_information(self) -> None:
        """Handle the log-dropbox-account-information command."""
        self.logger.info("[_handle_log_dropbox_account_information] Executing command handler: log-dropbox-account-information")
        
        # Build the dropbox account information structure
        dropbox_account_information = self._build_dropbox_account_information()
        
        # Store it in the command runner data
        self.set_data('dropbox_account_information', dropbox_account_information)
        
        # Get the account folder name
        dropbox_account_folder_name = self.get_data('dropbox_account_folder_name')
        
        # Log the information using the new logging utilities
        from sync.dropbox_client.utils.logging_utils import log_dropbox_account_information
        log_dropbox_account_information(
            dropbox_account_information,
            dropbox_account_folder_name,
            self.logger,
            self.summary_logger,
            self.report_logger
        )

    def _handle_log_dropbox_account_information_json(self) -> None:
        """Handle the log-dropbox-account-information-json command."""
        self.logger.info("Executing command handler: log-dropbox-account-information-json")
        
        # Build the dropbox account information structure
        dropbox_account_information = self._build_dropbox_account_information()
        
        # Store it in the command runner data
        self.set_data('dropbox_account_information', dropbox_account_information)
        
        # Log the information in JSON format
        from sync.dropbox_client.utils.logging_utils import log_json_format
        log_json_format(dropbox_account_information, self.logger)

    def _store_in_supabase(self) -> None:
        """Store data in Supabase database.
        This command will store the extracted DOB and gender information in Supabase.
        """
        self.logger.info("Starting store-in-supabase operation")
        self.report_logger.info("\n=== STORING DATA IN SUPABASE ===")
        
        # Get required context
        dropbox_client = self.get_context('dropbox_client')
        dropbox_salesforce_folder = dropbox_client.get_dropbox_salesforce_folder()
        dropbox_account_folder_name = self.get_data('dropbox_account_folder_name')
        logging.info(f"dropbox_account_folder_name: {dropbox_account_folder_name}")

        try:
            # Get or create Supabase client
            try:
                supabase_client = self.get_context('supabase_client')
                self.logger.info("Using existing Supabase client from context")
            except KeyError:
                self.logger.info("No Supabase client found in context, creating new instance")
                from supabase_client import SupabaseClient
                supabase_client = SupabaseClient()
                self.set_context('supabase_client', supabase_client)
            
            # Get the dropbox account folder from the database
            self.logger.info(f"Getting dropbox account from database for {dropbox_account_folder_name}")
            dropbox_account = supabase_client.get_dropbox_account_by_folder(dropbox_account_folder_name)
            if not dropbox_account:
                error_msg = f"Dropbox account not found for folder: {dropbox_account_folder_name}"
                self.logger.error(error_msg)
                self.report_logger.error(f"\n{error_msg}")
                return

            # Get the applications for the dropbox account
            applications = dropbox_account.applications
            self.logger.info(f"Found {len(applications)} applications for {dropbox_account_folder_name}")
            self.report_logger.info(f"\nFound {len(applications)} applications for {dropbox_account_folder_name}")

            # Generate the current account summary
            account_summary = supabase_client.generate_account_summary(dropbox_account_folder_name)
            self.logger.info(f"Account summary for {dropbox_account_folder_name}:\n{account_summary}")
            self.report_logger.info(f"\nAccount summary for {dropbox_account_folder_name}:\n{account_summary}")

            # Store the applications in Supabase
            for application in applications:
                supabase_client.store_application(application)
            
            # Get the data to store
            summary_data = self.get_data('summary_data')
            if not summary_data:
                error_msg = "No summary data found to store in Supabase"
                self.logger.error(error_msg)
                self.report_logger.error(f"\n{error_msg}")
                return
            
            # Store the data in Supabase
            for folder, files in summary_data['all_folder_app_files'].items():
                for file in files:
                    if file.path_display in summary_data['files_with_birthdate']:
                        birthdate = summary_data['file_birthdates'].get(file.path_display, '')
                        sex = summary_data['file_sexes'].get(file.path_display, '')
                        
                        # Prepare data for Supabase
                        data = {
                            'folder_name': folder,
                            'file_name': file.name,
                            'file_path': file.path_display,
                            'birthdate': birthdate,
                            'sex': sex,
                            'created_at': datetime.now().isoformat()
                        }
                        
                        try:
                            # Update data into Supabase using the client        
                            result = supabase_client.client.table('account_files').update(data).eq('file_path', file.path_display).execute()
                            self.logger.info(f"Successfully stored data for {file.name} in Supabase")
                            self.report_logger.info(f"\nSuccessfully stored data for {file.name} in Supabase")
                        except Exception as e:
                            error_msg = f"Error storing data for {file.name} in Supabase: {str(e)}"
                            self.logger.error(error_msg)
                            self.report_logger.error(f"\n{error_msg}")
                            if not self.args.continue_on_error:
                                raise
            
            self.logger.info("Successfully completed store-in-supabase operation")
            self.report_logger.info("\nSuccessfully completed store-in-supabase operation")
            
        except Exception as e:
            error_msg = f"Error in store-in-supabase operation: {str(e)}"
            self.logger.error(error_msg)
            self.report_logger.error(f"\n{error_msg}")
            raise

    def _search_supabase(self) -> None:
        """Search for account information in Supabase database.
        This command will search for account information in Supabase based on various criteria.
        """
        self.logger.info("Starting search-supabase operation")
        self.report_logger.info("\n=== SEARCHING SUPABASE DATABASE ===")
        
        try:
            # Get or create Supabase client
            try:
                supabase_client = self.get_context('supabase_client')
                self.logger.info("Using existing Supabase client from context")
            except KeyError:
                self.logger.info("No Supabase client found in context, creating new instance")
                from supabase_client.client import SupabaseClient
                supabase_client = SupabaseClient()
                self.set_context('supabase_client', supabase_client)
            
            # Get search criteria from data
            self.logger.debug("Available data keys: %s", list(self._data.keys()))
            folder_name = self.get_data('dropbox_account_folder_name')
            if not folder_name:
                self.logger.error("No search criteria provided. Please provide a folder name.")
                return
            
            # Get additional search criteria if provided
            search_criteria = {}
            try:
                if self.get_data('birthdate'):
                    search_criteria['birthdate'] = self.get_data('birthdate')
            except KeyError:
                pass
                
            try:
                if self.get_data('gender'):
                    search_criteria['gender'] = self.get_data('gender')
            except KeyError:
                pass
                
            try:
                if self.get_data('application_type'):
                    search_criteria['application_type'] = self.get_data('application_type')
            except KeyError:
                pass
            
            # Search in Supabase
            self.logger.info("Searching for account: %s", folder_name)
            result = supabase_client.generate_search_results_summary(folder_name, search_criteria)
            self.report_logger.info(result)
            
        except Exception as e:
            import traceback
            error_msg = f"Error searching Supabase: {str(e)}"
            stack_trace = traceback.format_exc()
            self.logger.error(error_msg)
            self.logger.error("Stack trace:\n%s", stack_trace)
            self.report_logger.error(f"\n{error_msg}")
            self.report_logger.error(f"\nStack trace:\n{stack_trace}") 

    def _list_dropbox_account_app_files(self) -> None:
        """List all application files in the Dropbox account folder.
        This command will list all files that appear to be application files in the specified Dropbox account folder.
        """
        self.logger.info("Starting list-dropbox-account-app-files operation")
        self.report_logger.info("\n=== LISTING DROPBOX ACCOUNT APPLICATION FILES ===")
        
        try:
            # Get required context
            dropbox_client = self.get_context('dropbox_client')
            dropbox_root_folder = self.get_context('dropbox_root_folder')
            dropbox_account_folder_name = self.get_data('dropbox_account_folder_name')
            logging.info(f"dropbox_account_folder_name: {dropbox_account_folder_name}")

            # Get file filter if specified
            file_filter = self.args.file_filter
            if file_filter:
                self.logger.info(f"Using file filter: {file_filter} (only files matching this pattern will be listed)")
                self.report_logger.info(f"\nUsing file filter: {file_filter} (only files matching this pattern will be listed)")

            # Construct folder path
            folder_path = f"/{dropbox_root_folder}/{dropbox_account_folder_name}"
            folder_path = folder_path.replace('//', '/')
            
            # List all files in the folder
            files = list_dropbox_folder_contents(dropbox_client.dbx, folder_path)
            
            # Filter for application files
            app_files = []
            for file in files:
                if isinstance(file, dropbox.files.FileMetadata):
                    # Check if file matches filter if specified
                    if file_filter and not fnmatch.fnmatch(file.name.lower(), file_filter.lower()):
                        continue
                    
                    # Check if file appears to be an application file
                    if any(keyword in file.name.lower() for keyword in ['application', 'app', 'form', 'registration']):
                        app_files.append(file)
            
            # Log the results
            self.summary_logger.info(f"\nDropbox Account Folder: {dropbox_account_folder_name}")
            if app_files:
                self.summary_logger.info(f"Found {len(app_files)} application files:")
                for file in app_files:
                    self.summary_logger.info(f"  📄 {file.name}")
                    # Log file metadata
                    self.summary_logger.info(f"    📅 Modified: {file.server_modified}")
                    self.summary_logger.info(f"    📦 Size: {file.size:,} bytes")
            else:
                self.summary_logger.info(f"  🚫 No application files found for {dropbox_account_folder_name}")

            self.logger.info("\nSuccessfully completed list-dropbox-account-app-files operation")
            
        except Exception as e:
            error_msg = f"Error in list-dropbox-account-app-files operation: {str(e)}"
            self.logger.error(error_msg)
            raise 

    def _handle_analyze_account_data(self) -> None:
        """Handle the analyze-account-data command."""
        self.logger.info("Executing command handler: analyze-account-data")
        self.logger.info("Starting analyze-account-data operation")
        
        # Rebuild dropbox account information to ensure it includes latest application files data
        self.logger.debug("Rebuilding dropbox account information for analysis")
        dropbox_account_information = self._build_dropbox_account_information()
        self.set_data('dropbox_account_information', dropbox_account_information)
        
        # Import and run the analysis using the proper function that includes logging
        from sync.commands.analyze_account_data import analyze_account_data
        
        # Run the analysis which will handle all the logging
        result = analyze_account_data(self)
        
        if result['status'] == 'success':
            self.logger.info("Successfully completed analyze-account-data operation")
        else:
            error_msg = f"Analysis failed: {result.get('message', 'Unknown error')}"
            self.logger.error(error_msg)
            raise Exception(error_msg) 

    def _create_account_report_file(self, dropbox_account_folder_name: str, aggregated_info: Dict[str, Any], summary_data: Dict[str, Any]) -> None:
        """Create a report file for the extracted account information.
        
        Args:
            dropbox_account_folder_name: The name of the Dropbox account folder
            aggregated_info: The aggregated account information
            summary_data: The summary data from app file extraction
        """
        try:
            # Create reports subdirectory
            reports_dir = os.path.join(self.log_dir, 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            
            # Sanitize the folder name for use as a filename
            safe_filename = dropbox_account_folder_name.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
            account_file_path = os.path.join(reports_dir, f"{safe_filename}_app_files_extraction.txt")
            
            # Get additional search results from command runner data
            dropbox_search_result = None
            salesforce_search_result = None
            try:
                dropbox_search_result = self.get_data('dropbox_account_info')
            except KeyError:
                pass
            
            try:
                salesforce_search_result = self.get_data('result')  # This contains the Salesforce search result
            except KeyError:
                pass
            
            # Write the report to the account-specific file
            with open(account_file_path, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write("📄 COMPREHENSIVE ACCOUNT SEARCH REPORT\n")
                f.write("=" * 80 + "\n")
                f.write(f"📁 Dropbox Account Folder: {dropbox_account_folder_name}\n")
                f.write(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
                
                # Search Results Summary
                f.write("🔍 **SEARCH RESULTS SUMMARY**\n")
                f.write("-" * 40 + "\n")
                
                # Dropbox Client List Search
                if dropbox_search_result:
                    dropbox_status = dropbox_search_result.get('search_info', {}).get('match_info', {}).get('match_status', 'Unknown')
                    # Use total_matches from match_info instead of length of matches array
                    dropbox_matches = dropbox_search_result.get('search_info', {}).get('match_info', {}).get('total_matches', 0)
                    f.write(f"📦 Dropbox Client List Search: {'✅ Match Found' if dropbox_status == 'Match found' else '❌ No Match Found'}\n")
                    f.write(f"   📊 Matches Found: {dropbox_matches}\n")
                    f.write(f"   📋 Status: {dropbox_status}\n")
                else:
                    f.write("📦 Dropbox Client List Search: ⚠️ Not Available\n")
                
                # Salesforce Search
                if salesforce_search_result:
                    salesforce_status = salesforce_search_result.get('match_info', {}).get('match_status', 'Unknown')
                    salesforce_matches = len(salesforce_search_result.get('matches', []))
                    salesforce_view = salesforce_search_result.get('view', 'Unknown')
                    f.write(f"⚡ Salesforce Search: {'✅ Match Found' if salesforce_status == 'Match Found' else '❌ No Match Found'}\n")
                    f.write(f"   📊 Matches Found: {salesforce_matches}\n")
                    f.write(f"   📋 Status: {salesforce_status}\n")
                    f.write(f"   👁️ View Searched: {salesforce_view}\n")
                else:
                    f.write("⚡ Salesforce Search: ⚠️ Not Available\n")
                
                # Application Files Search
                total_files = aggregated_info.get('total_files_processed', 0)
                complete_files = aggregated_info.get('files_with_complete_info', 0)
                partial_files = aggregated_info.get('files_with_partial_info', 0)
                no_info_files = aggregated_info.get('files_with_no_info', 0)
                
                if total_files > 0:
                    f.write(f"📄 Application Files Search: {'✅ Files Found' if complete_files > 0 or partial_files > 0 else '❌ No Useful Files Found'}\n")
                    f.write(f"   📊 Total Files: {total_files}\n")
                    f.write(f"   ✅ Complete Info: {complete_files}\n")
                    f.write(f"   ⚠️ Partial Info: {partial_files}\n")
                    f.write(f"   ❌ No Info: {no_info_files}\n")
                else:
                    f.write("📄 Application Files Search: 🚫 No Application Files Found\n")
                    f.write(f"   📊 Total Files: {total_files}\n")
                
                f.write("\n")
                
                # Overall Status
                f.write("📊 **OVERALL STATUS**\n")
                f.write("-" * 40 + "\n")
                
                # Determine overall status
                has_dropbox_match = dropbox_search_result and dropbox_search_result.get('search_info', {}).get('match_info', {}).get('match_status') == 'Match found'
                has_salesforce_match = salesforce_search_result and salesforce_search_result.get('match_info', {}).get('match_status') == 'Match Found'
                has_app_files = total_files > 0 and (complete_files > 0 or partial_files > 0)
                
                if has_dropbox_match and has_salesforce_match and has_app_files:
                    overall_status = "✅ Complete - All sources have data"
                elif has_dropbox_match or has_salesforce_match or has_app_files:
                    overall_status = "⚠️ Partial - Some sources have data"
                else:
                    overall_status = "❌ Incomplete - No data found in any source"
                
                f.write(f"🎯 Overall Status: {overall_status}\n")
                f.write(f"📦 Dropbox Match: {'✅ Yes' if has_dropbox_match else '❌ No'}\n")
                f.write(f"⚡ Salesforce Match: {'✅ Yes' if has_salesforce_match else '❌ No'}\n")
                f.write(f"📄 Application Files: {'✅ Yes' if has_app_files else '❌ No'}\n")
                f.write("\n")
                
                # File processing statistics
                f.write("📊 **FILE PROCESSING STATISTICS**\n")
                f.write("-" * 40 + "\n")
                f.write(f"📄 Total Files Processed: {total_files}\n")
                f.write(f"✅ Files with Complete Info: {complete_files}\n")
                f.write(f"⚠️ Files with Partial Info: {partial_files}\n")
                f.write(f"❌ Files with No Info: {no_info_files}\n")
                f.write(f"📊 Account Info Status: {'✅ Complete' if aggregated_info.get('has_complete_account_info', False) else '❌ Incomplete'}\n\n")
                
                # Status information
                f.write("📋 **STATUS INFORMATION**\n")
                f.write("-" * 40 + "\n")
                f.write(f"Status: {aggregated_info.get('status', 'Unknown')}\n")
                f.write(f"Application Type: {aggregated_info.get('application_type', 'N/A')}\n\n")
                
                # Best available information
                best_info = aggregated_info.get('best_available_info', {})
                if best_info:
                    f.write("👤 **BEST AVAILABLE INFORMATION**\n")
                    f.write("-" * 40 + "\n")
                    
                    # Owner information
                    owner = best_info.get('owner', {})
                    if owner:
                        f.write("📋 **Primary Account Holder**\n")
                        f.write(f"   First Name: {owner.get('firstName', 'N/A')}\n")
                        f.write(f"   Last Name: {owner.get('lastName', 'N/A')}\n")
                        f.write(f"   Date of Birth: {owner.get('dateOfBirth', 'N/A')}\n")
                        f.write(f"   Gender: {owner.get('gender', 'N/A')}\n")
                        
                        # Build address from components
                        if owner.get('mailingAddressStreet'):
                            address = f"{owner.get('mailingAddressStreet')}"
                            if owner.get('mailingAddressCity'):
                                address += f", {owner.get('mailingAddressCity')}"
                            if owner.get('mailingAddressState'):
                                address += f", {owner.get('mailingAddressState')}"
                            if owner.get('mailingAddressZip'):
                                address += f" {owner.get('mailingAddressZip')}"
                            f.write(f"   Address: {address}\n")
                        else:
                            f.write(f"   Address: N/A\n")
                        
                        f.write(f"   Phone: {owner.get('phoneNumber', 'N/A')}\n")
                        f.write(f"   Email: {owner.get('emailAddress', 'N/A')}\n")
                        f.write(f"   SSN/Tax ID: {owner.get('ssn', 'N/A')}\n\n")
                    
                    # Joint owner information
                    joint_owner = best_info.get('jointOwner', {})
                    if joint_owner:
                        f.write("👥 **Joint Account Holder**\n")
                        f.write(f"   First Name: {joint_owner.get('firstName', 'N/A')}\n")
                        f.write(f"   Last Name: {joint_owner.get('lastName', 'N/A')}\n")
                        f.write(f"   Date of Birth: {joint_owner.get('dateOfBirth', 'N/A')}\n")
                        f.write(f"   Gender: {joint_owner.get('gender', 'N/A')}\n")
                        
                        # Build address from components
                        if joint_owner.get('mailingAddressStreet'):
                            address = f"{joint_owner.get('mailingAddressStreet')}"
                            if joint_owner.get('mailingAddressCity'):
                                address += f", {joint_owner.get('mailingAddressCity')}"
                            if joint_owner.get('mailingAddressState'):
                                address += f", {joint_owner.get('mailingAddressState')}"
                            if joint_owner.get('mailingAddressZip'):
                                address += f" {joint_owner.get('mailingAddressZip')}"
                            f.write(f"   Address: {address}\n")
                        else:
                            f.write(f"   Address: N/A\n")
                        
                        f.write(f"   Phone: {joint_owner.get('phoneNumber', 'N/A')}\n")
                        f.write(f"   Email: {joint_owner.get('emailAddress', 'N/A')}\n")
                        f.write(f"   SSN/Tax ID: {joint_owner.get('ssn', 'N/A')}\n\n")
                
                # File details
                file_details = aggregated_info.get('file_details', {})
                if file_details:
                    f.write("📄 **FILE DETAILS**\n")
                    f.write("-" * 40 + "\n")
                    for file_path, detail in file_details.items():
                        f.write(f"📁 {file_path}\n")
                        f.write(f"   Status: {detail.get('status', 'Unknown')}\n")
                        f.write(f"   Info Quality: {detail.get('info_quality', 'Unknown')}\n")
                        
                        # Add extracted fields information
                        info = detail.get('info', {})
                        if info:
                            # Owner information
                            owner = info.get('owner', {})
                            if owner:
                                f.write(f"   👤 **Owner Information:**\n")
                                if owner.get('firstName') or owner.get('lastName'):
                                    f.write(f"      Name: {owner.get('firstName', '')} {owner.get('lastName', '')}\n")
                                if owner.get('dateOfBirth'):
                                    f.write(f"      DOB: {owner.get('dateOfBirth')}\n")
                                if owner.get('gender'):
                                    f.write(f"      Gender: {owner.get('gender')}\n")
                                if owner.get('phoneNumber'):
                                    f.write(f"      Phone: {owner.get('phoneNumber')}\n")
                                if owner.get('emailAddress'):
                                    f.write(f"      Email: {owner.get('emailAddress')}\n")
                                if owner.get('mailingAddressStreet'):
                                    address = f"{owner.get('mailingAddressStreet')}"
                                    if owner.get('mailingAddressCity'):
                                        address += f", {owner.get('mailingAddressCity')}"
                                    if owner.get('mailingAddressState'):
                                        address += f", {owner.get('mailingAddressState')}"
                                    if owner.get('mailingAddressZip'):
                                        address += f" {owner.get('mailingAddressZip')}"
                                    f.write(f"      Address: {address}\n")
                            
                            # Joint owner information
                            joint_owner = info.get('jointOwner', {})
                            if joint_owner:
                                f.write(f"   👥 **Joint Owner Information:**\n")
                                if joint_owner.get('firstName') or joint_owner.get('lastName'):
                                    f.write(f"      Name: {joint_owner.get('firstName', '')} {joint_owner.get('lastName', '')}\n")
                                if joint_owner.get('dateOfBirth'):
                                    f.write(f"      DOB: {joint_owner.get('dateOfBirth')}\n")
                                if joint_owner.get('gender'):
                                    f.write(f"      Gender: {joint_owner.get('gender')}\n")
                                if joint_owner.get('phoneNumber'):
                                    f.write(f"      Phone: {joint_owner.get('phoneNumber')}\n")
                                if joint_owner.get('emailAddress'):
                                    f.write(f"      Email: {joint_owner.get('emailAddress')}\n")
                                if joint_owner.get('mailingAddressStreet'):
                                    address = f"{joint_owner.get('mailingAddressStreet')}"
                                    if joint_owner.get('mailingAddressCity'):
                                        address += f", {joint_owner.get('mailingAddressCity')}"
                                    if joint_owner.get('mailingAddressState'):
                                        address += f", {joint_owner.get('mailingAddressState')}"
                                    if joint_owner.get('mailingAddressZip'):
                                        address += f" {joint_owner.get('mailingAddressZip')}"
                                    f.write(f"      Address: {address}\n")
                            
                            # Application type and status
                            if info.get('application_type'):
                                f.write(f"   📄 Application Type: {info.get('application_type')}\n")
                            if info.get('status'):
                                f.write(f"   📊 Status: {info.get('status')}\n")
                        
                        if detail.get('notes'):
                            f.write(f"   Notes: {', '.join(detail['notes'])}\n")
                        f.write("\n")
                
                # Notes
                notes = aggregated_info.get('notes', [])
                if notes:
                    f.write("📝 **PROCESSING NOTES**\n")
                    f.write("-" * 40 + "\n")
                    for note in notes:
                        f.write(f"   • {note}\n")
                    f.write("\n")
                
                # Summary data (if available)
                if summary_data:
                    f.write("📊 **SUMMARY DATA**\n")
                    f.write("-" * 40 + "\n")
                    f.write(f"Total App Files: {summary_data.get('total_app_files', 0)}\n")
                    f.write(f"Processed Folders: {len(summary_data.get('processed_folders', set()))}\n")
                    f.write(f"Files with Birthdate: {len(summary_data.get('files_with_birthdate', set()))}\n")
                    f.write(f"Files with Name: {len(summary_data.get('files_with_name', []))}\n")
                    f.write(f"Skipped Zero-Length Files: {summary_data.get('skipped_zero_length_files', 0)}\n")
                
                f.write("\n" + "=" * 80 + "\n")
                f.write("📄 END OF COMPREHENSIVE ACCOUNT SEARCH REPORT\n")
                f.write("=" * 80 + "\n")
            
            self.logger.info(f"✅ Account comprehensive search report written to: {account_file_path}")
            self.summary_logger.info(f"✅ Account comprehensive search report written to: {account_file_path}")
            
        except Exception as e:
            error_msg = f"❌ Error creating account report file: {str(e)}"
            self.logger.error(error_msg)
            self.summary_logger.error(error_msg) 

    def _copy_dropbox_account_files_preserve_dates(self) -> None:
        """Copy files in Dropbox account folder to another location while preserving original modification dates."""
        self.logger.info("Starting copy-dropbox-account-files-preserve-dates operation")
        self.report_logger.info("\n=== COPYING DROPBOX ACCOUNT FILES WITH PRESERVED DATES ===")
        
        try:
            # Get required context
            dropbox_client = self.get_context('dropbox_client')
            dropbox_root_folder = self.get_context('dropbox_root_folder')
            dropbox_account_folder_name = self.get_data('dropbox_account_folder_name')
            dropbox_salesforce_folder = dropbox_client.get_dropbox_salesforce_folder()

            self.logger.info(f"dropbox_client: {dropbox_client}")
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

            # Check if destination folder already exists
            try:
                dropbox_client.dbx.files_get_metadata(dest_path)
                # Folder exists, prompt for deletion
                self.logger.info(f"Destination folder already exists: {dest_path}")
                self.report_logger.info(f"\nDestination folder already exists: {dest_path}")
                
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

            # Create destination folder
            self.logger.info(f"Creating destination folder: {dest_path}")
            self.report_logger.info(f"\nCreating destination folder: {dest_path}")
            dropbox_client.dbx.files_create_folder_v2(dest_path)

            # List all files in the source folder
            source_files = list_dropbox_folder_contents(dropbox_client.dbx, source_path)
            
            if not source_files:
                self.logger.info("No files found in source folder")
                self.report_logger.info("\nNo files found in source folder")
                return
            
            # Create a temporary directory for downloads
            temp_dir = os.path.join(os.getcwd(), 'temp_preserve_dates')
            os.makedirs(temp_dir, exist_ok=True)
            
            copied_files = 0
            failed_files = 0
            
            try:
                # Process each file
                for file in source_files:
                    if isinstance(file, dropbox.files.FileMetadata):
                        try:
                            self.logger.info(f"Processing file: {file.name}")
                            self.report_logger.info(f"\nProcessing file: {file.name}")
                            
                            # Get original metadata
                            original_modified = file.server_modified
                            self.logger.info(f"Original modification date: {original_modified}")
                            
                            # Download file to temporary location
                            temp_file_path = os.path.join(temp_dir, file.name)
                            self.logger.info(f"Downloading to temporary location: {temp_file_path}")
                            
                            dropbox_client.dbx.files_download_to_file(temp_file_path, file.path_display)
                            
                            # Upload to destination with preserved modification date
                            dest_file_path = f"{dest_path}/{file.name}"
                            dest_file_path = dest_file_path.replace('//', '/')
                            
                            self.logger.info(f"Uploading to destination: {dest_file_path}")
                            
                            with open(temp_file_path, 'rb') as f:
                                file_content = f.read()
                                
                                # Upload with original modification date
                                dropbox_client.dbx.files_upload(
                                    file_content,
                                    dest_file_path,
                                    mode=dropbox.files.WriteMode.overwrite,
                                    client_modified=original_modified
                                )
                            
                            # Clean up temporary file
                            os.remove(temp_file_path)
                            
                            copied_files += 1
                            self.logger.info(f"Successfully copied {file.name} with preserved date")
                            self.report_logger.info(f"Successfully copied {file.name} with preserved date: {original_modified}")
                            
                        except Exception as e:
                            failed_files += 1
                            error_msg = f"Error copying file {file.name}: {str(e)}"
                            self.logger.error(error_msg)
                            self.report_logger.error(f"\n{error_msg}")
                            
                            # Clean up temporary file if it exists
                            temp_file_path = os.path.join(temp_dir, file.name)
                            if os.path.exists(temp_file_path):
                                try:
                                    os.remove(temp_file_path)
                                except:
                                    pass
                            
                            if not self.args.continue_on_error:
                                raise
                
            finally:
                # Clean up temporary directory
                try:
                    os.rmdir(temp_dir)
                    self.logger.info(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    self.logger.warning(f"Could not remove temporary directory {temp_dir}: {str(e)}")
            
            # Log summary
            self.logger.info(f"Copy operation completed. Files copied: {copied_files}, Failed: {failed_files}")
            self.report_logger.info(f"\nCopy operation completed. Files copied: {copied_files}, Failed: {failed_files}")
            
            if copied_files > 0:
                self.logger.info("Successfully completed copy-dropbox-account-files-preserve-dates operation")
                self.report_logger.info("\nSuccessfully completed copy-dropbox-account-files-preserve-dates operation")
            else:
                self.logger.warning("No files were successfully copied")
                self.report_logger.warning("\nNo files were successfully copied")

        except Exception as e:
            error_msg = f"Error in copy-dropbox-account-files-preserve-dates operation: {str(e)}"
            self.logger.error(error_msg)
            self.report_logger.error(f"\n{error_msg}")
            raise